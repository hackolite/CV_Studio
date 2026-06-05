#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyTorch-backed student for online knowledge distillation.

This module makes the student's **backpropagation actually functional**: the
student ONNX graph is loaded into PyTorch (converted on the fly with
``onnx2torch``) so the convolutional *backbone and/or detection heads* become
trainable ``torch.nn.Parameter`` tensors. The requested distillation loss is
then back-propagated through the real network with a standard optimizer step,
and inference is performed with the *updated* weights so the improvement is
observable frame after frame.

Everything here is optional: if PyTorch or ``onnx2torch`` is not installed, or
the conversion of a particular model fails, the caller falls back to the affine
correction head in :mod:`online_adapter`. Import errors never propagate.

Supported output formats for the differentiable decode: ``yolo11`` (Ultralytics
YOLOv8/v11, boxes already in input pixels) and ``yolox`` (grid + objectness).
"""

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy dependencies — never fail to import this module because of them
# ---------------------------------------------------------------------------
_TORCH_AVAILABLE = False
_ONNX2TORCH_AVAILABLE = False
try:  # pragma: no cover - exercised only when torch is installed
    import torch
    import torch.nn.functional as F
    _TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    torch = None
    F = None

try:  # pragma: no cover - exercised only when onnx2torch is installed
    from onnx2torch import convert as _onnx2torch_convert
    _ONNX2TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    _onnx2torch_convert = None


def is_torch_backprop_available() -> bool:
    """True when both PyTorch and onnx2torch can be used for real backprop."""
    return _TORCH_AVAILABLE and _ONNX2TORCH_AVAILABLE


# Number of trailing parameter tensors trained when ``train_scope='head'``.
_DEFAULT_HEAD_PARAMS = 8
# Weight of the classification term relative to the box term in the loss.
_CLASS_LOSS_WEIGHT = 1.0


class TorchStudent:
    """Trainable PyTorch student converted from an ONNX detector.

    Parameters
    ----------
    model_path : str
        Path to the student ONNX model.
    input_width, input_height : int
        Network input resolution.
    output_format : str
        ``'yolo11'`` or ``'yolox'``.
    num_classes : int
        Number of detection classes.
    learning_rate : float
        Optimizer learning rate.
    train_scope : str
        ``'head'`` to train only the last few parameter tensors (detection
        heads), or ``'all'`` to fine-tune the whole backbone + heads.
    """

    def __init__(
        self,
        model_path: str,
        input_width: int = 640,
        input_height: int = 640,
        output_format: str = "yolo11",
        num_classes: int = 80,
        learning_rate: float = 1e-4,
        train_scope: str = "head",
        head_params: int = _DEFAULT_HEAD_PARAMS,
    ):
        if not is_torch_backprop_available():
            raise RuntimeError(
                "PyTorch backprop unavailable: install 'torch' and 'onnx2torch'."
            )

        self.model_path = model_path
        self.input_width = int(input_width)
        self.input_height = int(input_height)
        self.output_format = output_format
        self.num_classes = int(num_classes)
        self.learning_rate = float(learning_rate)
        self.train_scope = train_scope

        # Convert ONNX -> torch.nn.Module (raises on failure; caller handles it).
        self.module = _onnx2torch_convert(model_path)
        self.module.train()

        # Select which parameters receive gradients.
        params = list(self.module.parameters())
        if not params:
            raise RuntimeError("Converted module exposes no trainable parameters.")
        if train_scope == "all":
            trainable = params
        else:  # 'head' (default): only the last few tensors near the output.
            for p in params:
                p.requires_grad_(False)
            trainable = params[-max(1, int(head_params)):]
        for p in trainable:
            p.requires_grad_(True)
        self._trainable_params = [p for p in trainable if p.requires_grad]

        self.optimizer = torch.optim.SGD(
            self._trainable_params, lr=self.learning_rate, momentum=0.9
        )
        self._initial_state = {
            k: v.detach().clone() for k, v in self.module.state_dict().items()
        }
        self.updates = 0
        logger.info(
            "[TorchStudent] Loaded %s into PyTorch — scope=%s, trainable tensors=%d, "
            "format=%s, classes=%d",
            model_path, train_scope, len(self._trainable_params),
            output_format, num_classes,
        )

    # ------------------------------------------------------------------
    # Forward / decode
    # ------------------------------------------------------------------
    def _to_input_tensor(self, blob: np.ndarray):
        """Convert a preprocessed NCHW float32 ``blob`` to a torch tensor."""
        return torch.from_numpy(np.ascontiguousarray(blob)).float()

    def _forward_raw(self, blob: np.ndarray):
        """Run the network, returning the first output tensor (with grad)."""
        x = self._to_input_tensor(blob)
        out = self.module(x)
        if isinstance(out, (list, tuple)):
            out = out[0]
        return out

    def _decode(self, raw):
        """Differentiable decode of a raw output tensor.

        Returns ``(boxes_xyxy, scores)`` in *input-pixel* coordinates where
        ``boxes_xyxy`` is ``[A, 4]`` and ``scores`` is ``[A, num_classes]``.
        Mirrors the NumPy post-processing in CustomONNX (without NMS).
        """
        out = raw
        if out.dim() == 3:
            out = out[0]  # drop batch

        if self.output_format == "yolox":
            # (anchors, C+5) expected; transpose if channels-first.
            if out.shape[1] != self.num_classes + 5 and out.shape[0] == self.num_classes + 5:
                out = out.t()
            out = self._decode_yolox_grid(out)
            cxcywh = out[:, :4]
            obj = torch.sigmoid(out[:, 4:5])
            cls = torch.sigmoid(out[:, 5:])
            scores = obj * cls
        else:
            # yolo11: (C+4, anchors) -> (anchors, C+4)
            expected = self.num_classes + 4
            if out.shape[0] == expected:
                out = out.t()
            elif out.shape[1] != expected and out.shape[0] != expected:
                # Unknown layout: assume channels-first.
                out = out.t()
            cxcywh = out[:, :4]
            scores = out[:, 4:]

        boxes_xyxy = self._cxcywh_to_xyxy(cxcywh)
        return boxes_xyxy, scores

    def _decode_yolox_grid(self, out):
        """Apply YOLOX grid + stride decoding to ``(anchors, C+5)`` (differentiable)."""
        strides = [8, 16, 32]
        grids = []
        expanded_strides = []
        for stride in strides:
            hsize = self.input_height // stride
            wsize = self.input_width // stride
            yv, xv = torch.meshgrid(
                torch.arange(hsize), torch.arange(wsize), indexing="ij"
            )
            grid = torch.stack((xv, yv), 2).reshape(-1, 2).float()
            grids.append(grid)
            expanded_strides.append(torch.full((grid.shape[0], 1), float(stride)))
        grid = torch.cat(grids, 0)
        strides_t = torch.cat(expanded_strides, 0)
        if grid.shape[0] != out.shape[0]:
            # Layout mismatch — fall back to treating boxes as already decoded.
            return out
        xy = (out[:, 0:2] + grid) * strides_t
        wh = torch.exp(out[:, 2:4]) * strides_t
        rest = out[:, 4:]
        return torch.cat([xy, wh, rest], dim=1)

    @staticmethod
    def _cxcywh_to_xyxy(cxcywh):
        cx, cy, w, h = cxcywh[:, 0], cxcywh[:, 1], cxcywh[:, 2], cxcywh[:, 3]
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2
        return torch.stack([x1, y1, x2, y2], dim=1)

    # ------------------------------------------------------------------
    # Distillation loss + training step
    # ------------------------------------------------------------------
    @staticmethod
    def _iou_matrix(boxes_a, boxes_b):
        """IoU between every box in ``boxes_a`` [N,4] and ``boxes_b`` [M,4]."""
        area_a = (boxes_a[:, 2] - boxes_a[:, 0]).clamp(min=0) * \
                 (boxes_a[:, 3] - boxes_a[:, 1]).clamp(min=0)
        area_b = (boxes_b[:, 2] - boxes_b[:, 0]).clamp(min=0) * \
                 (boxes_b[:, 3] - boxes_b[:, 1]).clamp(min=0)
        lt = torch.max(boxes_a[:, None, :2], boxes_b[None, :, :2])
        rb = torch.min(boxes_a[:, None, 2:], boxes_b[None, :, 2:])
        wh = (rb - lt).clamp(min=0)
        inter = wh[..., 0] * wh[..., 1]
        union = area_a[:, None] + area_b[None, :] - inter + 1e-9
        return inter / union

    def _build_loss(self, pred_boxes, pred_scores, teacher_boxes_in, teacher_classes):
        """Differentiable distillation loss between matched student/teacher boxes.

        The discrete assignment (which student anchor explains which teacher box)
        is computed without gradients; the per-pair box-regression and
        classification terms are differentiable and drive the backprop.
        """
        T = teacher_boxes_in.shape[0]
        A = pred_boxes.shape[0]
        if T == 0 or A == 0:
            return None

        with torch.no_grad():
            iou = self._iou_matrix(teacher_boxes_in, pred_boxes)  # [T, A]
            # Greedy unique assignment: highest IoU teacher->anchor first.
            assigned = [-1] * T
            taken = set()
            order = torch.argsort(iou.max(dim=1).values, descending=True).tolist()
            for t in order:
                row = iou[t]
                idx_sorted = torch.argsort(row, descending=True).tolist()
                for a in idx_sorted:
                    if a not in taken:
                        assigned[t] = a
                        taken.add(a)
                        break

        diag = float(np.hypot(self.input_width, self.input_height)) + 1e-6
        box_terms = []
        class_terms = []
        for t in range(T):
            a = assigned[t]
            if a < 0:
                continue
            tb = teacher_boxes_in[t]
            pb = pred_boxes[a]
            # Box regression: normalised L1 + (1 - IoU) of this pair.
            l1 = torch.abs(pb - tb).mean() / diag
            inter_lt = torch.max(pb[:2], tb[:2])
            inter_rb = torch.min(pb[2:], tb[2:])
            inter_wh = (inter_rb - inter_lt).clamp(min=0)
            inter = inter_wh[0] * inter_wh[1]
            area_p = (pb[2] - pb[0]).clamp(min=0) * (pb[3] - pb[1]).clamp(min=0)
            area_t = (tb[2] - tb[0]).clamp(min=0) * (tb[3] - tb[1]).clamp(min=0)
            iou_pair = inter / (area_p + area_t - inter + 1e-9)
            box_terms.append(l1 + (1.0 - iou_pair))

            # Classification: push the matched anchor toward the teacher class.
            target = torch.zeros(self.num_classes)
            cls_id = int(teacher_classes[t]) if teacher_classes is not None else 0
            if 0 <= cls_id < self.num_classes:
                target[cls_id] = 1.0
            prob = pred_scores[a].clamp(1e-6, 1.0 - 1e-6)
            class_terms.append(F.binary_cross_entropy(prob, target))

        if not box_terms:
            return None
        loss = torch.stack(box_terms).mean()
        if class_terms:
            loss = loss + _CLASS_LOSS_WEIGHT * torch.stack(class_terms).mean()
        return loss

    def train_step(
        self,
        blob: np.ndarray,
        teacher_boxes_orig: List,
        teacher_classes: List,
        orig_w: int,
        orig_h: int,
    ) -> Optional[float]:
        """One real backprop step through the network. Returns the loss value.

        ``blob`` is the preprocessed NCHW input. ``teacher_boxes_orig`` are
        ``[x1,y1,x2,y2]`` boxes in *original image* pixels; they are scaled into
        the network input space to match the decoded student boxes.
        """
        if len(teacher_boxes_orig) == 0:
            return None
        self.module.train()
        raw = self._forward_raw(blob)
        pred_boxes, pred_scores = self._decode(raw)

        sx = self.input_width / max(1, int(orig_w))
        sy = self.input_height / max(1, int(orig_h))
        scale = torch.tensor([sx, sy, sx, sy], dtype=pred_boxes.dtype)
        teacher_in = torch.tensor(
            np.asarray(teacher_boxes_orig, dtype=np.float32)
        ).reshape(-1, 4) * scale

        loss = self._build_loss(pred_boxes, pred_scores, teacher_in, teacher_classes)
        if loss is None:
            return None

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.updates += 1
        return float(loss.detach().cpu().item())

    # ------------------------------------------------------------------
    # Inference with the (updated) weights
    # ------------------------------------------------------------------
    def forward_numpy(self, blob: np.ndarray) -> np.ndarray:
        """Run a no-grad forward pass and return the raw output as NumPy.

        The result can be fed straight into CustomONNX's ``_postprocess_*`` so the
        displayed detections reflect the latest trained weights and use exactly
        the same decoding/NMS as the rest of the application.
        """
        self.module.eval()
        with torch.no_grad():
            out = self._forward_raw(blob)
        return out.detach().cpu().numpy()

    def reset(self):
        """Restore the original (pre-training) weights and optimizer state."""
        self.module.load_state_dict(self._initial_state)
        self.optimizer = torch.optim.SGD(
            self._trainable_params, lr=self.learning_rate, momentum=0.9
        )
        self.updates = 0

    def export_onnx(self, output_path: str) -> str:
        """Export the current (trained) weights back to an ONNX file."""
        self.module.eval()
        dummy = torch.zeros(
            1, 3, self.input_height, self.input_width, dtype=torch.float32
        )
        torch.onnx.export(
            self.module, dummy, output_path,
            input_names=["images"], output_names=["output"],
            opset_version=12, dynamic_axes=None,
        )
        return output_path
