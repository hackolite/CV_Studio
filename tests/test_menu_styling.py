#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that menu_style function creates valid themes for menu items
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dearpygui.dearpygui as dpg
from node_editor.node_editor import menu_style
from node_editor.style import STYLE


class TestMenuStyling(unittest.TestCase):
    """Test that menu_style function works for all categories"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize DearPyGUI context once for all tests"""
        dpg.create_context()
    
    @classmethod
    def tearDownClass(cls):
        """Cleanup DearPyGUI context"""
        try:
            dpg.destroy_context()
        except Exception:
            pass
    
    def test_menu_style_returns_theme(self):
        """Test that menu_style function returns a valid theme for all categories"""
        for module_name in STYLE.keys():
            with self.subTest(module_name=module_name):
                theme = menu_style(module_name)
                self.assertIsNotNone(theme, f"menu_style should return a theme for {module_name}")
    
    def test_menu_style_for_input_category(self):
        """Test menu style for Input category"""
        theme = menu_style("Input")
        self.assertIsNotNone(theme)
    
    def test_menu_style_for_visionprocess_category(self):
        """Test menu style for VisionProcess category"""
        theme = menu_style("VisionProcess")
        self.assertIsNotNone(theme)
    
    def test_menu_style_for_visionmodel_category(self):
        """Test menu style for VisionModel category"""
        theme = menu_style("VisionModel")
        self.assertIsNotNone(theme)
    
    def test_menu_style_for_audioprocess_category(self):
        """Test menu style for AudioProcess category"""
        theme = menu_style("AudioProcess")
        self.assertIsNotNone(theme)
    
    def test_all_standard_categories(self):
        """Test that menu_style works for all standard categories"""
        standard_categories = [
            "Input",
            "VisionProcess", 
            "VisionModel",
            "AudioProcess",
            "AudioModel",
            "DataProcess",
            "DataModel",
            "Trigger",
            "Router",
            "Action",
            "Overlay",
            "Tracking",
            "Visual",
            "Video",
            "System",
        ]
        
        for category in standard_categories:
            with self.subTest(category=category):
                try:
                    theme = menu_style(category)
                    self.assertIsNotNone(theme, f"Theme should be created for {category}")
                except KeyError as e:
                    self.fail(f"KeyError when creating menu_style for {category}: {e}")


if __name__ == '__main__':
    unittest.main()
