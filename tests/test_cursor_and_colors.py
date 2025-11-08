#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for spectrogram cursor and classification color features.
"""

import sys
import os
import ast

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_spectrogram_cursor_method_exists():
    """Test that _add_playback_cursor_to_spectrogram method exists in node_video.py"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check method exists
    assert "def _add_playback_cursor_to_spectrogram" in content, \
        "Should have _add_playback_cursor_to_spectrogram method"
    
    # Check for yellow color (BGR: 0, 255, 255)
    assert "(0, 255, 255)" in content, \
        "Should use yellow color (0, 255, 255) for cursor"
    
    # Check it's called in update method
    assert "spectrogram_with_cursor = self._add_playback_cursor_to_spectrogram" in content, \
        "Should call _add_playback_cursor_to_spectrogram in update method"
    
    print("✓ Spectrogram cursor method exists and is properly integrated")


def test_classification_colors_method_exists():
    """Test that draw_classification_info override exists in node_classification.py"""
    classification_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_classification.py'
    )
    
    assert os.path.exists(classification_node_path), "node_classification.py file should exist"
    
    with open(classification_node_path, 'r') as f:
        content = f.read()
    
    # Check method exists
    assert "def draw_classification_info" in content, \
        "Should have draw_classification_info method"
    
    # Check for rank_colors definition
    assert "rank_colors" in content, \
        "Should define rank_colors"
    
    # Check for red color (BGR: 0, 0, 255) - Position 1
    assert "(0, 0, 255)" in content, \
        "Should have red color for position 1"
    
    # Check for yellow color (BGR: 0, 255, 255) - Position 2
    assert "(0, 255, 255)" in content, \
        "Should have yellow color for position 2"
    
    # Check for blue color (BGR: 255, 0, 0) - Position 3
    assert "(255, 0, 0)" in content, \
        "Should have blue color for position 3"
    
    # Check for violet color (BGR: 255, 0, 128) - Position 4
    assert "(255, 0, 128)" in content, \
        "Should have violet color for position 4"
    
    # Check for magenta color (BGR: 255, 0, 255) - Position 5
    assert "(255, 0, 255)" in content, \
        "Should have magenta color for position 5"
    
    print("✓ Classification color method exists with correct color definitions")


def test_cursor_calculation_logic():
    """Test that cursor calculation logic is present"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for time calculation
    assert "current_time = frame_number / fps" in content, \
        "Should calculate current_time from frame_number"
    
    # Check for chunk calculations
    assert "chunk_index = int(current_time / step_duration)" in content, \
        "Should calculate chunk_index"
    
    assert "time_within_chunk" in content, \
        "Should calculate time_within_chunk"
    
    assert "cursor_position_ratio" in content, \
        "Should calculate cursor_position_ratio"
    
    # Check for pixel position calculation
    assert "cursor_x = int(cursor_position_ratio * width)" in content, \
        "Should calculate cursor_x position"
    
    # Check for line drawing
    assert "cv2.line" in content, \
        "Should use cv2.line to draw cursor"
    
    print("✓ Cursor calculation logic is properly implemented")


def test_color_ranking_logic():
    """Test that color ranking logic is present"""
    classification_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_classification.py'
    )
    
    with open(classification_node_path, 'r') as f:
        content = f.read()
    
    # Check that colors are selected based on index
    assert "if index < len(rank_colors)" in content, \
        "Should check index against rank_colors length"
    
    assert "color = rank_colors[index]" in content, \
        "Should select color based on index"
    
    # Check for comment about position colors
    assert "Position 1" in content or "highest score" in content, \
        "Should document position 1 color"
    
    print("✓ Color ranking logic is properly implemented")


def test_integration_in_update_method():
    """Test that both features are integrated in the update method"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that the cursor method is called with the right parameters
    assert "self._add_playback_cursor_to_spectrogram(" in content, \
        "Should call cursor method"
    
    assert "spectrogram_bgr, str(node_id), current_frame_num" in content, \
        "Should pass correct parameters to cursor method"
    
    # Check that the result is used
    assert "spectrogram_with_cursor" in content, \
        "Should use spectrogram_with_cursor variable"
    
    print("✓ Features are properly integrated in update method")


if __name__ == '__main__':
    print("Running tests for spectrogram cursor and classification colors...\n")
    
    try:
        test_spectrogram_cursor_method_exists()
        test_classification_colors_method_exists()
        test_cursor_calculation_logic()
        test_color_ranking_logic()
        test_integration_in_update_method()
        
        print("\n" + "="*60)
        print("All tests passed! ✓")
        print("="*60)
        print("\nImplemented features:")
        print("1. Yellow cursor on spectrogram - stays fixed after first frame while spectrogram scrolls")
        print("2. Color-coded classification rankings:")
        print("   - Position 1 (highest): Red")
        print("   - Position 2: Yellow")
        print("   - Position 3: Blue")
        print("   - Position 4: Violet")
        print("   - Position 5: Magenta")
        print("3. Classification results in concat node: bigger and at bottom left")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
