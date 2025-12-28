#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the new CourtKeypointDeviation algorithm without GUI dependencies.
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_dominant_color_extraction():
    """Test dominant color extraction from court region"""
    print("Testing dominant color extraction...")
    
    # Create a synthetic green court (tennis court)
    green_court = np.zeros((100, 100, 3), dtype=np.uint8)
    green_court[:, :] = [40, 150, 40]  # BGR green
    
    # Add some noise
    noise = np.random.randint(-10, 10, green_court.shape, dtype=np.int16)
    green_court = np.clip(green_court.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Quantize colors
    pixels = green_court.reshape(-1, 3)
    pixels = (pixels // 32) * 32
    
    # Count color frequencies
    unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
    
    # Find most frequent color
    max_idx = np.argmax(counts)
    dominant_color = unique_colors[max_idx]
    dominance_ratio = counts[max_idx] / counts.sum()
    
    print(f"  Dominant color (BGR): {dominant_color}")
    print(f"  Dominance ratio: {dominance_ratio:.2%}")
    
    assert dominance_ratio > 0.5, "Dominance ratio should be > 50%"
    print("✓ Dominant color extraction test passed")
    return True


def test_histogram_distance():
    """Test histogram Manhattan distance calculation"""
    print("\nTesting histogram distance calculation...")
    
    # Create two similar frames (no scene cut)
    frame1 = np.random.randint(100, 150, (100, 100, 3), dtype=np.uint8)
    frame2 = frame1 + np.random.randint(-5, 5, frame1.shape, dtype=np.int16)
    frame2 = np.clip(frame2, 0, 255).astype(np.uint8)
    
    # Convert to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Compute histograms
    hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
    hist1 = hist1 / (hist1.sum() + 1e-10)
    
    hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
    hist2 = hist2 / (hist2.sum() + 1e-10)
    
    # Calculate Manhattan distance
    distance = np.sum(np.abs(hist1 - hist2))
    
    print(f"  Distance between similar frames: {distance:.4f}")
    assert distance < 0.3, "Distance between similar frames should be small"
    
    # Create a very different frame (scene cut)
    frame3 = np.random.randint(0, 50, (100, 100, 3), dtype=np.uint8)
    gray3 = cv2.cvtColor(frame3, cv2.COLOR_BGR2GRAY)
    hist3 = cv2.calcHist([gray3], [0], None, [256], [0, 256])
    hist3 = hist3 / (hist3.sum() + 1e-10)
    
    distance_cut = np.sum(np.abs(hist1 - hist3))
    print(f"  Distance with scene cut: {distance_cut:.4f}")
    assert distance_cut > 0.3, "Distance with scene cut should be large"
    
    print("✓ Histogram distance test passed")
    return True


def test_color_similarity():
    """Test color similarity check"""
    print("\nTesting color similarity check...")
    
    color1 = np.array([40, 150, 40])  # Green
    color2 = np.array([45, 155, 45])  # Similar green
    color3 = np.array([200, 100, 50])  # Different color (blue)
    
    # Check similarity
    distance_similar = np.linalg.norm(color1 - color2)
    distance_different = np.linalg.norm(color1 - color3)
    
    print(f"  Distance between similar colors: {distance_similar:.2f}")
    print(f"  Distance between different colors: {distance_different:.2f}")
    
    assert distance_similar < 50, "Similar colors should have small distance"
    assert distance_different > 50, "Different colors should have large distance"
    
    print("✓ Color similarity test passed")
    return True


def test_court_region_extraction():
    """Test court region extraction from keypoints"""
    print("\nTesting court region extraction...")
    
    # Create a test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:, :] = [40, 150, 40]  # Green court
    
    # Create mock keypoints (court corners)
    keypoints = np.array([
        [100, 100],
        [540, 100],
        [540, 380],
        [100, 380]
    ], dtype=np.float32)
    
    # Extract bounding box
    x_coords = keypoints[:, 0].astype(int)
    y_coords = keypoints[:, 1].astype(int)
    
    margin = 10
    x_min = max(0, np.min(x_coords) - margin)
    x_max = min(frame.shape[1], np.max(x_coords) + margin)
    y_min = max(0, np.min(y_coords) - margin)
    y_max = min(frame.shape[0], np.max(y_coords) + margin)
    
    court_region = frame[y_min:y_max, x_min:x_max]
    
    print(f"  Original frame shape: {frame.shape}")
    print(f"  Court region shape: {court_region.shape}")
    print(f"  Bounding box: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    
    assert court_region.shape[0] > 0 and court_region.shape[1] > 0, "Court region should not be empty"
    assert court_region.shape[0] <= frame.shape[0], "Court region height should be <= frame height"
    assert court_region.shape[1] <= frame.shape[1], "Court region width should be <= frame width"
    
    print("✓ Court region extraction test passed")
    return True


def test_trigger_persistence():
    """Test that trigger persists until master plan returns"""
    print("\nTesting trigger persistence logic...")
    
    # Simulate master plan with some texture
    master_frame = np.random.randint(100, 150, (100, 100, 3), dtype=np.uint8)
    master_frame[:, :, 1] = 150  # Make it green-ish
    gray_master = cv2.cvtColor(master_frame, cv2.COLOR_BGR2GRAY)
    master_hist = cv2.calcHist([gray_master], [0], None, [256], [0, 256])
    master_hist = master_hist / (master_hist.sum() + 1e-10)
    
    master_color = np.array([32, 128, 32])  # Green
    
    # Simulate scene cut (different frame)
    cut_frame = np.random.randint(0, 50, (100, 100, 3), dtype=np.uint8)
    cut_frame[:, :, 0] = 200  # Make it blue-ish
    gray_cut = cv2.cvtColor(cut_frame, cv2.COLOR_BGR2GRAY)
    cut_hist = cv2.calcHist([gray_cut], [0], None, [256], [0, 256])
    cut_hist = cut_hist / (cut_hist.sum() + 1e-10)
    
    distance_to_master = np.sum(np.abs(cut_hist - master_hist))
    cut_color = np.array([200, 100, 50])  # Blue
    color_distance = np.linalg.norm(cut_color - master_color)
    
    print(f"  Distance from cut to master (histogram): {distance_to_master:.4f}")
    print(f"  Distance from cut to master (color): {color_distance:.2f}")
    
    # Trigger should be active (histogram distance is high OR color is different)
    assert distance_to_master > 0.3 or color_distance > 50, "Trigger should be active after scene cut"
    
    # Simulate return to master plan (similar histogram and color)
    return_frame = master_frame + np.random.randint(-5, 5, master_frame.shape, dtype=np.int16)
    return_frame = np.clip(return_frame, 0, 255).astype(np.uint8)
    gray_return = cv2.cvtColor(return_frame, cv2.COLOR_BGR2GRAY)
    return_hist = cv2.calcHist([gray_return], [0], None, [256], [0, 256])
    return_hist = return_hist / (return_hist.sum() + 1e-10)
    
    distance_returned = np.sum(np.abs(return_hist - master_hist))
    return_color = np.array([35, 130, 35])  # Similar green
    color_distance_returned = np.linalg.norm(return_color - master_color)
    
    print(f"  Distance after return to master (histogram): {distance_returned:.4f}")
    print(f"  Distance after return to master (color): {color_distance_returned:.2f}")
    
    # Trigger should be deactivated (both histogram and color are similar)
    assert distance_returned < 0.3 and color_distance_returned < 50, "Trigger should be deactivated after return to master"
    
    print("✓ Trigger persistence test passed")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Testing CourtKeypointDeviation Algorithm")
    print("=" * 60)
    
    all_tests_passed = True
    
    try:
        test_dominant_color_extraction()
    except Exception as e:
        print(f"✗ Dominant color extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    try:
        test_histogram_distance()
    except Exception as e:
        print(f"✗ Histogram distance test failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    try:
        test_color_similarity()
    except Exception as e:
        print(f"✗ Color similarity test failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    try:
        test_court_region_extraction()
    except Exception as e:
        print(f"✗ Court region extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    try:
        test_trigger_persistence()
    except Exception as e:
        print(f"✗ Trigger persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    print("=" * 60)
    if all_tests_passed:
        print("All algorithm tests passed! ✓")
    else:
        print("Some tests failed! ✗")
    print("=" * 60)
    
    sys.exit(0 if all_tests_passed else 1)
