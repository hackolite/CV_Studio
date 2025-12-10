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
import tempfile

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
        
        # Create temporary file for worker output
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        self.output_path = self.temp_file.name
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'output_path') and os.path.exists(self.output_path):
            os.unlink(self.output_path)
    
    def test_default_queue_size(self):
        """Test default queue size (30 fps, 5 second chunks)"""
        worker = VideoBackgroundWorker(
            output_path=self.output_path,
            width=1280,
            height=720,
            fps=30.0,
            chunk_duration=5.0
        )
        
        # Expected: 30 fps * 5 seconds = 150 frames
        expected_size = 150
        actual_size = worker.queue_frames.get_max_size()
        
        self.assertEqual(actual_size, expected_size,
                        f"Queue size should be {expected_size} for 30fps, 5s chunks")
    
    def test_high_fps_queue_size(self):
        """Test queue size with high FPS (60 fps, 4 second chunks)"""
        worker = VideoBackgroundWorker(
            output_path=self.output_path,
            width=1280,
            height=720,
            fps=60.0,
            chunk_duration=4.0
        )
        
        # Expected: 60 fps * 4 seconds = 240 frames
        expected_size = 240
        actual_size = worker.queue_frames.get_max_size()
        
        self.assertEqual(actual_size, expected_size,
                        f"Queue size should be {expected_size} for 60fps, 4s chunks")
    
    def test_minimum_queue_size(self):
        """Test minimum queue size is enforced"""
        worker = VideoBackgroundWorker(
            output_path=self.output_path,
            width=1280,
            height=720,
            fps=30.0,
            chunk_duration=1.0  # Small chunk
        )
        
        # Expected: max(MIN_FRAME_QUEUE_SIZE, 30 * 1) = max(50, 30) = 50
        actual_size = worker.queue_frames.get_max_size()
        
        self.assertGreaterEqual(actual_size, VideoBackgroundWorker.MIN_FRAME_QUEUE_SIZE,
                               f"Queue size should be at least {VideoBackgroundWorker.MIN_FRAME_QUEUE_SIZE}")
        self.assertEqual(actual_size, VideoBackgroundWorker.MIN_FRAME_QUEUE_SIZE,
                        "For small chunks, queue should equal minimum")
    
    def test_maximum_queue_size(self):
        """Test maximum queue size is enforced"""
        worker = VideoBackgroundWorker(
            output_path=self.output_path,
            width=1280,
            height=720,
            fps=60.0,
            chunk_duration=10.0  # Large chunk
        )
        
        # Expected: min(MAX_FRAME_QUEUE_SIZE, 60 * 10) = min(300, 600) = 300
        actual_size = worker.queue_frames.get_max_size()
        
        self.assertLessEqual(actual_size, VideoBackgroundWorker.MAX_FRAME_QUEUE_SIZE,
                            f"Queue size should not exceed {VideoBackgroundWorker.MAX_FRAME_QUEUE_SIZE}")
        self.assertEqual(actual_size, VideoBackgroundWorker.MAX_FRAME_QUEUE_SIZE,
                        "For large chunks, queue should equal maximum")
    
    def test_backward_compatibility(self):
        """Test that chunk_duration is optional (uses default)"""
        # Create worker without chunk_duration parameter
        worker = VideoBackgroundWorker(
            output_path=self.output_path,
            width=1280,
            height=720,
            fps=30.0
        )
        
        # Should use DEFAULT_CHUNK_DURATION (5.0)
        actual_size = worker.queue_frames.get_max_size()
        
        # Verify it's reasonable for default chunk duration
        self.assertGreaterEqual(actual_size, VideoBackgroundWorker.MIN_FRAME_QUEUE_SIZE)
        self.assertLessEqual(actual_size, VideoBackgroundWorker.MAX_FRAME_QUEUE_SIZE)
        # For 30fps * 5s default, should be 150
        self.assertEqual(actual_size, 150, "Default should be 30fps * 5s = 150")
    
    def test_fractional_fps(self):
        """Test queue size with fractional FPS"""
        worker = VideoBackgroundWorker(
            output_path=self.output_path,
            width=1280,
            height=720,
            fps=29.97,  # Common NTSC frame rate
            chunk_duration=5.0
        )
        
        # Expected: int(29.97 * 5.0) = 149
        actual_size = worker.queue_frames.get_max_size()
        
        # Verify it's correctly calculated
        self.assertGreaterEqual(actual_size, int(29.97 * 5.0),
                               "Queue should handle fractional FPS")
        self.assertLessEqual(actual_size, int(29.97 * 5.0) + 1,
                            "Queue should be close to calculated value")
    
    def test_memory_limits(self):
        """Test that memory usage is reasonable"""
        # Test various common configurations
        test_cases = [
            (30, 5.0),   # Standard definition
            (60, 4.0),   # High frame rate, 4s chunks
            (25, 5.0),   # PAL
            (24, 5.0),   # Film
        ]
        
        for fps, chunk_duration in test_cases:
            with self.subTest(fps=fps, chunk_duration=chunk_duration):
                worker = VideoBackgroundWorker(
                    output_path=self.output_path,
                    width=1280,
                    height=720,
                    fps=fps,
                    chunk_duration=chunk_duration
                )
                
                actual_size = worker.queue_frames.get_max_size()
                
                # Verify it's within acceptable memory limits
                self.assertGreaterEqual(actual_size, VideoBackgroundWorker.MIN_FRAME_QUEUE_SIZE,
                                      f"Queue size should be at least minimum for {fps}fps, {chunk_duration}s")
                self.assertLessEqual(actual_size, VideoBackgroundWorker.MAX_FRAME_QUEUE_SIZE,
                                   f"Queue size should not exceed maximum for {fps}fps, {chunk_duration}s")
    
    def test_invalid_fps(self):
        """Test that invalid FPS raises ValueError"""
        with self.assertRaises(ValueError):
            VideoBackgroundWorker(
                output_path=self.output_path,
                width=1280,
                height=720,
                fps=0.0,  # Invalid
                chunk_duration=5.0
            )
        
        with self.assertRaises(ValueError):
            VideoBackgroundWorker(
                output_path=self.output_path,
                width=1280,
                height=720,
                fps=-30.0,  # Invalid
                chunk_duration=5.0
            )
    
    def test_invalid_chunk_duration(self):
        """Test that invalid chunk_duration raises ValueError"""
        with self.assertRaises(ValueError):
            VideoBackgroundWorker(
                output_path=self.output_path,
                width=1280,
                height=720,
                fps=30.0,
                chunk_duration=0.0  # Invalid
            )
        
        with self.assertRaises(ValueError):
            VideoBackgroundWorker(
                output_path=self.output_path,
                width=1280,
                height=720,
                fps=30.0,
                chunk_duration=-5.0  # Invalid
            )


if __name__ == '__main__':
    unittest.main()
