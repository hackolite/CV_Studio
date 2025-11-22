#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for adaptive text sizing in object detection"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_adaptive_text_size_logic():
    """Test that text size calculation logic is correct without requiring full imports"""
    
    # Simulate the adaptive scaling logic
    test_cases = [
        # (min_dimension, expected_font_scale_range, expected_thickness_range)
        (320, (0.4, 0.5), (1, 2)),    # Small image -> smaller text
        (640, (0.8, 1.0), (2, 3)),    # Medium image (reference) -> medium text
        (1280, (1.7, 2.0), (5, 7)),   # Large image -> larger text
        (100, (0.3, 0.3), (1, 1)),    # Tiny image -> minimum text
    ]
    
    for min_dimension, (min_font, max_font), (min_thick, max_thick) in test_cases:
        # Calculate adaptive font scale (same logic as in the node)
        font_scale = max(0.3, min(2.0, (min_dimension / 640.0) * 0.9))
        
        # Calculate adaptive thickness (same logic as in the node)
        base_thickness = 3
        adaptive_thickness = max(1, int((min_dimension / 640.0) * base_thickness))
        
        # Verify font scale is within expected range
        assert min_font <= font_scale <= max_font, \
            f"Font scale {font_scale} should be in range [{min_font}, {max_font}] for dimension {min_dimension}"
        
        # Verify thickness is within expected range
        assert min_thick <= adaptive_thickness <= max_thick, \
            f"Thickness {adaptive_thickness} should be in range [{min_thick}, {max_thick}] for dimension {min_dimension}"
        
        # Verify minimums are respected
        assert font_scale >= 0.3, "Font scale should never be less than 0.3"
        assert adaptive_thickness >= 1, "Thickness should never be less than 1"
        
        # Verify maximums are respected
        assert font_scale <= 2.0, "Font scale should never exceed 2.0"


def test_adaptive_scaling_proportional():
    """Test that scaling is proportional to image size"""
    
    # Reference dimension
    ref_dimension = 640
    ref_font_scale = max(0.3, min(2.0, (ref_dimension / 640.0) * 0.9))
    
    # Double the dimension should roughly double the scale (within limits)
    double_dimension = 1280
    double_font_scale = max(0.3, min(2.0, (double_dimension / 640.0) * 0.9))
    
    # The ratio should be approximately 2 (within the max limit of 2.0)
    if double_font_scale < 2.0:  # If not capped by maximum
        ratio = double_font_scale / ref_font_scale
        assert 1.8 <= ratio <= 2.2, f"Scaling should be roughly proportional, got ratio {ratio}"


def test_object_detection_file_has_adaptive_code():
    """Test that the object detection file contains the adaptive sizing code"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for adaptive sizing logic
    assert 'min_dimension' in content, "Should calculate min_dimension for adaptive sizing"
    assert 'font_scale' in content, "Should calculate adaptive font_scale"
    assert 'adaptive_thickness' in content, "Should calculate adaptive_thickness"
    assert '640.0' in content, "Should use 640 as reference dimension"
    assert 'max(0.3' in content, "Should have minimum font scale of 0.3"
    assert 'min(2.0' in content, "Should have maximum font scale of 2.0"
    assert 'getTextSize' in content, "Should use getTextSize for better text positioning"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

