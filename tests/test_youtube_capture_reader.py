#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the YouTube node's background video capture reader.

``cap.read()`` used to run on the node-graph thread.  Because a YouTube stream
has no flow control, consuming slower than real time made FFmpeg buffer up and
``read()`` return ever-staler frames while blocking inference.  A dedicated
reader thread now drains the stream and keeps only the newest frame.
"""

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

pytest.importorskip("cv2")
pytest.importorskip("dearpygui")
pytest.importorskip("yt_dlp")

import numpy as np  # noqa: E402

from node.InputNode.node_youtube import YoutubeNode  # noqa: E402


class _FakeCapture:
    """Minimal cv2.VideoCapture stand-in producing numbered frames."""

    def __init__(self, total_frames=None):
        self._index = 0
        self._total = total_frames
        self.released = False

    def read(self):
        if self._total is not None and self._index >= self._total:
            return False, None
        frame = np.full((2, 2, 3), self._index % 256, dtype=np.uint8)
        self._index += 1
        time.sleep(0.001)
        return True, frame

    def release(self):
        self.released = True


def _make_node(cap):
    node = YoutubeNode()
    node.cap = cap
    return node


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_capture_reader_starts_and_stops_cleanly():
    node = _make_node(_FakeCapture())
    try:
        node._start_capture_reader()
        assert node._capture_thread is not None
        assert node._capture_thread.is_alive()
    finally:
        node._stop_capture_reader()
    assert node._capture_thread is None


def test_take_latest_frame_returns_none_before_any_frame():
    node = _make_node(_FakeCapture())
    assert node._take_latest_frame() is None


def test_take_latest_frame_consumes_each_frame_once():
    node = _make_node(_FakeCapture())
    try:
        node._start_capture_reader()
        assert _wait_for(lambda: node._take_latest_frame() is not None)
        # The frame just consumed must not be handed out a second time.
        assert node._take_latest_frame() is None
    finally:
        node._stop_capture_reader()


def test_slow_consumer_drops_stale_frames():
    """A consumer slower than the stream must receive the freshest frame."""
    node = _make_node(_FakeCapture())
    try:
        node._start_capture_reader()
        assert _wait_for(lambda: node._latest_frame_seq > 20)
        seq_before = node._latest_frame_seq
        frame = node._take_latest_frame()

        assert frame is not None
        # Frames produced while the consumer was busy were dropped rather than
        # queued, so the consumed sequence jumps straight to the newest frame.
        assert node._consumed_frame_seq >= seq_before
        assert node._dropped_frames > 0
    finally:
        node._stop_capture_reader()


def test_reader_thread_exits_when_stream_ends():
    node = _make_node(_FakeCapture(total_frames=3))
    try:
        node._start_capture_reader()
        # 150 consecutive read failures at ~10 ms back-off before giving up.
        assert _wait_for(lambda: not node._capture_thread.is_alive(), timeout=15.0)
    finally:
        node._stop_capture_reader()


def test_restarting_reader_resets_frame_state():
    node = _make_node(_FakeCapture())
    try:
        node._start_capture_reader()
        assert _wait_for(lambda: node._latest_frame_seq > 5)

        node.cap = _FakeCapture()
        node._start_capture_reader()

        assert node._consumed_frame_seq == 0
        assert node._dropped_frames == 0
    finally:
        node._stop_capture_reader()


def test_stop_capture_reader_is_idempotent():
    node = _make_node(_FakeCapture())
    node._stop_capture_reader()
    node._stop_capture_reader()
    assert node._capture_thread is None


def test_reader_thread_is_daemon():
    """A stuck read() must never keep the application alive."""
    node = _make_node(_FakeCapture())
    try:
        node._start_capture_reader()
        assert node._capture_thread.daemon is True
    finally:
        node._stop_capture_reader()


def test_capture_thread_does_not_leak_after_close():
    node = _make_node(_FakeCapture())
    node._start_capture_reader()
    assert _wait_for(lambda: node._latest_frame_seq > 0)

    before = threading.active_count()
    node.close("0")

    assert node._capture_thread is None
    assert node.cap is None
    assert threading.active_count() <= before
