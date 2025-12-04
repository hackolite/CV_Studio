#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test simulating the node_editor initialization flow
This test replicates the exact scenario from the error traceback to ensure the fix works
"""
import unittest
import sys
import os
from collections import OrderedDict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node_editor.style import STYLE


class TestNodeEditorInitialization(unittest.TestCase):
    """Test that simulates the node editor initialization flow"""
    
    def setUp(self):
        """Set up the menu_dict as defined in main.py"""
        self.menu_dict = OrderedDict({
            "Input": "InputNode",
            "VisionProcess": "ProcessNode",
            "VisionModel": "DLNode",
            "AudioProcess": "AudioProcessNode",
            "AudioModel": "AudioModelNode",
            "DataProcess": "StatsNode",
            "DataModel": "TimeseriesNode",
            "Trigger": "TriggerNode",
            "Router": "RouterNode",
            "Action": "ActionNode",
            "Overlay": "OverlayNode",
            "Tracking": "TrackerNode",
            "Visual": "VisualNode",
            "Video": "VideoNode",
            "System": "SystemNode",  # This was causing the KeyError
        })
    
    def test_simulate_node_style_lookup(self):
        """Simulate the node_style function call for all menu labels"""
        # This simulates the exact code path that was failing:
        # Line 196 in node_editor.py: factorynode.style = node_style(menu_label)
        # Line 25 in node_editor.py: tuple_style = STYLE[module_name]["style"][0]
        
        for menu_label in self.menu_dict.keys():
            with self.subTest(menu_label=menu_label):
                try:
                    # This is the exact lookup that was failing
                    tuple_style = STYLE[menu_label]["style"][0]
                    
                    # Verify it returns a valid RGBA tuple
                    self.assertIsInstance(tuple_style, tuple,
                                        f"{menu_label} style must be a tuple")
                    self.assertEqual(len(tuple_style), 4,
                                   f"{menu_label} style must have 4 values (RGBA)")
                    
                    # Verify all values are valid color components
                    for i, value in enumerate(tuple_style):
                        self.assertIsInstance(value, int,
                                            f"{menu_label} color component {i} must be int")
                        self.assertGreaterEqual(value, 0,
                                              f"{menu_label} color component {i} must be >= 0")
                        self.assertLessEqual(value, 255,
                                           f"{menu_label} color component {i} must be <= 255")
                    
                except KeyError as e:
                    self.fail(f"KeyError raised for menu_label '{menu_label}': {e}")
    
    def test_system_menu_specifically(self):
        """Specifically test the System menu that was causing the original error"""
        menu_label = "System"
        
        # This should not raise KeyError
        tuple_style = STYLE[menu_label]["style"][0]
        
        # Verify it's a valid color
        self.assertEqual(tuple_style, (192, 192, 192, 255),
                        "System style should be silver gray pastel")


if __name__ == '__main__':
    unittest.main()
