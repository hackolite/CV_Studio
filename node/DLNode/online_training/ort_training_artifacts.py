#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""End-to-end ORT-Training backprop for the distillation student.

This module wires the *real* onnxruntime-training backprop path described in the
plan. Plain ``onnxruntime`` is an inference engine (forward only, frozen
weights); to obtain gradients the **whole loss path must live inside one ONNX
graph** so ORT Training can auto-differentiate it. The discrete teacher↔student
assignment (Hungarian/greedy) is *not* differentiable, so it is computed
out-of-graph in NumPy and only the matched pairs are fed to the graph — exactly
the per-pair, differentiable terms (box L1 + (1 − IoU) + class BCE) drive the
weight update.

The pipeline is:

1. :func:`build_student_loss_graph` — append a **differentiable decode** of the
   raw student output (``cxcywh`` → ``xyxy``, no NMS) followed by the matched
   distillation loss, producing a single ``total_loss`` scalar.
2. :func:`merge_student_with_loss` — splice that graph onto the student ONNX so
   the student's trainable weights feed the loss.
3. :func:`generate_training_artifacts` — call
   ``onnxruntime.training.artifacts.generate_artifacts`` to emit the
   ``training``/``eval``/``optimizer`` models and the ``checkpoint``.
4. :func:`greedy_match_anchors` — NumPy greedy unique matcher used at run time to
   pick which student anchor explains each teacher box.

