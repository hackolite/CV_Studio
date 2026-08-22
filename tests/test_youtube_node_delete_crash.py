#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regression test: deleting a YouTube node while its loading thread is still
running must NOT crash (segfault / unhandled exception) on Linux.

Root cause: close() joins the loading thread with a 2-second timeout.  If
yt-dlp takes longer, the thread outlives the node.  Without the _node_closed
guard, the thread would call dpg.set_item_label() / dpg.bind_item_theme() on
already-deleted items, which causes a segfault in DearPyGui's C++ backend on
Linux.

The fix adds a _node_closed flag that close() sets before doing anything else.
_open_stream() checks this flag after the slow yt-dlp call and returns
immediately (releasing any just-opened VideoCapture) without touching dpg.
"""
import sys
import os
import threading
import unittest.mock as mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock heavy dependencies before importing the node.
# `import dearpygui.dearpygui as dpg` resolves via sys.modules['dearpygui'].dearpygui,
# so we need both keys to point at the same mock object.
_dpg_mod = mock.MagicMock()
_dpg_root = mock.MagicMock()
_dpg_root.dearpygui = _dpg_mod
sys.modules['dearpygui'] = _dpg_root
sys.modules['dearpygui.dearpygui'] = _dpg_mod
sys.modules['cv2'] = mock.MagicMock()
sys.modules['numpy'] = mock.MagicMock()
sys.modules['yt_dlp'] = mock.MagicMock()

from node.InputNode.node_youtube import YoutubeNode   # noqa: E402
import node.InputNode.node_youtube as _ny             # noqa: E402

# The actual dpg object bound inside node_youtube at import time
_dpg = _ny.dpg


def _make_mock_cap(opened=True):
    cap = mock.MagicMock()
    cap.isOpened.return_value = opened
    return cap


def _button_tag(node_instance, node_id="1"):
    """Return the tag_node_button_value_name that button() builds internally."""
    return f"{node_id}:{node_instance.node_tag}:{node_instance.TYPE_TEXT}:ButtonValue"


def _input_tag(node_instance, node_id="1"):
    """Return a user_data string that button() uses to derive tag_node_name."""
    return f"{node_id}:{node_instance.node_tag}:{node_instance.TYPE_TEXT}:Input01Value"


# ---------------------------------------------------------------------------
# _node_closed flag
# ---------------------------------------------------------------------------

def test_node_closed_flag_initialises_false():
    node = YoutubeNode()
    assert not node._node_closed.is_set(), "_node_closed should start as False"
    print("✓ _node_closed initialises to False")


def test_close_sets_node_closed_flag():
    node = YoutubeNode()
    node.close(node_id=1)
    assert node._node_closed.is_set(), "close() must set _node_closed to True"
    print("✓ close() sets _node_closed to True")


# ---------------------------------------------------------------------------
# No crash when node is deleted while _open_stream is running
# ---------------------------------------------------------------------------

def test_delete_during_loading_does_not_call_dpg_on_deleted_items():
    """
    Simulate: the loading thread receives a valid cap AFTER close() was called.
    The thread must not call any dpg API and must release the cap cleanly.
    """
    _dpg.reset_mock()
    node = YoutubeNode()

    mock_cap = _make_mock_cap(opened=True)
    slow_open_started = threading.Event()
    proceed_after_close = threading.Event()

    def slow_stream_url(url, cookies_browser=None):
        """Simulate a slow yt-dlp call that finishes AFTER close() is called."""
        slow_open_started.set()
        proceed_after_close.wait(timeout=5)
        return mock_cap

    with mock.patch('node.InputNode.node_youtube.get_light_live_stream_url',
                    side_effect=slow_stream_url):
        _dpg.get_item_label.return_value = node._start_label
        _dpg.get_value.return_value = "https://youtube.com/watch?v=test"
        _dpg.does_item_exist.return_value = True

        node.button(
            sender=_button_tag(node),
            data=None,
            user_data=_input_tag(node),
        )

        # Wait for the slow yt-dlp call to start
        assert slow_open_started.wait(timeout=2), "loading thread should have started"
        assert node._loading_thread is not None, "loading thread should exist"

        # Delete the node (simulate user pressing Delete)
        node.close(node_id=1)
        assert node._node_closed.is_set()

        # Track dpg calls that happen from this point on
        set_label_calls_after_close = []
        bind_theme_calls_after_close = []
        _dpg.set_item_label.side_effect = lambda *a, **kw: set_label_calls_after_close.append(a)
        _dpg.bind_item_theme.side_effect = lambda *a, **kw: bind_theme_calls_after_close.append(a)

        # Let the loading thread finish
        proceed_after_close.set()
        node._loading_thread.join(timeout=3)

    # The cap that was opened after close() should have been released
    mock_cap.release.assert_called_once()

    # No dpg calls should have been made after close()
    assert set_label_calls_after_close == [], (
        f"dpg.set_item_label was called after close(): {set_label_calls_after_close}"
    )
    assert bind_theme_calls_after_close == [], (
        f"dpg.bind_item_theme was called after close(): {bind_theme_calls_after_close}"
    )

    print("✓ No dpg calls on deleted items when node is closed during loading")


def test_delete_during_loading_failed_cap_no_dpg_crash():
    """
    If yt-dlp returns None after close(), the thread should exit silently
    without touching dpg.
    """
    _dpg.reset_mock()
    node = YoutubeNode()

    slow_open_started = threading.Event()
    proceed_after_close = threading.Event()

    def slow_stream_url(url, cookies_browser=None):
        slow_open_started.set()
        proceed_after_close.wait(timeout=5)
        return None  # Simulate failure after close

    with mock.patch('node.InputNode.node_youtube.get_light_live_stream_url',
                    side_effect=slow_stream_url):
        _dpg.get_item_label.return_value = node._start_label
        _dpg.get_value.return_value = "https://youtube.com/watch?v=test"
        _dpg.does_item_exist.return_value = False  # items already gone

        node.button(
            sender=_button_tag(node),
            data=None,
            user_data=_input_tag(node),
        )

        assert slow_open_started.wait(timeout=2), "loading thread should have started"
        node.close(node_id=1)

        set_label_calls_after_close = []
        _dpg.set_item_label.side_effect = lambda *a, **kw: set_label_calls_after_close.append(a)

        proceed_after_close.set()
        node._loading_thread.join(timeout=3)

    assert set_label_calls_after_close == [], (
        f"dpg.set_item_label called after close(): {set_label_calls_after_close}"
    )

    print("✓ Failed cap after close: no dpg calls on deleted items")


def test_normal_close_without_loading_thread():
    """close() must work cleanly when no loading thread is active."""
    node = YoutubeNode()
    node.close(node_id=1)
    assert node._node_closed.is_set()
    assert node.cap is None
    assert node.is_streaming is False
    print("✓ Normal close without loading thread works cleanly")


def test_close_with_active_cap():
    """close() releases cap when streaming is active."""
    node = YoutubeNode()
    mock_cap = _make_mock_cap()
    node.cap = mock_cap
    node.is_streaming = True

    node.close(node_id=1)

    mock_cap.release.assert_called_once()
    assert node.cap is None
    assert node.is_streaming is False
    assert node._node_closed.is_set()
    print("✓ close() properly releases an active VideoCapture")


if __name__ == '__main__':
    print("Testing YouTube node delete-during-loading crash fix...")
    print("=" * 60)

    tests = [
        ("_node_closed initialises False", test_node_closed_flag_initialises_false),
        ("close() sets _node_closed", test_close_sets_node_closed_flag),
        ("delete during loading: no dpg calls on deleted items",
         test_delete_during_loading_does_not_call_dpg_on_deleted_items),
        ("delete during loading (failed cap): no dpg crash",
         test_delete_during_loading_failed_cap_no_dpg_crash),
        ("normal close without loading thread", test_normal_close_without_loading_thread),
        ("close() releases active cap", test_close_with_active_cap),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n  {name}...")
        try:
            fn()
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  ✗ FAILED: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
