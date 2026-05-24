#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generic ONNX wrapper for custom image classification models.

Assumes the model outputs a 1-D (or 2-D [1, N]) array of logits/probabilities,
then returns the top-5 (scores, class_ids) arrays expected by
``node_classification.py``.
"""

import logging

import cv2
import numpy as np

from node.DLNode.object_detection.onnx_session_utils import make_session

logger = logging.getLogger(__name__)


class CustomONNX:
    """Generic ONNX classification wrapper.

    Compatible with the ``__call__(image) -> (class_scores, class_ids)``
    interface expected by ``node_classification.py``.
    """

    def __init__(self, model_path: str, input_width: int = 224,
                 input_height: int = 224, providers=None):
        if providers is None:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        self.input_width = input_width
        self.input_height = input_height
        self.onnx_session = make_session(model_path, providers=providers)
        self.input_name = self.onnx_session.get_inputs()[0].name
        logger.info(f"[CustomONNX:Classification] Loaded model: {model_path}")

    def __call__(self, image: np.ndarray):
        """Run inference and return (class_scores, class_ids) top-5 arrays."""
        try:
            inp = cv2.resize(image, (self.input_width, self.input_height))
            inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB)
            inp = inp.transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
            output = self.onnx_session.run(None, {self.input_name: inp})[0]
            scores = output.flatten()
            # Apply softmax
            scores = scores - scores.max()
            scores = np.exp(scores)
            scores = scores / scores.sum()
            # Return top-5
            top_k = min(5, len(scores))
            top_ids = np.argsort(scores)[::-1][:top_k]
            top_scores = scores[top_ids]
            return top_scores, top_ids
        except Exception as exc:
            logger.warning(f"[CustomONNX:Classification] Inference error: {exc}")
            return np.array([0.0]), np.array([0])
