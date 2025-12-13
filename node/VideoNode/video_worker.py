#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Background Video Worker Module

This module implements a multi-threaded producer-consumer architecture for
video encoding and muxing that runs completely in the background, preventing
UI freezes.

Architecture:
- ProducerThread: Captures frames and audio from the pipeline
- VideoEncoderWorker: Encodes video frames using FFmpeg
- AudioEncoderWorker: Encodes audio with monotonic PTS tracking
- MuxerThread: Merges encoded packets and writes to file
- ProgressTracker: Tracks encoding progress and calculates ETA

The system uses bounded queues with backpressure policies that prioritize
audio quality over video completeness (can drop video frames if needed).
"""

import threading
import queue
import time
import traceback
import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, List
from enum import Enum

import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    import ffmpeg
    import soundfile as sf
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    sf = None
    logger.warning("FFmpeg or soundfile not available - video encoding features will be limited")


class WorkerState(Enum):
    """States for the video worker"""
    IDLE = "idle"
    STARTING = "starting"
    ENCODING = "encoding"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FLUSHING = "flushing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProgressEvent:
    """Progress event data structure"""
    state: WorkerState
    percent: float  # 0.0 to 100.0
    eta_seconds: Optional[float]
    frames_encoded: int
    total_frames: Optional[int]
    encoded_duration_s: float
    bytes_written: int
    encode_speed: float  # frames/sec or speed ratio
    message: str = ""


class ThreadSafeQueue:
    """
    Thread-safe queue wrapper with timeout and backpressure support.
    
    Supports:
    - Bounded capacity
    - Non-blocking push with timeout
    - Drop policy for backpressure
    """
    
    def __init__(self, max_size: int, name: str = "Queue"):
        self._queue = queue.Queue(maxsize=max_size)
        self._name = name
        self._dropped_count = 0
        self._lock = threading.Lock()
    
    def get_max_size(self) -> int:
        """Get the maximum size of the queue"""
        return self._queue.maxsize
    
    def push(self, item, timeout: float = 0.1, drop_on_full: bool = False) -> bool:
        """
        Push item to queue.
        
        Args:
            item: Item to push
            timeout: Timeout in seconds
            drop_on_full: If True, drop item instead of blocking when queue is full
            
        Returns:
            True if item was pushed, False if dropped or timeout
        """
        try:
            self._queue.put(item, block=True, timeout=timeout)
            return True
        except queue.Full:
            if drop_on_full:
                with self._lock:
                    self._dropped_count += 1
                logger.warning(f"[{self._name}] Queue full, dropped item (total dropped: {self._dropped_count})")
                return False
            else:
                logger.debug(f"[{self._name}] Queue full, timeout waiting to push")
                return False
    
    def pop(self, timeout: float = 0.1) -> Optional[Any]:
        """Pop item from queue with timeout"""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def size(self) -> int:
        """Get current queue size"""
        return self._queue.qsize()
    
    def get_dropped_count(self) -> int:
        """Get number of dropped items"""
        with self._lock:
            return self._dropped_count


class ProgressTracker:
    """
    Tracks encoding progress and calculates ETA.
    
    Uses a moving average over the last N seconds to smooth ETA calculations.
    """
    
    def __init__(self, total_frames: Optional[int] = None, sample_rate: int = 44100):
        self.total_frames = total_frames
        self.sample_rate = sample_rate
        
        # Progress counters
        self.frames_encoded = 0
        self.audio_samples_written = 0
        self.bytes_written = 0
        
        # Timing
        self.start_time = time.time()
        self.last_update_time = self.start_time
        
        # Moving average for speed calculation (last 5 seconds)
        self._speed_window = []
        self._speed_window_duration = 5.0  # seconds
        
        self._lock = threading.Lock()
    
    def update_frames(self, count: int = 1):
        """Update frames encoded count"""
        with self._lock:
            self.frames_encoded += count
    
    def update_audio_samples(self, count: int):
        """Update audio samples written count"""
        with self._lock:
            self.audio_samples_written += count
    
    def update_bytes(self, count: int):
        """Update bytes written count"""
        with self._lock:
            self.bytes_written += count
    
    def get_progress(self, state: WorkerState) -> ProgressEvent:
        """
        Get current progress event.
        
        Returns:
            ProgressEvent with current statistics
        """
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.start_time
            
            # Calculate percentage
            if self.total_frames and self.total_frames > 0:
                percent = (self.frames_encoded / self.total_frames) * 100.0
            else:
                # Use audio duration as fallback
                encoded_duration = self.audio_samples_written / self.sample_rate if self.sample_rate > 0 else 0
                # Can't calculate percentage without total, use 0
                percent = 0.0
            
            percent = min(100.0, max(0.0, percent))
            
            # Calculate speed (moving average)
            speed = 0.0
            if elapsed > 0:
                current_speed = self.frames_encoded / elapsed
                
                # Add to window
                self._speed_window.append((current_time, current_speed))
                
                # Remove old entries
                cutoff_time = current_time - self._speed_window_duration
                self._speed_window = [(t, s) for t, s in self._speed_window if t > cutoff_time]
                
                # Calculate average
                if self._speed_window:
                    speed = sum(s for _, s in self._speed_window) / len(self._speed_window)
            
            # Calculate ETA
            eta_seconds = None
            if self.total_frames and self.total_frames > 0 and speed > 0:
                remaining_frames = self.total_frames - self.frames_encoded
                eta_seconds = remaining_frames / speed
            
            # Encoded duration
            encoded_duration = self.audio_samples_written / self.sample_rate if self.sample_rate > 0 else 0.0
            
            return ProgressEvent(
                state=state,
                percent=percent,
                eta_seconds=eta_seconds,
                frames_encoded=self.frames_encoded,
                total_frames=self.total_frames,
                encoded_duration_s=encoded_duration,
                bytes_written=self.bytes_written,
                encode_speed=speed,
            )


class VideoBackgroundWorker:
    """
    Main background worker for video encoding and muxing.
    
    This class orchestrates multiple worker threads to encode and mux video/audio
    in the background without blocking the UI.
    
    Queue Sizing Strategy:
    - Frame queue size is calculated as: fps * chunk_duration
    - This ensures the queue can hold enough frames for synchronization with audio chunks
    - Maximum queue size is capped at 300 frames to limit memory usage
    - Minimum queue size is 50 frames for short recordings
    """
    
    # Queue size limits to prevent excessive memory usage
    MIN_FRAME_QUEUE_SIZE = 50    # Minimum queue size for short recordings
    MAX_FRAME_QUEUE_SIZE = 300   # Maximum to limit memory (10 seconds at 30 fps)
    DEFAULT_CHUNK_DURATION = 3.0 # Default audio chunk duration in seconds
    DEFAULT_AUDIO_QUEUE_SIZE = 4  # Default audio queue size (4 elements)
    # Audio queue size calculation for coherence with SyncQueue:
    # - SyncQueue max retention: 10s + 1s overhead = 11s
    # - Total audio duration: audio_queue_size × chunk_duration = 4 × 3.0 = 12s
    # - This ensures audio retention (12s) >= max SyncQueue retention (11s)
    # - Total image frames: audio_duration × fps = 12 × fps frames
    
    def __init__(
        self,
        output_path: str,
        width: int,
        height: int,
        fps: float,
        sample_rate: int = 44100,
        total_frames: Optional[int] = None,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
        chunk_duration: float = DEFAULT_CHUNK_DURATION,
    ):
        """
        Initialize background worker.
        
        Args:
            output_path: Path to output video file
            width: Video width in pixels
            height: Video height in pixels
            fps: Target frames per second (must be > 0)
            sample_rate: Audio sample rate
            total_frames: Total frames to encode (if known)
            progress_callback: Callback for progress updates
            chunk_duration: Audio chunk duration in seconds (must be > 0, default: 5.0)
            
        Raises:
            ValueError: If fps or chunk_duration is not positive
        """
        # Validate inputs
        if fps <= 0:
            raise ValueError(f"fps must be positive, got {fps}")
        if chunk_duration <= 0:
            raise ValueError(f"chunk_duration must be positive, got {chunk_duration}")
        
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.sample_rate = sample_rate
        self.total_frames = total_frames
        self.progress_callback = progress_callback
        self.chunk_duration = chunk_duration
        
        # State
        self._state = WorkerState.IDLE
        self._state_lock = threading.Lock()
        
        # Calculate optimal queue sizes based on FPS and chunk duration
        # Image queue size = fps * chunk_duration * audio_queue_size
        # This ensures the queue can hold enough frames for synchronization with audio chunks
        calculated_queue_size = int(fps * chunk_duration * self.DEFAULT_AUDIO_QUEUE_SIZE)
        frame_queue_size = max(
            self.MIN_FRAME_QUEUE_SIZE,
            min(calculated_queue_size, self.MAX_FRAME_QUEUE_SIZE)
        )
        
        logger.info(
            f"[VideoWorker] Queue sizing: fps={fps}, chunk_duration={chunk_duration}s, "
            f"audio_queue_size={self.DEFAULT_AUDIO_QUEUE_SIZE}, "
            f"calculated={calculated_queue_size}, actual={frame_queue_size} frames"
        )
        
        # Queues with dynamic sizing
        # Image/frame queue: fps * chunk_duration * audio_queue_size
        self.queue_frames = ThreadSafeQueue(frame_queue_size, "FrameQueue")
        # Video packet queue for encoded video data
        self.queue_video_packets = ThreadSafeQueue(200, "VideoPacketQueue")
        # Audio packet queue: DEFAULT_AUDIO_QUEUE_SIZE (4 elements)
        # Each element is an audio chunk of chunk_duration seconds, so total buffer = 4 * 3s = 12s
        # This ensures coherence with SyncQueue max retention (10s + 1s overhead = 11s)
        self.queue_audio_packets = ThreadSafeQueue(self.DEFAULT_AUDIO_QUEUE_SIZE, "AudioPacketQueue")
        
        # Progress tracking
        self.progress_tracker = ProgressTracker(total_frames, sample_rate)
        
        # Threads
        self._encoder_thread = None
        self._muxer_thread = None
        
        # Audio PTS tracking (monotonic across all segments)
        self.audio_samples_written_total = 0
        
        # Temporary files
        self._temp_video_path = None
        self._temp_audio_path = None
        
        # Cancel/pause flags
        self._cancel_flag = threading.Event()
        self._pause_flag = threading.Event()
        
        # Progress update timer
        self._last_progress_time = 0
        self._progress_update_interval = 0.3  # seconds
    
    def _set_state(self, state: WorkerState):
        """Thread-safe state update"""
        with self._state_lock:
            self._state = state
    
    def _get_state(self) -> WorkerState:
        """Thread-safe state getter"""
        with self._state_lock:
            return self._state
    
    def start(self):
        """Start the background encoding process"""
        if self._get_state() != WorkerState.IDLE:
            logger.warning(f"[VideoWorker] Cannot start, state is {self._get_state()}")
            return
        
        self._set_state(WorkerState.STARTING)
        
        # Create temporary paths
        base_dir = os.path.dirname(self.output_path)
        base_name = os.path.splitext(os.path.basename(self.output_path))[0]
        
        self._temp_video_path = os.path.join(base_dir, f"{base_name}_temp_video.mp4")
        self._temp_audio_path = os.path.join(base_dir, f"{base_name}_temp_audio.wav")
        
        # Start encoder thread (handles both video and audio encoding)
        self._encoder_thread = threading.Thread(
            target=self._encoder_worker,
            name="VideoEncoderWorker",
            daemon=True
        )
        self._encoder_thread.start()
        
        # Start muxer thread
        self._muxer_thread = threading.Thread(
            target=self._muxer_worker,
            name="VideoMuxerWorker",
            daemon=True
        )
        self._muxer_thread.start()
        
        self._set_state(WorkerState.ENCODING)
        logger.info(f"[VideoWorker] Started background encoding for {self.output_path}")
    
    def push_frame(self, frame: np.ndarray, audio_chunk: Optional[np.ndarray] = None) -> bool:
        """
        Push a video frame (and optional audio) to the encoding queue.
        
        Args:
            frame: Video frame as numpy array (H, W, C)
            audio_chunk: Optional audio data as numpy array
            
        Returns:
            True if pushed successfully, False if dropped
        """
        if self._get_state() not in [WorkerState.ENCODING, WorkerState.STARTING]:
            return False
        
        # Check if paused
        if self._pause_flag.is_set():
            # While paused, drop frames to avoid queue buildup
            return False
        
        # Check if cancelled
        if self._cancel_flag.is_set():
            return False
        
        # Push to queue with backpressure policy
        # Video frames can be dropped, but we log it
        success = self.queue_frames.push(
            {'frame': frame, 'audio': audio_chunk},
            timeout=0.1,
            drop_on_full=True  # Drop video frames if queue is full (backpressure)
        )
        
        return success
    
    def stop(self, wait: bool = True):
        """
        Stop encoding and finalize the video.
        
        Args:
            wait: If True, wait for encoding to complete
        """
        if self._get_state() in [WorkerState.IDLE, WorkerState.COMPLETED, WorkerState.ERROR]:
            return
        
        # Signal end of stream by pushing None
        self.queue_frames.push(None, timeout=1.0)
        
        if wait:
            self._wait_for_completion()
    
    def cancel(self):
        """Cancel the encoding process"""
        self._cancel_flag.set()
        self._set_state(WorkerState.CANCELLED)
        
        # Wait for threads to finish
        self._wait_for_completion(timeout=5.0)
    
    def pause(self):
        """Pause encoding (queues will stop accepting new frames)"""
        self._pause_flag.set()
        self._set_state(WorkerState.PAUSED)
    
    def resume(self):
        """Resume encoding"""
        self._pause_flag.clear()
        self._set_state(WorkerState.ENCODING)
    
    def _wait_for_completion(self, timeout: float = 30.0):
        """Wait for all worker threads to complete"""
        start_time = time.time()
        
        if self._encoder_thread and self._encoder_thread.is_alive():
            remaining = timeout - (time.time() - start_time)
            self._encoder_thread.join(timeout=max(0.1, remaining))
        
        if self._muxer_thread and self._muxer_thread.is_alive():
            remaining = timeout - (time.time() - start_time)
            self._muxer_thread.join(timeout=max(0.1, remaining))
    
    def _emit_progress(self, force: bool = False):
        """Emit progress event if enough time has passed"""
        current_time = time.time()
        
        if not force and (current_time - self._last_progress_time) < self._progress_update_interval:
            return
        
        self._last_progress_time = current_time
        
        if self.progress_callback:
            progress = self.progress_tracker.get_progress(self._get_state())
            try:
                self.progress_callback(progress)
            except Exception as e:
                logger.error(f"[VideoWorker] Error in progress callback: {e}")
    
    def _encoder_worker(self):
        """
        Main encoder worker thread.
        
        This thread:
        1. Pops frames/audio from queue
        2. Writes video frames to temporary video file
        3. Accumulates audio samples
        4. Updates progress
        """
        try:
            import cv2
            
            logger.info(f"[VideoWorker] Initializing encoder for {self.width}x{self.height} @ {self.fps} fps")
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                self._temp_video_path,
                fourcc,
                self.fps,
                (self.width, self.height)
            )
            
            if not video_writer.isOpened():
                logger.error(f"[VideoWorker] Failed to open video writer for {self._temp_video_path}")
                raise RuntimeError("Failed to open video writer")
            
            # Accumulate audio samples
            audio_samples = []
            
            logger.info(f"[VideoWorker] Encoder started")
            
            # Metrics for logging
            frames_processed = 0
            audio_chunks_processed = 0
            last_metric_log = time.time()
            metric_log_interval = 5.0  # Log metrics every 5 seconds
            
            while True:
                # Check for cancellation
                if self._cancel_flag.is_set():
                    logger.info(f"[VideoWorker] Encoder cancelled")
                    break
                
                # Check for pause
                while self._pause_flag.is_set() and not self._cancel_flag.is_set():
                    time.sleep(0.1)
                
                # Pop from queue
                item = self.queue_frames.pop(timeout=0.1)
                
                if item is None:
                    # End of stream
                    logger.info(f"[VideoWorker] End of stream signal received")
                    break
                
                if item:
                    frame = item['frame']
                    audio = item.get('audio')
                    
                    # Write video frame
                    if frame is not None:
                        video_writer.write(frame)
                        self.progress_tracker.update_frames(1)
                        frames_processed += 1
                    
                    # Accumulate audio
                    if audio is not None and len(audio) > 0:
                        audio_samples.append(audio)
                        self.progress_tracker.update_audio_samples(len(audio))
                        self.audio_samples_written_total += len(audio)
                        audio_chunks_processed += 1
                    
                    # Emit progress update
                    self._emit_progress()
                    
                    # Log metrics periodically
                    current_time = time.time()
                    if current_time - last_metric_log >= metric_log_interval:
                        queue_size = self.queue_frames.size()
                        dropped = self.queue_frames.get_dropped_count()
                        logger.info(
                            f"[VideoWorker] Metrics - Frames: {frames_processed}, "
                            f"Audio chunks: {audio_chunks_processed}, "
                            f"Queue size: {queue_size}, Dropped: {dropped}"
                        )
                        last_metric_log = current_time
            
            # Flush and release video writer
            video_writer.release()
            logger.info(f"[VideoWorker] Video encoding complete, {self.progress_tracker.frames_encoded} frames")
            
            # Write audio file if we have samples
            if audio_samples and FFMPEG_AVAILABLE and sf is not None and not self._cancel_flag.is_set():
                logger.info(f"[VideoWorker] Writing audio file with {len(audio_samples)} chunks")
                full_audio = np.concatenate(audio_samples)
                sf.write(self._temp_audio_path, full_audio, self.sample_rate)
                logger.info(f"[VideoWorker] Audio file written: {self._temp_audio_path}")
            
            # Signal muxer that encoding is done (only if not cancelled)
            if not self._cancel_flag.is_set():
                self._set_state(WorkerState.FLUSHING)
            
        except Exception as e:
            logger.error(f"[VideoWorker] Error in encoder thread: {e}")
            logger.error(traceback.format_exc())
            if not self._cancel_flag.is_set():
                self._set_state(WorkerState.ERROR)
    
    def _muxer_worker(self):
        """
        Muxer worker thread.
        
        This thread:
        1. Waits for encoder to finish
        2. Merges video and audio using ffmpeg
        3. Writes final output file
        4. Cleans up temporary files
        """
        try:
            logger.info(f"[VideoWorker] Muxer thread started")
            
            # Wait for encoder to finish
            while self._get_state() not in [WorkerState.FLUSHING, WorkerState.ERROR, WorkerState.CANCELLED]:
                time.sleep(0.1)
            
            if self._get_state() in [WorkerState.ERROR, WorkerState.CANCELLED]:
                logger.info(f"[VideoWorker] Muxer exiting due to state: {self._get_state()}")
                return
            
            logger.info(f"[VideoWorker] Muxer starting merge process")
            
            # Wait for video file to exist
            timeout = 5.0
            elapsed = 0
            while not os.path.exists(self._temp_video_path) and elapsed < timeout:
                time.sleep(0.1)
                elapsed += 0.1
            
            if not os.path.exists(self._temp_video_path):
                logger.error(f"[VideoWorker] Temporary video file not found: {self._temp_video_path}")
                raise FileNotFoundError(f"Temporary video file not found: {self._temp_video_path}")
            
            # Check if we have audio
            has_audio = os.path.exists(self._temp_audio_path)
            
            if has_audio and FFMPEG_AVAILABLE:
                logger.info(f"[VideoWorker] Merging video and audio with ffmpeg")
                
                # Use ffmpeg to merge
                video_input = ffmpeg.input(self._temp_video_path)
                audio_input = ffmpeg.input(self._temp_audio_path)
                
                output = ffmpeg.output(
                    video_input,
                    audio_input,
                    self.output_path,
                    vcodec='copy',
                    acodec='aac',
                    loglevel='error'
                )
                
                output = ffmpeg.overwrite_output(output)
                
                # Run ffmpeg and capture output
                start_time = time.time()
                stdout, stderr = ffmpeg.run(output, capture_stdout=True, capture_stderr=True)
                merge_time = time.time() - start_time
                
                logger.info(f"[VideoWorker] Merge complete in {merge_time:.2f}s: {self.output_path}")
                
                if stderr:
                    logger.debug(f"[VideoWorker] FFmpeg stderr: {stderr.decode('utf-8', errors='ignore')}")
                
                # Get file size for logging
                file_size = os.path.getsize(self.output_path)
                logger.info(f"[VideoWorker] Output file size: {file_size / (1024*1024):.2f} MB")
                
                # Clean up temp files
                if os.path.exists(self._temp_video_path):
                    os.remove(self._temp_video_path)
                    logger.debug(f"[VideoWorker] Removed temp video: {self._temp_video_path}")
                if os.path.exists(self._temp_audio_path):
                    os.remove(self._temp_audio_path)
                    logger.debug(f"[VideoWorker] Removed temp audio: {self._temp_audio_path}")
                
            else:
                # No audio or ffmpeg not available, just rename video file
                logger.info(f"[VideoWorker] No audio merge needed, moving video file")
                if os.path.exists(self._temp_video_path):
                    os.rename(self._temp_video_path, self.output_path)
                    file_size = os.path.getsize(self.output_path)
                    logger.info(f"[VideoWorker] Video file size: {file_size / (1024*1024):.2f} MB")
            
            # Update final progress
            self._set_state(WorkerState.COMPLETED)
            self._emit_progress(force=True)
            
            logger.info(f"[VideoWorker] Encoding completed successfully")
            
        except Exception as e:
            logger.error(f"[VideoWorker] Error in muxer thread: {e}")
            logger.error(traceback.format_exc())
            self._set_state(WorkerState.ERROR)
    
    def get_state(self) -> WorkerState:
        """Get current worker state"""
        return self._get_state()
    
    def is_active(self) -> bool:
        """Check if worker is actively encoding"""
        state = self._get_state()
        return state in [WorkerState.STARTING, WorkerState.ENCODING, WorkerState.PAUSED, WorkerState.FLUSHING]
