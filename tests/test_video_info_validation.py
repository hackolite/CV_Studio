#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for video info validation.

This test verifies that the _get_video_info() method properly validates
video paths before attempting to extract metadata with ffprobe.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestVideoInfoValidation(unittest.TestCase):
    """Test video info validation"""
    
    @staticmethod
    def _get_method_source(method_name):
        """Helper to extract source code for a specific method from node_video.py"""
        node_video_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py'
        )
        
        with open(node_video_path, 'r') as f:
            content = f.read()
        
        # Find the method start
        start_marker = f'def {method_name}(self'
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return None
        
        # Find the next method definition (end of current method)
        # Look for the next 'def ' at the same indentation level
        end_idx = content.find('\n    def ', start_idx + 1)
        if end_idx == -1:
            # If no next method, look for class end or file end
            end_idx = content.find('\nclass ', start_idx + 1)
            if end_idx == -1:
                end_idx = len(content)
        
        return content[start_idx:end_idx]
    
    def test_get_video_info_has_validation(self):
        """Verify that _get_video_info validates the video path"""
        method_source = self._get_method_source('_get_video_info')
        self.assertIsNotNone(method_source, "_get_video_info method not found")
        
        # Check for validation
        self.assertIn('os.path.isfile', method_source,
                     "_get_video_info should validate file path with os.path.isfile")
        self.assertIn('Invalid video path', method_source,
                     "_get_video_info should log error for invalid paths")
    
    def test_get_video_info_improved_error_messages(self):
        """Verify that _get_video_info has improved error messages"""
        method_source = self._get_method_source('_get_video_info')
        self.assertIsNotNone(method_source, "_get_video_info method not found")
        
        # Check that video_path is included in error messages
        # Look for logger.warning calls that include video_path
        lines = method_source.split('\n')
        warning_lines = [line for line in lines if 'logger.warning' in line]
        
        # At least some warning messages should include the video path for context
        has_video_path_in_warnings = any('video_path' in line for line in warning_lines)
        self.assertTrue(has_video_path_in_warnings,
                       "_get_video_info should include video_path in warning messages")
    
    def test_start_ffmpeg_reader_error_message(self):
        """Verify that _start_ffmpeg_reader has helpful error message"""
        method_source = self._get_method_source('_start_ffmpeg_reader')
        self.assertIsNotNone(method_source, "_start_ffmpeg_reader method not found")
        
        # Check for improved error message
        self.assertIn('Check if the file exists', method_source,
                     "_start_ffmpeg_reader should provide helpful guidance in error message")


if __name__ == '__main__':
    unittest.main()
