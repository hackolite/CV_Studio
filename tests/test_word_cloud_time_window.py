#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Word Cloud time-window (delta T) accumulation logic."""

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

# Re-import real cv2 for rendering helpers
del sys.modules['cv2']
import cv2  # noqa: E402

from node.VisualNode.node_word_cloud import (
    WordCloudNode,
    FactoryNode,
    _clean_text,
    _render_word_cloud,
    _render_blank,
    DEFAULT_COLOURMAP,
    DEFAULT_MAX_WORDS,
    DEFAULT_DELTA_T,
    CANVAS_W,
    CANVAS_H,
)


# ---------------------------------------------------------------------------
# Helper to build a testable WordCloudNode without DearPyGui
# ---------------------------------------------------------------------------

def _make_node():
    """Create a WordCloudNode suitable for unit testing (no DPG required)."""
    node = WordCloudNode.__new__(WordCloudNode)
    node.node_tag = 'WordCloud'
    node._last_frame = None
    node._last_colourmap = DEFAULT_COLOURMAP
    node._last_max_words = DEFAULT_MAX_WORDS
    node._last_delta_t = DEFAULT_DELTA_T
    node._text_buffer = []
    node._last_appended_text = ''
    node._last_combined_text = ''
    node.TYPE_JSON = 'JSON'
    node.TYPE_IMAGE = 'IMAGE'
    node.convert_cv_to_dpg = lambda img, w, h: np.zeros(w * h * 3, dtype=np.float32)
    return node


