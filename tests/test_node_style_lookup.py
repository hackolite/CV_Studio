#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that node_style function can be called with 'System' without KeyError
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node_editor.style import STYLE


class TestNodeStyleFunction(unittest.TestCase):
    """Test that node_style function works with System menu label"""
    
    def test_system_lookup_in_style(self):
        """Test that looking up 'System' in STYLE doesn't raise KeyError"""
        # This simulates the operation that was failing in node_style function
        try:
            tuple_style = STYLE["System"]["style"][0]
            # If we get here, no KeyError was raised
            self.assertTrue(True)
        except KeyError as e:
            self.fail(f"KeyError raised when accessing STYLE['System']: {e}")
    
    def test_all_menu_labels_in_style(self):
        """Test that all expected menu labels exist in STYLE"""
        # These are the menu labels from main.py menu_dict
        expected_labels = [
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
            "System",  # This was missing and causing the KeyError
        ]
        
        for label in expected_labels:
            with self.subTest(label=label):
                self.assertIn(label, STYLE,
                              f"Menu label '{label}' must exist in STYLE dictionary")
                # Also verify the structure
                self.assertIn("style", STYLE[label],
                              f"Menu label '{label}' must have 'style' key")
                self.assertIn("names", STYLE[label],
                              f"Menu label '{label}' must have 'names' key")
                self.assertEqual(len(STYLE[label]["style"]), 1,
                                f"Menu label '{label}' style must have exactly one color tuple")


if __name__ == '__main__':
    unittest.main()
