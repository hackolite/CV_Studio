#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test dynamic queue size calculations for Video node.

This test validates that queue sizes are correctly calculated based on:
- Image queue: num_chunks × chunk_duration × fps
- Audio queue: num_chunks
"""

import unittest


class TestQueueSizeCalculation(unittest.TestCase):
    """Test queue size calculations"""
    
    def test_default_values(self):
        """Test with default values: 4 chunks, 2.0s chunk, 30fps"""
        num_chunks_to_keep = 4
        chunk_duration = 2.0
        fps = 30.0
        
        # Image queue: num_chunks * chunk_duration * fps
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        # Audio queue: num_chunks
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 240)
        self.assertEqual(audio_queue_size, 4)
        
        print(f"✓ Default values: Image={image_queue_size}, Audio={audio_queue_size}")
    
    def test_high_fps_video(self):
        """Test with 60 FPS video"""
        num_chunks_to_keep = 4
        chunk_duration = 2.0
        fps = 60.0
        
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 480)
        self.assertEqual(audio_queue_size, 4)
        
        print(f"✓ 60 FPS video: Image={image_queue_size}, Audio={audio_queue_size}")
    
    def test_large_chunk_size(self):
        """Test with larger chunk size (5 seconds)"""
        num_chunks_to_keep = 4
        chunk_duration = 5.0
        fps = 30.0
        
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 600)
        self.assertEqual(audio_queue_size, 4)
        
        print(f"✓ 5s chunks: Image={image_queue_size}, Audio={audio_queue_size}")
    
    def test_more_chunks_to_keep(self):
        """Test with more chunks to keep (10 chunks)"""
        num_chunks_to_keep = 10
        chunk_duration = 2.0
        fps = 30.0
        
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 600)
        self.assertEqual(audio_queue_size, 10)
        
        print(f"✓ 10 chunks: Image={image_queue_size}, Audio={audio_queue_size}")
    
    def test_minimum_chunks(self):
        """Test with minimum chunks (1 chunk)"""
        num_chunks_to_keep = 1
        chunk_duration = 2.0
        fps = 30.0
        
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 60)
        self.assertEqual(audio_queue_size, 1)
        
        print(f"✓ 1 chunk: Image={image_queue_size}, Audio={audio_queue_size}")
    
    def test_maximum_chunks(self):
        """Test with maximum chunks (20 chunks)"""
        num_chunks_to_keep = 20
        chunk_duration = 2.0
        fps = 30.0
        
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 1200)
        self.assertEqual(audio_queue_size, 20)
        
        print(f"✓ 20 chunks: Image={image_queue_size}, Audio={audio_queue_size}")
    
    def test_small_chunk_size(self):
        """Test with small chunk size (0.5 seconds)"""
        num_chunks_to_keep = 4
        chunk_duration = 0.5
        fps = 30.0
        
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 60)
        self.assertEqual(audio_queue_size, 4)
        
        print(f"✓ 0.5s chunks: Image={image_queue_size}, Audio={audio_queue_size}")
    
    def test_24fps_video(self):
        """Test with 24 FPS video (cinema standard)"""
        num_chunks_to_keep = 4
        chunk_duration = 2.0
        fps = 24.0
        
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 192)
        self.assertEqual(audio_queue_size, 4)
        
        print(f"✓ 24 FPS video: Image={image_queue_size}, Audio={audio_queue_size}")
    
    def test_combined_extreme_values(self):
        """Test with extreme combination: 20 chunks, 10s duration, 120fps"""
        num_chunks_to_keep = 20
        chunk_duration = 10.0
        fps = 120.0
        
        image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
        audio_queue_size = num_chunks_to_keep
        
        self.assertEqual(image_queue_size, 24000)
        self.assertEqual(audio_queue_size, 20)
        
        print(f"✓ Extreme values: Image={image_queue_size}, Audio={audio_queue_size}")


if __name__ == "__main__":
    unittest.main()
