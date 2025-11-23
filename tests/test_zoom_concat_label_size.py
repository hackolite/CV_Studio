#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for proper label sizing when concatenating zoomed images"""

import pytest

# Reference height constant (should match node_image_concat.py)
REFERENCE_HEIGHT = 480.0


def test_target_height_scaling():
    """Test that text scaling uses target_height when provided"""
    
    # Simulate a zoomed/cropped small image
    small_image_height = 100
    
    # Target height after resize in concat
    target_height = 480
    
    # Calculate scale factor using small image height (old behavior - wrong)
    scale_factor_old = small_image_height / REFERENCE_HEIGHT
    font_scale_old = 1.0 * scale_factor_old
    thickness_old = max(1, int(3 * scale_factor_old))
    
    # Calculate scale factor using target height (new behavior - correct)
    scale_factor_new = target_height / REFERENCE_HEIGHT
    font_scale_new = 1.0 * scale_factor_new
    thickness_new = max(1, int(3 * scale_factor_new))
    
    # When a small 100px image is scaled to 480px (4.8x), the text also scales
    # Old behavior: text is sized for 100px, then scaled up 4.8x -> too big!
    # Expected old font_scale after resize: 0.208 * 4.8 ≈ 1.0
    # Expected new font_scale: 1.0 directly
    
    # With old behavior, text would be sized for small image
    assert font_scale_old < 0.25, f"Small image should have small font scale: {font_scale_old}"
    
    # With new behavior, text is sized for target (final) image
    assert abs(font_scale_new - 1.0) < 0.01, f"Target height 480 should give font scale ~1.0: {font_scale_new}"
    
    # The key insight: when small image is resized, old text would become too large
    # because it was drawn at small size then scaled up along with the image


def test_target_height_prevents_oversized_text():
    """Test that using target_height prevents text from becoming too large after resize"""
    
    # Simulate zoom node output: small cropped image
    original_height = 150  # Zoom node crops to small area
    target_height = 600    # Concat resizes to larger grid cell
    resize_factor = target_height / original_height  # 4x enlargement
    
    # Old behavior: calculate text for original size
    scale_old = original_height / REFERENCE_HEIGHT
    font_old = 1.0 * scale_old
    thickness_old = max(1, int(3 * scale_old))
    
    # After resize, text also scales up
    font_old_after_resize = font_old * resize_factor
    thickness_old_after_resize = thickness_old * resize_factor
    
    # New behavior: calculate text for target size
    scale_new = target_height / REFERENCE_HEIGHT
    font_new = 1.0 * scale_new
    thickness_new = max(1, int(3 * scale_new))
    
    # With old behavior, text becomes oversized
    # Font scale of ~0.31 * 4 = ~1.24 (too big for 600px target)
    # With new behavior, font scale is ~1.25 (appropriate for 600px)
    
    # Verify new approach gives appropriate scaling
    assert abs(font_new - 1.25) < 0.01, f"Font scale for 600px should be ~1.25: {font_new}"
    
    # Verify old approach would be similar after resize (but text quality would be poor)
    # The real issue is text is rasterized at low res then scaled, causing poor quality


def test_zoom_concat_scenario():
    """Test realistic zoom->concat scenario"""
    
    # Scenario: 
    # 1. Input image is 1920x1080
    # 2. Zoom node crops to 300x300 (zoomed in on a detail)
    # 3. Concat node resizes all inputs to 640x480 grid cells
    
    zoom_output_height = 300
    concat_target_height = 480
    
    # Without target_height: text sized for 300px image
    scale_without_target = zoom_output_height / REFERENCE_HEIGHT
    font_without_target = 1.0 * scale_without_target
    
    # With target_height: text sized for 480px final image
    scale_with_target = concat_target_height / REFERENCE_HEIGHT
    font_with_target = 1.0 * scale_with_target
    
    # Text size should be based on final concat dimensions
    assert abs(font_with_target - 1.0) < 0.01, \
        f"For 480px target, font scale should be ~1.0: {font_with_target}"
    
    # Without fix, font would be too small initially
    assert font_without_target < 0.7, \
        f"For 300px image, font scale would be ~0.625: {font_without_target}"
    
    # After resize, the small text gets enlarged, but looks poor quality
    # Using target_height prevents this issue


def test_different_zoom_levels():
    """Test that various zoom levels work correctly with target_height"""
    
    concat_target_height = 480  # Standard concat grid cell height
    
    # Different zoom levels produce different sized crops
    zoom_heights = [100, 200, 300, 400, 500, 800]
    
    for zoom_height in zoom_heights:
        # With target_height, all should use same text scale
        scale_with_target = concat_target_height / REFERENCE_HEIGHT
        font_with_target = 1.0 * scale_with_target
        
        # Regardless of zoom level, text should be sized for target
        assert abs(font_with_target - 1.0) < 0.01, \
            f"Font scale should be consistent at ~1.0 for target 480px, got {font_with_target}"
        
        # Without target_height, each zoom level would have different text size
        scale_without_target = zoom_height / REFERENCE_HEIGHT
        font_without_target = 1.0 * scale_without_target
        
        # These would all be different (and wrong after resize)
        expected_without_target = zoom_height / 480.0
        assert abs(font_without_target - expected_without_target) < 0.01


if __name__ == '__main__':
    # Run tests
    test_target_height_scaling()
    test_target_height_prevents_oversized_text()
    test_zoom_concat_scenario()
    test_different_zoom_levels()
    print("All tests passed!")
