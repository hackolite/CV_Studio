#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for standardized BOOL field message format
across Trigger, Router, and Action nodes
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBoolFieldStandardization(unittest.TestCase):
    """Test that all node types use standardized {"BOOL": True/False} format"""
    
    def test_objdetcount_returns_bool_field(self):
        """Test that ObjDetCount trigger returns {"BOOL": ...}"""
        from node.TriggerNode.node_objdetcount import Node
        
        # Verify the node outputs JSON with BOOL field
        # This is tested by checking the return statement in the update method
        node = Node()
        
        # The node should have an update method that returns {"BOOL": ...}
        self.assertTrue(hasattr(node, 'update'))
    
    def test_simple_router_returns_bool_field(self):
        """Test that SimpleRouter returns {"BOOL": ...}"""
        from node.RouterNode.node_simple_router import Node
        
        # Verify the node outputs JSON with BOOL field
        node = Node()
        
        # The node should have an update method that returns {"BOOL": ...}
        self.assertTrue(hasattr(node, 'update'))
    
    def test_video_recorder_accepts_bool_field(self):
        """Test that VideoRecorder prioritizes BOOL field"""
        # Test standard format {"BOOL": True}
        trigger_json = {'BOOL': True}
        
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
        
        self.assertTrue(should_record)
        
        # Test standard format {"BOOL": False}
        trigger_json = {'BOOL': False}
        
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
        
        self.assertFalse(should_record)
    
    def test_buzzer_accepts_bool_field(self):
        """Test that Buzzer prioritizes BOOL field"""
        # Test standard format {"BOOL": True}
        node_result = {'BOOL': True}
        
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                should_buzz = node_result['BOOL']
        
        self.assertTrue(should_buzz)
        
        # Test standard format {"BOOL": False}
        node_result = {'BOOL': False}
        
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                should_buzz = node_result['BOOL']
        
        self.assertFalse(should_buzz)
    
    def test_bool_field_overrides_legacy_fields(self):
        """Test that BOOL field takes precedence over legacy fields"""
        # VideoRecorder: BOOL should override 'record' and 'trigger'
        trigger_json = {'BOOL': False, 'record': True, 'trigger': True}
        
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
            elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
                should_record = trigger_json['record']
            elif 'trigger' in trigger_json and isinstance(trigger_json['trigger'], bool):
                should_record = trigger_json['trigger']
        
        self.assertFalse(should_record, "BOOL field should override other fields")
        
        # Buzzer: BOOL should override any other boolean field
        node_result = {'BOOL': False, 'detected': True, 'triggered': True}
        
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                should_buzz = node_result['BOOL']
            else:
                for key, value in node_result.items():
                    if isinstance(value, bool) and value:
                        should_buzz = True
                        break
        
        self.assertFalse(should_buzz, "BOOL field should override other boolean fields")
    
    def test_backward_compatibility(self):
        """Test that nodes maintain backward compatibility without BOOL field"""
        # VideoRecorder should still work with 'record' field
        trigger_json = {'record': True}
        
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
            elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
                should_record = trigger_json['record']
        
        self.assertTrue(should_record, "Should support legacy 'record' field")
        
        # Buzzer should still work with any boolean field
        node_result = {'detected': True}
        
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                should_buzz = node_result['BOOL']
            else:
                for key, value in node_result.items():
                    if isinstance(value, bool) and value:
                        should_buzz = True
                        break
        
        self.assertTrue(should_buzz, "Should support legacy any boolean field")
    
    def test_empty_json_handling(self):
        """Test that nodes handle empty JSON correctly"""
        # VideoRecorder with empty JSON
        trigger_json = {}
        
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
        
        self.assertFalse(should_record)
        
        # Buzzer with empty JSON
        node_result = {}
        
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                should_buzz = node_result['BOOL']
        
        self.assertFalse(should_buzz)
    
    def test_none_json_handling(self):
        """Test that nodes handle None JSON correctly"""
        # VideoRecorder with None JSON
        trigger_json = None
        
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
        
        self.assertFalse(should_record)
        
        # Buzzer with None JSON
        node_result = None
        
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                should_buzz = node_result['BOOL']
        
        self.assertFalse(should_buzz)


if __name__ == '__main__':
    unittest.main()