Everything degrades gracefully: when ``onnx`` or ``onnxruntime.training`` is not
installed the relevant helpers raise a clear ``RuntimeError`` and the caller
(:class:`~node.DLNode.online_training.student_trainer.StudentTrainer`) falls back
to the PyTorch path or the affine correction head.
"""

import logging
import math
import os
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy dependencies — importing this module must never fail.
# ---------------------------------------------------------------------------
try:
    import onnx
    from onnx import TensorProto, helper, numpy_helper
    _ONNX_AVAILABLE = True
except Exception:  # pragma: no cover - onnx not installed
    onnx = None
    TensorProto = helper = numpy_helper = None
    _ONNX_AVAILABLE = False

_ORT_TRAINING_AVAILABLE = False
try:  # pragma: no cover - exercised only with onnxruntime-training
    from onnxruntime.training import artifacts as _ort_artifacts
    _ORT_TRAINING_AVAILABLE = True
except Exception:  # pragma: no cover
    _ort_artifacts = None


def is_ort_training_available() -> bool:
    """True when both ``onnx`` and ``onnxruntime.training`` can be used."""
    return _ONNX_AVAILABLE and _ORT_TRAINING_AVAILABLE


# Weight of the classification BCE term relative to the box term (matches the
# PyTorch path in :mod:`torch_student` so both backends behave the same).
_CLASS_LOSS_WEIGHT = 1.0


# ---------------------------------------------------------------------------
# 1. Differentiable decode + matched distillation loss graph (plan section C)
# ---------------------------------------------------------------------------
def build_student_loss_graph(
    num_classes: int = 80,
    input_width: int = 640,
    input_height: int = 640,
    output_format: str = "yolo11",
    raw_input_name: str = "raw_output",
    transpose_output: bool = True,
    class_weight: float = _CLASS_LOSS_WEIGHT,
    reg_max: int = 7,
    nanodet_reg_first: bool = False,
    num_anchors: Optional[int] = None,
):
    """Build the differentiable decode + matched-pair distillation loss model.

    The graph consumes the *raw* student output plus the out-of-graph match
    (anchor indices + teacher targets) and produces a single ``total_loss``
    scalar that ORT Training can back-propagate through the student weights.

    Inputs
    ------
    raw_output : float32
        Raw student network output. For ``yolo11`` the canonical Ultralytics
        layout ``[1, C+4, A]`` is expected (set ``transpose_output`` to control
        the leading transpose). For ``yolox`` a ``[1, A, C+5]`` layout is used.
        For ``nanodet`` a ``[1, A, C + 4*(reg_max+1)]`` GFL/DFL layout is used.
    anchor_idx : int64 ``[T]``
        Index of the student anchor matched to each teacher box (NumPy match).
    teacher_boxes_in : float32 ``[T, 4]``
        Teacher boxes (``x1,y1,x2,y2``) in **network-input** pixel space.
    teacher_onehot : float32 ``[T, C]``
        One-hot (or soft) teacher class target per matched box.

    NanoDet parameters
    ------------------
    reg_max : int
        Maximum bin index of the DFL distribution; each side distance is the
        expectation over ``reg_max+1`` softmax bins.
    nanodet_reg_first : bool
        Channel layout of the raw output: ``False`` (default) for
        ``[classes, reg]``, ``True`` for ``[reg, classes]``.
    num_anchors : int, optional
        Anchor count of the student output, used to select the NanoDet stride
        set when building the constant anchor grid.

    Outputs
    -------
    total_loss, loss_box, loss_class : float32 scalars

    Returns
    -------
    onnx.ModelProto
    """
    if not _ONNX_AVAILABLE:
        raise RuntimeError("onnx package required to build the loss graph")
    if output_format not in ("yolo11", "yolox", "nanodet"):
        raise ValueError(f"unsupported output_format for ORT loss: {output_format}")

    nodes = []
    inits = []

    # ── Constants ────────────────────────────────────────────────────────────
    eps = 1e-6
    diag = float(np.hypot(input_width, input_height)) + 1e-6
    inits.append(numpy_helper.from_array(np.array(eps, dtype=np.float32), "ld_eps"))
    inits.append(numpy_helper.from_array(np.array(1.0 - eps, dtype=np.float32), "ld_one_m_eps"))
    inits.append(numpy_helper.from_array(np.array(1.0, dtype=np.float32), "ld_one"))
    inits.append(numpy_helper.from_array(np.array(2.0, dtype=np.float32), "ld_two"))
    inits.append(numpy_helper.from_array(np.array(diag, dtype=np.float32), "ld_diag"))
    inits.append(numpy_helper.from_array(np.array(class_weight, dtype=np.float32), "ld_cls_w"))
    inits.append(numpy_helper.from_array(np.array([0], dtype=np.int64), "ld_axis0"))

    # ── Decode raw → (anchors, C+4 or C+5) ───────────────────────────────────
    if output_format == "yolo11":
        # [1, C+4, A] → [1, A, C+4] → [A, C+4]
        if transpose_output:
            nodes.append(helper.make_node("Transpose", [raw_input_name], ["ld_t"], perm=[0, 2, 1]))
            nodes.append(helper.make_node("Squeeze", ["ld_t", "ld_axis0"], ["ld_dec"]))
        else:
            nodes.append(helper.make_node("Squeeze", [raw_input_name, "ld_axis0"], ["ld_dec"]))
        # Split columns: [A,4] box + [A,C] class scores.
        split_init = numpy_helper.from_array(np.array([4, num_classes], dtype=np.int64), "ld_split_bc")
        inits.append(split_init)
        nodes.append(helper.make_node("Split", ["ld_dec", "ld_split_bc"],
                                      ["ld_cxcywh", "ld_scores"], axis=1))
    elif output_format == "yolox":  # [1, A, C+5] → [A, C+5], grid-decode boxes, scores = obj*cls
        nodes.append(helper.make_node("Squeeze", [raw_input_name, "ld_axis0"], ["ld_dec"]))
        grid, strides = _yolox_grid(input_width, input_height)
        inits.append(numpy_helper.from_array(grid.astype(np.float32), "ld_grid"))      # [A,2]
        inits.append(numpy_helper.from_array(strides.astype(np.float32), "ld_stride"))  # [A,1]
        split5 = numpy_helper.from_array(
            np.array([2, 2, 1, num_classes], dtype=np.int64), "ld_split5")
        inits.append(split5)
        nodes.append(helper.make_node("Split", ["ld_dec", "ld_split5"],
                                      ["ld_xy", "ld_wh", "ld_obj_raw", "ld_cls_raw"], axis=1))
        # xy = (xy + grid) * stride ; wh = exp(wh) * stride
        nodes.append(helper.make_node("Add", ["ld_xy", "ld_grid"], ["ld_xy_g"]))
        nodes.append(helper.make_node("Mul", ["ld_xy_g", "ld_stride"], ["ld_cxy"]))
        nodes.append(helper.make_node("Exp", ["ld_wh"], ["ld_wh_e"]))
        nodes.append(helper.make_node("Mul", ["ld_wh_e", "ld_stride"], ["ld_cwh"]))
        nodes.append(helper.make_node("Concat", ["ld_cxy", "ld_cwh"], ["ld_cxcywh"], axis=1))
        # scores = sigmoid(obj) * sigmoid(cls)
        nodes.append(helper.make_node("Sigmoid", ["ld_obj_raw"], ["ld_obj"]))
        nodes.append(helper.make_node("Sigmoid", ["ld_cls_raw"], ["ld_cls"]))
        nodes.append(helper.make_node("Mul", ["ld_obj", "ld_cls"], ["ld_scores"]))

    if output_format == "nanodet":
        # nanodet GFL/DFL: [1, A, C + 4*(reg_max+1)] → [A, ...]. Each side
        # distance (l, t, r, b) is the expectation of a softmax over reg_max+1
        # bins; boxes are anchor-centre ± distance*stride (FCOS-style grid).
        reg_bins = int(reg_max) + 1
        reg_channels = 4 * reg_bins
        nodes.append(helper.make_node("Squeeze", [raw_input_name, "ld_axis0"], ["ld_dec"]))
        # Split classes / regression according to the channel layout.
        if nanodet_reg_first:
            split_nd = numpy_helper.from_array(
                np.array([reg_channels, num_classes], dtype=np.int64), "ld_split_nd")
            inits.append(split_nd)
            nodes.append(helper.make_node("Split", ["ld_dec", "ld_split_nd"],
                                          ["ld_reg_flat", "ld_cls_raw"], axis=1))
        else:
            split_nd = numpy_helper.from_array(
                np.array([num_classes, reg_channels], dtype=np.int64), "ld_split_nd")
            inits.append(split_nd)
            nodes.append(helper.make_node("Split", ["ld_dec", "ld_split_nd"],
                                          ["ld_cls_raw", "ld_reg_flat"], axis=1))
        nodes.append(helper.make_node("Sigmoid", ["ld_cls_raw"], ["ld_scores"]))

        # Anchor grid (constant) — centres and per-anchor stride.
        centers, strides_nd = nanodet_anchor_grid(input_width, input_height, num_anchors)
        inits.append(numpy_helper.from_array(
            centers[:, 0:1].astype(np.float32), "ld_nd_cx"))   # [A,1]
        inits.append(numpy_helper.from_array(
            centers[:, 1:2].astype(np.float32), "ld_nd_cy"))   # [A,1]
        inits.append(numpy_helper.from_array(
            strides_nd.astype(np.float32), "ld_nd_stride"))    # [A,1]
        inits.append(numpy_helper.from_array(
            np.array([-1, 4, reg_bins], dtype=np.int64), "ld_nd_rshape"))
        inits.append(numpy_helper.from_array(
            np.arange(reg_bins, dtype=np.float32), "ld_nd_proj"))  # [reg_bins]
        inits.append(numpy_helper.from_array(np.array([2], dtype=np.int64), "ld_nd_axis2"))

        # reg → [A,4,reg_bins] → softmax → expectation over bins → distances [A,4]
        nodes.append(helper.make_node("Reshape", ["ld_reg_flat", "ld_nd_rshape"], ["ld_nd_reg"]))
        nodes.append(helper.make_node("Softmax", ["ld_nd_reg"], ["ld_nd_sm"], axis=2))
        nodes.append(helper.make_node("Mul", ["ld_nd_sm", "ld_nd_proj"], ["ld_nd_wsum"]))
        nodes.append(helper.make_node("ReduceSum", ["ld_nd_wsum", "ld_nd_axis2"],
                                      ["ld_nd_dist"], keepdims=0))  # [A,4]
        # distances l,t,r,b → xyxy in input space.
        nodes.append(helper.make_node("Split", ["ld_nd_dist"],
                                      ["ld_nd_l", "ld_nd_t", "ld_nd_r", "ld_nd_b"],
                                      axis=1, num_outputs=4))
        nodes.append(helper.make_node("Mul", ["ld_nd_l", "ld_nd_stride"], ["ld_nd_ls"]))
        nodes.append(helper.make_node("Mul", ["ld_nd_t", "ld_nd_stride"], ["ld_nd_ts"]))
        nodes.append(helper.make_node("Mul", ["ld_nd_r", "ld_nd_stride"], ["ld_nd_rs"]))
        nodes.append(helper.make_node("Mul", ["ld_nd_b", "ld_nd_stride"], ["ld_nd_bs"]))
        nodes.append(helper.make_node("Sub", ["ld_nd_cx", "ld_nd_ls"], ["ld_x1"]))
        nodes.append(helper.make_node("Sub", ["ld_nd_cy", "ld_nd_ts"], ["ld_y1"]))
        nodes.append(helper.make_node("Add", ["ld_nd_cx", "ld_nd_rs"], ["ld_x2"]))
        nodes.append(helper.make_node("Add", ["ld_nd_cy", "ld_nd_bs"], ["ld_y2"]))
        nodes.append(helper.make_node("Concat", ["ld_x1", "ld_y1", "ld_x2", "ld_y2"],
                                      ["ld_boxes"], axis=1))  # [A,4]
    else:
        # ── cxcywh → xyxy (boxes in input space) ─────────────────────────────
        nodes.append(helper.make_node("Split", ["ld_cxcywh"],
                                      ["ld_cx", "ld_cy", "ld_w", "ld_h"], axis=1, num_outputs=4))
        nodes.append(helper.make_node("Div", ["ld_w", "ld_two"], ["ld_hw"]))
        nodes.append(helper.make_node("Div", ["ld_h", "ld_two"], ["ld_hh"]))
        nodes.append(helper.make_node("Sub", ["ld_cx", "ld_hw"], ["ld_x1"]))
        nodes.append(helper.make_node("Sub", ["ld_cy", "ld_hh"], ["ld_y1"]))
        nodes.append(helper.make_node("Add", ["ld_cx", "ld_hw"], ["ld_x2"]))
        nodes.append(helper.make_node("Add", ["ld_cy", "ld_hh"], ["ld_y2"]))
        nodes.append(helper.make_node("Concat", ["ld_x1", "ld_y1", "ld_x2", "ld_y2"],
                                      ["ld_boxes"], axis=1))  # [A,4]

    # ── Gather the matched anchors (NumPy match → anchor_idx) ─────────────────
    nodes.append(helper.make_node("Gather", ["ld_boxes", "anchor_idx"], ["ld_mp_boxes"], axis=0))
    nodes.append(helper.make_node("Gather", ["ld_scores", "anchor_idx"], ["ld_mp_scores"], axis=0))

    # ── Box L1 term: mean(|pred - teacher|) / diag ───────────────────────────
    nodes.append(helper.make_node("Sub", ["ld_mp_boxes", "teacher_boxes_in"], ["ld_box_diff"]))
    nodes.append(helper.make_node("Abs", ["ld_box_diff"], ["ld_box_abs"]))
    nodes.append(helper.make_node("ReduceMean", ["ld_box_abs"], ["ld_l1_raw"], keepdims=0))
    nodes.append(helper.make_node("Div", ["ld_l1_raw", "ld_diag"], ["ld_l1"]))

    # ── Per-pair IoU term: mean(1 - IoU) ─────────────────────────────────────
    nodes.append(helper.make_node("Split", ["ld_mp_boxes"],
                                  ["ld_px1", "ld_py1", "ld_px2", "ld_py2"], axis=1, num_outputs=4))
    nodes.append(helper.make_node("Split", ["teacher_boxes_in"],
                                  ["ld_tx1", "ld_ty1", "ld_tx2", "ld_ty2"], axis=1, num_outputs=4))
    nodes.append(helper.make_node("Max", ["ld_px1", "ld_tx1"], ["ld_ix1"]))
    nodes.append(helper.make_node("Max", ["ld_py1", "ld_ty1"], ["ld_iy1"]))
    nodes.append(helper.make_node("Min", ["ld_px2", "ld_tx2"], ["ld_ix2"]))
    nodes.append(helper.make_node("Min", ["ld_py2", "ld_ty2"], ["ld_iy2"]))
    nodes.append(helper.make_node("Sub", ["ld_ix2", "ld_ix1"], ["ld_iw_raw"]))
    nodes.append(helper.make_node("Sub", ["ld_iy2", "ld_iy1"], ["ld_ih_raw"]))
    nodes.append(helper.make_node("Relu", ["ld_iw_raw"], ["ld_iw"]))
    nodes.append(helper.make_node("Relu", ["ld_ih_raw"], ["ld_ih"]))
    nodes.append(helper.make_node("Mul", ["ld_iw", "ld_ih"], ["ld_inter"]))
    # areas (clamped to >= 0)
    nodes.append(helper.make_node("Sub", ["ld_px2", "ld_px1"], ["ld_pw_raw"]))
    nodes.append(helper.make_node("Sub", ["ld_py2", "ld_py1"], ["ld_ph_raw"]))
    nodes.append(helper.make_node("Relu", ["ld_pw_raw"], ["ld_pw"]))
    nodes.append(helper.make_node("Relu", ["ld_ph_raw"], ["ld_ph"]))
    nodes.append(helper.make_node("Mul", ["ld_pw", "ld_ph"], ["ld_area_p"]))
    nodes.append(helper.make_node("Sub", ["ld_tx2", "ld_tx1"], ["ld_tw_raw"]))
    nodes.append(helper.make_node("Sub", ["ld_ty2", "ld_ty1"], ["ld_th_raw"]))
    nodes.append(helper.make_node("Relu", ["ld_tw_raw"], ["ld_tw"]))
    nodes.append(helper.make_node("Relu", ["ld_th_raw"], ["ld_th"]))
    nodes.append(helper.make_node("Mul", ["ld_tw", "ld_th"], ["ld_area_t"]))
    nodes.append(helper.make_node("Add", ["ld_area_p", "ld_area_t"], ["ld_area_sum"]))
    nodes.append(helper.make_node("Sub", ["ld_area_sum", "ld_inter"], ["ld_union_raw"]))
    nodes.append(helper.make_node("Add", ["ld_union_raw", "ld_eps"], ["ld_union"]))
    nodes.append(helper.make_node("Div", ["ld_inter", "ld_union"], ["ld_iou"]))
    nodes.append(helper.make_node("Sub", ["ld_one", "ld_iou"], ["ld_one_m_iou"]))
    nodes.append(helper.make_node("ReduceMean", ["ld_one_m_iou"], ["ld_iou_term"], keepdims=0))

    # box loss = l1 + mean(1 - IoU)
    nodes.append(helper.make_node("Add", ["ld_l1", "ld_iou_term"], ["loss_box"]))

    # ── Class BCE term: mean(-(t*log p + (1-t)*log(1-p))) ────────────────────
    nodes.append(helper.make_node("Clip", ["ld_mp_scores", "ld_eps", "ld_one_m_eps"], ["ld_p"]))
    nodes.append(helper.make_node("Log", ["ld_p"], ["ld_logp"]))
    nodes.append(helper.make_node("Sub", ["ld_one", "ld_p"], ["ld_1mp"]))
    nodes.append(helper.make_node("Log", ["ld_1mp"], ["ld_log1mp"]))
    nodes.append(helper.make_node("Sub", ["ld_one", "teacher_onehot"], ["ld_1mt"]))
    nodes.append(helper.make_node("Mul", ["teacher_onehot", "ld_logp"], ["ld_pos"]))
    nodes.append(helper.make_node("Mul", ["ld_1mt", "ld_log1mp"], ["ld_neg"]))
    nodes.append(helper.make_node("Add", ["ld_pos", "ld_neg"], ["ld_bce_sum"]))
    nodes.append(helper.make_node("ReduceMean", ["ld_bce_sum"], ["ld_bce_mean"], keepdims=0))
    nodes.append(helper.make_node("Neg", ["ld_bce_mean"], ["loss_class"]))

    # ── Total loss = box + w_class * class ───────────────────────────────────
    nodes.append(helper.make_node("Mul", ["loss_class", "ld_cls_w"], ["ld_wcls"]))
    nodes.append(helper.make_node("Add", ["loss_box", "ld_wcls"], ["total_loss"]))

    if output_format == "yolo11":
        raw_shape = [1, num_classes + 4, "A"] if transpose_output else [1, "A", num_classes + 4]
    elif output_format == "nanodet":
        raw_shape = [1, "A", num_classes + 4 * (int(reg_max) + 1)]
    else:  # yolox
        raw_shape = [1, "A", num_classes + 5]
    graph_inputs = [
        helper.make_tensor_value_info(raw_input_name, TensorProto.FLOAT, raw_shape),
        helper.make_tensor_value_info("anchor_idx", TensorProto.INT64, ["T"]),
        helper.make_tensor_value_info("teacher_boxes_in", TensorProto.FLOAT, ["T", 4]),
        helper.make_tensor_value_info("teacher_onehot", TensorProto.FLOAT, ["T", num_classes]),
    ]
    graph_outputs = [
        helper.make_tensor_value_info("total_loss", TensorProto.FLOAT, []),
        helper.make_tensor_value_info("loss_box", TensorProto.FLOAT, []),
        helper.make_tensor_value_info("loss_class", TensorProto.FLOAT, []),
    ]
    graph = helper.make_graph(nodes, "StudentDistillationLoss",
                              graph_inputs, graph_outputs, initializer=inits)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 18)])
    model.ir_version = 9
    return model


def _yolox_grid(input_width: int, input_height: int,
                strides: Tuple[int, ...] = (8, 16, 32)):
    """Precompute the YOLOX (grid, stride) tensors for in-graph box decoding."""
    grids = []
    expanded = []
    for stride in strides:
        hsize = input_height // stride
        wsize = input_width // stride
        yv, xv = np.meshgrid(np.arange(hsize), np.arange(wsize), indexing="ij")
        grid = np.stack((xv, yv), 2).reshape(-1, 2).astype(np.float32)
        grids.append(grid)
        expanded.append(np.full((grid.shape[0], 1), float(stride), dtype=np.float32))
    return np.concatenate(grids, 0), np.concatenate(expanded, 0)


# Stride sets tried (in priority order) when building the NanoDet anchor grid,
# mirroring ``CustomONNX._postprocess_nanodet``: NanoDet-Plus uses 4 strides,
# the legacy NanoDet-m uses 3.
_NANODET_STRIDE_SETS: Tuple[Tuple[int, ...], ...] = ((8, 16, 32, 64), (8, 16, 32))


def nanodet_anchor_grid(input_width: int, input_height: int,
                        num_anchors: Optional[int] = None):
    """Precompute NanoDet anchor centres + per-anchor strides (FCOS-style grid).

    NanoDet's GFL/DFL head predicts, for every anchor point, four side distances
    (left, top, right, bottom) as the expectation of a softmax distribution. The
    anchor point is the **centre** of a grid cell, ``(x + 0.5) * stride``, with
    the grid built per feature level (stride) in row-major (``indexing='ij'``)
    order — identical to :meth:`CustomONNX._postprocess_nanodet` so the anchor
    ordering matches the raw network output.

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
            # NanoDet-Plus feature maps use ceil(input / stride) so the anchor
            # grid matches the network output (e.g. 7x7 for stride 64 at 416).
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
# 2. Merge the student model with the loss graph (plan section A.1)
# ---------------------------------------------------------------------------
def _infer_nanodet_shape(output_vi, num_classes: int):
    """Infer ``(num_anchors, reg_max)`` from a NanoDet student output value-info.

    Returns ``(num_anchors, reg_max)`` where either value may be ``None`` when
    the corresponding dimension is dynamic/unknown. The channel dimension is the
    last static dim of a ``[1, A, C]`` output; ``A`` is the (static) anchor dim.
    """
    num_anchors = None
    reg_max = None
    try:
        dims = output_vi.type.tensor_type.shape.dim
        shape = [d.dim_value if (d.HasField("dim_value") and d.dim_value > 0) else None
                 for d in dims]
        if len(shape) == 3:
            # Anchors-first [1, A, C]; channel is the last dim.
            num_anchors = shape[1]
            channels = shape[2]
            if channels is not None and channels > num_classes:
                reg_channels = channels - num_classes
                if reg_channels > 0 and reg_channels % 4 == 0:
                    reg_max = reg_channels // 4 - 1
    except Exception:  # pragma: no cover - defensive
        pass
    return num_anchors, reg_max


