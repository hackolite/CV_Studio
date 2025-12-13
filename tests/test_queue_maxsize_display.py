#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that queue info returns maxsize (capacity) instead of size (current items).

This test verifies that the VideoNode displays the maximum queue capacity
(configured number of chunks) rather than the current number of items in the queue.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.timestamped_queue import TimestampedQueue, NodeDataQueueManager


class TestQueueMaxsizeDisplay(unittest.TestCase):
    """Test that maxsize is available in queue info"""
    
    def test_timestamped_queue_maxsize_method(self):
        """Test that TimestampedQueue has a maxsize() method"""
        queue = TimestampedQueue(maxsize=100, node_id="test_node")
        
        # Verify maxsize method exists and returns correct value
        self.assertEqual(queue.maxsize(), 100)
        
        # Verify size is different from maxsize when queue is not full
        queue.put("item1")
        queue.put("item2")
        self.assertEqual(queue.size(), 2)
        self.assertEqual(queue.maxsize(), 100)
        
        print("✓ TimestampedQueue.maxsize() returns correct capacity")
    
    def test_queue_manager_get_queue_info_includes_maxsize(self):
        """Test that get_queue_info includes maxsize"""
        manager = NodeDataQueueManager(default_maxsize=50)
        
        # Create a queue and add some data
        manager.put_data("node1", "image", "frame1")
        manager.put_data("node1", "image", "frame2")
        
        # Get queue info
        info = manager.get_queue_info("node1", "image")
        
        # Verify info includes both size and maxsize
        self.assertTrue(info.get("exists", False))
        self.assertEqual(info.get("size", 0), 2, "Should have 2 items")
        self.assertEqual(info.get("maxsize", 0), 50, "Should have maxsize of 50")
        
        print(f"✓ Queue info includes: size={info['size']}, maxsize={info['maxsize']}")
    
    def test_maxsize_vs_size_after_queue_full(self):
        """Test that maxsize stays constant even when queue is full"""
        queue = TimestampedQueue(maxsize=5, node_id="test_node")
        
        # Fill queue beyond capacity
        for i in range(10):
            queue.put(f"item{i}")
        
        # Size should be capped at maxsize
        self.assertEqual(queue.size(), 5, "Size should be capped at maxsize")
        self.assertEqual(queue.maxsize(), 5, "Maxsize should remain constant")
        
        print("✓ Maxsize remains constant when queue is full")
    
    def test_maxsize_after_resize(self):
        """Test that maxsize is updated after resizing"""
        queue = TimestampedQueue(maxsize=10, node_id="test_node")
        
        # Add some items
        for i in range(5):
            queue.put(f"item{i}")
        
        # Resize queue
        queue.resize(20)
        
        # Verify maxsize is updated
        self.assertEqual(queue.maxsize(), 20)
        self.assertEqual(queue.size(), 5, "Size should remain unchanged")
        
        print("✓ Maxsize is correctly updated after resize")
    
    def test_audio_queue_maxsize_shows_chunks_not_items(self):
        """Test that audio queue maxsize reflects num_chunks, not 800"""
        manager = NodeDataQueueManager(default_maxsize=800)
        
        # Simulate video node with 4 audio chunks configured
        num_chunks = 4
        
        # Resize audio queue to num_chunks (as done in video node preprocessing)
        manager.resize_queue("1:Video", "audio", num_chunks)
        
        # Add some audio chunks
        manager.put_data("1:Video", "audio", {"data": [1, 2, 3], "sample_rate": 44100})
        manager.put_data("1:Video", "audio", {"data": [4, 5, 6], "sample_rate": 44100})
        
        # Get queue info
        info = manager.get_queue_info("1:Video", "audio")
        
        # Verify maxsize shows 4 (num_chunks), not 800
        self.assertEqual(info.get("maxsize"), 4, "Audio queue maxsize should be 4 chunks, not 800")
        self.assertEqual(info.get("size"), 2, "Should have 2 audio chunks")
        
        print(f"✓ Audio queue correctly shows maxsize={info['maxsize']} chunks (not 800 items)")
    
    def test_image_queue_maxsize_based_on_fps_and_chunks(self):
        """Test that image queue maxsize reflects fps * duration * chunks"""
        manager = NodeDataQueueManager(default_maxsize=800)
        
        # Simulate video node configuration: 4 chunks, 2s each, 30 FPS
        num_chunks = 4
        chunk_duration = 2.0
        fps = 30.0
        expected_image_maxsize = int(num_chunks * chunk_duration * fps)  # 4 * 2 * 30 = 240
        
        # Resize image queue as done in video node preprocessing
        manager.resize_queue("1:Video", "image", expected_image_maxsize)
        
        # Add some frames
        for i in range(10):
            manager.put_data("1:Video", "image", f"frame{i}")
        
        # Get queue info
        info = manager.get_queue_info("1:Video", "image")
        
        # Verify maxsize shows calculated value (240), not 800
        self.assertEqual(info.get("maxsize"), expected_image_maxsize, 
                        f"Image queue maxsize should be {expected_image_maxsize} (4 chunks × 2s × 30fps)")
        self.assertEqual(info.get("size"), 10, "Should have 10 frames")
        
        print(f"✓ Image queue correctly shows maxsize={info['maxsize']} frames (not 800 items)")


if __name__ == "__main__":
    unittest.main()
