#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test None-safe handling of dpg_get_value in node_api.py and node_video.py"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_node_api_update_with_undefined_frame():
    """Test that node_api.py update method handles undefined frame properly"""
    node_api_path = os.path.join(
        os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_api.py'
    )
    assert os.path.exists(node_api_path), "node_api.py should exist"
    
    # Read the file and check that frame is initialized before return
    with open(node_api_path, 'r') as f:
        content = f.read()
    
    # Find the update method
    assert 'def update(' in content, "update method should exist"
    
    # Check that frame is initialized as None before being used in return
    # Look for the pattern where frame is defined before the return statement
    update_method_start = content.find('def update(')
    update_method_end = content.find('def close(', update_method_start)
    update_method = content[update_method_start:update_method_end]
    
    # Verify frame is initialized
    assert 'frame = None' in update_method, "frame should be initialized to None"
    assert 'return {"image":frame' in update_method, "frame should be returned in image field"


def test_node_video_none_safe_int_conversion():
    """Test that node_video.py handles None values from dpg_get_value properly"""
    node_video_path = os.path.join(
        os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_video.py'
    )
    assert os.path.exists(node_video_path), "node_video.py should exist"
    
    with open(node_video_path, 'r') as f:
        content = f.read()
    
    # Check that skip_rate, target_fps, and playback_speed have None-safe handling
    # Look for the pattern: value = type(dpg_value) if dpg_value is not None else default
    
    # Find the update method
    update_method_start = content.find('def update(')
    update_method_end = content.find('def close(', update_method_start)
    update_method = content[update_method_start:update_method_end]
    
    # Verify None-safe conversions exist in update method
    assert 'skip_rate_value = dpg_get_value(tag_node_input03_value_name)' in update_method
    assert 'skip_rate = int(skip_rate_value) if skip_rate_value is not None else 1' in update_method
    assert 'target_fps_value = dpg_get_value(tag_node_input04_value_name)' in update_method
    assert 'target_fps = int(target_fps_value) if target_fps_value is not None else 24' in update_method
    assert 'playback_speed_value = dpg_get_value(tag_node_input05_value_name)' in update_method
    assert 'playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0' in update_method


def test_node_video_get_setting_dict_none_safe():
    """Test that node_video.py get_setting_dict handles None values properly"""
    node_video_path = os.path.join(
        os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_video.py'
    )
    assert os.path.exists(node_video_path), "node_video.py should exist"
    
    with open(node_video_path, 'r') as f:
        content = f.read()
    
    # Find the get_setting_dict method
    get_setting_start = content.find('def get_setting_dict(')
    get_setting_end = content.find('def set_setting_dict(', get_setting_start)
    get_setting_method = content[get_setting_start:get_setting_end]
    
    # Verify None-safe conversions exist in get_setting_dict method
    assert 'skip_rate_value = dpg_get_value(tag_node_input03_value_name)' in get_setting_method
    assert 'skip_rate = int(skip_rate_value) if skip_rate_value is not None else 1' in get_setting_method
    assert 'target_fps_value = dpg_get_value(tag_node_input04_value_name)' in get_setting_method
    assert 'target_fps = int(target_fps_value) if target_fps_value is not None else 24' in get_setting_method
    assert 'playback_speed_value = dpg_get_value(tag_node_input05_value_name)' in get_setting_method
    assert 'playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0' in get_setting_method


def test_node_api_get_setting_dict_none_safe():
    """Test that node_api.py get_setting_dict handles None values properly"""
    node_api_path = os.path.join(
        os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_api.py'
    )
    assert os.path.exists(node_api_path), "node_api.py should exist"
    
    with open(node_api_path, 'r') as f:
        content = f.read()
    
    # Find the get_setting_dict method
    get_setting_start = content.find('def get_setting_dict(')
    get_setting_end = content.find('def set_setting_dict(', get_setting_start)
    get_setting_method = content[get_setting_start:get_setting_end]
    
    # Verify None-safe conversion exists in get_setting_dict method
    assert 'skip_rate_value = dpg_get_value(tag_node_input03_value_name)' in get_setting_method
    assert 'skip_rate = int(skip_rate_value) if skip_rate_value is not None else 1' in get_setting_method


if __name__ == '__main__':
    test_node_api_update_with_undefined_frame()
    test_node_video_none_safe_int_conversion()
    test_node_video_get_setting_dict_none_safe()
    test_node_api_get_setting_dict_none_safe()
    print("All tests passed!")