def _run_update(node, node_id, text, delta_t=DEFAULT_DELTA_T,
                colourmap=DEFAULT_COLOURMAP, max_words=DEFAULT_MAX_WORDS):
    """Call node.update() with mocked DPG and a given text/delta_t."""
    tag_node_name = '{}:{}'.format(node_id, node.node_tag)
    connection_list = [
        [
            '1:VLM:JSON:OutputJson',
            '{}:WordCloud:JSON:InputJson'.format(node_id),
        ],
    ]
    node_result_dict = {'1:VLM': {'TEXT': text}}

    def fake_dpg_get(tag):
        if 'ColourmapValue' in tag:
            return colourmap
        if 'MaxWordsValue' in tag:
            return max_words
        if 'DeltaTValue' in tag:
            return delta_t
        return None

    with mock.patch(
        'node.VisualNode.node_word_cloud.dpg_get_value', side_effect=fake_dpg_get
    ), mock.patch(
        'node.VisualNode.node_word_cloud.dpg_set_value',
    ):
        return node.update(
            node_id=node_id,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_default_delta_t():
    assert DEFAULT_DELTA_T == 30


# ---------------------------------------------------------------------------
# Node metadata
# ---------------------------------------------------------------------------

def test_node_tag():
    assert WordCloudNode().node_tag == 'WordCloud'


def test_factory_node_tag():
    assert FactoryNode().node_tag == 'WordCloud'


# ---------------------------------------------------------------------------
# Buffer initialisation
# ---------------------------------------------------------------------------

def test_initial_buffer_empty():
    node = WordCloudNode()
    assert node._text_buffer == []


def test_initial_last_appended_text():
    node = WordCloudNode()
    assert node._last_appended_text == ''


def test_initial_last_combined_text():
    node = WordCloudNode()
    assert node._last_combined_text == ''


# ---------------------------------------------------------------------------
# Text is appended to buffer on first update
# ---------------------------------------------------------------------------

def test_buffer_receives_first_text():
    node = _make_node()
    _run_update(node, node_id=1, text='hello world')
    assert len(node._text_buffer) == 1
    assert node._text_buffer[0][1] == 'hello world'


def test_buffer_does_not_duplicate_same_text():
    """Repeated identical text should not create multiple buffer entries."""
    node = _make_node()
    _run_update(node, node_id=1, text='hello world')
    _run_update(node, node_id=1, text='hello world')
    assert len(node._text_buffer) == 1


def test_buffer_grows_with_distinct_texts():
    node = _make_node()
    _run_update(node, node_id=1, text='cats and dogs')
    _run_update(node, node_id=1, text='sun and moon')
    assert len(node._text_buffer) == 2


# ---------------------------------------------------------------------------
# Combined text reflects the full buffer
# ---------------------------------------------------------------------------

def test_combined_text_contains_all_buffer_texts():
    node = _make_node()
    _run_update(node, node_id=1, text='cats and dogs')
    _run_update(node, node_id=1, text='sun and moon')
    result = _run_update(node, node_id=1, text='rain and wind')
    combined = result['json']['TEXT']
    assert 'cats' in combined
    assert 'sun' in combined
    assert 'rain' in combined


def test_json_output_text_is_combined():
    """JSON output TEXT should be the concatenation of buffered texts."""
    node = _make_node()
    _run_update(node, node_id=1, text='alpha beta')
    result = _run_update(node, node_id=1, text='gamma delta')
    combined = result['json']['TEXT']
    assert 'alpha' in combined
    assert 'gamma' in combined


# ---------------------------------------------------------------------------
# Old entries are pruned when they exceed delta_t
# ---------------------------------------------------------------------------

def test_old_entries_pruned():
    """Entries timestamped before (now - delta_t) must be removed."""
    node = _make_node()
    past = time.time() - 100  # 100 s ago
    node._text_buffer = [(past, 'old text')]
    node._last_appended_text = 'old text'

    # delta_t = 30 → 100 s old entry should be pruned
    result = _run_update(node, node_id=1, text='new text', delta_t=30)
    texts_in_buffer = [txt for _, txt in node._text_buffer]
    assert 'old text' not in texts_in_buffer
    assert 'new text' in texts_in_buffer


def test_recent_entries_not_pruned():
    """Entries within delta_t must be kept."""
    node = _make_node()
    recent = time.time() - 5  # 5 s ago
    node._text_buffer = [(recent, 'recent text')]
    node._last_appended_text = 'recent text'

    # delta_t = 30 → 5 s old entry should be kept
    _run_update(node, node_id=1, text='new text', delta_t=30)
    texts_in_buffer = [txt for _, txt in node._text_buffer]
    assert 'recent text' in texts_in_buffer


# ---------------------------------------------------------------------------
# Image output
# ---------------------------------------------------------------------------

def test_update_returns_image():
    node = _make_node()
    result = _run_update(node, node_id=1, text='python machine learning')
    assert result['image'] is not None
    assert result['image'].shape == (CANVAS_H, CANVAS_W, 3)


def test_update_returns_none_audio():
    node = _make_node()
    result = _run_update(node, node_id=1, text='hello')
    assert result['audio'] is None


def test_update_returns_image_even_when_buffer_empty():
    """With no text at all the node should still return a placeholder image."""
    node = _make_node()
    result = _run_update(node, node_id=1, text='')
    assert result['image'] is not None
    assert result['image'].shape == (CANVAS_H, CANVAS_W, 3)


# ---------------------------------------------------------------------------
# Render only regenerates when necessary
# ---------------------------------------------------------------------------

def test_frame_not_regenerated_for_unchanged_input():
    """Repeated calls with same text and settings reuse the cached frame."""
    node = _make_node()
    r1 = _run_update(node, node_id=1, text='stable text')
    first_frame = r1['image']
    r2 = _run_update(node, node_id=1, text='stable text')
    # Same object (no regeneration)
    assert r2['image'] is first_frame


def test_frame_regenerated_when_delta_t_changes():
    """Changing delta_t should trigger a re-render."""
    node = _make_node()
    r1 = _run_update(node, node_id=1, text='stable text', delta_t=30)
    first_frame = r1['image']
    r2 = _run_update(node, node_id=1, text='stable text', delta_t=60)
    assert r2['image'] is not first_frame


# ---------------------------------------------------------------------------
# _clean_text helper
# ---------------------------------------------------------------------------

def test_clean_text_removes_tokens():
    cleaned = _clean_text('<OD>hello world<TOKENS>')
    assert '<' not in cleaned
    assert 'hello' in cleaned


def test_clean_text_strips_punctuation():
    cleaned = _clean_text('hello, world! how are you?')
    assert ',' not in cleaned
    assert '!' not in cleaned


# ---------------------------------------------------------------------------
# _render_word_cloud helper
# ---------------------------------------------------------------------------

def test_render_word_cloud_shape():
    img = _render_word_cloud('python data science machine learning')
    assert img.shape == (CANVAS_H, CANVAS_W, 3)


def test_render_word_cloud_dtype():
    img = _render_word_cloud('test word cloud image rendering')
    assert img.dtype == np.uint8


def test_render_word_cloud_empty_text_returns_placeholder():
    img = _render_word_cloud('')
    assert img.shape == (CANVAS_H, CANVAS_W, 3)


# ---------------------------------------------------------------------------
# get_setting_dict / set_setting_dict
# ---------------------------------------------------------------------------

def test_get_setting_dict_includes_delta_t():
    """get_setting_dict must include the DeltaTValue key."""
    node = WordCloudNode()

    def fake_dpg_get(tag):
        if 'ColourmapValue' in tag:
            return DEFAULT_COLOURMAP
        if 'MaxWordsValue' in tag:
            return DEFAULT_MAX_WORDS
        if 'DeltaTValue' in tag:
            return 60
        return None

    import dearpygui.dearpygui as dpg
    dpg.get_item_pos = mock.MagicMock(return_value=[0, 0])

    with mock.patch(
        'node.VisualNode.node_word_cloud.dpg_get_value', side_effect=fake_dpg_get
    ):
        settings = node.get_setting_dict(node_id=42)

    delta_t_key = '42:WordCloud:DeltaTValue'
    assert delta_t_key in settings
    assert settings[delta_t_key] == 60


def test_set_setting_dict_restores_delta_t():
    """set_setting_dict must restore the DeltaTValue."""
    node = WordCloudNode()
    calls = {}

    def fake_dpg_set(tag, value):
        calls[tag] = value

    settings = {
        '7:WordCloud:ColourmapValue': 'viridis',
        '7:WordCloud:MaxWordsValue': 50,
        '7:WordCloud:DeltaTValue': 120,
    }

    with mock.patch(
        'node.VisualNode.node_word_cloud.dpg_set_value', side_effect=fake_dpg_set
    ):
        node.set_setting_dict(node_id=7, setting_dict=settings)

    assert calls.get('7:WordCloud:DeltaTValue') == 120


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
