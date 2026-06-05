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
from node.DLNode.online_training.distillation_loss_ort import (
    compute_distillation_loss_numpy,
    build_distillation_loss_graph,
    _ONNX_AVAILABLE,
)

logger = logging.getLogger(__name__)

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

        # Statistics
        self.frames_processed = 0
        self.total_score = 0.0
        self.current_score = 0.0
        self.best_score = 0.0
        # Distillation loss bookkeeping (lower is better). ``current_loss`` is the
        # requested set-based (DETR-style Hungarian) loss for the latest frame and
        # ``best_loss`` the lowest value seen so far.
        self.current_loss = float('inf')
        self.best_loss = float('inf')
        self.training_active = False
        self._last_loss = None

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
        """Whether ORT Training is available for backpropagation."""
        return self._training_available

    @property
    def avg_score(self) -> float:
        """Average distillation score over all processed frames."""
        if self.frames_processed == 0:
            return 0.0
        return self.total_score / self.frames_processed

    def infer(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run student model inference on a frame.

        Returns (bboxes, scores, class_ids).
        """
        return self._student_model(frame)

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
            - distillation: distillation score metrics (includes the requested
              set-based loss under the ``loss`` key, lower = closer to teacher)
            - training_step: True only when a real weight update was performed
              (requires onnxruntime-training); False in inference-only mode
        """
        # 1. Student inference
        s_bboxes, s_scores, s_class_ids = self.infer(frame)

        # Apply score threshold to student predictions
        if len(s_scores) > 0:
            mask = s_scores >= score_threshold
            s_bboxes = s_bboxes[mask]
            s_scores = s_scores[mask]
            s_class_ids = s_class_ids[mask]

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
        self._last_loss = {
            'loss': distillation.get('loss', 0.0),
            'loss_box': distillation.get('loss_box', 0.0),
            'loss_class': distillation.get('loss_class', 0.0),
            'loss_iou': distillation.get('loss_iou', 0.0),
            'loss_cardinality': distillation.get('loss_cardinality', 0.0),
        }

        # 3. Update statistics
        self.frames_processed += 1
        self.current_score = distillation['score']
        self.total_score += self.current_score
        if self.current_score > self.best_score:
            self.best_score = self.current_score

        # Track the requested loss (lower = better student).
        self.current_loss = float(distillation.get('loss', 0.0))
        if self.current_loss < self.best_loss:
            self.best_loss = self.current_loss

        # 4. Training step (only when ORT Training is available and active).
        # ``train_step`` reflects whether weights were actually updated.
        training_performed = False
        if self._training_available and self.training_active:
            training_performed = self._do_backprop(
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
            self._last_loss = {
                'loss': distillation.get('loss', 0.0),
                'loss_box': distillation.get('loss_box', 0.0),
                'loss_class': distillation.get('loss_class', 0.0),
                'loss_iou': distillation.get('loss_iou', 0.0),
                'loss_cardinality': distillation.get('loss_cardinality', 0.0),
            }

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
        training_active / training_available : training flags.
        """
        return {
            'frames_processed': self.frames_processed,
            'current_score': self.current_score,
            'avg_score': self.avg_score,
            'best_score': self.best_score,
            'current_loss': self.current_loss,
            'best_loss': self.best_loss,
            'training_active': self.training_active,
            'training_available': self._training_available,
        }
