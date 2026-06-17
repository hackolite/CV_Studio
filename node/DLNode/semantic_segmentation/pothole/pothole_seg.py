#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Inference wrapper for the pothole YOLO segmentation model (Ultralytics YOLOv8n-seg).

Output of __call__: (segmentation_map, class_ids)
  - segmentation_map : np.ndarray shape [N, H, W] binary float32 masks
  - class_ids        : np.ndarray shape [N] int32 class indices

Use compute_pixel_counts() to get a {class_name: pixel_count} dict suitable
for the Chart node's flat-numeric-dict path.

PotholeYOLOSegV12 extends PotholeYOLOSeg for potehole_12.onnx:
  - Uses letterbox preprocessing (preserves aspect ratio with grey padding)
  - Applies NMS to filter overlapping detections
  - Provides draw_result() for coloured overlay + contours + bounding boxes
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

        # Group masks by class, take union, then count pixels
        for class_id in np.unique(class_ids):
            class_indices = np.where(class_ids == class_id)[0]
            union_mask = np.any(
                segmentation_map[class_indices] > 0.5, axis=0
            )
            pixel_count = int(np.count_nonzero(union_mask))
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


# ---------------------------------------------------------------------------
# Letterbox-aware variant for potehole_12.onnx
# ---------------------------------------------------------------------------

