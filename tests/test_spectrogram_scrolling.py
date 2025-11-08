#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for simplified spectrogram display functionality"""

import sys
import os
import ast

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_simplified_spectrogram_display():
    """Test that simplified spectrogram display code is present"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for simplified implementation
    assert "self._spectrogram_array[str(node_id)]" in content, "Should access spectrogram array"
    assert "spectrogram_bgr" in content, "Should use spectrogram_bgr variable"
    
    print("✓ Simplified spectrogram display code is present")


def test_no_complex_playback_logic():
    """Test that complex playback window extraction logic has been removed"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that complex playback logic has been removed
    assert "spectrogram_window = full_spectrogram[:, start_col:end_col].copy()" not in content, \
        "Should not have complex window extraction"
    assert "half_window" not in content, "Should not calculate half_window"
    assert "indicator_col = spectrogram_col - start_col" not in content, \
        "Should not calculate indicator relative to window"
    
    print("✓ Complex playback logic has been removed")


def test_spectrogram_toggle_exists():
    """Test that spectrogram toggle functionality is preserved"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that toggle functionality is still present
    assert "tag_node_spectrogram_toggle" in content, "Should have spectrogram toggle tag"
    assert "show_spectrogram" in content, "Should check show_spectrogram flag"
    
    print("✓ Spectrogram toggle functionality is preserved")


def test_texture_update_present():
    """Test that texture update code is present"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for texture update
    assert "convert_cv_to_dpg" in content, "Should convert to DPG format"
    assert "dpg_set_value" in content, "Should update texture value"
    
    print("✓ Texture update code is present")


def test_no_indicator_lines():
    """Test that indicator line drawing has been removed"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
        
    # Count occurrences of cv2.line in the spectrogram section
    # (There might be cv2.line elsewhere in the file for other purposes)
    # We're specifically checking that the yellow/green indicator lines are gone
    lines = content.split('\n')
    in_spectrogram_section = False
    cv2_line_count = 0
    
    for line in lines:
        if 'Update spectrogram display' in line:
            in_spectrogram_section = True
        elif 'def close' in line or 'def get_setting_dict' in line:
            in_spectrogram_section = False
        elif in_spectrogram_section and 'cv2.line' in line:
            cv2_line_count += 1
    
    assert cv2_line_count == 0, "Should not have indicator line drawing in spectrogram section"
    
    print("✓ Indicator line drawing has been removed")


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
    test_simplified_spectrogram_display()
    test_no_complex_playback_logic()
    test_spectrogram_toggle_exists()
    test_texture_update_present()
    test_no_indicator_lines()
    test_python_syntax_valid()
    print("\n✓ All simplified spectrogram tests passed successfully!")
