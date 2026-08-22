#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regression tests: deleting a node must not hold _dpg_lock while the node's
close() runs.

On Linux, closing a node that owns a texture (video/camera nodes) could block
for tens of seconds inside close() (thread joins, capture release, subprocess
wait).  Because deletion runs on the UI thread while _dpg_lock is held, the
async update thread stayed blocked in main.update_node_info and the fault
watchdog reported "Timeout (0:00:30)!", i.e. a frozen application.
"""
import os
import sys
import threading
import time
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Pre-mock heavy dependencies before any project imports
_mock_dpg = MagicMock()
_mock_dearpygui = MagicMock()
_mock_dearpygui.dearpygui = _mock_dpg
sys.modules['cv2'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['dearpygui'] = _mock_dearpygui
sys.modules['dearpygui.dearpygui'] = _mock_dpg

from node_editor.node_main import DpgNodeEditor  # noqa: E402
from node_editor.util import _dpg_lock  # noqa: E402


@pytest.fixture
def dpg_selection():
    """Patch the shared dpg mock so configuration does not leak to other tests."""
    with ExitStack() as stack:
        stack.enter_context(patch.object(_mock_dpg, 'get_selected_nodes', return_value=["1:Video"]))
        stack.enter_context(patch.object(_mock_dpg, 'get_selected_links', return_value=[]))
        stack.enter_context(patch.object(_mock_dpg, 'get_item_children', return_value=[]))
        stack.enter_context(patch.object(_mock_dpg, 'get_aliases', return_value=[]))
        yield


@pytest.fixture
def editor():
    _mock_dpg.reset_mock()
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
    _mock_dpg.reset_mock()
    _mock_dpg.get_item_alias.side_effect = lambda x: x if isinstance(x, str) else str(x)
    yield editor


class _SlowNode:
    """Node whose close() blocks until released, like a video node."""

    def __init__(self):
        self.release = threading.Event()
        self.close_started = threading.Event()
        self.closed_with = None

    def get_setting_dict(self, node_id):
        return {}

    def close(self, node_id):
        self.closed_with = node_id
        self.close_started.set()
        self.release.wait(10)


def test_slow_close_does_not_hold_dpg_lock(editor, dpg_selection):
    """A blocking close() must not keep _dpg_lock held after deletion."""
    slow_node = _SlowNode()
    editor._node_list = ["1:Video"]
    editor._node_link_list = []
    editor._node_instances_list["1:Video"] = slow_node

    start = time.time()
    editor._callback_mv_key_del()
    elapsed = time.time() - start

    # Deletion returned immediately even though close() is still blocked.
    assert elapsed < 2, f"deletion blocked for {elapsed:.1f}s on close()"
    assert slow_node.close_started.wait(5), "close() was never invoked"
    assert slow_node.closed_with == "1"
    assert "1:Video" not in editor._node_list

    # The lock must be free while close() is still running: the async update
    # thread has to keep acquiring it every iteration.
    acquired = _dpg_lock.acquire(timeout=2)
    try:
        assert acquired, "_dpg_lock still held while close() runs"
    finally:
        if acquired:
            _dpg_lock.release()

    slow_node.release.set()
    editor._join_pending_closes("1:Video")


def test_close_exception_is_logged_not_raised(editor, dpg_selection):
    """A close() raising in the background thread must not break deletion."""
    node = MagicMock()
    node.get_setting_dict.return_value = {}
    node.close.side_effect = RuntimeError("boom")

    editor._node_list = ["1:Video"]
    editor._node_link_list = []
    editor._node_instances_list["1:Video"] = node

    editor._callback_mv_key_del()
    editor._join_pending_closes("1:Video")

    node.close.assert_called_once_with("1")
    assert "1:Video" not in editor._node_list
    assert "1:Video" not in editor._node_instances_list


def test_join_pending_closes_clears_finished_threads(editor):
    """Finished close threads must be dropped from the pending map."""
    node = MagicMock()
    editor._start_node_close("1:Video", node, "1")
    editor._join_pending_closes("1:Video")

    assert "1:Video" not in editor._pending_close_threads
    node.close.assert_called_once_with("1")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
