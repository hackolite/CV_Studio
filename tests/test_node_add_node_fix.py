#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the fix of AttributeError in node_editor.py
Tests that Node.add_node() returns a Node instance with tag_node_name attribute
"""
import sys
import os
import unittest
from unittest import mock

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the DearPyGui module since we're not running a GUI
sys.modules['dearpygui'] = mock.MagicMock()
sys.modules['dearpygui.dearpygui'] = mock.MagicMock()


class TestNodeAddNodeReturnValue(unittest.TestCase):
    """Test that Node.add_node() methods return Node instances, not strings"""
    
    def setUp(self):
        """Set up common test fixtures"""
        self.opencv_setting_dict = {
            'process_width': 640,
            'process_height': 480,
            'result_width': 320,
            'result_height': 240,
            'use_pref_counter': False,
            'use_gpu': False,
            'draw_info_on_result': False,
        }
    
    def test_classification_node_returns_instance(self):
        """Test that Classification Node returns instance with tag_node_name"""
        from node.DLNode.node_classification import FactoryNode
        
        factory = FactoryNode()
        # Mock parent to avoid GUI issues
        with mock.patch('dearpygui.dearpygui.node'), \
             mock.patch('dearpygui.dearpygui.node_attribute'), \
             mock.patch('dearpygui.dearpygui.texture_registry'), \
             mock.patch('dearpygui.dearpygui.add_raw_texture'), \
             mock.patch('dearpygui.dearpygui.add_text'), \
             mock.patch('dearpygui.dearpygui.add_image'), \
             mock.patch('dearpygui.dearpygui.add_radio_button'), \
             mock.patch('dearpygui.dearpygui.add_slider_int'):
            
            result = factory.add_node(
                parent='test_parent',
                node_id=1,
                pos=[0, 0],
                opencv_setting_dict=self.opencv_setting_dict
            )
            
            # Verify result is not a string
            self.assertNotIsInstance(result, str, 
                "Node.add_node() should not return a string")
            
            # Verify result has tag_node_name attribute
            self.assertTrue(hasattr(result, 'tag_node_name'),
                "Returned object should have 'tag_node_name' attribute")
            
            # Verify tag_node_name is a string
            self.assertIsInstance(result.tag_node_name, str,
                "tag_node_name attribute should be a string")
    
    def test_semantic_segmentation_node_returns_instance(self):
        """Test that Semantic Segmentation Node returns instance with tag_node_name"""
        from node.DLNode.node_semantic_segmentation import FactoryNode
        
        factory = FactoryNode()
        with mock.patch('dearpygui.dearpygui.node'), \
             mock.patch('dearpygui.dearpygui.node_attribute'), \
             mock.patch('dearpygui.dearpygui.texture_registry'), \
             mock.patch('dearpygui.dearpygui.add_raw_texture'), \
             mock.patch('dearpygui.dearpygui.add_text'), \
             mock.patch('dearpygui.dearpygui.add_image'), \
             mock.patch('dearpygui.dearpygui.add_radio_button'), \
             mock.patch('dearpygui.dearpygui.add_slider_float'):
            
            result = factory.add_node(
                parent='test_parent',
                node_id=2,
                pos=[0, 0],
                opencv_setting_dict=self.opencv_setting_dict
            )
            
            self.assertNotIsInstance(result, str)
            self.assertTrue(hasattr(result, 'tag_node_name'))
            self.assertIsInstance(result.tag_node_name, str)
    
    def test_simple_filter_node_returns_instance(self):
        """Test that Simple Filter Node returns instance with tag_node_name"""
        from node.ProcessNode.node_simple_filter import FactoryNode
        
        factory = FactoryNode()
        with mock.patch('dearpygui.dearpygui.node'), \
             mock.patch('dearpygui.dearpygui.node_attribute'), \
             mock.patch('dearpygui.dearpygui.texture_registry'), \
             mock.patch('dearpygui.dearpygui.add_raw_texture'), \
             mock.patch('dearpygui.dearpygui.add_text'), \
             mock.patch('dearpygui.dearpygui.add_image'), \
             mock.patch('dearpygui.dearpygui.add_slider_float'), \
             mock.patch('node_editor.util.convert_cv_to_dpg', return_value=[]):
            
            result = factory.add_node(
                parent='test_parent',
                node_id=3,
                pos=[0, 0],
                opencv_setting_dict=self.opencv_setting_dict
            )
            
            self.assertNotIsInstance(result, str)
            self.assertTrue(hasattr(result, 'tag_node_name'))
            self.assertIsInstance(result.tag_node_name, str)
    
    def test_on_off_switch_node_returns_instance(self):
        """Test that On/Off Switch Node returns instance with tag_node_name"""
        from node.TriggerNode.node_on_off_switch import FactoryNode
        
        factory = FactoryNode()
        with mock.patch('dearpygui.dearpygui.node'), \
             mock.patch('dearpygui.dearpygui.node_attribute'), \
             mock.patch('dearpygui.dearpygui.texture_registry'), \
             mock.patch('dearpygui.dearpygui.add_raw_texture'), \
             mock.patch('dearpygui.dearpygui.add_text'), \
             mock.patch('dearpygui.dearpygui.add_image'), \
             mock.patch('dearpygui.dearpygui.add_radio_button'), \
             mock.patch('node_editor.util.convert_cv_to_dpg', return_value=[]):
            
            result = factory.add_node(
                parent='test_parent',
                node_id=4,
                pos=[0, 0],
                opencv_setting_dict=self.opencv_setting_dict
            )
            
            self.assertNotIsInstance(result, str)
            self.assertTrue(hasattr(result, 'tag_node_name'))
            self.assertIsInstance(result.tag_node_name, str)
    
    def test_trigger_node_returns_instance(self):
        """Test that Trigger Node returns instance with tag_node_name"""
        from node.TriggerNode.node_trigger import FactoryNode
        
        factory = FactoryNode()
        with mock.patch('dearpygui.dearpygui.node'), \
             mock.patch('dearpygui.dearpygui.node_attribute'), \
             mock.patch('dearpygui.dearpygui.texture_registry'), \
             mock.patch('dearpygui.dearpygui.add_raw_texture'), \
             mock.patch('dearpygui.dearpygui.add_text'), \
             mock.patch('dearpygui.dearpygui.add_image'), \
             mock.patch('dearpygui.dearpygui.add_button'), \
             mock.patch('node_editor.util.convert_cv_to_dpg', return_value=[]):
            
            result = factory.add_node(
                parent='test_parent',
                node_id=5,
                pos=[0, 0],
                opencv_setting_dict=self.opencv_setting_dict
            )
            
            self.assertNotIsInstance(result, str)
            self.assertTrue(hasattr(result, 'tag_node_name'))
            self.assertIsInstance(result.tag_node_name, str)
    
    def test_draw_information_node_returns_instance(self):
        """Test that Draw Information Node returns instance with tag_node_name"""
        from node.OverlayNode.node_draw_information import FactoryNode
        
        factory = FactoryNode()
        with mock.patch('dearpygui.dearpygui.node'), \
             mock.patch('dearpygui.dearpygui.node_attribute'), \
             mock.patch('dearpygui.dearpygui.texture_registry'), \
             mock.patch('dearpygui.dearpygui.add_raw_texture'), \
             mock.patch('dearpygui.dearpygui.add_text'), \
             mock.patch('dearpygui.dearpygui.add_image'), \
             mock.patch('node_editor.util.convert_cv_to_dpg', return_value=[]):
            
            result = factory.add_node(
                parent='test_parent',
                node_id=6,
                pos=[0, 0],
                opencv_setting_dict=self.opencv_setting_dict
            )
            
            self.assertNotIsInstance(result, str)
            self.assertTrue(hasattr(result, 'tag_node_name'))
            self.assertIsInstance(result.tag_node_name, str)


if __name__ == '__main__':
    unittest.main()
