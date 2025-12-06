#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test timestamp preservation from input nodes through processing pipeline.

This test verifies that:
1. Input nodes create timestamps when outputting data
2. Processing nodes preserve the timestamp from their input source
3. Timestamps remain constant as data flows through the pipeline
"""

import time
import unittest
from unittest.mock import Mock
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict


class TestTimestampPreservation(unittest.TestCase):
    """Test that timestamps are preserved from input nodes through the pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.queue_manager = NodeDataQueueManager(default_maxsize=10)
        self.node_image_dict = QueueBackedDict(self.queue_manager, "image")
        self.node_audio_dict = QueueBackedDict(self.queue_manager, "audio")
        self.node_result_dict = QueueBackedDict(self.queue_manager, "json")
    
    def test_input_node_creates_timestamp(self):
        """Test that input nodes create timestamps when outputting data."""
        # Simulate an input node (e.g., Webcam) producing data
        input_node_id = "1:Webcam"
        test_image = "test_image_data"
        
        # Input node sets data (creates new timestamp)
        self.node_image_dict[input_node_id] = test_image
        
        # Verify timestamp was created
        timestamp = self.node_image_dict.get_timestamp(input_node_id)
        self.assertIsNotNone(timestamp, "Input node should create timestamp")
        self.assertGreater(timestamp, time.time() - 1, "Timestamp should be recent")
    
    def test_processing_node_preserves_timestamp(self):
        """Test that processing nodes preserve timestamps from their input."""
        # Simulate input node creating data with timestamp
        input_node_id = "1:Webcam"
        processing_node_id = "2:Blur"
        test_image = "test_image_data"
        
        # Input node creates data
        self.node_image_dict[input_node_id] = test_image
        time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Get the timestamp from input node
        input_timestamp = self.node_image_dict.get_timestamp(input_node_id)
        self.assertIsNotNone(input_timestamp)
        
        # Processing node gets data and processes it
        processed_image = "processed_image_data"
        
        # Processing node should preserve the timestamp
        self.node_image_dict.set_with_timestamp(processing_node_id, processed_image, input_timestamp)
        
        # Verify timestamp is preserved
        processing_timestamp = self.node_image_dict.get_timestamp(processing_node_id)
        self.assertEqual(input_timestamp, processing_timestamp, 
                        "Processing node should preserve input timestamp")
    
    def test_timestamp_preservation_through_pipeline(self):
        """Test timestamp preservation through a multi-node pipeline."""
        # Simulate: Webcam -> Blur -> Grayscale
        webcam_id = "1:Webcam"
        blur_id = "2:Blur"
        grayscale_id = "3:Grayscale"
        
        # Webcam creates data
        self.node_image_dict[webcam_id] = "webcam_image"
        original_timestamp = self.node_image_dict.get_timestamp(webcam_id)
        
        time.sleep(0.01)
        
        # Blur processes (should preserve timestamp)
        blur_timestamp = self.node_image_dict.get_timestamp(webcam_id)
        self.node_image_dict.set_with_timestamp(blur_id, "blurred_image", blur_timestamp)
        
        time.sleep(0.01)
        
        # Grayscale processes (should preserve timestamp)
        grayscale_timestamp = self.node_image_dict.get_timestamp(blur_id)
        self.node_image_dict.set_with_timestamp(grayscale_id, "grayscale_image", grayscale_timestamp)
        
        # Verify all timestamps are the same
        final_timestamp = self.node_image_dict.get_timestamp(grayscale_id)
        self.assertEqual(original_timestamp, final_timestamp,
                        "Timestamp should be preserved through entire pipeline")
    
    def test_different_data_types_preserve_timestamp(self):
        """Test that timestamps are preserved for image, audio, and json data."""
        input_node_id = "1:Video"
        processing_node_id = "2:Processor"
        
        # Input node creates data for all types
        self.node_image_dict[input_node_id] = "video_frame"
        self.node_audio_dict[input_node_id] = "audio_chunk"
        self.node_result_dict[input_node_id] = {"data": "json_data"}
        
        # Get timestamps
        image_timestamp = self.node_image_dict.get_timestamp(input_node_id)
        audio_timestamp = self.node_audio_dict.get_timestamp(input_node_id)
        json_timestamp = self.node_result_dict.get_timestamp(input_node_id)
        
        # All should have timestamps
        self.assertIsNotNone(image_timestamp)
        self.assertIsNotNone(audio_timestamp)
        self.assertIsNotNone(json_timestamp)
        
        time.sleep(0.01)
        
        # Processing node preserves timestamps for all types
        self.node_image_dict.set_with_timestamp(processing_node_id, "processed_frame", image_timestamp)
        self.node_audio_dict.set_with_timestamp(processing_node_id, "processed_audio", audio_timestamp)
        self.node_result_dict.set_with_timestamp(processing_node_id, {"processed": "data"}, json_timestamp)
        
        # Verify timestamps are preserved
        self.assertEqual(image_timestamp, self.node_image_dict.get_timestamp(processing_node_id))
        self.assertEqual(audio_timestamp, self.node_audio_dict.get_timestamp(processing_node_id))
        self.assertEqual(json_timestamp, self.node_result_dict.get_timestamp(processing_node_id))
    
    def test_multiple_input_sources(self):
        """Test that when a node has multiple inputs, it uses the first data connection's timestamp."""
        # Two input nodes
        webcam_id = "1:Webcam"
        video_id = "2:Video"
        mixer_id = "3:Mixer"
        
        # Both input nodes create data
        self.node_image_dict[webcam_id] = "webcam_frame"
        webcam_timestamp = self.node_image_dict.get_timestamp(webcam_id)
        
        time.sleep(0.02)  # Ensure different timestamps
        
        self.node_image_dict[video_id] = "video_frame"
        video_timestamp = self.node_image_dict.get_timestamp(video_id)
        
        # Verify they have different timestamps
        self.assertNotEqual(webcam_timestamp, video_timestamp)
        
        # Mixer node should use timestamp from one of its inputs
        # (In real implementation, it would use the first data connection)
        # For this test, we'll simulate using webcam's timestamp
        self.node_image_dict.set_with_timestamp(mixer_id, "mixed_frame", webcam_timestamp)
        
        mixer_timestamp = self.node_image_dict.get_timestamp(mixer_id)
        self.assertEqual(webcam_timestamp, mixer_timestamp)


if __name__ == "__main__":
    unittest.main()
