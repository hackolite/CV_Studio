#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Color Space node functionality
"""

import sys
import os
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import cv2


def test_color_space_import():
    """Test that Color Space node can be imported"""
    # Mock dependencies
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    try:
        import node.ProcessNode.node_color_space as color_module
        print(f"✓ node.ProcessNode.node_color_space imported successfully")
        assert hasattr(color_module, 'FactoryNode')
        assert hasattr(color_module, 'Node')
        print(f"✓ Color Space node has required classes")
    except Exception as e:
        print(f"✗ Failed to import node_color_space: {e}")
        raise


def test_color_space_conversions():
    """Test color space conversion function"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Color Space conversion test - numpy is mocked")
        return
    
    from node.ProcessNode.node_color_space import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Test all color space conversions
    color_spaces = {
        0: 'BGR',
        1: 'HSV',
        2: 'YCrCb',
        3: 'LAB',
        4: 'HLS',
    }
    
    for cs_id, cs_name in color_spaces.items():
        result = image_process(test_image.copy(), cs_id)
        
        # Check that result is same shape
        assert result.shape == test_image.shape, f"Expected shape {test_image.shape}, got {result.shape}"
        
        # Check that output is valid image
        assert np.all(np.isfinite(result)), f"Output for {cs_name} should not contain NaN or inf"
        
        # Check value range
        assert result.min() >= 0 and result.max() <= 255, f"Output values for {cs_name} should be in valid range [0, 255]"
        
        print(f"✓ Color Space conversion to {cs_name} works correctly")


def test_color_space_bgr_passthrough():
    """Test that BGR (0) is pass-through"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Color Space BGR test - numpy is mocked")
        return
    
    from node.ProcessNode.node_color_space import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # BGR should be pass-through
    result = image_process(test_image.copy(), 0)
    
    assert np.array_equal(result, test_image), "BGR conversion should be pass-through"
    print("✓ BGR pass-through works correctly")


def test_color_space_preserves_channels():
    """Test that color space conversion preserves data without reverse conversion"""
    # Skip if cv2 or numpy are mocked
    import sys
    if hasattr(sys.modules.get('numpy', None), 'MagicMock'):
        print("⊘ Skipping Color Space channel test - numpy is mocked")
        return
    
    from node.ProcessNode.node_color_space import image_process
    
    # Create a test image
    test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Convert to HSV
    result = image_process(test_image.copy(), 1)
    
    # Manually convert to HSV to verify
    expected = cv2.cvtColor(test_image, cv2.COLOR_BGR2HSV)
    
    # Results should match (no reverse conversion)
    assert np.array_equal(result, expected), "Color space should return raw converted data"
    print("✓ Color space conversion preserves raw data without reverse conversion")


if __name__ == '__main__':
    test_color_space_import()
    test_color_space_conversions()
    test_color_space_bgr_passthrough()
    test_color_space_preserves_channels()
    print("\n✓ All Color Space tests passed!")
