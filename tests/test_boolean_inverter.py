#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the BooleanInverter trigger node.
"""
import sys
import os
from unittest.mock import MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dearpygui before importing the node
sys.modules['dearpygui'] = MagicMock()
sys.modules['dearpygui.dearpygui'] = MagicMock()


def test_boolean_inverter_basic():
    """Test basic BooleanInverter node functionality"""
    from node.TriggerNode.node_boolean_inverter import Node
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Simulate connections
    connection_list = [['1:SomeNode:Json:Output01', '2:BooleanInverter:Json:Input01']]
    
    # Mock dpg functions
    def mock_dpg_get_value(tag):
        return None
    
    def mock_dpg_set_value(tag, value):
        pass
    
    # Replace dpg functions
    import node.TriggerNode.node_boolean_inverter as module
    original_get = module.dpg_get_value
    original_set = module.dpg_set_value
    module.dpg_get_value = mock_dpg_get_value
    module.dpg_set_value = mock_dpg_set_value
    
    try:
        # Test 1: Invert True to False
        print("Test 1: Inverting True to False...")
        mock_json_data = {'BOOL': True}
        node_result_dict = {'1:SomeNode': mock_json_data}
        
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        assert 'json' in result
        assert result['json'] is not None
        assert 'BOOL' in result['json']
        assert result['json']['BOOL'] == False
        print("  ✓ True inverted to False")
        
        # Test 2: Invert False to True
        print("Test 2: Inverting False to True...")
        mock_json_data = {'BOOL': False}
        node_result_dict = {'1:SomeNode': mock_json_data}
        
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        assert 'json' in result
        assert result['json'] is not None
        assert 'BOOL' in result['json']
        assert result['json']['BOOL'] == True
        print("  ✓ False inverted to True")
        
        # Test 3: Handle missing BOOL field (default to False)
        print("Test 3: Handling missing BOOL field...")
        mock_json_data = {'other_field': 'value'}
        node_result_dict = {'1:SomeNode': mock_json_data}
        
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        assert 'json' in result
        assert result['json'] is not None
        assert 'BOOL' in result['json']
        assert result['json']['BOOL'] == True  # Inverts default False to True
        print("  ✓ Missing BOOL field handled (default False inverted to True)")
        
        # Test 4: Handle None input
        print("Test 4: Handling None input...")
        node_result_dict = {}
        
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        assert 'json' in result
        assert result['json'] is not None
        assert 'BOOL' in result['json']
        assert result['json']['BOOL'] == False  # Default output when no input
        print("  ✓ None input handled (outputs False)")
        
        print("\n✅ All BooleanInverter tests passed!")
        
    finally:
        # Restore original functions
        module.dpg_get_value = original_get
        module.dpg_set_value = original_set


if __name__ == '__main__':
    test_boolean_inverter_basic()
