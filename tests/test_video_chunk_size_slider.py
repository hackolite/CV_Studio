#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the chunk size slider is correctly implemented in the Video node.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_chunk_size_slider_in_factory():
    """Verify that the chunk size slider is added in the FactoryNode"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for Input06 tag definition
    assert 'tag_node_input06_name' in content, \
        "Should define tag_node_input06_name for chunk size slider"
    assert 'tag_node_input06_value_name' in content, \
        "Should define tag_node_input06_value_name for chunk size slider"
    
    # Check for slider widget creation
    assert 'label="Chunk Size (s)"' in content, \
        "Should have a slider labeled 'Chunk Size (s)'"
    assert 'default_value=2.0' in content, \
        "Should have default chunk size of 2.0 seconds"
    
    print("✓ Chunk size slider is defined in FactoryNode")


def test_chunk_size_in_update_method():
    """Verify that the update method reads the chunk size value"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that update method reads chunk_size
    assert 'chunk_size_value = dpg_get_value(tag_node_input06_value_name)' in content, \
        "update() should read chunk_size from slider"
    assert 'chunk_size = float(chunk_size_value) if chunk_size_value is not None else 2.0' in content, \
        "update() should convert chunk_size to float with 2.0 default"
    
    print("✓ Update method correctly reads chunk size value")


def test_chunk_size_in_settings():
    """Verify that chunk size is saved and loaded in settings"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check get_setting_dict
    assert 'setting_dict[tag_node_input06_value_name] = chunk_size' in content, \
        "get_setting_dict() should save chunk_size"
    
    # Check set_setting_dict
    assert "chunk_size = float(setting_dict.get(tag_node_input06_value_name, 2.0))" in content, \
        "set_setting_dict() should load chunk_size with 2.0 default"
    assert 'dpg_set_value(tag_node_input06_value_name, chunk_size)' in content, \
        "set_setting_dict() should set the slider value"
    
    print("✓ Chunk size is correctly saved and loaded in settings")


def test_chunk_size_in_callback():
    """Verify that file selection callback uses the chunk size"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that callback reads chunk size and passes it to _preprocess_video
    assert '_callback_file_select' in content, \
        "Should have _callback_file_select method"
    assert 'chunk_size_value = dpg_get_value(tag_node_input06_value_name)' in content, \
        "Callback should read chunk_size from slider"
    assert 'self._preprocess_video(node_id, data["file_path_name"], chunk_duration=chunk_size, step_duration=chunk_size)' in content, \
        "Callback should pass chunk_size to _preprocess_video"
    
    print("✓ File selection callback uses chunk size correctly")


def test_slider_range():
    """Verify that the slider has appropriate min/max values"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Find the slider definition
    lines = content.split('\n')
    found_slider = False
    min_value = None
    max_value = None
    
    for i, line in enumerate(lines):
        if 'label="Chunk Size (s)"' in line:
            found_slider = True
            # Look for min_value and max_value in surrounding lines
            for j in range(i-3, min(i+5, len(lines))):
                if 'min_value=' in lines[j]:
                    min_value = lines[j].split('min_value=')[1].split(',')[0].strip()
                if 'max_value=' in lines[j]:
                    max_value = lines[j].split('max_value=')[1].split(',')[0].strip()
    
    assert found_slider, "Should find chunk size slider definition"
    assert min_value == '0.5', f"Min value should be 0.5, got {min_value}"
    assert max_value == '10.0', f"Max value should be 10.0, got {max_value}"
    
    print("✓ Slider range is correctly set (0.5 to 10.0 seconds)")


if __name__ == '__main__':
    test_chunk_size_slider_in_factory()
    test_chunk_size_in_update_method()
    test_chunk_size_in_settings()
    test_chunk_size_in_callback()
    test_slider_range()
    print("\n✅ All chunk size slider tests passed!")
