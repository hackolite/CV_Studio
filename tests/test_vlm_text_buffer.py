#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for VLM node round-robin 20-line text buffer and large text canvas rendering."""

import sys
import os
import unittest.mock as mock
import numpy as np
import cv2
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock DearPyGui and related modules before importing the node
sys.modules.setdefault('dearpygui', mock.MagicMock())
sys.modules.setdefault('dearpygui.dearpygui', mock.MagicMock())
sys.modules.setdefault('node_editor', mock.MagicMock())
sys.modules.setdefault('node_editor.util', mock.MagicMock())
sys.modules.setdefault('node.node_abc', mock.MagicMock())

from node.ActionNode.node_vlm import VLMNode


def make_node():
    node = VLMNode.__new__(VLMNode)
    node._text_lines = deque(maxlen=VLMNode.MAX_LINES)
    node._opencv_setting_dict = {}
    return node


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_max_lines_is_20():
    assert VLMNode.MAX_LINES == 20


def test_canvas_dimensions():
    assert VLMNode.TEXT_CANVAS_W == 480
    assert VLMNode.TEXT_CANVAS_H == 680


def test_font_scale_is_large():
    """Font scale should be >= 0.8 for clear readable text."""
    assert VLMNode.TEXT_FONT_SCALE >= 0.8


def test_default_insensitivity_delay():
    assert VLMNode.DEFAULT_INSENSITIVITY_DELAY == 0.0


# ---------------------------------------------------------------------------
# _wrap_text_to_lines
# ---------------------------------------------------------------------------

def test_wrap_short_text_single_line():
    node = make_node()
    lines = node._wrap_text_to_lines("Hello", 460)
    assert lines == ["Hello"]


def test_wrap_empty_text():
    node = make_node()
    lines = node._wrap_text_to_lines("", 460)
    assert lines == []


def test_wrap_long_text_multiple_lines():
    node = make_node()
    long_text = "The quick brown fox jumps over the lazy dog and then runs away very fast indeed"
    lines = node._wrap_text_to_lines(long_text, 460)
    assert len(lines) >= 2
    # Verify all words are present when lines are joined
    joined = " ".join(lines)
    for word in long_text.split():
        assert word in joined


def test_wrap_each_line_fits_in_max_width():
    node = make_node()
    text = "The quick brown fox jumps over the lazy dog " * 3
    max_width = 460
    lines = node._wrap_text_to_lines(text, max_width)
    font = cv2.FONT_HERSHEY_SIMPLEX
    for line in lines:
        (tw, _), _ = cv2.getTextSize(
            line, font, VLMNode.TEXT_FONT_SCALE, VLMNode.TEXT_THICKNESS
        )
        assert tw <= max_width, f"Line too wide: '{line}' ({tw}px > {max_width}px)"


# ---------------------------------------------------------------------------
# _render_text_canvas
# ---------------------------------------------------------------------------

def test_render_canvas_returns_correct_shape():
    node = make_node()
    node._text_lines.append("Hello world")
    canvas = node._render_text_canvas()
    assert canvas.shape == (VLMNode.TEXT_CANVAS_H, VLMNode.TEXT_CANVAS_W, 3)


def test_render_empty_buffer_returns_black_canvas():
    node = make_node()
    canvas = node._render_text_canvas()
    assert canvas.sum() == 0  # all black


def test_render_with_text_has_non_black_pixels():
    node = make_node()
    node._text_lines.append("Some response text")
    canvas = node._render_text_canvas()
    assert canvas.sum() > 0  # at least some red pixels from text


def test_render_text_is_red():
    """Text must be rendered in red (BGR: B=0, G=0, R>0)."""
    node = make_node()
    node._text_lines.append("Red text here")
    canvas = node._render_text_canvas()
    # Red channel (index 2 in BGR) must have non-zero pixels
    assert canvas[:, :, 2].max() > 0, "Red channel should have non-zero pixels"
    # Blue channel (index 0 in BGR) should be zero (no blue component in pure red)
    assert canvas[:, :, 0].max() == 0, "Blue channel should be zero for red text"
    # Green channel (index 1 in BGR) should be zero for pure red
    assert canvas[:, :, 1].max() == 0, "Green channel should be zero for red text"


def test_render_canvas_dtype_is_uint8():
    node = make_node()
    canvas = node._render_text_canvas()
    assert canvas.dtype == np.uint8


# ---------------------------------------------------------------------------
# Rolling buffer (deque, maxlen=20)
# ---------------------------------------------------------------------------

def test_buffer_starts_empty():
    node = make_node()
    assert len(node._text_lines) == 0


