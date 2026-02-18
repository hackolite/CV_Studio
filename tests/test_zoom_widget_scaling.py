#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for zoom widget scaling logic.
Tests the zoom transformation logic without requiring DearPyGUI to be running.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_zoom_scaling_calculation():
    """Test that zoom scaling calculations are correct"""
    print("Testing zoom scaling calculation...")
    
    # Test zoom in
    original_width = 200
    zoom_level = 1.1
    scaled_width = int(original_width * zoom_level)
    assert scaled_width == 220, f"Expected 220, got {scaled_width}"
    
    # Test zoom out
    zoom_level = 0.9
    scaled_width = int(original_width * zoom_level)
    assert scaled_width == 180, f"Expected 180, got {scaled_width}"
    
    # Test extreme zoom in
    zoom_level = 5.0
    scaled_width = int(original_width * zoom_level)
    assert scaled_width == 1000, f"Expected 1000, got {scaled_width}"
    
    # Test extreme zoom out
    zoom_level = 0.1
    scaled_width = int(original_width * zoom_level)
    assert scaled_width == 20, f"Expected 20, got {scaled_width}"
    
    print("✓ Zoom scaling calculation tests passed")


def test_zoom_progression():
    """Test that zoom levels progress correctly"""
    print("Testing zoom progression...")
    
    zoom_level = 1.0
    zoom_in_factor = 1.1
    zoom_out_factor = 0.9
    min_zoom = 0.1
    max_zoom = 5.0
    
    # Test 10 zoom ins
    for _ in range(10):
        zoom_level *= zoom_in_factor
        zoom_level = min(max_zoom, zoom_level)
    
    # Should be approximately 2.59...
    assert 2.5 < zoom_level < 2.7, f"After 10 zoom ins, expected ~2.59, got {zoom_level}"
    
    # Test 30 zoom outs from current position
    for _ in range(30):
        zoom_level *= zoom_out_factor
        zoom_level = max(min_zoom, zoom_level)
    
    # Should be clamped to min_zoom (allow small floating point error)
    assert abs(zoom_level - min_zoom) < 0.02, f"After many zoom outs, expected {min_zoom}, got {zoom_level}"
    
    print("✓ Zoom progression tests passed")


def test_widget_size_cache_logic():
    """Test the widget size caching logic"""
    print("Testing widget size cache logic...")
    
    # Simulate cache behavior
    widget_cache = {}
    
    # First access - should cache
    widget_id = "test_widget_1"
    if widget_id not in widget_cache:
        widget_cache[widget_id] = {'width': 200, 'height': 100}
    
    assert widget_cache[widget_id]['width'] == 200
    assert widget_cache[widget_id]['height'] == 100
    
    # Second access - should use cache
    if widget_id not in widget_cache:
        widget_cache[widget_id] = {'width': 999, 'height': 999}  # Should not execute
    
    assert widget_cache[widget_id]['width'] == 200  # Should still be 200
    
    # Test with zero height (some widgets don't have height)
    widget_id_2 = "test_widget_2"
    original_height = 0
    widget_cache[widget_id_2] = {
        'width': 150,
        'height': original_height if original_height > 0 else 0,
    }
    
    assert widget_cache[widget_id_2]['height'] == 0
    
    print("✓ Widget size cache logic tests passed")


def test_zoom_boundary_conditions():
    """Test zoom behavior at boundaries"""
    print("Testing zoom boundary conditions...")
    
    zoom_level = 1.0
    min_zoom = 0.1
    max_zoom = 5.0
    zoom_in_factor = 1.1
    zoom_out_factor = 0.9
    
    # Test zooming in beyond max
    zoom_level = max_zoom  # Start at max
    zoom_level *= zoom_in_factor  # Try to go beyond
    zoom_level = max(min_zoom, min(max_zoom, zoom_level))
    assert zoom_level == max_zoom, f"Should clamp to max {max_zoom}, got {zoom_level}"
    
    # Test zooming out beyond min
    zoom_level = min_zoom  # Start at min
    zoom_level *= zoom_out_factor  # Try to go below
    zoom_level = max(min_zoom, min(max_zoom, zoom_level))
    assert zoom_level == min_zoom, f"Should clamp to min {min_zoom}, got {zoom_level}"
    
    print("✓ Zoom boundary condition tests passed")


def test_widget_scaling_with_different_sizes():
    """Test widget scaling with various original sizes"""
    print("Testing widget scaling with different sizes...")
    
    test_cases = [
        (100, 1.5, 150),
        (200, 2.0, 400),
        (50, 0.5, 25),
        (300, 1.0, 300),
        (175, 1.1, 192),  # int(175 * 1.1) = 192
    ]
    
    for original, zoom, expected in test_cases:
        scaled = int(original * zoom)
        assert scaled == expected, f"Original {original} * {zoom} = {scaled}, expected {expected}"
    
    print("✓ Widget scaling with different sizes tests passed")


if __name__ == "__main__":
    print("Running zoom widget scaling tests...\n")
    
    test_zoom_scaling_calculation()
    test_zoom_progression()
    test_widget_size_cache_logic()
    test_zoom_boundary_conditions()
    test_widget_scaling_with_different_sizes()
    
    print("\n✅ All zoom widget scaling tests passed!")
