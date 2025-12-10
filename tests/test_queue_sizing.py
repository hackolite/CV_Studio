#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for Queue Sizing based on FPS and Chunk Duration

This test verifies that the VideoBackgroundWorker correctly sizes its
frame queue based on FPS and chunk duration to prevent memory issues
and ensure proper audio/video synchronization.
"""

import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the worker module
try:
    from node.VideoNode.video_worker import VideoBackgroundWorker
    WORKER_AVAILABLE = True
except ImportError as e:
    WORKER_AVAILABLE = False
    print(f"Warning: video_worker module not available: {e}")


class TestQueueSizing(unittest.TestCase):
    """Test queue sizing calculations"""
    
    def setUp(self):
        """Set up test fixtures"""
        if not WORKER_AVAILABLE:
            self.skipTest("video_worker module not available")
    
    def test_default_queue_size(self):
        """Test default queue size (30 fps, 5 second chunks)"""
        worker = VideoBackgroundWorker(
            output_path='/tmp/test.mp4',
            width=1280,
            height=720,
            fps=30.0,
            chunk_duration=5.0
        )
        
        # Expected: 30 fps * 5 seconds = 150 frames
        expected_size = 150
        actual_size = worker.queue_frames._queue.maxsize
        
        self.assertEqual(actual_size, expected_size,
                        f"Queue size should be {expected_size} for 30fps, 5s chunks")
    
    def test_high_fps_queue_size(self):
        """Test queue size with high FPS (60 fps, 4 second chunks)"""
        worker = VideoBackgroundWorker(
            output_path='/tmp/test.mp4',
            width=1280,
            height=720,
            fps=60.0,
            chunk_duration=4.0
        )
        
        # Expected: 60 fps * 4 seconds = 240 frames
        expected_size = 240
        actual_size = worker.queue_frames._queue.maxsize
        
        self.assertEqual(actual_size, expected_size,
                        f"Queue size should be {expected_size} for 60fps, 4s chunks")
    
    def test_minimum_queue_size(self):
        """Test minimum queue size is enforced"""
        worker = VideoBackgroundWorker(
            output_path='/tmp/test.mp4',
            width=1280,
            height=720,
            fps=30.0,
            chunk_duration=1.0  # Small chunk
        )
        
        # Expected: max(MIN_FRAME_QUEUE_SIZE, 30 * 1) = max(50, 30) = 50
        expected_size = VideoBackgroundWorker.MIN_FRAME_QUEUE_SIZE
        actual_size = worker.queue_frames._queue.maxsize
        
        self.assertEqual(actual_size, expected_size,
                        f"Queue size should be at least {expected_size} (minimum)")
    
    def test_maximum_queue_size(self):
        """Test maximum queue size is enforced"""
        worker = VideoBackgroundWorker(
            output_path='/tmp/test.mp4',
            width=1280,
            height=720,
            fps=60.0,
            chunk_duration=10.0  # Large chunk
        )
        
        # Expected: min(MAX_FRAME_QUEUE_SIZE, 60 * 10) = min(300, 600) = 300
        expected_size = VideoBackgroundWorker.MAX_FRAME_QUEUE_SIZE
        actual_size = worker.queue_frames._queue.maxsize
        
        self.assertEqual(actual_size, expected_size,
                        f"Queue size should be capped at {expected_size} (maximum)")
    
    def test_backward_compatibility(self):
        """Test that chunk_duration is optional (uses default)"""
        # Create worker without chunk_duration parameter
        worker = VideoBackgroundWorker(
            output_path='/tmp/test.mp4',
            width=1280,
            height=720,
            fps=30.0
        )
        
        # Should use DEFAULT_CHUNK_DURATION (5.0)
        expected_size = int(30.0 * VideoBackgroundWorker.DEFAULT_CHUNK_DURATION)
        actual_size = worker.queue_frames._queue.maxsize
        
        self.assertEqual(actual_size, expected_size,
                        f"Queue size should use default chunk duration")
    
    def test_fractional_fps(self):
        """Test queue size with fractional FPS"""
        worker = VideoBackgroundWorker(
            output_path='/tmp/test.mp4',
            width=1280,
            height=720,
            fps=29.97,  # Common NTSC frame rate
            chunk_duration=5.0
        )
        
        # Expected: int(29.97 * 5.0) = 149
        expected_size = 149
        actual_size = worker.queue_frames._queue.maxsize
        
        self.assertEqual(actual_size, expected_size,
                        f"Queue size should handle fractional FPS correctly")
    
    def test_memory_limits(self):
        """Test that memory usage is reasonable"""
        # Test various common configurations
        test_cases = [
            (30, 5.0, 150),   # Standard definition
            (60, 4.0, 240),   # High frame rate, 4s chunks
            (25, 5.0, 125),   # PAL
            (24, 5.0, 120),   # Film
        ]
        
        for fps, chunk_duration, expected_size in test_cases:
            worker = VideoBackgroundWorker(
                output_path='/tmp/test.mp4',
                width=1280,
                height=720,
                fps=fps,
                chunk_duration=chunk_duration
            )
            
            actual_size = worker.queue_frames._queue.maxsize
            
            # Verify expected size
            self.assertEqual(actual_size, expected_size,
                            f"Queue size for {fps}fps, {chunk_duration}s should be {expected_size}")
            
            # Verify it's within acceptable memory limits (< MAX_FRAME_QUEUE_SIZE)
            self.assertLessEqual(actual_size, VideoBackgroundWorker.MAX_FRAME_QUEUE_SIZE,
                               f"Queue size should not exceed maximum")


if __name__ == '__main__':
    unittest.main()
