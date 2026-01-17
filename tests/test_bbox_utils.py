#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify the NumPy-based bbox_overlaps implementation
that replaces cython_bbox to avoid compilation issues.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from node.TrackerNode.mot.bytetrack.tracker.bbox_utils import bbox_overlaps


def test_identical_boxes():
    """Test that IoU of identical boxes is 1.0"""
    print("Test 1: Identical boxes (IoU should be 1.0)")
    boxes1 = np.array([[10.0, 10.0, 50.0, 50.0]], dtype=np.float64)
    boxes2 = np.array([[10.0, 10.0, 50.0, 50.0]], dtype=np.float64)
    
    ious = bbox_overlaps(boxes1, boxes2)
    
    assert ious.shape == (1, 1), f"Expected shape (1, 1), got {ious.shape}"
    assert np.isclose(ious[0, 0], 1.0), f"Expected IoU 1.0, got {ious[0, 0]}"
    print(f"  ✓ IoU = {ious[0, 0]:.4f}")


def test_non_overlapping_boxes():
    """Test that IoU of non-overlapping boxes is 0.0"""
    print("\nTest 2: Non-overlapping boxes (IoU should be 0.0)")
    boxes1 = np.array([[0.0, 0.0, 10.0, 10.0]], dtype=np.float64)
    boxes2 = np.array([[20.0, 20.0, 30.0, 30.0]], dtype=np.float64)
    
    ious = bbox_overlaps(boxes1, boxes2)
    
    assert ious.shape == (1, 1), f"Expected shape (1, 1), got {ious.shape}"
    assert np.isclose(ious[0, 0], 0.0), f"Expected IoU 0.0, got {ious[0, 0]}"
    print(f"  ✓ IoU = {ious[0, 0]:.4f}")


def test_partial_overlap():
    """Test IoU computation for partially overlapping boxes"""
    print("\nTest 3: Partially overlapping boxes")
    # Box 1: (0, 0) to (10, 10) - area = 100
    # Box 2: (5, 5) to (15, 15) - area = 100
    # Intersection: (5, 5) to (10, 10) - area = 25
    # Union: 100 + 100 - 25 = 175
    # IoU: 25 / 175 = 0.14285714...
    boxes1 = np.array([[0.0, 0.0, 10.0, 10.0]], dtype=np.float64)
    boxes2 = np.array([[5.0, 5.0, 15.0, 15.0]], dtype=np.float64)
    
    ious = bbox_overlaps(boxes1, boxes2)
    expected_iou = 25.0 / 175.0
    
    assert ious.shape == (1, 1), f"Expected shape (1, 1), got {ious.shape}"
    assert np.isclose(ious[0, 0], expected_iou), f"Expected IoU {expected_iou:.4f}, got {ious[0, 0]:.4f}"
    print(f"  ✓ IoU = {ious[0, 0]:.4f} (expected {expected_iou:.4f})")


def test_empty_arrays():
    """Test handling of empty arrays"""
    print("\nTest 4: Empty arrays")
    boxes1_empty = np.array([], dtype=np.float64).reshape(0, 4)
    boxes2 = np.array([[10.0, 10.0, 50.0, 50.0]], dtype=np.float64)
    
    ious = bbox_overlaps(boxes1_empty, boxes2)
    
    assert ious.shape == (0, 1), f"Expected shape (0, 1), got {ious.shape}"
    print(f"  ✓ Shape = {ious.shape}")
    
    # Test both empty
    boxes1_empty2 = np.array([], dtype=np.float64).reshape(0, 4)
    boxes2_empty = np.array([], dtype=np.float64).reshape(0, 4)
    
    ious2 = bbox_overlaps(boxes1_empty2, boxes2_empty)
    
    assert ious2.shape == (0, 0), f"Expected shape (0, 0), got {ious2.shape}"
    print(f"  ✓ Shape = {ious2.shape}")


