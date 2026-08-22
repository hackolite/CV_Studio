#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the deferred deletion of node textures.

Deleting a texture from a DearPyGui callback destroys it while the current
frame still references it, which segfaults on Linux.  _purge_node_textures must
therefore only release the alias and queue the item; the actual delete_item call
happens between two frames through process_deferred_deletes().
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Pre-mock heavy dependencies before any project imports.  Reuse any mock a
# previously imported test module already installed so the modules under test
# keep using a single dpg stub.
sys.modules.setdefault('cv2', MagicMock())
if 'dearpygui.dearpygui' not in sys.modules:
    _mock_dearpygui = MagicMock()
    _mock_dearpygui.dearpygui = MagicMock()
    sys.modules['dearpygui'] = _mock_dearpygui
    sys.modules['dearpygui.dearpygui'] = _mock_dearpygui.dearpygui
_mock_dpg = sys.modules['dearpygui.dearpygui']

import node_editor.util as util  # noqa: E402
from node_editor.node_main import DpgNodeEditor  # noqa: E402


@pytest.fixture(autouse=True)
def reset_state():
    _mock_dpg.reset_mock(return_value=True, side_effect=True)
    util._deferred_delete_queue.clear()
    yield
    util._deferred_delete_queue.clear()


@pytest.fixture
def editor():
    _mock_dpg.get_item_alias.side_effect = lambda x: x if isinstance(x, str) else str(x)
    editor = DpgNodeEditor(
        width=800,
        height=600,
        opencv_setting_dict={
            'webcam_width': 640,
            'webcam_height': 480,
            'input_window_width': 320,
            'input_window_height': 240,
        },
    )
    _mock_dpg.reset_mock(return_value=True, side_effect=True)
    return editor


def _setup_texture_registry():
    """Simulate a registry holding one texture belonging to node 1:YouTube."""
    _mock_dpg.get_aliases.return_value = [
        "1:YouTube:IMAGE:Output01Value",
        "2:Other:IMAGE:Output01Value",
    ]
    _mock_dpg.get_alias_id.side_effect = lambda alias: {
        "1:YouTube:IMAGE:Output01Value": 10019,
        "2:Other:IMAGE:Output01Value": 10020,
    }[alias]
    _mock_dpg.does_item_exist.return_value = True
    _mock_dpg.get_item_type.return_value = "mvAppItemType::mvRawTexture"


class TestPurgeNodeTextures:
    def test_purge_defers_delete_and_removes_alias(self, editor):
        _setup_texture_registry()

        editor._purge_node_textures("1:YouTube")

        # Alias freed immediately so undo can re-create the node's tag
        _mock_dpg.remove_alias.assert_called_once_with("1:YouTube:IMAGE:Output01Value")
        # But the item itself is not deleted during the frame
        _mock_dpg.delete_item.assert_not_called()
        assert util._deferred_delete_queue == [
            (10019, "1:YouTube:IMAGE:Output01Value")
        ]

    def test_deferred_delete_runs_after_frame(self, editor):
        _setup_texture_registry()

        editor._purge_node_textures("1:YouTube")
        deleted = util.process_deferred_deletes()

        assert deleted == 1
        _mock_dpg.delete_item.assert_called_once_with(10019)
        assert util._deferred_delete_queue == []

    def test_purge_ignores_non_texture_items(self, editor):
        _setup_texture_registry()
        _mock_dpg.get_item_type.return_value = "mvAppItemType::mvNode"

        editor._purge_node_textures("1:YouTube")

        _mock_dpg.remove_alias.assert_not_called()
        assert util._deferred_delete_queue == []

    def test_purge_does_not_queue_when_remove_alias_fails(self, editor):
        _setup_texture_registry()
        _mock_dpg.remove_alias.side_effect = RuntimeError("boom")

        editor._purge_node_textures("1:YouTube")

        assert util._deferred_delete_queue == []


class TestProcessDeferredDeletes:
    def test_empty_queue_is_noop(self):
        assert util.process_deferred_deletes() == 0
        _mock_dpg.delete_item.assert_not_called()

    def test_missing_item_is_skipped(self):
        util.schedule_deferred_delete(42, "gone")
        _mock_dpg.does_item_exist.return_value = False

        assert util.process_deferred_deletes() == 0
        _mock_dpg.delete_item.assert_not_called()

    def test_failure_does_not_block_other_items(self):
        util.schedule_deferred_delete(1, "a")
        util.schedule_deferred_delete(2, "b")
        _mock_dpg.does_item_exist.return_value = True
        _mock_dpg.delete_item.side_effect = [RuntimeError("boom"), None]

        assert util.process_deferred_deletes() == 1
        assert util._deferred_delete_queue == []


class TestRenderLoopDrainsQueue:
    def test_main_render_loop_calls_process_deferred_deletes(self):
        """The render loop must drain the queue outside of the frame render."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
        )
        with open(main_path, encoding="utf-8") as handle:
            source = handle.read()

        assert "process_deferred_deletes" in source
        frame_index = source.index("dpg.render_dearpygui_frame()")
        assert "process_deferred_deletes()" in source[frame_index:]
