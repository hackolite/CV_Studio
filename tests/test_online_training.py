#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for online training distillation loss module."""

import numpy as np
import pytest

from node.DLNode.online_training.distillation_loss import (
    compute_iou,
    match_detections,
    compute_distillation_score,
    _class_distribution_similarity,
    _count_ratio_score,
    _confidence_alignment,
    _spatial_coverage_score,
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


class TestClassDistributionSimilarity:
    def test_both_empty(self):
        assert _class_distribution_similarity([], []) == pytest.approx(1.0)

    def test_one_empty(self):
        assert _class_distribution_similarity([0, 1], []) == pytest.approx(0.0)

    def test_identical(self):
        assert _class_distribution_similarity([0, 1, 1], [0, 1, 1]) == pytest.approx(1.0)

    def test_same_distribution_different_counts(self):
        # Same proportions: 1 class-0, 2 class-1 vs 2 class-0, 4 class-1
        sim = _class_distribution_similarity([0, 1, 1], [0, 0, 1, 1, 1, 1])
        assert sim == pytest.approx(1.0, abs=0.01)

    def test_completely_different(self):
        sim = _class_distribution_similarity([0, 0, 0], [1, 1, 1])
        assert sim == pytest.approx(0.0)


class TestCountRatioScore:
    def test_equal_counts(self):
        assert _count_ratio_score(5, 5) == pytest.approx(1.0)

    def test_one_zero(self):
        assert _count_ratio_score(5, 0) == pytest.approx(0.0)

    def test_both_zero(self):
        assert _count_ratio_score(0, 0) == pytest.approx(1.0)

    def test_different_counts(self):
        assert _count_ratio_score(2, 4) == pytest.approx(0.5)
        assert _count_ratio_score(4, 2) == pytest.approx(0.5)

    def test_close_counts(self):
        assert _count_ratio_score(9, 10) == pytest.approx(0.9)


class TestConfidenceAlignment:
    def test_both_empty(self):
        assert _confidence_alignment([], []) == pytest.approx(1.0)

    def test_one_empty(self):
        assert _confidence_alignment([0.9], []) == pytest.approx(0.0)

    def test_identical(self):
        assert _confidence_alignment([0.9, 0.8], [0.9, 0.8]) == pytest.approx(1.0)

    def test_different_means(self):
        # Mean diff of 0.5 → mean_score = 0.5
        score = _confidence_alignment([0.9], [0.4])
        assert score < 0.8


class TestSpatialCoverageScore:
    def test_both_empty(self):
        assert _spatial_coverage_score([], []) == pytest.approx(1.0)

    def test_one_empty(self):
        assert _spatial_coverage_score([[0, 0, 50, 50]], []) == pytest.approx(0.0)

    def test_identical_boxes(self):
        boxes = [[0, 0, 100, 100]]
        assert _spatial_coverage_score(boxes, boxes) == pytest.approx(1.0)

    def test_non_overlapping(self):
        t_boxes = [[0, 0, 30, 30]]
        s_boxes = [[70, 70, 100, 100]]
        score = _spatial_coverage_score(t_boxes, s_boxes)
        assert score < 0.5


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
        assert result['student_count'] == 1

    def test_student_empty_teacher_has_detections(self):
        result = compute_distillation_score(
            [[0, 0, 50, 50]], [0.9], [0],
            [], [], [],
        )
        assert result['score'] == pytest.approx(0.0)
        assert result['teacher_count'] == 1

    def test_perfect_match(self):
        boxes = [[0, 0, 100, 100]]
        scores = [0.95]
        class_ids = [0]
        result = compute_distillation_score(
            boxes, scores, class_ids,
            boxes, scores, class_ids,
        )
        assert result['score'] > 0.9
        assert result['class_similarity'] == pytest.approx(1.0)
        assert result['count_ratio'] == pytest.approx(1.0)
        assert result['confidence_alignment'] == pytest.approx(1.0)
        assert result['spatial_coverage'] == pytest.approx(1.0)

    def test_different_counts_same_region(self):
        """Teacher has 2 detections, student has 1, but same class and region."""
        t_boxes = [[0, 0, 100, 100], [10, 10, 90, 90]]
        t_scores = [0.9, 0.8]
        t_classes = [0, 0]

        s_boxes = [[5, 5, 95, 95]]
        s_scores = [0.85]
        s_classes = [0]

        result = compute_distillation_score(
            t_boxes, t_scores, t_classes,
            s_boxes, s_scores, s_classes,
        )
        # Should still get a reasonable score because:
        # - same class distribution
        # - similar spatial coverage
        # - close confidences
        # - count ratio = 0.5 (penalty but not zero)
        assert result['score'] > 0.5
        assert result['class_similarity'] == pytest.approx(1.0)
        assert result['count_ratio'] == pytest.approx(0.5)
        assert result['spatial_coverage'] > 0.5

    def test_different_classes_penalized(self):
        """Same region and count but different classes → lower score."""
        boxes = [[0, 0, 100, 100]]
        result = compute_distillation_score(
            boxes, [0.9], [0],
            boxes, [0.9], [1],
        )
        assert result['score'] < 0.9
        assert result['class_similarity'] == pytest.approx(0.0)

    def test_many_student_few_teacher(self):
        """Student has many more detections than teacher."""
        t_boxes = [[50, 50, 150, 150]]
        t_scores = [0.9]
        t_classes = [0]

        s_boxes = [[0, 0, 50, 50], [50, 50, 100, 100], [100, 100, 200, 200],
                   [200, 200, 300, 300], [300, 300, 400, 400]]
        s_scores = [0.8, 0.7, 0.6, 0.5, 0.4]
        s_classes = [0, 0, 1, 1, 2]

        result = compute_distillation_score(
            t_boxes, t_scores, t_classes,
            s_boxes, s_scores, s_classes,
        )
        # Count ratio = 1/5 = 0.2, class similarity low → score should be low
        assert result['score'] < 0.5
        assert result['count_ratio'] == pytest.approx(0.2)
