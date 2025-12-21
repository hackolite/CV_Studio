#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for VideoWriter crash fix when stopping recording.
This test verifies that error handling prevents crashes during stop operation.
"""

import unittest
import tempfile
import os
import sys
import shutil
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies before importing the module
sys.modules['cv2'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['dearpygui'] = MagicMock()
sys.modules['dearpygui.dearpygui'] = MagicMock()
sys.modules['node_editor'] = MagicMock()
sys.modules['node_editor.util'] = MagicMock()
sys.modules['node.node_abc'] = MagicMock()
sys.modules['ffmpeg'] = MagicMock()
sys.modules['soundfile'] = MagicMock()

# Mock base node to allow instantiation
class MockNode:
    TYPE_IMAGE = 'Image'
    TYPE_TEXT = 'Text'
    
    def convert_cv_to_dpg(self, *args, **kwargs):
        return []

sys.modules['node.basenode'] = MagicMock()
sys.modules['node.basenode'].Node = MockNode

# Now import after mocking
from node.VideoNode.node_video_writer import VideoWriterNode


class TestVideoWriterStopCrashFix(unittest.TestCase):
    """Test cases for VideoWriter stop crash fix"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.node = VideoWriterNode()
        self.test_dir = tempfile.mkdtemp()
        self.tag_node_name = "test_node:VideoWriter"
        
        # Mock opencv_setting_dict
        self.node._opencv_setting_dict = {
            'video_writer_width': 1280,
            'video_writer_height': 720,
            'video_writer_fps': 30,
            'video_writer_directory': self.test_dir
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_stop_with_failed_video_writer_release(self):
        """Test that stop handles VideoWriter.release() failure gracefully"""
        # Create a mock video writer that fails on release
        mock_writer = Mock()
        mock_writer.release.side_effect = Exception("Release failed")
        
        # Add to dict
        self.node._video_writer_dict[self.tag_node_name] = mock_writer
        self.node._recording_metadata_dict[self.tag_node_name] = {
            'final_path': os.path.join(self.test_dir, 'test.mp4'),
            'temp_path': os.path.join(self.test_dir, 'test_temp.mp4'),
            'format': 'MP4',
            'sample_rate': 22050
        }
        
        # Mock dpg functions - need to patch at module level
        import node.VideoNode.node_video_writer as nvw
        with patch.object(nvw.dpg, 'get_item_label', return_value='Stop'):
            with patch.object(nvw.dpg, 'set_item_label'):
                with patch.object(nvw.dpg, 'does_item_exist', return_value=True):
                    # This should NOT crash even though release() fails
                    try:
                        self.node._recording_button(None, None, self.tag_node_name)
                    except Exception as e:
                        self.fail(f"_recording_button crashed: {e}")
        
        # Verify cleanup happened despite error
        self.assertNotIn(self.tag_node_name, self.node._video_writer_dict)
    
    def test_stop_with_missing_temp_file(self):
        """Test that stop handles missing temp file gracefully"""
        # Create recording metadata but no actual temp file
        self.node._recording_metadata_dict[self.tag_node_name] = {
            'final_path': os.path.join(self.test_dir, 'test.mp4'),
            'temp_path': os.path.join(self.test_dir, 'nonexistent_temp.mp4'),
            'format': 'MP4',
            'sample_rate': 22050
        }
        
        # Mock dpg functions - need to patch at module level
        import node.VideoNode.node_video_writer as nvw
        with patch.object(nvw.dpg, 'get_item_label', return_value='Stop'):
            with patch.object(nvw.dpg, 'set_item_label'):
                with patch.object(nvw.dpg, 'does_item_exist', return_value=True):
                    # This should NOT crash even though file doesn't exist
                    try:
                        self.node._recording_button(None, None, self.tag_node_name)
                    except Exception as e:
                        self.fail(f"_recording_button crashed: {e}")
        
        # Verify cleanup happened
        self.assertNotIn(self.tag_node_name, self.node._recording_metadata_dict)
    
    def test_stop_with_file_rename_error(self):
        """Test that stop handles file rename failure gracefully"""
        # Create a temp file
        temp_path = os.path.join(self.test_dir, 'test_temp.mp4')
        with open(temp_path, 'w') as f:
            f.write('test')
        
        # Create recording metadata
        self.node._recording_metadata_dict[self.tag_node_name] = {
            'final_path': '/invalid/path/test.mp4',  # Invalid path for rename
            'temp_path': temp_path,
            'format': 'MP4',
            'sample_rate': 22050
        }
        
        # Mock dpg functions - need to patch at module level
        import node.VideoNode.node_video_writer as nvw
        with patch.object(nvw.dpg, 'get_item_label', return_value='Stop'):
            with patch.object(nvw.dpg, 'set_item_label'):
                with patch.object(nvw.dpg, 'does_item_exist', return_value=True):
                    # This should NOT crash even though rename fails
                    try:
                        self.node._recording_button(None, None, self.tag_node_name)
                    except Exception as e:
                        self.fail(f"_recording_button crashed: {e}")
        
        # Verify cleanup happened
        self.assertNotIn(self.tag_node_name, self.node._recording_metadata_dict)
    
    def test_stop_with_metadata_handles_error(self):
        """Test that stop handles metadata file handle errors gracefully"""
        # Create mock file handles that fail on close
        mock_handle = Mock()
        mock_handle.closed = False
        mock_handle.close.side_effect = Exception("Close failed")
        
        # Add to metadata dict
        self.node._mkv_metadata_dict[self.tag_node_name] = {
            'audio_handles': {0: mock_handle},
            'json_handles': {0: mock_handle},
            'file_path': os.path.join(self.test_dir, 'test.mkv')
        }
        
        # Mock dpg functions - need to patch at module level
        import node.VideoNode.node_video_writer as nvw
        with patch.object(nvw.dpg, 'get_item_label', return_value='Stop'):
            with patch.object(nvw.dpg, 'set_item_label'):
                with patch.object(nvw.dpg, 'does_item_exist', return_value=True):
                    # This should NOT crash even though close fails
                    try:
                        self.node._recording_button(None, None, self.tag_node_name)
                    except Exception as e:
                        self.fail(f"_recording_button crashed: {e}")
        
        # Verify cleanup happened
        self.assertNotIn(self.tag_node_name, self.node._mkv_metadata_dict)
    
    def test_close_with_active_video_writer_error(self):
        """Test that close() handles VideoWriter.release() error gracefully"""
        # Create a mock video writer that fails on release
        mock_writer = Mock()
        mock_writer.release.side_effect = Exception("Release failed")
        
        # Add to dict
        self.node._video_writer_dict[self.tag_node_name] = mock_writer
        
        # This should NOT crash
        try:
            self.node.close("test_node")
        except Exception as e:
            self.fail(f"close() crashed: {e}")
        
        # Verify cleanup happened
        self.assertNotIn(self.tag_node_name, self.node._video_writer_dict)
    
    def test_close_with_metadata_error(self):
        """Test that close() handles metadata cleanup error gracefully"""
        # Create mock file handles that fail on close
        mock_handle = Mock()
        mock_handle.closed = False
        mock_handle.close.side_effect = Exception("Close failed")
        
        # Add to metadata dict
        self.node._mkv_metadata_dict[self.tag_node_name] = {
            'audio_handles': {0: mock_handle},
            'json_handles': {},
            'file_path': os.path.join(self.test_dir, 'test.mkv')
        }
        
        # This should NOT crash
        try:
            self.node.close("test_node")
        except Exception as e:
            self.fail(f"close() crashed: {e}")
        
        # Verify cleanup happened
        self.assertNotIn(self.tag_node_name, self.node._mkv_metadata_dict)
    
    def test_close_metadata_handles_with_errors(self):
        """Test that _close_metadata_handles handles errors gracefully"""
        # Create mock file handles that fail on close
        mock_audio_handle = Mock()
        mock_audio_handle.closed = False
        mock_audio_handle.close.side_effect = Exception("Audio close failed")
        
        mock_json_handle = Mock()
        mock_json_handle.closed = False
        mock_json_handle.close.side_effect = Exception("JSON close failed")
        
        metadata = {
            'audio_handles': {0: mock_audio_handle},
            'json_handles': {0: mock_json_handle},
            'file_path': os.path.join(self.test_dir, 'test.mkv')
        }
        
        # This should NOT crash
        try:
            self.node._close_metadata_handles(metadata)
        except Exception as e:
            self.fail(f"_close_metadata_handles crashed: {e}")
    
    def test_stop_with_dpg_error(self):
        """Test that stop handles DearPyGUI errors gracefully"""
        # Create recording metadata
        self.node._recording_metadata_dict[self.tag_node_name] = {
            'final_path': os.path.join(self.test_dir, 'test.mp4'),
            'temp_path': os.path.join(self.test_dir, 'test_temp.mp4'),
            'format': 'MP4',
            'sample_rate': 22050
        }
        
        # Mock dpg functions to fail - need to patch at module level
        import node.VideoNode.node_video_writer as nvw
        with patch.object(nvw.dpg, 'get_item_label', return_value='Stop'):
            with patch.object(nvw.dpg, 'set_item_label', side_effect=Exception("DPG error")):
                with patch.object(nvw.dpg, 'does_item_exist', return_value=True):
                    # This should NOT crash even though dpg.set_item_label fails
                    try:
                        self.node._recording_button(None, None, self.tag_node_name)
                    except Exception as e:
                        self.fail(f"_recording_button crashed: {e}")
        
        # Verify cleanup happened
        self.assertNotIn(self.tag_node_name, self.node._recording_metadata_dict)


def run_tests():
    """Run all tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestVideoWriterStopCrashFix)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    if success:
        print("\n✅ All VideoWriter stop crash fix tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
