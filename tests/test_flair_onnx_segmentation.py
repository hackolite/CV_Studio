#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the FLAIR Aerial INT8 ONNX semantic segmentation wrapper.

Verifies that ``FlairAerialSegmentationONNX`` produces output in the same
format as the other segmentation models registered in
``node_semantic_segmentation.py``.
"""
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "node", "DLNode", "semantic_segmentation",
    "aerial_segmentation_flair", "model", "flair_aerial_seg_static_int8.onnx",
)

_MODEL_AVAILABLE = os.path.isfile(_MODEL_PATH)


# ---------------------------------------------------------------------------
# Import checks
# ---------------------------------------------------------------------------

def test_import_flair_onnx_class():
    """FlairAerialSegmentationONNX can be imported without errors."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        FlairAerialSegmentationONNX,
    )
    assert FlairAerialSegmentationONNX is not None


def test_import_overlay_flair2():
    """overlay_flair2 helper can be imported."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        overlay_flair2,
    )
    assert callable(overlay_flair2)


def test_flair2_class_definitions():
    """FLAIR2_CLASSES and FLAIR2_COLORS_BGR have 19 entries each."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        FLAIR2_CLASSES,
        FLAIR2_COLORS_BGR,
        NUM_CLASSES_FLAIR2,
    )
    assert len(FLAIR2_CLASSES) == NUM_CLASSES_FLAIR2
    assert len(FLAIR2_COLORS_BGR) == NUM_CLASSES_FLAIR2


def test_colorize_flair2_mask():
    """colorize_flair2_mask returns correct shape and dtype."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        colorize_flair2_mask,
        NUM_CLASSES_FLAIR2,
    )
    mask = np.arange(NUM_CLASSES_FLAIR2, dtype=np.uint8).reshape(1, -1)
    color = colorize_flair2_mask(mask)
    assert color.shape == (1, NUM_CLASSES_FLAIR2, 3)
    assert color.dtype == np.uint8


def test_overlay_flair2_output_shape():
    """overlay_flair2 returns the same shape as the input image."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        overlay_flair2,
    )
    h, w = 64, 64
    image = np.zeros((h, w, 3), dtype=np.uint8)
    mask  = np.zeros((h, w), dtype=np.uint8)
    result = overlay_flair2(image, mask, alpha=0.5)
    assert result.shape == (h, w, 3)
    assert result.dtype == np.uint8


# ---------------------------------------------------------------------------
# Interface checks (without loading the model)
# ---------------------------------------------------------------------------

def test_flair_onnx_interface():
    """FlairAerialSegmentationONNX exposes get_class_num and __call__."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        FlairAerialSegmentationONNX,
    )
    assert hasattr(FlairAerialSegmentationONNX, 'get_class_num')
    assert hasattr(FlairAerialSegmentationONNX, '__call__')
    assert hasattr(FlairAerialSegmentationONNX, 'get_argmax_mask')


def test_flair_onnx_uses_disable_optimizations(tmp_path, monkeypatch):
    """FlairAerialSegmentationONNX calls make_session with disable_optimizations=True.

    ConvInteger ops in the INT8 model are not resolved correctly when ORT graph
    optimizations are enabled; disabling them is the fix for the NOT_IMPLEMENTED
    error at session creation time.
    """
    import unittest.mock as mock
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair import (
        aerial_segmentation_flair as _mod,
    )

    dummy_model = tmp_path / "dummy.onnx"
    dummy_model.write_bytes(b"dummy")

    fake_session = mock.MagicMock()
    fake_session.get_inputs.return_value = [mock.MagicMock(name="input")]
    fake_session.get_outputs.return_value = [
        mock.MagicMock(shape=[1, 19, 64, 64])
    ]

    with mock.patch.object(_mod, "make_session", return_value=fake_session) as patched:
        try:
            _mod.FlairAerialSegmentationONNX(
                model_path=str(dummy_model),
                providers=["CPUExecutionProvider"],
            )
        except Exception:
            pass  # session mock may not satisfy all attribute access; that's fine
        patched.assert_called_once()
        _, kwargs = patched.call_args
        assert kwargs.get("disable_optimizations") is True, (
            "make_session must be called with disable_optimizations=True to avoid "
            "ConvInteger NOT_IMPLEMENTED errors for the INT8 FLAIR model"
        )


def test_flair_onnx_get_argmax_mask():
    """get_argmax_mask converts a probability map to a uint8 class-index mask."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        FlairAerialSegmentationONNX,
        NUM_CLASSES_FLAIR2,
    )
    h, w = 32, 32
    prob_map = np.random.rand(NUM_CLASSES_FLAIR2, h, w).astype(np.float32)
    mask = FlairAerialSegmentationONNX.get_argmax_mask(prob_map)
    assert mask.shape == (h, w)
    assert mask.dtype == np.uint8
    assert mask.max() < NUM_CLASSES_FLAIR2


