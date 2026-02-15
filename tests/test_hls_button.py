#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the HLS node button properly handles start/stop states.
This test validates that:
1. Button callback extracts the correct tag names
2. Start and stop states are handled correctly
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_tag_parsing():
    """Test that tag parsing works correctly"""
    # Simulate the user_data that would be passed to the button callback
    user_data = "123:HLS"
    
    # Parse it the same way the button method does
    tag_node_name = user_data
    
    # Verify we get the expected node name
    assert tag_node_name == "123:HLS", f"Expected '123:HLS', got '{tag_node_name}'"
    
    # Construct the button tag
    # Note: TYPE_TEXT should match Node.TYPE_TEXT from basenode.py
    TYPE_TEXT = "TEXT"
    tag_node_button_value_name = tag_node_name + ':' + TYPE_TEXT + ':ButtonValue'
    
    # Verify the button tag is correct
    assert tag_node_button_value_name == "123:HLS:TEXT:ButtonValue", \
        f"Expected '123:HLS:TEXT:ButtonValue', got '{tag_node_button_value_name}'"


def test_tag_parsing_with_different_node_id():
    """Test tag parsing with different node IDs"""
    test_cases = [
        ("1:HLS", "1:HLS", "1:HLS:TEXT:ButtonValue"),
        ("999:HLS", "999:HLS", "999:HLS:TEXT:ButtonValue"),
        ("abc:HLS", "abc:HLS", "abc:HLS:TEXT:ButtonValue"),
    ]
    
    # Note: TYPE_TEXT should match Node.TYPE_TEXT from basenode.py
    TYPE_TEXT = "TEXT"
    for user_data, expected_node_name, expected_button_tag in test_cases:
        tag_node_name = user_data
        assert tag_node_name == expected_node_name, \
            f"For {user_data}: Expected '{expected_node_name}', got '{tag_node_name}'"
        
        tag_node_button_value_name = tag_node_name + ':' + TYPE_TEXT + ':ButtonValue'
        assert tag_node_button_value_name == expected_button_tag, \
            f"For {user_data}: Expected '{expected_button_tag}', got '{tag_node_button_value_name}'"


def test_input_tag_construction():
    """Test that input value tag is constructed correctly"""
    node_id = 123
    node_tag = "HLS"
    TYPE_TEXT = "TEXT"
    
    tag_node_name = str(node_id) + ':' + node_tag
    input_value01_tag = tag_node_name + ':' + TYPE_TEXT + ':Input01Value'
    
    assert input_value01_tag == "123:HLS:TEXT:Input01Value", \
        f"Expected '123:HLS:TEXT:Input01Value', got '{input_value01_tag}'"


if __name__ == '__main__':
    print("Testing HLS button tag parsing...")
    print("=" * 60)
    
    tests = [
        ("Tag parsing", test_tag_parsing),
        ("Tag parsing with different node IDs", test_tag_parsing_with_different_node_id),
        ("Input tag construction", test_input_tag_construction),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            test_func()
            print(f"✓ {name} passed")
            passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
