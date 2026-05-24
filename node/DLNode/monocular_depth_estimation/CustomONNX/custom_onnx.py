#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generic ONNX wrapper for custom monocular depth estimation models.

Assumes the model outputs a depth map (single channel), normalises it to
0-255 uint8, and resizes it to match the input frame dimensions, as
expected by ``node_monocular_depth_estimation.py``.
"""

import logging

import cv2
import numpy as np

from node.DLNode.object_detection.onnx_session_utils import make_session

logger = logging.getLogger(__name__)


class CustomONNX:
    """Generic ONNX depth-estimation wrapper.

    Compatible with the ``__call__(image) -> depth_map`` interface expected
    by ``node_monocular_depth_estimation.py`` (depth_map is a uint8 grayscale
    numpy array with the same spatial dimensions as the input image).
    """

    def __init__(self, model_path: str, input_width: int = 320,
                 input_height: int = 192, providers=None):
        if providers is None:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        self.input_width = input_width
        self.input_height = input_height
        self.onnx_session = make_session(model_path, providers=providers)
        self.input_name = self.onnx_session.get_inputs()[0].name
        logger.info(f"[CustomONNX:DepthEstimation] Loaded model: {model_path}")

    def __call__(self, image: np.ndarray) -> np.ndarray:
        """Run inference and return a grayscale depth map."""
        h, w = image.shape[:2]
        try:
            inp = cv2.resize(image, (self.input_width, self.input_height))
            inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB)
            inp = inp.transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
            output = self.onnx_session.run(None, {self.input_name: inp})[0]
            # Squeeze batch / channel dims to 2-D
            depth = np.squeeze(output)
            if depth.ndim == 3:
                # [C, H, W] or [H, W, C] — take first or only channel
                depth = depth[0] if depth.shape[0] <= depth.shape[-1] else depth[..., 0]
            # Normalise to 0-255
            d_min, d_max = float(depth.min()), float(depth.max())
            if d_max > d_min:
                depth = ((depth - d_min) / (d_max - d_min) * 255.0).astype(np.uint8)
            else:
                depth = np.zeros_like(depth, dtype=np.uint8)
            depth = cv2.resize(depth, (w, h))
            return depth
        except Exception as exc:
            logger.warning(f"[CustomONNX:DepthEstimation] Inference error: {exc}")
            return np.zeros((h, w), dtype=np.uint8)
