#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for the timestamped queue system with CV_Studio nodes.

This test verifies that the queue system works correctly with the actual
node update mechanism used in CV_Studio.
"""

import unittest
import time
import copy
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict


class MockNode:
    """Mock node for testing."""
    
    def __init__(self, node_tag, node_id):
        self.node_tag = node_tag
        self.node_id = node_id
        self.node_id_name = f"{node_id}:{node_tag}"
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        """Simulate a simple passthrough node."""
        # Get input from connected nodes
        input_image = None
        if connection_list:
            source_node = connection_list[0][0].split(":")[:2]
            source_node = ":".join(source_node)
            input_image = node_image_dict.get(source_node)
        
        # Process and return
        return {
            "image": input_image,
            "json": {"processed": True},
            "audio": None
        }


class TestQueueSystemIntegration(unittest.TestCase):
    """Integration tests for the queue system."""
    
    def setUp(self):
        """Set up the queue manager and mock nodes."""
        self.queue_manager = NodeDataQueueManager(default_maxsize=10)
        self.node_image_dict = QueueBackedDict(self.queue_manager, "image")
        self.node_result_dict = QueueBackedDict(self.queue_manager, "json")
        self.node_audio_dict = QueueBackedDict(self.queue_manager, "audio")
        
        # Create mock nodes
        self.source_node = MockNode("SourceNode", 1)
        self.process_node = MockNode("ProcessNode", 2)
    
    def test_basic_data_flow(self):
        """Test basic data flow from source to processing node."""
        # Source node produces data
        source_data = {"image": "test_image_1", "json": None, "audio": None}
        
        # Simulate main.py's update_node_info storing the data
        self.node_image_dict[self.source_node.node_id_name] = copy.deepcopy(source_data["image"])
        self.node_result_dict[self.source_node.node_id_name] = copy.deepcopy(source_data["json"])
        self.node_audio_dict[self.source_node.node_id_name] = copy.deepcopy(source_data["audio"])
        
        # Processing node consumes data
        connection_list = [[f"{self.source_node.node_id_name}:Image:Output01"]]
        
        result = self.process_node.update(
            self.process_node.node_id,
            connection_list,
            self.node_image_dict,
            self.node_result_dict,
            self.node_audio_dict
        )
        
        # Verify the processing node received the data
        self.assertEqual(result["image"], "test_image_1")
        self.assertTrue(result["json"]["processed"])
    
    def test_buffer_order_multiple_frames(self):
        """Test that multiple frames are stored in buffer and latest is retrieved."""
        source_node_name = self.source_node.node_id_name
        
        # Simulate source node producing multiple frames
        t1 = time.time()
        self.queue_manager.put_data(source_node_name, "image", "frame1", t1)
        
        time.sleep(0.01)
        t2 = time.time()
        self.queue_manager.put_data(source_node_name, "image", "frame2", t2)
        
        time.sleep(0.01)
        t3 = time.time()
        self.queue_manager.put_data(source_node_name, "image", "frame3", t3)
        
        # Retrieve frames - buffer behavior returns latest
        latest_frame = self.node_image_dict[source_node_name]
        self.assertEqual(latest_frame, "frame3")
        
        # The buffer still has all frames (get doesn't remove)
        oldest = self.queue_manager.get_oldest_data(source_node_name, "image")
        self.assertEqual(oldest, "frame1")
        
        latest = self.queue_manager.get_latest_data(source_node_name, "image")
        self.assertEqual(latest, "frame3")
        
        # All 3 frames should still be in buffer
        queue = self.queue_manager.get_queue(source_node_name, "image")
        all_frames = queue.get_all()
        self.assertEqual(len(all_frames), 3)
        self.assertEqual(all_frames[0].data, "frame1")
        self.assertEqual(all_frames[1].data, "frame2")
        self.assertEqual(all_frames[2].data, "frame3")
    
    def test_multiple_nodes_pipeline(self):
        """Test a pipeline of multiple nodes with queue system."""
        # Create a 3-node pipeline: Input -> Process -> Output
        input_node = MockNode("InputNode", 1)
        process_node = MockNode("ProcessNode", 2)
        output_node = MockNode("OutputNode", 3)
        
        # Input node produces data
        self.node_image_dict[input_node.node_id_name] = "input_image"
        
        # Process node consumes from input
        connection_list = [[f"{input_node.node_id_name}:Image:Output01"]]
        process_result = process_node.update(
            process_node.node_id,
            connection_list,
            self.node_image_dict,
            self.node_result_dict,
            self.node_audio_dict
        )
        
        # Store process node output
        self.node_image_dict[process_node.node_id_name] = process_result["image"]
        
        # Output node consumes from process node
        connection_list = [[f"{process_node.node_id_name}:Image:Output01"]]
        output_result = output_node.update(
            output_node.node_id,
            connection_list,
            self.node_image_dict,
            self.node_result_dict,
            self.node_audio_dict
        )
        
        # Verify data flowed through the pipeline
        self.assertEqual(output_result["image"], "input_image")
    
    def test_queue_info_monitoring(self):
        """Test monitoring queue status during operation."""
        source_node_name = self.source_node.node_id_name
        
        # Initially empty
        info = self.node_image_dict.get_queue_info(source_node_name)
        self.assertFalse(info.get("exists", False) and not info.get("is_empty", True))
        
        # Add some data
        for i in range(5):
            self.node_image_dict[source_node_name] = f"frame_{i}"
            time.sleep(0.001)
        
        # Check queue info
        info = self.node_image_dict.get_queue_info(source_node_name)
        self.assertTrue(info["exists"])
        self.assertEqual(info["size"], 5)
        self.assertFalse(info["is_empty"])
        self.assertIsNotNone(info["oldest_timestamp"])
        self.assertIsNotNone(info["latest_timestamp"])
        
        # Verify timestamps are in order
        self.assertLess(info["oldest_timestamp"], info["latest_timestamp"])
    
    def test_backward_compatibility_dict_operations(self):
        """Test that dict operations work as expected."""
        # Test 'in' operator
        self.assertNotIn("1:TestNode", self.node_image_dict)
        
        self.node_image_dict["1:TestNode"] = "test_value"
        self.assertIn("1:TestNode", self.node_image_dict)
        
        # Test get with default
        value = self.node_image_dict.get("1:NonExistent", "default")
        self.assertEqual(value, "default")
        
        value = self.node_image_dict.get("1:TestNode", "default")
        self.assertEqual(value, "test_value")
        
        # Test keys/values/items
        self.node_image_dict["2:AnotherNode"] = "another_value"
        
        keys = list(self.node_image_dict.keys())
        self.assertIn("1:TestNode", keys)
        self.assertIn("2:AnotherNode", keys)
    
    def test_concurrent_node_updates(self):
        """Test that multiple nodes can update concurrently."""
        import threading
        
        results = []
        
        def update_node(node_name, value):
            for i in range(10):
                self.node_image_dict[node_name] = f"{value}_{i}"
                time.sleep(0.001)
        
        # Create threads for concurrent updates
        threads = []
        for i in range(3):
            t = threading.Thread(target=update_node, args=(f"{i}:Node{i}", f"node{i}"))
            threads.append(t)
            t.start()
        
        # Wait for all to complete
        for t in threads:
            t.join()
        
        # Verify all nodes have data
        for i in range(3):
            node_name = f"{i}:Node{i}"
            self.assertIn(node_name, self.node_image_dict)
            
            # Check queue has data
            info = self.node_image_dict.get_queue_info(node_name)
            self.assertTrue(info["exists"])
            self.assertGreater(info["size"], 0)


if __name__ == '__main__':
    unittest.main()
