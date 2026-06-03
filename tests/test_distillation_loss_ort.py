#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the ONNX-based set-based distillation loss."""

import numpy as np
import pytest

from node.DLNode.online_training.distillation_loss_ort import (
    compute_distillation_loss_numpy,
    _compute_iou_matrix_numpy,
    _ONNX_AVAILABLE,
)

if _ONNX_AVAILABLE:
    from node.DLNode.online_training.distillation_loss_ort import build_distillation_loss_graph
    import onnx


class TestIoUMatrixNumpy:
    def test_self_iou(self):
        boxes = np.array([[0, 0, 100, 100], [50, 50, 150, 150]], dtype=np.float32)
        iou = _compute_iou_matrix_numpy(boxes, boxes)
        assert iou.shape == (2, 2)
        assert iou[0, 0] == pytest.approx(1.0, abs=1e-4)
        assert iou[1, 1] == pytest.approx(1.0, abs=1e-4)

    def test_no_overlap(self):
        a = np.array([[0, 0, 50, 50]], dtype=np.float32)
        b = np.array([[100, 100, 200, 200]], dtype=np.float32)
        iou = _compute_iou_matrix_numpy(a, b)
        assert iou[0, 0] == pytest.approx(0.0, abs=1e-4)

    def test_partial_overlap(self):
        a = np.array([[0, 0, 100, 100]], dtype=np.float32)
        b = np.array([[50, 50, 150, 150]], dtype=np.float32)
        iou = _compute_iou_matrix_numpy(a, b)
        expected = 2500.0 / 17500.0
        assert iou[0, 0] == pytest.approx(expected, rel=1e-3)

    def test_asymmetric_shapes(self):
        a = np.array([[0, 0, 50, 50], [60, 60, 120, 120]], dtype=np.float32)
        b = np.array([[0, 0, 50, 50]], dtype=np.float32)
        iou = _compute_iou_matrix_numpy(a, b)
        assert iou.shape == (2, 1)
        assert iou[0, 0] == pytest.approx(1.0, abs=1e-4)
        assert iou[1, 0] == pytest.approx(0.0, abs=1e-4)


class TestDistillationLossNumpy:
    def test_both_empty(self):
        result = compute_distillation_loss_numpy(
            np.zeros((0, 4), dtype=np.float32), np.array([], dtype=np.float32),
            np.array([], dtype=np.int64),
            np.zeros((0, 4), dtype=np.float32), np.array([], dtype=np.float32),
            np.array([], dtype=np.int64),
        )
        assert result['loss'] == pytest.approx(0.0, abs=1e-5)
        assert result['loss_count'] == pytest.approx(0.0)

    def test_perfect_match(self):
        boxes = np.array([[10, 10, 90, 90]], dtype=np.float32)
        scores = np.array([0.95], dtype=np.float32)
        classes = np.array([2], dtype=np.int64)
        result = compute_distillation_loss_numpy(
            boxes, scores, classes, boxes, scores, classes, num_classes=5
        )
        assert result['loss_count'] == pytest.approx(0.0)
        assert result['loss_class'] < 0.01  # Same distribution
        assert result['loss_confidence'] < 0.01  # Same confidence
        assert result['loss_spatial'] < 0.05  # Perfect overlap

    def test_count_loss(self):
        boxes_t = np.array([[0, 0, 50, 50], [60, 60, 120, 120]], dtype=np.float32)
        scores_t = np.array([0.9, 0.8], dtype=np.float32)
        classes_t = np.array([0, 1], dtype=np.int64)

        boxes_s = np.array([[5, 5, 55, 55]], dtype=np.float32)
        scores_s = np.array([0.85], dtype=np.float32)
        classes_s = np.array([0], dtype=np.int64)

        result = compute_distillation_loss_numpy(
            boxes_t, scores_t, classes_t,
            boxes_s, scores_s, classes_s, num_classes=5
        )
        # Count loss = (2-1)^2 = 1.0
        assert result['loss_count'] == pytest.approx(1.0)

    def test_different_classes_penalized(self):
        boxes = np.array([[0, 0, 100, 100]], dtype=np.float32)
        scores = np.array([0.9], dtype=np.float32)
        result = compute_distillation_loss_numpy(
            boxes, scores, np.array([0], dtype=np.int64),
            boxes, scores, np.array([3], dtype=np.int64),
            num_classes=5,
        )
        assert result['loss_class'] > 0.5

    def test_no_spatial_overlap_high_loss(self):
        boxes_t = np.array([[0, 0, 50, 50]], dtype=np.float32)
        boxes_s = np.array([[200, 200, 300, 300]], dtype=np.float32)
        scores = np.array([0.9], dtype=np.float32)
        classes = np.array([0], dtype=np.int64)
        result = compute_distillation_loss_numpy(
            boxes_t, scores, classes,
            boxes_s, scores, classes, num_classes=5,
        )
        assert result['loss_spatial'] > 0.5

    def test_many_student_few_teacher(self):
        """Student has more detections than teacher → count penalty."""
        boxes_t = np.array([[50, 50, 150, 150]], dtype=np.float32)
        scores_t = np.array([0.9], dtype=np.float32)
        classes_t = np.array([0], dtype=np.int64)

        boxes_s = np.array([[0, 0, 50, 50], [50, 50, 100, 100],
                            [100, 100, 200, 200], [200, 200, 300, 300]],
                           dtype=np.float32)
        scores_s = np.array([0.8, 0.7, 0.6, 0.5], dtype=np.float32)
        classes_s = np.array([0, 0, 1, 2], dtype=np.int64)

        result = compute_distillation_loss_numpy(
            boxes_t, scores_t, classes_t,
            boxes_s, scores_s, classes_s, num_classes=5,
        )
        # Count loss = (1-4)^2 = 9.0
        assert result['loss_count'] == pytest.approx(9.0)
        assert result['loss'] > 1.0

    def test_teacher_only_has_detections(self):
        boxes_t = np.array([[0, 0, 100, 100]], dtype=np.float32)
        scores_t = np.array([0.9], dtype=np.float32)
        classes_t = np.array([0], dtype=np.int64)
        result = compute_distillation_loss_numpy(
            boxes_t, scores_t, classes_t,
            np.zeros((0, 4), dtype=np.float32),
            np.array([], dtype=np.float32),
            np.array([], dtype=np.int64),
            num_classes=5,
        )
        assert result['loss_count'] == pytest.approx(1.0)
        assert result['loss_spatial'] == pytest.approx(1.0)


