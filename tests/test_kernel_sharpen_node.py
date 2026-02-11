#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Kernel Sharpen node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_kernel_sharpen_import():
    """Test that Kernel Sharpen node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_kernel_sharpen as sharpen_module
        print(f"✓ node.ProcessNode.node_kernel_sharpen imported successfully")
        assert hasattr(sharpen_module, 'FactoryNode')
        assert hasattr(sharpen_module, 'Node')
        print(f"✓ Kernel Sharpen node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_kernel_sharpen: {e}")
        raise


def test_kernel_sharpen_image_processing():
    """Test the Kernel Sharpen image processing function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Kernel Sharpen image processing test - numpy is mocked")
        return
    
    from node.ProcessNode.node_kernel_sharpen import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with default parameters
    kernel_type = 0  # Standard
    strength = 1.0
    
    result = image_process(test_image.copy(), kernel_type, strength)
    
    # Check that result is same shape
    assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
    
    # Check that output is valid image
    assert np.all(np.isfinite(result)), "Output should not contain NaN or inf"
    
    # Check value range
    assert result.min() >= 0 and result.max() <= 255, "Output values should be in valid range [0, 255]"
    
    print("✓ Kernel Sharpen image processing works correctly")


def test_kernel_sharpen_kernels():
    """Test different sharpening kernels"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Kernel Sharpen kernels test - numpy is mocked")
        return
    
    from node.ProcessNode.node_kernel_sharpen import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test all kernel types
    kernels = {0: 'Standard', 1: 'Mild', 2: 'Strong 5x5', 3: 'Laplacian'}
    
    for kernel_id, kernel_name in kernels.items():
        result = image_process(test_image.copy(), kernel_id, 1.0)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        assert result.min() >= 0 and result.max() <= 255
        print(f"✓ Kernel Sharpen works with {kernel_name} kernel")


def test_kernel_sharpen_strength():
    """Test different strength values"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Kernel Sharpen strength test - numpy is mocked")
        return
    
    from node.ProcessNode.node_kernel_sharpen import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test different strengths
    for strength in [0.0, 0.5, 1.0, 1.5, 2.0]:
        result = image_process(test_image.copy(), 0, strength)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Kernel Sharpen works with strength={strength}")


if __name__ == '__main__':
    test_kernel_sharpen_import()
    test_kernel_sharpen_image_processing()
    test_kernel_sharpen_kernels()
    test_kernel_sharpen_strength()
    print("\n✓ All Kernel Sharpen tests passed!")
