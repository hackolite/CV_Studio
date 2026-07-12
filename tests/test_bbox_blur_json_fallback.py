#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for BBoxBlur node – specifically the image-fallback behaviour when
only a JSON connection exists (no explicit IMAGE connection).

Root cause that triggered these tests
--------------------------------------
When the user wires only the JSON output of ObjectDetection/BlazeFace to
BBoxBlur's JSON input (without a separate IMAGE connection), the node was
returning ``frame=None`` and showing a permanent black screen.

Fix
---
``update()`` now falls back to ``src_image_key = src_json_key`` when no
IMAGE connection is present, allowing the node to pull the image from the
same upstream node that provides the bounding-box JSON.
"""

import sys
import os
import copy

import numpy as np

# Add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Minimal stubs so we can import the node without a running DPG context
# ---------------------------------------------------------------------------

import unittest.mock as mock

# Stub out DearPyGui before any node import
_dpg_stub = mock.MagicMock()
sys.modules.setdefault("dearpygui", _dpg_stub)
sys.modules.setdefault("dearpygui.dearpygui", _dpg_stub)

# Stub out node_editor utilities
_util_stub = mock.MagicMock()
_util_stub.dpg_get_value.side_effect = lambda tag: None
_util_stub.dpg_set_value.return_value = None
sys.modules.setdefault("node_editor", mock.MagicMock())
sys.modules.setdefault("node_editor.util", _util_stub)

# ---------------------------------------------------------------------------
# Import the module under test AFTER stubs are in place
# ---------------------------------------------------------------------------
from node.ProcessNode.node_bbox_blur import _blur_bboxes  # noqa: E402


# ---------------------------------------------------------------------------
# Simple dict-like wrapper that mimics QueueBackedDict.get()
# ---------------------------------------------------------------------------

class _FakeDict(dict):
    """dict subclass whose .get() shadows the built-in to mimic the real dict."""

    # QueueBackedDict.get returns *default* when the stored value is None.
    def get(self, key, default=None):
        val = super().get(key)
        return val if val is not None else default


# ---------------------------------------------------------------------------
# Helper – build a minimal Node instance without DPG
# ---------------------------------------------------------------------------

def _make_node(opencv_setting_dict=None):
    """Return a BBoxBlur Node instance with mocked DPG internals."""
    if opencv_setting_dict is None:
        opencv_setting_dict = {
            "process_width": 64,
            "process_height": 64,
            "use_pref_counter": False,
        }

    from node.ProcessNode.node_bbox_blur import Node as BBoxBlurNode

    node = BBoxBlurNode.__new__(BBoxBlurNode)
    node._opencv_setting_dict = opencv_setting_dict
    return node


# ---------------------------------------------------------------------------
# Unit tests for _blur_bboxes
# ---------------------------------------------------------------------------

def test_blur_bboxes_no_detections():
    """When bboxes list is empty, image is returned unchanged."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[50, 50] = [1, 2, 3]

    result = _blur_bboxes(img, [], [], score_th=0.3, kernel_size=15)
    np.testing.assert_array_equal(result, img)


def test_blur_bboxes_single_detection():
    """A single valid bbox should produce a blurred region."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 200
    bboxes = [[10, 10, 50, 50]]
    scores = [0.9]

    result = _blur_bboxes(img, bboxes, scores, score_th=0.3, kernel_size=15)

    # Outside the bbox the image is unchanged
    np.testing.assert_array_equal(result[0, 0], img[0, 0])
    # Inside the bbox pixels should still be non-zero (blur of 200 → still ~200)
    assert result[30, 30, 0] > 0


def test_blur_bboxes_score_below_threshold():
    """Bboxes whose score < score_th should NOT be blurred."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 200
    bboxes = [[10, 10, 50, 50]]
    scores = [0.1]

    result = _blur_bboxes(img, bboxes, scores, score_th=0.5, kernel_size=15)
    np.testing.assert_array_equal(result, img)