def merge_student_with_loss(
    student_model_path: str,
    num_classes: int,
    input_width: int,
    input_height: int,
    output_format: str = "yolo11",
    transpose_output: bool = True,
    reg_max: int = 7,
    nanodet_reg_first: bool = False,
):
    """Splice the differentiable loss graph onto a student ONNX model.

    The single student output tensor is connected to the loss graph's
    ``raw_output`` input, so the merged model's only output is the scalar
    ``total_loss`` (plus the two component losses), differentiable w.r.t. the
    student weights.

    For ``nanodet`` the DFL ``reg_max`` and the anchor count are inferred from
    the student output shape when static; the supplied ``reg_max`` is used as a
    fallback.

    Returns
    -------
    (merged_model, student_output_name) : (onnx.ModelProto, str)
    """
    if not _ONNX_AVAILABLE:
        raise RuntimeError("onnx package required to merge the student model")

    student = onnx.load(student_model_path)
    if len(student.graph.output) != 1:
        raise ValueError(
            "ORT training expects a single-output student model; got "
            f"{len(student.graph.output)} outputs."
        )
    student_out = student.graph.output[0].name

    num_anchors = None
    if output_format == "nanodet":
        inferred_anchors, inferred_reg_max = _infer_nanodet_shape(
            student.graph.output[0], num_classes)
        num_anchors = inferred_anchors
        if inferred_reg_max is not None:
            reg_max = inferred_reg_max

    loss_model = build_student_loss_graph(
        num_classes=num_classes,
        input_width=input_width,
        input_height=input_height,
        output_format=output_format,
        raw_input_name="raw_output",
        transpose_output=transpose_output,
        reg_max=reg_max,
        nanodet_reg_first=nanodet_reg_first,
        num_anchors=num_anchors,
    )

    # Align opset/IR so the two models can be composed.
    merged = onnx.compose.merge_models(
        student, loss_model,
        io_map=[(student_out, "raw_output")],
    )

    # ``generate_artifacts(loss=None)`` treats the model's output as the loss, so
    # the training model must expose a single scalar output. The component losses
    # (loss_box/loss_class) are dropped here; ``student_out`` is still an internal
    # tensor and can be requested via ``Module.export_model_for_inferencing`` to
    # recover a detection model carrying the trained weights (plan section B).
    keep = [o for o in merged.graph.output if o.name == "total_loss"]
    del merged.graph.output[:]
    merged.graph.output.extend(keep)
    return merged, student_out