class PotholeYOLOSegV12(PotholeYOLOSeg):
    """YOLOv8-seg wrapper for ``potehole_12.onnx`` using letterbox preprocessing.

    Differences from the base ``PotholeYOLOSeg``:

    * ``_preprocess`` performs letterbox resize (aspect-ratio-preserving with
      grey padding) instead of a plain resize.
    * ``_postprocess`` applies NMS and correctly unprojects masks / bounding
      boxes back to the original image coordinate space.
    * ``draw_result`` renders a per-instance coloured overlay, green contours,
      green bounding boxes, and confidence labels on the original frame.
    """

    _OVERLAY_COLOR = (0, 0, 255)   # BGR red for pothole
    _CONTOUR_COLOR = (0, 255, 0)   # BGR green
    _BBOX_COLOR    = (0, 255, 0)
    _LABEL_COLOR   = (0, 255, 0)
    _PAD_VALUE     = 114

    def __init__(self, model_path: str, providers=None,
                 confidence_threshold: float = 0.25,
                 iou_threshold: float = 0.45):
        super().__init__(model_path, providers, confidence_threshold)
        self.iou_threshold = iou_threshold
        # State stored by _preprocess and consumed by _postprocess / draw_result
        self._scale: float = 1.0
        self._pad_top: int = 0
        self._pad_left: int = 0
        # Stored after _postprocess for use in draw_result
        self._last_boxes: np.ndarray = np.empty((0, 4), dtype=np.float32)
        self._last_scores: np.ndarray = np.empty((0,), dtype=np.float32)

    # ------------------------------------------------------------------
    # Letterbox preprocessing
    # ------------------------------------------------------------------

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Letterbox-resize ``image`` to the model's input size.

        Stores ``_scale``, ``_pad_top``, and ``_pad_left`` for later
        use in ``_postprocess``.
        """
        h, w = image.shape[:2]
        in_h, in_w = self.input_height, self.input_width

        scale = in_h / max(h, w)
        nh, nw = int(h * scale), int(w * scale)
        resized = cv2.resize(image, (nw, nh))

        padded = np.full((in_h, in_w, 3), self._PAD_VALUE, dtype=np.uint8)
        pad_top  = (in_h - nh) // 2
        pad_left = (in_w - nw) // 2
        padded[pad_top:pad_top + nh, pad_left:pad_left + nw] = resized

        self._scale    = scale
        self._pad_top  = pad_top
        self._pad_left = pad_left

        # BGR → RGB, normalise, NCHW
        blob = padded[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[np.newaxis]
        return blob

    # ------------------------------------------------------------------
    # NMS helper
    # ------------------------------------------------------------------

    @staticmethod
    def _nms(boxes: np.ndarray, scores: np.ndarray,
             iou_thresh: float) -> list:
        """Greedy NMS.  ``boxes`` in xyxy format."""
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(int(i))
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            order = order[1:][iou < iou_thresh]
        return keep

    # ------------------------------------------------------------------
    # Postprocessing with letterbox unprojection
    # ------------------------------------------------------------------

    def _postprocess(self, outputs, image_width: int,
                     image_height: int):
        """Decode model outputs, apply NMS, and unproject to original size.

        Stores ``_last_boxes`` (xyxy in original image coords) and
        ``_last_scores`` on ``self`` for use in ``draw_result``.
        """
        pred       = outputs[0][0].T   # [8400, 5 + 32]
        proto      = outputs[1][0]     # [32, 160, 160]

        scores_all = pred[:, 4]
        mask_keep  = scores_all > self.confidence_threshold
        pred = pred[mask_keep]

        if len(pred) == 0:
            self._last_boxes  = np.empty((0, 4), dtype=np.float32)
            self._last_scores = np.empty((0,), dtype=np.float32)
            empty = np.zeros((0, image_height, image_width), dtype=np.float32)
            return empty, np.array([], dtype=np.int32)

        scores = pred[:, 4]
        coefs  = pred[:, 5:]   # [N, 32]

        # cx, cy, w, h → x1, y1, x2, y2 (letterbox space)
        cx, cy = pred[:, 0], pred[:, 1]
        bw, bh = pred[:, 2], pred[:, 3]
        boxes_lb = np.stack(
            [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], axis=1
        )

        # NMS
        keep = self._nms(boxes_lb, scores, self.iou_threshold)
        boxes_lb = boxes_lb[keep]
        scores   = scores[keep]
        coefs    = coefs[keep]

        proto_h, proto_w = proto.shape[1], proto.shape[2]
        in_h, in_w = self.input_height, self.input_width
        scale, pad_top, pad_left = self._scale, self._pad_top, self._pad_left

        # Convert letterbox boxes → original image coords
        orig_boxes = np.stack([
            np.clip((boxes_lb[:, 0] - pad_left) / scale, 0, image_width),
            np.clip((boxes_lb[:, 1] - pad_top)  / scale, 0, image_height),
            np.clip((boxes_lb[:, 2] - pad_left) / scale, 0, image_width),
            np.clip((boxes_lb[:, 3] - pad_top)  / scale, 0, image_height),
        ], axis=1)

        self._last_boxes  = orig_boxes.astype(np.float32)
        self._last_scores = scores.astype(np.float32)

        # Decode per-instance masks
        # [N, 32] @ [32, 160*160] → [N, 160, 160]
        mask_logits = (coefs @ proto.reshape(32, -1)).reshape(
            -1, proto_h, proto_w
        )
        mask_probs = 1.0 / (1.0 + np.exp(-mask_logits))   # sigmoid

        resized_masks = []
        for i, mask_prob in enumerate(mask_probs):
            # Upscale to model input size
            mask_full = cv2.resize(
                mask_prob, (in_w, in_h), interpolation=cv2.INTER_LINEAR
            )
            # Crop away letterbox padding
            crop_h = int(image_height * scale)
            crop_w = int(image_width  * scale)
            mask_crop = mask_full[
                pad_top: pad_top + crop_h,
                pad_left: pad_left + crop_w,
            ]
            # Resize to original image size
            mask_orig = cv2.resize(
                mask_crop, (image_width, image_height),
                interpolation=cv2.INTER_LINEAR,
            )
            resized_masks.append((mask_orig > 0.5).astype(np.float32))

        class_ids = np.zeros(len(keep), dtype=np.int32)
        return np.array(resized_masks), class_ids

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def draw_result(self, frame: np.ndarray,
                    segmentation_map: np.ndarray) -> np.ndarray:
        """Return a copy of ``frame`` with coloured mask overlays, contours,
        and bounding boxes drawn.

        Uses the bounding boxes and scores stored during the most recent
        ``__call__``.  The image returned also has the pixel-count per
        instance displayed as an annotation.

        Parameters
        ----------
        frame : np.ndarray
            Original BGR image (unmodified).
        segmentation_map : np.ndarray
            Binary masks returned by ``__call__``, shape [N, H, W].

        Returns
        -------
        np.ndarray
            Annotated BGR image.
        """
        result = frame.copy()
        boxes  = self._last_boxes
        scores = self._last_scores

        for i, binary_f in enumerate(segmentation_map):
            binary = binary_f.astype(np.uint8)

            # Coloured overlay (red)
            colored = np.zeros_like(result)
            colored[:] = self._OVERLAY_COLOR
            result = np.where(
                binary[:, :, None],
                cv2.addWeighted(result, 0.5, colored, 0.5, 0),
                result,
            )

            # Green contour
            contours, _ = cv2.findContours(
                binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(result, contours, -1, self._CONTOUR_COLOR, 2)

            # Pixel count annotation
            pixel_count = int(np.count_nonzero(binary))

            # Bounding box + label
            if i < len(boxes):
                bx1 = int(boxes[i, 0])
                by1 = int(boxes[i, 1])
                bx2 = int(boxes[i, 2])
                by2 = int(boxes[i, 3])
                cv2.rectangle(result, (bx1, by1), (bx2, by2),
                              self._BBOX_COLOR, 2)
                score  = float(scores[i]) if i < len(scores) else 0.0
                label  = f"Pothole {score:.2f}  px:{pixel_count}"
                cv2.putText(result, label, (bx1, max(by1 - 8, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                            self._LABEL_COLOR, 2)

        return result
