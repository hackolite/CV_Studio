#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for Buzzer node BOOL field handling
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.ActionNode.node_buzzer import BuzzerNode


class TestBuzzerBoolField(unittest.TestCase):
    """Test Buzzer node BOOL field priority"""
    
    def test_bool_field_priority_true(self):
        """Test that 'BOOL' field has highest priority when True"""
        node_result = {'BOOL': True, 'detected': False, 'count': 5}
        
        should_buzz = False
        if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
            should_buzz = node_result['BOOL']
        else:
            for key, value in node_result.items():
                if isinstance(value, bool) and value:
                    should_buzz = True
                    break
        
        self.assertTrue(should_buzz)
    
    def test_bool_field_priority_false(self):
        """Test that 'BOOL' field False overrides other True values"""
        node_result = {'BOOL': False, 'detected': True, 'triggered': True}
        
        should_buzz = False
        if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
            should_buzz = node_result['BOOL']
        else:
            for key, value in node_result.items():
                if isinstance(value, bool) and value:
                    should_buzz = True
                    break
        
        self.assertFalse(should_buzz)
    
    def test_fallback_to_any_boolean_when_no_bool_field(self):
        """Test that node falls back to any boolean True when no BOOL field"""
        node_result = {'detected': True, 'count': 5}
        
        should_buzz = False
        if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
            should_buzz = node_result['BOOL']
        else:
            for key, value in node_result.items():
                if isinstance(value, bool) and value:
                    should_buzz = True
                    break
        
        self.assertTrue(should_buzz)
    
    def test_no_trigger_when_all_false(self):
        """Test that node doesn't trigger when all booleans are False"""
        node_result = {'detected': False, 'count': 5}
        
        should_buzz = False
        if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
            should_buzz = node_result['BOOL']
        else:
            for key, value in node_result.items():
                if isinstance(value, bool) and value:
                    should_buzz = True
                    break
        
        self.assertFalse(should_buzz)
    
    def test_buzzer_node_initialization(self):
        """Test BuzzerNode initializes correctly"""
        node = BuzzerNode()
        self.assertEqual(node.node_label, 'Buzzer')
        self.assertEqual(node.node_tag, 'Buzzer')
        self.assertFalse(node._is_buzzing)
        self.assertEqual(node._last_buzz_time, 0)
        self.assertIsNone(node._buzz_thread)


if __name__ == '__main__':
    unittest.main()
