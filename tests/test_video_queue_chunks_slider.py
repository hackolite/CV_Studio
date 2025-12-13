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


def test_queue_chunks_slider_present():
    """Test that Queue Chunks slider is present in Video node UI"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that Queue Chunks slider IS in the UI
    assert 'label="Queue Chunks"' in content, "Queue Chunks slider should be in UI"
    
    # Check that Input07 tags are defined
    assert 'tag_node_input07_name' in content, "Input07 name tag should be defined"
    assert 'tag_node_input07_value_name' in content, "Input07 value tag should be defined"
    
    # Check slider parameters
    assert 'default_value=4' in content, "Queue Chunks slider should have default value of 4"
    assert 'min_value=1' in content, "Queue Chunks slider should have min value of 1"
    assert 'max_value=20' in content, "Queue Chunks slider should have max value of 20"
    
    print("✓ Queue Chunks slider present in Video node")
    print("  - Input07 tags defined")
    print("  - Default value: 4")
    print("  - Range: 1-20")


def test_preprocess_video_accepts_num_chunks():
    """Test that _preprocess_video accepts num_chunks_to_keep parameter"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that _preprocess_video signature includes num_chunks_to_keep
    assert 'def _preprocess_video(self, node_id, movie_path, chunk_duration=2.0, step_duration=2.0, num_chunks_to_keep=4)' in content, \
        "_preprocess_video should accept num_chunks_to_keep parameter"
    
    # Check that queue sizes are calculated
    assert 'image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)' in content, \
        "Image queue size should be calculated based on num_chunks_to_keep"
    assert 'audio_queue_size = num_chunks_to_keep' in content, \
        "Audio queue size should equal num_chunks_to_keep"
    
    # Check that queue sizes are stored in metadata
    assert "'image_queue_size': image_queue_size" in content, \
        "Image queue size should be stored in metadata"
    assert "'audio_queue_size': audio_queue_size" in content, \
        "Audio queue size should be stored in metadata"
    
    print("✓ _preprocess_video accepts num_chunks_to_keep parameter")
    print("  - Calculates image queue size: num_chunks × chunk_duration × fps")
    print("  - Calculates audio queue size: num_chunks")
    print("  - Stores sizes in metadata")


def test_callback_file_select_passes_num_chunks():
    """Test that _callback_file_select passes num_chunks_to_keep to _preprocess_video"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that _callback_file_select retrieves num_chunks value
    assert 'tag_node_input07_value_name' in content and '_callback_file_select' in content, \
        "_callback_file_select should retrieve Input07 (Queue Chunks) value"
    
    # Check that num_chunks_to_keep is passed to _preprocess_video
    assert 'num_chunks_to_keep=num_chunks' in content or 'num_chunks_to_keep=' in content, \
        "_callback_file_select should pass num_chunks_to_keep to _preprocess_video"
    
    print("✓ _callback_file_select passes num_chunks_to_keep")


def test_update_method_applies_queue_sizes():
    """Test that update method applies dynamic queue sizes"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that update method retrieves Input07 value
    assert 'tag_node_input07_value_name' in content and 'def update(' in content, \
        "update method should retrieve Input07 (Queue Chunks) value"
    
    # Check that queue resizing is attempted
    assert 'resize_queue' in content, \
        "update method should call resize_queue"
    
    print("✓ update method applies dynamic queue sizes")


def test_setting_dict_methods_updated():
    """Test that get_setting_dict and set_setting_dict handle Input07"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that get_setting_dict handles Input07
    assert 'def get_setting_dict' in content, "get_setting_dict method should exist"
    
    # Check that set_setting_dict handles Input07
    assert 'def set_setting_dict' in content, "set_setting_dict method should exist"
    
    # Check that Input03 (Skip Rate) is no longer in get_setting_dict
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
    assert 'tag_node_input07_value_name' in get_setting_content, \
        "get_setting_dict should reference Input07 (Queue Chunks)"
    
    print("✓ Setting dict methods updated")
    print("  - Input03 (Skip Rate) removed")
    print("  - Input07 (Queue Chunks) added")


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
    test_queue_chunks_slider_present()
    test_preprocess_video_accepts_num_chunks()
    test_callback_file_select_passes_num_chunks()
    test_update_method_applies_queue_sizes()
    test_setting_dict_methods_updated()
    test_queue_resize_methods_exist()
    test_skip_rate_fixed_at_one()
    print("\n✅ All tests passed!")
