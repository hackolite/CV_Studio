#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for the timestamped buffer system.

This module tests that the buffer correctly maintains 10 timestamped items,
does not consume items when reading, and provides access to all buffered values.
"""

import unittest
import time
from node.timestamped_queue import (
    TimestampedData, 
    TimestampedQueue, 
    NodeDataQueueManager
)
from node.queue_adapter import QueueBackedDict


class TestBufferBehavior(unittest.TestCase):
    """Test the buffer behavior (not FIFO consumption)."""
    
    def setUp(self):
        """Set up a fresh buffer for each test."""
        self.buffer = TimestampedQueue(maxsize=10, node_id="1:TestNode")
    
    def test_buffer_default_size_is_10(self):
        """Test that default buffer size is 10."""
        default_buffer = TimestampedQueue(node_id="test")
        self.assertEqual(default_buffer._maxsize, 10)
    
    def test_buffer_keeps_last_10_items(self):
        """Test that buffer maintains only the last 10 items."""
        # Add 15 items
        for i in range(15):
            self.buffer.put(f"item_{i}", time.time() + i * 0.001)
            time.sleep(0.001)
        
        # Should only have 10 items
        self.assertEqual(self.buffer.size(), 10)
        
        # Should have items 5-14 (oldest 5 items removed)
        all_items = self.buffer.get_all()
        self.assertEqual(len(all_items), 10)
        self.assertEqual(all_items[0].data, "item_5")
        self.assertEqual(all_items[-1].data, "item_14")
    
    def test_get_latest_does_not_remove(self):
        """Test that getting latest data does not remove it from buffer."""
        self.buffer.put("data1", time.time())
        time.sleep(0.01)
        self.buffer.put("data2", time.time())
        time.sleep(0.01)
        self.buffer.put("data3", time.time())
        
        # Get latest multiple times
        latest1 = self.buffer.get_latest()
        latest2 = self.buffer.get_latest()
        latest3 = self.buffer.get_latest()
        
        # All should return the same latest item
        self.assertEqual(latest1.data, "data3")
        self.assertEqual(latest2.data, "data3")
        self.assertEqual(latest3.data, "data3")
        
        # Buffer should still have all 3 items
        self.assertEqual(self.buffer.size(), 3)
    
    def test_get_oldest_does_not_remove(self):
        """Test that getting oldest data does not remove it from buffer."""
        self.buffer.put("data1", time.time())
        time.sleep(0.01)
        self.buffer.put("data2", time.time())
        
        # Get oldest multiple times
        oldest1 = self.buffer.get_oldest()
        oldest2 = self.buffer.get_oldest()
        
        # Both should return the same oldest item
        self.assertEqual(oldest1.data, "data1")
        self.assertEqual(oldest2.data, "data1")
        
        # Buffer should still have both items
        self.assertEqual(self.buffer.size(), 2)
    
    def test_all_items_accessible_with_timestamps(self):
        """Test that all buffered items are accessible with their timestamps."""
        timestamps = []
        for i in range(5):
            ts = time.time()
            timestamps.append(ts)
            self.buffer.put(f"data_{i}", ts)
            time.sleep(0.01)
        
        # Get all items
        all_items = self.buffer.get_all()
        self.assertEqual(len(all_items), 5)
        
        # Verify each item has correct data and timestamp
        for i, item in enumerate(all_items):
            self.assertEqual(item.data, f"data_{i}")
            self.assertEqual(item.timestamp, timestamps[i])
            self.assertEqual(item.node_id, "1:TestNode")
    
    def test_buffer_synchronization_use_case(self):
        """Test buffer can be used for synchronization with timestamps."""
        # Simulate video frames coming in
        frame_times = []
        for i in range(10):
            ts = time.time()
            frame_times.append(ts)
            self.buffer.put(f"frame_{i}", ts)
            time.sleep(0.005)
        
        # Get all frames with timestamps
        frames = self.buffer.get_all()
        
        # Verify we can synchronize using timestamps
        self.assertEqual(len(frames), 10)
        for i, frame in enumerate(frames):
            self.assertEqual(frame.data, f"frame_{i}")
            self.assertAlmostEqual(frame.timestamp, frame_times[i], places=3)
            
            # Verify timestamps are in ascending order
            if i > 0:
                self.assertGreater(frame.timestamp, frames[i-1].timestamp)


class TestQueueBackedDictBufferBehavior(unittest.TestCase):
    """Test QueueBackedDict with buffer behavior."""
    
    def setUp(self):
        """Set up a fresh manager and dict for each test."""
        self.manager = NodeDataQueueManager(default_maxsize=10)
        self.image_dict = QueueBackedDict(self.manager, "image")
    
    def test_manager_default_size_is_10(self):
        """Test that NodeDataQueueManager default size is 10."""
        self.assertEqual(self.manager._default_maxsize, 10)
    
    def test_get_returns_latest_not_oldest(self):
        """Test that getting from dict returns latest data (buffer behavior)."""
        # Add multiple values
        self.image_dict["1:Node1"] = "image1"
        time.sleep(0.01)
        self.image_dict["1:Node1"] = "image2"
        time.sleep(0.01)
        self.image_dict["1:Node1"] = "image3"
        
        # Getting should return the latest (image3)
        result = self.image_dict["1:Node1"]
        self.assertEqual(result, "image3")
        
        # Getting again should still return image3 (not consumed)
        result2 = self.image_dict["1:Node1"]
        self.assertEqual(result2, "image3")
    
    def test_buffer_maintains_10_items(self):
        """Test that buffer maintains only 10 items per node."""
        # Add 15 items
        for i in range(15):
            self.image_dict["1:Node1"] = f"image_{i}"
            time.sleep(0.001)
        
        # Get queue info
        info = self.image_dict.get_queue_info("1:Node1")
        self.assertEqual(info["size"], 10)
        self.assertTrue(info["exists"])
        self.assertFalse(info["is_empty"])
    
    def test_all_buffered_items_accessible(self):
        """Test that all buffered items can be accessed."""
        # Add 5 items
        for i in range(5):
            self.image_dict["1:Node1"] = f"image_{i}"
            time.sleep(0.01)
        
        # Access underlying queue to get all items
        queue = self.manager.get_queue("1:Node1", "image")
        all_items = queue.get_all()
        
        # Verify all 5 items are present
        self.assertEqual(len(all_items), 5)
        for i, item in enumerate(all_items):
            self.assertEqual(item.data, f"image_{i}")
            self.assertIsNotNone(item.timestamp)
    
    def test_multiple_nodes_separate_buffers(self):
        """Test that each node has its own buffer."""
        # Add data to multiple nodes
        self.image_dict["1:Node1"] = "node1_img"
        self.image_dict["2:Node2"] = "node2_img"
        self.image_dict["3:Node3"] = "node3_img"
        
        # Each should maintain its own latest data
        self.assertEqual(self.image_dict["1:Node1"], "node1_img")
        self.assertEqual(self.image_dict["2:Node2"], "node2_img")
        self.assertEqual(self.image_dict["3:Node3"], "node3_img")
        
        # Each should have separate buffers
        info1 = self.image_dict.get_queue_info("1:Node1")
        info2 = self.image_dict.get_queue_info("2:Node2")
        info3 = self.image_dict.get_queue_info("3:Node3")
        
        self.assertEqual(info1["size"], 1)
        self.assertEqual(info2["size"], 1)
        self.assertEqual(info3["size"], 1)


class TestTimestampSynchronization(unittest.TestCase):
    """Test timestamp-based synchronization scenarios."""
    
    def setUp(self):
        """Set up buffers for synchronization testing."""
        self.manager = NodeDataQueueManager(default_maxsize=10)
        self.video_dict = QueueBackedDict(self.manager, "image")
        self.audio_dict = QueueBackedDict(self.manager, "audio")
    
    def test_multi_stream_synchronization(self):
        """Test synchronizing multiple data streams using timestamps."""
        # Simulate video and audio streams
        base_time = time.time()
        
        # Add 5 video frames and 5 audio chunks with specific timestamps
        for i in range(5):
            ts = base_time + i * 0.1  # 100ms intervals
            self.video_dict["1:Camera"] = f"frame_{i}"
            self.audio_dict["1:Microphone"] = f"audio_{i}"
            time.sleep(0.01)
        
        # Get all video and audio data
        video_queue = self.manager.get_queue("1:Camera", "image")
        audio_queue = self.manager.get_queue("1:Microphone", "audio")
        
        video_items = video_queue.get_all()
        audio_items = audio_queue.get_all()
        
        # Both should have 5 items
        self.assertEqual(len(video_items), 5)
        self.assertEqual(len(audio_items), 5)
        
        # All items should have timestamps for synchronization
        for item in video_items:
            self.assertIsNotNone(item.timestamp)
        for item in audio_items:
            self.assertIsNotNone(item.timestamp)
    
    def test_timestamp_ordering_in_buffer(self):
        """Test that buffer maintains chronological order."""
        # Add items with explicit timestamps
        timestamps = []
        for i in range(10):
            ts = time.time()
            timestamps.append(ts)
            self.video_dict["1:Node"] = f"item_{i}"
            time.sleep(0.005)
        
        # Get all items
        queue = self.manager.get_queue("1:Node", "image")
        items = queue.get_all()
        
        # Verify chronological order
        for i in range(len(items) - 1):
            self.assertLessEqual(items[i].timestamp, items[i+1].timestamp)


if __name__ == '__main__':
    unittest.main()
