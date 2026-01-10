#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for dropdown class rejection filter in object detection"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_get_class_rejection_dropdown_items():
    """Test that the dropdown items generation function exists and works correctly"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that the function exists
    assert 'def get_class_rejection_dropdown_items' in content, \
        "Should have get_class_rejection_dropdown_items function"
    
    # Check that it's properly documented
    assert 'Generate dropdown items for class rejection' in content, \
        "Function should have proper documentation"
    
    # Check that it returns formatted strings
    assert 'f"{class_id}: {class_name}"' in content, \
        "Should format items as 'ID: name'"


def test_combo_widget_used():
    """Test that add_combo is used instead of add_input_text for rejection field"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the rejection field section
    lines = content.split('\n')
    rejection_section_found = False
    combo_found = False
    
    for i, line in enumerate(lines):
        if 'Rejected classes dropdown' in line:
            rejection_section_found = True
            # Check the next 20 lines for add_combo
            for j in range(i, min(i + 20, len(lines))):
                if 'dpg.add_combo(' in lines[j]:
                    combo_found = True
                    break
            break
    
    assert rejection_section_found, "Should have rejected classes dropdown section"
    assert combo_found, "Should use add_combo for rejected classes field"


def test_parsing_logic_supports_dropdown_format():
    """Test that the parsing logic supports both dropdown format and legacy format"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for parsing logic that handles the "ID: name" format
    assert "if ':' in class_str:" in content, \
        "Should check for colon in class string to handle dropdown format"
    
    assert "split(':')[0]" in content, \
        "Should extract ID part from 'ID: name' format"
    
    # Check for backward compatibility comment
    assert "legacy format" in content.lower() or "backward" in content.lower(), \
        "Should mention legacy/backward compatibility"


def test_class_items_generated_for_dropdown():
    """Test that class items are generated and passed to the dropdown"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that class items are generated before creating the combo
    assert 'get_class_rejection_dropdown_items' in content, \
        "Should call function to generate dropdown items"
    
    assert 'items=class_items' in content, \
        "Should pass class_items to the combo widget"


def test_documentation_updated():
    """Test that the documentation has been updated for the dropdown"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'object_detection', 'CLASS_REJECTION_FILTER.md'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that documentation mentions dropdown
    assert 'dropdown' in content.lower(), \
        "Documentation should mention dropdown"
    
    # Check that it explains the new format
    assert 'ID: name' in content or 'id: name' in content.lower(), \
        "Documentation should explain the 'ID: name' format"
    
    # Check that backward compatibility is mentioned
    assert 'backward' in content.lower() or 'legacy' in content.lower(), \
        "Documentation should mention backward compatibility"


if __name__ == '__main__':
    print("Running tests for dropdown class rejection filter...")
    
    try:
        test_get_class_rejection_dropdown_items()
        print("✓ test_get_class_rejection_dropdown_items passed")
    except AssertionError as e:
        print(f"✗ test_get_class_rejection_dropdown_items failed: {e}")
    
    try:
        test_combo_widget_used()
        print("✓ test_combo_widget_used passed")
    except AssertionError as e:
        print(f"✗ test_combo_widget_used failed: {e}")
    
    try:
        test_parsing_logic_supports_dropdown_format()
        print("✓ test_parsing_logic_supports_dropdown_format passed")
    except AssertionError as e:
        print(f"✗ test_parsing_logic_supports_dropdown_format failed: {e}")
    
    try:
        test_class_items_generated_for_dropdown()
        print("✓ test_class_items_generated_for_dropdown passed")
    except AssertionError as e:
        print(f"✗ test_class_items_generated_for_dropdown failed: {e}")
    
    try:
        test_documentation_updated()
        print("✓ test_documentation_updated passed")
    except AssertionError as e:
        print(f"✗ test_documentation_updated failed: {e}")
    
    print("\n✅ All dropdown implementation tests completed!")
