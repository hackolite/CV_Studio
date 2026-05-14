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

        self.onnx_session = make_session(model_path, providers)

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
        blob, ratio, pad_top, pad_left = self._preprocess(image)
        logger.debug(
            f"[CustomONNX] Preprocessed blob shape: {blob.shape}, "
            f"letterbox ratio: {ratio:.4f}, pad_top={pad_top}, pad_left={pad_left}"
        )
        outputs = self.onnx_session.run(None, {self.input_name: blob})

        raw_output = outputs[0]
        logger.debug(f"[CustomONNX] Raw output shape: {raw_output.shape}")

        if self.output_format == "yolox":
            bboxes, scores, class_ids = self._postprocess_yolox(
                raw_output, orig_w, orig_h, ratio
            )
        else:
            # Default: yolo11 / ultralytics
            bboxes, scores, class_ids = self._postprocess_yolo11(
                raw_output, orig_w, orig_h, ratio, pad_top, pad_left
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
        blob     : np.ndarray  BCHW float32 blob ready for ONNX session
        ratio    : float       letterbox scale ratio (resized / original)
        pad_top  : int         pixels of top-padding added during letterbox
        pad_left : int         pixels of left-padding added during letterbox

        Both yolo11 and yolox paths now use letterbox preprocessing so that
        coordinate recovery is consistent: ``(coord - pad) / ratio``.
        """
        if self.output_format == "yolox":
            return self._preprocess_yolox(image)
        return self._preprocess_yolo11(image)

    def _preprocess_yolox(self, image):
        """Letterbox preprocessing for YOLOX / FreeYOLO models.

        YOLOX was trained with:
          - Letterbox padding (value=114) maintaining aspect ratio.
          - Raw pixel values in [0, 255] — **no** /255 normalisation.
          - BGR colour format (no colour space conversion needed).

        Returns (blob, ratio, pad_top=0, pad_left=0).
        The resized image is placed in the top-left corner so pad offsets are 0.
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
        return blob, ratio, 0, 0

    def _preprocess_yolo11(self, image):
        """Letterbox preprocessing for YOLO11/YOLOv8 Ultralytics models.

        Ultralytics models are trained with:
          - Centered letterbox padding (value=114) preserving aspect ratio.
          - Normalised pixel values in [0, 1].
          - RGB colour format.

        Using stretch-resize instead of letterbox causes incorrect bbox
        coordinates on non-square images because the model's coordinate
        predictions are calibrated for the letterbox input distribution.

        Returns (blob, ratio, pad_top, pad_left) for accurate coordinate
        back-projection: ``coord_original = (coord_model - pad) / ratio``.
        """
        orig_h, orig_w = image.shape[:2]
        ratio = min(self.input_height / orig_h, self.input_width / orig_w)
        new_h = int(orig_h * ratio)
        new_w = int(orig_w * ratio)

        # Centered letterbox: compute padding so the resized image is centred.
        pad_top = (self.input_height - new_h) // 2
        pad_left = (self.input_width - new_w) // 2

        # Letterbox canvas filled with 114 (Ultralytics default pad colour).
        padded = np.full(
            (self.input_height, self.input_width, 3), 114, dtype=np.uint8
        )
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        padded[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = resized

        logger.debug(
            f"[CustomONNX/yolo11 preprocess] orig={orig_w}x{orig_h}, "
            f"resized={new_w}x{new_h}, ratio={ratio:.4f}, "
            f"pad_top={pad_top}, pad_left={pad_left}, "
            f"input={self.input_width}x{self.input_height}"
        )

        img = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC → CHW
        img = np.expand_dims(img, axis=0)   # CHW → BCHW
        return img, ratio, pad_top, pad_left

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    def _postprocess_yolo11(self, raw_output, orig_w, orig_h, ratio=1.0,
                             pad_top=0, pad_left=0):
        """Post-process YOLO11/YOLOv8 Ultralytics output.

        Expected raw_output shape: (1, num_classes+4, num_anchors)

        Parameters
        ----------
        ratio : float
            Letterbox scale ratio returned by ``_preprocess_yolo11``.
        pad_top : int
            Top padding applied during letterbox preprocessing.
        pad_left : int
            Left padding applied during letterbox preprocessing.

        Coordinate back-projection uses the letterbox inverse:
            x_original = (cx_model - pad_left) / ratio
            y_original = (cy_model - pad_top)  / ratio
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

        boxes_xywh = output[:, :4]     # cx, cy, w, h (in letterboxed input pixels)
        class_scores = output[:, 4:]   # (num_anchors, num_classes)

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
            f"(ratio={ratio:.4f}, pad_top={pad_top}, pad_left={pad_left})"
        )

        # Convert cx,cy,w,h (letterboxed space) → x1,y1,x2,y2 (original image)
        # Letterbox inverse: coord_original = (coord_model - pad) / ratio
        cx = (boxes_xywh[:, 0] - pad_left) / ratio
        cy = (boxes_xywh[:, 1] - pad_top) / ratio
        bw = boxes_xywh[:, 2] / ratio
        bh = boxes_xywh[:, 3] / ratio

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
        grids = []
        expanded_strides = []
        for stride in strides:
            n_h = self.input_height // stride
            n_w = self.input_width // stride
            xv, yv = np.meshgrid(np.arange(n_w), np.arange(n_h))
            grid = np.stack((xv, yv), axis=2).reshape(-1, 2)   # (n_h*n_w, 2)
            grids.append(grid)
            expanded_strides.append(
                np.full((grid.shape[0], 1), stride, dtype=np.float32)
            )
        grids = np.concatenate(grids, axis=0)             # (num_anchors, 2)
        expanded_strides = np.concatenate(expanded_strides, axis=0)  # (num_anchors, 1)

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
