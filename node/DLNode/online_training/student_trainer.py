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
)
from node.DLNode.online_training.distillation_loss_ort import (
    compute_distillation_loss_numpy,
    build_distillation_loss_graph,
    _ONNX_AVAILABLE,
)

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
        Output format ('yolo11' or 'yolox').
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
        if is_torch_backprop_available():
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


        # Training state
        self._ort_training_session = None
        self._training_available = _ORT_TRAINING_AVAILABLE

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
        torch weights (so improvements are observable), decoded with exactly the
        same post-processing/NMS as the rest of the application. Otherwise the
        plain onnxruntime session is used.

        Returns (bboxes, scores, class_ids).
        """
        if self._torch_backprop and self._torch is not None:
            try:
                return self._torch_infer(frame)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"[StudentTrainer] torch inference failed: {exc}")
        return self._student_model(frame)

    def _torch_infer(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Inference through the trained torch weights, reusing CustomONNX decode."""
        orig_h, orig_w = self._frame_size(frame)
        blob, ratio = self._student_model._preprocess(frame)
        raw = self._torch.forward_numpy(blob)
        if self.output_format == "yolox":
            return self._student_model._postprocess_yolox(raw, orig_w, orig_h, ratio)
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

        # 1b. When training only the affine correction head (no PyTorch path),
        # apply it so the returned predictions reflect what the head has learned
        # so far. With the PyTorch backprop path the network weights themselves
        # are updated, so ``infer`` already returns the improved predictions and
        # no extra correction is applied.
        frame_h, frame_w = self._frame_size(frame)
        if not self._torch_backprop and len(s_bboxes) > 0:
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
            else:
                # Fallback: sub-gradient descent on the affine correction head.
                training_performed = self._adapt_step(
                    frame_w, frame_h,
                    teacher_bboxes, teacher_class_ids,
                    s_bboxes, s_class_ids,
                )
                # Optional: full-network backprop when onnxruntime-training is wired.
                if self._training_available and self._ort_training_session is not None:
                    self._do_backprop(
                        frame, teacher_bboxes, teacher_scores, teacher_class_ids,
                        distillation,
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
                               teacher_class_ids):  # pragma: no cover
        """Run one onnxruntime-training optimizer step (when wired).

        Placeholder for the ORT Training optimizer step. Returns False until an
        end-to-end differentiable training session is attached.
        """
        return False

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
            'network_updates': self._torch.updates if self._torch is not None else 0,
            'backprop_mode': self.backprop_mode,
            'train_loss': self.last_train_loss,
            'training_active': self.training_active,
            'training_available': self.is_training_available,
        }
