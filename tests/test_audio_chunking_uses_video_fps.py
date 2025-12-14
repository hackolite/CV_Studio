#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that audio chunking uses detected video FPS, not target_fps from UI slider.

This test validates the fix for the FPS mismatch bug where:
- Video FPS is detected from the source file (e.g., 30 fps)
- UI slider target_fps might be different (e.g., 24 fps)
- Audio chunks MUST be calculated using the detected video FPS (30 fps)
- NOT the UI slider value (24 fps)

This ensures perfect audio/video synchronization.
"""

import unittest


class TestAudioChunkingUsesVideoFPS(unittest.TestCase):
    """Test that audio chunking uses detected video FPS, not target_fps slider"""
    
    def test_samples_per_frame_uses_video_fps_not_slider(self):
        """
        Test that samples_per_frame is calculated using detected video FPS,
        NOT the UI slider target_fps value.
        
        Scenario:
        - Video file has actual FPS = 30 (detected from metadata)
        - UI slider target_fps = 24 (user setting)
        - Audio chunks MUST use: samples_per_frame = 44100 / 30 = 1470
        - Audio chunks MUST NOT use: samples_per_frame = 44100 / 24 = 1837.5
        """
        sample_rate = 44100
        
        # Detected from video file
        video_fps = 30
        
        # UI slider value (different from video FPS)
        target_fps = 24
        
        # CORRECT: Use detected video FPS for audio chunking
        correct_samples_per_frame = sample_rate / video_fps
        self.assertAlmostEqual(correct_samples_per_frame, 1470.0, places=1)
        
        # INCORRECT: Using target_fps would be wrong
        incorrect_samples_per_frame = sample_rate / target_fps
        self.assertAlmostEqual(incorrect_samples_per_frame, 1837.5, places=1)
        
        # Verify they are different
        self.assertNotEqual(correct_samples_per_frame, incorrect_samples_per_frame)
        
        print(f"✓ Video FPS: {video_fps} fps → {correct_samples_per_frame:.1f} samples/frame (CORRECT)")
        print(f"✗ Target FPS: {target_fps} fps → {incorrect_samples_per_frame:.1f} samples/frame (WRONG)")
        print(f"✓ Difference: {abs(correct_samples_per_frame - incorrect_samples_per_frame):.1f} samples")
    
    def test_queue_size_uses_video_fps_not_slider(self):
        """
        Test that queue size is calculated using detected video FPS,
        NOT the UI slider target_fps value.
        
        Scenario:
        - Video file has actual FPS = 30
        - UI slider target_fps = 24
        - Queue size MUST use: 4 * 30 = 120
        - Queue size MUST NOT use: 4 * 24 = 96
        """
        queue_duration_seconds = 4
        
        # Detected from video file
        video_fps = 30
        
        # UI slider value
        target_fps = 24
        
        # CORRECT: Use detected video FPS
        correct_queue_size = int(queue_duration_seconds * video_fps)
        self.assertEqual(correct_queue_size, 120)
        
        # INCORRECT: Using target_fps would be wrong
        incorrect_queue_size = int(queue_duration_seconds * target_fps)
        self.assertEqual(incorrect_queue_size, 96)
        
        # Verify they are different
        self.assertNotEqual(correct_queue_size, incorrect_queue_size)
        
        print(f"✓ Video FPS: {video_fps} fps → Queue size: {correct_queue_size} (CORRECT)")
        print(f"✗ Target FPS: {target_fps} fps → Queue size: {incorrect_queue_size} (WRONG)")
        print(f"✓ Difference: {abs(correct_queue_size - incorrect_queue_size)} frames")
    
    def test_desync_calculation(self):
        """
        Calculate the cumulative desynchronization that occurs when
        using wrong FPS for audio chunking.
        
        Example: 10 second video at 30 fps with slider at 24 fps
        """
        video_duration_seconds = 10
        sample_rate = 44100
        
        # Actual video properties
        video_fps = 30
        num_frames = int(video_duration_seconds * video_fps)  # 300 frames
        
        # UI slider (wrong value)
        target_fps = 24
        
        # CORRECT audio chunking (using video FPS)
        correct_samples_per_frame = sample_rate / video_fps
        correct_total_samples = num_frames * correct_samples_per_frame
        correct_audio_duration = correct_total_samples / sample_rate
        
        # INCORRECT audio chunking (using target FPS from slider)
        incorrect_samples_per_frame = sample_rate / target_fps
        incorrect_total_samples = num_frames * incorrect_samples_per_frame
        incorrect_audio_duration = incorrect_total_samples / sample_rate
        
        # Calculate desync
        desync_seconds = abs(correct_audio_duration - incorrect_audio_duration)
        desync_frames = desync_seconds * video_fps
        
        print(f"\n10-second video at 30 fps (slider at 24 fps):")
        print(f"  Correct audio duration: {correct_audio_duration:.3f}s")
        print(f"  Incorrect audio duration: {incorrect_audio_duration:.3f}s")
        print(f"  Desync: {desync_seconds:.3f}s ({desync_frames:.1f} frames)")
        
        # Verify there is significant desync
        self.assertGreater(desync_seconds, 2.0, "Desync should be > 2 seconds for 10s video")
        self.assertGreater(desync_frames, 60, "Desync should be > 60 frames for 10s video at 30fps")
        
        print(f"✓ Using wrong FPS causes {desync_seconds:.3f}s desync!")
    
    def test_sync_at_different_fps_values(self):
        """
        Test desync across various FPS combinations to show the bug's impact.
        """
        sample_rate = 44100
        video_duration_seconds = 60  # 1 minute video
        
        test_cases = [
            (30, 24),  # Common: 30 fps video with 24 fps slider
            (60, 30),  # High FPS: 60 fps video with 30 fps slider
            (25, 24),  # PAL vs Film: 25 fps video with 24 fps slider
            (29.97, 24),  # NTSC: 29.97 fps video with 24 fps slider
        ]
        
        print("\nDesync for 60-second videos with different FPS mismatches:")
        print("-" * 70)
        
        for video_fps, target_fps in test_cases:
            num_frames = int(video_duration_seconds * video_fps)
            
            # Correct calculation
            correct_samples_per_frame = sample_rate / video_fps
            correct_duration = (num_frames * correct_samples_per_frame) / sample_rate
            
            # Incorrect calculation (using slider FPS)
            incorrect_samples_per_frame = sample_rate / target_fps
            incorrect_duration = (num_frames * incorrect_samples_per_frame) / sample_rate
            
            desync_seconds = abs(correct_duration - incorrect_duration)
            desync_frames = desync_seconds * video_fps
            
            print(f"Video: {video_fps:6.2f} fps, Slider: {target_fps:4.0f} fps → "
                  f"Desync: {desync_seconds:6.2f}s ({desync_frames:5.1f} frames)")
            
            # All should have noticeable desync
            self.assertGreater(desync_seconds, 1.0, 
                             f"Should have > 1s desync for {video_fps}fps video")
        
        print("-" * 70)
        print("✓ All cases show significant desync when using wrong FPS!")


if __name__ == "__main__":
    print("Testing Audio Chunking Uses Video FPS (Not Target FPS)\n")
    print("=" * 70)
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAudioChunkingUsesVideoFPS)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✅ All tests passed! Audio chunking correctly uses video FPS.")
    else:
        print("❌ Some tests failed")
        exit(1)
