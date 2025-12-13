#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that Video node displays both current queue size and maxsize.

This test verifies that the Video node displays both:
- Current number of elements in the queue (size)
- Maximum queue capacity (maxsize)

Format: "Queue: Image={size}/{maxsize} Audio={size}/{maxsize}"
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.timestamped_queue import NodeDataQueueManager


class TestVideoQueueSizeAndMaxsizeDisplay(unittest.TestCase):
    """Test that video node displays both size and maxsize"""
    
    def test_queue_info_returns_both_size_and_maxsize(self):
        """Test that get_queue_info returns both size and maxsize"""
        manager = NodeDataQueueManager(default_maxsize=100)
        
        # Add some data to the queue
        manager.put_data("1:Video", "image", "frame1")
        manager.put_data("1:Video", "image", "frame2")
        manager.put_data("1:Video", "image", "frame3")
        
        # Get queue info
        info = manager.get_queue_info("1:Video", "image")
        
        # Verify both size and maxsize are present
        self.assertTrue(info.get("exists", False))
        self.assertEqual(info.get("size", 0), 3, "Should have 3 items")
        self.assertEqual(info.get("maxsize", 0), 100, "Should have maxsize of 100")
        
        print(f"✓ Queue info includes both: size={info['size']}, maxsize={info['maxsize']}")
    
    def test_queue_display_format_in_code(self):
        """Test that video node code uses the correct display format"""
        video_node_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py'
        )
        
        with open(video_node_path, 'r') as f:
            content = f.read()
        
        # Check that both size and maxsize are retrieved
        self.assertIn('image_queue_size', content, "Should retrieve image queue size")
        self.assertIn('image_queue_maxsize', content, "Should retrieve image queue maxsize")
        self.assertIn('audio_queue_size', content, "Should retrieve audio queue size")
        self.assertIn('audio_queue_maxsize', content, "Should retrieve audio queue maxsize")
        
        # Check that the display format includes both size and maxsize
        # Format should be: "Queue: Image={size}/{maxsize} Audio={size}/{maxsize}"
        self.assertIn('image_queue_size}/{image_queue_maxsize}', content, 
                     "Display format should be 'Image={size}/{maxsize}'")
        self.assertIn('audio_queue_size}/{audio_queue_maxsize}', content,
                     "Display format should be 'Audio={size}/{maxsize}'")
        
        print("✓ Video node code uses correct display format")
        print("  - Retrieves both size and maxsize for image queue")
        print("  - Retrieves both size and maxsize for audio queue")
        print("  - Display format: 'Queue: Image={size}/{maxsize} Audio={size}/{maxsize}'")
    
    def test_multiple_queues_different_sizes(self):
        """Test that different queues can have different sizes and maxsizes"""
        manager = NodeDataQueueManager(default_maxsize=800)
        
        # Resize queues to different sizes
        manager.resize_queue("1:Video", "image", 240)
        manager.resize_queue("1:Video", "audio", 4)
        
        # Add different amounts of data
        for i in range(10):
            manager.put_data("1:Video", "image", f"frame{i}")
        
        for i in range(2):
            manager.put_data("1:Video", "audio", f"chunk{i}")
        
        # Get queue info
        image_info = manager.get_queue_info("1:Video", "image")
        audio_info = manager.get_queue_info("1:Video", "audio")
        
        # Verify image queue: 10 items, maxsize 240
        self.assertEqual(image_info.get("size", 0), 10)
        self.assertEqual(image_info.get("maxsize", 0), 240)
        
        # Verify audio queue: 2 items, maxsize 4
        self.assertEqual(audio_info.get("size", 0), 2)
        self.assertEqual(audio_info.get("maxsize", 0), 4)
        
        print(f"✓ Different queues have different sizes:")
        print(f"  - Image queue: {image_info['size']}/{image_info['maxsize']}")
        print(f"  - Audio queue: {audio_info['size']}/{audio_info['maxsize']}")


if __name__ == "__main__":
    unittest.main()
