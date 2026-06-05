#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Student model trainer for online knowledge distillation.

Uses onnxruntime-training (ORT Training) when available, falling back to
a pure-onnxruntime inference-only mode (no backprop) with an EMA-based
soft-label approach for progressive model refinement.

The primary workflow:
1. Load student ONNX model
2. Run student inference on incoming frame
3. Compute distillation loss vs teacher predictions
4. If ORT Training available: backpropagate and update weights
5. Export updated ONNX model on demand
"""

import copy
import logging
import os
import tempfile
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import onnxruntime

from node.DLNode.object_detection.onnx_session_utils import make_session
from node.DLNode.object_detection.CustomONNX.custom_onnx import CustomONNX
from node.DLNode.online_training.distillation_loss import compute_distillation_score
from node.DLNode.online_training.online_adapter import BoxAffineAdapter
from node.DLNode.online_training.torch_student import (
    TorchStudent,
    is_torch_backprop_available,
    is_format_supported as _torch_format_supported,
)
from node.DLNode.online_training.distillation_loss_ort import (
    compute_distillation_loss_numpy,
    build_distillation_loss_graph,
    _ONNX_AVAILABLE,
)
from node.DLNode.online_training import ort_training_artifacts as ort_art

logger = logging.getLogger(__name__)

# The student CNN is inference-only under plain onnxruntime, so the requested
# distillation loss is back-propagated through a small affine box-correction head
# (see online_adapter.py). The node learning-rate slider (~1e-5 .. 1e-2) is scaled
# into the normalised coordinate space the head works in so that improvement is
# actually visible within a reasonable number of frames.
_ADAPTER_LR_GAIN = 500.0
_ADAPTER_LR_MIN = 1e-3
_ADAPTER_LR_MAX = 0.5

# Check if onnxruntime-training is available
_ORT_TRAINING_AVAILABLE = False
try:
    from onnxruntime.training import api as ort_training_api
    _ORT_TRAINING_AVAILABLE = True
    logger.info("[StudentTrainer] onnxruntime-training is available — full backprop enabled.")
except ImportError:
    logger.info(
        "[StudentTrainer] onnxruntime-training not available — "
        "inference-only mode (no weight updates). Install with: pip install onnxruntime-training"
    )


class StudentTrainer:
    """Manages the student model lifecycle: inference, scoring, and optional training.

    Parameters
    ----------
    model_path : str
        Path to the student ONNX model file.
    input_width : int
        Model input width.
    input_height : int
        Model input height.
    output_format : str
        Output format ('yolo11', 'yolox' or 'nanodet').
    num_classes : int
        Number of detection classes.
    learning_rate : float
        Learning rate for weight updates.
    providers : list[str], optional
        ONNX Runtime execution providers.
    train_scope : str
        When the PyTorch backprop path is active, which part of the network to
        train: ``'head'`` (detection heads only, default) or ``'all'`` (backbone
        and heads).
    """

    def __init__(
        self,
        model_path: str,
        input_width: int = 640,
        input_height: int = 640,
        output_format: str = "yolo11",
        num_classes: int = 80,
        learning_rate: float = 0.0001,
        score_threshold: float = 0.3,
        providers: Optional[List[str]] = None,
        train_scope: str = "head",
    ):
        if providers is None:
            providers = ["CPUExecutionProvider"]

        self.model_path = model_path
        self.input_width = input_width
        self.input_height = input_height
        self.output_format = output_format
        self.num_classes = num_classes
        self.learning_rate = learning_rate
        self.score_threshold = score_threshold
        self.providers = providers
        self.train_scope = train_scope

        # Statistics
        self.frames_processed = 0
        self.total_score = 0.0
        self.current_score = 0.0
        self.best_score = 0.0
        # Distillation loss bookkeeping (lower is better). ``current_loss`` is the
        # requested set-based (DETR-style Hungarian) loss for the latest frame and
        # ``best_loss`` the lowest value seen so far. ``initial_loss`` is the very
        # first measured loss, used to report the student's improvement over time.
        self.current_loss = float('inf')
        self.best_loss = float('inf')
        self.initial_loss = None
        self.training_active = False
        self._last_loss = None
        self.last_train_loss = None

        # Real, gradient-trained correction head for the requested loss. This is
        # what lets the student's *output* actually change (and improve) frame to
        # frame even without onnxruntime-training.
        self._adapter = BoxAffineAdapter(learning_rate=_ADAPTER_LR_MIN)
        self._adaptation_available = True

        # Load the student model for inference
        self._student_model = CustomONNX(
            model_path=model_path,
            input_width=input_width,
            input_height=input_height,
            output_format=output_format,
            num_classes=num_classes,
            providers=providers,
        )

        # Keep a copy of the original model bytes for reset
        with open(model_path, 'rb') as f:
            self._original_model_bytes = f.read()

        # Real network backprop path: convert the student ONNX into a trainable
        # PyTorch module so the requested distillation loss is back-propagated
        # through the actual backbone/heads (not only the correction head). This
        # is optional: when torch/onnx2torch are unavailable or the conversion
        # fails, we silently fall back to the affine adaptation head.
        self._torch = None
        self._torch_backprop = False
        if is_torch_backprop_available() and _torch_format_supported(output_format):
            try:
                self._torch = TorchStudent(
                    model_path=model_path,
                    input_width=input_width,
                    input_height=input_height,
                    output_format=output_format,
                    num_classes=num_classes,
                    learning_rate=learning_rate,
                    train_scope=train_scope,
                )
                self._torch_backprop = True
                logger.info(
                    "[StudentTrainer] PyTorch backprop ENABLED — the student "
                    "network (%s) is trained with real gradient descent.",
                    train_scope,
                )
            except Exception as exc:
                logger.warning(
                    "[StudentTrainer] Could not enable PyTorch backprop (%s). "
                    "Falling back to the affine correction head.", exc,
                )
                self._torch = None
                self._torch_backprop = False
        elif is_torch_backprop_available():
            # PyTorch is installed but the student's decode format is not
            # supported by the differentiable TorchStudent path (e.g.
            # ``nanodet_multi``). Using it would yield no student boxes and no
            # weight updates, so keep ONNX inference (CustomONNX) and rely on the
            # ORT-training / affine-head path for learning instead.
            logger.info(
                "[StudentTrainer] PyTorch backprop not used for output_format "
                "'%s' (unsupported decode); using ONNX inference with "
                "ORT-training/affine-head updates.", output_format,
            )


        # Training state
        self._ort_training_session = None
        self._training_available = _ORT_TRAINING_AVAILABLE
        # ORT Training handles (set up below when available and the PyTorch path
        # is not already driving the backprop).
        self._ort_module = None
        self._ort_optimizer = None
        self._ort_checkpoint = None
        self._ort_student_out = None
        self._ort_artifact_dir = None
        self._ort_infer_dirty = False
        self._ort_export_every = 1
        self._ort_updates = 0

        # Real end-to-end ORT-training backprop. Built only when onnxruntime-training
        # is installed and the PyTorch path is not already active (PyTorch is
        # preferred when present). On any failure we silently keep the existing
        # fallbacks (affine correction head / inference-only loss).
        if self._training_available and not self._torch_backprop:
            self._setup_ort_training()

        # ONNX-based differentiable loss for training
        self._loss_session = None
        if _ONNX_AVAILABLE:
            try:
                loss_model = build_distillation_loss_graph(num_classes=num_classes)
                self._loss_model_path = os.path.join(
                    tempfile.gettempdir(), f"distillation_loss_{id(self)}.onnx"
                )
                import onnx as _onnx
                _onnx.save(loss_model, self._loss_model_path)
                self._loss_session = onnxruntime.InferenceSession(
                    self._loss_model_path, providers=["CPUExecutionProvider"]
                )
                logger.info("[StudentTrainer] ONNX distillation loss graph built and loaded.")
            except Exception as exc:
                logger.warning(f"[StudentTrainer] Failed to build ONNX loss graph: {exc}")
                self._loss_session = None

        logger.info(
            f"[StudentTrainer] Initialized — model={os.path.basename(model_path)}, "
            f"input={input_width}x{input_height}, format={output_format}, "
            f"training={'enabled' if self._training_available else 'inference-only'}, "
            f"ort_loss={'yes' if self._loss_session else 'numpy-fallback'}"
        )

    def _setup_ort_training(self):
        """Build ORT-training artifacts and create the training session.

        Implements plan sections A.1/A.2: merge the student ONNX with the
        differentiable decode + matched-distillation-loss graph, generate the
        ``training``/``eval``/``optimizer`` models + ``checkpoint`` via
        ``onnxruntime.training.artifacts``, then instantiate the
        ``CheckpointState`` + ``Module`` + ``Optimizer``. Stored on success in
        ``self._ort_training_session``; left as ``None`` on any failure so the
        caller falls back to the affine head.
        """
        if not ort_art.is_ort_training_available():
            logger.info(
                "[StudentTrainer] ORT-training artifacts module unavailable; "
                "skipping ORT backprop setup."
            )
            return
        try:
            merged, student_out = ort_art.merge_student_with_loss(
                self.model_path,
                num_classes=self.num_classes,
                input_width=self.input_width,
                input_height=self.input_height,
                output_format=self.output_format,
            )
            trainable, frozen = ort_art.select_trainable_params(
                merged, train_scope=self.train_scope,
            )
            if not trainable:
                logger.warning(
                    "[StudentTrainer] No trainable weights found for ORT training; "
                    "falling back to the affine head."
                )
                return

            self._ort_artifact_dir = os.path.join(
                tempfile.gettempdir(), f"ort_student_{id(self)}"
            )
            paths = ort_art.generate_training_artifacts(
                merged, trainable, frozen, self._ort_artifact_dir,
                optimizer="sgd",
            )

            self._ort_checkpoint = ort_training_api.CheckpointState.load_checkpoint(
                paths["checkpoint"]
            )
            self._ort_module = ort_training_api.Module(
                paths["training_model"],
                self._ort_checkpoint,
                paths["eval_model"],
            )
            self._ort_optimizer = ort_training_api.Optimizer(
                paths["optimizer_model"], self._ort_module
            )
            # Apply the requested learning rate to the optimizer.
            try:
                self._ort_optimizer.set_learning_rate(float(self.learning_rate))
            except Exception as exc:  # pragma: no cover - older ORT API
                logger.debug("ORT set_learning_rate unavailable: %s", exc)

            self._ort_student_out = student_out
            self._ort_training_session = self._ort_module
            self._ort_paths = paths
            logger.info(
                "[StudentTrainer] ORT-training backprop ENABLED — %d trainable "
                "weight tensors (scope=%s).", len(trainable), self.train_scope,
            )
        except Exception as exc:  # pragma: no cover - depends on ORT training
            logger.warning(
                "[StudentTrainer] Could not enable ORT-training backprop (%s). "
                "Falling back to the affine correction head.", exc,
            )
            self._ort_training_session = None
            self._ort_module = None
            self._ort_optimizer = None
            self._ort_checkpoint = None

    @property
    def is_training_available(self) -> bool:
        """Whether a real weight/parameter update can be performed.

        True when the PyTorch backprop path is active (real network training),
        when onnxruntime-training is installed (full-network backprop), or via
        the built-in affine adaptation head (always the case).
        """
        return (
            self._torch_backprop
            or self._training_available
            or self._adaptation_available
        )

    @property
    def backprop_mode(self) -> str:
        """Human-readable description of the active learning path."""
        if self._torch_backprop:
            return f"pytorch-{self.train_scope}"
        if self._training_available and self._ort_training_session is not None:
            return "ort-training"
        return "affine-head"

    @property
    def _network_update_count(self) -> int:
        """Number of real network backprop steps (PyTorch or ORT-training)."""
        if self._torch is not None:
            return int(self._torch.updates)
        return int(getattr(self, "_ort_updates", 0))

    @property
    def _network_backprop_active(self) -> bool:
        """True when a real-network backprop path (PyTorch or ORT) is active.

        In that case ``infer`` already returns predictions from the updated
        network weights, so the affine correction head must not be applied on
        top of them.
        """
        return bool(self._torch_backprop) or (self._ort_training_session is not None)

    @property
    def improvement(self) -> float:
        """Absolute loss reduction since the first frame (>= 0 means better)."""
        if self.initial_loss is None or self.current_loss == float('inf'):
            return 0.0
        return max(0.0, float(self.initial_loss - self.current_loss))

    @property
    def improvement_pct(self) -> float:
        """Relative loss reduction since the first frame, in percent."""
        if self.initial_loss is None or self.initial_loss <= 0.0:
            return 0.0
        return 100.0 * self.improvement / float(self.initial_loss)

    @property
    def avg_score(self) -> float:
        """Average distillation score over all processed frames."""
        if self.frames_processed == 0:
            return 0.0
        return self.total_score / self.frames_processed

    def infer(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run student model inference on a frame.

        When the PyTorch backprop path is active, inference uses the *trained*
        torch weights. When the ORT-training path is active, the trained weights
        are periodically exported back into a detection ONNX so the plain
        inference session reflects the learning (plan section B). Otherwise the
        original onnxruntime session is used.

        Returns (bboxes, scores, class_ids).
        """
        if self._torch_backprop and self._torch is not None:
            try:
                return self._torch_infer(frame)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"[StudentTrainer] torch inference failed: {exc}")
        elif self._ort_training_session is not None and self._ort_infer_dirty:
            self._refresh_ort_inference_model()
        return self._student_model(frame)

    def _refresh_ort_inference_model(self):  # pragma: no cover - needs ORT training
        """Export the trained ORT weights into a detection ONNX and reload it.

        Implements plan section B: ``Module.export_model_for_inferencing`` prunes
        the loss subgraph and emits a detection model carrying the updated
        weights (requesting the original student output tensor). The CustomONNX
        inference session is then rebuilt from it so displayed detections reflect
        the training.
        """
        try:
            infer_path = os.path.join(self._ort_artifact_dir, "student_trained.onnx")
            self._ort_module.export_model_for_inferencing(
                infer_path, [self._ort_student_out]
            )
            self._student_model = CustomONNX(
                model_path=infer_path,
                input_width=self.input_width,
                input_height=self.input_height,
                output_format=self.output_format,
                num_classes=self.num_classes,
                providers=self.providers,
            )
            self._ort_infer_dirty = False
            logger.debug("[StudentTrainer] Refreshed inference model from ORT weights.")
        except Exception as exc:
            logger.debug(f"[StudentTrainer] ORT inference refresh failed: {exc}")

    def _torch_infer(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Inference through the trained torch weights, reusing CustomONNX decode."""
        orig_h, orig_w = self._frame_size(frame)
        blob, ratio = self._student_model._preprocess(frame)
        raw = self._torch.forward_numpy(blob)
        if self.output_format == "yolox":
            return self._student_model._postprocess_yolox(raw, orig_w, orig_h, ratio)
        if self.output_format == "nanodet":
            return self._student_model._postprocess_nanodet(raw, orig_w, orig_h)
        return self._student_model._postprocess_yolo11(raw, orig_w, orig_h)

    def _update_last_loss(self, distillation: Dict) -> None:
        """Store the latest reported loss from the requested set-based metrics.

        Keeps a single source of truth for the loss across the inference and
        training paths.
        """
        self._last_loss = {
            'loss': distillation.get('loss', 0.0),
            'loss_box': distillation.get('loss_box', 0.0),
            'loss_class': distillation.get('loss_class', 0.0),
            'loss_iou': distillation.get('loss_iou', 0.0),
            'loss_cardinality': distillation.get('loss_cardinality', 0.0),
        }

    def train_step(
        self,
        frame: np.ndarray,
        teacher_bboxes: List,
        teacher_scores: List,
        teacher_class_ids: List,
        score_threshold: float = 0.3,
    ) -> Dict:
        """Perform one training step: inference + scoring + optional backprop.

        Parameters
        ----------
        frame : np.ndarray
            Input image (BGR).
        teacher_bboxes : list
            Teacher model bounding boxes [[x1,y1,x2,y2], ...].
        teacher_scores : list
            Teacher model confidence scores.
        teacher_class_ids : list
            Teacher model class IDs.
        score_threshold : float
            Minimum confidence to keep student predictions.

        Returns
        -------
        dict with keys:
            - student_bboxes, student_scores, student_class_ids: student predictions
              **after** the correction head has been applied (so the values you
              see reflect the current trained state)
            - distillation: distillation score metrics (includes the requested
              set-based loss under the ``loss`` key, lower = closer to teacher)
            - training_step: True when a real parameter update was performed this
              frame (the correction head learned from the requested loss)
        """
        # 1. Student inference (raw network output, before correction)
        s_bboxes, s_scores, s_class_ids = self.infer(frame)

        # Apply score threshold to student predictions
        if len(s_scores) > 0:
            mask = s_scores >= score_threshold
            s_bboxes = s_bboxes[mask]
            s_scores = s_scores[mask]
            s_class_ids = s_class_ids[mask]

        # 1b. When training only the affine correction head (no real-network
        # backprop path), apply it so the returned predictions reflect what the
        # head has learned so far. With the PyTorch or ORT-training backprop path
        # the network weights themselves are updated, so ``infer`` already returns
        # the improved predictions and no extra correction is applied.
        frame_h, frame_w = self._frame_size(frame)
        if not self._network_backprop_active and len(s_bboxes) > 0:
            s_bboxes = self._adapter.apply(s_bboxes, frame_w, frame_h).astype(np.float32)

        # 2. Compute distillation score + the requested set-based loss
        distillation = compute_distillation_score(
            list(teacher_bboxes),
            list(teacher_scores),
            list(teacher_class_ids),
            s_bboxes.tolist() if len(s_bboxes) > 0 else [],
            s_scores.tolist() if len(s_scores) > 0 else [],
            s_class_ids.tolist() if len(s_class_ids) > 0 else [],
        )

        # The reported loss is the *requested* set-based distillation loss (single
        # source of truth, identical to the one shown by the IoU/Chart nodes), not
        # a separate approximation.
        self._update_last_loss(distillation)

        # 3. Update statistics
        self.frames_processed += 1
        self.current_score = distillation['score']
        self.total_score += self.current_score
        if self.current_score > self.best_score:
            self.best_score = self.current_score

        # Track the requested loss (lower = better student).
        self.current_loss = float(distillation.get('loss', 0.0))
        if self.initial_loss is None:
            self.initial_loss = self.current_loss
        if self.current_loss < self.best_loss:
            self.best_loss = self.current_loss

        # 4. Training step. ``training_step`` is True only when a real parameter
        # update actually happened this frame.
        training_performed = False
        self.last_train_loss = None
        if self.training_active:
            if self._torch_backprop and self._torch is not None:
                # Real network backprop: the requested distillation loss is
                # propagated through the student backbone/heads via PyTorch.
                training_performed = self._torch_train_step(
                    frame, teacher_bboxes, teacher_class_ids, frame_w, frame_h,
                )
            elif self._ort_training_session is not None:
                # Real network backprop via onnxruntime-training: the merged
                # student+loss graph is differentiated and the optimizer updates
                # the trainable weights in-place.
                training_performed = self._do_backprop(
                    frame, teacher_bboxes, teacher_scores, teacher_class_ids,
                    distillation,
                )
            else:
                # Fallback: sub-gradient descent on the affine correction head.
                training_performed = self._adapt_step(
                    frame_w, frame_h,
                    teacher_bboxes, teacher_class_ids,
                    s_bboxes, s_class_ids,
                )

        return {
            'student_bboxes': s_bboxes,
            'student_scores': s_scores,
            'student_class_ids': s_class_ids,
            'distillation': distillation,
            'training_step': training_performed,
        }

    def _torch_train_step(self, frame, teacher_bboxes, teacher_class_ids,
                          frame_w, frame_h):
        """One real backprop step through the PyTorch student network.

        Returns True when an optimizer step updated the network weights.
        """
        try:
            blob, _ratio = self._student_model._preprocess(frame)
            loss_val = self._torch.train_step(
                blob, list(teacher_bboxes), list(teacher_class_ids),
                frame_w, frame_h,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"[StudentTrainer] torch train step failed: {exc}")
            return False
        if loss_val is None:
            return False
        self.last_train_loss = float(loss_val)
        return True

    @staticmethod
    def _frame_size(frame):
        """Return (height, width) of ``frame`` with a safe fallback."""
        if frame is not None and hasattr(frame, 'shape') and len(frame.shape) >= 2:
            return int(frame.shape[0]), int(frame.shape[1])
        return 1, 1

    def _adapt_step(self, frame_w, frame_h, teacher_bboxes, teacher_class_ids,
                    student_bboxes, student_class_ids):
        """One sub-gradient descent step of the correction head (requested loss).

        Returns True when the head parameters were updated.
        """
        # Scale the user learning rate into the head's normalised space so the
        # improvement is visible within a reasonable number of frames.
        eff_lr = float(np.clip(
            self.learning_rate * _ADAPTER_LR_GAIN,
            _ADAPTER_LR_MIN, _ADAPTER_LR_MAX,
        ))
        updated, _loss_before = self._adapter.update(
            teacher_bboxes, student_bboxes, frame_w, frame_h,
            teacher_classes=teacher_class_ids,
            student_classes=student_class_ids,
            learning_rate=eff_lr,
        )
        return bool(updated)

    def _do_backprop(self, frame, teacher_bboxes, teacher_scores,
                     teacher_class_ids, distillation=None):
        """Back-propagate the *requested* set-based distillation loss.

        The Hungarian set-based loss (``compute_set_distillation_loss``) drives the
        update. Because it relies on a discrete bipartite assignment, the matching
        is computed without gradients and the differentiable per-matched-pair terms
        (box L1 + (1 - IoU) + class CE) are what is propagated through the student
        network via onnxruntime-training.

        A real weight update requires a fully wired onnxruntime-training session.
        When that session is not available this method performs **no** weight
        update and returns ``False`` so callers never report a phantom training
        step.

        Returns
        -------
        bool
            True only if the student weights were actually updated.
        """
        # Keep the reported loss consistent with the requested set-based loss.
        if distillation is not None:
            self._update_last_loss(distillation)

        # Real backprop path: requires a wired onnxruntime-training session.
        if self._ort_training_session is None:
            # Inference-only: no differentiable end-to-end path is available
            # (post-processing/NMS runs in NumPy), so weights are left unchanged.
            return False

        try:
            return self._run_ort_training_step(
                frame, teacher_bboxes, teacher_scores, teacher_class_ids,
            )
        except Exception as exc:  # pragma: no cover - depends on ORT training
            logger.debug(f"[StudentTrainer] ORT training step failed: {exc}")
            return False

    def _run_ort_training_step(self, frame, teacher_bboxes, teacher_scores,
                               teacher_class_ids):  # pragma: no cover - needs ORT training
        """Run one onnxruntime-training optimizer step (plan sections A.3/A.4).

        Steps:
        1. Forward the student to get its raw output and decode it (NumPy) to
           obtain candidate anchor boxes in network-input space.
        2. Greedily match each teacher box to a unique student anchor
           out-of-graph (the discrete assignment is not differentiable).
        3. Feed the preprocessed image + matched anchor indices + teacher targets
           into the merged training graph; ``module.train_step`` runs the
           forward+backward, ``optimizer.step`` updates the trainable weights and
           ``module.lazy_reset_grad`` clears the gradients for the next frame.

        Returns True only when an optimizer step actually updated the weights.
        """
        teacher_boxes_orig = np.asarray(list(teacher_bboxes), dtype=np.float32).reshape(-1, 4)
        if len(teacher_boxes_orig) == 0:
            return False

        # 1. Preprocess once; reuse the blob for both the match forward and train.
        blob, _ratio = self._student_model._preprocess(frame)
        frame_h, frame_w = self._frame_size(frame)

        # Raw forward to decode candidate anchors for matching.
        raw_out = self._ort_student_raw_forward(blob)
        if raw_out is None:
            return False
        pred_boxes_in = self._decode_pred_boxes(raw_out)
        if pred_boxes_in is None or len(pred_boxes_in) == 0:
            return False

        # 2. Scale teacher boxes into network-input space and match out-of-graph.
        if self.output_format == "nanodet":
            # NanoDet uses letterbox (uniform aspect-ratio-preserving) preproc.
            ratio = min(self.input_height / max(1, int(frame_h)),
                        self.input_width / max(1, int(frame_w)))
            scale = np.array([ratio, ratio, ratio, ratio], dtype=np.float32)
        else:
            sx = self.input_width / max(1, int(frame_w))
            sy = self.input_height / max(1, int(frame_h))
            scale = np.array([sx, sy, sx, sy], dtype=np.float32)
        teacher_boxes_in = teacher_boxes_orig * scale
        anchor_idx = ort_art.greedy_match_anchors(pred_boxes_in, teacher_boxes_in)
        matched = ort_art.build_matched_targets(
            teacher_boxes_in, list(teacher_class_ids), anchor_idx, self.num_classes,
        )
        if matched is None:
            return False
        idx, tb, oh = matched

        # 3. One real forward+backward+optimizer step.
        inputs = [
            np.ascontiguousarray(blob, dtype=np.float32),
            np.ascontiguousarray(idx, dtype=np.int64),
            np.ascontiguousarray(tb, dtype=np.float32),
            np.ascontiguousarray(oh, dtype=np.float32),
        ]
        self._ort_module.train()
        outputs = self._ort_module.train_step(inputs)
        self._ort_optimizer.step()
        self._ort_module.lazy_reset_grad()

        loss_val = self._extract_scalar(outputs)
        if loss_val is not None:
            self.last_train_loss = float(loss_val)
        self._ort_updates += 1
        # The weights changed, so the cached inference model is now stale.
        self._ort_infer_dirty = True
        return True

    def _ort_student_raw_forward(self, blob):  # pragma: no cover - needs ORT training
        """Raw student forward used only to obtain anchors for the match.

        Uses the plain CustomONNX session (frozen at the latest exported weights),
        which is an acceptable approximation because the assignment is discrete
        and non-differentiable anyway.
        """
        try:
            session = self._student_model.onnx_session
            input_name = session.get_inputs()[0].name
            outputs = session.run(None, {input_name: blob})
            return outputs[0]
        except Exception as exc:
            logger.debug(f"[StudentTrainer] raw forward for match failed: {exc}")
            return None

    def _decode_pred_boxes(self, raw_out):  # pragma: no cover - needs ORT training
        """Decode raw student output to xyxy boxes in input space (NumPy).

        Mirrors the in-graph decode used by the training graph (without NMS), so
        the matcher sees the same anchor boxes the graph will score.
        """
        out = np.squeeze(np.asarray(raw_out))
        if out.ndim != 2:
            return None
        if self.output_format == "nanodet":
            return self._decode_pred_boxes_nanodet(out)
        if self.output_format == "yolox":
            if out.shape[1] != self.num_classes + 5 and out.shape[0] == self.num_classes + 5:
                out = out.T
            cxcywh = out[:, :4]
        else:  # yolo11
            expected = self.num_classes + 4
            if out.shape[0] == expected and out.shape[1] != expected:
                out = out.T
            cxcywh = out[:, :4]
        cx, cy, w, h = cxcywh[:, 0], cxcywh[:, 1], cxcywh[:, 2], cxcywh[:, 3]
        return np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)

    def _decode_pred_boxes_nanodet(self, out):  # pragma: no cover - needs ORT training
        """NumPy NanoDet GFL/DFL decode → ``[A,4]`` xyxy anchor boxes (input space).

        Used only to obtain candidate anchors for the (non-differentiable) match;
        mirrors the in-graph decode in ``build_student_loss_graph``.
        """
        a = out.shape[0]
        reg_channels = out.shape[1] - self.num_classes
        if reg_channels <= 0 or reg_channels % 4 != 0:
            return None
        reg_bins = reg_channels // 4
        # Standard mono-output NanoDet is classes-first.
        reg_flat = out[:, self.num_classes:]
        reg = reg_flat.reshape(a, 4, reg_bins)
        reg = reg - reg.max(axis=2, keepdims=True)
        sm = np.exp(reg)
        sm /= sm.sum(axis=2, keepdims=True)
        proj = np.arange(reg_bins, dtype=np.float32)
        distances = (sm * proj).sum(axis=2)  # [A,4]
        centers, strides = ort_art.nanodet_anchor_grid(
            self.input_width, self.input_height, a)
        if centers.shape[0] != a:
            return None
        cx = centers[:, 0]
        cy = centers[:, 1]
        st = strides[:, 0]
        x1 = cx - distances[:, 0] * st
        y1 = cy - distances[:, 1] * st
        x2 = cx + distances[:, 2] * st
        y2 = cy + distances[:, 3] * st
        return np.stack([x1, y1, x2, y2], axis=1).astype(np.float32)

    @staticmethod
    def _extract_scalar(outputs):  # pragma: no cover - needs ORT training
        """Pull a scalar loss value out of an ORT ``train_step`` result."""
        if outputs is None:
            return None
        val = outputs[0] if isinstance(outputs, (list, tuple)) else outputs
        try:
            return float(np.asarray(val).reshape(-1)[0])
        except Exception:
            return None

    def reset(self):
        """Reset the student model to its original weights."""
        # Restore original bytes to model path and reload
        try:
            with open(self.model_path, 'wb') as f:
                f.write(self._original_model_bytes)
            self._student_model = CustomONNX(
                model_path=self.model_path,
                input_width=self.input_width,
                input_height=self.input_height,
                output_format=self.output_format,
                num_classes=self.num_classes,
                providers=self.providers,
            )
            logger.info("[StudentTrainer] Model reset to original weights.")
        except Exception as exc:
            logger.error(f"[StudentTrainer] Reset failed: {exc}", exc_info=True)

        # Reset stats
        self.frames_processed = 0
        self.total_score = 0.0
        self.current_score = 0.0
        self.best_score = 0.0
        self.current_loss = float('inf')
        self.best_loss = float('inf')
        self.initial_loss = None
        self.last_train_loss = None
        # Restore the correction head to the identity (no learned correction).
        self._adapter.reset()
        # Restore the trained PyTorch network weights to their original state.
        if self._torch is not None:
            try:
                self._torch.reset()
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"[StudentTrainer] torch reset failed: {exc}")
        # Rebuild the ORT-training session from the pristine model so the trained
        # weights are discarded along with the inference session above.
        if self._ort_training_session is not None:
            self._ort_training_session = None
            self._ort_module = None
            self._ort_optimizer = None
            self._ort_checkpoint = None
            self._ort_infer_dirty = False
            try:
                self._setup_ort_training()
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"[StudentTrainer] ORT reset failed: {exc}")

    def export_onnx(self, output_path: str) -> str:
        """Export the current student model to an ONNX file.

        Parameters
        ----------
        output_path : str
            Destination path for the exported ONNX file.

        Returns
        -------
        str : The path where the model was saved.
        """
        # With the PyTorch backprop path the trained weights live in the torch
        # module, so export them (re-serialise to ONNX) to capture the learning.
        if self._torch_backprop and self._torch is not None:
            try:
                self._torch.export_onnx(output_path)
                logger.info(
                    f"[StudentTrainer] Exported trained PyTorch student to: {output_path}"
                )
                return output_path
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    f"[StudentTrainer] torch ONNX export failed ({exc}); "
                    "falling back to the original model bytes."
                )
        # With the ORT-training path the trained weights live in the ORT module;
        # export a detection model (loss subgraph pruned) carrying them.
        if self._ort_training_session is not None:
            try:
                self._ort_module.export_model_for_inferencing(
                    output_path, [self._ort_student_out]
                )
                logger.info(
                    f"[StudentTrainer] Exported trained ORT student to: {output_path}"
                )
                return output_path
            except Exception as exc:  # pragma: no cover - depends on ORT training
                logger.warning(
                    f"[StudentTrainer] ORT ONNX export failed ({exc}); "
                    "falling back to the original model bytes."
                )
        import shutil
        shutil.copy2(self.model_path, output_path)
        logger.info(f"[StudentTrainer] Exported student model to: {output_path}")
        return output_path

    def get_stats(self) -> Dict:
        """Get training statistics.

        Keys
        ----
        current_score / avg_score / best_score : distillation *score* in [0, 1]
            (higher = student agrees more with the teacher).
        current_loss / best_loss : requested set-based distillation *loss*
            (lower = student closer to the teacher). ``inf`` until the first frame.
        improvement / improvement_pct : loss reduction since the first frame
            (absolute and percentage; > 0 means the student got better).
        adapter_updates : number of correction-head gradient steps performed.
        network_updates : number of real network backprop steps performed.
        backprop_mode : active learning path ('pytorch-head'/'pytorch-all'/
            'ort-training'/'affine-head').
        train_loss : differentiable training loss of the last network backprop.
        training_active / training_available : training flags.
        """
        return {
            'frames_processed': self.frames_processed,
            'current_score': self.current_score,
            'avg_score': self.avg_score,
            'best_score': self.best_score,
            'current_loss': self.current_loss,
            'best_loss': self.best_loss,
            'improvement': self.improvement,
            'improvement_pct': self.improvement_pct,
            'adapter_updates': self._adapter.updates,
            'network_updates': self._network_update_count,
            'backprop_mode': self.backprop_mode,
            'train_loss': self.last_train_loss,
            'training_active': self.training_active,
            'training_available': self.is_training_available,
        }
