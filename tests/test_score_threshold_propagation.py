#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for propagating the UI score threshold into the detector.

The ObjectDetection node exposes a score threshold that used to be applied only
when drawing boxes.  Every candidate above the model default (0.1) therefore
went through the full Python/OpenCV NMS path on each frame.  ``CustomONNX`` now
exposes ``set_score_threshold`` so the node can prune candidates earlier.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest.importorskip("cv2")
pytest.importorskip("onnxruntime")

from node.DLNode.object_detection.CustomONNX.custom_onnx import CustomONNX  # noqa: E402


class _StubCustomONNX(CustomONNX):
    """CustomONNX without the ONNX session, to test threshold handling only."""

    def __init__(self, nms_score_th=0.1):
        self.nms_score_th = nms_score_th
        self._default_nms_score_th = nms_score_th


def test_set_score_threshold_raises_threshold():
    model = _StubCustomONNX()
    model.set_score_threshold(0.6)
    assert model.nms_score_th == pytest.approx(0.6)


def test_set_score_threshold_never_goes_below_model_default():
    """A lower UI threshold must not let more candidates through than before."""
    model = _StubCustomONNX(nms_score_th=0.1)
    model.set_score_threshold(0.01)
    assert model.nms_score_th == pytest.approx(0.1)


def test_set_score_threshold_is_not_sticky():
    """Lowering the slider after raising it restores the previous threshold."""
    model = _StubCustomONNX(nms_score_th=0.1)
    model.set_score_threshold(0.9)
    assert model.nms_score_th == pytest.approx(0.9)
    model.set_score_threshold(0.3)
    assert model.nms_score_th == pytest.approx(0.3)


@pytest.mark.parametrize("bad_value", [None, "abc", object()])
def test_set_score_threshold_ignores_invalid_values(bad_value):
    model = _StubCustomONNX(nms_score_th=0.25)
    model.set_score_threshold(bad_value)
    assert model.nms_score_th == pytest.approx(0.25)


def test_node_propagates_score_threshold_to_model():
    """The ObjectDetection node must call set_score_threshold each update."""
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "node", "DLNode", "node_object_detection.py",
    )
    with open(file_path, "r") as handle:
        content = handle.read()

    assert re.search(
        r"hasattr\s*\(\s*model_instance\s*,\s*['\"]set_score_threshold['\"]\s*\)",
        content,
    ), "Node should detect models exposing set_score_threshold"
    assert re.search(
        r"model_instance\.set_score_threshold\s*\(\s*score_th\s*\)", content
    ), "Node should forward the UI score threshold to the model"
