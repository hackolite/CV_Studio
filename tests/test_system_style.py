#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that System entry exists in STYLE dictionary to prevent KeyError
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node_editor.style import STYLE


class TestSystemStyle(unittest.TestCase):
    """Test that System style is properly defined"""
    
    def test_system_key_exists(self):
        """Test that 'System' key exists in STYLE dictionary"""
        self.assertIn('System', STYLE, 
                      "System key must exist in STYLE dictionary to prevent KeyError")
    
    def test_system_has_names(self):
        """Test that System entry has 'names' key"""
        self.assertIn('names', STYLE['System'],
                      "System entry must have 'names' key")
    
    def test_system_has_style(self):
        """Test that System entry has 'style' key"""
        self.assertIn('style', STYLE['System'],
                      "System entry must have 'style' key")
    
    def test_system_style_format(self):
        """Test that System style is in correct format (list with RGBA tuple)"""
        style = STYLE['System']['style']
        self.assertIsInstance(style, list, "Style must be a list")
        self.assertEqual(len(style), 1, "Style must contain exactly one color tuple")
        
        color = style[0]
        self.assertIsInstance(color, tuple, "Color must be a tuple")
        self.assertEqual(len(color), 4, "Color tuple must have 4 values (RGBA)")
        
        # Check all values are integers between 0 and 255
        for value in color:
            self.assertIsInstance(value, int, "Color values must be integers")
            self.assertGreaterEqual(value, 0, "Color values must be >= 0")
            self.assertLessEqual(value, 255, "Color values must be <= 255")
    
    def test_system_names_list(self):
        """Test that System names is a list"""
        names = STYLE['System']['names']
        self.assertIsInstance(names, list, "Names must be a list")
        self.assertGreater(len(names), 0, "Names list should not be empty")
        
    def test_syncqueue_in_system_names(self):
        """Test that SyncQueue is in System names"""
        names = STYLE['System']['names']
        self.assertIn('SyncQueue', names,
                      "SyncQueue should be in System names list")


if __name__ == '__main__':
    unittest.main()
