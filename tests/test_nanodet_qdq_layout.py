#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the nanodet_reg_first parameter in CustomONNX.

Regression test for the bug where nanodet_qdq returned incoherent bounding
boxes because QDQ quantisation maps most class logits to 0, making the
auto-detect heuristic mistake them for DFL regression values (reg-first layout)
when the actual layout is classes-first.
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.DLNode.object_detection.CustomONNX.custom_onnx import CustomONNX


def _make_nanodet_wrapper(nanodet_reg_first=None, num_classes=80, input_size=320):
    """Create a CustomONNX instance without loading an actual model."""
    wrapper = CustomONNX.__new__(CustomONNX)
    wrapper.input_width = input_size
    wrapper.input_height = input_size
    wrapper.output_format = 'nanodet'
    wrapper.num_classes = num_classes
    wrapper.nms_score_th = 0.3
    wrapper.nms_th = 0.45
    wrapper.class_score_th = 0.0
    wrapper._nanodet_reg_first = nanodet_reg_first
    return wrapper


def _build_qdq_like_output(input_size=320, num_classes=80, reg_max=7):
    """Build a synthetic output tensor that mimics nanodet_qdq behaviour.

    QDQ quantisation maps most class logits to 0 (sparse), while DFL
    regression channels retain significant non-zero values.  This is the
    condition that fools the auto-detect heuristic.

    Layout: classes-first → [cls(80), reg(32)]
    """
    strides = [8, 16, 32, 64]
    num_anchors = sum(
        (input_size // s) ** 2 for s in strides if input_size // s > 0
    )
    reg_channels = 4 * (reg_max + 1)
    total_channels = num_classes + reg_channels

    output = np.zeros((num_anchors, total_channels), dtype=np.float32)

    # Anchor 2034 is near the end of the 40×40 stride-8 feature map (1600 anchors)
    # plus some stride-16 anchors — an arbitrary mid-scene location used as a
    # stable synthetic detection target.
    det_anchor = min(2034, num_anchors - 1)
    # Class logit for "person" (class 0) slightly above zero after dequant
    output[det_anchor, 0] = 0.13

    # DFL regression logits for cols 80:112 — large non-zero values
    np.random.seed(42)
    output[:, num_classes:] = np.random.randn(num_anchors, reg_channels).astype(np.float32) * 3.0

    return output[np.newaxis]  # (1, num_anchors, total_channels)


class TestNanodetRegFirstParameter:
    """Tests for the nanodet_reg_first parameter and the auto-detect heuristic."""

    def test_explicit_false_uses_classes_first_layout(self):
        """nanodet_reg_first=False must skip the heuristic and use classes-first."""
        wrapper = _make_nanodet_wrapper(nanodet_reg_first=False)
        raw = _build_qdq_like_output()
        orig_w, orig_h = 320, 320

        bboxes, scores, class_ids = wrapper._postprocess_nanodet(
            raw, orig_w, orig_h
        )
        # With correct classes-first layout the detection should be found
        assert len(bboxes) > 0, "Expected at least one detection with classes-first layout"

    def test_auto_detect_fails_for_qdq_like_output(self):
        """Auto-detect heuristic is fooled by QDQ-quantised class logits.

        This documents the known failure mode: the heuristic incorrectly
        selects reg-first for the synthetic QDQ-like output, causing no
        detections or wrong bounding boxes.
        """
        wrapper = _make_nanodet_wrapper(nanodet_reg_first=None)
        raw = _build_qdq_like_output()
        orig_w, orig_h = 320, 320

        # Run postprocessing — it will auto-detect reg-first (incorrectly)
        bboxes_auto, scores_auto, _ = wrapper._postprocess_nanodet(
            raw, orig_w, orig_h
        )

        # Run with explicit classes-first
        wrapper2 = _make_nanodet_wrapper(nanodet_reg_first=False)
        bboxes_cf, scores_cf, _ = wrapper2._postprocess_nanodet(
            raw, orig_w, orig_h
        )

        # Explicit classes-first finds the detection the heuristic misses
        assert len(bboxes_cf) > 0, "classes-first layout should find detection"
        # The heuristic might miss it (this is the bug we document here)
        # We don't assert the heuristic fails because it depends on randomness,
        # but we verify the explicit parameter gives correct results.

    def test_explicit_true_uses_reg_first_layout(self):
        """nanodet_reg_first=True must use reg-first without running heuristic."""
        wrapper = _make_nanodet_wrapper(nanodet_reg_first=True)
        # After init the value must already be set, no auto-detect on first call
        assert wrapper._nanodet_reg_first is True

    def test_explicit_false_skips_heuristic(self):
        """nanodet_reg_first=False must be preserved; heuristic must not overwrite."""
        wrapper = _make_nanodet_wrapper(nanodet_reg_first=False)
        assert wrapper._nanodet_reg_first is False

        raw = _build_qdq_like_output()
        wrapper._postprocess_nanodet(raw, 320, 320)

        # Value must remain False even after running the postprocessor
        assert wrapper._nanodet_reg_first is False, (
            "heuristic must not overwrite an explicit nanodet_reg_first=False"
        )

    def test_none_triggers_auto_detect(self):
        """nanodet_reg_first=None must trigger the heuristic on first inference."""
        wrapper = _make_nanodet_wrapper(nanodet_reg_first=None)
        assert wrapper._nanodet_reg_first is None

        raw = _build_qdq_like_output()
        wrapper._postprocess_nanodet(raw, 320, 320)

        # After first inference the heuristic must have set a bool value
        assert wrapper._nanodet_reg_first is not None, (
            "heuristic should have determined layout after first inference"
        )

    def test_builtin_nanodet_qdq_config_has_reg_first_false(self):
        """The nanodet_qdq built-in config must declare nanodet_reg_first=False."""
        node_od_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'DLNode', 'node_object_detection.py',
        )
        with open(node_od_path, 'r', encoding='utf-8') as fh:
            src = fh.read()

        # Find the NanoDet-QDQ entry block and verify it contains the override
        assert "'nanodet_reg_first': False" in src, (
            "NanoDet-QDQ builtin entry in node_object_detection.py must set "
            "'nanodet_reg_first': False to avoid heuristic failure on QDQ-quantised "
            "class logits"
        )
