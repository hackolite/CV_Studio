#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration script for queue logging functionality.

This script demonstrates the logging of data insertions into buffer queues
with timestamp and data type information.
"""

import logging
import time
from node.timestamped_queue import TimestampedQueue, NodeDataQueueManager
from node.queue_adapter import QueueBackedDict

# Configure logging to display on console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def demo_timestamped_queue():
    """Demonstrate logging with TimestampedQueue."""
    print("\n" + "="*80)
    print("DEMO 1: TimestampedQueue Logging")
    print("="*80)
    
    queue = TimestampedQueue(maxsize=5, node_id="1:CameraNode")
    
    # Insert different types of data
    print("\nInserting string data...")
    queue.put("video_frame_001")
    time.sleep(0.1)
    
    print("\nInserting integer data...")
    queue.put(42)
    time.sleep(0.1)
    
    print("\nInserting list data...")
    queue.put([1, 2, 3, 4, 5])
    time.sleep(0.1)
    
    print("\nInserting dictionary data...")
    queue.put({"width": 1920, "height": 1080})
    time.sleep(0.1)

def demo_node_data_queue_manager():
    """Demonstrate logging with NodeDataQueueManager."""
    print("\n" + "="*80)
    print("DEMO 2: NodeDataQueueManager Logging")
    print("="*80)
    
    manager = NodeDataQueueManager(default_maxsize=10)
    
    print("\nSimulating video stream from camera...")
    for i in range(3):
        manager.put_data("1:Webcam", "image", f"frame_{i:03d}")
        time.sleep(0.05)
    
    print("\nSimulating audio stream from microphone...")
    for i in range(3):
        manager.put_data("2:Microphone", "audio", f"audio_chunk_{i:03d}")
        time.sleep(0.05)
    
    print("\nSimulating JSON metadata...")
    manager.put_data("3:MetadataNode", "json", {"fps": 30, "resolution": "1080p"})

def demo_queue_adapter():
    """Demonstrate logging with QueueBackedDict."""
    print("\n" + "="*80)
    print("DEMO 3: QueueBackedDict (Adapter) Logging")
    print("="*80)
    
    manager = NodeDataQueueManager(default_maxsize=10)
    
    # Create adapters for different data types
    image_dict = QueueBackedDict(manager, "image")
    audio_dict = QueueBackedDict(manager, "audio")
    result_dict = QueueBackedDict(manager, "result")
    
    print("\nSetting image data via adapter...")
    image_dict["1:LeftCamera"] = "left_frame_001"
    time.sleep(0.05)
    image_dict["2:RightCamera"] = "right_frame_001"
    time.sleep(0.05)
    
    print("\nSetting audio data via adapter...")
    audio_dict["1:BuiltInMic"] = "audio_sample_001"
    time.sleep(0.05)
    
    print("\nSetting result data via adapter...")
    result_dict["1:ObjectDetector"] = {"objects": ["person", "car", "dog"]}

def demo_realistic_scenario():
    """Demonstrate a realistic multi-stream scenario."""
    print("\n" + "="*80)
    print("DEMO 4: Realistic Multi-Stream Scenario")
    print("="*80)
    
    manager = NodeDataQueueManager(default_maxsize=10)
    
    print("\nSimulating synchronized video and audio capture...")
    base_time = time.time()
    
    for i in range(5):
        # Video frame
        frame_timestamp = base_time + (i * 0.033)  # 30 fps
        manager.put_data("1:VideoCapture", "image", 
                        f"video_frame_{i}", 
                        frame_timestamp)
        
        # Audio chunk (audio samples come faster)
        if i % 2 == 0:
            audio_timestamp = base_time + (i * 0.033)
            manager.put_data("2:AudioCapture", "audio", 
                            f"audio_chunk_{i//2}", 
                            audio_timestamp)
        
        time.sleep(0.04)  # Simulate real-time capture
    
    print("\nQueue statistics:")
    video_info = manager.get_queue_info("1:VideoCapture", "image")
    audio_info = manager.get_queue_info("2:AudioCapture", "audio")
    
    print(f"  Video queue: {video_info['size']} frames")
    print(f"  Audio queue: {audio_info['size']} chunks")

if __name__ == '__main__':
    print("\n" + "#"*80)
    print("# Queue Logging Demonstration")
    print("# This demonstrates logging of data insertions with timestamps and types")
    print("#"*80)
    
    demo_timestamped_queue()
    demo_node_data_queue_manager()
    demo_queue_adapter()
    demo_realistic_scenario()
    
    print("\n" + "#"*80)
    print("# Demonstration Complete")
    print("#"*80 + "\n")
