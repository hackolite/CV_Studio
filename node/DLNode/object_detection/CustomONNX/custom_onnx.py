#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic ONNX wrapper for CvStudio object detection.

Supports two common YOLO output formats:
  - yolo11  (Ultralytics YOLO v8/v11): output shape [1, num_classes+4, num_anchors]
  - yolox   (YOLOX):                   output shape [1, num_anchors, num_classes+5]

The wrapper is initialised from the metadata returned by
``onnx_inspector.inspect_onnx_model()``.
"""

import copy
import logging
import math
import os

import cv2
import numpy as np
import onnxruntime

from node.DLNode.object_detection.onnx_session_utils import make_session

# Disable cuDNN for safer operation (mirrors other YOLO wrappers in this project)
os.environ["ORT_CUDA_USE_CUDNN"] = "0"

logger = logging.getLogger(__name__)
class CustomONNX:
    """Generic ONNX object-detection wrapper.

    Compatible with the ``__call__(image) -> (bboxes, scores, class_ids)``
    interface expected by ``node_object_detection.py``.
    """

    def __init__(
        self,
        model_path: str,
        input_name: str = None,
        input_width: int = 640,
        input_height: int = 640,
        output_format: str = "yolo11",
        num_classes: int = 80,
        class_score_th: float = 0.0,
        nms_th: float = 0.45,
        nms_score_th: float = 0.1,
        providers=None,
        disable_optimizations: bool = False,
        nanodet_reg_first: bool = None,
    ):
        if providers is None:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        self.input_width = input_width
        self.input_height = input_height
        self.output_format = output_format
        self.num_classes = num_classes
        self.class_score_th = class_score_th
        self.nms_th = nms_th
        self.nms_score_th = nms_score_th

        logger.info(
            f"[CustomONNX] Loading model: {model_path} | "
            f"format='{output_format}', input={input_width}x{input_height}, "
            f"num_classes={num_classes}, providers={providers}"
        )

        self.onnx_session = make_session(
            model_path, providers, disable_optimizations=disable_optimizations
        )

        # Use provided input name, fall back to first input name from model
        if input_name:
            self.input_name = input_name
        else:
            self.input_name = self.onnx_session.get_inputs()[0].name

        self.output_name = self.onnx_session.get_outputs()[0].name

        # Validate that the actual session input shape matches expected dimensions
        actual_input = self.onnx_session.get_inputs()[0]
        actual_shape = list(actual_input.shape)
        if len(actual_shape) == 4:
            actual_h = actual_shape[2]
            actual_w = actual_shape[3]
            if isinstance(actual_h, int) and actual_h > 0 and actual_h != input_height:
                logger.warning(
                    f"[CustomONNX] Height mismatch: model expects {actual_h}px "
                    f"but wrapper was initialised with input_height={input_height}. "
                    f"Updating to {actual_h}."
                )
                self.input_height = actual_h
            if isinstance(actual_w, int) and actual_w > 0 and actual_w != input_width:
                logger.warning(
                    f"[CustomONNX] Width mismatch: model expects {actual_w}px "
                    f"but wrapper was initialised with input_width={input_width}. "
                    f"Updating to {actual_w}."
                )
                self.input_width = actual_w

        # Channel layout for NanoDet post-processing.
        # None = auto-detect on first inference (heuristic).
        # True/False = caller-supplied override (avoids heuristic failures on
        # QDQ models whose quantised class logits mimic DFL regression statistics).
        self._nanodet_reg_first = nanodet_reg_first

        logger.info(
            f"[CustomONNX] Ready — input_name='{self.input_name}', "
            f"output_name='{self.output_name}', "
            f"effective input size: {self.input_width}x{self.input_height}"
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __call__(self, image):
        """Run inference on a BGR image.

        Returns
        -------
        bboxes   : np.ndarray shape (N, 4)  – [[x1,y1,x2,y2], ...]
        scores   : np.ndarray shape (N,)
        class_ids: np.ndarray shape (N,)
        """
        orig_h, orig_w = image.shape[:2]
        logger.debug(
            f"[CustomONNX] Inference request — image size: {orig_w}x{orig_h} (WxH), "
            f"model input: {self.input_width}x{self.input_height}, "
            f"format: {self.output_format}"
        )
        blob, ratio = self._preprocess(image)
        logger.debug(
            f"[CustomONNX] Preprocessed blob shape: {blob.shape}, "
            f"letterbox ratio: {ratio:.4f}"
        )
        try:
            outputs = self.onnx_session.run(None, {self.input_name: blob})
        except (
            onnxruntime.capi.onnxruntime_pybind11_state.InvalidArgument,
            onnxruntime.capi.onnxruntime_pybind11_state.Fail,
            onnxruntime.capi.onnxruntime_pybind11_state.RuntimeException,
        ) as exc:
            # Models with built-in NMS/post-processing (e.g. nanodet_qdq) may
            # raise when there are zero detections (Gather into an empty
            # tensor).  Return empty results rather than crashing the pipeline.
            if "indices element out of data bounds" in str(exc):
                logger.debug(
                    "[CustomONNX] Model returned zero detections "
                    "(Gather into empty tensor) — returning empty results."
                )
                return (
                    np.empty((0, 4), dtype=np.float32),
                    np.empty((0,), dtype=np.float32),
                    np.empty((0,), dtype=np.int64),
                )
            raise

        if self.output_format == "ssd":
            bboxes, scores, class_ids = self._postprocess_ssd(
                outputs, orig_w, orig_h
            )
        elif self.output_format == "nanodet_multi":
            bboxes, scores, class_ids = self._postprocess_nanodet_multi(
                outputs, orig_w, orig_h
            )
        else:
            raw_output = outputs[0]
            logger.debug(f"[CustomONNX] Raw output shape: {raw_output.shape}")

            if self.output_format == "nanodet":
                bboxes, scores, class_ids = self._postprocess_nanodet(
                    raw_output, orig_w, orig_h
                )
            elif self.output_format == "yolox":
                bboxes, scores, class_ids = self._postprocess_yolox(
                    raw_output, orig_w, orig_h, ratio
                )
            else:
                # Default: yolo11 / ultralytics
                bboxes, scores, class_ids = self._postprocess_yolo11(
                    raw_output, orig_w, orig_h
                )

        logger.debug(f"[CustomONNX] Detections after NMS: {len(bboxes)}")
        return bboxes, scores, class_ids

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------

    def _preprocess(self, image):
        """Preprocess image for inference.

        Returns
        -------
        blob  : np.ndarray  BCHW float32 blob ready for ONNX session
        ratio : float       letterbox scale ratio (1.0 for non-letterbox formats)

        Format-specific behaviour
        --------------------------
        yolox   — letterbox padding (value=114) preserving aspect ratio, raw
                  pixel values in [0, 255]. ``ratio`` is the scale factor used
                  to map model-space coordinates back to original image space.
        yolo11  — simple stretch resize, normalised to [0, 1]. ``ratio`` is
                  always 1.0 (coordinate mapping uses scale_x/scale_y instead).
        nanodet — letterbox padding preserving aspect ratio, normalised with
                  ImageNet mean/std.
        """
        if self.output_format == "yolox":
            return self._preprocess_yolox(image)
        elif self.output_format == "ssd":
            return self._preprocess_ssd(image)
        elif self.output_format in ("nanodet", "nanodet_multi"):
            return self._preprocess_nanodet(image)
        return self._preprocess_yolo11(image)

    def _preprocess_yolox(self, image):
        """Letterbox preprocessing for YOLOX / FreeYOLO models.

        YOLOX was trained with:
          - Letterbox padding (value=114) maintaining aspect ratio.
          - Raw pixel values in [0, 255] — **no** /255 normalisation.
          - BGR colour format (no colour space conversion needed).

        Returns (blob, ratio) where ratio = resized / original.
        """
        orig_h, orig_w = image.shape[:2]
        ratio = min(self.input_height / orig_h, self.input_width / orig_w)
        new_h = int(orig_h * ratio)
        new_w = int(orig_w * ratio)

        # Letterbox canvas filled with 114 — the neutral gray value used during
        # YOLOX training to pad images to the target resolution.
        padded = np.full(
            (self.input_height, self.input_width, 3), 114.0, dtype=np.float32
        )
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        padded[:new_h, :new_w] = resized.astype(np.float32)

        logger.debug(
            f"[CustomONNX/yolox preprocess] orig={orig_w}x{orig_h}, "
            f"resized={new_w}x{new_h}, ratio={ratio:.4f}, "
            f"input={self.input_width}x{self.input_height}"
        )

        blob = np.transpose(padded, (2, 0, 1))          # HWC → CHW
        blob = np.ascontiguousarray(blob, dtype=np.float32)
        blob = np.expand_dims(blob, axis=0)             # CHW → BCHW
        return blob, ratio

    def _preprocess_yolo11(self, image):
        """Simple stretch-resize preprocessing for YOLO11/YOLOv8 models.

        Returns (blob, 1.0).  Coordinate back-projection uses scale_x/scale_y
        instead of a letterbox ratio.
        """
        img = cv2.resize(
            image,
            (self.input_width, self.input_height),
            interpolation=cv2.INTER_LINEAR,
        )
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC → CHW
        img = np.expand_dims(img, axis=0)   # CHW → BCHW
        return img, 1.0

    def _preprocess_ssd(self, image):
        """Preprocessing for SSD models (e.g. SSD MobileNet V2).

        SSD models typically expect:
          - Input shape: [1, 3, H, W] (BCHW) with pixel values in [0, 1]
            or [1, H, W, 3] (BHWC) with uint8 values in [0, 255]
          - Simple stretch-resize to the model input size
          - RGB colour format

        This method produces a [1, 3, H, W] float32 normalised blob by default.
        The model's actual input shape is checked at session init and determines
        whether BCHW or BHWC layout is used.

        Returns (blob, 1.0).
        """
        img = cv2.resize(
            image,
            (self.input_width, self.input_height),
            interpolation=cv2.INTER_LINEAR,
        )
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Detect input layout from the ONNX session
        # Some SSD models use BHWC layout (batch, height, width, channels)
        # where dim[1] equals the input height. Others use BCHW (batch, channels, H, W).
        actual_shape = list(self.onnx_session.get_inputs()[0].shape)
        is_bhwc = (
            len(actual_shape) == 4
            and isinstance(actual_shape[1], int)
            and actual_shape[1] == self.input_height
            and isinstance(actual_shape[3], int)
            and actual_shape[3] == 3
        )
        if is_bhwc:
            # BHWC layout — keep as uint8 [0, 255]
            img = img.astype(np.uint8)
            blob = np.expand_dims(img, axis=0).astype(np.float32)
        else:
            # BCHW layout — normalise to [0, 1]
            img = img.astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))  # HWC → CHW
            blob = np.expand_dims(img, axis=0)   # CHW → BCHW

        return blob, 1.0

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    def _postprocess_yolo11(self, raw_output, orig_w, orig_h):
        """Post-process YOLO11/YOLOv8 Ultralytics output.

        Expected raw_output shape: (1, num_classes+4, num_anchors)
        """
        # Squeeze batch dimension: (num_classes+4, num_anchors)
        output = np.squeeze(raw_output)
        if output.ndim != 2:
            logger.warning(
                f"[CustomONNX] yolo11 post-process: unexpected output ndim={output.ndim} "
                f"after squeeze (raw shape={raw_output.shape}). Returning empty detections."
            )
            return np.array([]), np.array([]), np.array([])

        # output is (num_classes+4, num_anchors); check orientation
        # Use num_classes when known, otherwise fall back to dimension comparison.
        expected_channels = self.num_classes + 4 if self.num_classes > 0 else None
        needs_transpose = False
        if expected_channels is not None:
            if output.shape[0] != expected_channels and output.shape[1] == expected_channels:
                needs_transpose = True
                logger.warning(
                    f"[CustomONNX] yolo11 post-process: output shape {output.shape} does not "
                    f"match expected [C+4={expected_channels}, anchors]. Transposing."
                )
        elif output.shape[0] > output.shape[1]:
            # Heuristic: larger axis-0 suggests (anchors, C+4) orientation
            needs_transpose = True
            logger.warning(
                f"[CustomONNX] yolo11 post-process: shape after squeeze is "
                f"{output.shape} — axis-0 ({output.shape[0]}) > axis-1 ({output.shape[1]}). "
                f"Expected [C+4, anchors]. Transposing to correct orientation."
            )
        if needs_transpose:
            output = output.T

        # Transpose to (num_anchors, num_classes+4)
        output = output.T

        if output.shape[1] < 5:
            logger.warning(
                f"[CustomONNX] yolo11 post-process: too few columns ({output.shape[1]}) "
                f"after transpose — need at least 5 (4 box + 1 class). Returning empty."
            )
            return np.array([]), np.array([]), np.array([])

        boxes_xywh = output[:, :4]     # cx, cy, w, h (in input image pixels)
        class_scores = output[:, 4:]   # (num_anchors, num_classes)

        # Scale factors back to original image
        scale_x = orig_w / self.input_width
        scale_y = orig_h / self.input_height

        max_scores = class_scores.max(axis=1)
        class_ids_all = class_scores.argmax(axis=1)

        # Filter by threshold
        mask = max_scores >= self.nms_score_th
        if not mask.any():
            logger.debug("[CustomONNX] yolo11 post-process: no detections above score threshold.")
            return np.array([]), np.array([]), np.array([])

        boxes_xywh = boxes_xywh[mask]
        max_scores = max_scores[mask]
        class_ids_all = class_ids_all[mask]
        logger.debug(
            f"[CustomONNX] yolo11 post-process: {mask.sum()} candidates above threshold "
            f"(scale_x={scale_x:.4f}, scale_y={scale_y:.4f})"
        )

        # Convert cx,cy,w,h → x1,y1,x2,y2 scaled to original image
        cx, cy, bw, bh = (
            boxes_xywh[:, 0] * scale_x,
            boxes_xywh[:, 1] * scale_y,
            boxes_xywh[:, 2] * scale_x,
            boxes_xywh[:, 3] * scale_y,
        )
        x1 = (cx - bw / 2).astype(int)
        y1 = (cy - bh / 2).astype(int)
        x2 = (cx + bw / 2).astype(int)
        y2 = (cy + bh / 2).astype(int)

        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1).tolist()
        scores_list = max_scores.tolist()

        indices = cv2.dnn.NMSBoxes(
            boxes_xyxy, scores_list, self.nms_score_th, self.nms_th
        )

        if len(indices) == 0:
            logger.debug("[CustomONNX] yolo11 post-process: all candidates removed by NMS.")
            return np.array([]), np.array([]), np.array([])

        indices = np.array(indices).flatten()
        logger.debug(f"[CustomONNX] yolo11 post-process: {len(indices)} detections after NMS.")
        return (
            np.array(boxes_xyxy)[indices],
            np.array(scores_list)[indices],
            class_ids_all[indices],
        )

    def _postprocess_yolox(self, raw_output, orig_w, orig_h, ratio=1.0):
        """Post-process YOLOX output.

        Expected raw_output shape: (1, num_anchors, num_classes+5)
        The +5 columns are: cx, cy, w, h, objectness, class_scores...

        Parameters
        ----------
        ratio : float
            Letterbox ratio returned by ``_preprocess_yolox``.
            Coordinates in model-input space are divided by this ratio to
            recover original-image coordinates.
        """
        output = np.squeeze(raw_output)
        if output.ndim != 2:
            logger.warning(
                f"[CustomONNX] yolox post-process: unexpected output ndim={output.ndim} "
                f"after squeeze (raw shape={raw_output.shape}). Returning empty detections."
            )
            return np.array([]), np.array([]), np.array([])

        logger.debug(
            f"[CustomONNX] yolox post-process: output shape after squeeze = {output.shape}, "
            f"letterbox ratio={ratio:.4f}"
        )

        # output is (num_anchors, num_classes+5); check orientation
        # Use num_classes when known, otherwise fall back to dimension comparison.
        expected_channels = self.num_classes + 5 if self.num_classes > 0 else None
        needs_transpose = False
        if expected_channels is not None:
            if output.shape[1] != expected_channels and output.shape[0] == expected_channels:
                needs_transpose = True
                logger.warning(
                    f"[CustomONNX] yolox post-process: output shape {output.shape} does not "
                    f"match expected [anchors, C+5={expected_channels}]. Transposing."
                )
        elif output.shape[1] > output.shape[0]:
            # Heuristic: larger axis-1 suggests (C+5, anchors) orientation
            needs_transpose = True
            logger.warning(
                f"[CustomONNX] yolox post-process: shape after squeeze is "
                f"{output.shape} — axis-1 ({output.shape[1]}) > axis-0 ({output.shape[0]}). "
                f"Expected [anchors, C+5]. Transposing to correct orientation."
            )
        if needs_transpose:
            output = output.T

        if output.shape[1] < 6:
            logger.warning(
                f"[CustomONNX] yolox post-process: too few columns ({output.shape[1]}) "
                f"— need at least 6 (4 box + 1 obj + 1 class). Returning empty."
            )
            return np.array([]), np.array([]), np.array([])

        # Apply YOLOX grid decoding.
        # The ONNX models store raw (undecoded) predictions:
        #   - columns 0-1: offset within the grid cell  (range ~ -2 to 4)
        #   - columns 2-3: log-scale width / height     (range ~ -1 to 3)
        # Decoding formula (mirrors original yolox.py _postprocess):
        #   cx_decoded = (raw_cx + grid_x) * stride
        #   w_decoded  = exp(raw_w)         * stride
        self._decode_yolox_output(output)

        objectness = output[:, 4]
        class_scores = output[:, 5:]

        conf = objectness[:, np.newaxis] * class_scores
        max_scores = conf.max(axis=1)
        class_ids_all = conf.argmax(axis=1)

        mask = max_scores >= self.nms_score_th
        if not mask.any():
            logger.debug("[CustomONNX] yolox post-process: no detections above score threshold.")
            return np.array([]), np.array([]), np.array([])

        output_filtered = output[mask]
        max_scores = max_scores[mask]
        class_ids_all = class_ids_all[mask]

        logger.debug(
            f"[CustomONNX] yolox post-process: {mask.sum()} candidates above threshold "
            f"(ratio={ratio:.4f}, orig={orig_w}x{orig_h})"
        )

        # Coordinates are now in letterboxed-input space (decoded absolute pixels).
        # Divide by ratio to recover original-image coordinates.
        cx = output_filtered[:, 0] / ratio
        cy = output_filtered[:, 1] / ratio
        bw = output_filtered[:, 2] / ratio
        bh = output_filtered[:, 3] / ratio

        x1 = np.clip((cx - bw / 2).astype(int), 0, orig_w)
        y1 = np.clip((cy - bh / 2).astype(int), 0, orig_h)
        x2 = np.clip((cx + bw / 2).astype(int), 0, orig_w)
        y2 = np.clip((cy + bh / 2).astype(int), 0, orig_h)

        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1).tolist()
        scores_list = max_scores.tolist()

        indices = cv2.dnn.NMSBoxes(
            boxes_xyxy, scores_list, self.nms_score_th, self.nms_th
        )

        if len(indices) == 0:
            logger.debug("[CustomONNX] yolox post-process: all candidates removed by NMS.")
            return np.array([]), np.array([]), np.array([])

        indices = np.array(indices).flatten()
        logger.debug(f"[CustomONNX] yolox post-process: {len(indices)} detections after NMS.")
        return (
            np.array(boxes_xyxy)[indices],
            np.array(scores_list)[indices],
            class_ids_all[indices],
        )

    def _postprocess_ssd(self, outputs, orig_w, orig_h):
        """Post-process SSD-style multi-output ONNX models.

        SSD MobileNet V2 (and similar) typically produce multiple output tensors.
        Common patterns:

        Pattern A (TF-exported / ONNX Model Zoo):
          - output[0]: boxes      [1, num_det, 4]  (y1, x1, y2, x2) normalised [0,1]
          - output[1]: class_ids  [1, num_det]
          - output[2]: scores     [1, num_det]
          - output[3]: num_detections [1]  (optional)

        Pattern B (some TF2 exports):
          - output[0]: boxes      [1, num_det, 4]  (y1, x1, y2, x2) normalised
          - output[1]: scores     [1, num_det, num_classes] or [1, num_det]
          - output[2]: class_ids  [1, num_det]
          - (output[3]: num_detections)

        Pattern C (Kalray / alternative):
          - output[0]: boxes      [1, num_det, 4]
          - output[1]: scores     [1, num_det]

        The method auto-detects which pattern based on output shapes and count.
        """
        num_outputs = len(outputs)
        logger.debug(
            f"[CustomONNX] ssd post-process: {num_outputs} outputs, "
            f"shapes={[o.shape for o in outputs]}"
        )

        if num_outputs == 0:
            return np.array([]), np.array([]), np.array([])

        # --- Identify boxes tensor (always the first 3D output with last dim == 4) ---
        boxes_raw = None
        scores_raw = None
        class_ids_raw = None
        num_det = None

        # Squeeze batch dim from all outputs
        squeezed = [np.squeeze(o) for o in outputs]

        # Find boxes: shape (..., 4)
        boxes_idx = -1
        for i, s in enumerate(squeezed):
            if s.ndim == 2 and s.shape[-1] == 4:
                boxes_raw = s
                boxes_idx = i
                break
            elif s.ndim == 1 and s.shape[0] == 4 and num_outputs > 1:
                # Single detection squeezed from [1, 1, 4] → (4,)
                boxes_raw = s.reshape(1, 4)
                boxes_idx = i
                break
            elif s.ndim == 1 and num_outputs == 1:
                # Single flat output — not SSD compatible
                logger.warning("[CustomONNX] ssd post-process: single flat output, not SSD format.")
                return np.array([]), np.array([]), np.array([])

        if boxes_raw is None:
            logger.warning(
                "[CustomONNX] ssd post-process: could not identify boxes tensor. "
                f"Output shapes: {[o.shape for o in outputs]}"
            )
            return np.array([]), np.array([]), np.array([])

        n_detections = boxes_raw.shape[0]

        # Find scores and class_ids from remaining outputs
        remaining = [s for j, s in enumerate(squeezed) if j != boxes_idx]

        for arr in remaining:
            if arr.ndim == 2 and arr.shape[0] == n_detections and arr.shape[1] > 4:
                # Multi-class scores: [num_det, num_classes]
                scores_raw = arr.max(axis=1)
                class_ids_raw = arr.argmax(axis=1).astype(np.int64)
            elif arr.ndim == 1 and arr.shape[0] == n_detections:
                if scores_raw is None:
                    # Could be scores or class_ids — heuristic: float with values
                    # in [0,1] range → scores; integer-like → class_ids
                    if arr.dtype in (np.float32, np.float64) and arr.max() <= 1.0:
                        scores_raw = arr
                    elif np.all(arr == arr.astype(int)):
                        class_ids_raw = arr.astype(np.int64)
                    else:
                        scores_raw = arr
                elif class_ids_raw is None:
                    class_ids_raw = arr.astype(np.int64)
            elif arr.ndim == 0 or (arr.ndim == 1 and arr.shape[0] == 1):
                # Could be num_detections scalar OR a score for a single detection
                val = float(arr.flat[0])
                if n_detections == 1 and 0.0 <= val <= 1.0 and scores_raw is None:
                    # Likely a confidence score for the single detection
                    scores_raw = np.array([val], dtype=np.float32)
                else:
                    num_det = int(val)

        # If num_detections was provided, slice everything
        if num_det is not None and num_det < n_detections:
            boxes_raw = boxes_raw[:num_det]
            if scores_raw is not None:
                scores_raw = scores_raw[:num_det]
            if class_ids_raw is not None:
                class_ids_raw = class_ids_raw[:num_det]
            n_detections = num_det

        # Default class_ids to 0 if not provided
        if class_ids_raw is None:
            class_ids_raw = np.zeros(n_detections, dtype=np.int64)

        # Default scores to 1.0 if not provided
        if scores_raw is None:
            scores_raw = np.ones(n_detections, dtype=np.float32)

        # --- Determine if boxes are normalised [0,1] or absolute pixels ---
        # If max coordinate <= 1.0 (with small tolerance), assume normalised
        boxes_max = boxes_raw.max() if n_detections > 0 else 0.0
        if boxes_max <= 1.5:
            # Normalised coordinates — SSD standard format is (y1, x1, y2, x2)
            y1 = boxes_raw[:, 0] * orig_h
            x1 = boxes_raw[:, 1] * orig_w
            y2 = boxes_raw[:, 2] * orig_h
            x2 = boxes_raw[:, 3] * orig_w
        else:
            # Absolute pixel coordinates — assume already in (x1, y1, x2, y2) or (y1, x1, y2, x2)
            # Heuristic: if col0 range ≈ height and col1 range ≈ width → (y1,x1,y2,x2)
            col0_range = boxes_raw[:, 2].max() - boxes_raw[:, 0].min() if n_detections > 0 else 0
            col1_range = boxes_raw[:, 3].max() - boxes_raw[:, 1].min() if n_detections > 0 else 0
            if col0_range > 0 and col1_range > 0:
                ratio_0 = col0_range / self.input_height if self.input_height > 0 else 1
                ratio_1 = col1_range / self.input_width if self.input_width > 0 else 1
                if abs(ratio_0 - 1.0) < 0.5 and abs(ratio_1 - 1.0) < 0.5:
                    # Likely (y1, x1, y2, x2) in model-input pixel space
                    scale_y = orig_h / self.input_height
                    scale_x = orig_w / self.input_width
                    y1 = boxes_raw[:, 0] * scale_y
                    x1 = boxes_raw[:, 1] * scale_x
                    y2 = boxes_raw[:, 2] * scale_y
                    x2 = boxes_raw[:, 3] * scale_x
                else:
                    # Assume (x1, y1, x2, y2) in model-input pixel space
                    scale_x = orig_w / self.input_width
                    scale_y = orig_h / self.input_height
                    x1 = boxes_raw[:, 0] * scale_x
                    y1 = boxes_raw[:, 1] * scale_y
                    x2 = boxes_raw[:, 2] * scale_x
                    y2 = boxes_raw[:, 3] * scale_y
            else:
                x1 = boxes_raw[:, 0]
                y1 = boxes_raw[:, 1]
                x2 = boxes_raw[:, 2]
                y2 = boxes_raw[:, 3]

        # Clip to image bounds and convert to int
        x1 = np.clip(x1, 0, orig_w).astype(int)
        y1 = np.clip(y1, 0, orig_h).astype(int)
        x2 = np.clip(x2, 0, orig_w).astype(int)
        y2 = np.clip(y2, 0, orig_h).astype(int)

        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

        # Filter by score threshold
        mask = scores_raw >= self.nms_score_th
        if not mask.any():
            logger.debug("[CustomONNX] ssd post-process: no detections above score threshold.")
            return np.array([]), np.array([]), np.array([])

        boxes_xyxy = boxes_xyxy[mask]
        scores_raw = scores_raw[mask]
        class_ids_raw = class_ids_raw[mask]

        # NMS
        boxes_list = boxes_xyxy.tolist()
        scores_list = scores_raw.tolist()
        indices = cv2.dnn.NMSBoxes(boxes_list, scores_list, self.nms_score_th, self.nms_th)

        if len(indices) == 0:
            logger.debug("[CustomONNX] ssd post-process: all candidates removed by NMS.")
            return np.array([]), np.array([]), np.array([])

        indices = np.array(indices).flatten()
        logger.debug(f"[CustomONNX] ssd post-process: {len(indices)} detections after NMS.")
        return (
            boxes_xyxy[indices],
            scores_raw[indices],
            class_ids_raw[indices],
        )

    # ------------------------------------------------------------------
    # NanoDet pre/post-processing
    # ------------------------------------------------------------------

    def _preprocess_nanodet(self, image):
        """Letterbox preprocessing for NanoDet models.

        NanoDet uses:
          - Letterbox padding (value=0) maintaining aspect ratio.
          - BGR → RGB, normalised with ImageNet mean=[103.53, 116.28, 123.675]
            and std=[57.375, 57.12, 58.395] (BGR order, no /255).

        Returns (blob, ratio) where ratio = resized / original.
        """
        orig_h, orig_w = image.shape[:2]
        ratio = min(self.input_height / orig_h, self.input_width / orig_w)
        new_h = int(orig_h * ratio)
        new_w = int(orig_w * ratio)

        padded = np.zeros(
            (self.input_height, self.input_width, 3), dtype=np.float32
        )
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        padded[:new_h, :new_w] = resized.astype(np.float32)

        # NanoDet normalisation (BGR order): (pixel - mean) / std
        mean = np.array([103.53, 116.28, 123.675], dtype=np.float32)
        std = np.array([57.375, 57.12, 58.395], dtype=np.float32)
        padded = (padded - mean) / std

        blob = np.transpose(padded, (2, 0, 1))          # HWC → CHW
        blob = np.ascontiguousarray(blob, dtype=np.float32)
        blob = np.expand_dims(blob, axis=0)             # CHW → BCHW
        return blob, ratio

    def _postprocess_nanodet(self, raw_output, orig_w, orig_h,
                             cls_pre_activated=None, reg_first_override=None):
        """Post-process NanoDet GFL/DFL output.

        Expected raw_output shape: (1, num_anchors, num_classes + 4*(reg_max+1))
        For NanoDet-m with 80 classes and reg_max=7: (1, 2125, 112)

        The DFL (Distribution Focal Loss) regression encodes each of the 4 box
        sides as a discrete distribution over reg_max+1 bins. The expected value
        of this distribution gives the distance from anchor center to box edge.

        Parameters
        ----------
        cls_pre_activated : bool or None
            Whether the class scores are already passed through sigmoid in the
            model graph.  Some exports (e.g. OpenCV Zoo NanoDet) apply the
            activation in-graph; applying sigmoid a second time pushes every
            anchor's score to ~0.5 and floods NMS with thousands of boxes.
            Defaults to ``None``/``False`` (treat scores as raw logits and apply
            sigmoid), preserving the standard NanoDet behaviour.  Callers that
            know the scores are already activated pass ``True``.
        reg_first_override : bool or None
            Force the channel layout (``True`` = ``[reg, classes]``,
            ``False`` = ``[classes, reg]``) instead of relying on the
            statistical heuristic.  Callers that build the combined tensor with
            a known layout (e.g. the multi-head path) should set this.
        """
        output = np.squeeze(raw_output)
        if output.ndim != 2:
            logger.warning(
                f"[CustomONNX] nanodet post-process: unexpected ndim={output.ndim}. "
                f"Returning empty detections."
            )
            return np.array([]), np.array([]), np.array([])

        num_anchors = output.shape[0]
        total_channels = output.shape[1]

        # Determine reg_max from the output shape
        # total_channels = num_classes + 4 * (reg_max + 1)
        reg_channels = total_channels - self.num_classes
        if reg_channels <= 0 or reg_channels % 4 != 0:
            logger.warning(
                f"[CustomONNX] nanodet post-process: cannot determine reg_max. "
                f"total_channels={total_channels}, num_classes={self.num_classes}. "
                f"Returning empty detections."
            )
            return np.array([]), np.array([]), np.array([])

        reg_max_plus_1 = reg_channels // 4  # e.g., 8 for reg_max=7

        # Detect channel layout (cached after first inference).
        # Skipped when the caller forces a layout via reg_first_override, or
        # when an explicit layout was supplied via the nanodet_reg_first
        # constructor argument.
        # Some NanoDet models (e.g. nanodet_qdq) output regression channels
        # first [reg, classes] instead of [classes, reg].
        # Heuristic: DFL regression values are softmax outputs (bounded ~[0,1]
        # with low variance), while raw class logits have higher variance.
        # NOTE: QDQ-quantised models can fool this heuristic because quantisation
        # maps most class logits to 0, making them appear bounded.  Multi-head
        # exports whose class heads are already sigmoid-activated also fool it,
        # which is why the multi path forces reg_first_override=False.
        if reg_first_override is not None:
            reg_first = bool(reg_first_override)
            logger.debug(
                f"[CustomONNX] nanodet post-process: layout forced by caller to "
                f"{'reg-first' if reg_first else 'classes-first'}."
            )
        else:
            if self._nanodet_reg_first is None:
                first_block = output[:, :reg_channels]
                last_block = output[:, reg_channels:]
                first_std = first_block.std()
                last_std = last_block.std()
                self._nanodet_reg_first = (
                    first_std < last_std
                    and first_block.min() >= -0.5
                    and first_block.max() <= 1.5
                )
                layout = "reg-first" if self._nanodet_reg_first else "classes-first"
                logger.debug(f"[CustomONNX] nanodet post-process: detected {layout} layout.")
            reg_first = self._nanodet_reg_first

        if reg_first:
            reg_output = output[:, :reg_channels]       # (num_anchors, 4*(reg_max+1))
            class_scores = output[:, reg_channels:]     # (num_anchors, num_classes)
        else:
            class_scores = output[:, :self.num_classes]  # (num_anchors, num_classes)
            reg_output = output[:, self.num_classes:]    # (num_anchors, 4*(reg_max+1))

        # Apply sigmoid to class scores only when they are raw logits.
        # NanoDet GFL heads normally output logits, but some exports (e.g.
        # OpenCV Zoo NanoDet) bake the sigmoid into the graph.  Re-applying it
        # would map every near-zero probability to ~0.5, so every anchor would
        # clear the score threshold and NMS would emit a flood of boxes.
        # Default (None/False) preserves the historical logits behaviour; only
        # callers that know the scores are already activated pass True.
        if not cls_pre_activated:
            class_scores = 1.0 / (1.0 + np.exp(-class_scores))

        # Get max class score and class id per anchor
        max_scores = class_scores.max(axis=1)
        class_ids_all = class_scores.argmax(axis=1)

        # Filter by score threshold
        mask = max_scores >= self.nms_score_th
        if not mask.any():
            logger.debug("[CustomONNX] nanodet post-process: no detections above threshold.")
            return np.array([]), np.array([]), np.array([])

        # Decode DFL regression to distances
        # Reshape reg: (num_anchors, 4, reg_max+1)
        reg_reshaped = reg_output.reshape(num_anchors, 4, reg_max_plus_1)

        # Softmax on last dimension
        reg_exp = np.exp(reg_reshaped - reg_reshaped.max(axis=2, keepdims=True))
        reg_softmax = reg_exp / reg_exp.sum(axis=2, keepdims=True)

        # Expected value: sum(i * softmax[i]) for i in 0..reg_max
        proj = np.arange(reg_max_plus_1, dtype=np.float32)
        distances = (reg_softmax * proj).sum(axis=2)  # (num_anchors, 4): left, top, right, bottom

        # Generate grid centers for all anchor points
        strides = [8, 16, 32, 64]
        centers = []
        stride_list = []
        for stride in strides:
            # NanoDet-Plus feature maps use ceil(input / stride): e.g. a 416
            # input with stride 64 yields a 7x7 grid (not 6x6 from floor div),
            # so the anchor count matches the network output (3598 for 416).
            n_h = math.ceil(self.input_height / stride)
            n_w = math.ceil(self.input_width / stride)
            if n_h <= 0 or n_w <= 0:
                continue
            yv, xv = np.meshgrid(np.arange(n_h), np.arange(n_w), indexing='ij')
            center_x = (xv.ravel() + 0.5) * stride
            center_y = (yv.ravel() + 0.5) * stride
            grid = np.stack([center_x, center_y], axis=1)  # (n_h*n_w, 2)
            centers.append(grid)
            stride_list.append(np.full(grid.shape[0], stride, dtype=np.float32))

        centers = np.concatenate(centers, axis=0)       # (num_anchors, 2)
        stride_arr = np.concatenate(stride_list, axis=0)  # (num_anchors,)

        # If anchor count doesn't match, try without stride 64
        if centers.shape[0] != num_anchors:
            strides_alt = [8, 16, 32]
            centers_alt = []
            stride_list_alt = []
            for stride in strides_alt:
                n_h = math.ceil(self.input_height / stride)
                n_w = math.ceil(self.input_width / stride)
                if n_h <= 0 or n_w <= 0:
                    continue
                yv, xv = np.meshgrid(np.arange(n_h), np.arange(n_w), indexing='ij')
                center_x = (xv.ravel() + 0.5) * stride
                center_y = (yv.ravel() + 0.5) * stride
                grid = np.stack([center_x, center_y], axis=1)
                centers_alt.append(grid)
                stride_list_alt.append(np.full(grid.shape[0], stride, dtype=np.float32))
            centers_alt = np.concatenate(centers_alt, axis=0)
            stride_arr_alt = np.concatenate(stride_list_alt, axis=0)
            if centers_alt.shape[0] == num_anchors:
                centers = centers_alt
                stride_arr = stride_arr_alt
            else:
                logger.warning(
                    f"[CustomONNX] nanodet post-process: anchor count mismatch. "
                    f"Expected {num_anchors}, got {centers.shape[0]} (4 strides) "
                    f"or {centers_alt.shape[0]} (3 strides). Returning empty."
                )
                return np.array([]), np.array([]), np.array([])

        # Convert distances to absolute coordinates:
        # x1 = cx - left * stride, y1 = cy - top * stride
        # x2 = cx + right * stride, y2 = cy + bottom * stride
        stride_col = stride_arr[:, np.newaxis]  # (num_anchors, 1)
        x1_all = centers[:, 0] - distances[:, 0] * stride_arr
        y1_all = centers[:, 1] - distances[:, 1] * stride_arr
        x2_all = centers[:, 0] + distances[:, 2] * stride_arr
        y2_all = centers[:, 1] + distances[:, 3] * stride_arr

        # Scale from letterbox-input space to original image
        ratio = min(self.input_height / orig_h, self.input_width / orig_w)
        x1_all = x1_all / ratio
        y1_all = y1_all / ratio
        x2_all = x2_all / ratio
        y2_all = y2_all / ratio

        # Apply mask
        x1 = np.clip(x1_all[mask], 0, orig_w).astype(int)
        y1 = np.clip(y1_all[mask], 0, orig_h).astype(int)
        x2 = np.clip(x2_all[mask], 0, orig_w).astype(int)
        y2 = np.clip(y2_all[mask], 0, orig_h).astype(int)
        filtered_scores = max_scores[mask]
        filtered_class_ids = class_ids_all[mask]

        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1).tolist()
        scores_list = filtered_scores.tolist()

        indices = cv2.dnn.NMSBoxes(
            boxes_xyxy, scores_list, self.nms_score_th, self.nms_th
        )

        if len(indices) == 0:
            logger.debug("[CustomONNX] nanodet post-process: all candidates removed by NMS.")
            return np.array([]), np.array([]), np.array([])

        indices = np.array(indices).flatten()
        logger.debug(f"[CustomONNX] nanodet post-process: {len(indices)} detections after NMS.")
        return (
            np.array(boxes_xyxy)[indices],
            np.array(scores_list)[indices],
            filtered_class_ids[indices],
        )

    def _postprocess_nanodet_multi(self, outputs, orig_w, orig_h):
        """Post-process NanoDet multi-head output (separate cls + reg tensors per stride).

        This handles models like ``object_detection_nanodet_2022nov.onnx`` that export
        6 separate output tensors instead of a single concatenated tensor:
          - 3 classification heads: shape (1, n_anchors, num_classes)
          - 3 regression heads:     shape (1, n_anchors, 4*(reg_max+1))

        The method groups outputs by anchor count, concatenates cls and reg per stride,
        then forwards the combined single tensor to ``_postprocess_nanodet``.
        """
        # Separate cls and reg outputs by their last dimension.
        # cls: last_dim == num_classes, reg: last_dim == 4*(reg_max+1)
        cls_by_anchors = {}
        reg_by_anchors = {}
        for out in outputs:
            out_squeezed = np.squeeze(out, axis=0)  # (n_anchors, channels)
            n_anchors, channels = out_squeezed.shape
            if channels == self.num_classes:
                cls_by_anchors[n_anchors] = out_squeezed
            else:
                reg_by_anchors[n_anchors] = out_squeezed

        if not cls_by_anchors or not reg_by_anchors:
            logger.warning(
                "[CustomONNX] nanodet_multi: could not separate cls/reg outputs. "
                f"num_classes={self.num_classes}. Returning empty detections."
            )
            return np.array([]), np.array([]), np.array([])

        # Validate that cls and reg heads are paired (same set of anchor counts).
        if cls_by_anchors.keys() != reg_by_anchors.keys():
            logger.warning(
                "[CustomONNX] nanodet_multi: cls and reg heads have mismatched anchor counts. "
                f"cls anchor counts={sorted(cls_by_anchors)}, "
                f"reg anchor counts={sorted(reg_by_anchors)}. "
                "Returning empty detections."
            )
            return np.array([]), np.array([]), np.array([])

        # Build combined tensor by pairing cls+reg per anchor count, sorted descending
        anchor_counts = sorted(cls_by_anchors.keys(), reverse=True)
        combined_parts = []
        for n in anchor_counts:
            cls = cls_by_anchors[n]   # (n, num_classes)
            reg = reg_by_anchors[n]   # (n, 4*(reg_max+1))
            combined_parts.append(np.concatenate([cls, reg], axis=1))  # (n, num_classes+reg)

        combined = np.concatenate(combined_parts, axis=0)  # (total_anchors, num_classes+reg)
        combined = combined[np.newaxis, ...]               # (1, total_anchors, num_classes+reg)

        # The combined tensor is built as [classes, reg] per stride, so the
        # layout is unambiguously classes-first; bypass the statistical
        # heuristic (which mistakes the low-variance, already-activated class
        # block for the DFL regression block).  Detect whether the class heads
        # are already sigmoid-activated so we do not apply sigmoid twice.
        cls_concat = np.concatenate(
            [cls_by_anchors[n] for n in anchor_counts], axis=0
        )
        cls_pre_activated = bool(
            cls_concat.min() >= 0.0 and cls_concat.max() <= 1.0
        )

        logger.debug(
            f"[CustomONNX] nanodet_multi: combined tensor shape={combined.shape}, "
            f"cls_pre_activated={cls_pre_activated}"
        )
        return self._postprocess_nanodet(
            combined, orig_w, orig_h,
            cls_pre_activated=cls_pre_activated,
            reg_first_override=False,
        )

    # ------------------------------------------------------------------
    # YOLOX grid decoding
    # ------------------------------------------------------------------

    def _decode_yolox_output(self, output):
        """Apply YOLOX grid decoding to raw model output in-place.

        YOLOX ONNX models export *undecoded* predictions:
          - col 0-1: raw offset within the grid cell   (not absolute pixels)
          - col 2-3: log-scale width / height           (not absolute pixels)

        This method applies the decoding used by the original yolox.py,
        **modifying columns 0-3 of the array in-place**:
          cx = (raw_cx + grid_x) * stride
          cy = (raw_cy + grid_y) * stride
          w  = exp(raw_w)         * stride
          h  = exp(raw_h)         * stride

        After decoding, columns 0-3 hold absolute pixel coordinates in
        letterboxed-input space ready for / ratio back-projection.

        Parameters
        ----------
        output : np.ndarray  shape (num_anchors, num_classes + 5)
            Raw squeezed model output — columns 0-3 are modified in-place.
        """
        strides = [8, 16, 32]
        num_anchors = output.shape[0]
        grids = []
        per_head_strides = []
        total_anchors = 0
        for stride in strides:
            n_h = self.input_height // stride
            n_w = self.input_width // stride
            head_anchors = n_h * n_w
            if total_anchors + head_anchors > num_anchors:
                # Adding this head would exceed the anchor count; stop here.
                break
            xv, yv = np.meshgrid(np.arange(n_w), np.arange(n_h))
            grid = np.stack((xv, yv), axis=2).reshape(-1, 2)   # (n_h*n_w, 2)
            grids.append(grid)
            per_head_strides.append(
                np.full((head_anchors, 1), stride, dtype=np.float32)
            )
            total_anchors += head_anchors
            if total_anchors == num_anchors:
                break

        if total_anchors != num_anchors:
            logger.warning(
                f"[CustomONNX] yolox decode: anchor count mismatch — output has "
                f"{num_anchors} anchors but grid built from input "
                f"{self.input_width}x{self.input_height} with strides {strides} "
                f"accumulated {total_anchors}. Skipping grid decoding; coordinates will be raw."
            )
            return

        grids = np.concatenate(grids, axis=0)             # (num_anchors, 2)
        expanded_strides = np.concatenate(per_head_strides, axis=0)  # (num_anchors, 1)

        output[:, :2] = (output[:, :2] + grids) * expanded_strides
        output[:, 2:4] = np.exp(output[:, 2:4]) * expanded_strides

    # ------------------------------------------------------------------
    # Drawing helper (optional, matches the interface of other wrappers)
    # ------------------------------------------------------------------

    def draw(self, image, score_th, bboxes, scores, class_ids, class_names, thickness=1):
        debug_image = copy.deepcopy(image)
        for bbox, score, class_id in zip(bboxes, scores, class_ids):
            if score < score_th:
                continue
            x1, y1, x2, y2 = map(int, bbox)
            color = self._get_color(int(class_id))
            cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, thickness)
            label = class_names.get(int(class_id), str(int(class_id)))
            cv2.putText(
                debug_image,
                f"{label}: {score:.2f}",
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                thickness,
            )
        return debug_image

    def _get_color(self, index):
        t = abs(int(index + 5)) * 3
        return ((29 * t) % 255, (17 * t) % 255, (37 * t) % 255)
