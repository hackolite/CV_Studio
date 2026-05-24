#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generic ONNX wrapper for custom pose estimation models.

Returns an empty keypoints list so that the existing
draw_pose_estimation_info() call simply passes through without crashing.
"""

import logging

import cv2
import numpy as np

from node.DLNode.object_detection.onnx_session_utils import make_session

logger = logging.getLogger(__name__)


class CustomONNX:
    """Generic ONNX pose-estimation wrapper.

    Compatible with the ``__call__(image) -> results_list`` interface
    expected by ``node_pose_estimation.py``.
    """

    def __init__(self, model_path: str, input_width: int = 192,
                 input_height: int = 192, providers=None):
        if providers is None:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        self.input_width = input_width
        self.input_height = input_height
        self.onnx_session = make_session(model_path, providers=providers)
        self.input_name = self.onnx_session.get_inputs()[0].name
        logger.info(f"[CustomONNX:PoseEstimation] Loaded model: {model_path}")

    def __call__(self, image: np.ndarray):
        """Run inference and return an empty keypoints list."""
        try:
            inp = cv2.resize(image, (self.input_width, self.input_height))
            inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB)
            inp = inp.transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
            self.onnx_session.run(None, {self.input_name: inp})
        except Exception as exc:
            logger.warning(f"[CustomONNX:PoseEstimation] Inference error: {exc}")
        return []
