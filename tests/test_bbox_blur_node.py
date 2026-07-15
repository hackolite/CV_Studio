#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for the BBoxBlur node's core logic.

Covers:
- _extract_bboxes_scores with ObjectDetection (bboxes key) format
- _extract_bboxes_scores with FaceDetection (results_list key) format
- _blur_bboxes applies Gaussian blur inside the correct regions
- Implicit JSON-from-image-source fallback in the update connection resolver
"""
import sys
import os
import copy

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Import only the pure-Python helpers – avoids the DearPyGUI / OpenCV GUI dep
# ---------------------------------------------------------------------------
from node.ProcessNode.node_bbox_blur import (
    _extract_bboxes_scores,
    _blur_bboxes,
    _resolve_connection_sources,
)


# ============================================================
# _extract_bboxes_scores
# ============================================================

class TestExtractBboxesScores:
    """Tests for the JSON-format-agnostic bbox/score extractor."""

    def test_object_detection_format_with_detections(self):
        """ObjectDetection result with bounding boxes is parsed correctly."""
        od_result = {
            'bboxes': [[10.0, 20.0, 110.0, 120.0], [200.0, 200.0, 300.0, 300.0]],
            'scores': [0.9, 0.75],
            'class_ids': [0, 0],
            'class_names': {0: 'person'},
            'score_th': 0.3,
        }
        bboxes, scores = _extract_bboxes_scores(od_result)
        assert bboxes == [[10.0, 20.0, 110.0, 120.0], [200.0, 200.0, 300.0, 300.0]]
        assert scores == [0.9, 0.75]

    def test_object_detection_format_empty(self):
        """ObjectDetection result with no detections returns empty lists."""
        od_empty = {
            'bboxes': [],
            'scores': [],
            'class_ids': [],
            'class_names': {0: 'person'},
            'score_th': 0.3,
        }
        bboxes, scores = _extract_bboxes_scores(od_empty)
        assert bboxes == []
        assert scores == []

    def test_face_detection_yunet_mediapipe_format(self):
        """FaceDetection results_list format (YuNet / MediaPipe) is parsed correctly."""
        fd_result = {
            'model_name': 'YuNet',
            'score_th': 0.5,
            'results_list': [
                {0: [100, 100, 0.9], 'bbox': [80, 80, 180, 180]},
                {0: [210, 200, 0.8], 'bbox': [190, 190, 280, 280]},
            ],
        }
        bboxes, scores = _extract_bboxes_scores(fd_result)
        assert bboxes == [[80, 80, 180, 180], [190, 190, 280, 280]]
        assert scores == pytest.approx([0.9, 0.8])

    def test_face_detection_no_keypoint_defaults_score_1(self):
        """A face entry without a keypoint gets a default score of 1.0."""
        fd_result = {
            'results_list': [
                {'bbox': [10, 10, 50, 50]},  # no keypoints
            ]
        }
        bboxes, scores = _extract_bboxes_scores(fd_result)
        assert bboxes == [[10, 10, 50, 50]]
        assert scores == [1.0]

    def test_unknown_format_returns_empty(self):
        """JSON with neither 'bboxes' nor 'results_list' returns empty lists."""
        bboxes, scores = _extract_bboxes_scores({'some_key': 'some_value'})
        assert bboxes == []
        assert scores == []


# ============================================================
# _blur_bboxes
# ============================================================

class TestBlurBboxes:
    """Tests for the Gaussian-blur-inside-bbox helper."""

    def _grey_frame(self, h=200, w=200):
        return np.full((h, w, 3), 128, dtype=np.uint8)

    def test_blur_is_applied_inside_bbox(self):
        frame = self._grey_frame()
        frame[60:70, 60:70] = 255   # small bright square inside bbox
        original_frame = frame.copy()
        bboxes = [[50, 50, 150, 150]]
        scores = [0.9]
        result = _blur_bboxes(frame, bboxes, scores, score_th=0.3, kernel_size=15)
        # Outside bbox must be untouched
        assert np.array_equal(result[0:50, 0:50], original_frame[0:50, 0:50])
        # Inside bbox: the bright square should have been smeared out
        assert not np.array_equal(result[60:70, 60:70], original_frame[60:70, 60:70])

    def test_outside_bbox_is_unchanged(self):
        frame = self._grey_frame()
        frame[10:20, 10:20] = 255   # bright area outside the bbox
        original_frame = frame.copy()
        bboxes = [[80, 80, 150, 150]]
        scores = [0.9]
        result = _blur_bboxes(frame, bboxes, scores, score_th=0.3, kernel_size=15)
        assert np.array_equal(result[10:20, 10:20], original_frame[10:20, 10:20])

    def test_score_below_threshold_is_skipped(self):
        frame = self._grey_frame()
        bboxes = [[50, 50, 150, 150]]
        scores = [0.1]  # below threshold of 0.3
        result = _blur_bboxes(frame, bboxes, scores, score_th=0.3, kernel_size=15)
        # Frame must be unchanged (returned copy, but content identical)
        assert np.array_equal(result, frame)

    def test_even_kernel_is_made_odd(self):
        """Even kernel values should not raise an OpenCV error."""
        frame = self._grey_frame()
        bboxes = [[20, 20, 100, 100]]
        scores = [0.9]
        # kernel_size=10 (even) should be bumped to 11 internally
        result = _blur_bboxes(frame, bboxes, scores, score_th=0.0, kernel_size=10)
        assert result.shape == frame.shape

    def test_multiple_bboxes(self):
        frame = self._grey_frame()
        bboxes = [[10, 10, 50, 50], [100, 100, 160, 160]]
        scores = [0.9, 0.8]
        result = _blur_bboxes(frame, bboxes, scores, score_th=0.3, kernel_size=15)
        assert result.shape == frame.shape


# ============================================================
# Implicit JSON fallback in connection resolver
# ============================================================

class TestImplicitJsonFallback:
    """
    Verify that _resolve_connection_sources returns the correct keys and that
    the implicit JSON fallback works when no explicit JSON wire is connected.
    """

    def test_implicit_json_when_only_image_connected(self):
        """
        Only the IMAGE wire is connected; JSON should be fetched implicitly
        from the same source node.
        """
        connection_list = [
            ['0:ObjectDetection:IMAGE:Output01', '1:BBoxBlur:IMAGE:Input01'],
        ]
        src_image_key, src_json_key = _resolve_connection_sources(connection_list)
        assert src_image_key == '0:ObjectDetection'
        assert src_json_key == '0:ObjectDetection', (
            "json key must fall back to image source when no JSON wire exists"
        )

        od_result = {
            'bboxes': [[10.0, 20.0, 110.0, 120.0]],
            'scores': [0.9],
            'class_ids': [0],
            'class_names': {0: 'person'},
        }
        node_image_dict = {'0:ObjectDetection': np.zeros((120, 160, 3), dtype=np.uint8)}
        node_result_dict = {'0:ObjectDetection': od_result}

        frame = node_image_dict.get(src_image_key)
        json_data = node_result_dict.get(src_json_key)
        assert frame is not None, "frame must be retrieved"
        assert json_data is not None, "json_data must be retrieved via implicit fallback"
        assert 'bboxes' in json_data

    def test_explicit_json_takes_priority(self):
        """
        When an explicit JSON wire exists, it is used instead of the fallback.
        """
        connection_list = [
            ['0:ObjectDetection:IMAGE:Output01', '1:BBoxBlur:IMAGE:Input01'],
            ['0:ObjectDetection:JSON:Output03', '1:BBoxBlur:JSON:Input02'],
        ]
        src_image_key, src_json_key = _resolve_connection_sources(connection_list)
        assert src_image_key == '0:ObjectDetection'
        assert src_json_key == '0:ObjectDetection'

        od_result = {'bboxes': [[10.0, 20.0, 110.0, 120.0]], 'scores': [0.9]}
        node_image_dict = {'0:ObjectDetection': np.zeros((120, 160, 3), dtype=np.uint8)}
        node_result_dict = {'0:ObjectDetection': od_result}

        frame = node_image_dict.get(src_image_key)
        json_data = node_result_dict.get(src_json_key)
        assert frame is not None
        assert json_data == od_result

    def test_no_connections_returns_empty_keys(self):
        """No connections at all → both keys are empty strings."""
        src_image_key, src_json_key = _resolve_connection_sources([])
        assert src_image_key == ''
        assert src_json_key == ''
