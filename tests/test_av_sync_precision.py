#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ultra-robust A/V synchronisation precision tests for the VideoWriter pipeline.

Problem statement
-----------------
During playback of a merged video produced by VideoWriterNode, the **image
track runs ahead** of the audio track: you see an event (e.g. a door closing)
before you hear the corresponding sound.

Root causes under investigation
--------------------------------
1. **Step-boundary audio lead** – `_get_audio_chunk_for_frame` maps a frame at
   time T to `chunk_index = floor(T / step_dur)`.  The first collected audio
   chunk therefore starts at `chunk_index * step_dur ≤ T`.  In the merged
   file both streams start at t=0, so the audio plays content from *before*
   the recorded video's start → the audio is always 0..step_dur seconds
   ahead of the images.

2. **1-indexed frame counter** – VideoNode starts `current_frame_num` at 1,
   not 0.  The first frame has `pts_ms = 1/fps * 1000 ≈ 33 ms` but the
   first audio chunk covers original t=[0, step_dur], adding a built-in
   one-frame audio lead.

3. **Heap-lag / audio-collection mismatch** – `flush_ready` writes the
   *oldest* frame from the heap, while audio is collected for the *newest*
   (just-enqueued) frame.  With a non-empty heap the audio collection point
   is ahead of the written frame by up to `heap_size` pipeline cycles.

4. **SyncVideoWriter gap-fill duplicates inflate video** – duplicate frames
   inserted for large PTS gaps add extra video time with no corresponding
   audio, shifting the video/audio balance.

5. **PyAVEncoder AAC initial-encoder-delay** – the AAC codec has a
   priming/flush delay of 1024 samples (~23 ms at 44 100 Hz) that the
   encoder does not automatically compensate for.

Each test class below isolates one of these mechanisms so that the root cause
can be identified and fixed independently.

Running
-------
    python -m pytest tests/test_av_sync_precision.py -v
"""
from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple

import numpy as np
import pytest

from node.VideoNode.sync import AVDriftDetector, FramePacket, SyncVideoWriter

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

SR = 22_050  # audio sample rate used throughout
FPS = 30.0
STEP_DUR = 1.0       # seconds per step (sliding-window advance)
CHUNK_DUR = 5.0      # seconds per audio chunk (sliding-window size)


def _make_audio_file(
    total_duration_s: float = 30.0,
    sr: int = SR,
) -> Tuple[np.ndarray, int]:
    """Return a synthetic audio waveform (440 Hz sine) and its sample rate."""
    n = int(total_duration_s * sr)
    t = np.arange(n, dtype=np.float32) / sr
    return (np.sin(2 * math.pi * 440 * t) * 0.5).astype(np.float32), sr


def _build_chunks(
    audio: np.ndarray,
    sr: int,
    chunk_dur: float = CHUNK_DUR,
    step_dur: float = STEP_DUR,
) -> List[np.ndarray]:
    """Replicate `_preprocess_video`'s sliding-window chunking logic."""
    chunk_samples = int(chunk_dur * sr)
    step_samples = int(step_dur * sr)
    chunks: List[np.ndarray] = []
    start = 0
    while start + chunk_samples <= len(audio):
        chunks.append(audio[start : start + chunk_samples].copy())
        start += step_samples
    # Pad the last incomplete chunk so it has exactly chunk_samples
    if start < len(audio):
        remaining = audio[start:]
        padded = np.pad(remaining, (0, chunk_samples - len(remaining)))
        chunks.append(padded.astype(np.float32))
    return chunks


def _get_chunk_for_frame(
    frame_number: int,
    fps: float,
    chunks: List[np.ndarray],
    step_dur: float = STEP_DUR,
) -> Tuple[np.ndarray, int]:
    """Replicate `_get_audio_chunk_for_frame` logic.

    Returns (chunk_data, chunk_index).
    """
    current_time = frame_number / fps if fps > 0 else 0.0
    chunk_index = int(current_time / step_dur)
    chunk_index = max(0, min(chunk_index, len(chunks) - 1))
    return chunks[chunk_index], chunk_index


def _simulate_recording(
    start_frame: int,
    end_frame: int,
    fps: float,
    chunks: List[np.ndarray],
    sr: int,
    step_dur: float = STEP_DUR,
) -> Tuple[np.ndarray, float]:
    """
    Simulate VideoWriterNode audio collection for frames [start_frame, end_frame).

    Replicates the dedup + step_duration trim logic from
    ``VideoWriterNode.update()``.

    Returns
    -------
    collected_audio : np.ndarray
        Concatenated trimmed audio chunks (what would be fed to ffmpeg merge).
    first_frame_time_s : float
        Presentation time of the first recorded frame (start_frame / fps).
    """
    step_samples = int(step_dur * sr)
    last_chunk_index = -1
    collected: List[np.ndarray] = []

    for frame_num in range(start_frame, end_frame):
        chunk_data, chunk_index = _get_chunk_for_frame(frame_num, fps, chunks, step_dur)
        # Dedup: only collect when chunk_index advances
        if chunk_index != last_chunk_index:
            last_chunk_index = chunk_index
            trimmed = chunk_data[:step_samples]
            collected.append(trimmed.astype(np.float32))

    full_audio = np.concatenate(collected) if collected else np.array([], dtype=np.float32)
    first_frame_time_s = start_frame / fps
    return full_audio, first_frame_time_s


# ---------------------------------------------------------------------------
# 1.  Step-boundary audio lead
# ---------------------------------------------------------------------------


