#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Inference wrapper for the pothole YOLO segmentation model (Ultralytics YOLOv8n-seg).

Output of __call__: (segmentation_map, class_ids)
  - segmentation_map : np.ndarray shape [N, H, W] binary float32 masks
  - class_ids        : np.ndarray shape [N] int32 class indices

Use compute_pixel_counts() to get a {class_name: pixel_count} dict suitable
for the Chart node's flat-numeric-dict path.
"""

import os

import cv2
import numpy as np
import onnxruntime

os.environ.setdefault("ORT_CUDA_USE_CUDNN", "0")


class PotholeYOLOSeg:
    """Ultralytics YOLOv8n-seg wrapper specialised for the pothole model.

    Compatible with the ``get_class_num()`` interface used by
    ``node_semantic_segmentation.py``.  Unlike the generic YOLOv8Seg class,
    ``__call__`` returns a *tuple* ``(segmentation_map, class_ids)`` so that
    the node can produce per-class pixel-count JSON for the Chart node.
    """

    CLASS_NAMES = {0: "Pothole"}

    def __init__(
        self,
        model_path: str,
        providers=None,
        confidence_threshold: float = 0.25,
    ):
        if providers is None:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.onnx_session = onnxruntime.InferenceSession(
            model_path, providers=providers
        )
        self.confidence_threshold = confidence_threshold

        inp = self.onnx_session.get_inputs()[0]
        self.input_name = inp.name
        # shape: [1, 3, H, W]
        self.input_height = int(inp.shape[2])
        self.input_width = int(inp.shape[3])

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_class_num(self) -> int:
        return len(self.CLASS_NAMES)

    def __call__(self, image: np.ndarray):
        """Run inference on a BGR image.

        Returns
        -------
        segmentation_map : np.ndarray, shape [N, H, W], dtype float32
            Binary masks (values 0.0 / 1.0) for each detected instance.
        class_ids : np.ndarray, shape [N], dtype int32
            Class index of each detected instance.
        """
        h, w = image.shape[:2]
        inp = self._preprocess(image)
        outputs = self.onnx_session.run(None, {self.input_name: inp})
        return self._postprocess(outputs, w, h)

    def compute_pixel_counts(
        self,
        segmentation_map: np.ndarray,
        class_ids: np.ndarray,
    ) -> dict:
        """Return ``{class_name: pixel_count}`` for the given masks.

        Pixels belonging to overlapping instances of the same class are
        counted once (union of masks).  Classes with zero detections are
        included with a value of 0 so the Chart node always sees all labels.
        """
        # Initialise with zero counts for all known classes
        counts = {name: 0 for name in self.CLASS_NAMES.values()}

        if segmentation_map is None or len(segmentation_map) == 0:
            return counts

        # Group masks by class and OR them (union) before counting
        for class_id in np.unique(class_ids):
            class_indices = np.where(class_ids == int(class_id))[0]
            union_mask = np.zeros(segmentation_map.shape[1:], dtype=np.float32)
            for idx in class_indices:
                union_mask = np.maximum(union_mask, segmentation_map[idx])
            pixel_count = int(np.sum(union_mask > 0.5))
            class_name = self.CLASS_NAMES.get(int(class_id), f"class_{class_id}")
            counts[class_name] = pixel_count

        return counts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        inp = cv2.resize(image, (self.input_width, self.input_height))
        inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB)
        inp = inp.astype(np.float32) / 255.0
        inp = np.transpose(inp, (2, 0, 1))
        return np.expand_dims(inp, axis=0)

    def _postprocess(self, outputs, image_width: int, image_height: int):
        """Decode YOLOv8-seg outputs.

        output0 shape: [1, 4 + num_classes + 32, 8400]
        output1 shape: [1, 32, 160, 160]  (proto masks)
        """
        boxes_output = np.squeeze(outputs[0])   # [37, 8400]
        boxes_output = np.transpose(boxes_output)  # [8400, 37]

        num_classes = len(self.CLASS_NAMES)  # 1

        # Confidence scores (class columns: index 4 to 4+num_classes)
        scores = boxes_output[:, 4: 4 + num_classes]  # [8400, 1]
        max_scores = scores[:, 0]
        class_ids = np.zeros(len(max_scores), dtype=np.int32)

        keep = max_scores > self.confidence_threshold
        if not np.any(keep):
            empty = np.zeros((0, image_height, image_width), dtype=np.float32)
            return empty, np.array([], dtype=np.int32)

        kept_class_ids = class_ids[keep]
        # Mask coefficients start after bbox + class columns
        mask_coefficients = boxes_output[keep, 4 + num_classes:]  # [N, 32]

        proto_masks = np.squeeze(outputs[1])  # [32, 160, 160]
        proto_h, proto_w = proto_masks.shape[1], proto_masks.shape[2]

        # [N, 32] @ [32, 160*160] → [N, 160*160] → [N, 160, 160]
        masks = np.matmul(
            mask_coefficients, proto_masks.reshape(32, -1)
        ).reshape(-1, proto_h, proto_w)

        # Sigmoid activation
        masks = 1.0 / (1.0 + np.exp(-masks))

        # Resize to original frame size and threshold
        resized = []
        for mask in masks:
            m = cv2.resize(
                mask, (image_width, image_height), interpolation=cv2.INTER_LINEAR
            )
            resized.append((m > 0.5).astype(np.float32))

        if not resized:
            empty = np.zeros((0, image_height, image_width), dtype=np.float32)
            return empty, np.array([], dtype=np.int32)

        return np.array(resized), kept_class_ids
