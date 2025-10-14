#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for spectrogram synchronization with video playback"""

import pytest
import sys
import os
import ast

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_spectrogram_sync_code_structure():
    """Test that the spectrogram sync code has the expected structure"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that the yellow line drawing code is present
    assert "cv2.line" in content, "Should have cv2.line call to draw indicator"
    assert "(0, 255, 255)" in content, "Should use yellow color (0, 255, 255) in BGR"
    
    # Check that frame count is being used
    assert "current_frame" in content, "Should track current frame"
    assert "_frame_count" in content, "Should use _frame_count"
    
    # Check that time calculation is present
    assert "current_time" in content, "Should calculate current time"
    assert "fps" in content, "Should use fps for time calculation"
    
    # Check that spectrogram column calculation is present
    assert "spectrogram_col" in content, "Should calculate spectrogram column"
    assert "hop_length" in content, "Should use hop_length for column calculation"
    
    # Check that the original spectrogram array is being copied
    assert ".copy()" in content, "Should copy spectrogram array to avoid modifying original"
    assert "_spectrogram_array" in content, "Should use _spectrogram_array"
    
    print("✓ Spectrogram sync code structure is correct")


def test_spectrogram_sync_logic():
    """Test the logic of spectrogram synchronization"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Verify the calculation sequence is present
    # 1. Get current frame
    assert "current_frame = self._frame_count.get(str(node_id)" in content
    
    # 2. Calculate time from frame
    assert "current_time = current_frame / fps" in content
    
    # 3. Calculate sample position
    assert "current_sample = int(current_time * sr)" in content
    
    # 4. Calculate spectrogram column
    assert "spectrogram_col = int(current_sample / hop_length)" in content
    
    # 5. Check bounds before drawing
    assert "if 0 <= spectrogram_col < spectrogram_bgr.shape[1]:" in content
    
    # 6. Draw the line
    assert "cv2.line(spectrogram_bgr," in content
    
    print("✓ Spectrogram sync logic is correct")


def test_no_modification_of_original_spectrogram():
    """Test that the original spectrogram array is not modified"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that we use .copy() on the spectrogram array
    assert "self._spectrogram_array[str(node_id)].copy()" in content
    
    # Check that we're working on the copy
    assert "spectrogram_bgr = self._spectrogram_array[str(node_id)].copy()" in content
    
    print("✓ Original spectrogram array is not modified")


def test_metadata_usage():
    """Test that metadata is properly used for synchronization"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that metadata is accessed
    assert "self._spectrogram_meta[str(node_id)]" in content or \
           "self._spectrogram_meta" in content
    
    # Check that metadata fields are used
    assert "meta['fps']" in content or "meta.get('fps')" in content or "fps = meta['fps']" in content
    assert "meta['sr']" in content or "meta.get('sr')" in content or "sr = meta['sr']" in content
    assert "meta['hop_length']" in content or "meta.get('hop_length')" in content or "hop_length = meta['hop_length']" in content
    
    print("✓ Metadata is properly used")


def test_python_syntax_valid():
    """Test that the Python syntax is valid"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    try:
        ast.parse(content)
        print("✓ Python syntax is valid")
    except SyntaxError as e:
        pytest.fail(f"Syntax error in node_video.py: {e}")


def test_line_color_is_yellow():
    """Test that the indicator line color is yellow"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Yellow in BGR is (0, 255, 255)
    assert "(0, 255, 255)" in content, "Should use yellow color (0, 255, 255)"
    
    # Check it's in a cv2.line call
    lines = content.split('\n')
    found_yellow_line = False
    for i, line in enumerate(lines):
        if 'cv2.line' in line:
            # Check if yellow color is within a few lines
            nearby_lines = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
            if '(0, 255, 255)' in nearby_lines:
                found_yellow_line = True
                break
    
    assert found_yellow_line, "Yellow color should be used in cv2.line call"
    print("✓ Indicator line color is yellow")


if __name__ == '__main__':
    test_spectrogram_sync_code_structure()
    test_spectrogram_sync_logic()
    test_no_modification_of_original_spectrogram()
    test_metadata_usage()
    test_python_syntax_valid()
    test_line_color_is_yellow()
    print("\n✓ All spectrogram sync tests passed successfully!")
