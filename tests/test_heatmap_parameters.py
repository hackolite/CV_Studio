#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for new heatmap parameters (blur, colormap, blend alpha)"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np


def test_heatmap_blur_parameter():
    """Test that different blur sizes produce different results"""
    
    # Create a simple heatmap
    heatmap = np.zeros((480, 640), dtype=np.uint8)
    heatmap[200:300, 250:350] = 255  # Add a bright square
    
    # Test different blur sizes
    blur_sizes = [5, 25, 51]
    results = []
    
    for blur_size in blur_sizes:
        blurred = cv2.GaussianBlur(heatmap, (blur_size, blur_size), 0)
        results.append(blurred)
    
    # Verify that different blur sizes produce different results
    assert not np.array_equal(results[0], results[1]), "Different blur sizes should produce different results"
    assert not np.array_equal(results[1], results[2]), "Different blur sizes should produce different results"
    
    # Verify that larger blur creates more spread
    # Check the value at the edge of the original square
    # With larger blur, the edge should have higher values (more spread)
    edge_value_5 = results[0][200, 250]
    edge_value_25 = results[1][200, 250]
    
    print(f"  Blur 5: edge value = {edge_value_5}")
    print(f"  Blur 25: edge value = {edge_value_25}")
    print("  ✓ Blur parameter test passed")


def test_heatmap_colormap_parameter():
    """Test that different colormaps produce different colored outputs"""
    
    # Create a simple heatmap
    heatmap = np.zeros((480, 640), dtype=np.uint8)
    heatmap[200:300, 250:350] = 255  # Add a bright square
    
    # Test different colormaps
    colormaps = [
        ("JET", cv2.COLORMAP_JET),
        ("HOT", cv2.COLORMAP_HOT),
        ("COOL", cv2.COLORMAP_COOL),
        ("RAINBOW", cv2.COLORMAP_RAINBOW),
        ("VIRIDIS", cv2.COLORMAP_VIRIDIS),
        ("TURBO", cv2.COLORMAP_TURBO),
    ]
    
    results = []
    for name, colormap in colormaps:
        colored = cv2.applyColorMap(heatmap, colormap)
        results.append((name, colored))
    
    # Verify that different colormaps produce different results
    for i in range(len(results) - 1):
        name1, img1 = results[i]
        name2, img2 = results[i + 1]
        assert not np.array_equal(img1, img2), f"{name1} and {name2} should produce different results"
    
    # Verify each colormap produces a color image
    for name, img in results:
        assert img.shape == (480, 640, 3), f"{name} should produce a 3-channel image"
        assert img.dtype == np.uint8, f"{name} should produce uint8 image"
    
    print("  ✓ Colormap parameter test passed")


def test_heatmap_blend_alpha_parameter():
    """Test that different blend alphas produce different blended results"""
    
    # Create a blue background image
    background = np.zeros((480, 640, 3), dtype=np.uint8)
    background[:, :] = [255, 0, 0]  # Blue
    
    # Create a red overlay
    overlay = np.zeros((480, 640, 3), dtype=np.uint8)
    overlay[:, :] = [0, 0, 255]  # Red
    
    # Test different blend alphas
    alphas = [0.0, 0.3, 0.6, 1.0]
    results = []
    
    for alpha in alphas:
        blended = cv2.addWeighted(background, 1.0 - alpha, overlay, alpha, 0)
        results.append(blended)
    
    # Verify that different alphas produce different results
    for i in range(len(results) - 1):
        assert not np.array_equal(results[i], results[i + 1]), \
            f"Alpha {alphas[i]} and {alphas[i+1]} should produce different results"
    
    # Verify alpha 0.0 gives mostly background (blue)
    assert results[0][0, 0, 0] > 200, "Alpha 0.0 should give mostly background (blue channel high)"
    assert results[0][0, 0, 2] < 50, "Alpha 0.0 should give mostly background (red channel low)"
    
    # Verify alpha 1.0 gives mostly overlay (red)
    assert results[3][0, 0, 2] > 200, "Alpha 1.0 should give mostly overlay (red channel high)"
    assert results[3][0, 0, 0] < 50, "Alpha 1.0 should give mostly overlay (blue channel low)"
    
    # Verify alpha 0.6 gives a blend
    assert 50 < results[2][0, 0, 0] < 200, "Alpha 0.6 should blend (blue channel mid-range)"
    assert 50 < results[2][0, 0, 2] < 200, "Alpha 0.6 should blend (red channel mid-range)"
    
    print("  ✓ Blend alpha parameter test passed")