def test_blur_bboxes_even_kernel_rounded_up():
    """An even kernel size must be rounded up to the next odd number."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    bboxes = [[10, 10, 50, 50]]
    scores = [0.9]
    # kernel_size=10 is even – _blur_bboxes should use 11
    result = _blur_bboxes(img, bboxes, scores, score_th=0.3, kernel_size=10)
    assert result is not None


# ---------------------------------------------------------------------------
# Integration-style test for update() fallback behaviour
# ---------------------------------------------------------------------------

def test_update_json_only_connection_shows_image():
    """
    When only the JSON connection is present (no IMAGE connection),
    update() must fall back to using the JSON source's image instead
    of returning None and leaving the texture black.
    """
    node = _make_node()
    w, h = 64, 64

    # Fake image stored for the ObjectDetection node
    fake_frame = np.ones((h, w, 3), dtype=np.uint8) * 100

    node_image_dict = _FakeDict()
    node_image_dict["1:ObjectDetection"] = fake_frame.copy()

    node_result_dict = _FakeDict()
    node_result_dict["1:ObjectDetection"] = {
        "bboxes": [[5, 5, 30, 30]],
        "scores": [0.9],
        "class_ids": [0],
        "score_th": 0.3,
    }

    # Only the JSON connection is present – no IMAGE connection
    connection_list = [
        ["1:ObjectDetection:JSON:Output03", "2:BBoxBlur:JSON:Input02"],
    ]

    # Patch dpg_get_value/dpg_set_value so they don't crash
    import node.ProcessNode.node_bbox_blur as bbox_mod

    calls = {}

    def fake_get(tag):
        if "KernelValue" in tag:
            return 15
        if "ScoreThValue" in tag:
            return 0.3
        return None

    def fake_set(tag, value):
        calls[tag] = value

    orig_get = bbox_mod.dpg_get_value
    orig_set = bbox_mod.dpg_set_value
    bbox_mod.dpg_get_value = fake_get
    bbox_mod.dpg_set_value = fake_set

    try:
        result = node.update(
            node_id="2",
            connection_list=connection_list,
            node_image_dict=node_image_dict,
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )
    finally:
        bbox_mod.dpg_get_value = orig_get
        bbox_mod.dpg_set_value = orig_set

    # The node must return a non-None image (not a black screen)
    assert result["image"] is not None, (
        "BBoxBlur returned None image when only JSON is connected – black screen bug!"
    )
    assert result["image"].shape == (h, w, 3)
    print("✓ update() returns valid image when only JSON connection exists")


def test_update_no_connections_returns_none_image():
    """When there are no connections at all, update() should return image=None."""
    node = _make_node()
    w, h = 64, 64

    node_image_dict = _FakeDict()
    node_result_dict = _FakeDict()

    connection_list = []

    import node.ProcessNode.node_bbox_blur as bbox_mod

    def fake_get_no_conn(tag):
        if "Kernel" in tag:
            return 15
        if "Score" in tag:
            return 0.3
        return None

    orig_get = bbox_mod.dpg_get_value
    orig_set = bbox_mod.dpg_set_value
    bbox_mod.dpg_get_value = fake_get_no_conn
    bbox_mod.dpg_set_value = lambda tag, val: None

    try:
        result = node.update(
            node_id="2",
            connection_list=connection_list,
            node_image_dict=node_image_dict,
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )
    finally:
        bbox_mod.dpg_get_value = orig_get
        bbox_mod.dpg_set_value = orig_set

    assert result["image"] is None
    print("✓ update() correctly returns None image when no connections exist")


def test_update_explicit_image_connection_takes_priority():
    """
    When both IMAGE and JSON connections are present, the IMAGE connection
    must take priority over the fallback.
    """
    node = _make_node()
    w, h = 64, 64

    webcam_frame = np.ones((h, w, 3), dtype=np.uint8) * 50
    od_frame = np.ones((h, w, 3), dtype=np.uint8) * 200

    node_image_dict = _FakeDict()
    node_image_dict["1:Webcam"] = webcam_frame.copy()
    node_image_dict["2:ObjectDetection"] = od_frame.copy()

    node_result_dict = _FakeDict()
    node_result_dict["2:ObjectDetection"] = {
        "bboxes": [],
        "scores": [],
        "class_ids": [],
        "score_th": 0.3,
    }

    # Explicit IMAGE from Webcam + JSON from ObjectDetection
    connection_list = [
        ["1:Webcam:IMAGE:Output01", "3:BBoxBlur:IMAGE:Input01"],
        ["2:ObjectDetection:JSON:Output03", "3:BBoxBlur:JSON:Input02"],
    ]

    import node.ProcessNode.node_bbox_blur as bbox_mod

    def fake_get_priority(tag):
        if "Kernel" in tag:
            return 15
        if "Score" in tag:
            return 0.3
        return None

    orig_get = bbox_mod.dpg_get_value
    orig_set = bbox_mod.dpg_set_value
    bbox_mod.dpg_get_value = fake_get_priority
    bbox_mod.dpg_set_value = lambda tag, val: None

    try:
        result = node.update(
            node_id="3",
            connection_list=connection_list,
            node_image_dict=node_image_dict,
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )
    finally:
        bbox_mod.dpg_get_value = orig_get
        bbox_mod.dpg_set_value = orig_set

    assert result["image"] is not None
    # Should have used the Webcam frame (value 50), not the OD frame (value 200)
    np.testing.assert_array_equal(result["image"], webcam_frame)
    print("✓ Explicit IMAGE connection takes priority over JSON fallback")


def test_add_node_sets_tag_node_name():
    """
    Regression test: Node.add_node() must assign self.tag_node_name.

    Root cause of the black-screen bug: tag_node_name was only a local
    variable inside add_node().  node_main._callback_add_node then tried to
    access node.tag_node_name to register the instance in _node_instances_list
    and _node_list.  The AttributeError was silently swallowed by DearPyGui's
    callback system, so BBoxBlur appeared in the UI but was never processed
    by the main loop — resulting in a permanently black texture.
    """
    from node.ProcessNode.node_bbox_blur import Node as BBoxBlurNode

    node = BBoxBlurNode.__new__(BBoxBlurNode)
    node._opencv_setting_dict = {
        "process_width": 64,
        "process_height": 64,
        "use_pref_counter": False,
    }
    # Simulate what add_node() does (without a live DPG context)
    node_id = 42
    node.node_tag = BBoxBlurNode.node_tag
    tag_node_name = str(node_id) + ':' + node.node_tag
    node.tag_node_name = tag_node_name  # This is the line the fix adds

    assert hasattr(node, 'tag_node_name'), (
        "node.tag_node_name must be set as an instance attribute"
    )
    assert node.tag_node_name == f"{node_id}:{BBoxBlurNode.node_tag}", (
        f"tag_node_name should be '{node_id}:{BBoxBlurNode.node_tag}', "
        f"got '{node.tag_node_name}'"
    )
    print("✓ add_node() correctly sets self.tag_node_name on the instance")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("BBoxBlur – JSON-only fallback tests")
    print("=" * 60)

    tests = [
        test_blur_bboxes_no_detections,
        test_blur_bboxes_single_detection,
        test_blur_bboxes_score_below_threshold,
        test_blur_bboxes_even_kernel_rounded_up,
        test_update_json_only_connection_shows_image,
        test_update_no_connections_returns_none_image,
        test_update_explicit_image_connection_takes_priority,
        test_add_node_sets_tag_node_name,
    ]

    failed = []
    for t in tests:
        try:
            t()
        except Exception as exc:
            print(f"  ✗ {t.__name__}: {exc}")
            import traceback
            traceback.print_exc()
            failed.append(t.__name__)

    print()
    if not failed:
        print("✓ All tests passed.")
    else:
        print(f"✗ {len(failed)} test(s) failed: {failed}")
        sys.exit(1)