# ---------------------------------------------------------------------------
# 3. Choose trainable weights + generate ORT training artifacts (plan A.1/A.2)
# ---------------------------------------------------------------------------
def select_trainable_params(
    merged_model,
    train_scope: str = "head",
    head_params: int = 8,
) -> Tuple[List[str], List[str]]:
    """Split the student weight initializers into (trainable, frozen) names.

    ``train_scope='all'`` trains every multi-dimensional float weight;
    ``'head'`` trains only the last ``head_params`` of them (the detection
    heads near the output), mirroring the PyTorch ``train_scope`` semantics.
    Only the student's own initializers are considered; the loss-graph
    constants (``ld_*``) are always frozen.
    """
    if not _ONNX_AVAILABLE:
        raise RuntimeError("onnx package required to select trainable params")

    float_types = {TensorProto.FLOAT, TensorProto.FLOAT16, TensorProto.DOUBLE}
    candidates = [
        init.name for init in merged_model.graph.initializer
        if not init.name.startswith("ld_")
        and init.data_type in float_types
        and len(init.dims) >= 1
    ]
    if not candidates:
        return [], [init.name for init in merged_model.graph.initializer]

    if train_scope == "all":
        trainable = list(candidates)
    else:  # 'head': last few weight tensors near the output
        trainable = candidates[-max(1, int(head_params)):]

    trainable_set = set(trainable)
    frozen = [
        init.name for init in merged_model.graph.initializer
        if init.name not in trainable_set
    ]
    return trainable, frozen


