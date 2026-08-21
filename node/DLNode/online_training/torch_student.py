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
YOLOv8/v11, boxes already in input pixels), ``yolox`` (grid + objectness) and
``nanodet`` (GFL/DFL distribution heads, single concatenated output).
"""

import contextlib
import logging
import math
import os
import tempfile
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# NanoDet feature-pyramid stride sets: NanoDet-Plus uses 4 levels (8/16/32/64),
# the original NanoDet-m only 3 (8/16/32). The first whose total anchor count
# matches the network output is selected.
_NANODET_STRIDE_SETS: Tuple[Tuple[int, ...], ...] = ((8, 16, 32, 64), (8, 16, 32))

# ---------------------------------------------------------------------------
# Catalog of student models validated to be compatible with onnx2torch ≥ 0.0.30
# and the differentiable decode implemented in this module.
#
# ``download_url`` is left empty until the models are hosted; populate it and
# call ``student_models_registry.download_model(url, dest_path)`` to retrieve
# the ONNX file and register it for the OnlineTraining node.
# ---------------------------------------------------------------------------
_COCO_80_CLASS_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant",
    "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]
_COCO_CLASS_NAMES_DICT = {str(i): n for i, n in enumerate(_COCO_80_CLASS_NAMES)}

VALIDATED_STUDENT_MODELS = [
    {
        "name": "yolov8n-coco",
        "description": (
            "YOLOv8 nano — 80 COCO classes, 640×640. "
            "Export: yolo export model=yolov8n.pt format=onnx opset=12"
        ),
        "output_format": "yolo11",   # YOLOv8 and YOLO11 share the same head format
        "num_classes": 80,
        "input_width": 640,
        "input_height": 640,
        "download_url": "",          # populate when hosted
        "class_names": _COCO_CLASS_NAMES_DICT,
    },
    {
        "name": "yolov8s-coco",
        "description": (
            "YOLOv8 small — 80 COCO classes, 640×640. "
            "Export: yolo export model=yolov8s.pt format=onnx opset=12"
        ),
        "output_format": "yolo11",
        "num_classes": 80,
        "input_width": 640,
        "input_height": 640,
        "download_url": "",
        "class_names": _COCO_CLASS_NAMES_DICT,
    },
    {
        "name": "nanodet-plus-m_416",
        "description": (
            "NanoDet-Plus-m — 80 COCO classes, 416×416. "
            "Download: github.com/RangiLyu/nanodet/releases"
        ),
        "output_format": "nanodet",
        "num_classes": 80,
        "input_width": 416,
        "input_height": 416,
        "download_url": "",
        "class_names": _COCO_CLASS_NAMES_DICT,
    },
]
"""Catalog of student models validated with onnx2torch (≥ 0.0.30) and the
differentiable decode in this module.  Each entry follows the registry schema
and can be registered directly via ``student_models_registry.save_entry``
after the ONNX file is obtained."""


def nanodet_anchor_grid(input_width: int, input_height: int,
                        num_anchors: Optional[int] = None):
    """Precompute NanoDet anchor centres + per-anchor strides (FCOS-style grid).

    NanoDet's GFL/DFL head predicts, for every anchor point, four side distances
    (left, top, right, bottom) as the expectation of a softmax distribution. The
    anchor point is the **centre** of a grid cell, ``(x + 0.5) * stride``, with
    the grid built per feature level (stride) in row-major (``indexing='ij'``)
    order — identical to :meth:`CustomONNX._postprocess_nanodet` so the anchor
    ordering matches the raw network output.

    The number of cells per level is ``ceil(input / stride)``: NanoDet-Plus pads
    the feature map up (e.g. 416/64 -> 7, not 6), so floor division undercounts
    the anchors (3585 vs 3598 for nanodet-plus-m_416) and breaks the decode.

    Parameters
    ----------
    num_anchors : int, optional
        When given, the stride set whose total anchor count equals this value is
        selected (4-stride NanoDet-Plus first, then 3-stride NanoDet-m). This
        keeps the decode aligned with the actual student output.

    Returns
    -------
    (centers, strides) : (np.ndarray[A, 2], np.ndarray[A, 1]) float32
        Anchor centres ``(cx, cy)`` in input-pixel space and the matching stride
        of each anchor.
    """
    def _build(strides_list):
        centers = []
        stride_col = []
        for s in strides_list:
            n_h = math.ceil(int(input_height) / s)
            n_w = math.ceil(int(input_width) / s)
            if n_h <= 0 or n_w <= 0:
                continue
            yv, xv = np.meshgrid(np.arange(n_h), np.arange(n_w), indexing="ij")
            cx = (xv.ravel() + 0.5) * s
            cy = (yv.ravel() + 0.5) * s
            centers.append(np.stack([cx, cy], axis=1))
            stride_col.append(np.full(n_h * n_w, float(s)))
        if not centers:
            return (np.zeros((0, 2), dtype=np.float32),
                    np.zeros((0, 1), dtype=np.float32))
        c = np.concatenate(centers, axis=0).astype(np.float32)
        st = np.concatenate(stride_col, axis=0).astype(np.float32).reshape(-1, 1)
        return c, st

    built = []
    for strides_list in _NANODET_STRIDE_SETS:
        c, st = _build(strides_list)
        if num_anchors is not None and c.shape[0] == num_anchors:
            return c, st
        built.append((c, st))
    # No exact match (or num_anchors unknown): prefer the 3-stride layout, the
    # most common for the mono-output NanoDet export.
    if not built:
        return (np.zeros((0, 2), dtype=np.float32),
                np.zeros((0, 1), dtype=np.float32))
    return built[-1]



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


# Output formats for which the differentiable decode (``TorchStudent._decode``)
# and the matched distillation loss are implemented. ``nanodet`` is the
# single-output GFL/DFL export (one concatenated tensor). Detectors using a
# different decode (e.g. ``nanodet_multi`` with separate per-level heads, or
# ``ssd``) must NOT take the PyTorch backprop path: their raw outputs cannot be
# decoded here, so it would yield no student boxes and no real weight updates.
SUPPORTED_FORMATS = ("yolo11", "yolox", "nanodet")


def is_format_supported(output_format: str) -> bool:
    """True when ``output_format`` can be decoded/trained by :class:`TorchStudent`."""
    return str(output_format).lower() in SUPPORTED_FORMATS


def probe_pytorch_compatibility(model_path: str, output_format: str) -> dict:
    """Check whether a model can use the PyTorch backprop path.

    Performs a step-by-step probe:

    1. Verifies that PyTorch and ``onnx2torch`` are installed.
    2. Verifies that the output format is supported by the differentiable
       decode.
    3. Attempts to convert the model with ``onnx2torch`` and counts trainable
       parameters.

    All steps are defensive — the function never raises.

    Returns
    -------
    dict with keys:
        compatible : bool
            True iff real gradient backprop can be used for this model.
        reason : str
            Human-readable explanation (especially useful when ``compatible``
            is False).
        torch_available, onnx2torch_available, format_supported,
        conversion_ok : bool — individual step outcomes.
        num_trainable_params : int — trainable tensors found after conversion
            (0 when conversion failed).
    """
    result: dict = {
        'compatible': False,
        'reason': '',
        'torch_available': _TORCH_AVAILABLE,
        'onnx2torch_available': _ONNX2TORCH_AVAILABLE,
        'format_supported': is_format_supported(output_format),
        'conversion_ok': False,
        'num_trainable_params': 0,
    }

    if not _TORCH_AVAILABLE:
        result['reason'] = (
            "PyTorch not installed. Run `pip install torch` (≥2.0) to enable "
            "real gradient backprop. Falling back to the affine correction head."
        )
        return result

    if not _ONNX2TORCH_AVAILABLE:
        result['reason'] = (
            "onnx2torch not installed. Run `pip install onnx2torch` (≥0.0.30) "
            "to convert ONNX models to trainable PyTorch modules. "
            "Falling back to the affine correction head."
        )
        return result

    if not is_format_supported(output_format):
        result['reason'] = (
            f"Output format '{output_format}' is not supported by the "
            f"differentiable decode (supported: {', '.join(SUPPORTED_FORMATS)}). "
            "Re-export the model in a supported format or choose a model from "
            "VALIDATED_STUDENT_MODELS."
        )
        return result

    try:
        module = _convert_onnx_to_torch(model_path)
        n_params = len(list(module.parameters()))
        result['conversion_ok'] = True
        result['compatible'] = True
        result['num_trainable_params'] = n_params
        result['reason'] = (
            f"PyTorch backprop available — {n_params} trainable parameter "
            f"tensor(s) found after onnx2torch conversion."
        )
    except Exception as exc:
        result['reason'] = (
            f"onnx2torch conversion failed: {type(exc).__name__}: {exc}. "
            "Common fixes: (a) re-export with opset_version=11 or 12; "
            "(b) use a model from VALIDATED_STUDENT_MODELS; "
            "(c) the affine correction head remains active as a fallback."
        )

    return result


def _convert_onnx_to_torch(model_path: str):
    """Convert an ONNX model to a ``torch.nn.Module`` with ``onnx2torch``.

    ``onnx2torch.convert`` (and the ONNX shape-inference it triggers) may try to
    create temporary files **next to the model file**. When the model lives in a
    read-only directory this fails with ``PermissionError`` and would otherwise
    disable the whole PyTorch backprop path. To stay robust we first attempt the
    plain conversion and, on any ``OSError`` (e.g. ``[Errno 13] Permission
    denied``), retry by loading the model into memory and running the conversion
    from a writable temporary working directory so the temp files land there.
    """
    try:
        return _onnx2torch_convert(model_path)
    except OSError as exc:
        logger.warning(
            "[TorchStudent] onnx2torch could not write next to the model (%s); "
            "retrying conversion from a writable temporary directory.", exc,
        )

    # Fallback: load the model (resolving any external data) into memory and run
    # the conversion with the working directory pointed at the system temp dir,
    # so onnx2torch/onnx never need to write into the read-only model directory.
    import onnx  # local import: onnx2torch already depends on onnx

    model_proto = onnx.load(model_path)
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="onnx2torch_") as tmp_dir:
        try:
            os.chdir(tmp_dir)
            return _onnx2torch_convert(model_proto)
        finally:
            with contextlib.suppress(OSError):
                os.chdir(original_cwd)


# Number of trailing parameter tensors trained when ``train_scope='head'``.
_DEFAULT_HEAD_PARAMS = 8

# Default backprop depth expressed as a number of trailing parameter tensors.
# 0  → no PyTorch backprop (fall back to affine head).
# 1‥N → train the last N parameter tensors.
# A special sentinel value of -1 means "train all" (equivalent to train_scope='all').
_BACKPROP_DEPTH_ALL = -1

# Adaptive class-loss weight phases (keyed by update count thresholds).
# Phase 1 (updates < 100): focus on localisation.
# Phase 2 (100 ≤ updates < 500): balanced.
# Phase 3 (updates ≥ 500): refine classification.
_CLASS_LOSS_PHASES = ((100, 0.3), (500, 1.0), (float("inf"), 2.0))

# Temperature scheduling for soft-label distillation.
# T decays linearly from T_INIT to 1.0 over T_STEPS update steps.
_TEMPERATURE_INIT = 4.0
_TEMPERATURE_STEPS = 500

# Weight for the negative-mining background BCE loss applied to unmatched
# student anchors.  Kept deliberately small (0.2) so hard negatives regularise
# the student without dominating the foreground distillation signal.
_NEG_WEIGHT = 0.2


class TorchStudent:
    """Trainable PyTorch student converted from an ONNX detector.

    Parameters
    ----------
    model_path : str
        Path to the student ONNX model.
    input_width, input_height : int
        Network input resolution.
    output_format : str
        ``'yolo11'``, ``'yolox'`` or ``'nanodet'``.
    num_classes : int
        Number of detection classes.
    learning_rate : float
        Optimizer learning rate.
    train_scope : str
        ``'head'`` to train only the last few parameter tensors (detection
        heads), or ``'all'`` to fine-tune the whole backbone + heads.
        Ignored when ``backprop_depth`` is set to a value other than ``None``.
    backprop_depth : int or None
        Number of trailing parameter tensors to train.  ``0`` disables
        PyTorch backprop entirely (caller should use the affine-head path).
        Positive values train the last N tensors. ``-1`` trains all parameters.
        ``None`` (default) falls back to the ``train_scope``/``head_params``
        behaviour for backwards compatibility.
    head_params : int
        Number of trailing tensors used when ``train_scope='head'`` and
        ``backprop_depth`` is ``None``.
    nanodet_reg_first : bool
        NanoDet channel layout: ``False`` (default) for ``[classes, reg]``,
        ``True`` for ``[reg, classes]``.
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
        backprop_depth: Optional[int] = None,
        nanodet_reg_first: bool = False,
        device: str = "cpu",
    ):
        if not is_torch_backprop_available():
            raise RuntimeError(
                "PyTorch backprop unavailable: install 'torch' and 'onnx2torch'."
            )
        if not is_format_supported(output_format):
            raise RuntimeError(
                f"PyTorch backprop does not support output_format "
                f"'{output_format}' (supported: {', '.join(SUPPORTED_FORMATS)})."
            )

        self.model_path = model_path
        self.input_width = int(input_width)
        self.input_height = int(input_height)
        self.output_format = output_format
        self.num_classes = int(num_classes)
        self.learning_rate = float(learning_rate)
        self.train_scope = train_scope
        self._head_params = int(head_params)
        # Resolve backprop_depth from the (backprop_depth, train_scope, head_params) trio.
        # backprop_depth=None → keep legacy train_scope behaviour.
        if backprop_depth is None:
            if train_scope == "all":
                self._backprop_depth = _BACKPROP_DEPTH_ALL
            else:
                self._backprop_depth = max(1, int(head_params))
        else:
            self._backprop_depth = int(backprop_depth)
        # Resolve the device string, falling back to CPU when the requested
        # device (e.g. 'cuda') is not available.
        if _TORCH_AVAILABLE:
            requested = torch.device(device)
            if requested.type == "cuda" and not torch.cuda.is_available():
                logger.warning(
                    "[TorchStudent] CUDA requested but not available — falling back to CPU."
                )
                requested = torch.device("cpu")
            self.device = requested
        else:
            self.device = "cpu"
        # NanoDet GFL/DFL: channel layout ([classes, reg] vs [reg, classes]) and
        # a small cache of the (anchor centres, strides) grid keyed by anchor
        # count, built lazily from the first decoded tensor.
        self.nanodet_reg_first = bool(nanodet_reg_first)
        self._nanodet_grid_cache = {}

        # Convert ONNX -> torch.nn.Module (raises on failure; caller handles it).
        # Resilient to read-only model directories (see ``_convert_onnx_to_torch``).
        self.module = _convert_onnx_to_torch(model_path)
        self.module.to(self.device)
        self.module.train()

        # Select which parameters receive gradients.
        params = list(self.module.parameters())
        if not params:
            raise RuntimeError("Converted module exposes no trainable parameters.")
        self._all_params = params
        self._apply_backprop_depth(self._backprop_depth)

        self.optimizer = torch.optim.AdamW(
            self._trainable_params, lr=self.learning_rate, weight_decay=1e-4
        )
        # Cosine-annealing restarts every T_0 update steps so the optimiser
        # can escape flat regions in online learning.
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer, T_0=200
        )
        self._initial_state = {
            k: v.detach().clone() for k, v in self.module.state_dict().items()
        }
        self.updates = 0
        logger.info(
            "[TorchStudent] Loaded %s into PyTorch — depth=%s, trainable tensors=%d, "
            "format=%s, classes=%d, device=%s",
            model_path, self._backprop_depth, len(self._trainable_params),
            output_format, num_classes, self.device,
        )

    # ------------------------------------------------------------------
    # Backprop depth management
    # ------------------------------------------------------------------

    def _apply_backprop_depth(self, depth: int) -> None:
        """Apply ``depth`` to control which parameters receive gradients.

        Parameters
        ----------
        depth : int
            ``-1`` (or any negative value) → all params.
            ``0`` → none (inference only).
            Positive → last ``depth`` parameter tensors.
        """
        params = self._all_params
        for p in params:
            p.requires_grad_(False)
        if depth < 0:
            # Any negative value means "train all" (-1 is the documented sentinel).
            trainable = params
        elif depth == 0:
            trainable = []
        else:
            trainable = params[-min(depth, len(params)):]
        for p in trainable:
            p.requires_grad_(True)
        self._trainable_params = [p for p in trainable if p.requires_grad]

    def set_backprop_depth(self, depth: int) -> None:
        """Change the backprop depth at runtime without reloading the model.

        Reapplies ``requires_grad_()`` flags and rebuilds the optimizer
        param-groups so the new depth takes effect on the next training step.

        Parameters
        ----------
        depth : int
            Number of trailing parameter tensors to train.
            ``-1`` trains all, ``0`` disables PyTorch backprop.
        """
        depth = int(depth)
        if depth == self._backprop_depth:
            return
        self._backprop_depth = depth
        self._apply_backprop_depth(depth)
        # Rebuild optimizer param_groups with the new trainable set.
        if self._trainable_params:
            self.optimizer = torch.optim.AdamW(
                self._trainable_params, lr=self.learning_rate, weight_decay=1e-4
            )
            self.scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
                self.optimizer, T_0=200
            )
        logger.info(
            "[TorchStudent] backprop_depth updated to %d — trainable tensors: %d",
            depth, len(self._trainable_params),
        )

    @property
    def backprop_depth(self) -> int:
        """Current backprop depth (number of trailing trainable tensors, or -1 for all)."""
        return self._backprop_depth

    # ------------------------------------------------------------------
    # Forward / decode
    # ------------------------------------------------------------------
    def _to_input_tensor(self, blob: np.ndarray):
        """Convert a preprocessed NCHW float32 ``blob`` to a torch tensor."""
        return torch.from_numpy(np.ascontiguousarray(blob)).float().to(self.device)

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
        elif self.output_format == "nanodet":
            return self._decode_nanodet(out)
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

    def _nanodet_grid(self, num_anchors: int):
        """Return cached ``(centers[A,2], strides[A,1])`` torch tensors."""
        cached = self._nanodet_grid_cache.get(num_anchors)
        if cached is None:
            centers_np, strides_np = nanodet_anchor_grid(
                self.input_width, self.input_height, num_anchors)
            centers = torch.from_numpy(centers_np).float().to(self.device)
            strides = torch.from_numpy(strides_np).float().to(self.device)
            cached = (centers, strides)
            self._nanodet_grid_cache[num_anchors] = cached
        return cached

    def _decode_nanodet(self, out):
        """Differentiable NanoDet GFL/DFL decode of ``(anchors, channels)``.

        Each of the 4 box sides is the expectation of a softmax distribution over
        ``reg_max+1`` bins; boxes are anchor-centre ± distance*stride. Mirrors
        :meth:`CustomONNX._postprocess_nanodet` (without NMS), so the anchor
        ordering and geometry match the inference path.
        """
        a = out.shape[0]
        total = out.shape[1]
        reg_channels = total - self.num_classes
        if reg_channels <= 0 or reg_channels % 4 != 0:
            raise RuntimeError(
                f"NanoDet decode: cannot infer reg_max from channels={total}, "
                f"num_classes={self.num_classes}."
            )
        reg_bins = reg_channels // 4

        if self.nanodet_reg_first:
            reg_flat = out[:, :reg_channels]
            cls_raw = out[:, reg_channels:]
        else:
            cls_raw = out[:, :self.num_classes]
            reg_flat = out[:, self.num_classes:]

        scores = torch.sigmoid(cls_raw)

        reg = reg_flat.reshape(a, 4, reg_bins)
        reg_sm = torch.softmax(reg, dim=2)
        proj = torch.arange(reg_bins, dtype=reg_sm.dtype, device=reg_sm.device)
        distances = (reg_sm * proj).sum(dim=2)  # [A,4] = left, top, right, bottom

        centers, strides = self._nanodet_grid(a)
        centers = centers.to(out.dtype)
        strides = strides.to(out.dtype)
        cx = centers[:, 0]
        cy = centers[:, 1]
        st = strides[:, 0]
        x1 = cx - distances[:, 0] * st
        y1 = cy - distances[:, 1] * st
        x2 = cx + distances[:, 2] * st
        y2 = cy + distances[:, 3] * st
        boxes_xyxy = torch.stack([x1, y1, x2, y2], dim=1)
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
            grid = torch.stack((xv, yv), 2).reshape(-1, 2).float().to(self.device)
            grids.append(grid)
            expanded_strides.append(
                torch.full((grid.shape[0], 1), float(stride), device=self.device)
            )
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

    def _build_loss(self, pred_boxes, pred_scores, teacher_boxes_in, teacher_classes,
                    teacher_scores=None):
        """Differentiable distillation loss between matched student/teacher boxes.

        The discrete assignment (which student anchor explains which teacher box)
        is computed without gradients; the per-pair box-regression and
        classification terms are differentiable and drive the backprop.

        Improvements over the original implementation:

        * **GIoU** replaces (1 - IoU) so unmatched boxes still receive a
          non-zero gradient even when IoU = 0.
        * **Soft labels** use the teacher confidence score for the matched class
          instead of a hard 1.0, and **temperature scaling** (T decaying from 4
          to 1 over 500 steps) is applied to the student logits before BCE so
          the student learns the teacher's confidence calibration.
        * **Adaptive class weight** automatically shifts emphasis from
          localisation (early) to classification (later) based on update count.
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

        # Adaptive class weight: phase-1 → localisation, phase-3 → classification.
        class_weight = _CLASS_LOSS_PHASES[-1][1]
        for threshold, weight in _CLASS_LOSS_PHASES:
            if self.updates < threshold:
                class_weight = weight
                break

        # Temperature schedule: linear decay T_INIT → 1.0 over T_STEPS updates.
        t_ratio = min(1.0, self.updates / max(1, _TEMPERATURE_STEPS))
        temperature = max(1.0, _TEMPERATURE_INIT - t_ratio * (_TEMPERATURE_INIT - 1.0))

        diag = float(np.hypot(self.input_width, self.input_height)) + 1e-6
        box_terms = []
        class_terms = []
        for t in range(T):
            a = assigned[t]
            if a < 0:
                continue
            tb = teacher_boxes_in[t]
            pb = pred_boxes[a]

            # ── Box regression: normalised L1 + (1 − GIoU) ──────────────────
            l1 = torch.abs(pb - tb).mean() / diag

            # GIoU = IoU − |enclosing \ union| / |enclosing|
            inter_lt = torch.max(pb[:2], tb[:2])
            inter_rb = torch.min(pb[2:], tb[2:])
            inter_wh = (inter_rb - inter_lt).clamp(min=0)
            inter = inter_wh[0] * inter_wh[1]
            area_p = (pb[2] - pb[0]).clamp(min=0) * (pb[3] - pb[1]).clamp(min=0)
            area_t = (tb[2] - tb[0]).clamp(min=0) * (tb[3] - tb[1]).clamp(min=0)
            union = area_p + area_t - inter + 1e-9
            iou_pair = inter / union
            enc_lt = torch.min(pb[:2], tb[:2])
            enc_rb = torch.max(pb[2:], tb[2:])
            enc_wh = (enc_rb - enc_lt).clamp(min=0)
            enc_area = enc_wh[0] * enc_wh[1] + 1e-9
            giou = iou_pair - (enc_area - union) / enc_area
            box_terms.append(l1 + (1.0 - giou))

            # ── Classification: soft targets + temperature scaling ────────────
            target = torch.zeros(self.num_classes, device=self.device)
            cls_id = int(teacher_classes[t]) if teacher_classes is not None else 0
            if 0 <= cls_id < self.num_classes:
                # Use teacher confidence as soft label when available.
                soft_val = float(teacher_scores[t]) if (
                    teacher_scores is not None and t < len(teacher_scores)
                ) else 1.0
                target[cls_id] = float(np.clip(soft_val, 0.0, 1.0))

            # Apply temperature to student logits before BCE (temp > 1 → softer).
            prob = (pred_scores[a] / temperature).sigmoid().clamp(1e-6, 1.0 - 1e-6)
            class_terms.append(F.binary_cross_entropy(prob, target))

        if not box_terms:
            return None
        loss = torch.stack(box_terms).mean()
        if class_terms:
            loss = loss + class_weight * torch.stack(class_terms).mean()

        # ── Negative mining ─────────────────────────────────────────────────
        # FP student predictions (no teacher match) receive a background BCE
        # loss.  We sample up to max(T*3, 9) hard negatives — those with the
        # highest predicted class score — mirroring the hard-negative strategy
        # in SSD/FCOS without exploding compute for large anchor sets (e.g.
        # YOLO with ~8400 anchors).
        unmatched_anchors = [a for a in range(A) if a not in taken]
        if unmatched_anchors and _NEG_WEIGHT > 0.0:
            max_neg = max(T * 3, 9)
            sorted_neg = sorted(
                unmatched_anchors,
                key=lambda a: float(pred_scores[a].max().detach()),
                reverse=True,
            )
            hard_negs = sorted_neg[:max_neg]
            bg_target = torch.zeros(self.num_classes, device=self.device)
            neg_terms = []
            for a in hard_negs:
                prob = (pred_scores[a] / temperature).sigmoid().clamp(1e-6, 1.0 - 1e-6)
                neg_terms.append(F.binary_cross_entropy(prob, bg_target))
            if neg_terms:
                loss = loss + _NEG_WEIGHT * class_weight * torch.stack(neg_terms).mean()

        return loss

    def train_step(
        self,
        blob: np.ndarray,
        teacher_boxes_orig: List,
        teacher_classes: List,
        orig_w: int,
        orig_h: int,
        teacher_scores: Optional[List] = None,
    ) -> Optional[float]:
        """One real backprop step through the network. Returns the loss value.

        ``blob`` is the preprocessed NCHW input. ``teacher_boxes_orig`` are
        ``[x1,y1,x2,y2]`` boxes in *original image* pixels; they are scaled into
        the network input space to match the decoded student boxes.

        ``teacher_scores`` (optional) are the teacher confidence scores for each
        box, used as soft labels in the classification loss.
        """
        if len(teacher_boxes_orig) == 0:
            return None
        if not self._trainable_params:
            # backprop_depth=0: inference-only, no gradient update.
            return None
        self.module.train()
        raw = self._forward_raw(blob)
        pred_boxes, pred_scores = self._decode(raw)

        scale = self._teacher_input_scale(orig_w, orig_h, pred_boxes.dtype)
        teacher_in = torch.tensor(
            np.asarray(teacher_boxes_orig, dtype=np.float32)
        ).reshape(-1, 4).to(self.device) * scale

        loss = self._build_loss(pred_boxes, pred_scores, teacher_in, teacher_classes,
                                teacher_scores=teacher_scores)
        if loss is None:
            return None

        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping prevents divergence on frames with large loss spikes.
        torch.nn.utils.clip_grad_norm_(self._trainable_params, max_norm=1.0)
        self.optimizer.step()
        self.scheduler.step()
        self.updates += 1
        return float(loss.detach().cpu().item())

    def _teacher_input_scale(self, orig_w: int, orig_h: int, dtype):
        """Scale factor mapping original-image boxes into network-input space.

        NanoDet preprocessing is letterbox (aspect-ratio preserving, top-left
        aligned), so a single uniform ``ratio`` maps original pixels to input
        pixels. yolo11/yolox keep the historical per-axis stretch mapping.
        """
        if self.output_format == "nanodet":
            ratio = min(self.input_height / max(1, int(orig_h)),
                        self.input_width / max(1, int(orig_w)))
            return torch.tensor([ratio, ratio, ratio, ratio], dtype=dtype, device=self.device)
        sx = self.input_width / max(1, int(orig_w))
        sy = self.input_height / max(1, int(orig_h))
        return torch.tensor([sx, sy, sx, sy], dtype=dtype, device=self.device)

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
        self.optimizer = torch.optim.AdamW(
            self._trainable_params, lr=self.learning_rate, weight_decay=1e-4
        )
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer, T_0=200
        )
        self.updates = 0

    def export_onnx(self, output_path: str) -> str:
        """Export the current (trained) weights back to an ONNX file."""
        self.module.eval()
        dummy = torch.zeros(
            1, 3, self.input_height, self.input_width, dtype=torch.float32,
            device=self.device,
        )
        torch.onnx.export(
            self.module, dummy, output_path,
            input_names=["images"], output_names=["output"],
            opset_version=12, dynamic_axes=None,
        )
        return output_path
