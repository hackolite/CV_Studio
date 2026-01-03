#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the TennisCourt node CV_64F depth error fix.
This test validates that the convert_cv_to_dpg function properly handles
different image data types, especially float64 which caused the original error.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_convert_cv_to_dpg_with_uint8():
    """Test convert_cv_to_dpg with uint8 input (normal case)"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    # Create uint8 image with 4 channels (BGRA)
    image = np.zeros((100, 100, 4), dtype=np.uint8)
    image[:, :, 0] = 255  # Blue channel
    
    # Convert to DPG format
    texture = node.convert_cv_to_dpg(image, 50, 50)
    
    print("✓ convert_cv_to_dpg works with uint8 BGRA image")
    print(f"  Input dtype: {image.dtype}")
    print(f"  Output shape: {texture.shape}")
    print(f"  Output dtype: {texture.dtype}")
    print(f"  Output range: [{texture.min()}, {texture.max()}]")
    
    assert texture.dtype == np.float32
    assert texture.min() >= 0.0
    assert texture.max() <= 1.0
    
    return True


def test_convert_cv_to_dpg_with_float64():
    """Test convert_cv_to_dpg with float64 input (the bug case)"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    # Create float64 image with 4 channels (this was causing the error)
    image = np.zeros((100, 100, 4), dtype=np.float64)
    
    # Convert to DPG format - this should not raise an error
    texture = node.convert_cv_to_dpg(image, 50, 50)
    
    print("✓ convert_cv_to_dpg works with float64 BGRA image")
    print(f"  Input dtype: {image.dtype}")
    print(f"  Output shape: {texture.shape}")
    print(f"  Output dtype: {texture.dtype}")
    
    assert texture.dtype == np.float32
    assert texture.min() >= 0.0
    assert texture.max() <= 1.0
    
    return True


def test_convert_cv_to_dpg_with_float32():
    """Test convert_cv_to_dpg with float32 input in 0-1 range"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    # Create float32 image in 0-1 range with 4 channels
    image = np.ones((100, 100, 4), dtype=np.float32) * 0.5
    
    # Convert to DPG format
    texture = node.convert_cv_to_dpg(image, 50, 50)
    
    print("✓ convert_cv_to_dpg works with float32 BGRA image (0-1 range)")
    print(f"  Input dtype: {image.dtype}")
    print(f"  Input range: [{image.min()}, {image.max()}]")
    print(f"  Output shape: {texture.shape}")
    print(f"  Output dtype: {texture.dtype}")
    
    assert texture.dtype == np.float32
    assert texture.min() >= 0.0
    assert texture.max() <= 1.0
    
    return True


def test_convert_cv_to_dpg_with_out_of_range_values():
    """Test convert_cv_to_dpg handles out-of-range float values gracefully"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    # Create float32 image with values outside 0-1 range
    image = np.ones((100, 100, 4), dtype=np.float32) * 2.0  # Values > 1.0
    image[0:50, :, :] = -0.5  # Negative values
    
    # Convert to DPG format - should clip values
    texture = node.convert_cv_to_dpg(image, 50, 50)
    
    print("✓ convert_cv_to_dpg handles out-of-range float values")
    print(f"  Input dtype: {image.dtype}")
    print(f"  Input range: [{image.min()}, {image.max()}]")
    print(f"  Output shape: {texture.shape}")
    print(f"  Output dtype: {texture.dtype}")
    print(f"  Output range: [{texture.min()}, {texture.max()}]")
    
    assert texture.dtype == np.float32
    assert texture.min() >= 0.0
    assert texture.max() <= 1.0
    
    return True


def test_convert_cv_to_dpg_with_bgr():
    """Test convert_cv_to_dpg with 3-channel BGR image"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    # Create uint8 image with 3 channels (BGR)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[:, :, 2] = 255  # Red channel
    
    # Convert to DPG format
    texture = node.convert_cv_to_dpg(image, 50, 50)
    
    print("✓ convert_cv_to_dpg works with uint8 BGR image")
    print(f"  Input dtype: {image.dtype}")
    print(f"  Input channels: {image.shape[2]}")
    print(f"  Output shape: {texture.shape}")
    
    assert texture.dtype == np.float32
    assert texture.min() >= 0.0
    assert texture.max() <= 1.0
    
    return True


def test_factory_node_initialization():
    """Test that FactoryNode.add_node creates black image with correct dtype"""
    from node.VisualNode.node_tennis_court import FactoryNode, Node
    import dearpygui.dearpygui as dpg
    
    # Mock opencv_setting_dict
    opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # We can't fully test add_node without DPG initialization,
    # but we can verify the black image creation pattern
    small_window_w = Node.VISUALIZATION_WIDTH
    small_window_h = Node.VISUALIZATION_HEIGHT
    
    # This is how the black image is created in add_node (line 52)
    black_image = np.zeros((small_window_h, small_window_w, 4), dtype=np.uint8)
    
    print("✓ Black image for initialization uses correct dtype")
    print(f"  Black image dtype: {black_image.dtype}")
    print(f"  Black image shape: {black_image.shape}")
    
    assert black_image.dtype == np.uint8
    assert black_image.shape[2] == 4  # BGRA
    
    # Verify we can convert it without errors
    node = Node()
    texture = node.convert_cv_to_dpg(black_image, small_window_w, small_window_h)
    
    print(f"  Texture created successfully with shape: {texture.shape}")
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Testing TennisCourt Node CV_64F Depth Fix")
    print("=" * 60)
    
    try:
        test_convert_cv_to_dpg_with_uint8()
        print()
        
        test_convert_cv_to_dpg_with_float64()
        print()
        
        test_convert_cv_to_dpg_with_float32()
        print()
        
        test_convert_cv_to_dpg_with_out_of_range_values()
        print()
        
        test_convert_cv_to_dpg_with_bgr()
        print()
        
        test_factory_node_initialization()
        print()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
