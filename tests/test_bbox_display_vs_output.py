#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for separate display vs output image in object detection"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_separate_display_and_output_frames():
    """
    Test that the object detection node correctly separates display_frame from output_frame.
    
    The requirement is:
    - Display frame (UI): ALWAYS shows bounding boxes (for visual feedback)
    - Output frame (downstream): Conditionally shows bounding boxes based on checkbox
        - Checked: Include bounding boxes (for video saving)
        - Unchecked: Clean frame (for tracking)
    """
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for separate display_frame and output_frame variables
    # Use more flexible patterns that work with various formatting
    import re
    assert re.search(r'display_frame\s*=\s*None', content), \
        "Should initialize display_frame variable"
    assert re.search(r'output_frame\s*=\s*None', content), \
        "Should initialize output_frame variable"
    
    # Check that display frame ALWAYS gets bounding boxes
    assert re.search(r'display_frame\s*=\s*copy\.deepcopy\s*\(\s*frame\s*\)', content), \
        "Display frame should be created with deepcopy"
    assert re.search(r'display_frame\s*=\s*self\.draw_object_detection_info\s*\(', content), \
        "Display frame should always have bounding boxes drawn"
    
    # Check that output frame respects checkbox setting
    assert re.search(r'if\s+draw_bbox\s*:', content), \
        "Should check draw_bbox for output frame"
    assert re.search(r'output_frame\s*=\s*copy\.deepcopy\s*\(\s*frame\s*\)', content), \
        "Output frame with bboxes should use deepcopy"
    assert re.search(r'output_frame\s*=\s*self\.draw_object_detection_info\s*\(', content), \
        "Output frame should draw bboxes when checkbox is checked"
    
    # Check the else clause for unchecked state - more resilient pattern
    # Look for pattern: else: ... output_frame = frame (without deepcopy)
    else_pattern = r'else\s*:\s*(?:[^\n]*\n){0,3}[^\n]*output_frame\s*=\s*frame\s*(?!\s*=)'
    assert re.search(else_pattern, content, re.MULTILINE), \
        "Should send clean frame (output_frame = frame) when checkbox unchecked"
    
    # Check that UI uses display_frame (always has bboxes)
    # More complete regex that handles multiline function calls
    texture_pattern = r'texture\s*=\s*self\.convert_cv_to_dpg\s*\(\s*display_frame'
    assert re.search(texture_pattern, content, re.MULTILINE | re.DOTALL), \
        "UI texture should use display_frame (always has bboxes)"
    
    # Check that data output uses output_frame
    data_pattern = r'data\s*\[\s*["\']image["\']\s*\]\s*=\s*output_frame'
    assert re.search(data_pattern, content), \
        "Data output should use output_frame (respects checkbox)"
    
    print("✅ All checks passed!")
    print("✅ Display frame: Always shows bounding boxes")
    print("✅ Output frame: Respects checkbox setting")
    print("✅ When checked: Bounding boxes in output (for video recording)")
    print("✅ When unchecked: Clean output (for tracking)")


def test_comments_explain_behavior():
    """Test that the code has clear comments explaining the new behavior"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for explanatory comments
    assert 'Display image: ALWAYS show bounding boxes' in content, \
        "Should have comment explaining display image always shows bboxes"
    assert 'Output image: Respect checkbox setting' in content, \
        "Should have comment explaining output respects checkbox"
    assert 'for video saving vs tracking' in content or 'for video recording' in content, \
        "Should explain the use cases"
    
    print("✅ Code has clear explanatory comments")


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Separate Display vs Output Frame Implementation")
    print("=" * 70)
    
    try:
        test_separate_display_and_output_frames()
        print()
        test_comments_explain_behavior()
        print()
        print("=" * 70)
        print("ALL TESTS PASSED! ✅")
        print("=" * 70)
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"TEST FAILED! ❌")
        print(f"Error: {e}")
        print("=" * 70)
        sys.exit(1)
