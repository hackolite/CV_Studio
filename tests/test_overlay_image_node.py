#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for OverlayImage node functionality.
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_overlay_image_basic():
    """Test basic overlay functionality"""
    from node.OverlayNode.node_overlay_image import OverlayImageNode
    
    node = OverlayImageNode()
    node._opencv_setting_dict = {
        'process_width': 640,
        'process_height': 480
    }
    
    # Create master image (blue background)
    master_image = np.zeros((480, 640, 3), dtype=np.uint8)
    master_image[:, :] = (255, 0, 0)  # Blue in BGR
    
    # Create overlay image (red square)
    overlay_image = np.zeros((100, 100, 3), dtype=np.uint8)
    overlay_image[:, :] = (0, 0, 255)  # Red in BGR
    
    # Test overlay at position (50, 50) with full opacity
    result = node._overlay_image(master_image, overlay_image, 50, 50, 0, 0, 1.0)
    
    # Check that the overlay region is red
    overlay_region = result[50:150, 50:150]
    assert np.all(overlay_region[:, :, 2] == 255), "Overlay should be red"
    assert np.all(overlay_region[:, :, 0] == 0), "Overlay should have no blue"
    
    print("✓ Basic overlay works")
    print(f"  Master image: {master_image.shape}")
    print(f"  Overlay image: {overlay_image.shape}")
    print(f"  Position: (50, 50)")
    print(f"  Overlay applied successfully")
    
    return True


def test_overlay_with_transparency():
    """Test overlay with transparency"""
    from node.OverlayNode.node_overlay_image import OverlayImageNode
    
    node = OverlayImageNode()
    node._opencv_setting_dict = {
        'process_width': 640,
        'process_height': 480
    }
    
    # Create master image (white background)
    master_image = np.ones((480, 640, 3), dtype=np.uint8) * 255
    
    # Create overlay image (black square)
    overlay_image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Test overlay with 50% transparency
    result = node._overlay_image(master_image, overlay_image, 50, 50, 0, 0, 0.5)
    
    # Check that the overlay region is gray (blend of white and black)
    overlay_region = result[50:150, 50:150]
    # With 50% alpha, blending white (255) and black (0) should give ~127
    assert np.all(overlay_region[:, :, 0] > 100), "Overlay should be blended"
    assert np.all(overlay_region[:, :, 0] < 150), "Overlay should be blended"
    
    print("✓ Transparency works")
    print(f"  Alpha: 0.5 (50% transparent)")
    print(f"  Blended pixel value: {overlay_region[0, 0, 0]}")
    
    return True


def test_overlay_with_resize():
    """Test overlay with resizing"""
    from node.OverlayNode.node_overlay_image import OverlayImageNode
    
    node = OverlayImageNode()
    node._opencv_setting_dict = {
        'process_width': 640,
        'process_height': 480
    }
    
    # Create master image
    master_image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Create overlay image (100x100)
    overlay_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    # Test overlay with resizing to 200x200
    result = node._overlay_image(master_image, overlay_image, 50, 50, 200, 200, 1.0)
    
    # Check that the overlay region is 200x200
    overlay_region = result[50:250, 50:250]
    assert overlay_region.shape == (200, 200, 3), "Overlay should be resized"
    assert np.all(overlay_region == 255), "Resized overlay should be white"
    
    print("✓ Resizing works")
    print(f"  Original overlay size: (100, 100)")
    print(f"  Resized to: (200, 200)")
    print(f"  Applied successfully")
    
    return True


def test_overlay_negative_position():
    """Test overlay with negative position (partial overlay)"""
    from node.OverlayNode.node_overlay_image import OverlayImageNode
    
    node = OverlayImageNode()
    node._opencv_setting_dict = {
        'process_width': 640,
        'process_height': 480
    }
    
    # Create master image
    master_image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Create overlay image
    overlay_image = np.ones((100, 100, 3), dtype=np.uint8) * 200
    
    # Test overlay with negative position (only part visible)
    result = node._overlay_image(master_image, overlay_image, -50, -50, 0, 0, 1.0)
    
    # Check that only the bottom-right part of overlay is visible
    visible_region = result[0:50, 0:50]
    assert np.all(visible_region == 200), "Visible part should show overlay"
    
    print("✓ Negative positioning works")
    print(f"  Position: (-50, -50)")
    print(f"  Only bottom-right 50x50 visible")
    
    return True


def test_overlay_beyond_bounds():
    """Test overlay extending beyond master image bounds"""
    from node.OverlayNode.node_overlay_image import OverlayImageNode
    
    node = OverlayImageNode()
    node._opencv_setting_dict = {
        'process_width': 640,
        'process_height': 480
    }
    
    # Create master image
    master_image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Create overlay image
    overlay_image = np.ones((100, 100, 3), dtype=np.uint8) * 150
    
    # Test overlay that extends beyond bounds
    result = node._overlay_image(master_image, overlay_image, 600, 430, 0, 0, 1.0)
    
    # Check that only the visible part is overlaid
    visible_region = result[430:480, 600:640]
    assert np.all(visible_region == 150), "Visible part should show overlay"
    
    print("✓ Clipping at bounds works")
    print(f"  Position: (600, 430) with 100x100 overlay")
    print(f"  Only 40x50 visible (clipped at edges)")
    
    return True


def test_overlay_no_overlap():
    """Test overlay with no overlap (completely outside)"""
    from node.OverlayNode.node_overlay_image import OverlayImageNode
    
    node = OverlayImageNode()
    node._opencv_setting_dict = {
        'process_width': 640,
        'process_height': 480
    }
    
    # Create master image
    master_image = np.zeros((480, 640, 3), dtype=np.uint8)
    master_image[:, :] = (100, 100, 100)  # Gray
    
    # Create overlay image
    overlay_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    # Test overlay completely outside bounds
    result = node._overlay_image(master_image, overlay_image, 1000, 1000, 0, 0, 1.0)
    
    # Master image should be unchanged
    assert np.array_equal(result, master_image), "Master image should be unchanged"
    
    print("✓ No overlap handling works")
    print(f"  Position: (1000, 1000) - completely outside")
    print(f"  Master image unchanged")
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing OverlayImage Node")
    print("=" * 70)
    print()
    
    try:
        test_overlay_image_basic()
        print()
        
        test_overlay_with_transparency()
        print()
        
        test_overlay_with_resize()
        print()
        
        test_overlay_negative_position()
        print()
        
        test_overlay_beyond_bounds()
        print()
        
        test_overlay_no_overlap()
        print()
        
        print("=" * 70)
        print("All tests passed!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
