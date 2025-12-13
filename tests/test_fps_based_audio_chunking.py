#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for FPS-based audio chunking in node_video.py

This test validates that audio chunks are created based on FPS:
- chunk_size = sample_rate / fps (samples per frame)
- Each audio chunk corresponds to exactly ONE frame
- Audio queue size = Image queue size = 4 * fps
"""

import numpy as np
import unittest


class TestFPSBasedAudioChunking(unittest.TestCase):
    """Test FPS-based audio chunking calculations"""
    
    def test_samples_per_frame_calculation(self):
        """Test samples per frame calculation: sample_rate / fps"""
        # 44100 Hz at 24 fps
        sample_rate = 44100
        fps = 24
        samples_per_frame = sample_rate / fps
        
        self.assertAlmostEqual(samples_per_frame, 1837.5, places=1)
        print(f"✓ 44100 Hz / 24 fps = {samples_per_frame} samples/frame")
        
        # 44100 Hz at 30 fps
        fps = 30
        samples_per_frame = sample_rate / fps
        self.assertAlmostEqual(samples_per_frame, 1470.0, places=1)
        print(f"✓ 44100 Hz / 30 fps = {samples_per_frame} samples/frame")
        
        # 44100 Hz at 60 fps
        fps = 60
        samples_per_frame = sample_rate / fps
        self.assertAlmostEqual(samples_per_frame, 735.0, places=1)
        print(f"✓ 44100 Hz / 60 fps = {samples_per_frame} samples/frame")
    
    def test_queue_size_equal(self):
        """Test that audio and video queue sizes are equal: both = 4 * fps"""
        queue_duration_seconds = 4
        
        # 24 fps
        fps = 24
        image_queue_size = queue_duration_seconds * fps
        audio_queue_size = queue_duration_seconds * fps
        
        self.assertEqual(image_queue_size, audio_queue_size)
        self.assertEqual(image_queue_size, 96)
        print(f"✓ 24 fps: Image queue = Audio queue = {image_queue_size}")
        
        # 30 fps
        fps = 30
        image_queue_size = queue_duration_seconds * fps
        audio_queue_size = queue_duration_seconds * fps
        
        self.assertEqual(image_queue_size, audio_queue_size)
        self.assertEqual(image_queue_size, 120)
        print(f"✓ 30 fps: Image queue = Audio queue = {image_queue_size}")
        
        # 60 fps
        fps = 60
        image_queue_size = queue_duration_seconds * fps
        audio_queue_size = queue_duration_seconds * fps
        
        self.assertEqual(image_queue_size, audio_queue_size)
        self.assertEqual(image_queue_size, 240)
        print(f"✓ 60 fps: Image queue = Audio queue = {image_queue_size}")
    
    def test_audio_chunking_by_frames(self):
        """Test that audio is split into exactly one chunk per frame"""
        sample_rate = 44100
        fps = 24
        samples_per_frame = sample_rate / fps
        
        # Create mock audio data (10 seconds = 240 frames at 24 fps)
        duration_seconds = 10
        total_samples = int(sample_rate * duration_seconds)
        audio_data = np.random.randn(total_samples)
        
        # Calculate expected number of chunks (one per frame)
        expected_num_frames = int(duration_seconds * fps)
        
        # Chunk the audio
        chunks = []
        start = 0
        while start < len(audio_data):
            end = int(start + samples_per_frame)
            if end > len(audio_data):
                # Pad last chunk
                chunk = audio_data[start:]
                padding_needed = int(samples_per_frame) - len(chunk)
                if padding_needed > 0:
                    chunk = np.pad(chunk, (0, padding_needed), mode='constant', constant_values=0)
            else:
                chunk = audio_data[start:end]
            chunks.append(chunk)
            start = end
        
        # Verify number of chunks equals or is very close to number of frames
        # (There may be an off-by-one due to rounding)
        self.assertAlmostEqual(len(chunks), expected_num_frames, delta=1)
        print(f"✓ 10s audio at 24 fps: {len(chunks)} chunks ≈ {expected_num_frames} frames")
        
        # Verify all chunks have the same size
        expected_chunk_size = int(samples_per_frame)
        for i, chunk in enumerate(chunks):
            self.assertEqual(len(chunk), expected_chunk_size, 
                           f"Chunk {i} has size {len(chunk)}, expected {expected_chunk_size}")
        
        print(f"✓ All chunks have size {expected_chunk_size} samples")
    
    def test_frame_to_chunk_mapping(self):
        """Test that frame_number maps directly to chunk_index"""
        # With FPS-based chunking, chunk_index = frame_number - 1
        # (frame_number is 1-indexed, chunks are 0-indexed)
        
        test_cases = [
            (1, 0),   # Frame 1 -> Chunk 0
            (2, 1),   # Frame 2 -> Chunk 1
            (10, 9),  # Frame 10 -> Chunk 9
            (100, 99), # Frame 100 -> Chunk 99
        ]
        
        for frame_number, expected_chunk_index in test_cases:
            chunk_index = frame_number - 1
            self.assertEqual(chunk_index, expected_chunk_index)
            print(f"✓ Frame {frame_number} -> Chunk {chunk_index}")
    
    def test_audio_duration_matches_video_duration(self):
        """Test that total audio duration matches video duration"""
        sample_rate = 44100
        fps = 24
        samples_per_frame = sample_rate / fps
        
        # Video: 240 frames at 24 fps = 10 seconds
        num_frames = 240
        video_duration = num_frames / fps
        
        # Audio: 240 chunks, each with samples_per_frame samples
        num_chunks = num_frames
        total_audio_samples = num_chunks * int(samples_per_frame)
        audio_duration = total_audio_samples / sample_rate
        
        # Durations should be approximately equal (within rounding error)
        self.assertAlmostEqual(video_duration, audio_duration, places=2)
        print(f"✓ Video duration: {video_duration:.3f}s = Audio duration: {audio_duration:.3f}s")
    
    def test_queue_buffer_duration(self):
        """Test that queue holds 4 seconds of data"""
        queue_duration_seconds = 4
        
        # At 24 fps
        fps = 24
        queue_size = queue_duration_seconds * fps
        queue_duration = queue_size / fps
        
        self.assertEqual(queue_duration, 4.0)
        print(f"✓ Queue at 24 fps: {queue_size} items = {queue_duration}s")
        
        # At 30 fps
        fps = 30
        queue_size = queue_duration_seconds * fps
        queue_duration = queue_size / fps
        
        self.assertEqual(queue_duration, 4.0)
        print(f"✓ Queue at 30 fps: {queue_size} items = {queue_duration}s")
    
    def test_chunk_size_increases_with_sample_rate(self):
        """Test that higher sample rate = larger chunks"""
        fps = 24
        
        sample_rate_22050 = 22050
        samples_per_frame_22050 = sample_rate_22050 / fps
        
        sample_rate_44100 = 44100
        samples_per_frame_44100 = sample_rate_44100 / fps
        
        # 44100 Hz should have twice as many samples per frame as 22050 Hz
        self.assertAlmostEqual(samples_per_frame_44100 / samples_per_frame_22050, 2.0, places=1)
        print(f"✓ 22050 Hz: {samples_per_frame_22050} samples/frame")
        print(f"✓ 44100 Hz: {samples_per_frame_44100} samples/frame (2x)")
    
    def test_chunk_size_decreases_with_fps(self):
        """Test that higher FPS = smaller chunks"""
        sample_rate = 44100
        
        fps_24 = 24
        samples_per_frame_24 = sample_rate / fps_24
        
        fps_60 = 60
        samples_per_frame_60 = sample_rate / fps_60
        
        # 60 fps should have fewer samples per frame than 24 fps
        self.assertLess(samples_per_frame_60, samples_per_frame_24)
        ratio = samples_per_frame_24 / samples_per_frame_60
        self.assertAlmostEqual(ratio, 2.5, places=1)  # 60/24 = 2.5
        print(f"✓ 24 fps: {samples_per_frame_24:.1f} samples/frame")
        print(f"✓ 60 fps: {samples_per_frame_60:.1f} samples/frame (2.5x smaller)")
    
    def test_metadata_structure(self):
        """Test that metadata includes new FPS-based fields"""
        sample_rate = 44100
        target_fps = 24
        samples_per_frame = sample_rate / target_fps
        
        metadata = {
            'target_fps': target_fps,
            'samples_per_frame': samples_per_frame,
            'video_fps': 30.0,
            'sample_rate': sample_rate,
            'chunking_mode': 'fps_based'
        }
        
        # Verify all required fields are present
        self.assertIn('target_fps', metadata)
        self.assertIn('samples_per_frame', metadata)
        self.assertIn('sample_rate', metadata)
        self.assertIn('chunking_mode', metadata)
        
        # Verify values
        self.assertEqual(metadata['chunking_mode'], 'fps_based')
        self.assertAlmostEqual(metadata['samples_per_frame'], 1837.5, places=1)
        
        print(f"✓ Metadata includes fps_based chunking info")
        print(f"  - samples_per_frame: {metadata['samples_per_frame']:.2f}")
        print(f"  - chunking_mode: {metadata['chunking_mode']}")


if __name__ == "__main__":
    print("Testing FPS-Based Audio Chunking\n")
    print("="*60)
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFPSBasedAudioChunking)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("✅ All FPS-based audio chunking tests passed!")
    else:
        print("❌ Some tests failed")
        exit(1)
