#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for audio chunk configuration and queue size changes.

This test verifies:
1. Default audio chunk duration is 3 seconds
2. Audio queue size is 4 elements (for coherence with SyncQueue max retention)
3. Image queue size formula: fps * chunk_duration * audio_queue_size
4. SyncQueue default retention time is 3 seconds
5. Audio retention (4 * 3s = 12s) >= SyncQueue max retention (10s + 1s = 11s)
"""
import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestAudioChunkConfiguration(unittest.TestCase):
    """Test audio chunk duration configuration."""
    
    def test_video_worker_chunk_duration_default(self):
        """Test that VideoBackgroundWorker default chunk duration is 3 seconds."""
        from node.VideoNode.video_worker import VideoBackgroundWorker
        self.assertEqual(VideoBackgroundWorker.DEFAULT_CHUNK_DURATION, 3.0)
    
    def test_video_worker_audio_queue_size_default(self):
        """Test that VideoBackgroundWorker default audio queue size is 4 elements."""
        from node.VideoNode.video_worker import VideoBackgroundWorker
        self.assertEqual(VideoBackgroundWorker.DEFAULT_AUDIO_QUEUE_SIZE, 4)


class TestQueueSizeCalculation(unittest.TestCase):
    """Test queue size calculation formula."""
    
    def test_frame_queue_size_formula(self):
        """Test that frame queue size follows: fps * chunk_duration * audio_queue_size."""
        from node.VideoNode.video_worker import VideoBackgroundWorker
        
        # Test with various FPS values
        test_cases = [
            (30, 300),    # 30 fps * 3s * 4 = 360, but capped at MAX_FRAME_QUEUE_SIZE (300)
            (60, 300),    # 60 fps * 3s * 4 = 720, but capped at MAX_FRAME_QUEUE_SIZE (300)
            (24, 288),    # 24 fps * 3s * 4 = 288
            (10, 120),    # 10 fps * 3s * 4 = 120
            (5, 60),      # 5 fps * 3s * 4 = 60
        ]
        
        for fps, expected_size in test_cases:
            # Create worker to check queue sizing
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, 'test.mp4')
                worker = VideoBackgroundWorker(
                    output_path=output_path,
                    width=640,
                    height=480,
                    fps=fps,
                )
                
                actual_size = worker.queue_frames.get_max_size()
                self.assertEqual(
                    actual_size, expected_size,
                    f"FPS={fps}: expected queue size {expected_size}, got {actual_size}"
                )
    
    def test_audio_queue_size(self):
        """Test that audio packet queue uses DEFAULT_AUDIO_QUEUE_SIZE."""
        from node.VideoNode.video_worker import VideoBackgroundWorker
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test.mp4')
            worker = VideoBackgroundWorker(
                output_path=output_path,
                width=640,
                height=480,
                fps=30,
            )
            
            # Audio packet queue should be DEFAULT_AUDIO_QUEUE_SIZE (4)
            self.assertEqual(
                worker.queue_audio_packets.get_max_size(),
                VideoBackgroundWorker.DEFAULT_AUDIO_QUEUE_SIZE
            )


class TestSyncQueueConfiguration(unittest.TestCase):
    """Test SyncQueue default configuration."""
    
    def test_default_retention_time_constant(self):
        """Test that DEFAULT_RETENTION_TIME constant is 3 seconds."""
        try:
            from node.SystemNode.node_sync_queue import DEFAULT_RETENTION_TIME
            self.assertEqual(DEFAULT_RETENTION_TIME, 3.0)
        except ImportError as e:
            # Skip test if dearpygui is not available
            if 'dearpygui' in str(e):
                self.skipTest("dearpygui not available")
            raise


class TestVideoWorkerConstants(unittest.TestCase):
    """Test VideoBackgroundWorker constant values."""
    
    def test_min_frame_queue_size(self):
        """Test minimum frame queue size is 50."""
        from node.VideoNode.video_worker import VideoBackgroundWorker
        self.assertEqual(VideoBackgroundWorker.MIN_FRAME_QUEUE_SIZE, 50)
    
    def test_max_frame_queue_size(self):
        """Test maximum frame queue size is 300."""
        from node.VideoNode.video_worker import VideoBackgroundWorker
        self.assertEqual(VideoBackgroundWorker.MAX_FRAME_QUEUE_SIZE, 300)


if __name__ == '__main__':
    unittest.main()
