"""
TDD tests for the CV_Studio synchronisation layer (node/VideoNode/sync.py).

Three tests:
1. test_stress_jitter_framerate    – Stress-Jitter
2. test_sync_drift_av_alignment    – Sync-Drift / AVDriftDetector
3. test_buffer_overflow_load_shedding – Buffer Overflow / Load Shedding
"""
from __future__ import annotations

import random
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
    """Create a FramePacket with a configurable pipeline delay."""
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
# Test 1 – Stress-Jitter
# ---------------------------------------------------------------------------


class TestStressJitter:
    """Simulate AI latency jitter and verify the writer honours framerate."""

    TARGET_FPS = 30
    JITTER_MAX_MS = 150
    NUM_FRAMES = 60

    def test_stress_jitter_framerate(self):
        """
        Simulate 60 frames with random AI latency in [0, 150 ms].

        Asserts:
        * Total encoded duration matches expected (tolerance 5 %).
        * At least 95 % of source frames survive (no silent mass-drops).
        """
        writer = SyncVideoWriter(
            fps=self.TARGET_FPS,
            max_buffer_size=20,
            # High drop threshold so jitter alone doesn't trigger drops.
            drop_latency_ms=self.JITTER_MAX_MS + 50,
        )

        rng = random.Random(42)
        packets = []
        for i in range(self.NUM_FRAMES):
            jitter_ms = rng.uniform(0, self.JITTER_MAX_MS)
            packets.append(make_packet(i, self.TARGET_FPS, delay_ms=jitter_ms))

        written = writer.consume_and_collect(packets)

        assert written, "No frames were written"

        total_duration_ms = written[-1].pts_ms - written[0].pts_ms
        expected_duration_ms = (self.NUM_FRAMES - 1) / self.TARGET_FPS * 1000.0

        rel_error = (
            abs(total_duration_ms - expected_duration_ms) / expected_duration_ms
        )
        assert rel_error < 0.05, (
            f"Framerate drift too large: {total_duration_ms:.1f} ms vs "
            f"{expected_duration_ms:.1f} ms (rel_error={rel_error:.2%})"
        )

        # At least 95 % of source frames must be in the output
        # (duplicates are OK, drops should be minimal)
        assert len(written) >= self.NUM_FRAMES * 0.95, (
            f"Too many frames dropped: {len(written)} / {self.NUM_FRAMES}"
        )

    def test_stress_jitter_pts_monotone(self):
        """PTS must be monotonically non-decreasing in the output sequence."""
        writer = SyncVideoWriter(fps=self.TARGET_FPS, max_buffer_size=20)
        rng = random.Random(7)
        packets = [
            make_packet(
                i, self.TARGET_FPS, delay_ms=rng.uniform(0, self.JITTER_MAX_MS)
            )
            for i in range(self.NUM_FRAMES)
        ]
        written = writer.consume_and_collect(packets)
        pts_list = [p.pts_ms for p in written]
        for i in range(len(pts_list) - 1):
            assert pts_list[i] <= pts_list[i + 1], (
                f"Non-monotone PTS at index {i}: "
                f"{pts_list[i]:.2f} > {pts_list[i + 1]:.2f}"
            )


# ---------------------------------------------------------------------------
# Test 2 – Sync-Drift / AVDriftDetector
# ---------------------------------------------------------------------------