@pytest.mark.skipif(not _ONNX_AVAILABLE, reason="onnx not installed")
class TestBuildONNXLossGraph:
    def test_graph_valid(self):
        model = build_distillation_loss_graph(num_classes=5)
        assert model is not None
        onnx.checker.check_model(model)

    def test_graph_has_correct_io(self):
        model = build_distillation_loss_graph(num_classes=5)
        graph = model.graph
        input_names = [i.name for i in graph.input]
        output_names = [o.name for o in graph.output]
        assert "boxes_t" in input_names
        assert "scores_t" in input_names
        assert "classes_t" in input_names
        assert "boxes_s" in input_names
        assert "scores_s" in input_names
        assert "classes_s" in input_names
        assert "total_loss" in output_names
        assert "loss_class" in output_names
        assert "loss_count" in output_names
        assert "loss_confidence" in output_names
        assert "loss_spatial" in output_names


@pytest.mark.skipif(not _ONNX_AVAILABLE, reason="onnx not installed")
class TestONNXLossRuntime:
    """Test the ONNX loss graph execution with onnxruntime."""

    @pytest.fixture
    def session(self, tmp_path):
        import onnxruntime
        model = build_distillation_loss_graph(num_classes=5)
        path = str(tmp_path / "loss.onnx")
        onnx.save(model, path)
        return onnxruntime.InferenceSession(path, providers=["CPUExecutionProvider"])

    def test_perfect_match(self, session):
        boxes = np.array([[10, 10, 90, 90]], dtype=np.float32)
        scores = np.array([0.95], dtype=np.float32)
        classes = np.array([2], dtype=np.int64)
        results = session.run(None, {
            "boxes_t": boxes, "scores_t": scores, "classes_t": classes,
            "boxes_s": boxes, "scores_s": scores, "classes_s": classes,
        })
        total_loss = float(results[0])
        assert total_loss < 0.2  # Near-zero loss for identical predictions

    def test_count_mismatch(self, session):
        boxes_t = np.array([[0, 0, 50, 50], [60, 60, 120, 120]], dtype=np.float32)
        scores_t = np.array([0.9, 0.8], dtype=np.float32)
        classes_t = np.array([0, 1], dtype=np.int64)

        boxes_s = np.array([[5, 5, 55, 55]], dtype=np.float32)
        scores_s = np.array([0.85], dtype=np.float32)
        classes_s = np.array([0], dtype=np.int64)

        results = session.run(None, {
            "boxes_t": boxes_t, "scores_t": scores_t, "classes_t": classes_t,
            "boxes_s": boxes_s, "scores_s": scores_s, "classes_s": classes_s,
        })
        loss_count = float(results[2])
        assert loss_count == pytest.approx(1.0, abs=0.01)
