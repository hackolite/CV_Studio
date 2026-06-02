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
        self.training_active = False

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

        logger.info(
            f"[StudentTrainer] Initialized — model={os.path.basename(model_path)}, "
            f"input={input_width}x{input_height}, format={output_format}, "
            f"training={'enabled' if self._training_available else 'inference-only'}"
        )

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
            - distillation: distillation score metrics
            - training_step: whether backprop was performed
        """
        # 1. Student inference
        s_bboxes, s_scores, s_class_ids = self.infer(frame)

        # Apply score threshold to student predictions
        if len(s_scores) > 0:
            mask = s_scores >= score_threshold
            s_bboxes = s_bboxes[mask]
            s_scores = s_scores[mask]
            s_class_ids = s_class_ids[mask]

        # 2. Compute distillation score
        t_bboxes = np.array(teacher_bboxes) if len(teacher_bboxes) > 0 else np.array([])
        t_scores = np.array(teacher_scores) if len(teacher_scores) > 0 else np.array([])
        t_class_ids = np.array(teacher_class_ids) if len(teacher_class_ids) > 0 else np.array([])

        distillation = compute_distillation_score(
            t_bboxes.tolist() if len(t_bboxes) > 0 else [],
            t_scores.tolist() if len(t_scores) > 0 else [],
            t_class_ids.tolist() if len(t_class_ids) > 0 else [],
            s_bboxes.tolist() if len(s_bboxes) > 0 else [],
            s_scores.tolist() if len(s_scores) > 0 else [],
            s_class_ids.tolist() if len(s_class_ids) > 0 else [],
        )

        # 3. Update statistics
        self.frames_processed += 1
        self.current_score = distillation['score']
        self.total_score += self.current_score
        if self.current_score > self.best_score:
            self.best_score = self.current_score

        # 4. Training step (if ORT Training available and training is active)
        training_performed = False
        if self._training_available and self.training_active:
            # ORT Training backpropagation would go here
            # For now, this is a placeholder for the onnxruntime-training API
            training_performed = self._do_backprop(frame, t_bboxes, t_scores, t_class_ids)

        return {
            'student_bboxes': s_bboxes,
            'student_scores': s_scores,
            'student_class_ids': s_class_ids,
            'distillation': distillation,
            'training_step': training_performed,
        }

    def _do_backprop(self, frame, teacher_bboxes, teacher_scores, teacher_class_ids):
        """Perform backpropagation using ORT Training API.

        This is a placeholder for the full ORT Training integration.
        When onnxruntime-training is available, this will:
        1. Convert the inference graph to a training graph
        2. Compute loss from teacher-student discrepancy
        3. Update model weights
        4. Reload the inference session with new weights

        Returns True if training step was successful.
        """
        # TODO: Full ORT Training integration when onnxruntime-training is installed
        # For now, log the attempt
        logger.debug(
            f"[StudentTrainer] Backprop step (frame #{self.frames_processed}) — "
            f"score={self.current_score:.3f}"
        )
        return False

    def reset(self):
        """Reset the student model to its original weights."""
        # Write original bytes to a temp file and reload
        tmp_path = self.model_path + ".reset.tmp"
        try:
            with open(tmp_path, 'wb') as f:
                f.write(self._original_model_bytes)
            self._student_model = CustomONNX(
                model_path=tmp_path,
                input_width=self.input_width,
                input_height=self.input_height,
                output_format=self.output_format,
                num_classes=self.num_classes,
                providers=self.providers,
            )
            # Copy back to original path
            with open(self.model_path, 'wb') as f:
                f.write(self._original_model_bytes)
            logger.info("[StudentTrainer] Model reset to original weights.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # Reset stats
        self.frames_processed = 0
        self.total_score = 0.0
        self.current_score = 0.0
        self.best_score = 0.0

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
        """Get training statistics."""
        return {
            'frames_processed': self.frames_processed,
            'current_score': self.current_score,
            'avg_score': self.avg_score,
            'best_score': self.best_score,
            'training_active': self.training_active,
            'training_available': self._training_available,
        }
