#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for the QueueBackedDict adapter.

This module tests the backward-compatible dictionary interface
that uses timestamped queues internally.
"""

import unittest
import time
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict


class TestQueueBackedDict(unittest.TestCase):
    """Test the QueueBackedDict class."""
    
    def setUp(self):
        """Set up a fresh manager and dict for each test."""
        self.manager = NodeDataQueueManager(default_maxsize=10)
        self.queue_dict = QueueBackedDict(self.manager, "image")
    
    def test_set_and_get_item(self):
        """Test setting and getting items like a dict."""
        self.queue_dict["1:TestNode"] = "test_image"
        
        result = self.queue_dict["1:TestNode"]
        self.assertEqual(result, "test_image")
    
    def test_get_with_default(self):
        """Test get method with default value."""
        result = self.queue_dict.get("1:NonExistent", "default_value")
        self.assertEqual(result, "default_value")
        
        self.queue_dict["1:TestNode"] = "test_data"
        result = self.queue_dict.get("1:TestNode", "default_value")
        self.assertEqual(result, "test_data")
    
    def test_contains(self):
        """Test __contains__ (in operator)."""
        self.assertNotIn("1:TestNode", self.queue_dict)
        
        self.queue_dict["1:TestNode"] = "test_data"
        self.assertIn("1:TestNode", self.queue_dict)
    
    def test_delete_item(self):
        """Test deleting items."""
        self.queue_dict["1:TestNode"] = "test_data"
        self.assertIn("1:TestNode", self.queue_dict)
        
        del self.queue_dict["1:TestNode"]
        
        result = self.queue_dict.get("1:TestNode")
        self.assertIsNone(result)
    
    def test_buffer_behavior(self):
        """Test that buffer behavior works through the dict interface (returns latest)."""
        # Add multiple values with different timestamps
        t1 = time.time()
        self.manager.put_data("1:TestNode", "image", "old_image", t1)
        
        time.sleep(0.01)
        t2 = time.time()
        self.manager.put_data("1:TestNode", "image", "new_image", t2)
        
        # Getting from dict should return the latest (buffer behavior)
        result = self.queue_dict["1:TestNode"]
        self.assertEqual(result, "new_image")
    
    def test_get_latest(self):
        """Test getting the latest data directly."""
        t1 = time.time()
        self.manager.put_data("1:TestNode", "image", "old_image", t1)
        
        time.sleep(0.01)
        t2 = time.time()
        self.manager.put_data("1:TestNode", "image", "new_image", t2)
        
        # Get latest should return the newest
        latest = self.queue_dict.get_latest("1:TestNode")
        self.assertEqual(latest, "new_image")
    
    def test_cache_fallback(self):
        """Test that cache is used when queue is empty."""
        # Set directly (adds to cache and queue)
        self.queue_dict["1:TestNode"] = "cached_value"
        
        # Clear the queue but leave cache
        self.manager.clear_node_queues("1:TestNode")
        
        # Should still get cached value
        result = self.queue_dict["1:TestNode"]
        self.assertEqual(result, "cached_value")
    
    def test_keys_values_items(self):
        """Test dict-like methods."""
        self.queue_dict["1:Node1"] = "value1"
        self.queue_dict["2:Node2"] = "value2"
        
        keys = list(self.queue_dict.keys())
        self.assertIn("1:Node1", keys)
        self.assertIn("2:Node2", keys)
        
        values = list(self.queue_dict.values())
        self.assertIn("value1", values)
        self.assertIn("value2", values)
        
        items = list(self.queue_dict.items())
        self.assertIn(("1:Node1", "value1"), items)
        self.assertIn(("2:Node2", "value2"), items)
    
    def test_clear(self):
        """Test clearing the dict."""
        self.queue_dict["1:Node1"] = "value1"
        self.queue_dict["2:Node2"] = "value2"
        
        self.queue_dict.clear()
        
        # Cache should be empty
        self.assertEqual(len(list(self.queue_dict.keys())), 0)
    
    def test_get_queue_info(self):
        """Test getting queue information through the dict."""
        self.queue_dict["1:TestNode"] = "value1"
        time.sleep(0.01)
        self.queue_dict["1:TestNode"] = "value2"
        
        info = self.queue_dict.get_queue_info("1:TestNode")
        self.assertTrue(info["exists"])
        self.assertEqual(info["size"], 2)
        self.assertFalse(info["is_empty"])
    
    def test_none_values(self):
        """Test handling of None values."""
        self.queue_dict["1:TestNode"] = None
        
        # None should not be added to queue (only to cache)
        result = self.queue_dict.get("1:TestNode")
        self.assertIsNone(result)
        
        # Queue info - queue might not exist or be empty
        info = self.queue_dict.get_queue_info("1:TestNode")
        # Either doesn't exist or is empty
        if info["exists"]:
            self.assertTrue(info["is_empty"])
        else:
            self.assertFalse(info["exists"])
    
    def test_multiple_data_types(self):
        """Test using different QueueBackedDict instances for different data types."""
        image_dict = QueueBackedDict(self.manager, "image")
        audio_dict = QueueBackedDict(self.manager, "audio")
        json_dict = QueueBackedDict(self.manager, "json")
        
        # Add data to different types
        image_dict["1:TestNode"] = "image_data"
        audio_dict["1:TestNode"] = "audio_data"
        json_dict["1:TestNode"] = "json_data"
        
        # Each should maintain its own data
        self.assertEqual(image_dict["1:TestNode"], "image_data")
        self.assertEqual(audio_dict["1:TestNode"], "audio_data")
        self.assertEqual(json_dict["1:TestNode"], "json_data")


if __name__ == '__main__':
    unittest.main()