class TestSyncDrift:
    """Verify that A/V drift is detected before it exceeds the hard limit."""

    MAX_AV_DRIFT_MS = 80.0
    TARGET_FPS = 25
    STEP_DURATION_MS = 1000.0  # 1 audio chunk = 1 second
    NUM_FRAMES = 50

    def test_sync_drift_av_alignment(self):
        """
        Inject frames with audio PTS drifting +2 ms per frame.

        At i=2: drift = |video_pts - audio_pts| = |80 - 76| ms → 76 ms
        (above warn threshold 72 ms, below hard limit 80 ms) → warning fires.

        Asserts:
        * At least one drift warning was emitted.
        * The maximum drift value that triggered a warning is < MAX_AV_DRIFT_MS.
        """
        drift_warnings: list[float] = []

        writer = SyncVideoWriter(
            fps=self.TARGET_FPS,
            max_av_drift_ms=self.MAX_AV_DRIFT_MS,
            step_duration_ms=self.STEP_DURATION_MS,
        )
        writer.on_drift_warning = lambda pkt, drift: drift_warnings.append(drift)

        for i in range(self.NUM_FRAMES):
            video_pts_ms = (i / self.TARGET_FPS) * 1000.0
            # Audio PTS drifts progressively: +2 ms per frame
            audio_pts_ms = (i // int(self.TARGET_FPS)) * self.STEP_DURATION_MS + i * 2.0

            packet = FramePacket(
                frame_index=i,
                pts_ms=video_pts_ms,
                audio_chunk_index=i // int(self.TARGET_FPS),
                image=BASE_IMAGE.copy(),
                audio_data={"pts_ms": audio_pts_ms},
                pipeline_entry_ts=time.monotonic(),
                pipeline_exit_ts=time.monotonic(),
            )
            writer.enqueue(packet)

        assert len(drift_warnings) > 0, (
            "AVDriftDetector never fired a warning despite growing drift"
        )

        max_detected = max(drift_warnings)
        assert max_detected < self.MAX_AV_DRIFT_MS, (
            f"Drift warning fired at {max_detected:.1f} ms "
            f"(>= hard limit {self.MAX_AV_DRIFT_MS} ms)"
        )

    def test_drift_detector_standalone(self):
        """AVDriftDetector standalone: callback fires in warning zone only."""
        warnings: list[float] = []
        errors: list[float] = []

        detector = AVDriftDetector(
            max_av_drift_ms=80.0,
            step_duration_ms=1000.0,
            on_warning=lambda pkt, d: warnings.append(d),
            on_error=lambda pkt, d: errors.append(d),
        )

        # 0 ms drift → no callbacks
        p0 = FramePacket(
            frame_index=0, pts_ms=0.0, audio_chunk_index=0,
            image=BASE_IMAGE.copy(), audio_data={"pts_ms": 0.0},
            pipeline_entry_ts=time.monotonic(), pipeline_exit_ts=time.monotonic(),
        )
        detector.check(p0)
        assert not warnings and not errors

        # 75 ms drift → warning (72 ≤ 75 < 80)
        p1 = FramePacket(
            frame_index=1, pts_ms=75.0, audio_chunk_index=0,
            image=BASE_IMAGE.copy(), audio_data={"pts_ms": 0.0},
            pipeline_entry_ts=time.monotonic(), pipeline_exit_ts=time.monotonic(),
        )
        detector.check(p1)
        assert len(warnings) == 1, f"Expected 1 warning, got {len(warnings)}"
        assert not errors

        # 100 ms drift → error (≥ 80), no warning
        p2 = FramePacket(
            frame_index=2, pts_ms=100.0, audio_chunk_index=0,
            image=BASE_IMAGE.copy(), audio_data={"pts_ms": 0.0},
            pipeline_entry_ts=time.monotonic(), pipeline_exit_ts=time.monotonic(),
        )
        detector.check(p2)
        assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"
        # Warning count must NOT increase
        assert len(warnings) == 1


# ---------------------------------------------------------------------------
# Test 3 – Buffer Overflow / Load Shedding
# ---------------------------------------------------------------------------


class TestBufferOverflow:
    """Verify Drop/Wait policy under buffer saturation."""

    BUFFER_SIZE = 5
    NUM_FRAMES = 50
    TARGET_FPS = 30

    def test_buffer_overflow_load_shedding(self):
        """
        Inject 50 frames with 500 ms simulated delay (all above drop threshold).
        The buffer size is 5.

        With drop_policy='drop_oldest':
        * Frames 0–4 fill the buffer (no drop).
        * Frames 5–49 each trigger: pop oldest → drop count +1, push new.
        * Result: dropped_frame_count >= 1, peak_buffer_size <= BUFFER_SIZE.
        * Written frames are monotonically ordered by PTS.

        The enqueue() method must never raise an exception.
        """
        writer = SyncVideoWriter(
            fps=self.TARGET_FPS,
            max_buffer_size=self.BUFFER_SIZE,
            drop_policy="drop_oldest",
            drop_latency_ms=200.0,
        )

        for i in range(self.NUM_FRAMES):
            packet = FramePacket(
                frame_index=i,
                pts_ms=(i / self.TARGET_FPS) * 1000.0,
                audio_chunk_index=i // 3,
                image=BASE_IMAGE.copy(),
                audio_data=None,
                pipeline_entry_ts=time.monotonic() - 0.5,  # 500 ms delay
                pipeline_exit_ts=time.monotonic(),
            )
            # Must not raise
            writer.enqueue(packet)

        written = writer.flush_and_collect()

        # Drops must have occurred
        assert writer.dropped_frame_count > 0, (
            "No drops recorded despite saturated buffer"
        )

        # PTS monotonicity
        pts_list = [p.pts_ms for p in written]
        for i in range(len(pts_list) - 1):
            assert pts_list[i] <= pts_list[i + 1], (
                f"Non-monotone PTS at index {i}: "
                f"{pts_list[i]:.2f} > {pts_list[i + 1]:.2f}"
            )

        # Peak buffer size must never exceed configured maximum
        assert writer.peak_buffer_size <= self.BUFFER_SIZE, (
            f"Buffer overflow: peak_buffer_size={writer.peak_buffer_size} "
            f"> BUFFER_SIZE={self.BUFFER_SIZE}"
        )

    def test_buffer_overflow_drop_newest(self):
        """
        Same scenario with drop_policy='drop_newest'.
        Incoming frames are discarded once the buffer is full.
        """
        writer = SyncVideoWriter(
            fps=self.TARGET_FPS,
            max_buffer_size=self.BUFFER_SIZE,
            drop_policy="drop_newest",
            drop_latency_ms=200.0,
        )

        for i in range(self.NUM_FRAMES):
            packet = make_packet(
                i, self.TARGET_FPS, delay_ms=500.0
            )
            writer.enqueue(packet)

        written = writer.flush_and_collect()

        assert writer.dropped_frame_count > 0, (
            "No drops recorded despite saturated buffer (drop_newest)"
        )
        assert writer.peak_buffer_size <= self.BUFFER_SIZE, (
            f"Buffer overflow: {writer.peak_buffer_size} > {self.BUFFER_SIZE}"
        )

        # PTS must still be monotone
        pts_list = [p.pts_ms for p in written]
        for i in range(len(pts_list) - 1):
            assert pts_list[i] <= pts_list[i + 1]

    def test_no_exception_on_empty_flush(self):
        """flush_and_collect on an empty writer must not raise."""
        writer = SyncVideoWriter(fps=30)
        result = writer.flush_and_collect()
        assert result == []