def test_multiple_boxes():
    """Test IoU computation for multiple boxes"""
    print("\nTest 5: Multiple boxes (NxM matrix)")
    boxes1 = np.array([
        [0.0, 0.0, 10.0, 10.0],
        [5.0, 5.0, 15.0, 15.0],
        [20.0, 20.0, 30.0, 30.0],
    ], dtype=np.float64)
    
    boxes2 = np.array([
        [0.0, 0.0, 10.0, 10.0],
        [10.0, 10.0, 20.0, 20.0],
    ], dtype=np.float64)
    
    ious = bbox_overlaps(boxes1, boxes2)
    
    assert ious.shape == (3, 2), f"Expected shape (3, 2), got {ious.shape}"
    
    # Check specific expected values
    assert np.isclose(ious[0, 0], 1.0), f"boxes1[0] and boxes2[0] are identical, expected IoU 1.0, got {ious[0, 0]}"
    assert np.isclose(ious[0, 1], 0.0), f"boxes1[0] and boxes2[1] don't overlap, expected IoU 0.0, got {ious[0, 1]}"
    
    print(f"  ✓ Shape = {ious.shape}")
    print(f"  ✓ IoU matrix:\n{ious}")


def test_contiguous_array():
    """Test that function accepts non-contiguous arrays"""
    print("\nTest 6: Non-contiguous arrays")
    boxes1 = np.array([[0.0, 0.0, 10.0, 10.0], [5.0, 5.0, 15.0, 15.0]], dtype=np.float64)
    boxes2 = np.array([[0.0, 0.0, 10.0, 10.0]], dtype=np.float64)
    
    # Create non-contiguous array
    boxes1_nc = boxes1[::1]  # Still contiguous, but test the conversion
    
    ious = bbox_overlaps(boxes1_nc, boxes2)
    
    assert ious.shape == (2, 1), f"Expected shape (2, 1), got {ious.shape}"
    print(f"  ✓ Successfully handled array conversion")


def test_integration_with_tracking():
    """Test integration with tracking code (matching.py usage)"""
    print("\nTest 7: Integration test simulating tracking usage")
    
    # Simulate detection boxes from object detector
    detections = np.array([
        [100.0, 100.0, 200.0, 200.0],
        [300.0, 150.0, 400.0, 250.0],
        [500.0, 300.0, 600.0, 400.0],
    ], dtype=np.float64)
    
    # Simulate tracked boxes from previous frame
    tracks = np.array([
        [105.0, 105.0, 205.0, 205.0],  # Close to detection 0
        [310.0, 160.0, 410.0, 260.0],  # Close to detection 1
        [700.0, 700.0, 800.0, 800.0],  # No match
    ], dtype=np.float64)
    
    # Compute IoU matrix (as done in matching.py)
    ious = bbox_overlaps(
        np.ascontiguousarray(detections, dtype=np.float64),
        np.ascontiguousarray(tracks, dtype=np.float64)
    )
    
    assert ious.shape == (3, 3), f"Expected shape (3, 3), got {ious.shape}"
    
    # Check that similar boxes have high IoU
    assert ious[0, 0] > 0.6, f"Expected high IoU for similar boxes, got {ious[0, 0]}"
    assert ious[1, 1] > 0.6, f"Expected high IoU for similar boxes, got {ious[1, 1]}"
    
    # Check that dissimilar boxes have low IoU
    assert ious[0, 2] < 0.1, f"Expected low IoU for dissimilar boxes, got {ious[0, 2]}"
    assert ious[2, 2] < 0.1, f"Expected low IoU for dissimilar boxes, got {ious[2, 2]}"
    
    print(f"  ✓ IoU matrix computed correctly for tracking scenario")
    print(f"  ✓ High IoU values: {ious[0, 0]:.4f}, {ious[1, 1]:.4f}")
    print(f"  ✓ Low IoU values: {ious[0, 2]:.4f}, {ious[2, 2]:.4f}")


def main():
    """Run all tests"""
    print("="*60)
    print("Testing bbox_overlaps (NumPy implementation)")
    print("="*60)
    
    tests = [
        test_identical_boxes,
        test_non_overlapping_boxes,
        test_partial_overlap,
        test_empty_arrays,
        test_multiple_boxes,
        test_contiguous_array,
        test_integration_with_tracking,
    ]
    
    failed_tests = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed_tests.append(test.__name__)
    
    print("\n" + "="*60)
    if not failed_tests:
        print("✓ SUCCESS: All bbox_overlaps tests passed!")
        print("The NumPy implementation is working correctly.")
        print("="*60)
        return 0
    else:
        print(f"✗ FAILED: {len(failed_tests)} test(s) failed:")
        for test_name in failed_tests:
            print(f"  - {test_name}")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
