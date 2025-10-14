#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Video Node FPS and Speed Control features"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_video_node_fps_speed_structure():
    """Test that VideoNode has the required FPS and speed control attributes"""
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    # Read the file and check for required components
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for new input tags
    assert 'tag_node_input04_name' in content, "Should have input04 tag for FPS control"
    assert 'tag_node_input04_value_name' in content, "Should have input04 value tag"
    assert 'tag_node_input05_name' in content, "Should have input05 tag for speed control"
    assert 'tag_node_input05_value_name' in content, "Should have input05 value tag"
    
    # Check for UI elements
    assert 'Target FPS' in content, "Should have Target FPS slider label"
    assert 'Speed' in content, "Should have Speed slider label"
    assert 'add_slider_int' in content, "Should have integer slider for FPS"
    assert 'add_slider_float' in content, "Should have float slider for speed"
    
    # Check for timing control attributes
    assert '_last_frame_time = {}' in content, "Should have _last_frame_time dict"
    
    # Check for timing logic in update method
    assert 'target_fps' in content, "Should read target_fps value"
    assert 'playback_speed' in content, "Should read playback_speed value"
    assert 'frame_interval' in content, "Should calculate frame_interval"
    assert 'should_read_frame' in content, "Should have frame timing check"
    
    # Check default values
    assert 'default_value=24' in content, "Target FPS should default to 24"
    assert 'default_value=1.0' in content, "Speed should default to 1.0x"
    
    # Check value ranges
    assert 'min_value=1' in content, "FPS should have min value of 1"
    assert 'max_value=120' in content, "FPS should have max value of 120"
    assert 'min_value=0.25' in content, "Speed should have min value of 0.25"
    assert 'max_value=4.0' in content, "Speed should have max value of 4.0"
    
    print("✓ All FPS and speed control structure checks passed")


def test_setting_dict_includes_new_params():
    """Test that get/set_setting_dict methods handle new parameters"""
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check get_setting_dict includes new parameters
    assert 'tag_node_input04_value_name' in content, "get_setting_dict should reference FPS tag"
    assert 'tag_node_input05_value_name' in content, "get_setting_dict should reference speed tag"
    
    # Check set_setting_dict includes new parameters
    lines = content.split('\n')
    set_setting_dict_found = False
    has_fps_set = False
    has_speed_set = False
    
    for i, line in enumerate(lines):
        if 'def set_setting_dict' in line:
            set_setting_dict_found = True
        if set_setting_dict_found:
            if 'dpg_set_value(tag_node_input04_value_name' in line:
                has_fps_set = True
            if 'dpg_set_value(tag_node_input05_value_name' in line:
                has_speed_set = True
    
    assert has_fps_set, "set_setting_dict should set FPS value"
    assert has_speed_set, "set_setting_dict should set speed value"
    
    print("✓ All setting dict checks passed")


def test_frame_timing_logic():
    """Test that frame timing logic is implemented correctly"""
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check timing calculation
    assert 'frame_interval = (1.0 / target_fps) / playback_speed' in content, \
        "Should calculate frame_interval based on FPS and speed"
    
    # Check timing check
    assert 'should_read_frame = (last_time is None) or ((current_time - last_time) >= frame_interval)' in content, \
        "Should check if enough time has passed to read next frame"
    
    # Check frame time recording
    assert "self._last_frame_time[str(node_id)] = current_time" in content, \
        "Should record frame time after reading"
    
    # Check initialization on file change
    assert "self._last_frame_time[str(node_id)] = None" in content, \
        "Should reset frame time when video file changes"
    
    print("✓ All frame timing logic checks passed")


if __name__ == '__main__':
    test_video_node_fps_speed_structure()
    test_setting_dict_includes_new_params()
    test_frame_timing_logic()
    print("\n✓ All tests passed successfully!")
