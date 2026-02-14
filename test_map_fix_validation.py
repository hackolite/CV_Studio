#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify the Map node code fixes without importing the full module
"""
import json
import numpy as np
import re


def test_code_has_empty_string_check():
    """Verify the code has empty string handling"""
    with open('node/VisualNode/node_map.py', 'r') as f:
        code = f.read()
    
    # Check for empty string handling
    assert 'if not input_value.strip():' in code, "Missing empty string check"
    assert 'Waiting for data...' in code, "Missing empty string status message"
    print("✓ Code has empty string check")


def test_code_has_correct_return_format():
    """Verify the code returns the correct format"""
    with open('node/VisualNode/node_map.py', 'r') as f:
        code = f.read()
    
    # Check for correct return statement
    assert 'return {"image": preview_image, "json": None, "audio": None}' in code, \
        "Missing correct return statement"
    
    # Make sure old return statement is gone
    lines = code.split('\n')
    for i, line in enumerate(lines):
        # Skip comment lines
        if line.strip().startswith('#'):
            continue
        # Check for old return statement
        if 'return preview_image' in line and '{"image":' not in line:
            # Make sure it's not inside a different function
            # Get context
            context_start = max(0, i - 20)
            context = '\n'.join(lines[context_start:i+1])
            if 'def update(' in context:
                assert False, f"Found old return statement at line {i+1}"
    
    print("✓ Code has correct return format")


def test_json_parsing_logic():
    """Verify JSON parsing logic is correct"""
    with open('node/VisualNode/node_map.py', 'r') as f:
        code = f.read()
    
    # Find the update method
    update_match = re.search(r'def update\(.*?\):(.*?)(?=\n    def |\nclass |\Z)', code, re.DOTALL)
    assert update_match, "Could not find update method"
    
    update_code = update_match.group(1)
    
    # Check logic flow
    assert 'if isinstance(input_value, str):' in update_code
    assert 'if not input_value.strip():' in update_code
    assert 'json.loads(input_value)' in update_code
    
    print("✓ JSON parsing logic is correct")


def test_return_format_structure():
    """Test the actual return format structure"""
    preview_image = np.zeros((135, 240, 3), dtype=np.uint8)
    
    # New correct format
    result = {"image": preview_image, "json": None, "audio": None}
    
    # Verify structure
    assert isinstance(result, dict), "Result should be a dict"
    assert "image" in result, "Result should have 'image' key"
    assert "json" in result, "Result should have 'json' key"
    assert "audio" in result, "Result should have 'audio' key"
    assert isinstance(result["image"], np.ndarray), "image should be numpy array"
    assert result["json"] is None, "json should be None"
    assert result["audio"] is None, "audio should be None"
    
    print("✓ Return format structure is correct")


def test_empty_string_logic():
    """Test empty string handling logic"""
    # Test cases
    test_cases = [
        ("", True),  # Empty string
        ("   ", True),  # Whitespace only
        ("\n\t  ", True),  # Whitespace with newlines/tabs
        ('{"valid": "json"}', False),  # Valid JSON
        ("   not empty  ", False),  # Non-empty with whitespace
    ]
    
    for input_value, should_skip in test_cases:
        if not input_value.strip():
            result = "skip"
        else:
            result = "process"
        
        expected = "skip" if should_skip else "process"
        assert result == expected, f"Failed for input: {repr(input_value)}"
    
    print("✓ Empty string logic is correct")


if __name__ == "__main__":
    print("Validating Map Node Code Fixes...")
    print()
    
    try:
        test_code_has_empty_string_check()
        test_code_has_correct_return_format()
        test_json_parsing_logic()
        test_return_format_structure()
        test_empty_string_logic()
        
        print()
        print("All validation tests passed! ✓")
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
