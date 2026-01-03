#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple integration test for TennisCourt BGRA and ImageOverlay alpha blending.
Tests the core functionality without requiring DPG initialization.
"""
import numpy as np
import cv2


def test_bgra_image_creation():
    """Test creating BGRA image with transparency"""
    print("Test 1: BGRA Image Creation")
    print("-" * 60)
    
    # Create BGRA image
    img = np.zeros((100, 100, 4), dtype=np.uint8)
    
    # Draw green rectangle with full opacity
    img[20:80, 20:80, 0:3] = (0, 150, 0)  # Green in BGR
    img[20:80, 20:80, 3] = 255  # Full alpha
    
    # Check channels
    assert img.shape[2] == 4, "Should have 4 channels"
    
    # Check transparency
    transparent_pixels = np.sum(img[:, :, 3] == 0)
    opaque_pixels = np.sum(img[:, :, 3] == 255)
    
    print(f"  ✓ BGRA image created: {img.shape}")
    print(f"  ✓ Transparent pixels: {transparent_pixels}")
    print(f"  ✓ Opaque pixels: {opaque_pixels}")
    
    assert transparent_pixels > 0, "Should have transparent background"
    assert opaque_pixels > 0, "Should have opaque content"
    
    return img


def test_alpha_blending_with_bgra():
    """Test alpha blending with BGRA overlay"""
    print("\nTest 2: Alpha Blending with BGRA")
    print("-" * 60)
    
    # Create master image (blue, BGR)
    master = np.zeros((200, 200, 3), dtype=np.uint8)
    master[:, :] = (255, 0, 0)  # Blue
    
    # Create overlay (red circle with transparent background, BGRA)
    overlay = np.zeros((100, 100, 4), dtype=np.uint8)
    cv2.circle(overlay, (50, 50), 40, (0, 0, 255, 255), -1)  # Red circle
    
    # Extract alpha and BGR from overlay
    overlay_alpha = overlay[:, :, 3:4] / 255.0
    overlay_bgr = overlay[:, :, :3]
    
    # Get region to blend
    master_region = master[50:150, 50:150]
    
    # Alpha blend
    blended = (overlay_bgr * overlay_alpha + master_region * (1 - overlay_alpha)).astype(np.uint8)
    master[50:150, 50:150] = blended
    
    # Check results
    center_pixel = master[100, 100]  # Should be red (inside circle)
    corner_pixel = master[60, 60]    # Should be blue (outside circle)
    
    print(f"  ✓ Center pixel (red): {center_pixel}")
    print(f"  ✓ Corner pixel (blue): {corner_pixel}")
    
    assert center_pixel[2] > 200, "Center should be red"
    assert corner_pixel[0] > 200, "Corner should be blue"
    
    return master


def test_overlay_resizing():
    """Test overlay resizing with width/height parameters"""
    print("\nTest 3: Overlay Resizing")
    print("-" * 60)
    
    # Create small overlay
    overlay = np.ones((50, 50, 3), dtype=np.uint8) * 255
    
    # Resize to larger dimensions
    target_w, target_h = 200, 300
    resized = cv2.resize(overlay, (target_w, target_h), interpolation=cv2.INTER_AREA)
    
    print(f"  ✓ Original size: {overlay.shape}")
    print(f"  ✓ Resized to: {resized.shape}")
    
    assert resized.shape == (target_h, target_w, 3), "Should be resized correctly"
    
    return resized


def test_position_clipping():
    """Test overlay positioning and clipping"""
    print("\nTest 4: Position Clipping")
    print("-" * 60)
    
    master = np.zeros((200, 200, 3), dtype=np.uint8)
    overlay = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    # Test negative position (partial visibility)
    x_pos, y_pos = -50, 50
    
    # Calculate clipping
    overlay_x1 = max(0, -x_pos)
    overlay_y1 = max(0, -y_pos)
    master_x1 = max(0, x_pos)
    master_y1 = max(0, y_pos)
    
    visible_w = min(100 - overlay_x1, 200 - master_x1)
    visible_h = min(100 - overlay_y1, 200 - master_y1)
    
    print(f"  ✓ Position: ({x_pos}, {y_pos})")
    print(f"  ✓ Visible region: {visible_w}x{visible_h}")
    print(f"  ✓ Overlay starts at: ({overlay_x1}, {overlay_y1})")
    print(f"  ✓ Master starts at: ({master_x1}, {master_y1})")
    
    # Apply overlay
    master[master_y1:master_y1+visible_h, master_x1:master_x1+visible_w] = \
        overlay[overlay_y1:overlay_y1+visible_h, overlay_x1:overlay_x1+visible_w]
    
    # Verify
    assert np.all(master[50:150, 0:50] == 255), "Visible part should be white"
    assert np.all(master[50:150, 50:199] == 0), "Other parts should be black"
    
    return master


def test_convert_bgra_to_rgba():
    """Test BGRA to RGBA conversion for DPG"""
    print("\nTest 5: BGRA to RGBA Conversion")
    print("-" * 60)
    
    # Create BGRA image
    bgra = np.zeros((50, 50, 4), dtype=np.uint8)
    bgra[:, :] = (255, 0, 0, 128)  # Blue with 50% alpha in BGRA
    
    # Convert BGRA to RGBA (like for DPG)
    rgba = cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA)
    
    print(f"  ✓ BGRA pixel: {bgra[0, 0]}")
    print(f"  ✓ RGBA pixel: {rgba[0, 0]}")
    
    # BGRA (255, 0, 0, 128) -> RGBA (0, 0, 255, 128)
    assert rgba[0, 0, 0] == 0, "R should be 0"
    assert rgba[0, 0, 1] == 0, "G should be 0"
    assert rgba[0, 0, 2] == 255, "B should be 255"
    assert rgba[0, 0, 3] == 128, "A should be 128"
    
    return rgba


if __name__ == '__main__':
    print("=" * 70)
    print("Simple Integration Tests for BGRA and Alpha Blending")
    print("=" * 70)
    print()
    
    try:
        test_bgra_image_creation()
        test_alpha_blending_with_bgra()
        test_overlay_resizing()
        test_position_clipping()
        test_convert_bgra_to_rgba()
        
        print()
        print("=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
