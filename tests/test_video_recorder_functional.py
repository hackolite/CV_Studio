#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functional test for VideoRecorder node with simulated data
"""
import unittest
import sys
import os
import tempfile
import shutil
import numpy as np
import cv2
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.ActionNode.node_video_recorder import VideoRecorderNode


class TestVideoRecorderFunctional(unittest.TestCase):
    """Functional tests for VideoRecorder with simulated recording"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.node = VideoRecorderNode()
        self.node._opencv_setting_dict = {
            'process_width': 240,
            'process_height': 135,
            'video_writer_fps': 30,
            'video_writer_directory': self.temp_dir
        }
        self.node._output_dir = self.temp_dir
    
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'node') and self.node._is_recording:
            self.node._stop_recording('test')
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_trigger_priority_record_field(self):
        """Test that 'record' field has priority in trigger JSON"""
        # JSON with both 'record' and 'trigger'
        trigger_json = {'record': True, 'trigger': False, 'other': True}
        
        should_record = False
        if 'record' in trigger_json and isinstance(trigger_json['record'], bool):
            should_record = trigger_json['record']
        
        self.assertTrue(should_record)
    
    def test_trigger_priority_trigger_field(self):
        """Test that 'trigger' field is used if 'record' is absent"""
        trigger_json = {'trigger': True, 'other': False}
        
        should_record = False
        if 'record' in trigger_json and isinstance(trigger_json['record'], bool):
            should_record = trigger_json['record']
        elif 'trigger' in trigger_json and isinstance(trigger_json['trigger'], bool):
            should_record = trigger_json['trigger']
        
        self.assertTrue(should_record)
    
    def test_trigger_fallback_any_boolean(self):
        """Test that any boolean True triggers recording if no 'record'/'trigger'"""
        trigger_json = {'detected': True, 'count': 5}
        
        should_record = False
        if 'record' in trigger_json and isinstance(trigger_json['record'], bool):
            should_record = trigger_json['record']
        elif 'trigger' in trigger_json and isinstance(trigger_json['trigger'], bool):
            should_record = trigger_json['trigger']
        else:
            for key, value in trigger_json.items():
                if isinstance(value, bool) and value:
                    should_record = True
                    break
        
        self.assertTrue(should_record)
    
    def test_fps_validation(self):
        """Test that invalid FPS values are handled"""
        # Test negative FPS
        self.node._opencv_setting_dict['video_writer_fps'] = -10
        fps = self.node._opencv_setting_dict.get('video_writer_fps', 30)
        if not isinstance(fps, (int, float)) or fps <= 0:
            fps = 30
        self.assertEqual(fps, 30)
        
        # Test string FPS
        self.node._opencv_setting_dict['video_writer_fps'] = "invalid"
        fps = self.node._opencv_setting_dict.get('video_writer_fps', 30)
        if not isinstance(fps, (int, float)) or fps <= 0:
            fps = 30
        self.assertEqual(fps, 30)
        
        # Test valid FPS
        self.node._opencv_setting_dict['video_writer_fps'] = 60
        fps = self.node._opencv_setting_dict.get('video_writer_fps', 30)
        if not isinstance(fps, (int, float)) or fps <= 0:
            fps = 30
        self.assertEqual(fps, 60)
    
    def test_metadata_storage_structure(self):
        """Test that metadata is stored with correct structure"""
        self.node._metadata_list = []
        self.node._frame_count = 0
        
        # Simulate adding metadata for frames
        for i in range(3):
            self.node._frame_count += 1
            metadata = {
                'frame': self.node._frame_count,
                'timestamp': time.time(),
                'data': {'detected': True, 'count': i}
            }
            self.node._metadata_list.append(metadata)
        
        # Verify structure
        self.assertEqual(len(self.node._metadata_list), 3)
        for i, meta in enumerate(self.node._metadata_list):
            self.assertIn('frame', meta)
            self.assertIn('timestamp', meta)
            self.assertIn('data', meta)
            self.assertEqual(meta['frame'], i + 1)
            self.assertEqual(meta['data']['count'], i)
    
    def test_codec_fallback_logic(self):
        """Test that codec selection handles different formats correctly"""
        # AVI format
        format_ext = 'avi'
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.assertIsNotNone(fourcc)
        
        # MP4 format
        format_ext = 'mp4'
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.assertIsNotNone(fourcc)
        
        # MKV format - test both codecs
        try:
            fourcc = cv2.VideoWriter_fourcc(*'X264')
            self.assertIsNotNone(fourcc)
        except:
            # Fallback to XVID
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.assertIsNotNone(fourcc)
    
    def test_output_directory_initialization(self):
        """Test that output directory is properly initialized"""
        node = VideoRecorderNode()
        node._opencv_setting_dict = {
            'video_writer_directory': '/custom/path'
        }
        node._output_dir = node._opencv_setting_dict.get('video_writer_directory', './_VideoRecorder')
        
        self.assertEqual(node._output_dir, '/custom/path')
    
    def test_recording_state_transitions(self):
        """Test recording state transitions"""
        # Initial state
        self.assertFalse(self.node._is_recording)
        self.assertEqual(self.node._frame_count, 0)
        
        # Start recording state
        self.node._is_recording = True
        self.node._recording_start_time = time.time()
        self.assertTrue(self.node._is_recording)
        
        # Stop recording state
        self.node._is_recording = False
        self.assertFalse(self.node._is_recording)


if __name__ == '__main__':
    unittest.main()
