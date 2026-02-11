#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Bilateral Filter node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_bilateral_filter_import():
    """Test that Bilateral Filter node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_bilateral_filter as bilateral_module
        print(f"✓ node.ProcessNode.node_bilateral_filter imported successfully")
        assert hasattr(bilateral_module, 'FactoryNode')
        assert hasattr(bilateral_module, 'Node')
        print(f"✓ Bilateral Filter node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_bilateral_filter: {e}")
        raise


def test_bilateral_filter_image_processing():
    """Test the Bilateral Filter image processing function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Bilateral Filter image processing test - numpy is mocked")
        return
    
    from node.ProcessNode.node_bilateral_filter import image_process
    
    # Create a test image with noise
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with default parameters
    d = 9
    sigma_color = 75.0
    sigma_space = 75.0
    
    result = image_process(test_image.copy(), d, sigma_color, sigma_space)
    
    # Check that result is same shape
    assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
    
    # Check that result is different from input (bilateral filter should denoise)
    assert not np.array_equal(result, test_image), "Bilateral filter should modify the image"
    
    # Check that output is valid image (no NaN or inf values)
    assert np.all(np.isfinite(result)), "Output should not contain NaN or inf"
    
    # Check value range
    assert result.min() >= 0 and result.max() <= 255, "Output values should be in valid range [0, 255]"
    
    print("✓ Bilateral Filter image processing works correctly")


def test_bilateral_filter_edge_preservation():
    """Test that Bilateral Filter preserves edges"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Bilateral Filter edge preservation test - numpy is mocked")
        return
    
    from node.ProcessNode.node_bilateral_filter import image_process
    
    # Create an image with a sharp edge
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    test_image[:, :50] = 0  # Left half black
    test_image[:, 50:] = 255  # Right half white
    
    # Apply bilateral filter
    result = image_process(test_image.copy(), 9, 75.0, 75.0)
    
    # Check that the edge is still relatively sharp
    # (bilateral filter should preserve edges better than Gaussian blur)
    edge_profile = result[50, :, 0]  # Middle row
    edge_transition = np.where(np.diff(edge_profile) > 50)[0]
    
    # Edge should still exist
    assert len(edge_transition) > 0, "Edge should be preserved"
    
    print("✓ Bilateral Filter preserves edges")


def test_bilateral_filter_different_parameters():
    """Test Bilateral Filter with different parameter values"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Bilateral Filter parameter test - numpy is mocked")
        return
    
    from node.ProcessNode.node_bilateral_filter import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with different diameter values
    for d in [1, 5, 9, 15]:
        result = image_process(test_image.copy(), d, 75.0, 75.0)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Bilateral Filter works with d={d}")
    
    # Test with different sigma values
    for sigma in [10.0, 50.0, 100.0, 150.0]:
        result = image_process(test_image.copy(), 9, sigma, sigma)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Bilateral Filter works with sigma={sigma}")


if __name__ == '__main__':
    test_bilateral_filter_import()
    test_bilateral_filter_image_processing()
    test_bilateral_filter_edge_preservation()
    test_bilateral_filter_different_parameters()
    print("\n✓ All Bilateral Filter tests passed!")