def generate_training_artifacts(
    merged_model,
    trainable_params: List[str],
    frozen_params: List[str],
    output_dir: str,
    optimizer: str = "sgd",
):
    """Emit ``training``/``eval``/``optimizer`` ONNX models + ``checkpoint``.

    Thin wrapper around ``onnxruntime.training.artifacts.generate_artifacts``.
    The loss is already baked into ``merged_model`` (its ``total_loss`` output),
    so we pass ``loss=None`` and let ORT use the existing scalar output.

    Returns
    -------
    dict with keys: checkpoint, training_model, eval_model, optimizer_model
    """
    if not is_ort_training_available():
        raise RuntimeError(
            "onnxruntime-training is required to generate training artifacts."
        )
    os.makedirs(output_dir, exist_ok=True)

    opt_enum = {
        "sgd": _ort_artifacts.OptimType.SGD,
        "adamw": _ort_artifacts.OptimType.AdamW,
    }.get(optimizer.lower(), _ort_artifacts.OptimType.SGD)

    _ort_artifacts.generate_artifacts(
        merged_model,
        requires_grad=list(trainable_params),
        frozen_params=list(frozen_params),
        loss=None,
        optimizer=opt_enum,
        artifact_directory=output_dir,
    )
    return {
        "checkpoint": os.path.join(output_dir, "checkpoint"),
        "training_model": os.path.join(output_dir, "training_model.onnx"),
        "eval_model": os.path.join(output_dir, "eval_model.onnx"),
        "optimizer_model": os.path.join(output_dir, "optimizer_model.onnx"),
    }


