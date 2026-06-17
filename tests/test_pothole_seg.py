#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for PotholeYOLOSeg with both potehole.onnx and potehole_12.onnx."""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODEL_DIR = os.path.join(
    _REPO_ROOT, "node", "DLNode", "semantic_segmentation", "pothole", "model"
)
_MODEL_V1 = os.path.join(_MODEL_DIR, "pothole.onnx")
_MODEL_V12 = os.path.join(_MODEL_DIR, "potehole_12.onnx")


def test_pothole_seg_import():
    from node.DLNode.semantic_segmentation.pothole.pothole_seg import PotholeYOLOSeg
    assert PotholeYOLOSeg is not None


def test_pothole_seg_interface():
    from node.DLNode.semantic_segmentation.pothole.pothole_seg import PotholeYOLOSeg
    assert hasattr(PotholeYOLOSeg, "get_class_num")
    assert hasattr(PotholeYOLOSeg, "__call__")
    assert hasattr(PotholeYOLOSeg, "compute_pixel_counts")
    assert hasattr(PotholeYOLOSeg, "_preprocess")
    assert hasattr(PotholeYOLOSeg, "_postprocess")


def _make_dummy_frame(h=480, w=640):
    """Return a plain BGR dummy frame."""
    return np.zeros((h, w, 3), dtype=np.uint8)


@pytest.mark.skipif(not os.path.isfile(_MODEL_V1), reason="pothole.onnx not found")
def test_pothole_v1_no_white_output():
    """PotholeYOLOSeg with pothole.onnx must not return a fully-white mask."""
    from node.DLNode.semantic_segmentation.pothole.pothole_seg import PotholeYOLOSeg

    model = PotholeYOLOSeg(_MODEL_V1, providers=["CPUExecutionProvider"])
    assert model.get_class_num() == 1

    frame = _make_dummy_frame()
    seg_map, class_ids = model(frame)

    # On a blank frame there should be no detections (empty arrays)
    assert isinstance(seg_map, np.ndarray)
    assert isinstance(class_ids, np.ndarray)
    # seg_map should be [N, H, W] — not a flat YOLO output cast to uint8
    assert seg_map.ndim in (3,) or len(seg_map) == 0


@pytest.mark.skipif(not os.path.isfile(_MODEL_V12), reason="potehole_12.onnx not found")
def test_pothole_v12_no_white_output():
    """PotholeYOLOSeg with potehole_12.onnx must not return a fully-white mask."""
    from node.DLNode.semantic_segmentation.pothole.pothole_seg import PotholeYOLOSeg

    model = PotholeYOLOSeg(_MODEL_V12, providers=["CPUExecutionProvider"])
    assert model.get_class_num() == 1

    frame = _make_dummy_frame()
    seg_map, class_ids = model(frame)

    assert isinstance(seg_map, np.ndarray)
    assert isinstance(class_ids, np.ndarray)
    # Must be binary masks [N, H, W], not a raw YOLO output interpreted as uint8
    assert seg_map.ndim in (3,) or len(seg_map) == 0
    # All mask values must be 0.0 or 1.0 (binary) — not raw floats/255
    if len(seg_map) > 0:
        unique_vals = np.unique(seg_map)
        assert set(unique_vals.tolist()).issubset({0.0, 1.0}), (
            f"Expected binary masks, got values: {unique_vals}"
        )


@pytest.mark.skipif(not os.path.isfile(_MODEL_V12), reason="potehole_12.onnx not found")
def test_pothole_v12_pixel_counts():
    """compute_pixel_counts must return a dict with 'Pothole' key."""
    from node.DLNode.semantic_segmentation.pothole.pothole_seg import PotholeYOLOSeg

    model = PotholeYOLOSeg(_MODEL_V12, providers=["CPUExecutionProvider"])
    frame = _make_dummy_frame()
    seg_map, class_ids = model(frame)
    counts = model.compute_pixel_counts(seg_map, class_ids)

    assert isinstance(counts, dict)
    assert "Pothole" in counts
    assert isinstance(counts["Pothole"], int)


def test_node_registers_v12_builtin():
    """'Pothole YOLO-seg (v12)' must appear in the builtin model set."""
    try:
        from node.DLNode.node_semantic_segmentation import _BUILTIN_SEG_MODEL_NAMES
    except ImportError as e:
        if 'dearpygui' in str(e):
            pytest.skip("Skipping due to missing GUI dependencies")
        raise
    assert "Pothole YOLO-seg (v12)" in _BUILTIN_SEG_MODEL_NAMES


def test_node_model_class_v12_is_pothole_yolo_seg():
    """The model class for 'Pothole YOLO-seg (v12)' must be PotholeYOLOSeg."""
    try:
        from node.DLNode.node_semantic_segmentation import Node
    except ImportError as e:
        if 'dearpygui' in str(e):
            pytest.skip("Skipping due to missing GUI dependencies")
        raise
    from node.DLNode.semantic_segmentation.pothole.pothole_seg import PotholeYOLOSeg
    assert Node._model_class.get("Pothole YOLO-seg (v12)") is PotholeYOLOSeg


def test_node_model_path_v12_points_to_file():
    """The model path for 'Pothole YOLO-seg (v12)' must point to a real file."""
    try:
        from node.DLNode.node_semantic_segmentation import Node
    except ImportError as e:
        if 'dearpygui' in str(e):
            pytest.skip("Skipping due to missing GUI dependencies")
        raise
    path = Node._model_path_setting.get("Pothole YOLO-seg (v12)", "")
    assert os.path.isfile(path), f"Model file not found: {path}"
