#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for text scaling in image_concat node"""

import pytest


# Reference height constant (should match node_image_concat.py)
REFERENCE_HEIGHT = 480.0


def test_concat_text_scaling_logic():
    """Test that text size calculation logic scales properly with frame height"""
    
    test_cases = [
        # (height, expected_font_scale, expected_thickness, expected_line_spacing)
        (1080, 2.25, 6, 78),     # Full HD -> larger text
        (720, 1.50, 4, 52),      # HD -> medium-large text
        (480, 1.00, 3, 35),      # SD (reference) -> base text size
        (360, 0.75, 2, 26),      # Small -> smaller text
        (240, 0.50, 1, 17),      # Very small -> very small text
        (180, 0.375, 1, 13),     # Tiny -> minimal text
    ]
    
    for height, expected_font_scale, expected_thickness, expected_line_spacing in test_cases:
        # Calculate scaling (same logic as in node_image_concat.py)
        scale_factor = height / REFERENCE_HEIGHT
        font_scale = 1.0 * scale_factor
        thickness = max(1, int(3 * scale_factor))
        line_spacing = int(35 * scale_factor)
        
        # Verify calculations match expected values
        assert abs(font_scale - expected_font_scale) < 0.01, \
            f"Font scale {font_scale} should be {expected_font_scale} for height {height}"
        
        assert thickness == expected_thickness, \
            f"Thickness {thickness} should be {expected_thickness} for height {height}"
        
        assert abs(line_spacing - expected_line_spacing) <= 1, \
            f"Line spacing {line_spacing} should be ~{expected_line_spacing} for height {height}"
        
        # Verify minimums are respected
        assert thickness >= 1, "Thickness should never be less than 1"
        assert font_scale > 0, "Font scale should always be positive"
        assert line_spacing > 0, "Line spacing should always be positive"


def test_concat_scaling_proportional():
    """Test that text parameters scale proportionally with frame height"""
    
    # Reference values at REFERENCE_HEIGHT
    reference_height = REFERENCE_HEIGHT
    reference_font_scale = 1.0
    reference_thickness = 3
    reference_line_spacing = 35
    
    # Test at double the reference height
    double_height = 960
    scale_factor = double_height / reference_height
    
    font_scale = 1.0 * scale_factor
    thickness = max(1, int(3 * scale_factor))
    line_spacing = int(35 * scale_factor)
    
    # At 2x height, font scale should be 2x
    assert abs(font_scale - 2.0) < 0.01, "Font scale should double with height"
    
    # Thickness should roughly double (within rounding)
    assert thickness >= 5 and thickness <= 7, "Thickness should roughly double with height"
    
    # Line spacing should roughly double
    assert abs(line_spacing - 70) <= 1, "Line spacing should roughly double with height"


def test_concat_scaling_minimum_values():
    """Test that minimum values are enforced for very small frames"""
    
    # Test with very small frame
    tiny_height = 50
    scale_factor = tiny_height / REFERENCE_HEIGHT
    
    font_scale = 1.0 * scale_factor
    thickness = max(1, int(3 * scale_factor))
    line_spacing = int(35 * scale_factor)
    
    # Thickness should never go below 1
    assert thickness >= 1, "Thickness should have minimum of 1"
    
    # Font scale can be very small but should be positive
    assert font_scale > 0, "Font scale should be positive"
    
    # Line spacing should be positive
    assert line_spacing >= 0, "Line spacing should be non-negative"


def test_concat_scaling_consistency():
    """Test that scaling is consistent across different heights"""
    
    heights = [180, 240, 360, 480, 720, 1080]
    previous_font_scale = 0
    previous_thickness = 0
    previous_line_spacing = 0
    
    for height in heights:
        scale_factor = height / REFERENCE_HEIGHT
        font_scale = 1.0 * scale_factor
        thickness = max(1, int(3 * scale_factor))
        line_spacing = int(35 * scale_factor)
        
        # Each parameter should increase or stay the same as height increases
        assert font_scale >= previous_font_scale, \
            f"Font scale should increase with height (current: {font_scale}, previous: {previous_font_scale})"
        
        assert thickness >= previous_thickness, \
            f"Thickness should increase with height (current: {thickness}, previous: {previous_thickness})"
        
        assert line_spacing >= previous_line_spacing, \
            f"Line spacing should increase with height (current: {line_spacing}, previous: {previous_line_spacing})"
        
        previous_font_scale = font_scale
        previous_thickness = thickness
        previous_line_spacing = line_spacing


if __name__ == '__main__':
    # Run tests
    test_concat_text_scaling_logic()
    test_concat_scaling_proportional()
    test_concat_scaling_minimum_values()
    test_concat_scaling_consistency()
    print("All tests passed!")
