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
    assert canvas.sum() > 0  # at least some white pixels from text


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


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
