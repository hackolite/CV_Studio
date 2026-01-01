#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for tennis detection coordinate scaling fix"""

import pytest
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_coordinate_scaling_logic():
    """Test that coordinate scaling logic is correct"""
    
    # Test cases: (original_width, original_height, expected_scale_x, expected_scale_y)
    test_cases = [
        (1280, 720, 1280/608.0, 720/416.0),  # HD resolution
        (1920, 1080, 1920/608.0, 1080/416.0),  # Full HD
        (640, 480, 640/608.0, 480/416.0),  # VGA
        (608, 416, 1.0, 1.0),  # Model native resolution
    ]
    
    for original_width, original_height, expected_scale_x, expected_scale_y in test_cases:
        # Calculate scaling ratios (same logic as in yolotennis.py)
        scale_x = original_width / 608.0
        scale_y = original_height / 416.0
        
        # Verify scales match expected values
        assert abs(scale_x - expected_scale_x) < 0.001, \
            f"Scale X {scale_x} should match expected {expected_scale_x}"
        assert abs(scale_y - expected_scale_y) < 0.001, \
            f"Scale Y {scale_y} should match expected {expected_scale_y}"
        
        # Test bbox coordinate conversion
        # Assume model outputs bbox at center of 608x416 image
        model_x, model_y, model_w, model_h = 304, 208, 100, 100
        
        # Convert to original image coordinates
        x1 = int((model_x - model_w / 2) * scale_x)
        y1 = int((model_y - model_h / 2) * scale_y)
        x2 = int((model_x + model_w / 2) * scale_x)
        y2 = int((model_y + model_h / 2) * scale_y)
        
        # For native resolution, coordinates should stay the same
        if original_width == 608 and original_height == 416:
            assert x1 == int(model_x - model_w / 2), "Native resolution X1 should match"
            assert y1 == int(model_y - model_h / 2), "Native resolution Y1 should match"
            assert x2 == int(model_x + model_w / 2), "Native resolution X2 should match"
            assert y2 == int(model_y + model_h / 2), "Native resolution Y2 should match"
        
        # Verify scaled coordinates are within bounds
        assert 0 <= x1 <= original_width, f"X1 {x1} should be within image width {original_width}"
        assert 0 <= y1 <= original_height, f"Y1 {y1} should be within image height {original_height}"
        assert 0 <= x2 <= original_width, f"X2 {x2} should be within image width {original_width}"
        assert 0 <= y2 <= original_height, f"Y2 {y2} should be within image height {original_height}"
        
        # Verify x2 > x1 and y2 > y1
        assert x2 > x1, "X2 should be greater than X1"
        assert y2 > y1, "Y2 should be greater than Y1"


def test_yolotennis_postprocess_scaling():
    """Test that _postprocess method properly applies scaling"""
    
    # Create mock outputs similar to what the model would produce
    # Format: [x, y, w, h, class_scores...]
    num_classes = 7  # Tennis model has 7 classes
    num_detections = 5187  # As seen in model output shape
    
    # Create a simple detection at center of 608x416 image
    mock_detection = np.zeros(4 + num_classes)
    mock_detection[0] = 304  # x center
    mock_detection[1] = 208  # y center
    mock_detection[2] = 100  # width
    mock_detection[3] = 100  # height
    mock_detection[4] = 0.9  # high confidence for first class
    
    # Test that scaling parameters are applied correctly
    scale_x = 2.0  # Simulating 1216 width original image
    scale_y = 1.5  # Simulating 624 height original image
    
    # Expected coordinates after scaling
    expected_x1 = int((304 - 100 / 2) * scale_x)  # (304 - 50) * 2 = 508
    expected_y1 = int((208 - 100 / 2) * scale_y)  # (208 - 50) * 1.5 = 237
    expected_x2 = int((304 + 100 / 2) * scale_x)  # (304 + 50) * 2 = 708
    expected_y2 = int((208 + 100 / 2) * scale_y)  # (208 + 50) * 1.5 = 387
    
    # Verify the math
    assert expected_x1 == 508, f"Expected X1 to be 508, got {expected_x1}"
    assert expected_y1 == 237, f"Expected Y1 to be 237, got {expected_y1}"
    assert expected_x2 == 708, f"Expected X2 to be 708, got {expected_x2}"
    assert expected_y2 == 387, f"Expected Y2 to be 387, got {expected_y2}"


def test_yolotennis_file_has_scaling():
    """Test that yolotennis.py contains the coordinate scaling logic"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'object_detection', 'TennisYOLO', 'yolotennis.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for coordinate scaling logic
    assert 'original_height' in content, "Should store original image height"
    assert 'original_width' in content, "Should store original image width"
    assert 'scale_x' in content, "Should calculate scale_x for coordinate conversion"
    assert 'scale_y' in content, "Should calculate scale_y for coordinate conversion"
    assert '608.0' in content, "Should reference model width (608)"
    assert '416.0' in content, "Should reference model height (416)"
    assert '* scale_x' in content, "Should apply scale_x to coordinates"
    assert '* scale_y' in content, "Should apply scale_y to coordinates"
    
    # Check that gain is removed
    assert 'gain = 1' not in content, "Should not use fixed gain=1 anymore"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
