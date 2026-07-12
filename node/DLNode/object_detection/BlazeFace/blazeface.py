#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BlazeFace ONNX inference wrapper for CvStudio.

The bundled ``blaze.onnx`` model takes 4 inputs:
  - image          [1, 3, 128, 128] float32 – RGB normalised [0, 1]
  - conf_threshold [1]              float32 – minimum face confidence
  - max_detections [1]              int64   – cap on returned detections
  - iou_threshold  [1]              float32 – NMS IoU threshold

Output:
  - selectedBoxes  [1, N, 16] float32
      Each row: [cx, cy, w, h, kp0x, kp0y, …, kp5x, kp5y] (normalised [0, 1])
      N is the number of detections that survived NMS.

The wrapper satisfies the ``__call__(image) -> (bboxes, scores, class_ids)``
interface expected by ``node_object_detection.py``.  All returned faces are
assigned class_id = 0.

Note on scores
--------------
The ``blaze.onnx`` model's single output tensor (``selectedBoxes``) contains
only box coordinates and facial keypoints – the per-detection confidence scores
are consumed internally by the ONNX NMS operator and are **not** included in
the output.  To preserve interface compatibility, all returned detections are
assigned ``score = conf_threshold``, which is the lower-bound confidence
already guaranteed by the model's built-in NMS.

Dynamic threshold support
--------------------------
The ``conf_threshold`` attribute is **mutable**: downstream code can set
``model.conf_threshold = new_value`` before each ``__call__`` to change the
confidence cut-off without re-loading the model.  ``node_object_detection``
does this automatically when it detects that the model supports the attribute.
"""

import logging
import os

import cv2
import numpy as np

from node.DLNode.object_detection.onnx_session_utils import make_session

os.environ["ORT_CUDA_USE_CUDNN"] = "0"

logger = logging.getLogger(__name__)

# Model input resolution (fixed by the ONNX graph)
_INPUT_W = 128
_INPUT_H = 128


class BlazeFace:
    """BlazeFace face-detection wrapper compatible with the CvStudio detection interface."""

    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.3,
        iou_threshold: float = 0.3,
        max_detections: int = 100,
        providers=None,
    ):
        if providers is None:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.max_detections = max_detections

        logger.info(
            f"[BlazeFace] Loading model: {model_path} | "
            f"conf_threshold={conf_threshold}, iou_threshold={iou_threshold}, "
            f"max_detections={max_detections}, providers={providers}"
        )

        self.onnx_session = make_session(model_path, providers)

        # Resolve input / output names from the session
        inputs = self.onnx_session.get_inputs()
        self._input_image_name = inputs[0].name        # "image"
        self._input_conf_name = inputs[1].name         # "conf_threshold"
        self._input_max_det_name = inputs[2].name      # "max_detections"
        self._input_iou_name = inputs[3].name          # "iou_threshold"
        self._output_name = self.onnx_session.get_outputs()[0].name  # "selectedBoxes"

        logger.info("[BlazeFace] Ready.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __call__(self, image: np.ndarray):
        """Run BlazeFace inference on a BGR image.

        Parameters
        ----------
        image : np.ndarray
            Input BGR image (H, W, 3).

        Returns
        -------
        bboxes    : np.ndarray  (N, 4)  – [[x1, y1, x2, y2], …] in pixel coords
        scores    : np.ndarray  (N,)    – confidence scores
        class_ids : np.ndarray  (N,)    – all zeros (single class: "face")
        """
        orig_h, orig_w = image.shape[:2]
        blob = self._preprocess(image)

        try:
            outputs = self.onnx_session.run(
                None,
                {
                    self._input_image_name: blob,
                    self._input_conf_name: np.array(
                        [self.conf_threshold], dtype=np.float32
                    ),
                    self._input_max_det_name: np.array(
                        [self.max_detections], dtype=np.int64
                    ),
                    self._input_iou_name: np.array(
                        [self.iou_threshold], dtype=np.float32
                    ),
                },
            )
        except Exception as exc:
            logger.error(f"[BlazeFace] Inference error: {exc}")
            return (
                np.empty((0, 4), dtype=np.float32),
                np.empty((0,), dtype=np.float32),
                np.empty((0,), dtype=np.int64),
            )

        # selectedBoxes: (1, N, 16)  or  (1, 0, 16) when no detection
        selected = outputs[0]  # shape (1, N, 16)
        n_det = selected.shape[1]

        if n_det == 0:
            return (
                np.empty((0, 4), dtype=np.float32),
                np.empty((0,), dtype=np.float32),
                np.empty((0,), dtype=np.int64),
            )

        rows = selected[0]  # (N, 16)

        bboxes = self._decode_boxes(rows, orig_w, orig_h)
        scores = np.full(n_det, self.conf_threshold, dtype=np.float32)
        class_ids = np.zeros(n_det, dtype=np.int64)

        return bboxes, scores, class_ids

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Resize and normalise the image for BlazeFace.

        Returns
        -------
        np.ndarray  shape (1, 3, 128, 128)  float32  values in [0, 1]
        """
        resized = cv2.resize(image, (_INPUT_W, _INPUT_H), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        norm = rgb.astype(np.float32) / 255.0
        chw = np.transpose(norm, (2, 0, 1))   # HWC → CHW
        blob = np.expand_dims(chw, axis=0)     # CHW → BCHW
        return blob

    def _decode_boxes(
        self, rows: np.ndarray, orig_w: int, orig_h: int
    ) -> np.ndarray:
        """Convert normalised [cx, cy, w, h] to pixel-space [x1, y1, x2, y2].

        Parameters
        ----------
        rows : np.ndarray  (N, 16)
        orig_w, orig_h : int  – original image dimensions

        Returns
        -------
        np.ndarray  (N, 4)  float32  [[x1, y1, x2, y2], …]
        """
        cx = rows[:, 0]
        cy = rows[:, 1]
        w = rows[:, 2]
        h = rows[:, 3]

        x1 = (cx - w / 2.0) * orig_w
        y1 = (cy - h / 2.0) * orig_h
        x2 = (cx + w / 2.0) * orig_w
        y2 = (cy + h / 2.0) * orig_h

        # Clip to image bounds
        x1 = np.clip(x1, 0, orig_w)
        y1 = np.clip(y1, 0, orig_h)
        x2 = np.clip(x2, 0, orig_w)
        y2 = np.clip(y2, 0, orig_h)

        return np.stack([x1, y1, x2, y2], axis=1).astype(np.float32)
