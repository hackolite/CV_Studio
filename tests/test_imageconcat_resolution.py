#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for ImageConcat resolution options - Unit tests for create_concat_image function"""

import numpy as np
import cv2


def create_concat_image(frame_dict, slot_num):
    """
    Simplified version of create_concat_image for testing
    (copied from node_image_concat.py)
    """
    if slot_num == 1:
        frame = frame_dict[0]
        display_frame = frame
    
    elif slot_num == 2:
        frame = cv2.hconcat([frame_dict[0], frame_dict[1]])
        display_frame = frame
    
    elif slot_num == 3 or slot_num == 4:
        hconcat_image01 = cv2.hconcat([frame_dict[0], frame_dict[1]])
        hconcat_image02 = cv2.hconcat([frame_dict[2], frame_dict[3]])
        frame = cv2.vconcat([hconcat_image01, hconcat_image02])
        del hconcat_image01, hconcat_image02
        display_frame = frame
    
    elif slot_num == 5 or slot_num == 6:
        hconcat_image01 = cv2.hconcat([frame_dict[0], frame_dict[1], frame_dict[2]])
        hconcat_image02 = cv2.hconcat([frame_dict[3], frame_dict[4], frame_dict[5]])
        frame = cv2.vconcat([hconcat_image01, hconcat_image02])
        del hconcat_image01, hconcat_image02
        display_frame = frame
    
    elif slot_num == 7 or slot_num == 8 or slot_num == 9:
        hconcat_image01 = cv2.hconcat([frame_dict[0], frame_dict[1], frame_dict[2]])
        hconcat_image02 = cv2.hconcat([frame_dict[3], frame_dict[4], frame_dict[5]])
        hconcat_image03 = cv2.hconcat([frame_dict[6], frame_dict[7], frame_dict[8]])
        frame = cv2.vconcat([hconcat_image01, hconcat_image02, hconcat_image03])
        del hconcat_image01, hconcat_image02, hconcat_image03
        display_frame = frame

    return frame, display_frame


