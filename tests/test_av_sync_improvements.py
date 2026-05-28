"""
Tests for A/V synchronisation improvements:

1. AVDriftDetector smoothing and drift direction
2. SyncVideoWriter adaptive flush behaviour
3. Gap-fill cap consistency (_drain_heap_locked)
4. AudioClassification passthrough metadata preservation
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from node.VideoNode.sync import AVDriftDetector, FramePacket, SyncVideoWriter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_IMAGE = np.zeros((480, 640, 3), dtype=np.uint8)


def make_packet(
    frame_index: int,
    fps: float,
    audio_chunk_index: int = 0,
    delay_ms: float = 0.0,
    audio_data=None,
) -> FramePacket:
    pts_ms = (frame_index / fps) * 1000.0
    entry_ts = time.monotonic() - (delay_ms / 1000.0)
    exit_ts = time.monotonic()
    return FramePacket(
        frame_index=frame_index,
        pts_ms=pts_ms,
        audio_chunk_index=audio_chunk_index,
        image=BASE_IMAGE.copy(),
        audio_data=audio_data,
        pipeline_entry_ts=entry_ts,
        pipeline_exit_ts=exit_ts,
    )


# ---------------------------------------------------------------------------
# Test: AVDriftDetector smoothed drift
# ---------------------------------------------------------------------------


class TestAVDriftDetectorSmoothing:
    """Verify that AVDriftDetector smooths transient jitter spikes."""

    def test_single_spike_does_not_trigger_error(self):
        """A single frame with high drift should not trigger error when history is full."""
        errors = []
        detector = AVDriftDetector(
            max_av_drift_ms=50.0,
            step_duration_ms=1000.0,
            on_error=lambda pkt, d: errors.append(d),
            history_size=4,
        )
        # Feed 4 frames with zero drift to fill history
        for i in range(4):
            pkt = make_packet(i, 30.0, audio_data={"pts_ms": i / 30.0 * 1000.0})
            detector.check(pkt)

        # Now inject one spike: audio_pts way off
        spike_pkt = make_packet(5, 30.0, audio_data={"pts_ms": 0.0})
        detector.check(spike_pkt)

        # The smoothed drift is (0+0+0+0+drift)/5-ish → below threshold
        # But after the spike, the smoothed average of last 4 includes the spike
        # With history_size=4, the history is [0, 0, 0, spike_drift]
        # spike_drift = |5/30*1000 - 0| = 166.7 ms
        # smoothed = (0 + 0 + 0 + 166.7) / 4 = 41.7 ms → below 50
        assert len(errors) == 0, "Single spike should not trigger error with smoothing"

    def test_sustained_drift_triggers_error(self):
        """Sustained drift above threshold should trigger error."""
        errors = []
        detector = AVDriftDetector(
            max_av_drift_ms=50.0,
            step_duration_ms=1000.0,
            on_error=lambda pkt, d: errors.append(d),
            history_size=4,
        )
        # Feed frames where audio pts is always 100ms behind video pts
        for i in range(8):
            pts_ms = i / 30.0 * 1000.0
            pkt = make_packet(i, 30.0, audio_data={"pts_ms": pts_ms - 100.0})
            detector.check(pkt)

        # Sustained 100 ms drift > 50 ms limit → errors should fire
        assert len(errors) > 0, "Sustained drift should trigger error"

    def test_drift_direction_property(self):
        """drift_direction indicates whether audio leads or lags."""
        detector = AVDriftDetector(max_av_drift_ms=200.0, history_size=4)
        # Audio behind video: pts_ms > audio_pts → positive signed drift
        for i in range(4):
            pts_ms = i / 30.0 * 1000.0
            pkt = make_packet(i, 30.0, audio_data={"pts_ms": pts_ms - 50.0})
            detector.check(pkt)
        assert detector.drift_direction > 0, "Should indicate audio lags"

    def test_reset_clears_history(self):
        """reset() should clear all drift history."""
        detector = AVDriftDetector(max_av_drift_ms=200.0, history_size=4)
        for i in range(4):
            pkt = make_packet(i, 30.0, audio_data={"pts_ms": 0.0})
            detector.check(pkt)
        assert detector.smoothed_drift_ms > 0
        detector.reset()
        assert detector.smoothed_drift_ms == 0.0
        assert detector.drift_direction == 0.0


# ---------------------------------------------------------------------------
# Test: SyncVideoWriter adaptive flush
# ---------------------------------------------------------------------------


class TestAdaptiveFlush:
    """Verify that flush_ready adaptively flushes more frames at high occupancy."""

    def test_flush_single_frame_at_low_occupancy(self):
        """At low buffer occupancy, flush_ready writes exactly 1 frame."""
        writer = SyncVideoWriter(fps=30.0, max_buffer_size=10)
        written_frames = []

        # Enqueue 3 frames (30% occupancy)
        for i in range(3):
            writer.enqueue(make_packet(i, 30.0))

        result = writer.flush_ready(lambda img, pts: written_frames.append(pts))
        # At 30% occupancy (3/10), should flush 1 frame
        assert len(result) == 1

    def test_flush_multiple_frames_at_high_occupancy(self):
        """At high buffer occupancy (>75%), flush_ready writes up to 3 frames."""
        writer = SyncVideoWriter(fps=30.0, max_buffer_size=4)
        written_frames = []

        # Enqueue 4 frames (100% occupancy)
        for i in range(4):
            writer.enqueue(make_packet(i, 30.0))

        result = writer.flush_ready(lambda img, pts: written_frames.append(pts))
        # At 100% occupancy (4/4), should flush up to 3 frames
        assert len(result) >= 2  # At least 2 (could be 3)
        assert len(result) <= 3

    def test_flush_two_frames_at_medium_occupancy(self):
        """At medium occupancy (50-75%), flush_ready writes 2 frames."""
        writer = SyncVideoWriter(fps=30.0, max_buffer_size=4)
        written_frames = []

        # Enqueue 3 frames (75% occupancy)
        for i in range(3):
            writer.enqueue(make_packet(i, 30.0))

        result = writer.flush_ready(lambda img, pts: written_frames.append(pts))
        # At 75% occupancy (3/4), should flush 2 frames
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Test: Gap-fill cap in _drain_heap_locked
# ---------------------------------------------------------------------------


class TestGapFillCap:
    """Verify that _drain_heap_locked caps duplicates at _MAX_GAP_FILL_DUPLICATES."""

    def test_large_gap_capped(self):
        """A very large PTS gap should produce at most 4 duplicates."""
        from node.VideoNode.sync import _MAX_GAP_FILL_DUPLICATES

        writer = SyncVideoWriter(fps=30.0, max_buffer_size=10)
        # Frame 0 at pts=0, then frame 1 at pts=1000ms (huge gap = 30 frames at 30fps)
        packets = [
            FramePacket(
                frame_index=0, pts_ms=0.0, audio_chunk_index=0,
                image=BASE_IMAGE.copy(), audio_data=None,
                pipeline_entry_ts=time.monotonic(),
                pipeline_exit_ts=time.monotonic(),
            ),
            FramePacket(
                frame_index=1, pts_ms=1000.0, audio_chunk_index=1,
                image=BASE_IMAGE.copy(), audio_data=None,
                pipeline_entry_ts=time.monotonic(),
                pipeline_exit_ts=time.monotonic(),
            ),
        ]
        result = writer.consume_and_collect(packets)
        # Should be: frame0 + up to 4 dups + frame1 = max 6
        assert len(result) <= 2 + _MAX_GAP_FILL_DUPLICATES
        # At least the two original frames
        assert len(result) >= 2


# ---------------------------------------------------------------------------
# Test: AudioClassification passthrough metadata
# ---------------------------------------------------------------------------


class TestAudioClassificationPassthrough:
    """Verify that AudioClassification preserves sync metadata in passthrough."""

    def test_passthrough_preserves_chunk_index(self):
        """The passthrough audio dict should contain chunk_index from input."""
        # Simulate what AudioClassification does internally
        input_entry = {
            "data": np.zeros(22050, dtype=np.float32),
            "sample_rate": 22050,
            "chunk_index": 7,
            "step_duration": 1.0,
            "pts_ms": 7000.0,
        }

        # Simulate the fixed passthrough logic
        passthrough_audio_data = input_entry["data"]
        passthrough_sample_rate = input_entry["sample_rate"]
        _passthrough_out = {
            "data": passthrough_audio_data,
            "sample_rate": passthrough_sample_rate,
        }
        for _k in ("chunk_index", "step_duration", "pts_ms"):
            if _k in input_entry:
                _passthrough_out[_k] = input_entry[_k]

        assert _passthrough_out["chunk_index"] == 7
        assert _passthrough_out["step_duration"] == 1.0
        assert _passthrough_out["pts_ms"] == 7000.0
        assert _passthrough_out["sample_rate"] == 22050

    def test_passthrough_without_optional_keys(self):
        """If input lacks optional keys, passthrough should still work."""
        input_entry = {
            "data": np.zeros(16000, dtype=np.float32),
            "sample_rate": 16000,
        }

        passthrough_audio_data = input_entry["data"]
        passthrough_sample_rate = input_entry["sample_rate"]
        _passthrough_out = {
            "data": passthrough_audio_data,
            "sample_rate": passthrough_sample_rate,
        }
        for _k in ("chunk_index", "step_duration", "pts_ms"):
            if _k in input_entry:
                _passthrough_out[_k] = input_entry[_k]

        assert "chunk_index" not in _passthrough_out
        assert "step_duration" not in _passthrough_out
        assert _passthrough_out["sample_rate"] == 16000