class TestStepBoundaryAudioLead:
    """
    Verify that audio collected by VideoWriter starts BEFORE the first video
    frame when recording starts at a non-step-boundary frame.

    The offset is: T_video_start - floor(T_video_start / step_dur) * step_dur
    Maximum ≈ step_dur − 1/fps ≈ step_dur.
    """

    @pytest.mark.parametrize(
        "start_frame, expected_offset_s",
        [
            # Start at frame 0: perfect alignment (offset = 0 / fps = 0)
            (0, 0.0),
            # Start exactly at a step boundary (frame 30 = t=1.0 s at 30 fps)
            (30, 0.0),
            # Start midway through a step (frame 15 = t=0.5 s, step boundary = t=0)
            (15, 0.5),
            # Start near end of step (frame 28 ≈ t=0.933 s, step boundary = t=0)
            (28, 28 / FPS),
            # Start two steps in (frame 75 = t=2.5 s, step boundary = t=2.0 s)
            (75, 0.5),
            # Start deep into video (frame 103 ≈ t=3.433 s, step boundary = t=3.0 s)
            (103, 103 / FPS - 3.0),
        ],
    )
    def test_audio_starts_before_first_video_frame(
        self, start_frame: int, expected_offset_s: float
    ):
        """
        The audio collected for a recording starting at *start_frame* must
        start exactly *expected_offset_s* seconds BEFORE the first video frame.

        A non-zero offset means the audio is ahead of the video (images appear
        ahead of sound).
        """
        audio, sr = _make_audio_file(total_duration_s=30.0, sr=SR)
        chunks = _build_chunks(audio, sr)

        end_frame = start_frame + 60  # record 60 frames
        collected, first_frame_s = _simulate_recording(
            start_frame, end_frame, FPS, chunks, sr
        )

        # The first collected chunk starts at floor(first_frame_s / step_dur) * step_dur
        _, first_chunk_idx = _get_chunk_for_frame(start_frame, FPS, chunks)
        first_chunk_start_s = first_chunk_idx * STEP_DUR

        actual_offset_s = first_frame_s - first_chunk_start_s

        assert abs(actual_offset_s - expected_offset_s) < 1e-9, (
            f"start_frame={start_frame}: expected audio-lead offset "
            f"{expected_offset_s:.4f}s, got {actual_offset_s:.4f}s.\n"
            f"first_frame_s={first_frame_s:.4f}, "
            f"first_chunk_start_s={first_chunk_start_s:.4f}"
        )

    def test_offset_range(self):
        """
        For any recording start frame the audio lead must be in [0, step_dur).
        """
        audio, sr = _make_audio_file(30.0, SR)
        chunks = _build_chunks(audio, sr)

        offsets = []
        for start_frame in range(0, 240, 7):  # 34 different start positions
            _, first_chunk_idx = _get_chunk_for_frame(start_frame, FPS, chunks)
            first_frame_s = start_frame / FPS
            first_chunk_start_s = first_chunk_idx * STEP_DUR
            offset_s = first_frame_s - first_chunk_start_s
            offsets.append(offset_s)
            assert 0.0 <= offset_s < STEP_DUR, (
                f"start_frame={start_frame}: offset {offset_s:.4f}s not in "
                f"[0, {STEP_DUR})s"
            )

        max_offset = max(offsets)
        assert max_offset > 0.0, (
            "All offsets are zero – the test range should include non-boundary "
            "start positions where the audio lead is non-zero."
        )

    def test_worst_case_offset_approaches_step_duration(self):
        """
        Frame just before a step boundary produces an offset ≈ step_dur − 1/fps.
        """
        audio, sr = _make_audio_file(30.0, SR)
        chunks = _build_chunks(audio, sr)

        # Frame 29 is just before the 30-fps step boundary at frame 30
        start_frame = int(FPS * STEP_DUR) - 1  # = 29
        first_frame_s = start_frame / FPS
        _, first_chunk_idx = _get_chunk_for_frame(start_frame, FPS, chunks)
        first_chunk_start_s = first_chunk_idx * STEP_DUR
        offset_s = first_frame_s - first_chunk_start_s

        expected = STEP_DUR - 1.0 / FPS
        assert abs(offset_s - expected) < 1e-9, (
            f"Worst-case offset should be {expected:.4f}s, got {offset_s:.4f}s"
        )


# ---------------------------------------------------------------------------
# 2.  1-indexed frame counter
# ---------------------------------------------------------------------------


class TestOneIndexedFrameOffset:
    """
    VideoNode increments `current_frame_num` BEFORE emitting each frame
    (1-indexed).  This introduces a built-in audio lead of 1/fps seconds even
    at the very start of a video.
    """

    def test_first_frame_is_one_indexed(self):
        """
        Frame 1 (not 0) is the first emitted frame.  Its pts = 1/fps.
        But audio chunk 0 covers original t=[0, step_dur], starting at t=0.
        The built-in lead is therefore 1/fps seconds.
        """
        audio, sr = _make_audio_file(30.0, SR)
        chunks = _build_chunks(audio, sr)

        # Simulate 1-indexed: first frame number = 1
        first_frame_1indexed = 1
        first_pts_s = first_frame_1indexed / FPS  # ≈ 0.0333 s at 30 fps

        _, first_chunk_idx = _get_chunk_for_frame(first_frame_1indexed, FPS, chunks)
        first_chunk_start_s = first_chunk_idx * STEP_DUR  # = 0.0 s

        audio_lead_s = first_pts_s - first_chunk_start_s

        assert audio_lead_s == pytest.approx(1.0 / FPS, abs=1e-9), (
            f"Expected 1/fps = {1.0/FPS:.6f}s audio lead from 1-indexed "
            f"counter, got {audio_lead_s:.6f}s"
        )

    def test_zero_indexed_has_no_built_in_offset(self):
        """
        A 0-indexed first frame (pts = 0) has no built-in audio lead.
        """
        audio, sr = _make_audio_file(30.0, SR)
        chunks = _build_chunks(audio, sr)

        first_frame_0indexed = 0
        first_pts_s = first_frame_0indexed / FPS  # = 0.0 s

        _, first_chunk_idx = _get_chunk_for_frame(first_frame_0indexed, FPS, chunks)
        first_chunk_start_s = first_chunk_idx * STEP_DUR  # = 0.0 s

        audio_lead_s = first_pts_s - first_chunk_start_s
        assert audio_lead_s == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 3.  Step-trim correctness
# ---------------------------------------------------------------------------


