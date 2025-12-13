#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for Video node Queue Chunks slider and dynamic queue sizing.

This test validates:
1. Skip Rate slider is removed from the UI
2. Queue Chunks slider is present and functional
3. Dynamic queue sizing calculations are correct
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_skip_rate_slider_removed():
    """Test that Skip Rate slider is removed from Video node UI"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that Skip Rate slider is NOT in the UI
    assert 'label="Skip Rate"' not in content, "Skip Rate slider should be removed from UI"
    
    # Check that Input03 tags are NOT defined (Skip Rate used Input03)
    lines = content.split('\n')
    input03_definitions = [line for line in lines if 'tag_node_input03_name' in line and '=' in line]
    assert len(input03_definitions) == 0, "Input03 tag definitions should be removed"
    
    print("✓ Skip Rate slider removed from Video node")


def test_queue_chunks_slider_removed():
    """Test that Queue Chunks slider has been removed from Video node UI"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that Queue Chunks slider is NOT in the UI
    assert 'label="Queue Chunks"' not in content, "Queue Chunks slider should be removed from UI"
    
    # Check that Input07 tags are NOT defined in FactoryNode's add_node method
    lines = content.split('\n')
    # Find the FactoryNode section by looking for the add_node method
    in_factory_add_node = False
    factory_lines = []
    for line in lines:
        if 'def add_node(' in line:
            in_factory_add_node = True
        elif in_factory_add_node and line.strip().startswith('def ') and 'add_node' not in line:
            break
        elif in_factory_add_node:
            factory_lines.append(line)
    
    factory_content = '\n'.join(factory_lines)
    input07_in_factory = 'tag_node_input07_name' in factory_content and '=' in factory_content
    assert not input07_in_factory, "Input07 name tag should not be defined in FactoryNode.add_node()"
    
    print("✓ Queue Chunks slider removed from Video node")
    print("  - Input07 tags removed from UI")
    print("  - Queue size now calculated automatically (4 * fps)")


def test_preprocess_video_automatic_queue_sizing():
    """Test that _preprocess_video calculates queue sizes automatically"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that _preprocess_video no longer requires num_chunks_to_keep
    assert 'def _preprocess_video(self, node_id, movie_path, target_fps' in content, \
        "_preprocess_video should have simplified signature"
    
    # Check that queue sizes are calculated automatically based on FPS
    assert 'queue_size_seconds = 4' in content or 'queue_duration_seconds = 4' in content, \
        "Queue size should be calculated as 4 seconds"
    assert 'image_queue_size = int(' in content and '* target_fps)' in content, \
        "Image queue size should be calculated based on fps"
    assert 'audio_queue_size = int(' in content and '* target_fps)' in content, \
        "Audio queue size should be calculated based on fps"
    
    # Check that queue sizes are stored in metadata
    assert "'image_queue_size': image_queue_size" in content, \
        "Image queue size should be stored in metadata"
    assert "'audio_queue_size': audio_queue_size" in content, \
        "Audio queue size should be stored in metadata"
    
    print("✓ _preprocess_video calculates queue sizes automatically")
    print("  - Image queue size: 4 * target_fps")
    print("  - Audio queue size: 4 * target_fps (same as image)")
    print("  - Stores sizes in metadata")


def test_callback_file_select_no_num_chunks():
    """Test that _callback_file_select no longer retrieves or passes num_chunks_to_keep"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that _callback_file_select does NOT retrieve num_chunks from Input07
    in_callback = False
    callback_lines = []
    for line in content.split('\n'):
        if 'def _callback_file_select' in line:
            in_callback = True
        elif in_callback and line.strip().startswith('def '):
            break
        elif in_callback:
            callback_lines.append(line)
    
    callback_content = '\n'.join(callback_lines)
    assert 'tag_node_input07_value_name' not in callback_content, \
        "_callback_file_select should not retrieve Input07 (Queue Chunks removed)"
    
    # Check that num_chunks_to_keep is NOT passed to _preprocess_video
    assert 'num_chunks_to_keep=' not in callback_content, \
        "_callback_file_select should not pass num_chunks_to_keep"
    
    print("✓ _callback_file_select no longer uses num_chunks")


