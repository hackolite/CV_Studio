#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Vigilance Gauge visual node."""

import os
import sys
import time
import unittest.mock as mock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock DearPyGui and related modules before importing the node
sys.modules.setdefault('dearpygui', mock.MagicMock())
sys.modules.setdefault('dearpygui.dearpygui', mock.MagicMock())
sys.modules.setdefault('node_editor', mock.MagicMock())
sys.modules.setdefault('node_editor.util', mock.MagicMock())
sys.modules.setdefault('node.node_abc', mock.MagicMock())
sys.modules.setdefault('cv2', mock.MagicMock())

# We need real cv2 + numpy for rendering tests, so import after mocks
# and re-import cv2 as real module
del sys.modules['cv2']
import cv2  # noqa: E402

from node.VisualNode.node_vigilance_gauge import (
    VigilanceGaugeNode,
    FactoryNode,
    render_gauge,
    render_blank,
    VIGILANCE_LEVELS,
    CANVAS_W,
    CANVAS_H,
    BLINK_PERIOD,
)


# ---------------------------------------------------------------------------
# render_gauge
# ---------------------------------------------------------------------------

def test_render_gauge_returns_correct_shape():
    """render_gauge should return an image of the expected dimensions."""
    img = render_gauge(3)
    assert img.shape == (CANVAS_H, CANVAS_W, 3)


def test_render_gauge_returns_uint8():
    img = render_gauge(1)
    assert img.dtype == np.uint8


def test_render_gauge_all_levels():
    """All five vigilance levels should render without error."""
    for level in range(1, 6):
        img = render_gauge(level)
        assert img.shape == (CANVAS_H, CANVAS_W, 3)


def test_render_gauge_clamps_below():
    """Level below 1 should be clamped to 1."""
    img = render_gauge(0)
    assert img.shape == (CANVAS_H, CANVAS_W, 3)


def test_render_gauge_clamps_above():
    """Level above 5 should be clamped to 5."""
    img = render_gauge(7)
    assert img.shape == (CANVAS_H, CANVAS_W, 3)


def test_render_gauge_not_all_black():
    """A rendered gauge should have non-zero pixels (text + bar)."""
    img = render_gauge(3)
    assert img.sum() > 0


