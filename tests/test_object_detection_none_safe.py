#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test None-safe handling of dpg_get_value in node_object_detection.py"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_object_detection_update_none_safe():
    """Test that node_object_detection.py update method handles None values properly"""
    node_path = os.path.join(
        os.path.dirname(__file__), '..', 'node', 'DLNode', 'node_object_detection.py'
    )
    assert os.path.exists(node_path), "node_object_detection.py should exist"
    
    with open(node_path, 'r') as f:
        content = f.read()
    
    # Find the update method
    update_method_start = content.find('def update(')
    update_method_end = content.find('def close(', update_method_start)
    update_method = content[update_method_start:update_method_end]
    
    # Verify None-safe conversions exist for provider
    assert 'provider_value = dpg_get_value(self.tag_provider_select_value_name)' in update_method, \
        "provider_value should be retrieved from dpg_get_value"
    assert "provider = provider_value if provider_value is not None else 'CPU'" in update_method, \
        "provider should have None-safe default to 'CPU'"
    
    # Verify None-safe conversions exist for model_name
    assert 'model_name_value = dpg_get_value(self.tag_node_input_text_value_name)' in update_method, \
        "model_name_value should be retrieved from dpg_get_value"
    assert 'model_name = model_name_value if model_name_value is not None else list(self._model_class.keys())[0]' in update_method, \
        "model_name should have None-safe default to first model in list"


def test_object_detection_get_setting_dict_none_safe():
    """Test that node_object_detection.py get_setting_dict method handles None values properly"""
    node_path = os.path.join(
        os.path.dirname(__file__), '..', 'node', 'DLNode', 'node_object_detection.py'
    )
    assert os.path.exists(node_path), "node_object_detection.py should exist"
    
    with open(node_path, 'r') as f:
        content = f.read()
    
    # Find the get_setting_dict method
    get_setting_start = content.find('def get_setting_dict(')
    get_setting_end = content.find('def set_setting_dict(', get_setting_start)
    get_setting_method = content[get_setting_start:get_setting_end]
    
    # Verify None-safe conversions exist for model_name
    assert 'model_name_value = dpg_get_value(input_value02_tag)' in get_setting_method, \
        "model_name_value should be retrieved from dpg_get_value"
    assert 'model_name = model_name_value if model_name_value is not None else list(self._model_class.keys())[0]' in get_setting_method, \
        "model_name should have None-safe default to first model in list"
    
    # Verify None-safe conversions exist for score_th
    assert 'score_th_value = dpg_get_value(input_value03_tag)' in get_setting_method, \
        "score_th_value should be retrieved from dpg_get_value"
    assert 'score_th = round(float(score_th_value), 3) if score_th_value is not None else 0.3' in get_setting_method, \
        "score_th should have None-safe default to 0.3"


if __name__ == '__main__':
    test_object_detection_update_none_safe()
    test_object_detection_get_setting_dict_none_safe()
    print("All tests passed!")
