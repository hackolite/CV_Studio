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
    """
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
    }
