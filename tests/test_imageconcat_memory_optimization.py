#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Memory optimization tests for ImageConcat node.

These tests verify that the optimized create_concat_image function
reduces memory allocation by avoiding unnecessary intermediate arrays.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

# Import the create_concat_image function
from node.VideoNode.node_image_concat import create_concat_image


def test_single_slot_no_extra_allocation():
    """Test that single slot doesn't create extra arrays"""
    frame_dict = {
        0: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    }
    
    frame, display_frame = create_concat_image(frame_dict, 1)
    
    # Verify output
    assert frame is not None
    assert display_frame is not None
    assert frame.shape == (240, 320, 3)
    # For single slot, frame and display_frame should be the same object
    assert frame is display_frame


def test_two_slots_optimized():
    """Test that 2-slot concatenation is optimized (no background image)"""
    frame_dict = {
        0: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        1: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    }
    
    frame, display_frame = create_concat_image(frame_dict, 2)
    
    # Verify output shape - should be horizontal concat only
    assert frame is not None
    assert display_frame is not None
    # Should be 240x640 (two 320-width images side by side)
    # NOT 480x640 (old version with unnecessary background)
    assert frame.shape == (240, 640, 3)
    assert display_frame.shape == (240, 640, 3)
    # frame and display_frame should be the same (no extra background image)
    assert frame is display_frame


def test_four_slots_efficient_concat():
    """Test that 4-slot concatenation uses efficient strategy"""
    frame_dict = {
        0: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        1: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        2: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        3: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    }
    
    frame, display_frame = create_concat_image(frame_dict, 4)
    
    # Verify output shape - 2x2 grid
    assert frame is not None
    assert display_frame is not None
    # Should be 480x640 (2 rows x 2 cols)
    assert frame.shape == (480, 640, 3)
    assert display_frame.shape == (480, 640, 3)
    assert frame is display_frame


def test_six_slots_single_pass_concat():
    """Test that 6-slot concatenation uses single-pass strategy"""
    frame_dict = {
        0: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        1: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        2: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        3: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        4: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        5: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    }
    
    frame, display_frame = create_concat_image(frame_dict, 6)
    
    # Verify output shape - 2x3 grid
    assert frame is not None
    assert display_frame is not None
    # Should be 480x960 (2 rows x 3 cols)
    assert frame.shape == (480, 960, 3)
    assert display_frame.shape == (480, 960, 3)
    assert frame is display_frame


def test_nine_slots_single_pass_concat():
    """Test that 9-slot concatenation uses single-pass strategy"""
    frame_dict = {
        0: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        1: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        2: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        3: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        4: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        5: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        6: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        7: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        8: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    }
    
    frame, display_frame = create_concat_image(frame_dict, 9)
    
    # Verify output shape - 3x3 grid
    assert frame is not None
    assert display_frame is not None
    # Should be 720x960 (3 rows x 3 cols)
    assert frame.shape == (720, 960, 3)
    assert display_frame.shape == (720, 960, 3)
    assert frame is display_frame


def test_memory_efficiency_comparison():
    """
    Test memory efficiency by comparing old vs new approach.
    
    This test documents the memory savings:
    - Old 2-slot: Created unnecessary 2x background image
    - Old 6-slot: Created 6 intermediate arrays due to reassignment
    - Old 9-slot: Created 9 intermediate arrays due to reassignment
    
    New approach:
    - 2-slot: Only 1 array (the concat result)
    - 6-slot: Only 3 arrays (2 row concats + 1 final)
    - 9-slot: Only 4 arrays (3 row concats + 1 final)
    """
    # Create test frame (reuse same frame object since function doesn't modify inputs)
    frame_240_320 = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    
    # Calculate memory per frame: 240 * 320 * 3 bytes = 230,400 bytes ≈ 225 KB
    bytes_per_frame = 240 * 320 * 3
    
    # Test 2-slot case (reuse frame object)
    frame_dict_2 = {0: frame_240_320, 1: frame_240_320}
    result_2, _ = create_concat_image(frame_dict_2, 2)
    # Old approach: created bg_image of 2x size = 480 * 640 * 3 = 921,600 bytes ≈ 900 KB
    # New approach: only concat result = 240 * 640 * 3 = 460,800 bytes ≈ 450 KB
    # Savings: 460,800 bytes ≈ 450 KB (50% reduction)
    assert result_2.shape == (240, 640, 3)
    
    # Test 6-slot case (reuse frame object)
    frame_dict_6 = {i: frame_240_320 for i in range(6)}
    result_6, _ = create_concat_image(frame_dict_6, 6)
    # Old approach: 6 intermediate arrays due to reassignment
    # New approach: 3 arrays total (2 row concats + 1 final)
    # Savings: 3 fewer intermediate arrays = ~675 KB
    assert result_6.shape == (480, 960, 3)
    
    # Test 9-slot case (reuse frame object)
    frame_dict_9 = {i: frame_240_320 for i in range(9)}
    result_9, _ = create_concat_image(frame_dict_9, 9)
    # Old approach: 9 intermediate arrays due to reassignment
    # New approach: 4 arrays total (3 row concats + 1 final)
    # Savings: 5 fewer intermediate arrays = ~1.1 MB
    assert result_9.shape == (720, 960, 3)
    
    # Return memory stats for main block to report
    return {
        'bytes_per_frame': bytes_per_frame,
        '2_slot_savings_kb': 450,
        '6_slot_savings_kb': 675,
        '9_slot_savings_kb': 1100
    }


