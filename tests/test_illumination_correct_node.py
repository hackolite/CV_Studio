#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Illumination Correct node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_illumination_correct_import():
    """Test that Illumination Correct node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_illumination_correct as illum_module
        print(f"✓ node.ProcessNode.node_illumination_correct imported successfully")
        assert hasattr(illum_module, 'FactoryNode')
        assert hasattr(illum_module, 'Node')
        print(f"✓ Illumination Correct node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_illumination_correct: {e}")
        raise


def test_illumination_correct_image_processing():
    """Test the Illumination Correct image processing function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Illumination Correct image processing test - numpy is mocked")
        return
    
    from node.ProcessNode.node_illumination_correct import image_process
    
    # Create a test image with uneven illumination
    test_image = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
    
    # Add gradient to simulate uneven lighting
    gradient = np.linspace(0.5, 1.5, 100).reshape(100, 1)
    test_image = (test_image * gradient).astype(np.uint8)
    
    # Test with default parameters
    method = 0  # Division
    kernel_size = 51
    
    result = image_process(test_image.copy(), method, kernel_size)
    
    # Check that result is same shape
    assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
    
    # Check that output is valid image
    assert np.all(np.isfinite(result)), "Output should not contain NaN or inf"
    
    # Check value range
    assert result.min() >= 0 and result.max() <= 255, "Output values should be in valid range [0, 255]"
    
    print("✓ Illumination Correct image processing works correctly")


def test_illumination_correct_methods():
    """Test different illumination correction methods"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Illumination Correct methods test - numpy is mocked")
        return
    
    from node.ProcessNode.node_illumination_correct import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test all methods
    methods = {0: 'Division', 1: 'Subtraction', 2: 'Morphological'}
    
    for method_id, method_name in methods.items():
        result = image_process(test_image.copy(), method_id, 51)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        assert result.min() >= 0 and result.max() <= 255
        print(f"✓ Illumination Correct works with {method_name} method")


def test_illumination_correct_kernel_sizes():
    """Test different kernel sizes"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Illumination Correct kernel size test - numpy is mocked")
        return
    
    from node.ProcessNode.node_illumination_correct import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test different kernel sizes
    for kernel_size in [11, 31, 51, 71]:
        result = image_process(test_image.copy(), 0, kernel_size)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Illumination Correct works with kernel_size={kernel_size}")


if __name__ == '__main__':
    test_illumination_correct_import()
    test_illumination_correct_image_processing()
    test_illumination_correct_methods()
    test_illumination_correct_kernel_sizes()
    print("\n✓ All Illumination Correct tests passed!")
