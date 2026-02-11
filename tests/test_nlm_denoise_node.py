#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for NLM Denoise node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_nlm_denoise_import():
    """Test that NLM Denoise node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_nlm_denoise as nlm_module
        print(f"✓ node.ProcessNode.node_nlm_denoise imported successfully")
        assert hasattr(nlm_module, 'FactoryNode')
        assert hasattr(nlm_module, 'Node')
        print(f"✓ NLM Denoise node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_nlm_denoise: {e}")
        raise


def test_nlm_denoise_image_processing():
    """Test the NLM Denoise image processing function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping NLM Denoise image processing test - numpy is mocked")
        return
    
    from node.ProcessNode.node_nlm_denoise import image_process
    
    # Create a test image with noise
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test with default parameters
    h = 10.0
    h_color = 10.0
    template_size = 7
    search_size = 21
    
    result = image_process(test_image.copy(), h, h_color, template_size, search_size)
    
    # Check that result is same shape
    assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
    
    # Check that output is valid image
    assert np.all(np.isfinite(result)), "Output should not contain NaN or inf"
    
    # Check value range
    assert result.min() >= 0 and result.max() <= 255, "Output values should be in valid range [0, 255]"
    
    print("✓ NLM Denoise image processing works correctly")


def test_nlm_denoise_different_parameters():
    """Test NLM Denoise with different parameter values"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping NLM Denoise parameter test - numpy is mocked")
        return
    
    from node.ProcessNode.node_nlm_denoise import image_process
    
    # Create a small test image (NLM is slow on large images)
    test_image = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
    
    # Test with different h values
    for h in [5.0, 10.0, 15.0]:
        result = image_process(test_image.copy(), h, h, 7, 21)
        assert result.shape == test_image.shape
        assert np.all(np.isfinite(result))
        print(f"✓ NLM Denoise works with h={h}")


if __name__ == '__main__':
    test_nlm_denoise_import()
    test_nlm_denoise_image_processing()
    test_nlm_denoise_different_parameters()
    print("\n✓ All NLM Denoise tests passed!")