# ---------------------------------------------------------------------------
# 4. Out-of-graph greedy teacher↔student matcher (plan section A.4)
# ---------------------------------------------------------------------------
def iou_matrix_numpy(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """Vectorised IoU between ``boxes_a`` [N,4] and ``boxes_b`` [M,4] (xyxy)."""
    boxes_a = np.asarray(boxes_a, dtype=np.float32).reshape(-1, 4)
    boxes_b = np.asarray(boxes_b, dtype=np.float32).reshape(-1, 4)
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float32)
    area_a = (np.clip(boxes_a[:, 2] - boxes_a[:, 0], 0, None)
              * np.clip(boxes_a[:, 3] - boxes_a[:, 1], 0, None))
    area_b = (np.clip(boxes_b[:, 2] - boxes_b[:, 0], 0, None)
              * np.clip(boxes_b[:, 3] - boxes_b[:, 1], 0, None))
    lt = np.maximum(boxes_a[:, None, :2], boxes_b[None, :, :2])
    rb = np.minimum(boxes_a[:, None, 2:], boxes_b[None, :, 2:])
    wh = np.clip(rb - lt, 0, None)
    inter = wh[..., 0] * wh[..., 1]
    union = area_a[:, None] + area_b[None, :] - inter + 1e-9
    return (inter / union).astype(np.float32)


