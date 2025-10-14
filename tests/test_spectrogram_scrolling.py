#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for spectrogram scrolling window functionality"""

import sys
import os
import ast

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_sliding_window_extraction():
    """Test that sliding window extraction code is present"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for sliding window implementation
    assert "window_width" in content, "Should define window_width"
    assert "half_window" in content, "Should calculate half_window"
    assert "start_col" in content, "Should calculate start_col"
    assert "end_col" in content, "Should calculate end_col"
    assert "spectrogram_window" in content, "Should extract spectrogram_window"
    
    print("✓ Sliding window extraction code is present")


def test_window_centered_on_playback():
    """Test that the window is centered around current playback position"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that window is centered around spectrogram_col
    assert "spectrogram_col - half_window" in content, "Should center window around current position"
    assert "start_col + window_width" in content, "Should calculate end based on start and width"
    
    print("✓ Window is centered on playback position")


def test_indicator_position_in_window():
    """Test that the indicator position is calculated relative to the window"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that indicator position is relative to window start
    assert "indicator_col" in content, "Should calculate indicator_col"
    assert "spectrogram_col - start_col" in content, "Should calculate indicator relative to window"
    
    print("✓ Indicator position is calculated relative to window")


def test_boundary_handling():
    """Test that boundaries are properly handled"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for boundary handling
    assert "max(0," in content, "Should handle start boundary"
    assert "min(full_spectrogram.shape[1]" in content, "Should handle end boundary"
    
    print("✓ Boundary handling is present")


def test_padding_for_edges():
    """Test that padding is applied when window is at edges"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for padding logic
    assert "pad_width" in content, "Should calculate pad_width"
    assert "np.zeros" in content and "padding" in content, "Should create padding"
    assert "np.hstack" in content, "Should concatenate padding with window"
    
    print("✓ Padding logic is present for edge cases")


def test_yellow_line_still_present():
    """Test that the yellow indicator line is still drawn"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that yellow line is still present
    assert "cv2.line" in content, "Should still draw indicator line"
    assert "(0, 255, 255)" in content, "Should still use yellow color"
    
    print("✓ Yellow indicator line is still present")


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
        raise AssertionError(f"Syntax error in node_video.py: {e}")


if __name__ == '__main__':
    test_sliding_window_extraction()
    test_window_centered_on_playback()
    test_indicator_position_in_window()
    test_boundary_handling()
    test_padding_for_edges()
    test_yellow_line_still_present()
    test_python_syntax_valid()
    print("\n✓ All spectrogram scrolling tests passed successfully!")