# ---------------------------------------------------------------------------
# Registry integration check
# ---------------------------------------------------------------------------

def test_flair_int8_in_model_class():
    """'FLAIR Aerial INT8 (ONNX)' is present in Node._model_class."""
    try:
        from node.DLNode.node_semantic_segmentation import Node
    except ImportError as exc:
        if 'dearpygui' in str(exc):
            pytest.skip("Skipping: dearpygui not available")
        raise
    assert 'FLAIR Aerial INT8 (ONNX)' in Node._model_class


def test_flair_int8_model_path_setting():
    """'FLAIR Aerial INT8 (ONNX)' path in _model_path_setting points to the ONNX file."""
    try:
        from node.DLNode.node_semantic_segmentation import Node
    except ImportError as exc:
        if 'dearpygui' in str(exc):
            pytest.skip("Skipping: dearpygui not available")
        raise
    path = Node._model_path_setting.get('FLAIR Aerial INT8 (ONNX)')
    assert path is not None
    assert path.endswith('flair_aerial_seg_static_int8.onnx')


# ---------------------------------------------------------------------------
# End-to-end inference (requires the ONNX file)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _MODEL_AVAILABLE, reason="ONNX model file not found")
def test_flair_onnx_inference_output_shape():
    """End-to-end: model returns (num_classes, H, W) float32 for a dummy frame."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        FlairAerialSegmentationONNX,
        NUM_CLASSES_FLAIR2,
    )
    model = FlairAerialSegmentationONNX(model_path=_MODEL_PATH,
                                        providers=['CPUExecutionProvider'])
    assert model.get_class_num() == NUM_CLASSES_FLAIR2

    # Small dummy BGR frame
    frame = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    seg_map = model(frame)

    assert seg_map.ndim == 3
    assert seg_map.shape[0] == NUM_CLASSES_FLAIR2
    assert seg_map.shape[1] == 64
    assert seg_map.shape[2] == 64
    assert seg_map.dtype == np.float32
    # Probabilities should sum to ~1 along class axis
    prob_sum = seg_map.sum(axis=0)
    np.testing.assert_allclose(prob_sum, np.ones((64, 64)), atol=1e-4)


@pytest.mark.skipif(not _MODEL_AVAILABLE, reason="ONNX model file not found")
def test_flair_onnx_overlay_pipeline():
    """End-to-end: full pipeline (model → argmax → overlay) produces a valid BGR image."""
    from node.DLNode.semantic_segmentation.aerial_segmentation_flair.aerial_segmentation_flair import (
        FlairAerialSegmentationONNX,
        overlay_flair2,
    )
    model = FlairAerialSegmentationONNX(model_path=_MODEL_PATH,
                                        providers=['CPUExecutionProvider'])
    frame = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    seg_map = model(frame)
    mask = FlairAerialSegmentationONNX.get_argmax_mask(seg_map)
    result = overlay_flair2(frame, mask, alpha=0.5)

    assert result.shape == (64, 64, 3)
    assert result.dtype == np.uint8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
