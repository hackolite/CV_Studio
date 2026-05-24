#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generic ONNX wrapper for custom semantic segmentation models.

Assumes the model outputs either [1, num_classes, H, W] logits (argmax applied)
or [1, H, W] class-ID maps.  The result is resized to the input frame dimensions
as expected by ``node_semantic_segmentation.py``.
"""

import logging

import cv2
import numpy as np

from node.DLNode.object_detection.onnx_session_utils import make_session

logger = logging.getLogger(__name__)


class CustomONNX:
    """Generic ONNX semantic-segmentation wrapper.

    Compatible with the ``get_class_num()`` and ``__call__(image) ->
    segmentation_map`` interface expected by ``node_semantic_segmentation.py``.
    """

    def __init__(self, model_path: str, input_width: int = 512,
                 input_height: int = 512, num_classes: int = 2, providers=None):
        if providers is None:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        self.input_width = input_width
        self.input_height = input_height
        self.num_classes = num_classes
        self.onnx_session = make_session(model_path, providers=providers)
        self.input_name = self.onnx_session.get_inputs()[0].name
        logger.info(f"[CustomONNX:SemanticSegmentation] Loaded model: {model_path}")

    def get_class_num(self) -> int:
        return self.num_classes

    def __call__(self, image: np.ndarray) -> np.ndarray:
        """Run inference and return a 2-D uint8 segmentation map."""
        h, w = image.shape[:2]
        try:
            inp = cv2.resize(image, (self.input_width, self.input_height))
            inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB)
            inp = inp.transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
            output = self.onnx_session.run(None, {self.input_name: inp})[0]
            # output: [1, num_classes, H, W]  or  [1, 1, H, W]  or  [1, H, W]
            seg = np.squeeze(output)
            if seg.ndim == 3:
                # [num_classes, H, W] — argmax over class axis
                seg = np.argmax(seg, axis=0).astype(np.uint8)
            else:
                seg = seg.astype(np.uint8)
            seg = cv2.resize(seg, (w, h), interpolation=cv2.INTER_NEAREST)
            return seg
        except Exception as exc:
            logger.warning(f"[CustomONNX:SemanticSegmentation] Inference error: {exc}")
            return np.zeros((h, w), dtype=np.uint8)
