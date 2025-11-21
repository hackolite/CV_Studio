#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for queue logging functionality.

This module tests that data insertions into queues are properly logged
with timestamp and data type information.
"""

import unittest
import logging
import time
from io import StringIO
from node.timestamped_queue import TimestampedQueue, NodeDataQueueManager
from node.queue_adapter import QueueBackedDict


class TestQueueLogging(unittest.TestCase):
    """Test logging functionality for queue operations."""
    
    def setUp(self):
        """Set up logging capture for each test."""
        # Create a string buffer to capture log output
        self.log_buffer = StringIO()
        self.handler = logging.StreamHandler(self.log_buffer)
        self.handler.setLevel(logging.INFO)
        
        # Set up formatter
        formatter = logging.Formatter(
            '%(name)s - %(levelname)s - %(message)s'
        )
        self.handler.setFormatter(formatter)
        
        # Add handler to the relevant loggers
        self.timestamped_queue_logger = logging.getLogger('node.timestamped_queue')
        self.timestamped_queue_logger.setLevel(logging.INFO)
        self.timestamped_queue_logger.addHandler(self.handler)
        
        self.queue_adapter_logger = logging.getLogger('node.queue_adapter')
        self.queue_adapter_logger.setLevel(logging.INFO)
        self.queue_adapter_logger.addHandler(self.handler)
    
    def tearDown(self):
        """Clean up logging handlers."""
        self.timestamped_queue_logger.removeHandler(self.handler)
        self.queue_adapter_logger.removeHandler(self.handler)
        self.handler.close()
    
    def get_log_output(self):
        """Get the captured log output."""
        return self.log_buffer.getvalue()
    
    def test_timestamped_queue_logging(self):
        """Test that TimestampedQueue logs data insertions."""
        queue = TimestampedQueue(maxsize=10, node_id="1:TestNode")
        
        # Insert some data
        test_data = "test_value"
        queue.put(test_data)
        
        # Check log output
        log_output = self.get_log_output()
        self.assertIn("Queue [1:TestNode]", log_output)
        self.assertIn("Inserted data", log_output)
        self.assertIn("type=str", log_output)
        self.assertIn("timestamp=", log_output)
        self.assertIn("queue_size=1/10", log_output)
    
    def test_timestamped_queue_logging_different_types(self):
        """Test logging with different data types."""
        queue = TimestampedQueue(maxsize=10, node_id="2:DataNode")
        
        # Insert different types of data
        queue.put(42)  # int
        queue.put([1, 2, 3])  # list
        queue.put({"key": "value"})  # dict
        
        log_output = self.get_log_output()
        
        # Check that different types are logged
        self.assertIn("type=int", log_output)
        self.assertIn("type=list", log_output)
        self.assertIn("type=dict", log_output)
    
    def test_node_data_queue_manager_logging(self):
        """Test that NodeDataQueueManager logs data insertions."""
        manager = NodeDataQueueManager(default_maxsize=10)
        
        # Put data through the manager
        test_timestamp = time.time()
        manager.put_data("1:Camera", "image", "test_image_data", test_timestamp)
        
        # Check log output
        log_output = self.get_log_output()
        self.assertIn("Manager - Node [1:Camera]", log_output)
        self.assertIn("received image data", log_output)
        self.assertIn(f"timestamp={test_timestamp:.6f}", log_output)
    
    def test_queue_adapter_logging(self):
        """Test that QueueBackedDict logs data insertions."""
        manager = NodeDataQueueManager(default_maxsize=10)
        image_dict = QueueBackedDict(manager, "image")
        
        # Set data through the adapter
        image_dict["1:Webcam"] = "webcam_frame_data"
        
        # Check log output
        log_output = self.get_log_output()
        self.assertIn("QueueAdapter [image]", log_output)
        self.assertIn("Node [1:Webcam]", log_output)
        self.assertIn("type=str", log_output)
    
    def test_logging_with_multiple_insertions(self):
        """Test logging with multiple sequential insertions."""
        queue = TimestampedQueue(maxsize=5, node_id="3:MultiNode")
        
        # Insert multiple items
        for i in range(5):
            queue.put(f"data_{i}")
            time.sleep(0.001)  # Small delay to ensure different timestamps
        
        log_output = self.get_log_output()
        
        # Count the number of log entries
        log_lines = [line for line in log_output.split('\n') if 'Inserted data' in line]
        self.assertEqual(len(log_lines), 5)
        
        # Check that queue size is properly tracked
        self.assertIn("queue_size=5/5", log_output)
    
    def test_logging_shows_timestamp_precision(self):
        """Test that timestamps are logged with sufficient precision."""
        queue = TimestampedQueue(maxsize=10, node_id="4:PrecisionNode")
        
        # Insert data with explicit timestamp
        explicit_timestamp = 1234567890.123456
        queue.put("test_data", timestamp=explicit_timestamp)
        
        log_output = self.get_log_output()
        
        # Check that timestamp is logged with 6 decimal places
        self.assertIn(f"timestamp={explicit_timestamp:.6f}", log_output)
    
    def test_logging_buffer_overflow(self):
        """Test logging when buffer reaches max capacity and starts overwriting."""
        queue = TimestampedQueue(maxsize=3, node_id="5:OverflowNode")
        
        # Insert 4 items into a size-3 queue
        queue.put("item1")
        queue.put("item2")
        queue.put("item3")
        queue.put("item4")  # This should cause overflow
        
        log_output = self.get_log_output()
        
        # All insertions should be logged
        log_lines = [line for line in log_output.split('\n') if 'Inserted data' in line]
        self.assertEqual(len(log_lines), 4)
        
        # Last entry should show queue at max capacity
        self.assertIn("queue_size=3/3", log_output)


if __name__ == '__main__':
    unittest.main()