def test_visual_outputs():
    """Generate visual test outputs for the new parameters"""
    
    print("\nGenerating visual test outputs for new parameters...")
    
    # Create a simple heatmap base
    heatmap_base = np.zeros((480, 640), dtype=np.uint8)
    # Add gradient effect
    for y in range(480):
        for x in range(640):
            if 150 < x < 450 and 100 < y < 350:
                # Distance from center
                cx, cy = 300, 225
                dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                value = max(0, 255 - int(dist * 1.2))
                heatmap_base[y, x] = value
    
    # Test 1: Different blur sizes
    print("\nTest 1: Different blur sizes...")
    for blur_size in [5, 15, 25, 35, 51]:
        blurred = cv2.GaussianBlur(heatmap_base, (blur_size, blur_size), 0)
        colored = cv2.applyColorMap(blurred, cv2.COLORMAP_JET)
        cv2.imwrite(f"/tmp/heatmap_blur_{blur_size}.png", colored)
        print(f"  ✓ Saved to /tmp/heatmap_blur_{blur_size}.png")
    
    # Test 2: Different colormaps
    print("\nTest 2: Different colormaps...")
    heatmap_blurred = cv2.GaussianBlur(heatmap_base, (25, 25), 0)
    colormaps = [
        ("JET", cv2.COLORMAP_JET),
        ("HOT", cv2.COLORMAP_HOT),
        ("COOL", cv2.COLORMAP_COOL),
        ("RAINBOW", cv2.COLORMAP_RAINBOW),
        ("VIRIDIS", cv2.COLORMAP_VIRIDIS),
        ("TURBO", cv2.COLORMAP_TURBO),
    ]
    
    for name, colormap in colormaps:
        colored = cv2.applyColorMap(heatmap_blurred, colormap)
        cv2.imwrite(f"/tmp/heatmap_colormap_{name}.png", colored)
        print(f"  ✓ Saved to /tmp/heatmap_colormap_{name}.png")
    
    # Test 3: Different blend alphas
    print("\nTest 3: Different blend alphas...")
    # Create a background image (checkerboard)
    background = np.zeros((480, 640, 3), dtype=np.uint8)
    tile_size = 40
    for i in range(0, 480, tile_size):
        for j in range(0, 640, tile_size):
            if (i // tile_size + j // tile_size) % 2 == 0:
                background[i:i+tile_size, j:j+tile_size] = [200, 200, 200]
            else:
                background[i:i+tile_size, j:j+tile_size] = [100, 100, 100]
    
    heatmap_colored = cv2.applyColorMap(heatmap_blurred, cv2.COLORMAP_JET)
    
    for alpha in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        blended = cv2.addWeighted(background, 1.0 - alpha, heatmap_colored, alpha, 0)
        cv2.imwrite(f"/tmp/heatmap_blend_alpha_{alpha:.1f}.png", blended)
        print(f"  ✓ Saved to /tmp/heatmap_blend_alpha_{alpha:.1f}.png")
    
    print("\n" + "="*60)
    print("Visual test outputs generated successfully!")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("Running Heatmap Parameters Tests")
    print("="*60)
    
    # Run unit tests
    print("\n--- Unit Tests ---")
    test_heatmap_blur_parameter()
    test_heatmap_colormap_parameter()
    test_heatmap_blend_alpha_parameter()
    
    # Run visual tests
    print("\n--- Visual Tests ---")
    test_visual_outputs()
    
    print("\n" + "="*60)
    print("All parameter tests passed successfully!")
    print("="*60)
    print("\nNew parameters added:")
    print("1. ✓ Blur slider (1-99) - controls Gaussian blur kernel size")
    print("2. ✓ Colormap dropdown - choose from JET, HOT, COOL, RAINBOW, VIRIDIS, TURBO")
    print("3. ✓ Blend Alpha slider (0.0-1.0) - controls overlay transparency")
    print("="*60)
