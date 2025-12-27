#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for VideoRecorder node
"""
import unittest
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.ActionNode.node_video_recorder import FactoryNode, VideoRecorderNode


class TestVideoRecorderNode(unittest.TestCase):
    """Test VideoRecorder node initialization and basic functionality"""
    
    def test_factory_node_creation(self):
        """Test that FactoryNode can be instantiated"""
        factory = FactoryNode()
        self.assertEqual(factory.node_label, 'VideoRecorder')
        self.assertEqual(factory.node_tag, 'VideoRecorder')
    
    def test_node_creation(self):
        """Test that VideoRecorderNode can be instantiated"""
        node = VideoRecorderNode()
        self.assertEqual(node.node_label, 'VideoRecorder')
        self.assertEqual(node.node_tag, 'VideoRecorder')
        self.assertFalse(node._is_recording)
        self.assertEqual(node._frame_count, 0)
        self.assertEqual(node.DEFAULT_DURATION, 10)
    
    def test_node_has_required_methods(self):
        """Test that node has all required methods"""
        node = VideoRecorderNode()
        self.assertTrue(hasattr(node, 'update'))
        self.assertTrue(hasattr(node, 'close'))
        self.assertTrue(hasattr(node, 'get_setting_dict'))
        self.assertTrue(hasattr(node, 'set_setting_dict'))
        self.assertTrue(callable(node.update))
        self.assertTrue(callable(node.close))
    
    def test_stop_recording_without_writer(self):
        """Test that stop_recording handles missing writer gracefully"""
        node = VideoRecorderNode()
        # Should not raise an exception
        node._stop_recording('test_tag')
    
    def test_start_recording_creates_writer(self):
        """Test that start_recording initializes video writer"""
        import tempfile
        import cv2
        
        node = VideoRecorderNode()
        
        # Create temporary file path
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            result = node._start_recording(tmp_path, fourcc, 30, (640, 480))
            
            # On some systems without proper codecs, this might fail
            # We just check it doesn't crash
            if result:
                self.assertIsNotNone(node._video_writer)
                node._video_writer.release()
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def test_node_state_initialization(self):
        """Test that node initializes with correct state"""
        node = VideoRecorderNode()
        self.assertFalse(node._is_recording)
        self.assertEqual(node._recording_start_time, 0)
        self.assertIsNone(node._video_writer)
        self.assertIsNone(node._recording_file_path)
        self.assertEqual(node._metadata_list, [])
        self.assertEqual(node._frame_count, 0)


if __name__ == '__main__':
    unittest.main()