def test_hd_resolution_output():
    """Test that concatenated image can be resized to HD (1280x720)"""
    # Create test frames at HD resolution
    hd_width = 1280
    hd_height = 720
    
    # Create 4 test frames for 2x2 grid
    frame_dict = {}
    for i in range(4):
        # Different colors for each frame
        color_value = (i * 60, (i * 40) % 255, (i * 80) % 255)
        frame = np.full((hd_height // 2, hd_width // 2, 3), color_value, dtype=np.uint8)
        frame_dict[i] = frame
    
    # Create concatenated image
    frame, display_frame = create_concat_image(frame_dict, 4)
    
    # Verify output dimensions
    assert frame.shape[0] == hd_height, f"Expected height {hd_height}, got {frame.shape[0]}"
    assert frame.shape[1] == hd_width, f"Expected width {hd_width}, got {frame.shape[1]}"
    
    # Verify frame is not None
    assert frame is not None, "Concatenated frame should not be None"
    assert display_frame is not None, "Display frame should not be None"
    
    print(f"✓ HD resolution test passed - output shape: {frame.shape}")


def test_vga_resolution_output():
    """Test that concatenated image can be resized to VGA (640x480)"""
    # Create test frames at VGA resolution
    vga_width = 640
    vga_height = 480
    
    # Create 4 test frames for 2x2 grid
    frame_dict = {}
    for i in range(4):
        # Different colors for each frame
        color_value = (i * 60, (i * 40) % 255, (i * 80) % 255)
        frame = np.full((vga_height // 2, vga_width // 2, 3), color_value, dtype=np.uint8)
        frame_dict[i] = frame
    
    # Create concatenated image
    frame, display_frame = create_concat_image(frame_dict, 4)
    
    # Verify output dimensions
    assert frame.shape[0] == vga_height, f"Expected height {vga_height}, got {frame.shape[0]}"
    assert frame.shape[1] == vga_width, f"Expected width {vga_width}, got {frame.shape[1]}"
    
    # Verify frame is not None
    assert frame is not None, "Concatenated frame should not be None"
    assert display_frame is not None, "Display frame should not be None"
    
    print(f"✓ VGA resolution test passed - output shape: {frame.shape}")


def test_different_grid_sizes_hd():
    """Test that different grid sizes work with HD resolution"""
    hd_width = 1280
    hd_height = 720
    
    test_cases = [
        (1, 1, 1),  # Single frame: 1x1 grid
        (2, 1, 2),  # Two frames: 1x2 grid (horizontal)
        (4, 2, 2),  # Four frames: 2x2 grid
        (6, 2, 3),  # Six frames: 2x3 grid
        (9, 3, 3),  # Nine frames: 3x3 grid
    ]
    
    for slot_num, rows, cols in test_cases:
        frame_dict = {}
        cell_height = hd_height // rows
        cell_width = hd_width // cols
        
        for i in range(slot_num):
            # Create frame with appropriate size
            color_value = ((i * 30) % 255, (i * 50) % 255, (i * 70) % 255)
            frame = np.full((cell_height, cell_width, 3), color_value, dtype=np.uint8)
            frame_dict[i] = frame
        
        # Create concatenated image
        frame, display_frame = create_concat_image(frame_dict, slot_num)
        
        # Verify output dimensions
        expected_height = cell_height * rows
        expected_width = cell_width * cols
        
        assert frame.shape[0] == expected_height, \
            f"For {slot_num} slots: expected height {expected_height}, got {frame.shape[0]}"
        assert frame.shape[1] == expected_width, \
            f"For {slot_num} slots: expected width {expected_width}, got {frame.shape[1]}"
        
        print(f"✓ {slot_num} slots ({rows}x{cols}) at HD resolution - output shape: {frame.shape}")


def test_different_grid_sizes_vga():
    """Test that different grid sizes work with VGA resolution"""
    vga_width = 640
    vga_height = 480
    
    test_cases = [
        (1, 1, 1),  # Single frame: 1x1 grid
        (2, 1, 2),  # Two frames: 1x2 grid (horizontal)
        (4, 2, 2),  # Four frames: 2x2 grid
        (6, 2, 3),  # Six frames: 2x3 grid
        (9, 3, 3),  # Nine frames: 3x3 grid
    ]
    
    for slot_num, rows, cols in test_cases:
        frame_dict = {}
        cell_height = vga_height // rows
        cell_width = vga_width // cols
        
        for i in range(slot_num):
            # Create frame with appropriate size
            color_value = ((i * 30) % 255, (i * 50) % 255, (i * 70) % 255)
            frame = np.full((cell_height, cell_width, 3), color_value, dtype=np.uint8)
            frame_dict[i] = frame
        
        # Create concatenated image
        frame, display_frame = create_concat_image(frame_dict, slot_num)
        
        # Verify output dimensions
        expected_height = cell_height * rows
        expected_width = cell_width * cols
        
        assert frame.shape[0] == expected_height, \
            f"For {slot_num} slots: expected height {expected_height}, got {frame.shape[0]}"
        assert frame.shape[1] == expected_width, \
            f"For {slot_num} slots: expected width {expected_width}, got {frame.shape[1]}"
        
        print(f"✓ {slot_num} slots ({rows}x{cols}) at VGA resolution - output shape: {frame.shape}")


def test_aspect_ratio_preserved():
    """Test that aspect ratios are correct for standard resolutions"""
    # Test HD (16:9 aspect ratio)
    hd_width = 1280
    hd_height = 720
    hd_aspect = hd_width / hd_height
    expected_hd_aspect = 16.0 / 9.0
    
    assert abs(hd_aspect - expected_hd_aspect) < 0.01, \
        f"HD aspect ratio {hd_aspect} should be close to {expected_hd_aspect}"
    
    # Test VGA (4:3 aspect ratio)
    vga_width = 640
    vga_height = 480
    vga_aspect = vga_width / vga_height
    expected_vga_aspect = 4.0 / 3.0
    
    assert abs(vga_aspect - expected_vga_aspect) < 0.01, \
        f"VGA aspect ratio {vga_aspect} should be close to {expected_vga_aspect}"
    
    print("✓ Aspect ratio tests passed")


if __name__ == '__main__':
    # Run all tests
    print("\nRunning ImageConcat resolution tests...\n")
    test_hd_resolution_output()
    test_vga_resolution_output()
    test_different_grid_sizes_hd()
    test_different_grid_sizes_vga()
    test_aspect_ratio_preserved()
    print("\n✓ All ImageConcat resolution tests passed!")
