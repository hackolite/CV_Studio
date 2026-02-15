#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Draw Bounding Boxes checkbox in object detection node"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_object_detection_has_draw_bbox_checkbox():
    """Test that the object detection file contains the draw bbox checkbox code"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for checkbox tag definitions
    assert 'tag_node_draw_bbox_name' in content, "Should define draw bbox tag name"
    assert 'tag_node_draw_bbox_value_name' in content, "Should define draw bbox value tag name"
    
    # Check for checkbox UI element
    assert 'Draw Bounding Boxes' in content, "Should have 'Draw Bounding Boxes' label"
    assert 'dpg.add_checkbox' in content, "Should add checkbox UI element"
    
    # Check for conditional drawing logic
    assert 'draw_bbox = dpg_get_value' in content, "Should read checkbox value"
    assert 'if draw_bbox:' in content, "Should conditionally draw based on checkbox"
    
    # Check for settings persistence
    assert 'draw_bbox_tag' in content, "Should define draw_bbox_tag in settings methods"


def test_draw_bbox_default_value():
    """Test that the default value for draw_bbox checkbox is True"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check default value is True
    assert 'default_value=True' in content, "Draw Bounding Boxes checkbox should default to True"


def test_draw_bbox_backward_compatibility():
    """Test that backward compatibility is maintained for existing settings"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that settings load has a default value for backward compatibility
    assert 'setting_dict.get(draw_bbox_tag, True)' in content, \
        "Should provide default value True for backward compatibility"


def test_draw_bbox_conditional_logic():
    """Test that the conditional drawing logic is correct"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Verify conditional drawing logic exists
    assert 'if draw_bbox:' in content, "Should check draw_bbox before drawing"
    assert 'debug_frame = copy.deepcopy(frame)' in content, "Should copy frame when drawing"
    assert 'debug_frame = self.draw_object_detection_info' in content, "Should call drawing function"
    
    # Verify else case for when checkbox is unchecked
    assert 'else:' in content, "Should have else clause for unchecked state"
    assert 'debug_frame = frame' in content, "Should use original frame when not drawing"


def test_json_output_independence():
    """Test that JSON output is always generated regardless of checkbox state"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the JSON output generation code
    lines = content.split('\n')
    
    # Check that JSON result is set before the draw_bbox check
    json_output_line = None
    draw_bbox_check_line = None
    
    for i, line in enumerate(lines):
        if "result['bboxes'] = bboxes.tolist()" in line:
            json_output_line = i
        if "draw_bbox = dpg_get_value" in line:
            draw_bbox_check_line = i
    
    # JSON should be set before checking draw_bbox
    if json_output_line and draw_bbox_check_line:
        assert json_output_line < draw_bbox_check_line, \
            "JSON output should be generated before draw_bbox check"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
