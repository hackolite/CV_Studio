#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Distillation loss functions for teacher-student online training.

Computes a combined score between student predictions and teacher targets
in the object detection context (bounding boxes + class scores).

This module uses a **set-based** scoring approach designed to handle the case
where the teacher and student have different numbers of detections.
Instead of relying on strict 1-to-1 IoU matching, it evaluates:
  - Class distribution similarity (do they detect the same kinds of objects?)
  - Count ratio (how close are the detection counts?)
  - Confidence alignment (are confidence levels comparable?)
  - Spatial coverage (do the student detections cover the same area?)
"""

import numpy as np

try:
    from scipy.optimize import linear_sum_assignment
    _SCIPY_AVAILABLE = True
except ImportError:  # pragma: no cover - scipy is a declared dependency
    _SCIPY_AVAILABLE = False


def compute_iou(box_a, box_b):
    """Compute IoU between two boxes [x1, y1, x2, y2]."""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, box_a[2] - box_a[0]) * max(0, box_a[3] - box_a[1])
    area_b = max(0, box_b[2] - box_b[0]) * max(0, box_b[3] - box_b[1])
    union = area_a + area_b - inter

    if union <= 0:
        return 0.0
    return inter / union


# ─── Set-based scoring helpers ───────────────────────────────────────────────


def _class_distribution_similarity(teacher_class_ids, student_class_ids):
    """Compute cosine similarity between class histograms.

    Works regardless of detection count difference.
    Returns 1.0 for identical distributions, 0.0 for completely different.
    """
    if len(teacher_class_ids) == 0 and len(student_class_ids) == 0:
        return 1.0
    if len(teacher_class_ids) == 0 or len(student_class_ids) == 0:
        return 0.0

    all_classes = set(teacher_class_ids) | set(student_class_ids)
    if not all_classes:
        return 1.0

    # Build normalized histograms
    t_hist = np.zeros(max(all_classes) + 1)
    s_hist = np.zeros(max(all_classes) + 1)
    for c in teacher_class_ids:
        t_hist[c] += 1
    for c in student_class_ids:
        s_hist[c] += 1

    # Normalize to proportions
    t_norm = np.linalg.norm(t_hist)
    s_norm = np.linalg.norm(s_hist)
    if t_norm == 0 or s_norm == 0:
        return 0.0

    cosine_sim = float(np.dot(t_hist, s_hist) / (t_norm * s_norm))
    return max(0.0, cosine_sim)


def _count_ratio_score(teacher_count, student_count):
    """Score based on how close the counts are.

    Returns 1.0 when counts are equal, decays smoothly as they diverge.
    Uses min/max ratio so it's symmetric and handles 0 cases.
    """
    if teacher_count == 0 and student_count == 0:
        return 1.0
    if teacher_count == 0 or student_count == 0:
        return 0.0
    return min(teacher_count, student_count) / max(teacher_count, student_count)


def _confidence_alignment(teacher_scores, student_scores):
    """Compare overall confidence distributions.

    Uses difference of means + std alignment.
    Returns a value in [0, 1], 1.0 = identical confidence profile.
    """
    if len(teacher_scores) == 0 and len(student_scores) == 0:
        return 1.0
    if len(teacher_scores) == 0 or len(student_scores) == 0:
        return 0.0

    t_mean = float(np.mean(teacher_scores))
    s_mean = float(np.mean(student_scores))

    # Mean difference penalty (max diff is 1.0)
    mean_diff = abs(t_mean - s_mean)
    mean_score = 1.0 - mean_diff

    # Std difference penalty
    t_std = float(np.std(teacher_scores)) if len(teacher_scores) > 1 else 0.0
    s_std = float(np.std(student_scores)) if len(student_scores) > 1 else 0.0
    std_diff = abs(t_std - s_std)
    std_score = 1.0 - min(std_diff, 1.0)

    return 0.7 * mean_score + 0.3 * std_score


def _spatial_coverage_score(teacher_bboxes, student_bboxes, img_area=None):
    """Evaluate how well student detections cover the same spatial regions.

    Uses union-over-union of aggregate coverage areas rather than per-box IoU.
    This handles different detection counts naturally.
    """
    if len(teacher_bboxes) == 0 and len(student_bboxes) == 0:
        return 1.0
    if len(teacher_bboxes) == 0 or len(student_bboxes) == 0:
        return 0.0

    # Use a common normalization extent for both
    all_bboxes = list(teacher_bboxes) + list(student_bboxes)
    all_boxes_arr = np.array(all_bboxes, dtype=np.float32)
    global_max_x = max(float(all_boxes_arr[:, [0, 2]].max()), 1.0)
    global_max_y = max(float(all_boxes_arr[:, [1, 3]].max()), 1.0)

    grid_size = 32

    def _fill_mask(bboxes):
        mask = np.zeros((grid_size, grid_size), dtype=np.float32)
        for box in bboxes:
            x1 = int(np.clip(box[0] / global_max_x * grid_size, 0, grid_size - 1))
            y1 = int(np.clip(box[1] / global_max_y * grid_size, 0, grid_size - 1))
            x2 = int(np.clip(box[2] / global_max_x * grid_size, 0, grid_size - 1))
            y2 = int(np.clip(box[3] / global_max_y * grid_size, 0, grid_size - 1))
            mask[y1:y2 + 1, x1:x2 + 1] = 1.0
        return mask

    t_mask = _fill_mask(teacher_bboxes)
    s_mask = _fill_mask(student_bboxes)

    # IoU of coverage masks (set-level, not per-detection)
    intersection = float(np.sum(t_mask * s_mask))
    union = float(np.sum(np.clip(t_mask + s_mask, 0, 1)))

    if union <= 0:
        return 0.0
    return intersection / union


# ─── Legacy helper (kept for compatibility) ──────────────────────────────────


def match_detections(teacher_bboxes, teacher_scores, student_bboxes, student_scores, iou_threshold=0.5):
    """Match student detections to teacher detections using IoU.

    Returns a list of (teacher_idx, student_idx) pairs where IoU >= threshold.
    Unmatched teacher detections represent missed detections (FN penalty).
    Unmatched student detections represent false positives (FP penalty).

    Note: This is kept for backward compatibility. The main scoring now uses
    set-based metrics that don't require 1-to-1 matching.
    """
    if len(teacher_bboxes) == 0 or len(student_bboxes) == 0:
        return [], list(range(len(teacher_bboxes))), list(range(len(student_bboxes)))

    # Compute IoU matrix
    iou_matrix = np.zeros((len(teacher_bboxes), len(student_bboxes)))
    for i, t_box in enumerate(teacher_bboxes):
        for j, s_box in enumerate(student_bboxes):
            iou_matrix[i, j] = compute_iou(t_box, s_box)

    # Greedy matching (highest IoU first)
    matched_pairs = []
    matched_teachers = set()
    matched_students = set()

    while True:
        max_iou = iou_matrix.max()
        if max_iou < iou_threshold or max_iou == 0:
            break
        t_idx, s_idx = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
        matched_pairs.append((int(t_idx), int(s_idx)))
        matched_teachers.add(int(t_idx))
        matched_students.add(int(s_idx))
        iou_matrix[t_idx, :] = 0
        iou_matrix[:, s_idx] = 0

    unmatched_teachers = [i for i in range(len(teacher_bboxes)) if i not in matched_teachers]
    unmatched_students = [i for i in range(len(student_bboxes)) if i not in matched_students]

    return matched_pairs, unmatched_teachers, unmatched_students


# ─── Hungarian (optimal) set matching + set-based distillation loss ──────────


def _coord_l1(box_a, box_b, scale=1.0):
    """Mean absolute (L1) difference of the 4 box coordinates, optionally
    normalised by ``scale`` so the value stays comparable to (1 - IoU)."""
    if scale <= 0:
        scale = 1.0
    return (
        abs(box_a[0] - box_b[0])
        + abs(box_a[1] - box_b[1])
        + abs(box_a[2] - box_b[2])
        + abs(box_a[3] - box_b[3])
    ) / (4.0 * scale)


def _global_scale(boxes_a, boxes_b):
    """Largest coordinate extent across both box sets (>= 1.0).

    Used to normalise L1 distances so they are on roughly the same scale as
    (1 - IoU), regardless of the image resolution.
    """
    all_boxes = list(boxes_a) + list(boxes_b)
    if not all_boxes:
        return 1.0
    arr = np.asarray(all_boxes, dtype=np.float32).reshape(-1, 4)
    return max(float(arr.max()), 1.0)


def hungarian_match_boxes(
    boxes_a, boxes_b,
    classes_a=None, classes_b=None,
    w_iou=1.0, w_class=1.0, w_l1=0.0, scale=None,
):
    """Optimally match two sets of boxes with the Hungarian algorithm (DETR-style).

    The assignment cost between a pair of boxes (teacher ``a`` vs student ``b``)
    follows the matching specification (no confidence is used):

        cost = w_iou * (1 - IoU(a, b)) + w_class * class_cost
               [+ w_l1 * L1(a, b)]   (L1 term off by default, w_l1=0)

    where ``class_cost = 0`` when the class IDs are equal and ``1`` otherwise
    (only applied when both class lists are provided). The optional L1 term is
    disabled by default to match the DETR-style "IoU + class" matching cost; it
    can be re-enabled for finer localisation tie-breaking.

    When SciPy is unavailable the function falls back to greedy matching by
    ascending cost.

    Returns ``(pairs, cost_matrix)`` where ``pairs`` is a list of
    ``(index_a, index_b)`` tuples giving the optimal one-to-one assignment.
    """
    n_a = len(boxes_a)
    n_b = len(boxes_b)
    if n_a == 0 or n_b == 0:
        return [], np.zeros((n_a, n_b), dtype=np.float32)

    if scale is None:
        scale = _global_scale(boxes_a, boxes_b)

    use_class = bool(classes_a) and bool(classes_b)

    cost = np.zeros((n_a, n_b), dtype=np.float32)
    for i, box_a in enumerate(boxes_a):
        for j, box_b in enumerate(boxes_b):
            iou_cost = 1.0 - compute_iou(box_a, box_b)
            class_cost = 0.0
            if use_class and i < len(classes_a) and j < len(classes_b):
                class_cost = 0.0 if int(classes_a[i]) == int(classes_b[j]) else 1.0
            c = w_iou * iou_cost + w_class * class_cost
            if w_l1:
                c += w_l1 * _coord_l1(box_a, box_b, scale)
            cost[i, j] = c

    if _SCIPY_AVAILABLE:
        row_idx, col_idx = linear_sum_assignment(cost)
        pairs = [(int(i), int(j)) for i, j in zip(row_idx, col_idx)]
    else:
        # Greedy fallback: repeatedly pick the lowest-cost available pair.
        pairs = []
        used_a, used_b = set(), set()
        order = np.dstack(np.unravel_index(np.argsort(cost, axis=None), cost.shape))[0]
        for i, j in order:
            i, j = int(i), int(j)
            if i in used_a or j in used_b:
                continue
            used_a.add(i)
            used_b.add(j)
            pairs.append((i, j))
            if len(pairs) >= min(n_a, n_b):
                break

    return pairs, cost


def _max_iou_with_set(box, other_boxes):
    """Largest IoU between ``box`` and any box in ``other_boxes`` (0 if empty)."""
    if not other_boxes:
        return 0.0
    return max(compute_iou(box, ob) for ob in other_boxes)


def compute_set_distillation_loss(
    teacher_bboxes,
    student_bboxes,
    teacher_class_ids=None,
    student_class_ids=None,
    teacher_logits=None,
    student_logits=None,
    w_box=1.0,
    w_class=1.0,
    w_cardinality=1.0,
    w_fp=1.0,
    w_fn=1.0,
    w_cls_mismatch=1.0,
    fn_constant=1.0,
    match_w_iou=1.0,
    match_w_class=1.0,
    match_w_l1=0.0,
    # Weights for the (non-loss) live benchmark detection_score.
    score_alpha=0.1,
    score_beta=0.1,
    score_gamma=0.2,
    score_delta=0.05,
):
    """SOTA set-based distillation loss between teacher and student detections.

    Pipeline (see ``docs/distillation_loss.md`` for the full description):

    1. **Matching** — boxes are matched optimally with
       :func:`hungarian_match_boxes` using a DETR-style cost
       ``w_iou*(1-IoU) + w_class*class_cost`` (no confidence).
    2. **Assignment** — yields ``matched_pairs``, ``unmatched_teacher`` (false
       negatives) and ``unmatched_student`` (false positives).
    3. **Loss** — the weighted sum of:

       - ``L_box``  : ``L1(s, t) + (1 - IoU(s, t))`` over matched pairs.
       - ``L_class``: cross-entropy / KL of class predictions over matched
         pairs (one-hot mismatch when no logits are available).
       - ``L_card`` : ``|N_student - N_teacher|``.
       - ``L_fp``   : ``Σ (1 - max_i IoU(student_unmatched, teacher_i))``.
       - ``L_fn``   : ``fn_constant * count(unmatched_teacher)``.
       - ``L_cls_mismatch`` : ``Σ [class_student != class_teacher]`` (matched).

       ``L_total = w_box*L_box + w_class*L_class + w_cardinality*L_card
                   + w_fp*L_fp + w_fn*L_fn + w_cls_mismatch*L_cls_mismatch``.

    The returned dict carries ``loss`` (= ``L_total``) and every component, the
    chart metrics (``loss_total``, ``loss_box``, ``loss_class``,
    ``cardinality_error``, ``fp_count``, ``fn_count``, ``iou_mean_matched``,
    ``class_mismatch_rate``) and a non-loss ``detection_score`` for live model
    benchmarking. Lower ``loss`` is better; higher ``detection_score`` is better.

    Note: box coordinates are normalised by the largest extent across both sets
    before the L1 term, so ``L_box`` stays resolution-independent and bounded,
    mirroring DETR's use of normalised boxes.
    """
    t_boxes = list(teacher_bboxes)
    s_boxes = list(student_bboxes)
    n_t = len(t_boxes)
    n_s = len(s_boxes)

    # ─── (3.3) Cardinality error |N_s - N_t| (always defined) ───────────────
    cardinality_error = abs(n_s - n_t)
    loss_card = float(cardinality_error)

    has_classes = bool(teacher_class_ids) and bool(student_class_ids)
    has_logits = teacher_logits is not None and student_logits is not None

    # ─── Empty-set shortcuts ────────────────────────────────────────────────
    if n_t == 0 and n_s == 0:
        return _empty_loss_dict()

    if n_t == 0 or n_s == 0:
        # No pairs: everything is FP (student-only) or FN (teacher-only).
        fp_count = n_s
        fn_count = n_t
        loss_fp = float(n_s)  # 1 - max IoU(.) = 1 since the other set is empty
        loss_fn = float(fn_constant * n_t)
        loss = (
            w_cardinality * loss_card
            + w_fp * loss_fp
            + w_fn * loss_fn
        )
        detection_score = (
            0.0
            - score_alpha * fp_count
            - score_beta * fn_count
            - score_delta * cardinality_error
        )
        return {
            'loss': float(loss),
            'loss_total': float(loss),
            'loss_box': 0.0,
            'loss_iou': 1.0,
            'loss_class': 1.0 if (n_t and n_s) else 0.0,
            'loss_cardinality': loss_card,
            'loss_fp': float(loss_fp),
            'loss_fn': float(loss_fn),
            'loss_cls_mismatch': 0.0,
            'cardinality_error': int(cardinality_error),
            'fp_count': int(fp_count),
            'fn_count': int(fn_count),
            'iou_mean_matched': 0.0,
            'class_mismatch_rate': 0.0,
            'num_matched': 0,
            'detection_score': float(detection_score),
            'teacher_count': int(n_t),
            'student_count': int(n_s),
        }

    # ─── (1-2) Hungarian matching + assignment ─────────────────────────────
    scale = _global_scale(t_boxes, s_boxes)
    pairs, _cost = hungarian_match_boxes(
        t_boxes, s_boxes,
        classes_a=teacher_class_ids, classes_b=student_class_ids,
        w_iou=match_w_iou, w_class=match_w_class, w_l1=match_w_l1, scale=scale,
    )

    matched_t = {i for i, _j in pairs}
    matched_s = {j for _i, j in pairs}
    unmatched_teacher = [i for i in range(n_t) if i not in matched_t]
    unmatched_student = [j for j in range(n_s) if j not in matched_s]
    num_matched = len(pairs)

    # ─── (3.1) Box regression loss: L1 + (1 - IoU) over matched pairs ───────
    iou_list = []
    box_terms = []
    class_mismatches = 0
    ce_terms = []
    for i, j in pairs:
        iou = compute_iou(t_boxes[i], s_boxes[j])
        iou_list.append(iou)
        l1 = _coord_l1(t_boxes[i], s_boxes[j], scale)
        box_terms.append(l1 + (1.0 - iou))

        same_class = True
        if has_classes and i < len(teacher_class_ids) and j < len(student_class_ids):
            same_class = int(teacher_class_ids[i]) == int(student_class_ids[j])
            if not same_class:
                class_mismatches += 1

        # ─── (3.2) Class distillation loss (matched only) ───────────────────
        if has_logits:
            ce_terms.append(_kl_divergence(teacher_logits[i], student_logits[j]))
        elif has_classes:
            # One-hot cross-entropy with hard labels reduces to a 0/1 mismatch.
            ce_terms.append(0.0 if same_class else 1.0)

    loss_box = float(np.mean(box_terms)) if box_terms else 0.0
    iou_mean_matched = float(np.mean(iou_list)) if iou_list else 0.0
    loss_iou = float(1.0 - iou_mean_matched)
    loss_class = float(np.mean(ce_terms)) if ce_terms else 0.0
    class_mismatch_rate = (
        class_mismatches / float(num_matched) if num_matched > 0 else 0.0
    )

    # ─── (3.4) Unmatched penalties ─────────────────────────────────────────
    # False positives: student boxes with no teacher match.
    loss_fp = float(sum(
        1.0 - _max_iou_with_set(s_boxes[j], t_boxes) for j in unmatched_student
    ))
    fp_count = len(unmatched_student)
    # False negatives: teacher boxes the student missed.
    fn_count = len(unmatched_teacher)
    loss_fn = float(fn_constant * fn_count)

    # ─── (3.5) Explicit class-mismatch penalty (sum over matched) ──────────
    loss_cls_mismatch = float(class_mismatches)

    # ─── Total loss ─────────────────────────────────────────────────────────
    loss = (
        w_box * loss_box
        + w_class * loss_class
        + w_cardinality * loss_card
        + w_fp * loss_fp
        + w_fn * loss_fn
        + w_cls_mismatch * loss_cls_mismatch
    )

    # ─── Non-loss benchmark score (higher = better) ────────────────────────
    detection_score = (
        iou_mean_matched
        - score_alpha * fp_count
        - score_beta * fn_count
        - score_gamma * class_mismatch_rate
        - score_delta * cardinality_error
    )

    return {
        'loss': float(loss),
        'loss_total': float(loss),
        'loss_box': float(loss_box),
        'loss_iou': float(loss_iou),
        'loss_class': float(loss_class),
        'loss_cardinality': float(loss_card),
        'loss_fp': float(loss_fp),
        'loss_fn': float(loss_fn),
        'loss_cls_mismatch': float(loss_cls_mismatch),
        'cardinality_error': int(cardinality_error),
        'fp_count': int(fp_count),
        'fn_count': int(fn_count),
        'iou_mean_matched': float(iou_mean_matched),
        'class_mismatch_rate': float(class_mismatch_rate),
        'num_matched': int(num_matched),
        'detection_score': float(detection_score),
        'teacher_count': int(n_t),
        'student_count': int(n_s),
    }


def _empty_loss_dict():
    """Loss dict when both teacher and student detect nothing (perfect match)."""
    return {
        'loss': 0.0,
        'loss_total': 0.0,
        'loss_box': 0.0,
        'loss_iou': 0.0,
        'loss_class': 0.0,
        'loss_cardinality': 0.0,
        'loss_fp': 0.0,
        'loss_fn': 0.0,
        'loss_cls_mismatch': 0.0,
        'cardinality_error': 0,
        'fp_count': 0,
        'fn_count': 0,
        # Both sides empty is a perfect agreement, so report a perfect IoU.
        'iou_mean_matched': 1.0,
        'class_mismatch_rate': 0.0,
        'num_matched': 0,
        'detection_score': 1.0,
        'teacher_count': 0,
        'student_count': 0,
    }


def _kl_divergence(teacher_logits, student_logits, eps=1e-8):
    """KL(softmax(teacher) || softmax(student)) for soft class distillation."""
    t = np.asarray(teacher_logits, dtype=np.float64).ravel()
    s = np.asarray(student_logits, dtype=np.float64).ravel()
    if t.size == 0 or s.size != t.size:
        return 0.0
    t_p = np.exp(t - t.max())
    t_p /= t_p.sum() + eps
    s_p = np.exp(s - s.max())
    s_p /= s_p.sum() + eps
    return float(np.sum(t_p * np.log((t_p + eps) / (s_p + eps))))


# ─── Main scoring function ───────────────────────────────────────────────────


def compute_distillation_score(
    teacher_bboxes,
    teacher_scores,
    teacher_class_ids,
    student_bboxes,
    student_scores,
    student_class_ids,
    iou_threshold=0.5,
):
    """Compute a distillation score between teacher and student predictions.

    Uses a **set-based** approach that handles different detection counts
    naturally, without requiring strict 1-to-1 IoU matching.

    The score is computed from four components:
      - class_similarity: cosine similarity of class distributions
      - count_ratio: min/max ratio of detection counts
      - confidence_alignment: similarity of confidence statistics
      - spatial_coverage: IoU of aggregate spatial coverage masks

    Returns a dict with:
      - score: float in [0, 1], 1.0 = perfect match with teacher
      - class_similarity: class distribution cosine similarity
      - count_ratio: detection count ratio
      - confidence_alignment: confidence distribution similarity
      - spatial_coverage: aggregate spatial coverage IoU
      - teacher_count: number of teacher detections
      - student_count: number of student detections
      - loss / loss_box / loss_iou / loss_cardinality / loss_class:
        the Hungarian-matched set-based distillation loss and its components
        (see :func:`compute_set_distillation_loss`).
    """
    # Hungarian-matched set-based loss (used both for charting and to drive the
    # student update inside the distillation step).
    set_loss = compute_set_distillation_loss(
        teacher_bboxes,
        student_bboxes,
        teacher_class_ids=teacher_class_ids,
        student_class_ids=student_class_ids,
    )

    t_count = len(teacher_bboxes)
    s_count = len(student_bboxes)

    if t_count == 0 and s_count == 0:
        return {
            'score': 1.0,
            'class_similarity': 1.0,
            'count_ratio': 1.0,
            'confidence_alignment': 1.0,
            'spatial_coverage': 1.0,
            'teacher_count': 0,
            'student_count': 0,
            **_loss_keys(set_loss),
        }

    if t_count == 0:
        # Teacher sees nothing but student detects things → penalty
        return {
            'score': 0.0,
            'class_similarity': 0.0,
            'count_ratio': 0.0,
            'confidence_alignment': 0.0,
            'spatial_coverage': 0.0,
            'teacher_count': 0,
            'student_count': s_count,
            **_loss_keys(set_loss),
        }

    if s_count == 0:
        # Teacher detects but student sees nothing → penalty
        return {
            'score': 0.0,
            'class_similarity': 0.0,
            'count_ratio': 0.0,
            'confidence_alignment': 0.0,
            'spatial_coverage': 0.0,
            'teacher_count': t_count,
            'student_count': 0,
            **_loss_keys(set_loss),
        }

    # Compute individual components
    class_sim = _class_distribution_similarity(teacher_class_ids, student_class_ids)
    count_r = _count_ratio_score(t_count, s_count)
    conf_align = _confidence_alignment(teacher_scores, student_scores)
    spatial_cov = _spatial_coverage_score(teacher_bboxes, student_bboxes)

    # Weighted combination
    # Spatial coverage and class distribution are the most important
    _W_CLASS = 0.30
    _W_SPATIAL = 0.35
    _W_COUNT = 0.15
    _W_CONF = 0.20

    score = (
        _W_CLASS * class_sim
        + _W_SPATIAL * spatial_cov
        + _W_COUNT * count_r
        + _W_CONF * conf_align
    )

    return {
        'score': float(np.clip(score, 0.0, 1.0)),
        'class_similarity': float(class_sim),
        'count_ratio': float(count_r),
        'confidence_alignment': float(conf_align),
        'spatial_coverage': float(spatial_cov),
        'teacher_count': t_count,
        'student_count': s_count,
        **_loss_keys(set_loss),
    }


def _loss_keys(set_loss):
    """Extract the set-based loss components + chart metrics for merging into
    a score dict (consumed by the OnlineTraining node and the Chart node)."""
    return {
        'loss': set_loss['loss'],
        'loss_total': set_loss.get('loss_total', set_loss['loss']),
        'loss_box': set_loss['loss_box'],
        'loss_iou': set_loss['loss_iou'],
        'loss_class': set_loss['loss_class'],
        'loss_cardinality': set_loss['loss_cardinality'],
        'loss_fp': set_loss.get('loss_fp', 0.0),
        'loss_fn': set_loss.get('loss_fn', 0.0),
        'loss_cls_mismatch': set_loss.get('loss_cls_mismatch', 0.0),
        'cardinality_error': set_loss.get('cardinality_error', 0),
        'fp_count': set_loss.get('fp_count', 0),
        'fn_count': set_loss.get('fn_count', 0),
        'iou_mean_matched': set_loss.get('iou_mean_matched', 0.0),
        'class_mismatch_rate': set_loss.get('class_mismatch_rate', 0.0),
        'detection_score': set_loss.get('detection_score', 0.0),
    }