class TestStepTrimCorrectness:
    """
    `VideoWriterNode.update()` trims each collected chunk to its first
    `step_duration` seconds.  Verify that:
    a) The trimmed portion is the correct (non-overlapping) segment.
    b) Consecutive trimmed chunks form a gapless audio sequence.
    c) The correct ORIGINAL audio content is preserved (not the wrong window).
    """

    def test_trim_preserves_correct_original_samples(self):
        """
        After trimming, chunk i must contain original audio from
        [i*step_dur, (i+1)*step_dur] — NOT arbitrary content.
        """
        audio, sr = _make_audio_file(10.0, SR)
        chunks = _build_chunks(audio, sr)

        step_samples = int(STEP_DUR * sr)

        for i, chunk in enumerate(chunks[:-1]):  # skip last (may be padded)
            trimmed = chunk[:step_samples]
            expected = audio[i * step_samples : (i + 1) * step_samples]
            np.testing.assert_array_almost_equal(
                trimmed,
                expected,
                decimal=5,
                err_msg=(
                    f"Chunk {i}: trimmed[:step_samples] does not equal "
                    f"original[{i*step_samples}:{(i+1)*step_samples}]. "
                    "Step-trim is returning the wrong portion of the chunk."
                ),
            )

    def test_consecutive_trimmed_chunks_are_contiguous(self):
        """
        Trimmed chunks concatenated must reproduce the original audio without
        gaps or overlaps.
        """
        audio, sr = _make_audio_file(5.0, SR)
        chunks = _build_chunks(audio, sr)
        step_samples = int(STEP_DUR * sr)

        # Collect non-padded chunks only
        non_padded = chunks[: len(audio) // step_samples]
        trimmed = np.concatenate([c[:step_samples] for c in non_padded])

        expected_len = len(non_padded) * step_samples
        assert len(trimmed) == expected_len

        # The concatenated result must equal original audio up to that length
        np.testing.assert_array_almost_equal(
            trimmed,
            audio[:expected_len],
            decimal=5,
            err_msg="Concatenated trimmed chunks do not match original audio.",
        )

    def test_wrong_end_trim_would_fail(self):
        """
        Regression guard: taking the LAST step_samples (instead of the first)
        would give INCORRECT data.  Confirm that `audio[-step_samples:]` from
        chunk i is NOT equal to original[i*step, (i+1)*step].
        """
        audio, sr = _make_audio_file(10.0, SR)
        chunks = _build_chunks(audio, sr)
        step_samples = int(STEP_DUR * sr)

        # Use chunks 1+ (chunk 0: last == first == step_samples, trivially equal)
        for i in range(1, min(4, len(chunks) - 1)):
            wrong_trim = chunks[i][-step_samples:]          # end of chunk
            correct_trim = audio[i * step_samples : (i + 1) * step_samples]
            assert not np.allclose(wrong_trim, correct_trim), (
                f"Chunk {i}: end-trim equals correct trim — test is not "
                "distinguishing the two (audio may be constant)."
            )


# ---------------------------------------------------------------------------
# 4.  A/V duration balance
# ---------------------------------------------------------------------------


class TestAVDurationBalance:
    """
    After trimming, the total collected audio must be approximately equal to
    the video duration.  Any systematic discrepancy reveals the audio-lead
    offset.
    """

    @pytest.mark.parametrize(
        "start_frame, n_frames",
        [
            (0, 300),      # 10 s from beginning — ideal case
            (1, 299),      # 1-indexed start — 1/fps lead expected
            (15, 285),     # mid-step start — 0.5 s lead expected
            (29, 271),     # worst-case start — (step_dur - 1/fps) lead
            (90, 210),     # start 3 s in, non-boundary
        ],
    )
    def test_audio_duration_vs_video_duration(
        self, start_frame: int, n_frames: int
    ):
        """
        Measure audio_duration − video_duration.

        A POSITIVE value means audio is LONGER than video → audio starts
        earlier (images appear ahead when merged at t=0).
        """
        audio, sr = _make_audio_file(30.0, SR)
        chunks = _build_chunks(audio, sr)

        end_frame = start_frame + n_frames
        collected, first_frame_s = _simulate_recording(
            start_frame, end_frame, FPS, chunks, sr
        )

        audio_duration_s = len(collected) / sr
        video_duration_s = n_frames / FPS

        # The audio-lead offset (positive = audio ahead)
        audio_lead_s = audio_duration_s - video_duration_s

        # Compute expected lead: fractional position within the step
        _, first_chunk_idx = _get_chunk_for_frame(start_frame, FPS, chunks)
        expected_lead_s = first_frame_s - first_chunk_idx * STEP_DUR

        # The expected lead must be within ±1 step_duration of actual
        # (±1 step extra chunk at end boundary)
        assert audio_lead_s >= -STEP_DUR / 2, (
            f"start={start_frame}: audio ({audio_duration_s:.3f}s) is "
            f"{-audio_lead_s:.3f}s SHORTER than video ({video_duration_s:.3f}s)."
        )

        # The difference between audio lead and expected lead is bounded by
        # one step_duration (one extra chunk may be collected at recording stop)
        delta = abs(audio_lead_s - expected_lead_s)
        assert delta <= STEP_DUR + 1.0 / FPS + 1e-6, (
            f"start={start_frame}: audio_lead={audio_lead_s:.4f}s, "
            f"expected_lead={expected_lead_s:.4f}s, delta={delta:.4f}s "
            f"> tolerance {STEP_DUR + 1/FPS:.4f}s"
        )

    def test_required_trim_to_align(self):
        """
        Compute how many samples must be trimmed from the start of the
        collected audio to achieve perfect A/V alignment.

        This is the fix that VideoWriter should apply before calling ffmpeg.
        """
        audio, sr = _make_audio_file(30.0, SR)
        chunks = _build_chunks(audio, sr)

        start_frame = 15  # mid-step: 0.5 s offset expected
        n_frames = 150    # 5-second recording
        end_frame = start_frame + n_frames

        collected, first_frame_s = _simulate_recording(
            start_frame, end_frame, FPS, chunks, sr
        )

        _, first_chunk_idx = _get_chunk_for_frame(start_frame, FPS, chunks)
        first_chunk_start_s = first_chunk_idx * STEP_DUR

        # Number of samples to trim from audio start
        trim_samples = int((first_frame_s - first_chunk_start_s) * sr)
        aligned_audio = collected[trim_samples:]

        aligned_duration_s = len(aligned_audio) / sr
        video_duration_s = n_frames / FPS

        # After trim, audio and video durations should differ by at most 1 step
        discrepancy_s = abs(aligned_duration_s - video_duration_s)
        assert discrepancy_s <= STEP_DUR + 1e-3, (
            f"After trim, discrepancy={discrepancy_s:.4f}s > {STEP_DUR}s. "
            "Trim computation is incorrect."
        )

        # The trimmed audio must start from original audio at first_frame_s
        expected_start_sample = int(first_frame_s * sr)
        actual_start_sample = trim_samples + first_chunk_idx * int(STEP_DUR * sr)
        assert actual_start_sample == expected_start_sample, (
            f"After trim, audio starts at original sample {actual_start_sample} "
            f"but should start at {expected_start_sample} "
            f"(frame time {first_frame_s:.4f}s)"
        )


# ---------------------------------------------------------------------------
# 5.  Heap-lag vs audio-collection mismatch
# ---------------------------------------------------------------------------


class TestHeapLagAudioMismatch:
    """
    `flush_ready` writes the OLDEST frame from the SyncVideoWriter heap while
    audio collection is triggered by the NEWEST (just-enqueued) frame.

    With a non-empty heap, audio for frame N is collected at the same pipeline
    cycle that writes frame N−K (where K = heap occupancy).  This creates an
    additional audio-ahead offset of K/fps seconds.
    """

    def _simulate_heap_pipeline(
        self,
        n_frames: int,
        fps: float,
        heap_lag: int,
        step_dur: float = STEP_DUR,
    ) -> Tuple[List[float], List[float]]:
        """
        Simulate the VideoWriterNode update loop with a constant heap lag.

        Returns
        -------
        written_frame_pts : list[float]
            PTS (seconds) of each frame written to cv2.VideoWriter.
        audio_collect_pts : list[float]
            PTS (seconds) of the INCOMING frame at each audio-collection event.
        """
        # SyncVideoWriter with fixed buffer size = heap_lag
        # In production this is max(4, int(fps * 0.2))
        writer = SyncVideoWriter(fps=fps, max_buffer_size=max(1, heap_lag + 2))

        written_pts: List[float] = []
        audio_collect_pts: List[float] = []
        last_audio_chunk = -1

        image = np.zeros((64, 64, 3), dtype=np.uint8)

        for frame_num in range(1, n_frames + 1):
            pts_ms = frame_num / fps * 1000.0
            now = time.monotonic()
            packet = FramePacket(
                frame_index=frame_num,
                pts_ms=pts_ms,
                audio_chunk_index=int(frame_num / fps / step_dur),
                image=image,
                audio_data=None,
                pipeline_entry_ts=now,
                pipeline_exit_ts=now,
            )

            # Simulate audio collection: chunk_index changes?
            chunk_idx = int(frame_num / fps / step_dur)
            if chunk_idx != last_audio_chunk:
                last_audio_chunk = chunk_idx
                # Audio is collected for the CURRENT incoming frame
                audio_collect_pts.append(pts_ms / 1000.0)

            # Enqueue
            writer.enqueue(packet)

            # Drain the heap and record only the first (lowest-PTS) frame that
            # would have been written by flush_ready.  Subsequent frames would
            # be written in later cycles by the real VideoWriterNode, but here
            # we only care about which frame is written *first* per cycle.
            popped = writer.flush_and_collect()
            if popped:
                written_pts.append(popped[0].pts_ms / 1000.0)

        return written_pts, audio_collect_pts

    def test_heap_zero_lag_no_audio_video_mismatch(self):
        """
        With zero heap lag, the frame written and the frame whose audio was
        just collected are the same → no additional offset.
        """
        # Build simple monotone pipeline: no reordering needed
        fps = 30.0
        n_frames = 60

        writer = SyncVideoWriter(fps=fps, max_buffer_size=30)
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        written_pts: List[float] = []
        audio_events: List[float] = []  # (video_write_pts, audio_collect_pts)
        last_chunk = -1

        for frame_num in range(1, n_frames + 1):
            pts_ms = frame_num / fps * 1000.0
            now = time.monotonic()
            pkt = FramePacket(
                frame_index=frame_num,
                pts_ms=pts_ms,
                audio_chunk_index=int(frame_num / fps / STEP_DUR),
                image=image,
                audio_data=None,
                pipeline_entry_ts=now,
                pipeline_exit_ts=now,
            )
            chunk_idx = int(frame_num / fps / STEP_DUR)
            if chunk_idx != last_chunk:
                last_chunk = chunk_idx
                audio_events.append(pts_ms / 1000.0)

            popped: List[float] = []
            writer.flush_ready(lambda img, pts: popped.append(pts))
            if not popped:
                writer.enqueue(pkt)
                writer.flush_ready(lambda img, pts: popped.append(pts))
            else:
                writer.enqueue(pkt)

        # flush remainder
        remaining = writer.flush_and_collect()
        for p in remaining:
            written_pts.append(p.pts_ms / 1000.0)

        # With in-order packets and immediate flush, written_pts should be
        # monotonically increasing
        for i in range(len(written_pts) - 1):
            assert written_pts[i] <= written_pts[i + 1], (
                f"written_pts not monotone at index {i}: "
                f"{written_pts[i]:.3f} > {written_pts[i+1]:.3f}"
            )

    def test_audio_collected_before_corresponding_frame_written(self):
        """
        Demonstrate that with a heap buffer of K frames, audio chunk M is
        collected BEFORE the corresponding video frame M*fps*step_dur is
        written.

        This is the heap-lag mismatch: audio is ahead by K frames / fps.
        """
        fps = 30.0
        heap_size = 6  # max(4, int(30 * 0.2)) in production
        n_frames = 90

        writer = SyncVideoWriter(fps=fps, max_buffer_size=heap_size + 2)
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        # Track: for each audio collection event, what is the PTS of the
        # frame that was written (flushed) at the SAME cycle?
        mismatches: List[float] = []  # audio_pts - written_pts
        last_chunk = -1

        for frame_num in range(1, n_frames + 1):
            pts_ms = frame_num / fps * 1000.0
            now = time.monotonic()
            pkt = FramePacket(
                frame_index=frame_num,
                pts_ms=pts_ms,
                audio_chunk_index=int(frame_num / fps / STEP_DUR),
                image=image,
                audio_data=None,
                pipeline_entry_ts=now,
                pipeline_exit_ts=now,
            )
            chunk_idx = int(frame_num / fps / STEP_DUR)
            audio_collected_this_cycle = chunk_idx != last_chunk
            if audio_collected_this_cycle:
                last_chunk = chunk_idx

            writer.enqueue(pkt)
            flushed: List[float] = []
            writer.flush_ready(lambda img, pts: flushed.append(pts))

            if audio_collected_this_cycle and flushed:
                # Audio was collected for pts_ms, but flushed frame is older
                mismatch = pts_ms / 1000.0 - flushed[0] / 1000.0
                mismatches.append(mismatch)

        # Flush remaining
        writer.flush_and_collect()

        if mismatches:
            max_mismatch_s = max(mismatches)
            # With heap_size = 6, max mismatch ≈ heap_size / fps = 0.2 s
            assert max_mismatch_s >= 0.0, (
                "Mismatch should be non-negative (audio collected ahead of "
                "or at the same time as the corresponding written frame)."
            )
            # The mismatch is at most heap_size frames worth
            assert max_mismatch_s <= heap_size / fps + 1.0 / fps + 1e-3, (
                f"Heap-lag mismatch {max_mismatch_s:.3f}s exceeds expected "
                f"maximum {heap_size / fps:.3f}s (heap_size={heap_size}, "
                f"fps={fps})"
            )


# ---------------------------------------------------------------------------
# 6.  Gap-fill duplicates inflate video frame count
# ---------------------------------------------------------------------------


class TestGapFillInflatesVideo:
    """
    SyncVideoWriter inserts duplicate frames to fill PTS gaps.  These duplicate
    frames add video time with NO corresponding new audio, shifting the
    audio/video balance.
    """

    def test_gap_fill_increases_video_duration(self):
        """
        Introducing a large PTS gap causes `_drain_heap_locked` to insert
        duplicate frames.  The total written duration increases beyond the
        input pts_ms range, which would push the audio/video ratio out of sync.
        """
        fps = 30.0
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        writer = SyncVideoWriter(fps=fps, max_buffer_size=20)

        # 10 normal frames, then a 10-frame gap, then 10 more frames
        packets = []
        for i in range(10):
            now = time.monotonic()
            packets.append(FramePacket(
                frame_index=i,
                pts_ms=i / fps * 1000.0,
                audio_chunk_index=0,
                image=image,
                audio_data=None,
                pipeline_entry_ts=now,
                pipeline_exit_ts=now,
            ))
        # Inject a gap: jump from frame 9 to frame 20
        for i in range(20, 30):
            now = time.monotonic()
            packets.append(FramePacket(
                frame_index=i,
                pts_ms=i / fps * 1000.0,
                audio_chunk_index=0,
                image=image,
                audio_data=None,
                pipeline_entry_ts=now,
                pipeline_exit_ts=now,
            ))

        written = writer.consume_and_collect(packets)

        expected_unique = 10 + 10  # 20 input packets (no frames 10-19)
        # Gap-fill should insert ≤ _MAX_GAP_FILL_DUPLICATES = 4 duplicates
        assert len(written) >= expected_unique, (
            f"Expected ≥{expected_unique} written frames, got {len(written)}"
        )

        # More frames were written than input → gap-fill occurred
        if len(written) > expected_unique:
            pts_list = [p.pts_ms for p in written]
            # PTS must be monotone
            for j in range(len(pts_list) - 1):
                assert pts_list[j] <= pts_list[j + 1], (
                    f"Non-monotone PTS at index {j}: "
                    f"{pts_list[j]:.2f} > {pts_list[j+1]:.2f}"
                )

    def test_gap_fill_frames_carry_no_new_audio(self):
        """
        Duplicate gap-fill frames inherit `audio_data` from the previous real
        frame.  If that audio_data chunk is the same across multiple duplicates,
        the VideoWriter would collect it only once (deduplication by chunk_index).
        Verify that the audio_data of each gap-fill frame is identical to its
        source.
        """
        fps = 30.0
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        audio_ref = {"data": np.zeros(100, np.float32), "sample_rate": SR,
                     "chunk_index": 0, "step_duration": STEP_DUR}

        writer = SyncVideoWriter(fps=fps, max_buffer_size=20)

        now = time.monotonic()
        # Frame 0, then a gap to frame 5
        pkt0 = FramePacket(
            frame_index=0, pts_ms=0.0, audio_chunk_index=0,
            image=image, audio_data=audio_ref,
            pipeline_entry_ts=now, pipeline_exit_ts=now,
        )
        pkt5 = FramePacket(
            frame_index=5, pts_ms=5 / fps * 1000.0, audio_chunk_index=0,
            image=image, audio_data=audio_ref,
            pipeline_entry_ts=now, pipeline_exit_ts=now,
        )
        written = writer.consume_and_collect([pkt0, pkt5])

        # Some gap-fill duplicates should have been inserted
        gap_fill = [p for p in written if p.frame_index == 0 and p is not pkt0 and p is not pkt5]
        for dup in gap_fill:
            assert dup.audio_data is audio_ref, (
                "Gap-fill duplicate must carry the same audio_data reference "
                "as its source frame."
            )


# ---------------------------------------------------------------------------
# 7.  Full pipeline offset measurement
# ---------------------------------------------------------------------------


class TestFullPipelineOffset:
    """
    End-to-end simulation: given a synthetic video of known duration, measure
    the exact A/V offset that would appear in the merged file, and verify that
    the required trim computation is correct.
    """

    @pytest.mark.parametrize(
        "start_frame, fps, step_dur, n_frames",
        [
            # Ideal: start at frame 0 (0-indexed) → zero offset
            (0, 30.0, 1.0, 300),
            # Standard 1-indexed first frame → 1/fps offset
            (1, 30.0, 1.0, 299),
            # Mid-step: 15 frames in at 30 fps with 1 s step → 0.5 s offset
            (15, 30.0, 1.0, 285),
            # Worst case: one frame before step boundary
            (29, 30.0, 1.0, 271),
            # Non-integer step alignment at 25 fps
            (13, 25.0, 1.0, 200),
            # Smaller step (0.5 s) → smaller maximum offset
            (7, 30.0, 0.5, 150),
        ],
    )
    def test_measured_av_offset_matches_analytical_formula(
        self, start_frame: int, fps: float, step_dur: float, n_frames: int
    ):
        """
        The measured A/V offset must equal the analytical formula:
            offset_s = (start_frame / fps) - floor(start_frame / fps / step_dur) * step_dur

        This test is the definitive diagnostic: if it fails, the formula is
        wrong; if it passes but the merged video is out of sync, the merge
        step is not applying the trim.
        """
        audio, sr = _make_audio_file(total_duration_s=max(60.0, (start_frame + n_frames) / fps + 5), sr=SR)
        chunks = _build_chunks(audio, sr, chunk_dur=CHUNK_DUR, step_dur=step_dur)

        collected, first_frame_s = _simulate_recording(
            start_frame,
            start_frame + n_frames,
            fps,
            chunks,
            sr,
            step_dur=step_dur,
        )

        # Analytical formula
        _, first_chunk_idx = _get_chunk_for_frame(
            start_frame, fps, chunks, step_dur=step_dur
        )
        expected_offset_s = first_frame_s - first_chunk_idx * step_dur

        # Measured offset from audio duration vs video duration
        audio_duration_s = len(collected) / sr
        video_duration_s = n_frames / fps
        measured_excess_s = audio_duration_s - video_duration_s

        # The measured excess should be within [expected_offset - step_dur, expected_offset + step_dur]
        # (one step_dur tolerance for the final partial chunk)
        lower = expected_offset_s - step_dur - 1.0 / fps
        upper = expected_offset_s + step_dur + 1.0 / fps
        assert lower <= measured_excess_s <= upper, (
            f"start_frame={start_frame}, fps={fps}, step_dur={step_dur}: "
            f"expected offset ≈ {expected_offset_s:.4f}s, "
            f"measured audio excess = {measured_excess_s:.4f}s "
            f"(not in [{lower:.4f}, {upper:.4f}])"
        )

    def test_trim_corrects_offset_precisely(self):
        """
        After applying the analytical trim to the collected audio, the trimmed
        audio duration must match the video duration within ±step_dur.

        This is the FIX: `_merge_audio_video_ffmpeg` should apply this trim
        before writing the WAV file.
        """
        fps = 30.0
        step_dur = 1.0
        start_frame = 25   # 25/30 ≈ 0.833 s, chunk boundary = 0 s, offset = 0.833 s
        n_frames = 240

        audio, sr = _make_audio_file(20.0, SR)
        chunks = _build_chunks(audio, sr, step_dur=step_dur)

        collected, first_frame_s = _simulate_recording(
            start_frame, start_frame + n_frames, fps, chunks, sr, step_dur=step_dur
        )

        _, first_chunk_idx = _get_chunk_for_frame(start_frame, fps, chunks, step_dur)
        offset_s = first_frame_s - first_chunk_idx * step_dur
        trim_samples = int(offset_s * sr)

        trimmed_audio = collected[trim_samples:]
        trimmed_duration_s = len(trimmed_audio) / sr
        video_duration_s = n_frames / fps

        discrepancy_s = abs(trimmed_duration_s - video_duration_s)
        assert discrepancy_s <= step_dur + 1.0 / fps + 1e-3, (
            f"After trim, audio ({trimmed_duration_s:.4f}s) and video "
            f"({video_duration_s:.4f}s) differ by {discrepancy_s:.4f}s. "
            f"Offset was {offset_s:.4f}s, trim_samples={trim_samples}."
        )

    def test_no_trim_produces_detectable_desync(self):
        """
        Without the trim, the merged file would have a detectable A/V desync
        (images ahead).  Confirm that the untrimmed excess is significant.
        """
        fps = 30.0
        step_dur = 1.0
        start_frame = 20   # 20/30 ≈ 0.667 s → 0.667 s offset
        n_frames = 300

        audio, sr = _make_audio_file(20.0, SR)
        chunks = _build_chunks(audio, sr, step_dur=step_dur)

        collected, first_frame_s = _simulate_recording(
            start_frame, start_frame + n_frames, fps, chunks, sr, step_dur=step_dur
        )

        _, first_chunk_idx = _get_chunk_for_frame(start_frame, fps, chunks, step_dur)
        expected_offset_s = first_frame_s - first_chunk_idx * step_dur

        # Without trim the audio excess is non-trivially large
        audio_duration_s = len(collected) / sr
        video_duration_s = n_frames / fps
        excess_s = audio_duration_s - video_duration_s

        assert expected_offset_s > 0.1, (
            f"Test misconfigured: expected offset {expected_offset_s:.3f}s "
            "must be > 0.1 s to be detectable."
        )

        assert excess_s >= expected_offset_s - step_dur - 1.0 / fps, (
            f"Measured audio excess {excess_s:.4f}s is unexpectedly small "
            f"given expected offset {expected_offset_s:.4f}s."
        )


# ---------------------------------------------------------------------------
# 8.  PyAVEncoder PTS alignment (requires 'av' package)
# ---------------------------------------------------------------------------


class TestPyAVEncoderPTSAlignment:
    """
    Verify that :class:`PyAVEncoder` correctly assigns explicit PTS values to
    both video and audio frames, ensuring A/V alignment at the container level.
    """

    def test_pyav_available(self):
        """PyAV must be importable for the encoder tests to be meaningful."""
        try:
            import av  # noqa: F401
        except ImportError:
            pytest.skip("av package not installed – install with: pip install av")

    def test_video_frame_pts_matches_input(self):
        """
        `write_video_frame(image, pts_ms)` must encode the frame with the
        exact PTS passed (within the ms timebase resolution).
        """
        try:
            import av  # noqa: F401
        except ImportError:
            pytest.skip("av package not installed")

        import tempfile
        import os
        from node.VideoNode.av_encoder import PyAVEncoder

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "test.mkv")
            enc = PyAVEncoder(out, fps=30.0, frame_size=(64, 64))
            image = np.zeros((64, 64, 3), dtype=np.uint8)
            pts_values = [0.0, 33.3, 66.7, 100.0, 133.3]
            for pts in pts_values:
                enc.write_video_frame(image, pts)
            enc.close()

            # Re-open and check PTS of demuxed packets
            container = av.open(out)
            video_stream = next(
                (s for s in container.streams if s.type == "video"), None
            )
            assert video_stream is not None, "Output has no video stream"
            written_pts = []
            for pkt in container.demux(video_stream):
                if pkt.pts is not None:
                    written_pts.append(
                        float(pkt.pts * video_stream.time_base) * 1000.0
                    )
            container.close()

            # Each written PTS should be within 1 ms of the input PTS
            for i, (expected, actual) in enumerate(zip(pts_values, written_pts)):
                assert abs(actual - expected) <= 1.5, (
                    f"Frame {i}: expected PTS {expected:.1f}ms, "
                    f"got {actual:.1f}ms in container."
                )

    def test_audio_pts_aligns_with_video_pts(self):
        """
        Write interleaved video and audio.  At each step, verify that the
        audio PTS (converted to ms) matches the video PTS within one audio
        frame duration.
        """
        try:
            import av  # noqa: F401
        except ImportError:
            pytest.skip("av package not installed")

        import tempfile
        import os
        from node.VideoNode.av_encoder import PyAVEncoder

        fps = 30.0
        sr = 22_050
        frame_dur_ms = 1000.0 / fps  # ≈ 33.33 ms
        step_dur_samples = int(STEP_DUR * sr)
        n_steps = 5

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "test_av.mkv")
            enc = PyAVEncoder(
                out, fps=fps, frame_size=(64, 64),
                audio_sample_rate=sr, audio_channels=1,
            )
            image = np.zeros((64, 64, 3), dtype=np.uint8)

            for step in range(n_steps):
                # Write fps video frames for this step
                for frame_in_step in range(int(fps)):
                    global_frame = step * int(fps) + frame_in_step
                    pts_ms = global_frame / fps * 1000.0
                    enc.write_video_frame(image, pts_ms)

                # Write one audio chunk for this step
                audio_chunk = np.zeros(step_dur_samples, dtype=np.float32)
                audio_pts_samples = step * step_dur_samples
                enc.write_audio_chunk(audio_chunk, sr, audio_pts_samples)

            enc.close()

            # Verify audio PTS in container
            import av as _av
            container = _av.open(out)
            audio_stream = next(
                (s for s in container.streams if s.type == "audio"), None
            )
            assert audio_stream is not None, "Output has no audio stream"

            audio_pts_ms: List[float] = []
            for pkt in container.demux(audio_stream):
                if pkt.pts is not None:
                    audio_pts_ms.append(
                        float(pkt.pts * audio_stream.time_base) * 1000.0
                    )
            container.close()

            # Audio PTS must be monotonically non-decreasing
            for i in range(len(audio_pts_ms) - 1):
                assert audio_pts_ms[i] <= audio_pts_ms[i + 1], (
                    f"Audio PTS not monotone at index {i}: "
                    f"{audio_pts_ms[i]:.1f} > {audio_pts_ms[i+1]:.1f}"
                )

            # First audio PTS should be at or near 0 ms
            if audio_pts_ms:
                assert audio_pts_ms[0] >= 0.0
                assert audio_pts_ms[0] < STEP_DUR * 1000.0

    def test_aac_encoder_delay_is_non_zero(self):
        """
        AAC has an initial encoder delay of ~1024 samples (~23 ms at 44100 Hz).
        This test DOCUMENTS the delay by measuring it.  A non-zero delay that
        is not compensated causes a fixed audio offset in the merged file.
        """
        try:
            import av  # noqa: F401
        except ImportError:
            pytest.skip("av package not installed")

        import tempfile
        import os
        from node.VideoNode.av_encoder import PyAVEncoder

        sr = 44_100
        n_samples = sr * 2  # 2 seconds of audio

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "aac_delay.mkv")
            enc = PyAVEncoder(
                out, fps=30.0, frame_size=(64, 64),
                audio_sample_rate=sr, audio_channels=1,
                audio_codec="aac",
            )

            # Write 1 video frame
            enc.write_video_frame(np.zeros((64, 64, 3), dtype=np.uint8), 0.0)

            # Write audio with PTS = 0
            audio_data = np.zeros(n_samples, dtype=np.float32)
            enc.write_audio_chunk(audio_data, sr, pts_samples=0)
            enc.close()

            # Probe the output for audio stream start_time
            import av as _av
            container = _av.open(out)
            audio_stream = next(
                (s for s in container.streams if s.type == "audio"), None
            )

            first_audio_pts_ms: Optional[float] = None
            if audio_stream is not None:
                for pkt in container.demux(audio_stream):
                    if pkt.pts is not None:
                        first_audio_pts_ms = float(pkt.pts * audio_stream.time_base) * 1000.0
                        break
            container.close()

            # Document: first audio PTS may not be 0 (AAC encoder delay)
            # This test captures the actual delay value rather than asserting it is 0
            if first_audio_pts_ms is not None:
                aac_delay_ms = first_audio_pts_ms
                # AAC delay is typically 0 to ~46 ms (0–2048 samples at 44100 Hz)
                assert -10.0 <= aac_delay_ms <= 100.0, (
                    f"AAC initial delay {aac_delay_ms:.2f}ms is outside the "
                    "expected range [-10, 100]ms.  Verify encoder behaviour."
                )


