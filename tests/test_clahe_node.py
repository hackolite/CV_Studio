#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for CLAHE node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_clahe_import():
    """Test that CLAHE node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_clahe as clahe_module
        print(f"✓ node.ProcessNode.node_clahe imported successfully")
        assert hasattr(clahe_module, 'FactoryNode')
        assert hasattr(clahe_module, 'Node')
        print(f"✓ CLAHE node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_clahe: {e}")
        raise


def test_clahe_image_processing():
    """Test the CLAHE image processing function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping CLAHE image processing test - numpy is mocked")
        return
    
    from node.ProcessNode.node_clahe import image_process
    
    # Create a test image (darker on left, brighter on right)
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    test_image[:, :50] = 50  # Left half darker
    test_image[:, 50:] = 150  # Right half brighter
    
    # Test with default parameters
    clip_limit = 2.0
    tile_grid_size = 8
    
    result = image_process(test_image.copy(), clip_limit, tile_grid_size)
    
    # Check that result is same shape
    assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
    
    # Check that result is different from input (CLAHE should enhance contrast)
    assert not np.array_equal(result, test_image), "CLAHE should modify the image"
    
    # Check that output is valid image (no NaN or inf values)
    assert np.all(np.isfinite(result)), "Output should not contain NaN or inf"
    
    # Check value range
    assert result.min() >= 0 and result.max() <= 255, "Output values should be in valid range [0, 255]"
    
    print("✓ CLAHE image processing works correctly")


def test_clahe_different_parameters():
    """Test CLAHE with different parameter values"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping CLAHE parameter test - numpy is mocked")
        return
    
    from node.ProcessNode.node_clahe import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with different clip limits
    for clip_limit in [0.1, 1.0, 2.0, 5.0, 10.0]:
        result = image_process(test_image.copy(), clip_limit, 8)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ CLAHE works with clip_limit={clip_limit}")
    
    # Test with different tile grid sizes
    for tile_size in [1, 4, 8, 16, 32]:
        result = image_process(test_image.copy(), 2.0, tile_size)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ CLAHE works with tile_grid_size={tile_size}")


if __name__ == '__main__':
    test_clahe_import()
    test_clahe_image_processing()
    test_clahe_different_parameters()
    print("\n✓ All CLAHE tests passed!")