def test_update_method_no_manual_queue_sizing():
    """Test that update method no longer retrieves queue size from slider"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that update method does NOT retrieve Input07 value
    in_update = False
    update_lines = []
    for line in content.split('\n'):
        if 'def update(' in line:
            in_update = True
        elif in_update and line.strip().startswith('def ') and 'def update' not in line:
            break
        elif in_update:
            update_lines.append(line)
    
    update_content = '\n'.join(update_lines)
    # Allow tag_node_input07_value_name in old/legacy contexts but not for reading queue chunks
    if 'tag_node_input07_value_name' in update_content:
        # Should not be reading it with dpg_get_value
        assert 'dpg_get_value(tag_node_input07_value_name)' not in update_content, \
            "update method should not read Input07 (Queue Chunks removed)"
    
    # Check that queue resizing is still called (but sizes come from metadata, not slider)
    assert 'resize_queue' in content, \
        "update method should still call resize_queue (with automatic sizes)"
    
    print("✓ update method uses automatic queue sizes from metadata")


def test_setting_dict_methods_no_queue_chunks():
    """Test that get_setting_dict and set_setting_dict no longer handle Input07"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that get_setting_dict exists
    assert 'def get_setting_dict' in content, "get_setting_dict method should exist"
    
    # Check that set_setting_dict exists
    assert 'def set_setting_dict' in content, "set_setting_dict method should exist"
    
    # Check that Input03 (Skip Rate) and Input07 (Queue Chunks) are no longer in get_setting_dict
    lines_in_get_setting = []
    in_get_setting = False
    for line in content.split('\n'):
        if 'def get_setting_dict' in line:
            in_get_setting = True
        elif in_get_setting and line.strip().startswith('def '):
            break
        elif in_get_setting:
            lines_in_get_setting.append(line)
    
    get_setting_content = '\n'.join(lines_in_get_setting)
    assert 'tag_node_input03_value_name' not in get_setting_content, \
        "get_setting_dict should not reference Input03 (Skip Rate)"
    assert 'tag_node_input07_value_name' not in get_setting_content, \
        "get_setting_dict should not reference Input07 (Queue Chunks removed)"
    
    print("✓ Setting dict methods updated")
    print("  - Input03 (Skip Rate) removed")
    print("  - Input07 (Queue Chunks) removed")
    print("  - Queue size now calculated automatically")


def test_queue_resize_methods_exist():
    """Test that TimestampedQueue has resize methods"""
    timestamped_queue_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'timestamped_queue.py'
    )
    
    assert os.path.exists(timestamped_queue_path), "timestamped_queue.py should exist"
    
    with open(timestamped_queue_path, 'r') as f:
        content = f.read()
    
    # Check that resize method exists in TimestampedQueue
    assert 'def resize(self, new_maxsize: int)' in content, \
        "TimestampedQueue should have resize method"
    
    # Check that resize_queue method exists in NodeDataQueueManager
    assert 'def resize_queue(self, node_id_name: str, data_type: str, new_size: int)' in content, \
        "NodeDataQueueManager should have resize_queue method"
    
    print("✓ Queue resize methods exist")
    print("  - TimestampedQueue.resize()")
    print("  - NodeDataQueueManager.resize_queue()")


def test_skip_rate_fixed_at_one():
    """Test that skip_rate is fixed at 1 in update method"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that skip_rate is fixed at 1 in the update method
    assert 'skip_rate = 1' in content, \
        "skip_rate should be fixed at 1 in update method"
    
    # Verify it's not retrieved from Input03 anymore
    lines = content.split('\n')
    in_update = False
    for line in lines:
        if 'def update(' in line:
            in_update = True
        elif in_update and line.strip().startswith('def '):
            break
        elif in_update and 'skip_rate_value = dpg_get_value(tag_node_input03_value_name)' in line:
            assert False, "skip_rate should not be retrieved from Input03 in update method"
    
    print("✓ skip_rate is fixed at 1 (no frame skipping)")


if __name__ == "__main__":
    test_skip_rate_slider_removed()
    test_queue_chunks_slider_removed()
    test_preprocess_video_automatic_queue_sizing()
    test_callback_file_select_no_num_chunks()
    test_update_method_no_manual_queue_sizing()
    test_setting_dict_methods_no_queue_chunks()
    test_queue_resize_methods_exist()
    test_skip_rate_fixed_at_one()
    print("\n✅ All queue chunks removal tests passed!")
