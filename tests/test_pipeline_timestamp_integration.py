#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for timestamp preservation in a realistic node pipeline.

This test simulates a complete pipeline:
Webcam -> Blur -> Grayscale -> Object Detection -> Output

It verifies that the timestamp from the Webcam (input node) is preserved
throughout the entire processing pipeline.
"""

import time
import unittest
import copy
from unittest.mock import Mock, MagicMock
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict


class TestPipelineTimestampIntegration(unittest.TestCase):
    """Integration test for timestamp preservation in a realistic pipeline."""
    
    def setUp(self):
        """Set up a complete node pipeline with queue system."""
        self.queue_manager = NodeDataQueueManager(default_maxsize=10)
        self.node_image_dict = QueueBackedDict(self.queue_manager, "image")
        self.node_result_dict = QueueBackedDict(self.queue_manager, "json")
        self.node_audio_dict = QueueBackedDict(self.queue_manager, "audio")
    
    def _simulate_node_update(self, node_id_name, connection_list, data):
        """
        Simulate the main loop's node update logic.
        This mirrors the logic in main.py update_node_info()
        """
        # Determine if this is an input node or a processing node
        has_data_input = False
        source_timestamp = None
        
        for connection_info in connection_list:
            if len(connection_info) >= 2:
                connection_type = connection_info[0].split(":")[2]
                if connection_type in ["IMAGE", "AUDIO", "JSON"]:
                    has_data_input = True
                    # Get the timestamp from the source node
                    source_node_id = ":".join(connection_info[0].split(":")[:2])
                    
                    # Try to get timestamp based on connection type
                    if connection_type == "IMAGE":
                        source_timestamp = self.node_image_dict.get_timestamp(source_node_id)
                    elif connection_type == "AUDIO":
                        source_timestamp = self.node_audio_dict.get_timestamp(source_node_id)
                    elif connection_type == "JSON":
                        source_timestamp = self.node_result_dict.get_timestamp(source_node_id)
                    
                    # Use the first data connection's timestamp
                    if source_timestamp is not None:
                        break
        
        # Store data with appropriate timestamp
        if has_data_input and source_timestamp is not None:
            # Processing node - preserve source timestamp
            self.node_image_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["image"]), source_timestamp)
            self.node_result_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["json"]), source_timestamp)
            self.node_audio_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["audio"]), source_timestamp)
        else:
            # Input node - create new timestamp
            self.node_image_dict[node_id_name] = copy.deepcopy(data["image"])
            self.node_result_dict[node_id_name] = copy.deepcopy(data["json"])
            self.node_audio_dict[node_id_name] = copy.deepcopy(data["audio"])
    
    def test_complete_image_processing_pipeline(self):
        """Test timestamp preservation through a complete image processing pipeline."""
        # Define the pipeline: Webcam -> Blur -> Grayscale -> ObjectDetection
        
        # 1. Webcam (input node) produces frame
        webcam_id = "1:Webcam"
        webcam_data = {
            "image": "webcam_frame_data",
            "json": None,
            "audio": None
        }
        webcam_connections = []  # No input connections - it's an input node
        
        self._simulate_node_update(webcam_id, webcam_connections, webcam_data)
        
        # Get the original timestamp from webcam
        original_timestamp = self.node_image_dict.get_timestamp(webcam_id)
        self.assertIsNotNone(original_timestamp, "Webcam should create timestamp")
        
        time.sleep(0.01)  # Simulate processing delay
        
        # 2. Blur (processing node) receives and processes frame
        blur_id = "2:Blur"
        blur_connections = [
            (f"{webcam_id}:IMAGE:Output01", f"{blur_id}:IMAGE:Input01")
        ]
        blur_data = {
            "image": "blurred_frame_data",
            "json": None,
            "audio": None
        }
        
        self._simulate_node_update(blur_id, blur_connections, blur_data)
        
        blur_timestamp = self.node_image_dict.get_timestamp(blur_id)
        self.assertEqual(original_timestamp, blur_timestamp,
                        "Blur should preserve webcam timestamp")
        
        time.sleep(0.01)
        
        # 3. Grayscale (processing node) receives and processes frame
        grayscale_id = "3:Grayscale"
        grayscale_connections = [
            (f"{blur_id}:IMAGE:Output01", f"{grayscale_id}:IMAGE:Input01")
        ]
        grayscale_data = {
            "image": "grayscale_frame_data",
            "json": None,
            "audio": None
        }
        
        self._simulate_node_update(grayscale_id, grayscale_connections, grayscale_data)
        
        grayscale_timestamp = self.node_image_dict.get_timestamp(grayscale_id)
        self.assertEqual(original_timestamp, grayscale_timestamp,
                        "Grayscale should preserve original timestamp")
        
        time.sleep(0.01)
        
        # 4. Object Detection (processing node) produces both image and json
        detection_id = "4:ObjectDetection"
        detection_connections = [
            (f"{grayscale_id}:IMAGE:Output01", f"{detection_id}:IMAGE:Input01")
        ]
        detection_data = {
            "image": "detection_visualization",
            "json": {"detections": [{"class": "person", "confidence": 0.95}]},
            "audio": None
        }
        
        self._simulate_node_update(detection_id, detection_connections, detection_data)
        
        detection_image_timestamp = self.node_image_dict.get_timestamp(detection_id)
        detection_json_timestamp = self.node_result_dict.get_timestamp(detection_id)
        
        self.assertEqual(original_timestamp, detection_image_timestamp,
                        "Detection image should preserve original timestamp")
        self.assertEqual(original_timestamp, detection_json_timestamp,
                        "Detection JSON should preserve original timestamp")
    
    def test_video_with_audio_pipeline(self):
        """Test timestamp preservation for video with audio processing."""
        # Pipeline: Video -> [Video Processing, Audio Processing] -> Output
        
        # 1. Video node (input) produces both video frame and audio
        video_id = "1:Video"
        video_data = {
            "image": "video_frame",
            "json": None,
            "audio": "audio_chunk"
        }
        video_connections = []  # Input node
        
        self._simulate_node_update(video_id, video_connections, video_data)
        
        original_video_timestamp = self.node_image_dict.get_timestamp(video_id)
        original_audio_timestamp = self.node_audio_dict.get_timestamp(video_id)
        
        self.assertIsNotNone(original_video_timestamp)
        self.assertIsNotNone(original_audio_timestamp)
        
        time.sleep(0.01)
        
        # 2. Video processing node
        video_proc_id = "2:VideoEffect"
        video_proc_connections = [
            (f"{video_id}:IMAGE:Output01", f"{video_proc_id}:IMAGE:Input01")
        ]
        video_proc_data = {
            "image": "processed_video_frame",
            "json": None,
            "audio": None
        }
        
        self._simulate_node_update(video_proc_id, video_proc_connections, video_proc_data)
        
        # 3. Audio processing node
        audio_proc_id = "3:AudioEffect"
        audio_proc_connections = [
            (f"{video_id}:AUDIO:OutputAudio", f"{audio_proc_id}:AUDIO:InputAudio")
        ]
        audio_proc_data = {
            "image": None,
            "json": None,
            "audio": "processed_audio_chunk"
        }
        
        self._simulate_node_update(audio_proc_id, audio_proc_connections, audio_proc_data)
        
        # Verify timestamps are preserved separately for video and audio
        video_proc_timestamp = self.node_image_dict.get_timestamp(video_proc_id)
        audio_proc_timestamp = self.node_audio_dict.get_timestamp(audio_proc_id)
        
        self.assertEqual(original_video_timestamp, video_proc_timestamp,
                        "Video processing should preserve original video timestamp")
        self.assertEqual(original_audio_timestamp, audio_proc_timestamp,
                        "Audio processing should preserve original audio timestamp")
    
    def test_multiple_input_sources_independent_timestamps(self):
        """Test that different input nodes have independent timestamps."""
        # Two independent input sources
        webcam_id = "1:Webcam"
        video_id = "2:Video"
        
        # Webcam produces frame
        self._simulate_node_update(webcam_id, [], {
            "image": "webcam_frame",
            "json": None,
            "audio": None
        })
        webcam_timestamp = self.node_image_dict.get_timestamp(webcam_id)
        
        time.sleep(0.02)  # Ensure different timestamps
        
        # Video produces frame
        self._simulate_node_update(video_id, [], {
            "image": "video_frame",
            "json": None,
            "audio": None
        })
        video_timestamp = self.node_image_dict.get_timestamp(video_id)
        
        # Timestamps should be different
        self.assertNotEqual(webcam_timestamp, video_timestamp,
                           "Different input sources should have different timestamps")
        
        # Now process each through separate pipelines
        webcam_blur_id = "3:WebcamBlur"
        video_blur_id = "4:VideoBlur"
        
        self._simulate_node_update(webcam_blur_id, [
            (f"{webcam_id}:IMAGE:Output01", f"{webcam_blur_id}:IMAGE:Input01")
        ], {
            "image": "webcam_blurred",
            "json": None,
            "audio": None
        })
        
        self._simulate_node_update(video_blur_id, [
            (f"{video_id}:IMAGE:Output01", f"{video_blur_id}:IMAGE:Input01")
        ], {
            "image": "video_blurred",
            "json": None,
            "audio": None
        })
        
        # Each pipeline should preserve its source timestamp
        webcam_blur_timestamp = self.node_image_dict.get_timestamp(webcam_blur_id)
        video_blur_timestamp = self.node_image_dict.get_timestamp(video_blur_id)
        
        self.assertEqual(webcam_timestamp, webcam_blur_timestamp,
                        "Webcam pipeline should preserve webcam timestamp")
        self.assertEqual(video_timestamp, video_blur_timestamp,
                        "Video pipeline should preserve video timestamp")
        self.assertNotEqual(webcam_blur_timestamp, video_blur_timestamp,
                           "Different pipelines should maintain different timestamps")


if __name__ == "__main__":
    unittest.main()