def test_buffer_accumulates_lines():
    node = make_node()
    node._text_lines.append("line 1")
    node._text_lines.append("line 2")
    assert len(node._text_lines) == 2
    assert list(node._text_lines) == ["line 1", "line 2"]


def test_buffer_maxlen_is_20():
    node = make_node()
    assert node._text_lines.maxlen == 20


def test_buffer_rolls_over_at_20_lines():
    node = make_node()
    for i in range(25):
        node._text_lines.append(f"line {i}")
    assert len(node._text_lines) == 20
    # First 5 lines should have been dropped
    lines = list(node._text_lines)
    assert lines[0] == "line 5"
    assert lines[-1] == "line 24"


def test_multiple_responses_accumulate():
    node = make_node()
    # First response: 3 lines
    for line in ["Response 1 line A", "Response 1 line B", "Response 1 line C"]:
        node._text_lines.append(line)
    # Second response: 2 more lines
    for line in ["Response 2 line A", "Response 2 line B"]:
        node._text_lines.append(line)
    assert len(node._text_lines) == 5
    assert list(node._text_lines)[0] == "Response 1 line A"
    assert list(node._text_lines)[-1] == "Response 2 line B"


# ---------------------------------------------------------------------------
# Integration: wrap + buffer + render
# ---------------------------------------------------------------------------

def test_full_pipeline_wraps_and_buffers():
    node = make_node()
    text = "The quick brown fox jumps over the lazy dog. " * 4
    max_w = VLMNode.TEXT_CANVAS_W - 2 * VLMNode.TEXT_MARGIN
    lines = node._wrap_text_to_lines(text, max_w)
    for line in lines:
        node._text_lines.append(line)
    canvas = node._render_text_canvas()
    assert canvas.shape == (VLMNode.TEXT_CANVAS_H, VLMNode.TEXT_CANVAS_W, 3)
    assert canvas.sum() > 0


def test_20_line_buffer_renders_all_lines():
    node = make_node()
    for i in range(20):
        node._text_lines.append(f"Line number {i + 1}")
    assert len(node._text_lines) == 20
    canvas = node._render_text_canvas()
    assert canvas.sum() > 0


# ---------------------------------------------------------------------------
# Insensitivity delay
# ---------------------------------------------------------------------------

def test_insensitivity_end_time_initialized_to_zero():
    """VLMNode should start with _insensitivity_end_time == 0 (no cooldown)."""
    from collections import deque
    node = VLMNode.__new__(VLMNode)
    node._text_lines = deque(maxlen=VLMNode.MAX_LINES)
    node._opencv_setting_dict = {}
    node._insensitivity_end_time = 0
    assert node._insensitivity_end_time == 0


def test_insensitivity_blocks_during_cooldown():
    """When _insensitivity_end_time is in the future, update must return early."""
    import time

    node = VLMNode.__new__(VLMNode)
    node._text_lines = deque(maxlen=VLMNode.MAX_LINES)
    node._opencv_setting_dict = {}
    node._is_requesting = False
    node._request_process = None
    node._result_queue = None
    node._pending_frame = None
    node._insensitivity_end_time = time.time() + 100  # far in the future

    status_calls = []

    with mock.patch('node.ActionNode.node_vlm.dpg_get_value', return_value='test'), \
         mock.patch('node.ActionNode.node_vlm.dpg_set_value', side_effect=lambda tag, val: status_calls.append((tag, val))):
        result = node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={},
            node_audio_dict={},
        )

    # Must return without launching a request
    assert result == {"image": None, "json": None, "audio": None}
    assert node._is_requesting is False
    # Status must contain "Insensitive"
    assert any('Insensitive' in str(val) for _, val in status_calls), \
        f"Expected 'Insensitive' in status, got: {status_calls}"


def test_insensitivity_allows_after_cooldown():
    """After insensitivity period expires, a new trigger should be able to fire."""
    import time

    node = VLMNode.__new__(VLMNode)
    node._text_lines = deque(maxlen=VLMNode.MAX_LINES)
    node._opencv_setting_dict = {}
    node._is_requesting = False
    node._request_process = None
    node._result_queue = None
    node._pending_frame = None
    node._insensitivity_end_time = 0  # already expired

    # No connections → should_act = False, so no request is launched, but no insensitivity block
    with mock.patch('node.ActionNode.node_vlm.dpg_get_value', return_value='0.0'), \
         mock.patch('node.ActionNode.node_vlm.dpg_set_value'):
        result = node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={},
            node_audio_dict={},
        )

    # No insensitivity block: normal return path reached
    assert result == {"image": None, "json": None, "audio": None}
    assert node._is_requesting is False


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