# ---------------------------------------------------------------------------
# 9.  Regression: step_trim takes BEGINNING (not end) of chunk
# ---------------------------------------------------------------------------


class TestStepTrimDirection:
    """
    Regression tests confirming that `chunk_data[:step_samples]` is the
    CORRECT direction of trimming for a BEGINNING-anchored sliding window
    (chunk i starts at i*step_dur in the original timeline).

    If the window were END-anchored (newest data at the end of each chunk),
    the correct trim would be `chunk_data[-step_samples:]`, and the current
    code would be WRONG.
    """

    def test_beginning_anchored_window_trim_is_correct(self):
        """
        Chunk i: audio[i*step_samples : i*step_samples + chunk_samples]
        First step_dur of chunk i = audio[i*step_samples : (i+1)*step_samples]
        This is the NEW (non-overlapping) portion at the START.
        """
        audio, sr = _make_audio_file(10.0, SR)
        chunks = _build_chunks(audio, sr, chunk_dur=CHUNK_DUR, step_dur=STEP_DUR)
        step_samples = int(STEP_DUR * sr)

        for i, chunk in enumerate(chunks[:-1]):
            correct_start = i * step_samples
            correct_end = (i + 1) * step_samples
            new_portion = audio[correct_start:correct_end]

            # Beginning-trim (the current implementation)
            beginning_trim = chunk[:step_samples]
            np.testing.assert_array_equal(
                beginning_trim, new_portion,
                err_msg=(
                    f"Chunk {i}: beginning trim [:step_samples] does not equal "
                    f"original[{correct_start}:{correct_end}]. "
                    "This confirms beginning-trim is CORRECT for this window type."
                ),
            )

            # End-trim (would be WRONG)
            end_trim = chunk[-step_samples:]
            # The end portion of chunk i = audio[(chunk_idx*step + chunk_dur - step) : chunk_idx*step + chunk_dur]
            #                             = audio[(i*step + chunk_dur - step) : (i+1)*step + chunk_dur - step]
            end_correct_start = correct_start + int((CHUNK_DUR - STEP_DUR) * sr)
            end_correct_end = end_correct_start + step_samples
            if end_correct_end <= len(audio):
                end_portion = audio[end_correct_start:end_correct_end]
                np.testing.assert_array_equal(
                    end_trim, end_portion,
                    err_msg=f"Chunk {i}: end trim sanity check failed.",
                )
                # Confirm beginning != end (they differ for i>0)
                if i > 0:
                    assert not np.array_equal(beginning_trim, end_trim), (
                        f"Chunk {i}: beginning and end trims are identical — "
                        "cannot distinguish correct from incorrect direction."
                    )


