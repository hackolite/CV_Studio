#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for SSD output format support in CustomONNX and onnx_inspector.
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.DLNode.object_detection.CustomONNX.custom_onnx import CustomONNX


def _make_ssd_wrapper(**kwargs):
    """Create a CustomONNX instance without loading an actual model."""
    wrapper = CustomONNX.__new__(CustomONNX)
    wrapper.input_width = kwargs.get('input_width', 300)
    wrapper.input_height = kwargs.get('input_height', 300)
    wrapper.output_format = 'ssd'
    wrapper.num_classes = kwargs.get('num_classes', 91)
    wrapper.nms_score_th = kwargs.get('nms_score_th', 0.3)
    wrapper.nms_th = kwargs.get('nms_th', 0.45)
    wrapper.class_score_th = 0.0
    return wrapper


class TestSSDPostprocess:
    """Test _postprocess_ssd with various SSD output patterns."""

    def test_pattern_a_boxes_classes_scores_numdet(self):
        """Pattern A: [boxes, class_ids, scores, num_det] (TF-exported)."""
        wrapper = _make_ssd_wrapper()
        boxes = np.zeros((1, 10, 4), dtype=np.float32)
        boxes[0, 0] = [0.1, 0.2, 0.5, 0.8]  # y1, x1, y2, x2 normalised
        boxes[0, 1] = [0.3, 0.1, 0.7, 0.6]

        class_ids = np.zeros((1, 10), dtype=np.float32)
        class_ids[0, 0] = 1
        class_ids[0, 1] = 3

        scores = np.zeros((1, 10), dtype=np.float32)
        scores[0, 0] = 0.95
        scores[0, 1] = 0.85

        num_det = np.array([2], dtype=np.float32)

        bboxes, s, cids = wrapper._postprocess_ssd(
            [boxes, class_ids, scores, num_det], 640, 480
        )
        assert len(bboxes) == 2
        assert s[0] == pytest.approx(0.95, abs=0.01)
        assert s[1] == pytest.approx(0.85, abs=0.01)
        assert int(cids[0]) == 1
        assert int(cids[1]) == 3

    def test_pattern_c_boxes_scores_only(self):
        """Pattern C: [boxes, scores] (minimal, e.g. Kalray)."""
        wrapper = _make_ssd_wrapper()
        boxes = np.array([[[0.1, 0.1, 0.5, 0.5],
                           [0.2, 0.2, 0.6, 0.6]]], dtype=np.float32)
        scores = np.array([[0.9, 0.7]], dtype=np.float32)

        bboxes, s, cids = wrapper._postprocess_ssd([boxes, scores], 800, 600)
        assert len(bboxes) == 2
        # class_ids default to 0
        assert np.all(cids == 0)

    def test_no_detections_above_threshold(self):
        """All scores below threshold → empty."""
        wrapper = _make_ssd_wrapper(nms_score_th=0.5)
        boxes = np.array([[[0.1, 0.1, 0.5, 0.5]]], dtype=np.float32)
        scores = np.array([[0.2]], dtype=np.float32)

        bboxes, s, cids = wrapper._postprocess_ssd([boxes, scores], 640, 480)
        assert len(bboxes) == 0

    def test_num_detections_clips_output(self):
        """num_detections tensor should limit the number of valid boxes."""
        wrapper = _make_ssd_wrapper()
        boxes = np.zeros((1, 100, 4), dtype=np.float32)
        boxes[0, 0] = [0.1, 0.1, 0.5, 0.5]
        scores = np.zeros((1, 100), dtype=np.float32)
        scores[0, 0] = 0.9
        num_det = np.array([1], dtype=np.float32)

        bboxes, s, cids = wrapper._postprocess_ssd(
            [boxes, scores, num_det], 640, 480
        )
        assert len(bboxes) == 1

    def test_empty_outputs(self):
        """Zero outputs → empty detections."""
        wrapper = _make_ssd_wrapper()
        bboxes, s, cids = wrapper._postprocess_ssd([], 640, 480)
        assert len(bboxes) == 0

    def test_normalised_box_coordinates(self):
        """Verify normalised [0,1] box coords are properly scaled to image size."""
        wrapper = _make_ssd_wrapper()
        # Box: y1=0.0, x1=0.0, y2=1.0, x2=1.0 → full image
        boxes = np.array([[[0.0, 0.0, 1.0, 1.0]]], dtype=np.float32)
        scores = np.array([[0.9]], dtype=np.float32)

        bboxes, s, cids = wrapper._postprocess_ssd([boxes, scores], 800, 600)
        assert len(bboxes) == 1
        x1, y1, x2, y2 = bboxes[0]
        assert x1 == 0
        assert y1 == 0
        assert x2 == 800
        assert y2 == 600


class TestSSDInspector:
    """Test that onnx_inspector detects SSD models correctly."""

    def test_detect_ssd_multi_output(self):
        """Multi-output model with boxes tensor (last dim==4) → 'ssd'."""
        try:
            import onnx
            from onnx import helper, TensorProto
        except ImportError:
            pytest.skip("onnx package not installed")

        X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 300, 300])
        boxes_out = helper.make_tensor_value_info('boxes', TensorProto.FLOAT, [1, 100, 4])
        scores_out = helper.make_tensor_value_info('scores', TensorProto.FLOAT, [1, 100])

        shape1 = helper.make_tensor('s1', TensorProto.INT64, [3], [1, 100, 4])
        shape2 = helper.make_tensor('s2', TensorProto.INT64, [2], [1, 100])
        n1 = helper.make_node('ConstantOfShape', ['s1'], ['boxes'],
                              value=helper.make_tensor('v', TensorProto.FLOAT, [1], [0.0]))
        n2 = helper.make_node('ConstantOfShape', ['s2'], ['scores'],
                              value=helper.make_tensor('v2', TensorProto.FLOAT, [1], [0.0]))

        graph = helper.make_graph([n1, n2], 'ssd', [X], [boxes_out, scores_out],
                                  initializer=[shape1, shape2])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
        model.ir_version = 7

        path = '/tmp/test_ssd_inspector.onnx'
        onnx.save(model, path)

        from node.DLNode.object_detection.onnx_inspector import inspect_onnx_model
        result = inspect_onnx_model(path)
        assert result['output_format'] == 'ssd'
        assert result['input_width'] == 300
        assert result['input_height'] == 300

    def test_single_output_not_ssd(self):
        """Single-output YOLO model should NOT be detected as SSD."""
        try:
            import onnx
            from onnx import helper, TensorProto
        except ImportError:
            pytest.skip("onnx package not installed")

        X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 640, 640])
        Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 84, 8400])

        shape_init = helper.make_tensor('s', TensorProto.INT64, [3], [1, 84, 8400])
        node = helper.make_node('ConstantOfShape', ['s'], ['output'],
                                value=helper.make_tensor('v', TensorProto.FLOAT, [1], [0.0]))

        graph = helper.make_graph([node], 'yolo', [X], [Y], initializer=[shape_init])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
        model.ir_version = 7

        path = '/tmp/test_yolo_inspector.onnx'
        onnx.save(model, path)

        from node.DLNode.object_detection.onnx_inspector import inspect_onnx_model
        result = inspect_onnx_model(path)
        assert result['output_format'] == 'yolo11'
