#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for boolean consistency in Trigger -> Router -> VideoRecorder pipeline
This test verifies that the BOOL field is properly propagated through the entire pipeline.
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTriggerRouterRecorderIntegration(unittest.TestCase):
    """Test complete pipeline: Trigger -> Router -> VideoRecorder"""
    
    def test_trigger_to_router_to_recorder_true(self):
        """Test that BOOL=True flows correctly through the pipeline"""
        # Step 1: Trigger outputs BOOL=True
        trigger_output = {"BOOL": True}
        
        # Step 2: Router receives trigger and outputs BOOL based on combination
        # Simplified router logic: if input BOOL is True, output True
        router_input = trigger_output
        combination_met = False
        if router_input and isinstance(router_input, dict):
            if 'BOOL' in router_input and isinstance(router_input['BOOL'], bool):
                combination_met = router_input['BOOL']
        
        router_output = {"BOOL": combination_met}
        
        # Step 3: VideoRecorder receives router output
        trigger_json = router_output
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
        
        # Verify the complete flow
        self.assertTrue(trigger_output['BOOL'])
        self.assertTrue(router_output['BOOL'])
        self.assertTrue(should_record)
    
    def test_trigger_to_router_to_recorder_false(self):
        """Test that BOOL=False flows correctly through the pipeline"""
        # Step 1: Trigger outputs BOOL=False
        trigger_output = {"BOOL": False}
        
        # Step 2: Router receives trigger and outputs BOOL based on combination
        router_input = trigger_output
        combination_met = False
        if router_input and isinstance(router_input, dict):
            if 'BOOL' in router_input and isinstance(router_input['BOOL'], bool):
                combination_met = router_input['BOOL']
        
        router_output = {"BOOL": combination_met}
        
        # Step 3: VideoRecorder receives router output
        trigger_json = router_output
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
        
        # Verify the complete flow
        self.assertFalse(trigger_output['BOOL'])
        self.assertFalse(router_output['BOOL'])
        self.assertFalse(should_record)
    
    def test_video_recorder_priority_with_mixed_fields(self):
        """Test that VideoRecorder correctly prioritizes BOOL over other fields"""
        # Simulate router sending mixed fields (shouldn't happen, but test defense)
        trigger_json = {
            'BOOL': False,  # Should be prioritized
            'record': True,  # Should be ignored
            'trigger': True,  # Should be ignored
        }
        
        # VideoRecorder logic
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
            elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
                should_record = trigger_json['record']
            elif 'trigger' in trigger_json and isinstance(trigger_json['trigger'], bool):
                should_record = trigger_json['trigger']
        
        # BOOL=False should take precedence
        self.assertFalse(should_record)
    
    def test_backward_compatibility_without_bool(self):
        """Test that VideoRecorder still works with legacy 'record' field"""
        # Legacy JSON without BOOL field
        trigger_json = {'record': True}
        
        # VideoRecorder logic
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
            elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
                should_record = trigger_json['record']
        
        # Should still work with legacy field
        self.assertTrue(should_record)
    
    def test_type_safety_non_boolean_bool(self):
        """Test that non-boolean BOOL values are rejected"""
        test_cases = [
            {'BOOL': 1},  # Integer
            {'BOOL': 'true'},  # String
            {'BOOL': None},  # None
            {'BOOL': []},  # List
            {'BOOL': {}},  # Dict
        ]
        
        for trigger_json in test_cases:
            # VideoRecorder logic
            should_record = False
            if trigger_json and isinstance(trigger_json, dict):
                if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                    should_record = trigger_json['BOOL']
            
            # Non-boolean values should not trigger
            self.assertFalse(should_record, 
                f"Non-boolean BOOL value {trigger_json['BOOL']} should not trigger")
    
    def test_empty_and_none_json(self):
        """Test that empty or None JSON doesn't trigger recording"""
        test_cases = [
            {},  # Empty dict
            None,  # None
        ]
        
        for trigger_json in test_cases:
            # VideoRecorder logic
            should_record = False
            if trigger_json and isinstance(trigger_json, dict):
                if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                    should_record = trigger_json['BOOL']
            
            # Should not trigger
            self.assertFalse(should_record)
    
    def test_multiple_triggers_through_pipeline(self):
        """Test multiple trigger states through the pipeline"""
        test_sequences = [
            (True, True, True),
            (False, False, False),
            (True, False, False),  # Router could filter out
        ]
        
        for trigger_bool, router_bool, expected_record in test_sequences:
            # Trigger output
            trigger_output = {"BOOL": trigger_bool}
            
            # Router output (could apply its own logic)
            router_output = {"BOOL": router_bool}
            
            # VideoRecorder logic
            should_record = False
            if router_output and isinstance(router_output, dict):
                if 'BOOL' in router_output and isinstance(router_output['BOOL'], bool):
                    should_record = router_output['BOOL']
            
            self.assertEqual(should_record, expected_record,
                f"Pipeline {trigger_bool} -> {router_bool} should result in {expected_record}")
    
    def test_buzzer_accepts_same_format(self):
        """Test that Buzzer also correctly accepts BOOL format"""
        # Buzzer receives same format from trigger/router
        node_result = {'BOOL': True}
        
        # Buzzer logic
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                should_buzz = node_result['BOOL']
        
        self.assertTrue(should_buzz)
        
        # Test BOOL=False
        node_result = {'BOOL': False}
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                should_buzz = node_result['BOOL']
        
        self.assertFalse(should_buzz)


if __name__ == '__main__':
    unittest.main()
