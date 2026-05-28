#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Synchronisation layer for the CV_Studio video pipeline.

Provides:
  - FramePacket        : typed dataclass that travels from VideoNode through
                         the pipeline carrying PTS, audio metadata, and latency
                         metrics.
  - SyncVideoWriter    : PriorityQueue-backed writer with Drop/Wait policies
                         and A/V drift detection.
  - AVDriftDetector    : standalone detector emitting warnings when A/V drift
                         exceeds a configurable threshold.

Design goals
------------
* ``FramePacket`` is the single source of truth about when a frame should be
  presented.  It is created by VideoNode (the *Time-Reference Master*) and
  propagated through every processing node unchanged.
* ``SyncVideoWriter`` re-orders frames that arrive out-of-order due to AI
  processing jitter, fills timing gaps with frame duplication, and applies
  configurable drop/wait policies when the pipeline is overloaded.
* The module has **no dependency** on DearPyGui or cv2 so that tests can
  import it in pure-Python environments.
"""
from __future__ import annotations

import heapq
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SyncError(Exception):
    """Base class for synchronisation errors."""


class AVDriftError(SyncError):
    """Raised (or logged) when A/V drift exceeds the configured maximum."""

    def __init__(self, drift_ms: float, max_ms: float) -> None:
        super().__init__(
            f"A/V drift {drift_ms:.1f} ms exceeds maximum {max_ms:.1f} ms"
        )
        self.drift_ms = drift_ms
        self.max_ms = max_ms


# ---------------------------------------------------------------------------
# FramePacket
# ---------------------------------------------------------------------------


@dataclass
class FramePacket:
    """Typed container that travels through the CV_Studio pipeline.

    Created by :class:`~node.InputNode.node_video.VideoNode` and meant to be
    propagated unmodified through every downstream processing node so that
    :class:`SyncVideoWriter` can use the original PTS for ordering.

    Fields
    ------
    frame_index
        Frame index in the source video (0-based).
    pts_ms
        Presentation Time Stamp derived from the *source* video clock, in
        milliseconds.  ``pts_ms = frame_index / source_fps * 1000``.
    audio_chunk_index
        Index of the audio chunk that is synchronous with this frame.
    image
        BGR image as a NumPy ``uint8`` array.
    audio_data
        Audio chunk dict (or *None*).  Expected keys: ``'data'``,
        ``'sample_rate'``, ``'chunk_index'``.  May also contain a ``'pts_ms'``
        key used by :class:`AVDriftDetector`.
    pipeline_entry_ts
        ``time.monotonic()`` when the frame *entered* the AI/processing stage.
    pipeline_exit_ts
        ``time.monotonic()`` when the frame *exited* the AI/processing stage.
    late
        Set to ``True`` by :class:`SyncVideoWriter` when the pipeline delay
        exceeded the warn threshold.
    """

    frame_index: int
    pts_ms: float
    audio_chunk_index: int
    image: np.ndarray
    audio_data: Optional[Any]
    pipeline_entry_ts: float = field(default_factory=time.monotonic)
    pipeline_exit_ts: float = field(default_factory=time.monotonic)
    late: bool = False

    # ------------------------------------------------------------------
    # Ordering support (heapq uses __lt__)
    # ------------------------------------------------------------------

    def __lt__(self, other: "FramePacket") -> bool:  # noqa: D105
        return self.pts_ms < other.pts_ms

    def __le__(self, other: "FramePacket") -> bool:  # noqa: D105
        return self.pts_ms <= other.pts_ms

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def latency_ms(self) -> float:
        """AI processing latency for this frame (ms)."""
        return (self.pipeline_exit_ts - self.pipeline_entry_ts) * 1000.0

    def pipeline_delay_ms(self) -> float:
        """Total pipeline delay at the current instant (ms since entry)."""
        return (time.monotonic() - self.pipeline_entry_ts) * 1000.0

    def to_metadata(self) -> dict:
        """Return a JSON-serialisable dict *without* the image array.

        The result is suitable for embedding in ``node_result_dict`` so that
        downstream nodes (including :class:`SyncVideoWriter`) can reconstruct
        the :class:`FramePacket` from the metadata alone.
        """
        return {
            "_frame_packet": {
                "frame_index": self.frame_index,
                "pts_ms": self.pts_ms,
                "audio_chunk_index": self.audio_chunk_index,
                "pipeline_entry_ts": self.pipeline_entry_ts,
                "pipeline_exit_ts": self.pipeline_exit_ts,
                "late": self.late,
            }
        }

    @staticmethod
    def from_metadata(
        meta: dict,
        image: np.ndarray,
        audio_data: Optional[Any] = None,
    ) -> "FramePacket":
        """Reconstruct a :class:`FramePacket` from a metadata dict.

        Parameters
        ----------
        meta:
            Dict previously created by :meth:`to_metadata`.  The
            ``_frame_packet`` sub-dict must be present.
        image:
            BGR image to attach to the packet.
        audio_data:
            Optional audio chunk to attach.
        """
        fp = meta.get("_frame_packet", {})
        now = time.monotonic()
        return FramePacket(
            frame_index=fp.get("frame_index", 0),
            pts_ms=fp.get("pts_ms", 0.0),
            audio_chunk_index=fp.get("audio_chunk_index", 0),
            image=image,
            audio_data=audio_data,
            pipeline_entry_ts=fp.get("pipeline_entry_ts", now),
            pipeline_exit_ts=fp.get("pipeline_exit_ts", now),
            late=fp.get("late", False),
        )


# ---------------------------------------------------------------------------
# AVDriftDetector
# ---------------------------------------------------------------------------


class AVDriftDetector:
    """Stateless A/V drift checker.

    Call :meth:`check` on each :class:`FramePacket` to detect A/V drift.
    If ``packet.audio_data`` contains a ``'pts_ms'`` key, that value is used
    as the audio clock reference.  Otherwise drift is computed from
    ``audio_chunk_index * step_duration_ms``.

    Parameters
    ----------
    max_av_drift_ms:
        Hard maximum A/V drift in milliseconds.  Above this value the detector
        logs an error and calls ``on_error`` if provided.
    step_duration_ms:
        Duration of one audio chunk in milliseconds (default: 1000 ms).
    on_warning:
        Callable invoked as ``on_warning(packet, drift_ms)`` when drift enters
        the warning zone ``[warn_threshold, max_av_drift_ms)``.
    on_error:
        Callable invoked as ``on_error(packet, drift_ms)`` when drift reaches
        or exceeds ``max_av_drift_ms``.
    """

    def __init__(
        self,
        max_av_drift_ms: float = 80.0,
        step_duration_ms: float = 1000.0,
        on_warning: Optional[Callable[["FramePacket", float], None]] = None,
        on_error: Optional[Callable[["FramePacket", float], None]] = None,
    ) -> None:
        self._max_av_drift_ms = max_av_drift_ms
        self._step_duration_ms = step_duration_ms
        # Warning fires in [warn_threshold, max_av_drift_ms)
        self._warn_threshold_ms = max_av_drift_ms * 0.9
        self.on_warning = on_warning
        self.on_error = on_error

    # ------------------------------------------------------------------

    def check(self, packet: "FramePacket") -> float:
        """Check A/V drift for *packet* and fire callbacks as appropriate.

        Returns
        -------
        float
            The measured A/V drift in milliseconds (always >= 0).
        """
        audio_ref_ms = self._audio_ref_ms(packet)
        if audio_ref_ms is None:
            return 0.0

        drift_ms = abs(packet.pts_ms - audio_ref_ms)

        if drift_ms >= self._max_av_drift_ms:
            logger.error(
                "A/V drift %.1f ms exceeds hard limit %.1f ms (frame_index=%d)",
                drift_ms,
                self._max_av_drift_ms,
                packet.frame_index,
            )
            if self.on_error is not None:
                self.on_error(packet, drift_ms)
        elif drift_ms >= self._warn_threshold_ms:
            logger.warning(
                "A/V drift warning: %.1f ms (warn_threshold=%.1f ms, frame_index=%d)",
                drift_ms,
                self._warn_threshold_ms,
                packet.frame_index,
            )
            if self.on_warning is not None:
                self.on_warning(packet, drift_ms)

        return drift_ms

    # ------------------------------------------------------------------

    def _audio_ref_ms(self, packet: "FramePacket") -> Optional[float]:
        """Return the audio reference PTS in ms, or *None* if unavailable."""
        if packet.audio_data is None:
            return None
        if isinstance(packet.audio_data, dict):
            if "pts_ms" in packet.audio_data:
                return float(packet.audio_data["pts_ms"])
        # Fall back to chunk-index-based reference
        return packet.audio_chunk_index * self._step_duration_ms


# ---------------------------------------------------------------------------
# SyncVideoWriter
# ---------------------------------------------------------------------------


class SyncVideoWriter:
    """PriorityQueue-backed frame writer with Drop/Wait policies.

    The writer maintains an internal min-heap ordered by :attr:`FramePacket.pts_ms`.
    This re-orders frames that arrive out-of-order (e.g. due to variable AI
    processing latency) before they reach the actual encoder backend.

    When the pipeline is overloaded, one of two drop policies is applied:

    * ``'drop_oldest'`` (default) — evict the oldest buffered frame to make
      room for the incoming one.  Useful when you want to keep the most
      recent content.
    * ``'drop_newest'`` — discard the incoming frame.  Useful when the
      encoder must not be interrupted.

    Parameters
    ----------
    fps:
        Target video framerate.
    max_buffer_size:
        Maximum number of frames held in the internal heap at once.
    drop_policy:
        Either ``'drop_oldest'`` or ``'drop_newest'``.
    max_av_drift_ms:
        A/V drift hard limit passed to :class:`AVDriftDetector`.
    warn_latency_ms:
        Pipeline delay (ms) above which a frame is marked *late*.
    drop_latency_ms:
        Pipeline delay (ms) above which drop/wait logic is activated.
    consumer_delay_ms:
        Artificial delay per frame added by the consumer thread (ms).
        Used in tests to simulate a slow encoder.
    step_duration_ms:
        Audio chunk duration (ms) passed to :class:`AVDriftDetector`.
    """

    def __init__(
        self,
        fps: float,
        max_buffer_size: int = 10,
        drop_policy: str = "drop_oldest",
        max_av_drift_ms: float = 80.0,
        warn_latency_ms: float = 33.0,
        drop_latency_ms: float = 200.0,
        consumer_delay_ms: float = 0.0,
        step_duration_ms: float = 1000.0,
    ) -> None:
        self._fps = fps
        self._frame_duration_ms = 1000.0 / fps if fps > 0 else 33.3
        self._max_buffer_size = max_buffer_size
        self._drop_policy = drop_policy
        self._warn_latency_ms = warn_latency_ms
        self._drop_latency_ms = drop_latency_ms
        self._consumer_delay_ms = consumer_delay_ms

        # Internal state
        self._heap: List[FramePacket] = []
        self._lock = threading.Lock()
        self._written: List[FramePacket] = []
        self._dropped_frame_count: int = 0
        self._peak_buffer_size: int = 0

        # Optional drift-warning callback (set directly on the instance)
        self.on_drift_warning: Optional[Callable[["FramePacket", float], None]] = None

        # A/V drift detector
        self._drift_detector = AVDriftDetector(
            max_av_drift_ms=max_av_drift_ms,
            step_duration_ms=step_duration_ms,
        )

        # Wire up drift warning callback via property
        def _forward_warning(pkt: FramePacket, drift: float) -> None:
            if self.on_drift_warning is not None:
                self.on_drift_warning(pkt, drift)

        self._drift_detector.on_warning = _forward_warning

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def dropped_frame_count(self) -> int:
        """Total number of frames dropped since this writer was created."""
        return self._dropped_frame_count

    @property
    def peak_buffer_size(self) -> int:
        """Maximum number of frames that were buffered simultaneously."""
        return self._peak_buffer_size

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def enqueue(self, packet: FramePacket) -> None:
        """Thread-safe enqueue with Drop/Wait and A/V drift policies applied.

        The method **never raises** an exception; overload conditions are
        handled by drop policies and logged.

        Parameters
        ----------
        packet:
            Frame to enqueue.
        """
        try:
            with self._lock:
                # Run A/V drift check unconditionally
                self._drift_detector.check(packet)

                delay_ms = packet.pipeline_delay_ms()

                # Mark late flag
                if delay_ms >= self._warn_latency_ms:
                    packet.late = True

                # ---- Drop/Wait policy ----
                buffer_full = len(self._heap) >= self._max_buffer_size

                if delay_ms >= self._drop_latency_ms and buffer_full:
                    if self._drop_policy == "drop_oldest":
                        # Evict the oldest (lowest pts_ms) frame
                        heapq.heappop(self._heap)
                        self._dropped_frame_count += 1
                        logger.debug(
                            "SyncVideoWriter: dropped oldest frame "
                            "(delay=%.1f ms, buffer_size=%d)",
                            delay_ms,
                            self._max_buffer_size,
                        )
                    else:
                        # drop_newest: discard the incoming packet
                        self._dropped_frame_count += 1
                        logger.debug(
                            "SyncVideoWriter: dropped newest frame "
                            "(delay=%.1f ms, buffer_size=%d)",
                            delay_ms,
                            self._max_buffer_size,
                        )
                        return

                elif buffer_full:
                    # Buffer full but delay below drop threshold → drop newest anyway
                    self._dropped_frame_count += 1
                    logger.debug(
                        "SyncVideoWriter: buffer full, dropped newest frame "
                        "(delay=%.1f ms)",
                        delay_ms,
                    )
                    return

                heapq.heappush(self._heap, packet)
                self._peak_buffer_size = max(
                    self._peak_buffer_size, len(self._heap)
                )

        except Exception:
            logger.exception("SyncVideoWriter.enqueue: unexpected error")

    def consume_and_collect(
        self, packets: List[FramePacket]
    ) -> List[FramePacket]:
        """Synchronously process *packets* and return the written frame list.

        All packets are pushed into the internal heap then processed in PTS
        order.  Timing gaps larger than ``2 × frame_duration`` are filled with
        duplicate frames.

        This method is the primary entry-point for batch/test usage.

        Parameters
        ----------
        packets:
            Frames to process (order does not matter; they are sorted by PTS).

        Returns
        -------
        list[FramePacket]
            Frames in PTS order, with gap-fill duplicates inserted.
        """
        with self._lock:
            for p in packets:
                heapq.heappush(self._heap, p)
                self._peak_buffer_size = max(
                    self._peak_buffer_size, len(self._heap)
                )
            result = self._drain_heap_locked()
            self._written.extend(result)
        return result

    def flush_and_collect(self) -> List[FramePacket]:
        """Drain the internal buffer and return all written frames.

        Intended for use after a series of :meth:`enqueue` calls (e.g. at the
        end of a recording session or in tests that inject frames in bulk).

        Returns
        -------
        list[FramePacket]
            Frames in PTS order, with gap-fill duplicates inserted.
        """
        with self._lock:
            result = self._drain_heap_locked()
            self._written.extend(result)
        return result

    def flush_ready(
        self,
        write_fn: Callable[[np.ndarray, float], None],
    ) -> int:
        """Pop and write one frame from the heap (for streaming integration).

        Designed to be called from :meth:`VideoWriterNode.update` once per
        pipeline cycle.  It pops the frame with the lowest PTS from the heap,
        inserts duplicate frames if the PTS gap is too large, and calls
        ``write_fn(image, pts_ms)`` for each frame.

        Parameters
        ----------
        write_fn:
            Callable receiving ``(image_array, pts_ms)`` that performs the
            actual encoder write.

        Returns
        -------
        int
            Number of frames written (0 or more, including duplicates).
        """
        written_count = 0
        with self._lock:
            if not self._heap:
                return 0

            packet = heapq.heappop(self._heap)

            # Gap-fill duplicates
            if self._written:
                last_pts = self._written[-1].pts_ms
                gap_ms = packet.pts_ms - last_pts
                num_dup = int(gap_ms / self._frame_duration_ms) - 1
                if num_dup > 0 and last_pts >= 0:
                    dup_frame = self._written[-1]
                    for d in range(min(num_dup, 4)):  # cap at 4 duplicates
                        dup_pts = last_pts + (d + 1) * self._frame_duration_ms
                        dup = FramePacket(
                            frame_index=dup_frame.frame_index,
                            pts_ms=dup_pts,
                            audio_chunk_index=dup_frame.audio_chunk_index,
                            image=dup_frame.image,
                            audio_data=dup_frame.audio_data,
                            pipeline_entry_ts=dup_frame.pipeline_entry_ts,
                            pipeline_exit_ts=dup_frame.pipeline_exit_ts,
                        )
                        try:
                            write_fn(dup.image, dup_pts)
                        except Exception:
                            logger.exception("SyncVideoWriter.flush_ready: write_fn error (duplicate)")
                        self._written.append(dup)
                        written_count += 1

            try:
                write_fn(packet.image, packet.pts_ms)
            except Exception:
                logger.exception("SyncVideoWriter.flush_ready: write_fn error")
            self._written.append(packet)
            written_count += 1

        return written_count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _drain_heap_locked(self) -> List[FramePacket]:
        """Process all frames currently in the heap (must hold _lock).

        Returns frames in PTS order with gap-fill duplicates.
        """
        result: List[FramePacket] = []
        last_pts: Optional[float] = None

        while self._heap:
            if self._consumer_delay_ms > 0:
                time.sleep(self._consumer_delay_ms / 1000.0)

            packet = heapq.heappop(self._heap)

            # Enforce PTS monotonicity: skip out-of-order stragglers
            if last_pts is not None and packet.pts_ms < last_pts:
                logger.debug(
                    "SyncVideoWriter: skipped non-monotone packet "
                    "(pts=%.1f ms, last=%.1f ms)",
                    packet.pts_ms,
                    last_pts,
                )
                continue

            # Gap-fill: insert duplicate frames for large PTS gaps
            if last_pts is not None:
                gap_ms = packet.pts_ms - last_pts
                if gap_ms > 2.0 * self._frame_duration_ms and result:
                    num_dup = int(gap_ms / self._frame_duration_ms) - 1
                    prev = result[-1]
                    for d in range(num_dup):
                        dup_pts = last_pts + (d + 1) * self._frame_duration_ms
                        dup = FramePacket(
                            frame_index=prev.frame_index,
                            pts_ms=dup_pts,
                            audio_chunk_index=prev.audio_chunk_index,
                            image=prev.image,
                            audio_data=prev.audio_data,
                            pipeline_entry_ts=prev.pipeline_entry_ts,
                            pipeline_exit_ts=prev.pipeline_exit_ts,
                        )
                        result.append(dup)

            result.append(packet)
            last_pts = packet.pts_ms

        return result
