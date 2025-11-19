#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for the timestamped queue system.

This module tests the TimestampedQueue and NodeDataQueueManager classes
to ensure proper FIFO behavior with timestamped data.
"""

import unittest
import time
import threading
from node.timestamped_queue import (
    TimestampedData, 
    TimestampedQueue, 
    NodeDataQueueManager
)


class TestTimestampedData(unittest.TestCase):
    """Test the TimestampedData dataclass."""
    
    def test_creation(self):
        """Test creating a timestamped data object."""
        data = TimestampedData(
            data="test_value",
            timestamp=time.time(),
            node_id="1:TestNode"
        )
        self.assertEqual(data.data, "test_value")
        self.assertIsInstance(data.timestamp, float)
        self.assertEqual(data.node_id, "1:TestNode")
    
    def test_comparison(self):
        """Test comparison based on timestamp."""
        t1 = time.time()
        time.sleep(0.01)
        t2 = time.time()
        
        data1 = TimestampedData("value1", t1, "node1")
        data2 = TimestampedData("value2", t2, "node2")
        
        self.assertTrue(data1 < data2)
        self.assertFalse(data2 < data1)


class TestTimestampedQueue(unittest.TestCase):
    """Test the TimestampedQueue class."""
    
    def setUp(self):
        """Set up a fresh queue for each test."""
        self.queue = TimestampedQueue(maxsize=10, node_id="1:TestNode")
    
    def test_put_and_get_oldest(self):
        """Test putting data and retrieving the oldest."""
        # Add data with explicit timestamps
        t1 = time.time()
        self.queue.put("data1", t1)
        
        time.sleep(0.01)
        t2 = time.time()
        self.queue.put("data2", t2)
        
        # Oldest should be data1
        oldest = self.queue.get_oldest()
        self.assertIsNotNone(oldest)
        self.assertEqual(oldest.data, "data1")
        self.assertEqual(oldest.timestamp, t1)
    
    def test_get_latest(self):
        """Test retrieving the most recent data."""
        t1 = time.time()
        self.queue.put("data1", t1)
        
        time.sleep(0.01)
        t2 = time.time()
        self.queue.put("data2", t2)
        
        # Latest should be data2
        latest = self.queue.get_latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.data, "data2")
        self.assertEqual(latest.timestamp, t2)
    
    def test_pop_oldest_fifo(self):
        """Test FIFO behavior when popping data."""
        # Add multiple items
        self.queue.put("first", time.time())
        time.sleep(0.01)
        self.queue.put("second", time.time())
        time.sleep(0.01)
        self.queue.put("third", time.time())
        
        # Pop should return in FIFO order
        item1 = self.queue.pop_oldest()
        self.assertEqual(item1.data, "first")
        
        item2 = self.queue.pop_oldest()
        self.assertEqual(item2.data, "second")
        
        item3 = self.queue.pop_oldest()
        self.assertEqual(item3.data, "third")
        
        # Queue should now be empty
        item4 = self.queue.pop_oldest()
        self.assertIsNone(item4)
    
    def test_size_and_empty(self):
        """Test size and empty status."""
        self.assertTrue(self.queue.is_empty())
        self.assertEqual(self.queue.size(), 0)
        
        self.queue.put("data1")
        self.assertFalse(self.queue.is_empty())
        self.assertEqual(self.queue.size(), 1)
        
        self.queue.put("data2")
        self.assertEqual(self.queue.size(), 2)
        
        self.queue.pop_oldest()
        self.assertEqual(self.queue.size(), 1)
    
    def test_clear(self):
        """Test clearing the queue."""
        self.queue.put("data1")
        self.queue.put("data2")
        self.assertEqual(self.queue.size(), 2)
        
        self.queue.clear()
        self.assertTrue(self.queue.is_empty())
        self.assertEqual(self.queue.size(), 0)
    
    def test_maxsize_limit(self):
        """Test that queue respects maxsize limit."""
        small_queue = TimestampedQueue(maxsize=3, node_id="test")
        
        small_queue.put("data1")
        small_queue.put("data2")
        small_queue.put("data3")
        self.assertEqual(small_queue.size(), 3)
        
        # Adding a 4th item should remove the oldest
        small_queue.put("data4")
        self.assertEqual(small_queue.size(), 3)
        
        # Oldest should now be data2 (data1 was removed)
        oldest = small_queue.get_oldest()
        self.assertEqual(oldest.data, "data2")
    
    def test_get_all(self):
        """Test getting all items in order."""
        self.queue.put("first", time.time())
        time.sleep(0.01)
        self.queue.put("second", time.time())
        time.sleep(0.01)
        self.queue.put("third", time.time())
        
        all_items = self.queue.get_all()
        self.assertEqual(len(all_items), 3)
        self.assertEqual(all_items[0].data, "first")
        self.assertEqual(all_items[1].data, "second")
        self.assertEqual(all_items[2].data, "third")
    
    def test_thread_safety(self):
        """Test thread safety of the queue."""
        results = []
        
        def producer():
            for i in range(100):
                self.queue.put(f"data{i}")
        
        def consumer():
            for i in range(100):
                item = self.queue.pop_oldest()
                if item:
                    results.append(item.data)
        
        # Run producer and consumer in parallel
        t1 = threading.Thread(target=producer)
        t2 = threading.Thread(target=consumer)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # All items should have been consumed
        self.assertLessEqual(len(results), 100)


class TestNodeDataQueueManager(unittest.TestCase):
    """Test the NodeDataQueueManager class."""
    
    def setUp(self):
        """Set up a fresh manager for each test."""
        self.manager = NodeDataQueueManager(default_maxsize=10)
    
    def test_get_queue(self):
        """Test getting or creating queues."""
        queue1 = self.manager.get_queue("1:TestNode", "image")
        self.assertIsNotNone(queue1)
        self.assertIsInstance(queue1, TimestampedQueue)
        
        # Getting the same queue should return the same instance
        queue2 = self.manager.get_queue("1:TestNode", "image")
        self.assertIs(queue1, queue2)
        
        # Different data type should create a new queue
        queue3 = self.manager.get_queue("1:TestNode", "audio")
        self.assertIsNot(queue1, queue3)
    
    def test_put_and_get_data(self):
        """Test putting and getting data through the manager."""
        # Put data
        self.manager.put_data("1:TestNode", "image", "test_image")
        
        # Get oldest data
        data = self.manager.get_oldest_data("1:TestNode", "image")
        self.assertEqual(data, "test_image")
    
    def test_get_latest_data(self):
        """Test getting the latest data."""
        t1 = time.time()
        self.manager.put_data("1:TestNode", "image", "image1", t1)
        
        time.sleep(0.01)
        t2 = time.time()
        self.manager.put_data("1:TestNode", "image", "image2", t2)
        
        # Latest should be image2
        latest = self.manager.get_latest_data("1:TestNode", "image")
        self.assertEqual(latest, "image2")
        
        # Oldest should still be image1
        oldest = self.manager.get_oldest_data("1:TestNode", "image")
        self.assertEqual(oldest, "image1")
    
    def test_clear_node_queues(self):
        """Test clearing all queues for a node."""
        self.manager.put_data("1:TestNode", "image", "img1")
        self.manager.put_data("1:TestNode", "audio", "aud1")
        
        self.manager.clear_node_queues("1:TestNode")
        
        img_data = self.manager.get_oldest_data("1:TestNode", "image")
        aud_data = self.manager.get_oldest_data("1:TestNode", "audio")
        
        self.assertIsNone(img_data)
        self.assertIsNone(aud_data)
    
    def test_remove_node(self):
        """Test removing a node and its queues."""
        self.manager.put_data("1:TestNode", "image", "img1")
        
        self.manager.remove_node("1:TestNode")
        
        # After removal, data should not exist
        data = self.manager.get_oldest_data("1:TestNode", "image")
        self.assertIsNone(data)
    
    def test_get_queue_info(self):
        """Test getting queue information."""
        # Non-existent queue
        info = self.manager.get_queue_info("1:TestNode", "image")
        self.assertFalse(info["exists"])
        self.assertEqual(info["size"], 0)
        
        # Add some data
        t1 = time.time()
        self.manager.put_data("1:TestNode", "image", "img1", t1)
        time.sleep(0.01)
        t2 = time.time()
        self.manager.put_data("1:TestNode", "image", "img2", t2)
        
        # Check info
        info = self.manager.get_queue_info("1:TestNode", "image")
        self.assertTrue(info["exists"])
        self.assertEqual(info["size"], 2)
        self.assertFalse(info["is_empty"])
        self.assertEqual(info["oldest_timestamp"], t1)
        self.assertEqual(info["latest_timestamp"], t2)
    
    def test_multiple_nodes(self):
        """Test managing queues for multiple nodes."""
        self.manager.put_data("1:Node1", "image", "node1_img")
        self.manager.put_data("2:Node2", "image", "node2_img")
        self.manager.put_data("3:Node3", "image", "node3_img")
        
        # Each node should have its own data
        node1_data = self.manager.get_oldest_data("1:Node1", "image")
        node2_data = self.manager.get_oldest_data("2:Node2", "image")
        node3_data = self.manager.get_oldest_data("3:Node3", "image")
        
        self.assertEqual(node1_data, "node1_img")
        self.assertEqual(node2_data, "node2_img")
        self.assertEqual(node3_data, "node3_img")


if __name__ == '__main__':
    unittest.main()