def greedy_match_anchors(
    pred_boxes: np.ndarray,
    teacher_boxes_in: np.ndarray,
) -> np.ndarray:
    """Greedy unique assignment of teacher boxes to student anchors.

    Mirrors the (non-differentiable) assignment used by the PyTorch path: the
    teacher box with the highest best-IoU is matched first, each student anchor
    used at most once. Returns an int64 array ``anchor_idx`` of length ``T`` (one
    student anchor index per teacher box); unmatched teachers get ``-1``.
    """
    pred_boxes = np.asarray(pred_boxes, dtype=np.float32).reshape(-1, 4)
    teacher_boxes_in = np.asarray(teacher_boxes_in, dtype=np.float32).reshape(-1, 4)
    T = len(teacher_boxes_in)
    A = len(pred_boxes)
    assigned = np.full(T, -1, dtype=np.int64)
    if T == 0 or A == 0:
        return assigned

    iou = iou_matrix_numpy(teacher_boxes_in, pred_boxes)  # [T, A]
    taken = set()
    order = np.argsort(-iou.max(axis=1))
    for t in order:
        for a in np.argsort(-iou[t]):
            a = int(a)
            if a not in taken:
                assigned[t] = a
                taken.add(a)
                break
    return assigned


def build_matched_targets(
    teacher_boxes_in: np.ndarray,
    teacher_classes: np.ndarray,
    anchor_idx: np.ndarray,
    num_classes: int,
) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Drop unmatched teachers and build the graph inputs for one train step.

    Returns ``(anchor_idx, teacher_boxes_in, teacher_onehot)`` restricted to the
    matched pairs, or ``None`` when nothing matched.
    """
    anchor_idx = np.asarray(anchor_idx, dtype=np.int64).reshape(-1)
    keep = anchor_idx >= 0
    if not keep.any():
        return None
    boxes = np.asarray(teacher_boxes_in, dtype=np.float32).reshape(-1, 4)[keep]
    idx = anchor_idx[keep]
    classes = np.asarray(teacher_classes, dtype=np.int64).reshape(-1)[keep]
    onehot = np.zeros((len(idx), num_classes), dtype=np.float32)
    valid = (classes >= 0) & (classes < num_classes)
    onehot[np.arange(len(idx))[valid], classes[valid]] = 1.0
    return idx, boxes, onehot
