#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Differentiable set-based distillation loss as an ONNX computation graph.

Builds an ONNX model representing the loss function that can be appended to
a student detection model for use with onnxruntime-training. All operations
are standard ONNX ops and are automatically differentiable by ORT Training.

The loss is composed of four components:
1. Class distribution loss (KL divergence on soft class histograms)
2. Count consistency loss (MSE between detection counts)
3. Confidence alignment loss (soft-matched via IoU attention)
4. Spatial consistency loss (smooth IoU-based coverage)

No Hungarian matching. No discrete assignment.
"""

import numpy as np

try:
    import onnx
    from onnx import TensorProto, helper, numpy_helper
    _ONNX_AVAILABLE = True
except ImportError:
    _ONNX_AVAILABLE = False


def build_iou_matrix_graph(prefix="iou"):
    """Build ONNX sub-graph nodes that compute pairwise IoU matrix.

    Inputs:
        {prefix}_boxes_a: [N, 4] (x1, y1, x2, y2)
        {prefix}_boxes_b: [M, 4] (x1, y1, x2, y2)

    Output:
        {prefix}_iou: [N, M]
    """
    if not _ONNX_AVAILABLE:
        raise RuntimeError("onnx package required to build loss graph")

    nodes = []
    p = prefix

    # Split box coordinates: boxes_a → a_x1, a_y1, a_x2, a_y2
    nodes.append(helper.make_node("Split", [f"{p}_boxes_a"], [f"{p}_a_x1", f"{p}_a_y1", f"{p}_a_x2", f"{p}_a_y2"],
                                  axis=1, num_outputs=4))
    nodes.append(helper.make_node("Split", [f"{p}_boxes_b"], [f"{p}_b_x1", f"{p}_b_y1", f"{p}_b_x2", f"{p}_b_y2"],
                                  axis=1, num_outputs=4))

    # Transpose b coords for broadcasting: [M,1] → can broadcast with [N,1]
    # Actually we need [N,1] vs [1,M] for pairwise
    # a coords are [N,1], b coords need to be [1,M]
    nodes.append(helper.make_node("Transpose", [f"{p}_b_x1"], [f"{p}_b_x1_t"], perm=[1, 0]))
    nodes.append(helper.make_node("Transpose", [f"{p}_b_y1"], [f"{p}_b_y1_t"], perm=[1, 0]))
    nodes.append(helper.make_node("Transpose", [f"{p}_b_x2"], [f"{p}_b_x2_t"], perm=[1, 0]))
    nodes.append(helper.make_node("Transpose", [f"{p}_b_y2"], [f"{p}_b_y2_t"], perm=[1, 0]))

    # Intersection: max(a_x1, b_x1), max(a_y1, b_y1), min(a_x2, b_x2), min(a_y2, b_y2)
    nodes.append(helper.make_node("Max", [f"{p}_a_x1", f"{p}_b_x1_t"], [f"{p}_inter_x1"]))
    nodes.append(helper.make_node("Max", [f"{p}_a_y1", f"{p}_b_y1_t"], [f"{p}_inter_y1"]))
    nodes.append(helper.make_node("Min", [f"{p}_a_x2", f"{p}_b_x2_t"], [f"{p}_inter_x2"]))
    nodes.append(helper.make_node("Min", [f"{p}_a_y2", f"{p}_b_y2_t"], [f"{p}_inter_y2"]))

    # inter_w = max(0, inter_x2 - inter_x1), inter_h = max(0, inter_y2 - inter_y1)
    nodes.append(helper.make_node("Sub", [f"{p}_inter_x2", f"{p}_inter_x1"], [f"{p}_raw_w"]))
    nodes.append(helper.make_node("Sub", [f"{p}_inter_y2", f"{p}_inter_y1"], [f"{p}_raw_h"]))
    nodes.append(helper.make_node("Relu", [f"{p}_raw_w"], [f"{p}_inter_w"]))
    nodes.append(helper.make_node("Relu", [f"{p}_raw_h"], [f"{p}_inter_h"]))

    # inter_area = inter_w * inter_h
    nodes.append(helper.make_node("Mul", [f"{p}_inter_w", f"{p}_inter_h"], [f"{p}_inter_area"]))

    # area_a = (a_x2 - a_x1) * (a_y2 - a_y1)  [N,1]
    nodes.append(helper.make_node("Sub", [f"{p}_a_x2", f"{p}_a_x1"], [f"{p}_a_w"]))
    nodes.append(helper.make_node("Sub", [f"{p}_a_y2", f"{p}_a_y1"], [f"{p}_a_h"]))
    nodes.append(helper.make_node("Mul", [f"{p}_a_w", f"{p}_a_h"], [f"{p}_area_a"]))

    # area_b = (b_x2 - b_x1) * (b_y2 - b_y1)  [1,M]
    nodes.append(helper.make_node("Sub", [f"{p}_b_x2_t", f"{p}_b_x1_t"], [f"{p}_b_w"]))
    nodes.append(helper.make_node("Sub", [f"{p}_b_y2_t", f"{p}_b_y1_t"], [f"{p}_b_h"]))
    nodes.append(helper.make_node("Mul", [f"{p}_b_w", f"{p}_b_h"], [f"{p}_area_b"]))

    # union = area_a + area_b - inter_area + eps
    nodes.append(helper.make_node("Add", [f"{p}_area_a", f"{p}_area_b"], [f"{p}_sum_areas"]))
    nodes.append(helper.make_node("Sub", [f"{p}_sum_areas", f"{p}_inter_area"], [f"{p}_union_raw"]))

    # iou = inter_area / (union + eps)
    # eps is added as an initializer
    nodes.append(helper.make_node("Add", [f"{p}_union_raw", f"{p}_eps"], [f"{p}_union"]))
    nodes.append(helper.make_node("Div", [f"{p}_inter_area", f"{p}_union"], [f"{p}_iou"]))

    # Initializer for eps
    eps_init = numpy_helper.from_array(
        np.array(1e-6, dtype=np.float32), name=f"{p}_eps"
    )

    return nodes, [eps_init]


def build_distillation_loss_graph(num_classes=80, temperature=1.0,
                                  w_class=1.0, w_count=0.5,
                                  w_confidence=1.0, w_spatial=1.0):
    """Build a complete ONNX model representing the set-based distillation loss.

    Inputs:
        boxes_t: float32 [N_t, 4] teacher boxes (xyxy)
        scores_t: float32 [N_t] teacher confidences
        classes_t: int64 [N_t] teacher class IDs
        boxes_s: float32 [N_s, 4] student boxes (xyxy)
        scores_s: float32 [N_s] student confidences
        classes_s: int64 [N_s] student class IDs

    Outputs:
        total_loss: float32 scalar
        loss_class: float32 scalar
        loss_count: float32 scalar
        loss_confidence: float32 scalar
        loss_spatial: float32 scalar

    Returns
    -------
    onnx.ModelProto
    """
    if not _ONNX_AVAILABLE:
        raise RuntimeError("onnx package required to build loss graph")

    nodes = []
    initializers = []

    # ─── Inputs ───────────────────────────────────────────────────────────────
    inputs = [
        helper.make_tensor_value_info("boxes_t", TensorProto.FLOAT, ["N_t", 4]),
        helper.make_tensor_value_info("scores_t", TensorProto.FLOAT, ["N_t"]),
        helper.make_tensor_value_info("classes_t", TensorProto.INT64, ["N_t"]),
        helper.make_tensor_value_info("boxes_s", TensorProto.FLOAT, ["N_s", 4]),
        helper.make_tensor_value_info("scores_s", TensorProto.FLOAT, ["N_s"]),
        helper.make_tensor_value_info("classes_s", TensorProto.INT64, ["N_s"]),
    ]

    outputs = [
        helper.make_tensor_value_info("total_loss", TensorProto.FLOAT, []),
        helper.make_tensor_value_info("loss_class", TensorProto.FLOAT, []),
        helper.make_tensor_value_info("loss_count", TensorProto.FLOAT, []),
        helper.make_tensor_value_info("loss_confidence", TensorProto.FLOAT, []),
        helper.make_tensor_value_info("loss_spatial", TensorProto.FLOAT, []),
    ]

    # ─── Constants / Initializers ─────────────────────────────────────────────
    initializers.append(numpy_helper.from_array(
        np.array(1e-8, dtype=np.float32), name="eps"))
    initializers.append(numpy_helper.from_array(
        np.array(num_classes, dtype=np.int64), name="num_classes_val"))
    initializers.append(numpy_helper.from_array(
        np.array(temperature, dtype=np.float32), name="temperature"))
    initializers.append(numpy_helper.from_array(
        np.array(w_class, dtype=np.float32), name="w_class"))
    initializers.append(numpy_helper.from_array(
        np.array(w_count, dtype=np.float32), name="w_count"))
    initializers.append(numpy_helper.from_array(
        np.array(w_confidence, dtype=np.float32), name="w_confidence"))
    initializers.append(numpy_helper.from_array(
        np.array(w_spatial, dtype=np.float32), name="w_spatial"))
    initializers.append(numpy_helper.from_array(
        np.array(0, dtype=np.int64), name="zero_i"))
    initializers.append(numpy_helper.from_array(
        np.array(1.0, dtype=np.float32), name="one_f"))
    initializers.append(numpy_helper.from_array(
        np.array(0.0, dtype=np.float32), name="zero_f"))
    initializers.append(numpy_helper.from_array(
        np.array([0], dtype=np.int64), name="axis_0"))
    initializers.append(numpy_helper.from_array(
        np.array([1], dtype=np.int64), name="axis_1"))
    # OneHot values must be rank 1 tensor [off_value, on_value]
    initializers.append(numpy_helper.from_array(
        np.array([0.0, 1.0], dtype=np.float32), name="onehot_values"))

    # ─── 1. COUNT CONSISTENCY LOSS: MSE(N_t, N_s) ────────────────────────────
    # Shape → scalar count
    nodes.append(helper.make_node("Shape", ["scores_t"], ["shape_t"]))
    nodes.append(helper.make_node("Gather", ["shape_t", "zero_i"], ["n_t_i64"], axis=0))
    nodes.append(helper.make_node("Cast", ["n_t_i64"], ["n_t_f"], to=TensorProto.FLOAT))

    nodes.append(helper.make_node("Shape", ["scores_s"], ["shape_s"]))
    nodes.append(helper.make_node("Gather", ["shape_s", "zero_i"], ["n_s_i64"], axis=0))
    nodes.append(helper.make_node("Cast", ["n_s_i64"], ["n_s_f"], to=TensorProto.FLOAT))

    # MSE = (n_t - n_s)^2
    nodes.append(helper.make_node("Sub", ["n_t_f", "n_s_f"], ["count_diff"]))
    nodes.append(helper.make_node("Mul", ["count_diff", "count_diff"], ["loss_count"]))

    # ─── 2. CLASS DISTRIBUTION LOSS: KL divergence on soft histograms ─────────
    # OneHot for teacher classes → [N_t, C]
    nodes.append(helper.make_node("OneHot", ["classes_t", "num_classes_val", "onehot_values"],
                                  ["onehot_t"], axis=1))
    # Weight by scores_t: [N_t, C] * [N_t, 1]
    nodes.append(helper.make_node("Unsqueeze", ["scores_t", "axis_1"], ["scores_t_2d"]))
    nodes.append(helper.make_node("Mul", ["onehot_t", "scores_t_2d"], ["weighted_t"]))
    # Sum over detections → [1, C] then squeeze
    nodes.append(helper.make_node("ReduceSum", ["weighted_t", "axis_0"], ["hist_t_raw_2d"], keepdims=0))

    # OneHot for student classes → [N_s, C]
    nodes.append(helper.make_node("OneHot", ["classes_s", "num_classes_val", "onehot_values"],
                                  ["onehot_s"], axis=1))
    nodes.append(helper.make_node("Unsqueeze", ["scores_s", "axis_1"], ["scores_s_2d"]))
    nodes.append(helper.make_node("Mul", ["onehot_s", "scores_s_2d"], ["weighted_s"]))
    nodes.append(helper.make_node("ReduceSum", ["weighted_s", "axis_0"], ["hist_s_raw_2d"], keepdims=0))

    # Normalize to probability distributions (add eps for stability)
    nodes.append(helper.make_node("Add", ["hist_t_raw_2d", "eps"], ["hist_t_eps"]))
    nodes.append(helper.make_node("ReduceSum", ["hist_t_eps", "axis_0"], ["hist_t_sum"], keepdims=0))
    nodes.append(helper.make_node("Add", ["hist_t_sum", "eps"], ["hist_t_sum_safe"]))
    nodes.append(helper.make_node("Div", ["hist_t_eps", "hist_t_sum_safe"], ["p_t"]))

    nodes.append(helper.make_node("Add", ["hist_s_raw_2d", "eps"], ["hist_s_eps"]))
    nodes.append(helper.make_node("ReduceSum", ["hist_s_eps", "axis_0"], ["hist_s_sum"], keepdims=0))
    nodes.append(helper.make_node("Add", ["hist_s_sum", "eps"], ["hist_s_sum_safe"]))
    nodes.append(helper.make_node("Div", ["hist_s_eps", "hist_s_sum_safe"], ["p_s"]))

    # KL(p_t || p_s) = sum(p_t * log(p_t / p_s))
    nodes.append(helper.make_node("Log", ["p_t"], ["log_p_t"]))
    nodes.append(helper.make_node("Log", ["p_s"], ["log_p_s"]))
    nodes.append(helper.make_node("Sub", ["log_p_t", "log_p_s"], ["log_ratio"]))
    nodes.append(helper.make_node("Mul", ["p_t", "log_ratio"], ["kl_elements"]))
    nodes.append(helper.make_node("ReduceSum", ["kl_elements", "axis_0"], ["loss_class"], keepdims=0))

    # ─── 3. CONFIDENCE ALIGNMENT LOSS (soft-matched via IoU attention) ────────
    # Build IoU matrix between teacher and student boxes
    # Set up inputs for the IoU subgraph first
    nodes.append(helper.make_node("Identity", ["boxes_t"], ["conf_boxes_a"]))
    nodes.append(helper.make_node("Identity", ["boxes_s"], ["conf_boxes_b"]))

    iou_nodes, iou_inits = build_iou_matrix_graph(prefix="conf")
    nodes.extend(iou_nodes)
    initializers.extend(iou_inits)

    # Softmax attention over student dim: attention[i,j] = softmax(iou[i,:] / T)
    nodes.append(helper.make_node("Div", ["conf_iou", "temperature"], ["conf_iou_scaled"]))
    nodes.append(helper.make_node("Softmax", ["conf_iou_scaled"], ["conf_attention"], axis=1))

    # Soft student scores for each teacher: [N_t, N_s] @ [N_s, 1] → [N_t, 1]
    nodes.append(helper.make_node("Unsqueeze", ["scores_s", "axis_1"], ["scores_s_col"]))
    nodes.append(helper.make_node("MatMul", ["conf_attention", "scores_s_col"], ["soft_s_scores_2d"]))
    nodes.append(helper.make_node("Squeeze", ["soft_s_scores_2d", "axis_1"], ["soft_s_scores"]))

    # Weighted MSE: weights = scores_t / sum(scores_t)
    nodes.append(helper.make_node("ReduceSum", ["scores_t", "axis_0"], ["scores_t_total"], keepdims=0))
    nodes.append(helper.make_node("Add", ["scores_t_total", "eps"], ["scores_t_total_safe"]))
    nodes.append(helper.make_node("Div", ["scores_t", "scores_t_total_safe"], ["conf_weights"]))

    # (scores_t - soft_s_scores)^2 * weights → sum
    nodes.append(helper.make_node("Sub", ["scores_t", "soft_s_scores"], ["conf_diff"]))
    nodes.append(helper.make_node("Mul", ["conf_diff", "conf_diff"], ["conf_diff_sq"]))
    nodes.append(helper.make_node("Mul", ["conf_diff_sq", "conf_weights"], ["conf_weighted_sq"]))
    nodes.append(helper.make_node("ReduceSum", ["conf_weighted_sq", "axis_0"], ["loss_confidence"], keepdims=0))

    # ─── 4. SPATIAL CONSISTENCY LOSS (smooth coverage via IoU) ─────────────────
    # Set up inputs for the spatial IoU subgraph first
    nodes.append(helper.make_node("Identity", ["boxes_t"], ["spat_boxes_a"]))
    nodes.append(helper.make_node("Identity", ["boxes_s"], ["spat_boxes_b"]))

    spat_nodes, spat_inits = build_iou_matrix_graph(prefix="spat")
    nodes.extend(spat_nodes)
    initializers.extend(spat_inits)

    # For each teacher box, soft-max coverage = logsumexp(iou_row / T) * T
    # This approximates max(iou_row) but is differentiable
    nodes.append(helper.make_node("Div", ["spat_iou", "temperature"], ["spat_iou_scaled"]))
    nodes.append(helper.make_node("ReduceLogSumExp", ["spat_iou_scaled", "axis_1"], ["spat_lse"],
                                  keepdims=0))
    nodes.append(helper.make_node("Mul", ["spat_lse", "temperature"], ["spat_coverage_raw"]))

    # Clamp to [0, 1]
    nodes.append(helper.make_node("Clip", ["spat_coverage_raw", "zero_f", "one_f"], ["spat_coverage"]))

    # Loss = 1 - mean(coverage)
    nodes.append(helper.make_node("ReduceMean", ["spat_coverage", "axis_0"], ["spat_mean_cov"], keepdims=0))
    nodes.append(helper.make_node("Sub", ["one_f", "spat_mean_cov"], ["loss_spatial"]))

    # ─── TOTAL LOSS: weighted sum ─────────────────────────────────────────────
    nodes.append(helper.make_node("Mul", ["loss_class", "w_class"], ["wloss_class"]))
    nodes.append(helper.make_node("Mul", ["loss_count", "w_count"], ["wloss_count"]))
    nodes.append(helper.make_node("Mul", ["loss_confidence", "w_confidence"], ["wloss_conf"]))
    nodes.append(helper.make_node("Mul", ["loss_spatial", "w_spatial"], ["wloss_spat"]))

    nodes.append(helper.make_node("Add", ["wloss_class", "wloss_count"], ["sum_12"]))
    nodes.append(helper.make_node("Add", ["sum_12", "wloss_conf"], ["sum_123"]))
    nodes.append(helper.make_node("Add", ["sum_123", "wloss_spat"], ["total_loss"]))

    # ─── Build the ONNX graph ─────────────────────────────────────────────────
    graph = helper.make_graph(
        nodes, "SetBasedDistillationLoss", inputs, outputs, initializer=initializers
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 18)])
    model.ir_version = 9

    return model


# ─── Numpy-based forward pass (mirrors the ONNX graph for CPU evaluation) ────


def compute_distillation_loss_numpy(
    boxes_t: np.ndarray,
    scores_t: np.ndarray,
    classes_t: np.ndarray,
    boxes_s: np.ndarray,
    scores_s: np.ndarray,
    classes_s: np.ndarray,
    num_classes: int = 80,
    temperature: float = 1.0,
    w_class: float = 1.0,
    w_count: float = 0.5,
    w_confidence: float = 1.0,
    w_spatial: float = 1.0,
) -> dict:
    """Compute the set-based distillation loss using numpy (forward pass only).

    This mirrors the ONNX graph computation exactly, useful for:
    - Evaluation without onnxruntime-training installed
    - Verification / testing of the ONNX graph correctness

    Parameters
    ----------
    boxes_t : ndarray [N_t, 4] teacher boxes (xyxy)
    scores_t : ndarray [N_t] teacher confidences
    classes_t : ndarray [N_t] teacher class IDs (int)
    boxes_s : ndarray [N_s, 4] student boxes (xyxy)
    scores_s : ndarray [N_s] student confidences
    classes_s : ndarray [N_s] student class IDs (int)

    Returns
    -------
    dict with: loss, loss_class, loss_count, loss_confidence, loss_spatial
    """
    eps = 1e-8
    n_t = len(scores_t)
    n_s = len(scores_s)

    # ─── 1. Count loss ────────────────────────────────────────────────────────
    loss_count = float((n_t - n_s) ** 2)

    # ─── 2. Class distribution loss ──────────────────────────────────────────
    if n_t == 0 and n_s == 0:
        loss_class = 0.0
    else:
        # Soft histograms
        hist_t = np.zeros(num_classes, dtype=np.float32)
        hist_s = np.zeros(num_classes, dtype=np.float32)
        for i in range(n_t):
            hist_t[int(classes_t[i])] += scores_t[i]
        for i in range(n_s):
            hist_s[int(classes_s[i])] += scores_s[i]

        # Normalize to distributions
        p_t = (hist_t + eps) / (hist_t.sum() + eps * num_classes)
        p_s = (hist_s + eps) / (hist_s.sum() + eps * num_classes)

        # KL(p_t || p_s)
        loss_class = float(np.sum(p_t * np.log(p_t / p_s)))

    # ─── 3. Confidence alignment loss ────────────────────────────────────────
    if n_t == 0 or n_s == 0:
        loss_confidence = 0.0 if n_t == 0 else float(np.mean(scores_t))
    else:
        iou_matrix = _compute_iou_matrix_numpy(boxes_t, boxes_s)
        # Softmax attention over student dim
        scaled = iou_matrix / temperature
        exp_scaled = np.exp(scaled - scaled.max(axis=1, keepdims=True))
        attention = exp_scaled / (exp_scaled.sum(axis=1, keepdims=True) + eps)

        # Soft student scores
        soft_s_scores = attention @ scores_s  # [N_t]

        # Weighted MSE
        weights = scores_t / (scores_t.sum() + eps)
        loss_confidence = float(np.sum(weights * (scores_t - soft_s_scores) ** 2))

    # ─── 4. Spatial consistency loss ─────────────────────────────────────────
    if n_t == 0 or n_s == 0:
        loss_spatial = 1.0 if n_t > 0 else 0.0
    else:
        iou_matrix = _compute_iou_matrix_numpy(boxes_t, boxes_s)
        # LogSumExp approximation of max
        scaled = iou_matrix / temperature
        lse = np.log(np.sum(np.exp(scaled), axis=1)) * temperature
        coverage = np.clip(lse, 0.0, 1.0)
        loss_spatial = float(1.0 - coverage.mean())

    # ─── Total ────────────────────────────────────────────────────────────────
    total = (w_class * loss_class + w_count * loss_count
             + w_confidence * loss_confidence + w_spatial * loss_spatial)

    return {
        'loss': total,
        'loss_class': loss_class,
        'loss_count': loss_count,
        'loss_confidence': loss_confidence,
        'loss_spatial': loss_spatial,
    }


def _compute_iou_matrix_numpy(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """Compute pairwise IoU matrix [N, M] between two box arrays."""
    n = len(boxes_a)
    m = len(boxes_b)
    iou = np.zeros((n, m), dtype=np.float32)

    for i in range(n):
        for j in range(m):
            x1 = max(boxes_a[i, 0], boxes_b[j, 0])
            y1 = max(boxes_a[i, 1], boxes_b[j, 1])
            x2 = min(boxes_a[i, 2], boxes_b[j, 2])
            y2 = min(boxes_a[i, 3], boxes_b[j, 3])

            inter = max(0, x2 - x1) * max(0, y2 - y1)
            area_a = max(0, boxes_a[i, 2] - boxes_a[i, 0]) * max(0, boxes_a[i, 3] - boxes_a[i, 1])
            area_b = max(0, boxes_b[j, 2] - boxes_b[j, 0]) * max(0, boxes_b[j, 3] - boxes_b[j, 1])
            union = area_a + area_b - inter + 1e-6
            iou[i, j] = inter / union

    return iou
