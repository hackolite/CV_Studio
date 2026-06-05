#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regression test for the OpenCV Zoo NanoDet (multi-head) over-detection bug.

``object_detection_nanodet_2022nov.onnx`` exports its classification heads with
the sigmoid activation baked into the graph (scores already in [0, 1]) while the
regression heads remain raw logits.  The shared ``_postprocess_nanodet`` used to
unconditionally apply sigmoid again, mapping every near-zero probability to
~0.5.  Every anchor then cleared the score threshold and NMS emitted a flood of
bounding boxes.  The combined [cls, reg] layout also fooled the statistical
layout heuristic into picking a reg-first layout.

These tests pin both fixes:
  * the multi-head path forces a classes-first layout, and
  * already-activated class scores are not passed through sigmoid twice.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.DLNode.object_detection.CustomONNX.custom_onnx import CustomONNX


def _make_wrapper(num_classes=80, input_size=416):
    """Create a CustomONNX instance without loading an actual model."""
    wrapper = CustomONNX.__new__(CustomONNX)
    wrapper.input_width = input_size
    wrapper.input_height = input_size
    wrapper.output_format = 'nanodet_multi'
    wrapper.num_classes = num_classes
    wrapper.nms_score_th = 0.3
    wrapper.nms_th = 0.45
    wrapper.class_score_th = 0.0
    wrapper._nanodet_reg_first = None
    return wrapper


def _build_multi_head_outputs(input_size=416, num_classes=80, reg_max=7,
                              det_prob=0.9, background_prob=0.02):
    """Build synthetic multi-head outputs mimicking OpenCV Zoo NanoDet.

    Classification heads are *already* sigmoid-activated (values in [0, 1]);
    regression heads are raw DFL logits.  One anchor on the stride-8 head holds
    a confident person detection, the rest are low-probability background.
    """
    strides = [8, 16, 32]
    reg_channels = 4 * (reg_max + 1)

    np.random.seed(7)
    cls_outputs = []
    reg_outputs = []
    for s in strides:
        n = (input_size // s) ** 2
        cls = np.full((1, n, num_classes), background_prob, dtype=np.float32)
        reg = (np.random.randn(1, n, reg_channels).astype(np.float32) * 2.0)
        cls_outputs.append(cls)
        reg_outputs.append(reg)

    # Plant one confident detection (class 0 / person) on the stride-8 head.
    cls_outputs[0][0, 100, 0] = det_prob
    # Modest, centred box for that anchor (small positive DFL logits).
    reg_outputs[0][0, 100, :] = 0.5

    # Interleave as the ONNX runtime would return them (cls heads, reg heads).
    return cls_outputs + reg_outputs


def test_multi_head_preactivated_does_not_flood():
    """Already-activated class scores must not be re-sigmoided into a flood."""
    wrapper = _make_wrapper()
    outputs = _build_multi_head_outputs()

    bboxes, scores, class_ids = wrapper._postprocess_nanodet_multi(
        outputs, 640, 480
    )

    # Background probability 0.02 stays below the 0.3 threshold, so only the
    # single planted detection should survive — not hundreds of phantom boxes.
    assert len(bboxes) <= 5, (
        f"Expected a handful of detections, got {len(bboxes)} — sigmoid was "
        f"likely applied twice to already-activated scores."
    )
    assert len(bboxes) >= 1, "The confident planted detection should be found."
    assert 0 in list(class_ids), "Planted person (class 0) should be detected."


def test_double_sigmoid_would_flood_without_fix():
    """Sanity check: re-sigmoiding the activated scores reproduces the flood."""
    wrapper = _make_wrapper()
    outputs = _build_multi_head_outputs()

    # Force the historical buggy behaviour: apply sigmoid to already-activated
    # scores and let the heuristic pick the (wrong) layout.
    combined_cls = np.concatenate(
        [o.reshape(-1, wrapper.num_classes) for o in outputs[:3]], axis=0
    )
    # All class scores are in [0, 1]; sigmoid maps the 0.02 background to ~0.505,
    # which clears the 0.3 threshold for every one of the thousands of anchors.
    flooded = 1.0 / (1.0 + np.exp(-combined_cls))
    assert (flooded.max(axis=1) >= wrapper.nms_score_th).sum() > 1000, (
        "Synthetic data should demonstrate the flood when sigmoid is reapplied."
    )


def test_explicit_pre_activated_flag_skips_sigmoid():
    """cls_pre_activated=True keeps activated scores unchanged."""
    wrapper = _make_wrapper()
    num_anchors = 3549
    reg_channels = 32
    total = wrapper.num_classes + reg_channels
    raw = np.zeros((1, num_anchors, total), dtype=np.float32)
    # Activated probability 0.8 for class 0 at one anchor; classes-first layout.
    raw[0, 10, 0] = 0.8
    raw[0, 10, wrapper.num_classes:] = 0.5

    bboxes, scores, _ = wrapper._postprocess_nanodet(
        raw, 640, 480, cls_pre_activated=True, reg_first_override=False
    )
    assert len(bboxes) >= 1
    # Score is preserved (≈0.8), not squashed toward 0.69 by a second sigmoid.
    assert scores.max() > 0.7


if __name__ == '__main__':
    test_multi_head_preactivated_does_not_flood()
    test_double_sigmoid_would_flood_without_fix()
    test_explicit_pre_activated_flag_skips_sigmoid()
    print("All NanoDet multi-head pre-activation tests passed.")
