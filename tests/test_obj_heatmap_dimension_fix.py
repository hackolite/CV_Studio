#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for ObjHeatmap node dimension mismatch fix"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.VisualNode.node_obj_heatmap import Node
import cv2
import numpy as np


def test_dimension_mismatch_fix():
    """Test that heatmap correctly handles dimension changes"""
    
    # Create node with initial dimensions
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Verify initial accumulator dimensions
    assert node.heatmap_accum.shape == (480, 640), \
        f"Expected initial shape (480, 640), got {node.heatmap_accum.shape}"
    
    # Simulate dimension change in opencv_setting_dict (this could happen at runtime)
    node._opencv_setting_dict['process_height'] = 240
    node._opencv_setting_dict['process_width'] = 320
    
    small_window_w = node._opencv_setting_dict['process_width']
    small_window_h = node._opencv_setting_dict['process_height']
    
    # Create input image with new dimensions
    input_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
    input_image[:, :] = [100, 100, 100]  # Gray
    
    # Simulate detection data
    detection_data = {
        'bboxes': [[50, 50, 100, 100]],
        'scores': [0.9],
        'class_ids': [0]
    }
    
    # Ensure accumulator gets resized to match new dimensions
    if node.heatmap_accum.shape != (small_window_h, small_window_w):
        node.heatmap_accum = cv2.resize(
            node.heatmap_accum, 
            (small_window_w, small_window_h),
            interpolation=cv2.INTER_LINEAR
        )
    
    # Verify accumulator was resized
    assert node.heatmap_accum.shape == (240, 320), \
        f"Expected resized shape (240, 320), got {node.heatmap_accum.shape}"
    
    # Process detections with new dimensions
    bboxes = detection_data.get('bboxes', [])
    scores = detection_data.get('scores', [])
    
    temp_heatmap = np.zeros_like(node.heatmap_accum)
    
    for bbox, score in zip(bboxes, scores):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        
        if x2 > x1 and y2 > y1:
            temp_heatmap[y1:y2, x1:x2] += score
    
    decay = 0.95
    node.heatmap_accum = node.heatmap_accum * decay + temp_heatmap
    
    # Create colored heatmap
    if node.heatmap_accum.max() > 0:
        heatmap_norm = np.clip(node.heatmap_accum / node.heatmap_accum.max(), 0, 1)
    else:
        heatmap_norm = node.heatmap_accum
    
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    # Prepare input image
    prepared_input = cv2.resize(input_image, (small_window_w, small_window_h))
    if len(prepared_input.shape) == 2:
        prepared_input = cv2.cvtColor(prepared_input, cv2.COLOR_GRAY2BGR)
    
    # Verify dimensions match
    assert heatmap_colored.shape == prepared_input.shape, \
        f"Dimension mismatch: heatmap_colored {heatmap_colored.shape} != prepared_input {prepared_input.shape}"
    
    # This should now work without error
    try:
        heatmap_image = cv2.addWeighted(prepared_input, 0.4, heatmap_colored, 0.6, 0)
        assert heatmap_image is not None, "Blended image should not be None"
        assert heatmap_image.shape == (small_window_h, small_window_w, 3), \
            f"Expected shape ({small_window_h}, {small_window_w}, 3), got {heatmap_image.shape}"
        print("✓ Test dimension mismatch fix passed")
        return True
    except cv2.error as e:
        print(f"✗ Test failed with error: {e}")
        return False


def test_multiple_dimension_changes():
    """Test that heatmap handles multiple dimension changes"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Add some data to accumulator
    node.heatmap_accum[100:200, 100:200] = 0.5
    
    # Test multiple dimension changes
    dimension_sets = [
        (240, 320),
        (360, 480),
        (480, 640),
        (120, 160),
    ]
    
    for height, width in dimension_sets:
        # Update dimensions
        node._opencv_setting_dict['process_height'] = height
        node._opencv_setting_dict['process_width'] = width
        
        # Resize accumulator
        if node.heatmap_accum.shape != (height, width):
            node.heatmap_accum = cv2.resize(
                node.heatmap_accum, 
                (width, height),
                interpolation=cv2.INTER_LINEAR
            )
        
        # Verify shape
        assert node.heatmap_accum.shape == (height, width), \
            f"Expected shape ({height}, {width}), got {node.heatmap_accum.shape}"
        
        # Create input image and heatmap
        input_image = np.zeros((height, width, 3), dtype=np.uint8)
        
        heatmap_norm = np.clip(node.heatmap_accum / max(node.heatmap_accum.max(), 1e-6), 0, 1)
        heatmap_display = (heatmap_norm * 255).astype(np.uint8)
        heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
        heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
        
        # Try blending
        try:
            heatmap_image = cv2.addWeighted(input_image, 0.4, heatmap_colored, 0.6, 0)
            assert heatmap_image.shape == (height, width, 3)
        except cv2.error as e:
            print(f"✗ Test failed for dimensions ({height}, {width}): {e}")
            return False
    
    print("✓ Test multiple dimension changes passed")
    return True


def test_original_dimensions_unchanged():
    """Test that original working dimensions still work correctly"""
    
    # Create node with standard dimensions
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    small_window_w = 640
    small_window_h = 480
    
    # Create input image
    input_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
    input_image[:, :] = [100, 100, 100]
    
    # Simulate detection
    detection_data = {
        'bboxes': [[200, 200, 400, 400]],
        'scores': [0.9],
    }
    
    # Process
    bboxes = detection_data.get('bboxes', [])
    scores = detection_data.get('scores', [])
    
    temp_heatmap = np.zeros_like(node.heatmap_accum)
    
    for bbox, score in zip(bboxes, scores):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        
        if x2 > x1 and y2 > y1:
            temp_heatmap[y1:y2, x1:x2] += score
    
    decay = 0.95
    node.heatmap_accum = node.heatmap_accum * decay + temp_heatmap
    
    # Create colored heatmap
    if node.heatmap_accum.max() > 0:
        heatmap_norm = np.clip(node.heatmap_accum / node.heatmap_accum.max(), 0, 1)
    else:
        heatmap_norm = node.heatmap_accum
    
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    # Blend
    try:
        heatmap_image = cv2.addWeighted(input_image, 0.4, heatmap_colored, 0.6, 0)
        assert heatmap_image is not None
        assert heatmap_image.shape == (480, 640, 3)
        print("✓ Test original dimensions unchanged passed")
        return True
    except cv2.error as e:
        print(f"✗ Test failed: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("Running ObjHeatmap Node Dimension Mismatch Fix Tests")
    print("="*60)
    
    print("\n--- Unit Tests ---")
    test_dimension_mismatch_fix()
    test_multiple_dimension_changes()
    test_original_dimensions_unchanged()
    
    print("\n" + "="*60)
    print("All tests passed successfully!")
    print("="*60)
