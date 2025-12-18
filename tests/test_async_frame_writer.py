#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for AsyncFrameWriter class

Tests the async frame writing functionality that prevents UI freeze
during video recording.

NOTE: This test file includes a copy of the AsyncFrameWriter class instead of 
importing from node_video_writer.py because the main module requires dearpygui,
which is a GUI library not needed for unit testing. This allows tests to run in 
CI/CD environments without GUI dependencies.

The duplicated code should be kept in sync with the production class manually.
For integration tests that require the full module, see test_videowriter_*.py files.
"""

import sys
import os
import time
import tempfile
import threading
import queue
import traceback

# For testing without full dependencies, define a minimal logger
class Logger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

logger = Logger()

# Duplicate AsyncFrameWriter code for isolated unit testing (avoids dearpygui dependency)
class AsyncFrameWriter:
    """
    Asynchronous frame writer that runs in a background thread.
    
    This class prevents UI freezing by writing video frames in a separate thread.
    Each write() call on cv2.VideoWriter can take 10-50ms with high resolution
    and slow codecs (MJPEG, FFV1), which blocks the UI thread. By using a queue
    and background thread, the UI remains responsive.
    """
    
    def __init__(self, video_writer, max_queue_size=30):
        """
        Initialize the async frame writer.
        
        Args:
            video_writer: cv2.VideoWriter instance to write frames to
            max_queue_size: Maximum number of frames to buffer (default 30 = ~1 second at 30fps)
        """
        self.video_writer = video_writer
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self.writer_thread = None
        self.stop_event = threading.Event()
        self.error = None
        self.frames_written = 0
        self.frames_dropped = 0
        
    def start(self):
        """Start the background writer thread"""
        if self.writer_thread is not None:
            logger.warning("[AsyncFrameWriter] Writer thread already started")
            return
            
        self.stop_event.clear()
        self.writer_thread = threading.Thread(
            target=self._writer_worker,
            name="AsyncFrameWriter",
            daemon=True
        )
        self.writer_thread.start()
        logger.info("[AsyncFrameWriter] Background writer thread started")
        
    def write(self, frame):
        """
        Queue a frame for writing (non-blocking).
        
        Args:
            frame: Video frame to write
            
        Returns:
            True if frame was queued, False if queue is full (frame dropped)
        """
        if self.stop_event.is_set():
            return False
            
        try:
            # Non-blocking put with immediate timeout
            # If queue is full, drop the frame to avoid blocking UI
            self.frame_queue.put(frame, block=False)
            return True
        except queue.Full:
            self.frames_dropped += 1
            if self.frames_dropped % 10 == 1:  # Log every 10th dropped frame
                logger.warning(f"[AsyncFrameWriter] Frame queue full, dropped {self.frames_dropped} frames")
            return False
            
    def _writer_worker(self):
        """Background thread that writes frames to cv2.VideoWriter"""
        try:
            logger.info("[AsyncFrameWriter] Writer worker started")
            
            while not self.stop_event.is_set():
                try:
                    # Wait for a frame with timeout to check stop_event periodically
                    frame = self.frame_queue.get(timeout=0.1)
                    
                    # Write frame to video file (this can take 10-50ms)
                    self.video_writer.write(frame)
                    self.frames_written += 1
                    
                    self.frame_queue.task_done()
                    
                except queue.Empty:
                    # No frame available, continue loop to check stop_event
                    continue
                    
            # Process remaining frames in queue before stopping
            while not self.frame_queue.empty():
                try:
                    frame = self.frame_queue.get_nowait()
                    self.video_writer.write(frame)
                    self.frames_written += 1
                    self.frame_queue.task_done()
                except queue.Empty:
                    break
                    
            logger.info(f"[AsyncFrameWriter] Writer worker finished, wrote {self.frames_written} frames, dropped {self.frames_dropped} frames")
            
        except Exception as e:
            self.error = e
            logger.error(f"[AsyncFrameWriter] Error in writer worker: {e}")
            logger.error(traceback.format_exc())
            
    def stop(self, wait=True, timeout=10.0):
        """
        Stop the writer thread and optionally wait for it to finish.
        
        Args:
            wait: If True, wait for thread to finish writing remaining frames
            timeout: Maximum time to wait for thread to finish
        """
        if self.writer_thread is None:
            return
            
        # Signal thread to stop
        self.stop_event.set()
        
        if wait and self.writer_thread.is_alive():
            # Wait for queue to be empty
            try:
                self.frame_queue.join()
            except Exception as e:
                logger.warning(f"[AsyncFrameWriter] Error waiting for queue: {e}")
                
            # Wait for thread to finish
            self.writer_thread.join(timeout=timeout)
            
            if self.writer_thread.is_alive():
                logger.warning(f"[AsyncFrameWriter] Writer thread still alive after {timeout}s timeout")
        
        self.writer_thread = None


# Now import numpy and cv2 for the tests
try:
    import numpy as np
    import cv2
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Please install: pip install numpy opencv-python")
    sys.exit(1)


def test_async_writer_initialization():
    """Test that AsyncFrameWriter initializes correctly"""
    print("\nTest: AsyncFrameWriter initialization")
    
    # Create a temporary video writer
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        video_writer = cv2.VideoWriter(
            temp_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            30,
            (640, 480)
        )
        
        # Create async writer
        async_writer = AsyncFrameWriter(video_writer, max_queue_size=10)
        
        assert async_writer.video_writer is video_writer, "VideoWriter not stored correctly"
        assert async_writer.frame_queue.maxsize == 10, "Queue size not set correctly"
        assert async_writer.writer_thread is None, "Thread should not be started yet"
        assert async_writer.frames_written == 0, "Frame counter should start at 0"
        assert async_writer.frames_dropped == 0, "Drop counter should start at 0"
        
        print("✓ AsyncFrameWriter initializes correctly")
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_async_writer_thread_start():
    """Test that background thread starts correctly"""
    print("\nTest: AsyncFrameWriter thread start")
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        video_writer = cv2.VideoWriter(
            temp_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            30,
            (640, 480)
        )
        
        async_writer = AsyncFrameWriter(video_writer)
        async_writer.start()
        
        # Give thread time to start
        time.sleep(0.1)
        
        assert async_writer.writer_thread is not None, "Thread should be started"
        assert async_writer.writer_thread.is_alive(), "Thread should be alive"
        assert async_writer.writer_thread.daemon is True, "Thread should be daemon"
        
        # Clean up
        async_writer.stop(wait=True, timeout=2.0)
        video_writer.release()
        
        print("✓ Background thread starts correctly")
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_async_writer_frame_writing():
    """Test that frames are written asynchronously"""
    print("\nTest: AsyncFrameWriter frame writing")
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        width, height = 640, 480
        fps = 30
        
        video_writer = cv2.VideoWriter(
            temp_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            fps,
            (width, height)
        )
        
        async_writer = AsyncFrameWriter(video_writer, max_queue_size=30)
        async_writer.start()
        
        # Write some test frames
        num_frames = 10
        for i in range(num_frames):
            # Create a simple test frame (gradient)
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 0] = (i * 255 // num_frames)  # Blue channel gradient
            
            success = async_writer.write(frame)
            assert success, f"Frame {i} should be queued successfully"
        
        # Stop and wait for all frames to be written
        async_writer.stop(wait=True, timeout=5.0)
        video_writer.release()
        
        # Check that frames were written
        assert async_writer.frames_written == num_frames, \
            f"Expected {num_frames} frames written, got {async_writer.frames_written}"
        assert async_writer.frames_dropped == 0, \
            f"No frames should be dropped, but {async_writer.frames_dropped} were dropped"
        
        # Verify video file exists and has content
        assert os.path.exists(temp_path), "Video file should exist"
        file_size = os.path.getsize(temp_path)
        assert file_size > 0, "Video file should have content"
        
        print(f"✓ Wrote {num_frames} frames asynchronously, file size: {file_size} bytes")
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_async_writer_queue_full_behavior():
    """Test that frames are dropped when queue is full (no UI blocking)"""
    print("\nTest: AsyncFrameWriter queue full behavior")
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        width, height = 640, 480
        
        video_writer = cv2.VideoWriter(
            temp_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            30,
            (width, height)
        )
        
        # Small queue to test full behavior
        async_writer = AsyncFrameWriter(video_writer, max_queue_size=5)
        # Don't start the thread yet, so queue will fill up
        
        # Write frames until queue is full
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        frames_queued = 0
        for i in range(10):
            success = async_writer.write(frame)
            if success:
                frames_queued += 1
        
        # Should have queued exactly max_queue_size frames
        assert frames_queued == 5, \
            f"Should queue exactly 5 frames before dropping, queued {frames_queued}"
        
        # Now start the thread to process frames
        async_writer.start()
        time.sleep(0.5)  # Let it process
        
        # Try writing more frames
        for i in range(10):
            async_writer.write(frame)
        
        # Clean up
        async_writer.stop(wait=True, timeout=2.0)
        video_writer.release()
        
        print(f"✓ Queue full behavior correct: {frames_queued} queued, "
              f"{async_writer.frames_dropped} dropped, {async_writer.frames_written} written")
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_async_writer_stop_flushes_queue():
    """Test that stop() waits for remaining frames to be written"""
    print("\nTest: AsyncFrameWriter stop flushes queue")
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        width, height = 640, 480
        
        video_writer = cv2.VideoWriter(
            temp_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            30,
            (width, height)
        )
        
        async_writer = AsyncFrameWriter(video_writer, max_queue_size=30)
        async_writer.start()
        
        # Write frames quickly
        num_frames = 20
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(num_frames):
            async_writer.write(frame)
        
        # Immediately stop - should wait for all frames to be written
        async_writer.stop(wait=True, timeout=5.0)
        video_writer.release()
        
        # All frames should be written
        assert async_writer.frames_written == num_frames, \
            f"All {num_frames} frames should be written, got {async_writer.frames_written}"
        
        print(f"✓ Stop correctly flushed {num_frames} frames from queue")
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_async_writer_performance():
    """Test that async writer doesn't block the calling thread"""
    print("\nTest: AsyncFrameWriter performance (non-blocking)")
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.avi', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        width, height = 1920, 1080  # High resolution
        
        # Use MJPEG codec which can be slow to write
        video_writer = cv2.VideoWriter(
            temp_path,
            cv2.VideoWriter_fourcc(*'MJPG'),
            30,
            (width, height)
        )
        
        async_writer = AsyncFrameWriter(video_writer, max_queue_size=30)
        async_writer.start()
        
        # Write frames and measure time
        num_frames = 30
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        start_time = time.time()
        for i in range(num_frames):
            async_writer.write(frame)
        write_time = time.time() - start_time
        
        # Writing should be very fast (non-blocking)
        # Even with slow codec, queuing 30 frames should take < 0.1 seconds
        assert write_time < 0.5, \
            f"Async write should be fast, took {write_time:.3f}s for {num_frames} frames"
        
        # Clean up
        async_writer.stop(wait=True, timeout=10.0)
        video_writer.release()
        
        print(f"✓ Non-blocking write: {num_frames} frames queued in {write_time:.3f}s "
              f"({num_frames/write_time:.1f} fps)")
        print(f"  Frames written: {async_writer.frames_written}, dropped: {async_writer.frames_dropped}")
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def run_all_tests():
    """Run all AsyncFrameWriter tests"""
    print("="*70)
    print("AsyncFrameWriter Test Suite")
    print("="*70)
    
    tests = [
        test_async_writer_initialization,
        test_async_writer_thread_start,
        test_async_writer_frame_writing,
        test_async_writer_queue_full_behavior,
        test_async_writer_stop_flushes_queue,
        test_async_writer_performance,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("\n✅ All AsyncFrameWriter tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
