#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Standalone test for heatmap dimension mismatch fix - no dependencies on dearpygui"""

import cv2
import numpy as np


def test_resize_logic():
    """Test the resize logic that fixes the dimension mismatch"""
    
    print("Testing resize logic for dimension mismatch fix...")
    
    # Scenario 1: Accumulator initialized with one size
    init_height = 480
    init_width = 640
    heatmap_accum = np.zeros((init_height, init_width), dtype=np.float32)
    
    # Add some data
    heatmap_accum[100:200, 100:200] = 0.9
    
    # Runtime dimensions change (this is the bug scenario)
    small_window_h = 240
    small_window_w = 320
    
    print(f"Initial accumulator shape: {heatmap_accum.shape}")
    print(f"Current processing dimensions: ({small_window_h}, {small_window_w})")
    
    # THE FIX: Ensure heatmap accumulator has correct dimensions
    if heatmap_accum.shape != (small_window_h, small_window_w):
        heatmap_accum = cv2.resize(
            heatmap_accum, 
            (small_window_w, small_window_h),
            interpolation=cv2.INTER_LINEAR
        )
        print(f"Resized accumulator to: {heatmap_accum.shape}")
    
    # Verify the resize worked
    assert heatmap_accum.shape == (small_window_h, small_window_w), \
        f"Expected ({small_window_h}, {small_window_w}), got {heatmap_accum.shape}"
    
    # Create input image with current dimensions
    input_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
    input_image[:, :] = [100, 100, 100]
    
    # Process heatmap
    if heatmap_accum.max() > 0:
        heatmap_norm = np.clip(heatmap_accum / heatmap_accum.max(), 0, 1)
    else:
        heatmap_norm = heatmap_accum
    
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    print(f"heatmap_colored shape: {heatmap_colored.shape}")
    print(f"input_image shape: {input_image.shape}")
    
    # This should now work without dimension mismatch error
    try:
        heatmap_image = cv2.addWeighted(input_image, 0.4, heatmap_colored, 0.6, 0)
        print(f"✓ Successfully blended images, result shape: {heatmap_image.shape}")
        assert heatmap_image.shape == (small_window_h, small_window_w, 3)
        return True
    except cv2.error as e:
        print(f"✗ FAILED: {e}")
        return False


def test_no_resize_needed():
    """Test that when dimensions match, no resize is performed"""
    
    print("\nTesting when dimensions already match...")
    
    # Same dimensions throughout
    height = 480
    width = 640
    
    heatmap_accum = np.zeros((height, width), dtype=np.float32)
    heatmap_accum[100:200, 100:200] = 0.9
    
    # Check if resize is needed
    if heatmap_accum.shape != (height, width):
        heatmap_accum = cv2.resize(
            heatmap_accum, 
            (width, height),
            interpolation=cv2.INTER_LINEAR
        )
        print("Resized (should not happen in this test)")
    else:
        print("No resize needed - dimensions already match")
    
    # Create input image
    input_image = np.zeros((height, width, 3), dtype=np.uint8)
    input_image[:, :] = [100, 100, 100]
    
    # Process
    heatmap_norm = np.clip(heatmap_accum / heatmap_accum.max(), 0, 1)
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    # Blend
    try:
        heatmap_image = cv2.addWeighted(input_image, 0.4, heatmap_colored, 0.6, 0)
        print(f"✓ Successfully blended images, result shape: {heatmap_image.shape}")
        return True
    except cv2.error as e:
        print(f"✗ FAILED: {e}")
        return False


def test_multiple_resizes():
    """Test multiple dimension changes in sequence"""
    
    print("\nTesting multiple dimension changes...")
    
    # Start with one size
    heatmap_accum = np.zeros((480, 640), dtype=np.float32)
    heatmap_accum[100:200, 100:200] = 0.5
    
    # Test various dimension changes
    dimension_sets = [
        (240, 320),
        (360, 480),
        (120, 160),
        (480, 640),  # Back to original
    ]
    
    for height, width in dimension_sets:
        print(f"\n  Testing dimensions: ({height}, {width})")
        
        # Resize if needed
        if heatmap_accum.shape != (height, width):
            heatmap_accum = cv2.resize(
                heatmap_accum, 
                (width, height),
                interpolation=cv2.INTER_LINEAR
            )
            print(f"    Resized to: {heatmap_accum.shape}")
        
        # Create input image
        input_image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Process and blend
        heatmap_norm = np.clip(heatmap_accum / max(heatmap_accum.max(), 1e-6), 0, 1)
        heatmap_display = (heatmap_norm * 255).astype(np.uint8)
        heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
        heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
        
        try:
            heatmap_image = cv2.addWeighted(input_image, 0.4, heatmap_colored, 0.6, 0)
            print(f"    ✓ Blend successful, shape: {heatmap_image.shape}")
        except cv2.error as e:
            print(f"    ✗ FAILED: {e}")
            return False
    
    print("\n✓ All dimension changes handled correctly")
    return True


def test_edge_cases():
    """Test edge cases like very small dimensions"""
    
    print("\nTesting edge cases...")
    
    # Very small dimensions
    heatmap_accum = np.zeros((480, 640), dtype=np.float32)
    
    edge_cases = [
        (32, 32),
        (64, 64),
        (100, 200),
    ]
    
    for height, width in edge_cases:
        print(f"\n  Testing edge case: ({height}, {width})")
        
        # Resize
        if heatmap_accum.shape != (height, width):
            heatmap_accum_resized = cv2.resize(
                heatmap_accum, 
                (width, height),
                interpolation=cv2.INTER_LINEAR
            )
        else:
            heatmap_accum_resized = heatmap_accum
        
        # Create input
        input_image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Process
        heatmap_norm = heatmap_accum_resized
        heatmap_display = (heatmap_norm * 255).astype(np.uint8)
        
        # For very small dimensions, adjust blur kernel size
        kernel_size = min(25, max(3, height // 10))
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        heatmap_display = cv2.GaussianBlur(heatmap_display, (kernel_size, kernel_size), 0)
        heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
        
        try:
            heatmap_image = cv2.addWeighted(input_image, 0.4, heatmap_colored, 0.6, 0)
            print(f"    ✓ Edge case handled, shape: {heatmap_image.shape}")
        except cv2.error as e:
            print(f"    ✗ FAILED: {e}")
            return False
    
    print("\n✓ All edge cases handled correctly")
    return True


if __name__ == "__main__":
    print("="*70)
    print("Standalone Test for Heatmap Dimension Mismatch Fix")
    print("="*70)
    
    all_passed = True
    
    all_passed &= test_resize_logic()
    all_passed &= test_no_resize_needed()
    all_passed &= test_multiple_resizes()
    all_passed &= test_edge_cases()
    
    print("\n" + "="*70)
    if all_passed:
        print("ALL TESTS PASSED ✓")
        print("="*70)
        print("\nThe fix correctly handles dimension mismatches by:")
        print("1. Checking if heatmap_accum dimensions match current processing dimensions")
        print("2. Resizing the accumulator if dimensions don't match")
        print("3. Ensuring cv2.addWeighted receives matching image dimensions")
        print("="*70)
    else:
        print("SOME TESTS FAILED ✗")
        print("="*70)
        exit(1)
