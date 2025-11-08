#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Video Node 5-second block processing and 224x224 resizing"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_video_node_has_224_resize():
    """Test that VideoNode resizes frames to 224x224 before returning them"""
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for 224x224 resize logic
    assert 'cv2.resize(frame, (224, 224)' in content, \
        "Should resize frames to 224x224"
    
    # Check that resize happens before the frame is returned
    lines = content.split('\n')
    resize_line_idx = -1
    return_line_idx = -1
    
    for i, line in enumerate(lines):
        if 'cv2.resize(frame, (224, 224)' in line:
            resize_line_idx = i
        if 'return {"image": frame' in line:
            return_line_idx = i
    
    assert resize_line_idx >= 0, "Should have resize logic"
    assert return_line_idx >= 0, "Should have return statement"
    assert resize_line_idx < return_line_idx, \
        "Resize should happen before returning the frame"
    
    print("✓ Frame resizing to 224x224 is implemented correctly")


def test_video_node_has_5s_block_tracking():
    """Test that VideoNode tracks 5-second blocks"""
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for block tracking attributes
    assert '_current_block = {}' in content, \
        "Should have _current_block class attribute"
    assert '_block_start_frame = {}' in content, \
        "Should have _block_start_frame class attribute"
    
    # Check for block calculation logic
    assert 'frames_per_5s' in content, \
        "Should calculate frames per 5 seconds"
    assert 'current_block = current_frame // frames_per_5s' in content, \
        "Should calculate current block based on frame count"
    
    print("✓ 5-second block tracking is implemented")


def test_block_tracking_initialization():
    """Test that block tracking is initialized properly"""
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find where video file is changed
    file_change_block_start = -1
    for i, line in enumerate(lines):
        if 'if prev_movie_path != movie_path:' in line:
            file_change_block_start = i
            break
    
    assert file_change_block_start >= 0, \
        "Should have logic for when movie path changes"
    
    # Check that within this block, block tracking is initialized
    block_content = '\n'.join(lines[file_change_block_start:file_change_block_start + 15])
    
    assert '_current_block[str(node_id)] = 0' in block_content, \
        "Should initialize current_block when video changes"
    assert '_block_start_frame[str(node_id)] = 0' in block_content, \
        "Should initialize block_start_frame when video changes"
    
    print("✓ Block tracking initialization is correct")


def test_block_tracking_reset_on_loop():
    """Test that block tracking resets when video loops"""
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the loop_flag block
    loop_block_start = -1
    for i, line in enumerate(lines):
        if 'if loop_flag:' in line:
            loop_block_start = i
            break
    
    assert loop_block_start >= 0, "Should have 'if loop_flag:' block"
    
    # Check that within the next 15 lines, block tracking is reset
    block_content = '\n'.join(lines[loop_block_start:loop_block_start + 15])
    
    assert '_current_block[str(node_id)] = 0' in block_content, \
        "Should reset current_block on loop"
    assert '_block_start_frame[str(node_id)] = 0' in block_content, \
        "Should reset block_start_frame on loop"
    
    print("✓ Block tracking reset on loop is correct")


def test_resize_uses_inter_area_interpolation():
    """Test that resize uses INTER_AREA interpolation for downscaling"""
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that cv2.INTER_AREA is used for resizing
    # This is the best interpolation method for downscaling
    assert 'interpolation=cv2.INTER_AREA' in content, \
        "Should use INTER_AREA interpolation for downscaling to 224x224"
    
    print("✓ Resize uses proper interpolation method")


if __name__ == '__main__':
    test_video_node_has_224_resize()
    test_video_node_has_5s_block_tracking()
    test_block_tracking_initialization()
    test_block_tracking_reset_on_loop()
    test_resize_uses_inter_area_interpolation()
    print("\n✓ All 5-second block and 224x224 resize tests passed!")
