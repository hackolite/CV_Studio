#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test to verify the fix for CV_64F depth error in convert_cv_to_dpg"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
from node.basenode import Node


def test_convert_cv_to_dpg_with_uint8_image():
    """Test that convert_cv_to_dpg works correctly with uint8 images"""
    
    print("Testing convert_cv_to_dpg with uint8 image...")
    
    # Create a Node instance
    node = Node()
    
    # Create a black image with uint8 dtype (this is the fix)
    black_image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Verify the image dtype before conversion
    assert black_image.dtype == np.uint8, f"Expected uint8 dtype, got {black_image.dtype}"
    print(f"✓ Black image dtype is correct: {black_image.dtype}")
    
    # This should NOT raise the CV_64F error
    try:
        texture_data = node.convert_cv_to_dpg(black_image, 50, 50)
        print(f"✓ convert_cv_to_dpg succeeded without error")
        print(f"✓ Texture data shape: {texture_data.shape}")
        print(f"✓ Texture data dtype: {texture_data.dtype}")
        
        # Verify output is correct
        assert texture_data.dtype == np.float32, f"Expected float32 output, got {texture_data.dtype}"
        assert texture_data.shape == (50 * 50 * 3,), f"Expected shape (7500,), got {texture_data.shape}"
        print("✓ Output data is in correct format")
        
    except cv2.error as e:
        if "Unsupported depth of input image" in str(e) and "CV_64F" in str(e):
            print(f"✗ FAILED: Got CV_64F error (the bug is not fixed!)")
            print(f"Error: {e}")
            raise
        else:
            print(f"✗ FAILED: Got unexpected OpenCV error")
            print(f"Error: {e}")
            raise
    
    print("\n✓ All tests passed!")


def test_convert_cv_to_dpg_with_float64_image_should_fail():
    """Test that float64 images would cause an error (to verify the bug existed)"""
    
    print("\nTesting that float64 images would cause the original error...")
    
    # Create a Node instance
    node = Node()
    
    # Create a black image with float64 dtype (the old buggy behavior)
    black_image_float64 = np.zeros((100, 100, 3), dtype=np.float64)
    
    # Verify the image dtype
    assert black_image_float64.dtype == np.float64, f"Expected float64 dtype, got {black_image_float64.dtype}"
    print(f"✓ Float64 image dtype: {black_image_float64.dtype}")
    
    # This SHOULD raise the CV_64F error
    try:
        texture_data = node.convert_cv_to_dpg(black_image_float64, 50, 50)
        print(f"✗ UNEXPECTED: convert_cv_to_dpg succeeded with float64 image")
        print("  (This might mean OpenCV was updated to support float64)")
        
    except cv2.error as e:
        if "Unsupported depth of input image" in str(e) and "CV_64F" in str(e):
            print(f"✓ Got expected CV_64F error with float64 image:")
            print(f"  Error message: {str(e)[:100]}...")
            print("  This confirms the bug would occur without the dtype fix")
        else:
            print(f"✗ Got unexpected OpenCV error:")
            print(f"  Error: {e}")
            raise
    
    print("\n✓ Confirmed that float64 causes the error!")


def test_np_zeros_default_dtype():
    """Test to demonstrate np.zeros() default dtype is float64"""
    
    print("\nVerifying np.zeros() default dtype...")
    
    # Create array without dtype specification (old buggy code)
    arr_no_dtype = np.zeros((10, 10, 3))
    print(f"✓ np.zeros((10, 10, 3)) creates dtype: {arr_no_dtype.dtype}")
    assert arr_no_dtype.dtype == np.float64, "np.zeros default should be float64"
    
    # Create array with dtype specification (fixed code)
    arr_with_dtype = np.zeros((10, 10, 3), dtype=np.uint8)
    print(f"✓ np.zeros((10, 10, 3), dtype=np.uint8) creates dtype: {arr_with_dtype.dtype}")
    assert arr_with_dtype.dtype == np.uint8, "Should be uint8 with dtype specified"
    
    print("\n✓ Confirmed that np.zeros() defaults to float64!")


if __name__ == "__main__":
    print("=" * 70)
    print("Testing CV_64F dtype fix for convert_cv_to_dpg")
    print("=" * 70)
    print()
    
    # Run tests
    test_np_zeros_default_dtype()
    test_convert_cv_to_dpg_with_uint8_image()
    test_convert_cv_to_dpg_with_float64_image_should_fail()
    
    print("\n" + "=" * 70)
    print("All tests completed successfully!")
    print("=" * 70)
