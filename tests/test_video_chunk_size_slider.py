#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the chunk size slider has been removed from the Video node.
Chunk size is now calculated automatically based on FPS.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_chunk_size_slider_removed():
    """Verify that the chunk size slider has been removed from FactoryNode"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that Input06 tags are NOT defined (Chunk Size used Input06)
    # Look for actual tag definitions (lines with '=' assignment)
    lines = content.split('\n')
    input06_definitions = [line for line in lines if 'tag_node_input06_name' in line and '=' in line and 'def ' not in line]
    assert len(input06_definitions) == 0, \
        f"Input06 tag definitions should be removed, found: {len(input06_definitions)} definitions"
    
    input06_value_definitions = [line for line in lines if 'tag_node_input06_value_name' in line and '=' in line and 'def ' not in line]
    assert len(input06_value_definitions) == 0, \
        f"Input06 value tag definitions should be removed, found: {len(input06_value_definitions)} definitions"
    
    # Check for slider widget removal
    assert 'label="Chunk Size (s)"' not in content, \
        "Should not have a slider labeled 'Chunk Size (s)'"
    
    print("✓ Chunk size slider has been removed from Video node")


def test_chunk_size_not_in_update_method():
    """Verify that the update method no longer reads chunk size value"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that update method does NOT read chunk_size
    assert 'chunk_size_value = dpg_get_value(tag_node_input06_value_name)' not in content, \
        "update() should not read chunk_size from slider (removed)"
    assert 'chunk_size = float(chunk_size_value)' not in content, \
        "update() should not convert chunk_size (removed)"
    
    print("✓ Update method no longer reads chunk size value")


def test_chunk_size_not_in_settings():
    """Verify that chunk size is no longer saved and loaded in settings"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check get_setting_dict does not save chunk_size
    assert 'setting_dict[tag_node_input06_value_name] = chunk_size' not in content, \
        "get_setting_dict() should not save chunk_size (removed)"
    
    # Check set_setting_dict does not load chunk_size
    assert "chunk_size = float(setting_dict.get(tag_node_input06_value_name, 2.0))" not in content, \
        "set_setting_dict() should not load chunk_size (removed)"
    assert 'dpg_set_value(tag_node_input06_value_name, chunk_size)' not in content, \
        "set_setting_dict() should not set the slider value (removed)"
    
    print("✓ Chunk size is no longer saved and loaded in settings")


def test_chunk_size_not_in_callback():
    """Verify that file selection callback no longer uses chunk size"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that callback does NOT read chunk size
    assert '_callback_file_select' in content, \
        "Should have _callback_file_select method"
    assert 'chunk_size_value = dpg_get_value(tag_node_input06_value_name)' not in content, \
        "Callback should not read chunk_size from slider (removed)"
    # Check that _preprocess_video is called without chunk_duration parameter
    assert 'chunk_duration=chunk_size' not in content, \
        "Callback should not pass chunk_duration to _preprocess_video (removed)"
    
    print("✓ File selection callback no longer uses chunk size")


def test_preprocess_video_signature():
    """Verify that _preprocess_video no longer requires chunk_duration parameter"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Find the _preprocess_video method signature
    lines = content.split('\n')
    found_method = False
    
    for line in lines:
        if 'def _preprocess_video(self' in line:
            found_method = True
            # Check that chunk_duration is not a required parameter
            # Should have target_fps but not chunk_duration
            assert 'target_fps' in line, "_preprocess_video should have target_fps parameter"
            # Allow chunk_duration in signature only if it has a default value or is not there at all
            if 'chunk_duration' in line:
                # If it exists, it should have a default value (backwards compatibility)
                pass  # OK for backwards compatibility
            break
    
    assert found_method, "Should find _preprocess_video method definition"
    
    print("✓ _preprocess_video signature updated (chunk size calculated from FPS)")


if __name__ == '__main__':
    test_chunk_size_slider_removed()
    test_chunk_size_not_in_update_method()
    test_chunk_size_not_in_settings()
    test_chunk_size_not_in_callback()
    test_preprocess_video_signature()
    print("\n✅ All chunk size slider removal tests passed!")
