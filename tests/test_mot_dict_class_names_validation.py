#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for MOT node validation with dict class_names (object detection format).

This test verifies that:
1. MOT node accepts detection data with dict class_names (object detection format)
2. MOT node accepts extra keys like score_th from object detection
3. MOT node still works with legacy list class_names format
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_mot_validation_dict_class_names():
    """Test that MOT validation accepts dict class_names from object detection"""
    from node.TrackerNode.node_mot import Node as MOTNode
    
    print("Testing MOT validation with dict class_names...")
    
    # Create MOT node instance
    mot_node = MOTNode()
    
    # Test 1: Object detection format with dict class_names and score_th
    print("  Test 1: Object detection format (dict class_names + score_th)")
    detection_data_dict = {
        'bboxes': [[100, 100, 200, 200], [300, 300, 400, 400]],
        'scores': [0.95, 0.87],
        'class_ids': [0, 1],
        'class_names': {0: 'person', 1: 'car'},  # Dict format from object detection
        'score_th': 0.3  # Extra key from object detection
    }
    result = mot_node._is_valid_detection_format(detection_data_dict)
    assert result is True, "Should accept dict class_names with score_th"
    print("    ✓ PASSED: Dict class_names accepted")
    
    # Test 2: Legacy format with list class_names
    print("  Test 2: Legacy format (list class_names)")
    detection_data_list = {
        'bboxes': [[100, 100, 200, 200]],
        'scores': [0.95],
        'class_ids': [0],
        'class_names': ['person']  # List format
    }
    result = mot_node._is_valid_detection_format(detection_data_list)
    assert result is True, "Should accept list class_names"
    print("    ✓ PASSED: List class_names accepted")
    
    # Test 3: Empty detections with dict class_names
    print("  Test 3: Empty detections (dict class_names)")
    empty_data = {
        'bboxes': [],
        'scores': [],
        'class_ids': [],
        'class_names': {0: 'person', 1: 'car'},
        'score_th': 0.3
    }
    result = mot_node._is_valid_detection_format(empty_data)
    assert result is True, "Should accept empty detections"
    print("    ✓ PASSED: Empty detections accepted")
    
    # Test 4: Should reject invalid class_names type (not list/dict)
    print("  Test 4: Invalid class_names type (string)")
    invalid_data = {
        'bboxes': [[100, 100, 200, 200]],
        'scores': [0.95],
        'class_ids': [0],
        'class_names': "invalid_string"  # Invalid type
    }
    result = mot_node._is_valid_detection_format(invalid_data)
    assert result is False, "Should reject string class_names"
    print("    ✓ PASSED: Invalid type rejected")
    
    print("\nAll validation tests passed! ✓")


if __name__ == '__main__':
    test_mot_validation_dict_class_names()
    print("\n✓ All tests completed successfully")
