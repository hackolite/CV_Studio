#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Distillation loss functions for teacher-student online training.

Computes a combined loss between student predictions and teacher targets
in the object detection context (bounding boxes + class scores).
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


def match_detections(teacher_bboxes, teacher_scores, student_bboxes, student_scores, iou_threshold=0.5):
    """Match student detections to teacher detections using IoU.

    Returns a list of (teacher_idx, student_idx) pairs where IoU >= threshold.
    Unmatched teacher detections represent missed detections (FN penalty).
    Unmatched student detections represent false positives (FP penalty).
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

    Returns a dict with:
      - score: float in [0, 1], 1.0 = perfect match with teacher
      - matched_count: number of matched detections
      - missed_count: teacher detections not found by student
      - false_positive_count: student detections not matching any teacher
      - avg_iou: average IoU of matched pairs
      - avg_score_diff: average confidence score difference for matched pairs
      - class_accuracy: fraction of matched pairs with correct class
    """
    if len(teacher_bboxes) == 0 and len(student_bboxes) == 0:
        return {
            'score': 1.0,
            'matched_count': 0,
            'missed_count': 0,
            'false_positive_count': 0,
            'avg_iou': 1.0,
            'avg_score_diff': 0.0,
            'class_accuracy': 1.0,
        }

    if len(teacher_bboxes) == 0:
        return {
            'score': 0.0,
            'matched_count': 0,
            'missed_count': 0,
            'false_positive_count': len(student_bboxes),
            'avg_iou': 0.0,
            'avg_score_diff': 0.0,
            'class_accuracy': 0.0,
        }

    matched_pairs, unmatched_teachers, unmatched_students = match_detections(
        teacher_bboxes, teacher_scores, student_bboxes, student_scores, iou_threshold
    )

    matched_count = len(matched_pairs)
    missed_count = len(unmatched_teachers)
    fp_count = len(unmatched_students)

    # Compute metrics for matched pairs
    avg_iou = 0.0
    avg_score_diff = 0.0
    class_correct = 0

    if matched_count > 0:
        ious = []
        score_diffs = []
        for t_idx, s_idx in matched_pairs:
            iou = compute_iou(teacher_bboxes[t_idx], student_bboxes[s_idx])
            ious.append(iou)
            score_diffs.append(abs(teacher_scores[t_idx] - student_scores[s_idx]))
            if teacher_class_ids[t_idx] == student_class_ids[s_idx]:
                class_correct += 1

        avg_iou = float(np.mean(ious))
        avg_score_diff = float(np.mean(score_diffs))

    class_accuracy = class_correct / matched_count if matched_count > 0 else 0.0

    # Compute combined score
    # Recall component: how many teacher detections were found
    recall = matched_count / len(teacher_bboxes) if len(teacher_bboxes) > 0 else 1.0
    # Precision component: how many student detections are valid
    total_student = matched_count + fp_count
    precision = matched_count / total_student if total_student > 0 else 1.0
    # Quality: avg IoU of matches * class accuracy
    quality = avg_iou * class_accuracy if matched_count > 0 else 0.0

    # Combined score (F1-like with quality weighting)
    _BASE_WEIGHT = 0.7
    _QUALITY_WEIGHT = 0.3
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    score = f1 * (_BASE_WEIGHT + _QUALITY_WEIGHT * quality)  # Quality bonus

    return {
        'score': float(np.clip(score, 0.0, 1.0)),
        'matched_count': matched_count,
        'missed_count': missed_count,
        'false_positive_count': fp_count,
        'avg_iou': avg_iou,
        'avg_score_diff': avg_score_diff,
        'class_accuracy': class_accuracy,
    }
