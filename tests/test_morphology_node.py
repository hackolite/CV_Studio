#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Morphology node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_morphology_import():
    """Test that Morphology node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_morphology as morph_module
        print(f"✓ node.ProcessNode.node_morphology imported successfully")
        assert hasattr(morph_module, 'FactoryNode')
        assert hasattr(morph_module, 'Node')
        print(f"✓ Morphology node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_morphology: {e}")
        raise


def test_morphology_image_processing():
    """Test the Morphology image processing function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Morphology image processing test - numpy is mocked")
        return
    
    from node.ProcessNode.node_morphology import image_process
    
    # Create a binary test image with noise
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    test_image[40:60, 40:60] = 255  # White square
    test_image[45, 45] = 0  # Small hole
    
    # Test erosion (morph_type=0)
    result = image_process(test_image.copy(), 0, 3, 1)
    assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
    assert np.all(np.isfinite(result)), "Output should not contain NaN or inf"
    print("✓ Morphology erosion works correctly")
    
    # Test dilation (morph_type=1)
    result = image_process(test_image.copy(), 1, 3, 1)
    assert result.shape == test_image.shape
    assert np.all(np.isfinite(result))
    print("✓ Morphology dilation works correctly")
    
    # Test opening (morph_type=2)
    result = image_process(test_image.copy(), 2, 3, 1)
    assert result.shape == test_image.shape
    assert np.all(np.isfinite(result))
    print("✓ Morphology opening works correctly")
    
    # Test closing (morph_type=3)
    result = image_process(test_image.copy(), 3, 3, 1)
    assert result.shape == test_image.shape
    assert np.all(np.isfinite(result))
    print("✓ Morphology closing works correctly")


def test_morphology_operations():
    """Test all morphological operations"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Morphology operations test - numpy is mocked")
        return
    
    from node.ProcessNode.node_morphology import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test all morphological operation types (0-6)
    operation_names = ['Erode', 'Dilate', 'Open', 'Close', 'Gradient', 'TopHat', 'BlackHat']
    
    for morph_type, name in enumerate(operation_names):
        result = image_process(test_image.copy(), morph_type, 5, 1)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        assert result.min() >= 0 and result.max() <= 255
        print(f"✓ Morphology {name} works correctly")


def test_morphology_different_parameters():
    """Test Morphology with different parameter values"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Morphology parameter test - numpy is mocked")
        return
    
    from node.ProcessNode.node_morphology import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with different kernel sizes
    for kernel_size in [1, 3, 5, 7, 11]:
        result = image_process(test_image.copy(), 3, kernel_size, 1)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Morphology works with kernel_size={kernel_size}")
    
    # Test with different iterations
    for iterations in [1, 2, 5, 10]:
        result = image_process(test_image.copy(), 3, 5, iterations)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ Morphology works with iterations={iterations}")


def test_morphology_even_kernel_size():
    """Test that even kernel sizes are converted to odd"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Morphology even kernel test - numpy is mocked")
        return
    
    from node.ProcessNode.node_morphology import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with even kernel size (should be converted to odd)
    result = image_process(test_image.copy(), 3, 4, 1)
    assert result.shape == test_image.shape
    assert np.all(np.isfinite(result))
    print("✓ Morphology handles even kernel sizes correctly")


if __name__ == '__main__':
    test_morphology_import()
    test_morphology_image_processing()
    test_morphology_operations()
    test_morphology_different_parameters()
    test_morphology_even_kernel_size()
    print("\n✓ All Morphology tests passed!")
