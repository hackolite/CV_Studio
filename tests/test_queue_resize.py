#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for queue resize functionality.

This module tests the resize methods added to TimestampedQueue
and NodeDataQueueManager classes.
"""

import unittest
import time
from node.timestamped_queue import TimestampedQueue, NodeDataQueueManager


class TestTimestampedQueueResize(unittest.TestCase):
    """Test the resize functionality of TimestampedQueue."""
    
    def test_resize_increase(self):
        """Test increasing queue size."""
        queue = TimestampedQueue(maxsize=5, node_id="test_node")
        
        # Add 5 items
        for i in range(5):
            queue.put(f"data_{i}", timestamp=float(i))
        
        self.assertEqual(queue.size(), 5)
        
        # Resize to larger size
        queue.resize(10)
        
        # Verify size is still 5 and all data is preserved
        self.assertEqual(queue.size(), 5)
        oldest = queue.get_oldest()
        self.assertEqual(oldest.data, "data_0")
        latest = queue.get_latest()
        self.assertEqual(latest.data, "data_4")
    
    def test_resize_decrease(self):
        """Test decreasing queue size."""
        queue = TimestampedQueue(maxsize=10, node_id="test_node")
        
        # Add 10 items
        for i in range(10):
            queue.put(f"data_{i}", timestamp=float(i))
        
        self.assertEqual(queue.size(), 10)
        
        # Resize to smaller size (should keep most recent items)
        queue.resize(5)
        
        # Verify size is 5 and oldest items were dropped
        self.assertEqual(queue.size(), 5)
        oldest = queue.get_oldest()
        self.assertEqual(oldest.data, "data_5")
        latest = queue.get_latest()
        self.assertEqual(latest.data, "data_9")
    
    def test_resize_empty_queue(self):
        """Test resizing an empty queue."""
        queue = TimestampedQueue(maxsize=5, node_id="test_node")
        
        self.assertEqual(queue.size(), 0)
        
        # Resize empty queue
        queue.resize(10)
        
        # Verify queue is still empty
        self.assertEqual(queue.size(), 0)
    
    def test_resize_to_same_size(self):
        """Test resizing to the same size."""
        queue = TimestampedQueue(maxsize=5, node_id="test_node")
        
        # Add 3 items
        for i in range(3):
            queue.put(f"data_{i}", timestamp=float(i))
        
        self.assertEqual(queue.size(), 3)
        
        # Resize to same size
        queue.resize(5)
        
        # Verify all data is preserved
        self.assertEqual(queue.size(), 3)
        oldest = queue.get_oldest()
        self.assertEqual(oldest.data, "data_0")


class TestNodeDataQueueManagerResize(unittest.TestCase):
    """Test the resize_queue functionality of NodeDataQueueManager."""
    
    def test_resize_queue(self):
        """Test resizing a queue through the manager."""
        manager = NodeDataQueueManager(default_maxsize=10)
        
        # Add data to a queue
        for i in range(10):
            manager.put_data("1:Video", "image", f"frame_{i}", timestamp=float(i))
        
        # Verify initial size
        queue_info = manager.get_queue_info("1:Video", "image")
        self.assertEqual(queue_info["size"], 10)
        
        # Resize the queue
        manager.resize_queue("1:Video", "image", 5)
        
        # Verify resize (should keep most recent items)
        queue_info = manager.get_queue_info("1:Video", "image")
        self.assertEqual(queue_info["size"], 5)
        
        # Verify oldest item is now frame_5
        oldest_data = manager.get_oldest_data("1:Video", "image")
        self.assertEqual(oldest_data, "frame_5")
    
    def test_resize_multiple_data_types(self):
        """Test resizing different data types independently."""
        manager = NodeDataQueueManager(default_maxsize=10)
        
        # Add image and audio data
        for i in range(10):
            manager.put_data("1:Video", "image", f"frame_{i}", timestamp=float(i))
            manager.put_data("1:Video", "audio", f"audio_{i}", timestamp=float(i))
        
        # Resize only image queue
        manager.resize_queue("1:Video", "image", 5)
        
        # Verify image queue was resized
        image_info = manager.get_queue_info("1:Video", "image")
        self.assertEqual(image_info["size"], 5)
        
        # Verify audio queue was NOT resized
        audio_info = manager.get_queue_info("1:Video", "audio")
        self.assertEqual(audio_info["size"], 10)
    
    def test_resize_non_existent_queue(self):
        """Test resizing creates a queue if it doesn't exist."""
        manager = NodeDataQueueManager(default_maxsize=10)
        
        # Resize a queue that doesn't exist yet
        manager.resize_queue("1:Video", "image", 20)
        
        # Verify queue was created with the new size
        queue = manager.get_queue("1:Video", "image")
        self.assertIsNotNone(queue)
        self.assertEqual(queue._maxsize, 20)


if __name__ == "__main__":
    unittest.main()
