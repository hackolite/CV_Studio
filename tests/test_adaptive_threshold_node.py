#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Adaptive Threshold node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_adaptive_threshold_import():
    """Test that Adaptive Threshold node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_adaptive_threshold as adaptive_module
        print(f"✓ node.ProcessNode.node_adaptive_threshold imported successfully")
        assert hasattr(adaptive_module, 'FactoryNode')
        assert hasattr(adaptive_module, 'Node')
        print(f"✓ Adaptive Threshold node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_adaptive_threshold: {e}")
        raise


def test_adaptive_threshold_image_processing():
    """Test the Adaptive Threshold image processing function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Adaptive Threshold image processing test - numpy is mocked")
        return
    
    from node.ProcessNode.node_adaptive_threshold import image_process
    
    # Create a test image with varying intensity
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with default parameters
    method = 1  # Gaussian
    threshold_type = 0  # Binary
    block_size = 11
    c_value = 2.0
    
    result = image_process(test_image.copy(), method, threshold_type, block_size, c_value)
    
    # Check that result is same shape
    assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
    
    # Check that output is valid image
    assert np.all(np.isfinite(result)), "Output should not contain NaN or inf"
    
    # Check that output is binary-like (mostly 0s and 255s)
    unique_vals = np.unique(result)
    assert 0 in unique_vals or 255 in unique_vals, "Output should contain threshold values"
    
    print("✓ Adaptive Threshold image processing works correctly")


def test_adaptive_threshold_methods():
    """Test different adaptive threshold methods"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Adaptive Threshold methods test - numpy is mocked")
        return
    
    from node.ProcessNode.node_adaptive_threshold import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test both methods
    methods = {0: 'Mean', 1: 'Gaussian'}
    threshold_types = {0: 'Binary', 1: 'Binary Inverted'}
    
    for method_id, method_name in methods.items():
        for type_id, type_name in threshold_types.items():
            result = image_process(test_image.copy(), method_id, type_id, 11, 2.0)
            assert result.shape == test_image.shape
            assert np.all(np.isfinite(result))
            print(f"✓ Adaptive Threshold works with {method_name} + {type_name}")


if __name__ == '__main__':
    test_adaptive_threshold_import()
    test_adaptive_threshold_image_processing()
    test_adaptive_threshold_methods()
    print("\n✓ All Adaptive Threshold tests passed!")