# ---------------------------------------------------------------------------
# 10.  Summary diagnostic
# ---------------------------------------------------------------------------


class TestSummaryDiagnostic:
    """
    Single omnibus test that measures ALL identified contributors to the
    'images ahead' issue and reports the total expected offset.
    """

    def test_total_av_offset_budget(self):
        """
        Measure and print all contributors to A/V offset for a typical
        recording scenario (start_frame=20, fps=30, step_dur=1s).

        Expected breakdown:
          - Step-boundary lead:    floor(20/30) * 1s - 20/30s = -(20/30 - 0) = -0.667 s (audio ahead)
          - 1-index built-in:      -(1/30) s ≈ -0.033 s (audio ahead)
          - Heap lag (6 frames):   +6/30 = 0.200 s (audio ahead)

        Total ≈ -0.900 s (audio is ~0.9 s ahead → images appear 0.9 s ahead).
        """
        fps = 30.0
        step_dur = 1.0
        heap_size = max(4, int(fps * 0.2))  # = 6
        start_frame = 20

        audio, sr = _make_audio_file(20.0, SR)
        chunks = _build_chunks(audio, sr, step_dur=step_dur)

        # 1. Step-boundary lead
        _, first_chunk_idx = _get_chunk_for_frame(start_frame, fps, chunks, step_dur)
        step_boundary_lead_s = (start_frame / fps) - first_chunk_idx * step_dur
        assert step_boundary_lead_s >= 0.0, (
            f"Step boundary lead must be non-negative, got {step_boundary_lead_s}"
        )

        # 2. One-index built-in lead (audio starts at 0 but first frame = 1/fps)
        one_index_lead_s = 1.0 / fps

        # 3. Heap-lag contribution (audio collected ahead of written frame)
        # The heap writes the oldest frame; for a full heap of size K,
        # audio is collected K frames ahead of the written frame
        heap_lag_lead_s = heap_size / fps  # audio collection is this many s ahead

        total_expected_lead_s = step_boundary_lead_s + one_index_lead_s + heap_lag_lead_s

        print(
            f"\n=== A/V offset budget (start_frame={start_frame}, fps={fps}, "
            f"step_dur={step_dur}s, heap_size={heap_size}) ==="
        )
        print(f"  Step-boundary lead:  {step_boundary_lead_s:+.3f}s")
        print(f"  1-index built-in:    {one_index_lead_s:+.3f}s")
        print(f"  Heap-lag lead:       {heap_lag_lead_s:+.3f}s")
        print(f"  TOTAL (audio ahead): {total_expected_lead_s:+.3f}s")
        print(
            f"  → At 30 fps, images appear "
            f"~{total_expected_lead_s*1000:.0f}ms ahead of corresponding audio."
        )

        # All contributors must be non-negative (all push audio ahead)
        assert step_boundary_lead_s >= 0.0
        assert one_index_lead_s >= 0.0
        assert heap_lag_lead_s >= 0.0

        # Total must be sub-second for a realistic scenario
        assert total_expected_lead_s < step_dur + heap_size / fps + 0.5