def test_render_gauge_has_colour_bar():
    """The bottom bar should contain the level colour."""
    for level, info in VIGILANCE_LEVELS.items():
        img = render_gauge(level)
        # Check bottom row contains expected colour
        bar_row = img[-1, CANVAS_W // 2]
        expected = np.array(info['color_bgr'], dtype=np.uint8)
        np.testing.assert_array_equal(bar_row, expected)


def test_render_gauge_custom_size():
    """render_gauge should accept custom canvas dimensions."""
    img = render_gauge(2, canvas_w=320, canvas_h=320)
    assert img.shape == (320, 320, 3)


# ---------------------------------------------------------------------------
# render_blank
# ---------------------------------------------------------------------------

def test_render_blank_shape():
    img = render_blank()
    assert img.shape == (CANVAS_H, CANVAS_W, 3)


def test_render_blank_is_black():
    img = render_blank()
    assert img.sum() == 0


# ---------------------------------------------------------------------------
# VIGILANCE_LEVELS constants
# ---------------------------------------------------------------------------

def test_vigilance_levels_has_five_entries():
    assert len(VIGILANCE_LEVELS) == 5


def test_vigilance_levels_keys():
    assert set(VIGILANCE_LEVELS.keys()) == {1, 2, 3, 4, 5}


def test_vigilance_levels_labels():
    labels = [VIGILANCE_LEVELS[i]['label'] for i in range(1, 6)]
    assert labels == ['LOW', 'GUARDED', 'MEDIUM', 'HIGH', 'CRITICAL']


# ---------------------------------------------------------------------------
# Node metadata
# ---------------------------------------------------------------------------

def test_node_tag():
    assert VigilanceGaugeNode().node_tag == 'VigilanceGauge'


def test_node_label():
    assert VigilanceGaugeNode().node_label == 'Vigilance Gauge'


def test_factory_node_tag():
    assert FactoryNode().node_tag == 'VigilanceGauge'


def test_factory_node_label():
    assert FactoryNode().node_label == 'Vigilance Gauge'


# ---------------------------------------------------------------------------
# Update logic
# ---------------------------------------------------------------------------

def _make_node():
    """Create a VigilanceGaugeNode suitable for unit testing."""
    node = VigilanceGaugeNode.__new__(VigilanceGaugeNode)
    node.node_tag = 'VigilanceGauge'
    node._last_level = None
    node._thinking = False
    node._last_frame = None
    node.TYPE_JSON = 'JSON'
    node.TYPE_IMAGE = 'IMAGE'
    # Provide a real convert_cv_to_dpg (returns a flat texture array)
    node.convert_cv_to_dpg = lambda img, w, h: np.zeros(w * h * 3, dtype=np.float32)
    return node


def test_update_returns_image_with_valid_json():
    """When connected to a valid vigilance JSON, update returns an image."""
    node = _make_node()
    connection_list = [
        ['1:TinyBertVigilance:JSON:OutputJson',
         '2:VigilanceGauge:JSON:InputJson'],
    ]
    node_result_dict = {'1:TinyBertVigilance': {'vigilance': 3}}

    with mock.patch(
        'node.VisualNode.node_vigilance_gauge.dpg_set_value',
    ):
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )

    assert result['image'] is not None
    assert result['image'].shape == (CANVAS_H, CANVAS_W, 3)
    assert result['json'] is None
    assert result['audio'] is None


def test_update_thinking_when_no_json():
    """Without valid JSON input, the node should enter thinking (blink) mode."""
    node = _make_node()
    connection_list = [
        ['1:TinyBertVigilance:JSON:OutputJson',
         '2:VigilanceGauge:JSON:InputJson'],
    ]
    node_result_dict = {'1:TinyBertVigilance': {}}

    with mock.patch(
        'node.VisualNode.node_vigilance_gauge.dpg_set_value',
    ):
        node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )

    assert node._thinking is True


def test_update_not_thinking_with_valid_json():
    """With valid vigilance JSON the node should NOT be in thinking mode."""
    node = _make_node()
    connection_list = [
        ['1:TinyBertVigilance:JSON:OutputJson',
         '2:VigilanceGauge:JSON:InputJson'],
    ]
    node_result_dict = {'1:TinyBertVigilance': {'vigilance': 4}}

    with mock.patch(
        'node.VisualNode.node_vigilance_gauge.dpg_set_value',
    ):
        node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )

    assert node._thinking is False
    assert node._last_level == 4


def test_update_no_connection():
    """With no connections, node should enter thinking mode."""
    node = _make_node()

    with mock.patch(
        'node.VisualNode.node_vigilance_gauge.dpg_set_value',
    ):
        result = node.update(
            node_id=2,
            connection_list=[],
            node_image_dict={},
            node_result_dict={},
            node_audio_dict={},
        )

    assert node._thinking is True
    assert result['image'] is not None


def test_update_remembers_last_level():
    """After receiving a level, the node should remember it for blink display."""
    node = _make_node()
    conn = [
        ['1:TinyBertVigilance:JSON:OutputJson',
         '2:VigilanceGauge:JSON:InputJson'],
    ]

    with mock.patch(
        'node.VisualNode.node_vigilance_gauge.dpg_set_value',
    ):
        # First: valid input
        node.update(2, conn, {}, {'1:TinyBertVigilance': {'vigilance': 5}}, {})
        assert node._last_level == 5

        # Second: no input → thinking, but last_level preserved
        node.update(2, conn, {}, {'1:TinyBertVigilance': {}}, {})
        assert node._thinking is True
        assert node._last_level == 5


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
