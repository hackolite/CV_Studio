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
import os

import cv2
import numpy as np
import onnxruntime

# Disable cuDNN for safer operation (mirrors other YOLO wrappers in this project)
os.environ["ORT_CUDA_USE_CUDNN"] = "0"


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

        self.onnx_session = onnxruntime.InferenceSession(
            model_path, providers=providers
        )

        # Use provided input name, fall back to first input name from model
        if input_name:
            self.input_name = input_name
        else:
            self.input_name = self.onnx_session.get_inputs()[0].name

        self.output_name = self.onnx_session.get_outputs()[0].name

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
        blob = self._preprocess(image)
        outputs = self.onnx_session.run(None, {self.input_name: blob})

        if self.output_format == "yolox":
            bboxes, scores, class_ids = self._postprocess_yolox(
                outputs[0], orig_w, orig_h
            )
        else:
            # Default: yolo11 / ultralytics
            bboxes, scores, class_ids = self._postprocess_yolo11(
                outputs[0], orig_w, orig_h
            )

        return bboxes, scores, class_ids

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------

    def _preprocess(self, image):
        """Resize → RGB → HWC→CHW → float32 → batch."""
        img = cv2.resize(
            image,
            (self.input_width, self.input_height),
            interpolation=cv2.INTER_LINEAR,
        )
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC → CHW
        img = np.expand_dims(img, axis=0)   # CHW → BCHW
        return img

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
            return np.array([]), np.array([]), np.array([])

        # Transpose to (num_anchors, num_classes+4)
        output = output.T

        boxes_xywh = output[:, :4]     # cx, cy, w, h (normalised to input size)
        class_scores = output[:, 4:]   # (num_anchors, num_classes)

        # Scale factors back to original image
        scale_x = orig_w / self.input_width
        scale_y = orig_h / self.input_height

        max_scores = class_scores.max(axis=1)
        class_ids_all = class_scores.argmax(axis=1)

        # Filter by threshold
        mask = max_scores >= self.nms_score_th
        if not mask.any():
            return np.array([]), np.array([]), np.array([])

        boxes_xywh = boxes_xywh[mask]
        max_scores = max_scores[mask]
        class_ids_all = class_ids_all[mask]

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
            return np.array([]), np.array([]), np.array([])

        indices = np.array(indices).flatten()
        return (
            np.array(boxes_xyxy)[indices],
            np.array(scores_list)[indices],
            class_ids_all[indices],
        )

    def _postprocess_yolox(self, raw_output, orig_w, orig_h):
        """Post-process YOLOX output.

        Expected raw_output shape: (1, num_anchors, num_classes+5)
        The +5 columns are: cx, cy, w, h, objectness, class_scores...
        """
        output = np.squeeze(raw_output)
        if output.ndim != 2:
            return np.array([]), np.array([]), np.array([])

        objectness = output[:, 4]
        class_scores = output[:, 5:]

        conf = objectness[:, np.newaxis] * class_scores
        max_scores = conf.max(axis=1)
        class_ids_all = conf.argmax(axis=1)

        mask = max_scores >= self.nms_score_th
        if not mask.any():
            return np.array([]), np.array([]), np.array([])

        output = output[mask]
        max_scores = max_scores[mask]
        class_ids_all = class_ids_all[mask]

        scale_x = orig_w / self.input_width
        scale_y = orig_h / self.input_height

        cx = output[:, 0] * scale_x
        cy = output[:, 1] * scale_y
        bw = output[:, 2] * scale_x
        bh = output[:, 3] * scale_y

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
            return np.array([]), np.array([]), np.array([])

        indices = np.array(indices).flatten()
        return (
            np.array(boxes_xyxy)[indices],
            np.array(scores_list)[indices],
            class_ids_all[indices],
        )

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