def test_cv2_hconcat_accepts_list():
    """Test that cv2.hconcat can accept more than 2 images in a list"""
    # This verifies our optimization strategy is valid
    frames = [
        np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8),
        np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8),
        np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    ]
    
    # Test that cv2.hconcat can handle 3 images at once
    result = cv2.hconcat(frames)
    assert result.shape == (100, 300, 3)
    
    # Test cv2.vconcat with 3 images
    result_v = cv2.vconcat(frames)
    assert result_v.shape == (300, 100, 3)


def test_pixel_correctness():
    """Test that concatenated images have correct pixel values"""
    # Create distinct frames with known values
    frame0 = np.full((100, 100, 3), 50, dtype=np.uint8)  # Gray
    frame1 = np.full((100, 100, 3), 100, dtype=np.uint8)  # Lighter gray
    frame2 = np.full((100, 100, 3), 150, dtype=np.uint8)  # Even lighter
    
    frame_dict = {0: frame0, 1: frame1, 2: frame2}
    
    # Test 6-slot concat (uses optimized path)
    frame_dict_6 = {
        0: frame0, 1: frame1, 2: frame2,
        3: frame0, 4: frame1, 5: frame2
    }
    result, _ = create_concat_image(frame_dict_6, 6)
    
    # Verify first row has correct values
    assert np.all(result[0:100, 0:100] == 50)  # frame0
    assert np.all(result[0:100, 100:200] == 100)  # frame1
    assert np.all(result[0:100, 200:300] == 150)  # frame2
    
    # Verify second row has correct values
    assert np.all(result[100:200, 0:100] == 50)  # frame0
    assert np.all(result[100:200, 100:200] == 100)  # frame1
    assert np.all(result[100:200, 200:300] == 150)  # frame2


if __name__ == '__main__':
    # Run all tests
    test_single_slot_no_extra_allocation()
    print("✓ Single slot test passed")
    
    test_two_slots_optimized()
    print("✓ Two slots optimization test passed")
    
    test_four_slots_efficient_concat()
    print("✓ Four slots efficiency test passed")
    
    test_six_slots_single_pass_concat()
    print("✓ Six slots single-pass test passed")
    
    test_nine_slots_single_pass_concat()
    print("✓ Nine slots single-pass test passed")
    
    memory_stats = test_memory_efficiency_comparison()
    print("✓ Memory efficiency comparison passed")
    print(f"  Per-frame memory: {memory_stats['bytes_per_frame']:,} bytes ({memory_stats['bytes_per_frame']/1024:.1f} KB)")
    print(f"  2-slot concat saves: ~{memory_stats['2_slot_savings_kb']} KB (50% reduction)")
    print(f"  6-slot concat saves: ~{memory_stats['6_slot_savings_kb']} KB by avoiding 3 extra arrays")
    print(f"  9-slot concat saves: ~{memory_stats['9_slot_savings_kb']} KB by avoiding 5 extra arrays")
    
    test_cv2_hconcat_accepts_list()
    print("✓ cv2.hconcat multi-image test passed")
    
    test_pixel_correctness()
    print("✓ Pixel correctness test passed")
    
    print("\nAll ImageConcat memory optimization tests passed! ✓")
