#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Unsharp Mask node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_unsharp_mask_import():
    """Test that Unsharp Mask node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_unsharp_mask as unsharp_module
        print(f"✓ node.ProcessNode.node_unsharp_mask imported successfully")
        assert hasattr(unsharp_module, 'FactoryNode')
        assert hasattr(unsharp_module, 'Node')
        print(f"✓ Unsharp Mask node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_unsharp_mask: {e}")
        raise


def test_unsharp_mask_image_processing():
    """Test the Unsharp Mask image processing function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Unsharp Mask image processing test - numpy is mocked")
        return
    
    from node.ProcessNode.node_unsharp_mask import image_process
    
    # Create a slightly blurred test image
    test_image = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
    
    # Test with default parameters
    kernel_size = 5
    amount = 1.0
    threshold = 0
    
    result = image_process(test_image.copy(), kernel_size, amount, threshold)
    
    # Check that result is same shape
    assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
    
    # Check that result is different from input (unsharp mask should sharpen)
    assert not np.array_equal(result, test_image), "Unsharp mask should modify the image"
    
    # Check that output is valid image (no NaN or inf values)
    assert np.all(np.isfinite(result)), "Output should not contain NaN or inf"
    
    # Check value range (may exceed 0-255 range but should be clipped by uint8)
    assert result.dtype == test_image.dtype, "Output dtype should match input"
    
    print("✓ Unsharp Mask image processing works correctly")


def test_unsharp_mask_sharpening_effect():
    """Test that Unsharp Mask enhances edges"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Unsharp Mask sharpening test - numpy is mocked")
        return
    
    from node.ProcessNode.node_unsharp_mask import image_process
    
    # Create an image with a soft edge (simulated blur)
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    test_image[:, :50] = 100
    test_image[:, 50:] = 200
    test_image = cv2.GaussianBlur(test_image, (11, 11), 0)  # Blur to simulate soft edge
    
    # Apply unsharp mask with moderate sharpening
    result = image_process(test_image.copy(), 5, 1.5, 0)
    
    # The sharpened image should have higher edge gradients
    # Calculate gradient magnitude
    grad_x = np.abs(np.diff(test_image[50, :, 0].astype(float)))
    grad_x_sharp = np.abs(np.diff(result[50, :, 0].astype(float)))
    
    # Sharpened image should have stronger gradients on average
    assert np.max(grad_x_sharp) >= np.max(grad_x), "Sharpening should increase edge gradients"
    
    print("✓ Unsharp Mask enhances edges")


def test_unsharp_mask_threshold_effect():
    """Test that threshold parameter reduces noise amplification"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Unsharp Mask threshold test - numpy is mocked")
        return
    
    from node.ProcessNode.node_unsharp_mask import image_process
    
    # Create a flat image with small noise
    test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
    noise = np.random.randint(-2, 3, (100, 100, 3), dtype=np.int16)
    test_image = np.clip(test_image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Apply unsharp mask without threshold
    result_no_threshold = image_process(test_image.copy(), 5, 1.0, 0)
    
    # Apply unsharp mask with threshold
    result_with_threshold = image_process(test_image.copy(), 5, 1.0, 5)
    
    # With threshold, low-contrast areas should be less affected
    # The result with threshold should be closer to the original in flat areas
    diff_no_threshold = np.abs(result_no_threshold.astype(float) - test_image.astype(float)).mean()
    diff_with_threshold = np.abs(result_with_threshold.astype(float) - test_image.astype(float)).mean()
    
    assert diff_with_threshold <= diff_no_threshold, "Threshold should reduce changes in low-contrast areas"
    
    print("✓ Unsharp Mask threshold reduces noise amplification")


def test_unsharp_mask_different_parameters():
    """Test Unsharp Mask with different parameter values"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Unsharp Mask parameter test - numpy is mocked")
        return
    
    from node.ProcessNode.node_unsharp_mask import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with different kernel sizes
    for kernel_size in [1, 3, 5, 9, 15]:
        result = image_process(test_image.copy(), kernel_size, 1.0, 0)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Unsharp Mask works with kernel_size={kernel_size}")
    
    # Test with different amounts
    for amount in [0.0, 0.5, 1.0, 1.5, 2.0]:
        result = image_process(test_image.copy(), 5, amount, 0)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Unsharp Mask works with amount={amount}")
    
    # Test with different thresholds
    for threshold in [0, 5, 10, 20, 50]:
        result = image_process(test_image.copy(), 5, 1.0, threshold)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Unsharp Mask works with threshold={threshold}")


def test_unsharp_mask_even_kernel_size():
    """Test that even kernel sizes are converted to odd"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Unsharp Mask even kernel test - numpy is mocked")
        return
    
    from node.ProcessNode.node_unsharp_mask import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with even kernel size (should be converted to odd)
    result = image_process(test_image.copy(), 6, 1.0, 0)
    assert result.shape == test_image.shape
    assert np.all(np.isfinite(result))
    print("✓ Unsharp Mask handles even kernel sizes correctly")


if __name__ == '__main__':
    test_unsharp_mask_import()
    test_unsharp_mask_image_processing()
    test_unsharp_mask_sharpening_effect()
    test_unsharp_mask_threshold_effect()
    test_unsharp_mask_different_parameters()
    test_unsharp_mask_even_kernel_size()
    print("\n✓ All Unsharp Mask tests passed!")
