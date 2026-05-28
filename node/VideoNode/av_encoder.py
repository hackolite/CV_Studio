#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyAV-backed video encoder for CV_Studio.

Provides :class:`PyAVEncoder` as a drop-in replacement for ``cv2.VideoWriter``
when explicit per-frame PTS control is needed.

If the ``av`` package is not installed the module still imports successfully but
:class:`PyAVEncoder` is *None*.  Callers should check::

    if PyAVEncoder is None:
        # fall back to cv2.VideoWriter

``av`` can be installed with::

    pip install av

Justification for replacing ``cv2.VideoWriter``
------------------------------------------------
* ``cv2.VideoWriter`` has no concept of explicit PTS: frame timing is entirely
  determined by the *order* in which ``write()`` is called, plus the fps
  parameter baked into the container header.  When frames arrive out of order
  (due to AI processing jitter) or are duplicated for gap-filling, there is no
  way to tell the container their correct presentation time.

* It has no native audio support, forcing a post-hoc re-mux through FFmpeg (the
  current ``_merge_audio_video_ffmpeg`` step) which introduces an extra I/O
  round-trip and loses precise A/V alignment.

* PyAV (libavcodec/libavformat Python bindings) supports explicit
  ``packet.pts`` / ``packet.dts`` per frame, stream-level timebases, and
  simultaneous audio+video in a single container without intermediate files.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional PyAV import
# ---------------------------------------------------------------------------
try:
    import av as _av  # type: ignore

    _AV_AVAILABLE = True
except ImportError:  # pragma: no cover
    _av = None  # type: ignore
    _AV_AVAILABLE = False
    logger.debug(
        "av package not installed; PyAVEncoder is unavailable. "
        "Install it with: pip install av"
    )


# ---------------------------------------------------------------------------
# Exceptions (defined before PyAVEncoder so they can be referenced in its body)
# ---------------------------------------------------------------------------


class SyncError(Exception):
    """Raised on PyAVEncoder lifecycle errors."""


# ---------------------------------------------------------------------------
# PyAVEncoder
# ---------------------------------------------------------------------------


class PyAVEncoder:
    """Write video (and optionally audio) with explicit per-frame PTS via PyAV.

    Parameters
    ----------
    output_path:
        Destination file path.  MKV or MP4 are recommended.
    fps:
        Target video frame-rate.
    frame_size:
        ``(width, height)`` of the video stream.
    codec:
        FFmpeg video codec name (e.g. ``'libx264'``, ``'h264_nvenc'``).
    pixel_format:
        Pixel format string (default ``'yuv420p'`` for H.264 compatibility).
    crf:
        Constant-Rate Factor for the video encoder (lower = better quality).
    audio_sample_rate:
        Sample rate for the audio stream in Hz (default: 44100).
    audio_channels:
        Number of audio channels (default: 2 stereo).
    audio_codec:
        FFmpeg audio codec name (default: ``'aac'``).
    """

    def __init__(
        self,
        output_path: str,
        fps: float,
        frame_size: Tuple[int, int],
        codec: str = "libx264",
        pixel_format: str = "yuv420p",
        crf: int = 23,
        audio_sample_rate: int = 44100,
        audio_channels: int = 2,
        audio_codec: str = "aac",
    ) -> None:
        if not _AV_AVAILABLE:
            raise RuntimeError(
                "PyAVEncoder requires the 'av' package. "
                "Install it with: pip install av"
            )

        self._fps = fps
        self._frame_size = frame_size  # (width, height)
        self._output_path = output_path

        # Timebase: 1 / (fps * 1000) gives ms-level precision
        # We use a rational timebase of 1/1000 (ms) for simplicity.
        self._timebase = _av.Rational(1, 1000)

        self._container = _av.open(output_path, mode="w")

        # Video stream
        self._video_stream = self._container.add_stream(codec, rate=int(fps))
        self._video_stream.width = frame_size[0]
        self._video_stream.height = frame_size[1]
        self._video_stream.pix_fmt = pixel_format
        self._video_stream.codec_context.time_base = self._timebase
        self._video_stream.options = {"crf": str(crf)}

        # Audio stream (optional; only written if audio packets are pushed)
        self._audio_stream = self._container.add_stream(audio_codec)
        self._audio_stream.codec_context.sample_rate = audio_sample_rate
        self._audio_stream.codec_context.channels = audio_channels
        self._audio_stream.codec_context.time_base = _av.Rational(
            1, audio_sample_rate
        )

        self._closed = False
        self._last_pts_ms: Optional[float] = None

        logger.info(
            "PyAVEncoder opened: %s (%dx%d @ %s fps, codec=%s)",
            output_path,
            frame_size[0],
            frame_size[1],
            fps,
            codec,
        )

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    def write_video_frame(
        self, image: np.ndarray, pts_ms: float
    ) -> None:
        """Encode one video frame with an explicit PTS.

        Parameters
        ----------
        image:
            BGR (or RGB) ``uint8`` NumPy array with shape ``(H, W, 3)``.
        pts_ms:
            Presentation timestamp in milliseconds.  Must be monotonically
            increasing.
        """
        if self._closed:
            raise SyncError("PyAVEncoder is already closed.")

        # OpenCV uses BGR; PyAV expects RGB
        rgb = image[:, :, ::-1] if image.ndim == 3 else image
        av_frame = _av.VideoFrame.from_ndarray(rgb, format="rgb24")

        # Assign PTS in the ms timebase (1/1000 s)
        av_frame.pts = int(round(pts_ms))
        av_frame.time_base = self._timebase

        for packet in self._video_stream.encode(av_frame):
            self._container.mux(packet)

        self._last_pts_ms = pts_ms

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def write_audio_chunk(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        pts_samples: int,
    ) -> None:
        """Encode one audio chunk with an explicit PTS.

        Parameters
        ----------
        audio_data:
            1-D or 2-D float32 or int16 NumPy array
            (shape ``(samples,)`` or ``(channels, samples)``).
        sample_rate:
            Sample rate in Hz.  Should match ``audio_sample_rate`` used at
            construction.
        pts_samples:
            PTS in *samples* (i.e. ``chunk_start_second * sample_rate``).
        """
        if self._closed:
            raise SyncError("PyAVEncoder is already closed.")

        if audio_data.ndim == 1:
            audio_data = audio_data[np.newaxis, :]  # (1, samples)

        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        av_frame = _av.AudioFrame.from_ndarray(
            audio_data, format="fltp", layout="mono" if audio_data.shape[0] == 1 else "stereo"
        )
        av_frame.sample_rate = sample_rate
        av_frame.pts = pts_samples
        av_frame.time_base = _av.Rational(1, sample_rate)

        for packet in self._audio_stream.encode(av_frame):
            self._container.mux(packet)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush buffered frames and close the container."""
        if self._closed:
            return

        # Flush video
        for packet in self._video_stream.encode(None):
            self._container.mux(packet)

        # Flush audio
        for packet in self._audio_stream.encode(None):
            self._container.mux(packet)

        self._container.close()
        self._closed = True
        logger.info("PyAVEncoder closed: %s", self._output_path)

    def __enter__(self) -> "PyAVEncoder":
        return self

    def __exit__(self, *args) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Module-level availability guard
# ---------------------------------------------------------------------------

if not _AV_AVAILABLE:
    PyAVEncoder = None  # type: ignore  # noqa: F811
