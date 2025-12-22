#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that UI elements (input fields, sliders, buttons) are properly styled with node colors
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dearpygui.dearpygui as dpg
from node_editor.node_editor import node_style
from node_editor.style import STYLE


class TestUIElementStyling(unittest.TestCase):
    """Test that UI elements have proper color styling based on node category"""
    
    @classmethod
    def setUpClass(cls):
        """Set up DearPyGUI context once for all tests"""
        try:
            dpg.create_context()
        except Exception:
            # Context might already exist, that's ok
            pass
    
    def test_node_style_returns_theme(self):
        """Test that node_style function returns a valid theme"""
        for module_name in STYLE.keys():
            with self.subTest(module=module_name):
                theme = node_style(module_name)
                self.assertIsNotNone(theme, f"node_style should return a theme for {module_name}")
                self.assertIsInstance(theme, int, "Theme should be an integer ID")
    
    def test_input_nodes_have_yellow_theme(self):
        """Test that Input nodes have yellow pastel coloring"""
        theme = node_style("Input")
        self.assertIsNotNone(theme)
        # Verify the color is yellow pastel (255, 255, 153, 255)
        expected_color = STYLE["Input"]["style"][0]
        self.assertEqual(expected_color, (255, 255, 153, 255))
    
    def test_visionprocess_nodes_have_green_theme(self):
        """Test that VisionProcess nodes have green pastel coloring"""
        theme = node_style("VisionProcess")
        self.assertIsNotNone(theme)
        # Verify the color is green pastel (144, 238, 144, 255)
        expected_color = STYLE["VisionProcess"]["style"][0]
        self.assertEqual(expected_color, (144, 238, 144, 255))
    
    def test_visionmodel_nodes_have_peach_theme(self):
        """Test that VisionModel nodes have peach puff pastel coloring"""
        theme = node_style("VisionModel")
        self.assertIsNotNone(theme)
        # Verify the color is peach puff pastel (255, 218, 185, 255)
        expected_color = STYLE["VisionModel"]["style"][0]
        self.assertEqual(expected_color, (255, 218, 185, 255))
    
    def test_audioprocess_nodes_have_blue_theme(self):
        """Test that AudioProcess nodes have powder blue pastel coloring"""
        theme = node_style("AudioProcess")
        self.assertIsNotNone(theme)
        # Verify the color is powder blue pastel (176, 224, 230, 255)
        expected_color = STYLE["AudioProcess"]["style"][0]
        self.assertEqual(expected_color, (176, 224, 230, 255))
    
    def test_all_node_categories_have_themes(self):
        """Test that all node categories can create themes without errors"""
        categories = [
            "Input", "VisionProcess", "VisionModel", "AudioProcess", 
            "AudioModel", "DataProcess", "DataModel", "Trigger", 
            "Router", "Action", "Overlay", "Tracking", "Video", 
            "Visual", "System"
        ]
        
        for category in categories:
            with self.subTest(category=category):
                try:
                    theme = node_style(category)
                    self.assertIsNotNone(theme, f"Theme should be created for {category}")
                except Exception as e:
                    self.fail(f"Failed to create theme for {category}: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up DearPyGUI context"""
        try:
            dpg.destroy_context()
        except Exception:
            # Context might already be destroyed, that's ok
            pass


if __name__ == '__main__':
    unittest.main()
