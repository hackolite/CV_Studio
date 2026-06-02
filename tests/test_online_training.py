#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for online training distillation loss module."""

import numpy as np
import pytest

from node.DLNode.online_training.distillation_loss import (
    compute_iou,
    match_detections,
    compute_distillation_score,
)


class TestComputeIoU:
    def test_perfect_overlap(self):
        box = [0, 0, 100, 100]
        assert compute_iou(box, box) == pytest.approx(1.0)

    def test_no_overlap(self):
        box_a = [0, 0, 50, 50]
        box_b = [100, 100, 200, 200]
        assert compute_iou(box_a, box_b) == pytest.approx(0.0)

    def test_partial_overlap(self):
        box_a = [0, 0, 100, 100]
        box_b = [50, 50, 150, 150]
        # Intersection: 50x50 = 2500, Union: 10000 + 10000 - 2500 = 17500
        assert compute_iou(box_a, box_b) == pytest.approx(2500.0 / 17500.0, rel=1e-3)

    def test_contained_box(self):
        box_a = [0, 0, 100, 100]
        box_b = [25, 25, 75, 75]
        # Intersection: 50x50 = 2500, Union: 10000 + 2500 - 2500 = 10000
        assert compute_iou(box_a, box_b) == pytest.approx(2500.0 / 10000.0)

    def test_zero_area_box(self):
        box_a = [0, 0, 0, 0]
        box_b = [0, 0, 100, 100]
        assert compute_iou(box_a, box_b) == pytest.approx(0.0)


class TestMatchDetections:
    def test_empty_teacher(self):
        matched, unmatched_t, unmatched_s = match_detections(
            [], [], [[0, 0, 50, 50]], [0.9]
        )
        assert matched == []
        assert unmatched_t == []
        assert unmatched_s == [0]

    def test_empty_student(self):
        matched, unmatched_t, unmatched_s = match_detections(
            [[0, 0, 50, 50]], [0.9], [], []
        )
        assert matched == []
        assert unmatched_t == [0]
        assert unmatched_s == []

    def test_perfect_match(self):
        boxes = [[0, 0, 100, 100]]
        scores = [0.9]
        matched, unmatched_t, unmatched_s = match_detections(
            boxes, scores, boxes, scores, iou_threshold=0.5
        )
        assert len(matched) == 1
        assert matched[0] == (0, 0)
        assert unmatched_t == []
        assert unmatched_s == []

    def test_no_match_low_iou(self):
        t_boxes = [[0, 0, 50, 50]]
        s_boxes = [[200, 200, 300, 300]]
        matched, unmatched_t, unmatched_s = match_detections(
            t_boxes, [0.9], s_boxes, [0.8], iou_threshold=0.5
        )
        assert matched == []
        assert unmatched_t == [0]
        assert unmatched_s == [0]


class TestDistillationScore:
    def test_both_empty(self):
        result = compute_distillation_score([], [], [], [], [], [])
        assert result['score'] == pytest.approx(1.0)

    def test_teacher_empty_student_has_detections(self):
        result = compute_distillation_score(
            [], [], [],
            [[0, 0, 50, 50]], [0.9], [0],
        )
        assert result['score'] == pytest.approx(0.0)
        assert result['false_positive_count'] == 1

    def test_perfect_match(self):
        boxes = [[0, 0, 100, 100]]
        scores = [0.95]
        class_ids = [0]
        result = compute_distillation_score(
            boxes, scores, class_ids,
            boxes, scores, class_ids,
        )
        assert result['score'] > 0.9
        assert result['matched_count'] == 1
        assert result['missed_count'] == 0
        assert result['false_positive_count'] == 0
        assert result['avg_iou'] == pytest.approx(1.0)

    def test_partial_match(self):
        t_boxes = [[0, 0, 100, 100], [200, 200, 300, 300]]
        t_scores = [0.9, 0.8]
        t_classes = [0, 1]

        s_boxes = [[5, 5, 105, 105]]  # Only matches first teacher box
        s_scores = [0.85]
        s_classes = [0]

        result = compute_distillation_score(
            t_boxes, t_scores, t_classes,
            s_boxes, s_scores, s_classes,
        )
        assert result['matched_count'] == 1
        assert result['missed_count'] == 1
        assert result['score'] < 1.0
        assert result['score'] > 0.0
