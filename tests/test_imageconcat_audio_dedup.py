#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests that VideoWriterNode._collect_concat_audio applies the same
chunk_index deduplication and leading-audio trim as the single-chunk
(input:video) path.

All heavy dependencies (cv2, dearpygui, …) are stubbed at module-import time
so the test runs in the sandboxed CI environment that has only numpy/pytest.
"""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Stub every dependency that node_video_writer imports transitively.
# Must happen BEFORE any import of node code.
# ---------------------------------------------------------------------------

def _stub_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


_noop = lambda *a, **kw: None
_false = lambda *a, **kw: False

# cv2
cv2_stub = _stub_module("cv2")
cv2_stub.VideoWriter = type("VideoWriter", (), {"write": _noop, "release": _noop})
cv2_stub.VideoWriter_fourcc = lambda *a: 0
cv2_stub.resize = lambda img, size, **kw: img
cv2_stub.circle = lambda img, *a, **kw: img
cv2_stub.INTER_CUBIC = 2

# dearpygui / dearpygui.dearpygui
dpg_stub = _stub_module("dearpygui")
dpg_inner = _stub_module("dearpygui.dearpygui")
for _attr in (
    "does_item_exist", "configure_item", "set_value", "get_item_label",
    "set_item_label", "get_viewport_client_width", "get_viewport_client_height",
    "set_item_pos", "set_item_width", "set_item_height",
    "add_node", "add_node_attribute", "add_node_editor",
    "add_input_text", "add_button", "add_text", "add_progress_bar",
    "add_image",
):
    setattr(dpg_inner, _attr, _noop)
dpg_inner.does_item_exist = _false
dpg_inner.get_item_label = lambda *a, **kw: "Start"
dpg_stub.dearpygui = dpg_inner

# node_editor / node_editor.util
ne_stub = _stub_module("node_editor")
ne_util_stub = _stub_module("node_editor.util")
ne_util_stub.dpg_get_value = _noop
ne_util_stub.dpg_set_value = _noop

# node.node_abc
nabc_stub = _stub_module("node.node_abc")
nabc_stub.DpgNodeABC = object  # plain base class — enough for instantiation

# node.basenode
nbase_stub = _stub_module("node.basenode")


class _BaseNodeStub:
    TYPE_IMAGE = "IMAGE"
    TYPE_AUDIO = "AUDIO"
    TYPE_JSON = "JSON"
    TYPE_TEXT = "TEXT"
    _opencv_setting_dict = None

    @staticmethod
    def convert_cv_to_dpg(img, w, h):
        return None


nbase_stub.Node = _BaseNodeStub

# soundfile / ffmpeg (optional heavy deps)
_stub_module("soundfile")
_stub_module("ffmpeg")

# ---------------------------------------------------------------------------
# Now it is safe to import the node under test.
# ---------------------------------------------------------------------------

from node.VideoNode.node_video_writer import VideoWriterNode  # noqa: E402
from node.VideoNode.sync import FramePacket  # noqa: E402

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

SR = 16000
STEP_DUR = 1.0  # 1-second sliding-window step


def _make_writer_node(tag: str) -> VideoWriterNode:
    """Return a VideoWriterNode with its per-node dicts pre-seeded."""
    node = VideoWriterNode()
    node._audio_samples_dict[tag] = []
    node._last_chunk_index_dict[tag] = -1
    node._recording_metadata_dict[tag] = {
        "final_path": "/tmp/out.mp4",
        "temp_path": "/tmp/out_temp.mp4",
        "format": "MP4",
        "sample_rate": 22050,
        "fps": 30.0,
    }
    return node


def _make_packet(pts_ms: float) -> FramePacket:
    return FramePacket(
        frame_index=0,
        pts_ms=pts_ms,
        audio_chunk_index=0,
        image=np.zeros((64, 64, 3), dtype=np.uint8),
        audio_data=None,
        pipeline_entry_ts=0.0,
        pipeline_exit_ts=0.0,
    )


def _make_concat_audio(
    chunk_index: int,
    n_samples: int = SR,
    sr: int = SR,
    step_dur: float = STEP_DUR,
) -> dict:
    """Build an ImageConcat-style audio dict: {slot_idx: audio_chunk}."""
    data = np.ones(n_samples, dtype=np.float32) * (chunk_index + 1)
    return {
        0: {
            "data": data,
            "sample_rate": sr,
            "chunk_index": chunk_index,
            "step_duration": step_dur,
        }
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

TAG = "0:VideoWriter"


def test_collect_concat_audio_method_exists():
    node = VideoWriterNode()
    assert hasattr(node, "_collect_concat_audio"), (
        "VideoWriterNode must expose _collect_concat_audio helper"
    )


class TestImageConcatChunkIndexDedup:
    """_collect_concat_audio must deduplicate repeated chunk_index values."""

    def test_first_chunk_collected(self):
        node = _make_writer_node(TAG)
        audio_data = _make_concat_audio(chunk_index=0)
        node._collect_concat_audio(TAG, audio_data, _make_packet(0.0))
        assert len(node._audio_samples_dict[TAG]) == 1

    def test_duplicate_chunk_index_skipped(self):
        node = _make_writer_node(TAG)
        audio_data = _make_concat_audio(chunk_index=3)
        packet = _make_packet(0.0)
        # Deliver the same chunk_index twice
        node._collect_concat_audio(TAG, audio_data, packet)
        node._collect_concat_audio(TAG, audio_data, packet)
        assert len(node._audio_samples_dict[TAG]) == 1, (
            "Duplicate chunk_index must be discarded"
        )

    def test_new_chunk_index_collected(self):
        node = _make_writer_node(TAG)
        packet = _make_packet(0.0)
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=0), packet)
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=1), packet)
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=1), packet)  # dup
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=2), packet)
        assert len(node._audio_samples_dict[TAG]) == 3, (
            "Three distinct chunk_index values → 3 chunks"
        )

    def test_step_duration_trim_applied(self):
        """Only the non-overlapping step portion (step_dur * sr samples) is kept."""
        node = _make_writer_node(TAG)
        long_data = np.ones(2 * SR, dtype=np.float32)
        audio_data = {
            0: {
                "data": long_data,
                "sample_rate": SR,
                "chunk_index": 0,
                "step_duration": STEP_DUR,  # → keep only SR samples
            }
        }
        node._collect_concat_audio(TAG, audio_data, _make_packet(0.0))
        assert len(node._audio_samples_dict[TAG]) == 1
        assert len(node._audio_samples_dict[TAG][0]) == SR

    def test_sample_rate_updated_in_metadata(self):
        node = _make_writer_node(TAG)
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=0, sr=SR), _make_packet(0.0))
        assert node._recording_metadata_dict[TAG]["sample_rate"] == SR

    def test_leading_trim_first_chunk(self):
        """Leading samples in the first chunk are trimmed to align with pts_ms."""
        node = _make_writer_node(TAG)
        # chunk_index=0 starts at t=0 but the first video frame is at ~33.33 ms
        pts_ms = 1000.0 / 30.0  # ≈ 33.33 ms
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=0), _make_packet(pts_ms))
        expected_lead = int((pts_ms / 1000.0) * SR)
        expected_len = SR - expected_lead
        assert len(node._audio_samples_dict[TAG][0]) == expected_len, (
            f"Expected {expected_len} samples after lead trim"
        )

    def test_no_leading_trim_for_subsequent_chunks(self):
        """Leading trim applies only to the first collected chunk."""
        node = _make_writer_node(TAG)
        pts_ms = 1000.0 / 30.0
        packet = _make_packet(pts_ms)
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=0), packet)
        len_first = len(node._audio_samples_dict[TAG][0])
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=1), packet)
        len_second = len(node._audio_samples_dict[TAG][1])
        assert len_second == SR, f"Second chunk must have {SR} samples (no lead trim)"
        assert len_first < len_second, "First chunk must be shorter due to lead trim"

    def test_last_chunk_index_updated(self):
        node = _make_writer_node(TAG)
        node._collect_concat_audio(TAG, _make_concat_audio(chunk_index=5), _make_packet(0.0))
        assert node._last_chunk_index_dict[TAG] == 5

    def test_no_op_when_not_in_audio_samples_dict(self):
        """_collect_concat_audio must be a no-op when the node is not recording."""
        node = VideoWriterNode()
        # No pre-seeding — tag absent from _audio_samples_dict
        node._collect_concat_audio("missing:tag", _make_concat_audio(0), _make_packet(0.0))
        assert "missing:tag" not in node._audio_samples_dict
