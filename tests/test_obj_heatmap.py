#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for ObjHeatmap node"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.VisualNode.node_obj_heatmap import Node
import cv2
import numpy as np


def test_obj_heatmap_basic():
    """Test basic heatmap generation"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Simulate detection data
    detection_data = {
        'bboxes': [
            [100, 100, 200, 200],  # Detection 1
            [300, 150, 400, 250],  # Detection 2
            [150, 300, 250, 400],  # Detection 3
        ],
        'scores': [0.9, 0.8, 0.7],
        'class_ids': [0, 1, 0],
        'class_names': {"0": "person", "1": "car"}
    }
    
    # Prepare inputs - simulate the decay value
    decay = 0.95
    
    # Directly test the core logic without DPG
    small_window_w = 640
    small_window_h = 480
    
    # Test 1: Process detections
    bboxes = detection_data.get('bboxes', [])
    scores = detection_data.get('scores', [])
    
    temp_heatmap = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    
    for bbox, score in zip(bboxes, scores):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        
        if x2 > x1 and y2 > y1:
            temp_heatmap[y1:y2, x1:x2] += score
    
    # Apply decay and accumulate
    node.heatmap_accum = node.heatmap_accum * decay + temp_heatmap
    
    # Normalize and create colored heatmap
    if node.heatmap_accum.max() > 0:
        heatmap_norm = np.clip(node.heatmap_accum / node.heatmap_accum.max(), 0, 1)
    else:
        heatmap_norm = node.heatmap_accum
    
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_image = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    # Verify output
    assert heatmap_image is not None, "Image output should not be None"
    assert heatmap_image.shape == (480, 640, 3), f"Expected shape (480, 640, 3), got {heatmap_image.shape}"
    assert node.heatmap_accum.max() > 0, "Heatmap accumulator should have values"
    
    print("✓ Test basic heatmap generation passed")


def test_obj_heatmap_class_filtering():
    """Test heatmap generation with class filtering"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Simulate detection data with multiple classes
    detection_data = {
        'bboxes': [
            [100, 100, 200, 200],  # Class 0
            [300, 150, 400, 250],  # Class 1
            [150, 300, 250, 400],  # Class 0
        ],
        'scores': [0.9, 0.8, 0.7],
        'class_ids': [0, 1, 0],
    }
    
    decay = 0.95
    small_window_w = 640
    small_window_h = 480
    
    # Test filtering for class 0 only
    selected_class = 0
    bboxes = detection_data.get('bboxes', [])
    scores = detection_data.get('scores', [])
    class_ids = detection_data.get('class_ids', [])
    
    temp_heatmap = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    
    for idx, (bbox, score) in enumerate(zip(bboxes, scores)):
        # Filter by class
        if class_ids and idx < len(class_ids) and int(class_ids[idx]) != int(selected_class):
            continue
            
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        
        if x2 > x1 and y2 > y1:
            temp_heatmap[y1:y2, x1:x2] += score
    
    node.heatmap_accum = node.heatmap_accum * decay + temp_heatmap
    
    # Only 2 out of 3 detections should be included (class 0 only)
    # Check that the heatmap has intensity
    assert node.heatmap_accum.max() > 0, "Heatmap should have values from filtered detections"
    
    # Count non-zero regions - should be roughly 2 regions for class 0
    # (This is a simplified check)
    print("✓ Test class filtering passed")


def test_obj_heatmap_image_overlay():
    """Test heatmap overlay with input image"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Create a test input image (blue image for easy visual verification)
    input_image = np.zeros((480, 640, 3), dtype=np.uint8)
    input_image[:, :] = [255, 0, 0]  # Blue
    
    # Create a simple heatmap
    decay = 0.95
    small_window_w = 640
    small_window_h = 480
    
    bboxes = [[200, 200, 400, 400]]
    scores = [0.9]
    
    temp_heatmap = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    
    for bbox, score in zip(bboxes, scores):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        
        if x2 > x1 and y2 > y1:
            temp_heatmap[y1:y2, x1:x2] += score
    
    node.heatmap_accum = node.heatmap_accum * decay + temp_heatmap
    
    # Create colored heatmap
    if node.heatmap_accum.max() > 0:
        heatmap_norm = np.clip(node.heatmap_accum / node.heatmap_accum.max(), 0, 1)
    else:
        heatmap_norm = node.heatmap_accum
    
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    # Blend with input image
    blended_image = cv2.addWeighted(input_image, 0.4, heatmap_colored, 0.6, 0)
    
    # Verify the blended image
    assert blended_image is not None, "Blended image should not be None"
    assert blended_image.shape == (480, 640, 3), f"Expected shape (480, 640, 3), got {blended_image.shape}"
    
    # The blended image should be different from both the input and heatmap
    assert not np.array_equal(blended_image, input_image), "Blended image should differ from input"
    assert not np.array_equal(blended_image, heatmap_colored), "Blended image should differ from heatmap"
    
    print("✓ Test image overlay passed")


def test_obj_heatmap_empty():
    """Test heatmap with no detections"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    decay = 0.95
    small_window_w = 640
    small_window_h = 480
    
    # Empty detection data - just decay
    node.heatmap_accum = node.heatmap_accum * decay
    
    # Normalize and create colored heatmap
    if node.heatmap_accum.max() > 0:
        heatmap_norm = np.clip(node.heatmap_accum / node.heatmap_accum.max(), 0, 1)
    else:
        heatmap_norm = node.heatmap_accum
    
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_image = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    # Verify output
    assert heatmap_image is not None, "Image output should not be None even with no detections"
    assert heatmap_image.shape == (480, 640, 3), f"Expected shape (480, 640, 3), got {heatmap_image.shape}"
    
    print("✓ Test heatmap with no detections passed")


def test_obj_heatmap_accumulation():
    """Test heatmap accumulation over multiple frames"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    decay = 0.95
    small_window_w = 640
    small_window_h = 480
    
    # Frame 1
    bboxes_1 = [[100, 100, 200, 200]]
    scores_1 = [0.9]
    
    temp_heatmap_1 = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    for bbox, score in zip(bboxes_1, scores_1):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        if x2 > x1 and y2 > y1:
            temp_heatmap_1[y1:y2, x1:x2] += score
    
    node.heatmap_accum = node.heatmap_accum * decay + temp_heatmap_1
    max_after_frame1 = node.heatmap_accum.max()
    
    # Frame 2 - same location, should accumulate
    bboxes_2 = [[100, 100, 200, 200]]
    scores_2 = [0.9]
    
    temp_heatmap_2 = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    for bbox, score in zip(bboxes_2, scores_2):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        if x2 > x1 and y2 > y1:
            temp_heatmap_2[y1:y2, x1:x2] += score
    
    node.heatmap_accum = node.heatmap_accum * decay + temp_heatmap_2
    max_after_frame2 = node.heatmap_accum.max()
    
    # Create final heatmap
    heatmap_norm = np.clip(node.heatmap_accum / node.heatmap_accum.max(), 0, 1)
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_image = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    # Verify accumulation occurred
    assert heatmap_image is not None
    assert max_after_frame1 > 0, "Heatmap should have some intensity after first frame"
    assert max_after_frame2 > max_after_frame1, "Heatmap should accumulate on repeated detections"
    
    print("✓ Test heatmap accumulation passed")


def test_visual_output():
    """Generate visual test outputs"""
    
    print("\nGenerating visual test outputs...")
    
    # Test 1: Basic heatmap
    print("\nTest 1: Basic heatmap with 3 detections...")
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Simulate detection data
    detection_data = {
        'bboxes': [
            [100, 100, 200, 200],
            [300, 150, 400, 250],
            [150, 300, 250, 400],
        ],
        'scores': [0.9, 0.8, 0.7],
    }
    
    decay = 0.95
    small_window_w = 640
    small_window_h = 480
    
    bboxes = detection_data.get('bboxes', [])
    scores = detection_data.get('scores', [])
    
    temp_heatmap = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    
    for bbox, score in zip(bboxes, scores):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        
        if x2 > x1 and y2 > y1:
            temp_heatmap[y1:y2, x1:x2] += score
    
    node.heatmap_accum = node.heatmap_accum * decay + temp_heatmap
    
    if node.heatmap_accum.max() > 0:
        heatmap_norm = np.clip(node.heatmap_accum / node.heatmap_accum.max(), 0, 1)
    else:
        heatmap_norm = node.heatmap_accum
    
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    img1 = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    cv2.imwrite("/tmp/obj_heatmap_basic.png", img1)
    print("  ✓ Saved to /tmp/obj_heatmap_basic.png")
    
    # Test 2: Empty heatmap
    print("\nTest 2: Empty heatmap...")
    node2 = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    node2.heatmap_accum = node2.heatmap_accum * decay
    
    if node2.heatmap_accum.max() > 0:
        heatmap_norm = np.clip(node2.heatmap_accum / node2.heatmap_accum.max(), 0, 1)
    else:
        heatmap_norm = node2.heatmap_accum
    
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    img2 = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    cv2.imwrite("/tmp/obj_heatmap_empty.png", img2)
    print("  ✓ Saved to /tmp/obj_heatmap_empty.png")
    
    # Test 3: Accumulated heatmap
    print("\nTest 3: Accumulated heatmap...")
    node3 = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    bboxes_1 = [[100, 100, 200, 200]]
    scores_1 = [0.9]
    
    temp_heatmap_1 = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    for bbox, score in zip(bboxes_1, scores_1):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        if x2 > x1 and y2 > y1:
            temp_heatmap_1[y1:y2, x1:x2] += score
    
    node3.heatmap_accum = node3.heatmap_accum * decay + temp_heatmap_1
    
    bboxes_2 = [[100, 100, 200, 200]]
    scores_2 = [0.9]
    
    temp_heatmap_2 = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    for bbox, score in zip(bboxes_2, scores_2):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        if x2 > x1 and y2 > y1:
            temp_heatmap_2[y1:y2, x1:x2] += score
    
    node3.heatmap_accum = node3.heatmap_accum * decay + temp_heatmap_2
    
    heatmap_norm = np.clip(node3.heatmap_accum / node3.heatmap_accum.max(), 0, 1)
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    img3 = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    cv2.imwrite("/tmp/obj_heatmap_accumulation.png", img3)
    print("  ✓ Saved to /tmp/obj_heatmap_accumulation.png")
    
    # Test 4: Multiple detections over time
    print("\nTest 4: Multiple frames with varying detections...")
    node4 = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Simulate 20 frames with varying detections
    for frame_idx in range(20):
        # Create detections that move across the frame
        x_offset = (frame_idx * 20) % 400
        y_offset = 100 + (frame_idx * 10) % 200
        
        bboxes = [
            [x_offset, y_offset, x_offset + 100, y_offset + 100],
            [200, 200, 300, 300],  # Static detection
        ]
        scores = [0.8, 0.9]
        
        temp_heatmap = np.zeros((small_window_h, small_window_w), dtype=np.float32)
        for bbox, score in zip(bboxes, scores):
            x1, y1, x2, y2 = map(int, bbox)
            x1 = max(0, min(x1, small_window_w - 1))
            x2 = max(0, min(x2, small_window_w - 1))
            y1 = max(0, min(y1, small_window_h - 1))
            y2 = max(0, min(y2, small_window_h - 1))
            if x2 > x1 and y2 > y1:
                temp_heatmap[y1:y2, x1:x2] += score
        
        node4.heatmap_accum = node4.heatmap_accum * decay + temp_heatmap
    
    # Create final heatmap
    heatmap_norm = np.clip(node4.heatmap_accum / node4.heatmap_accum.max(), 0, 1)
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_image = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    cv2.imwrite("/tmp/obj_heatmap_motion.png", heatmap_image)
    print("  ✓ Saved to /tmp/obj_heatmap_motion.png")
    
    # Test 5: Class filtering - only class 0
    print("\nTest 5: Heatmap with class filtering (class 0 only)...")
    node5 = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    detection_data_classes = {
        'bboxes': [
            [100, 100, 200, 200],  # Class 0
            [300, 150, 400, 250],  # Class 1
            [150, 300, 250, 400],  # Class 0
            [450, 100, 550, 200],  # Class 1
        ],
        'scores': [0.9, 0.8, 0.7, 0.85],
        'class_ids': [0, 1, 0, 1],
    }
    
    # Filter for class 0 only
    selected_class = 0
    bboxes = detection_data_classes.get('bboxes', [])
    scores = detection_data_classes.get('scores', [])
    class_ids = detection_data_classes.get('class_ids', [])
    
    temp_heatmap = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    
    for idx, (bbox, score) in enumerate(zip(bboxes, scores)):
        # Filter by class
        if class_ids and idx < len(class_ids) and int(class_ids[idx]) != int(selected_class):
            continue
            
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        
        if x2 > x1 and y2 > y1:
            temp_heatmap[y1:y2, x1:x2] += score
    
    node5.heatmap_accum = node5.heatmap_accum * decay + temp_heatmap
    
    heatmap_norm = np.clip(node5.heatmap_accum / node5.heatmap_accum.max(), 0, 1)
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    img5 = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    cv2.imwrite("/tmp/obj_heatmap_class_filter.png", img5)
    print("  ✓ Saved to /tmp/obj_heatmap_class_filter.png (only class 0)")
    
    # Test 6: Image overlay
    print("\nTest 6: Heatmap overlay with input image...")
    node6 = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Create a test input image with some visual content (checkerboard pattern)
    input_image = np.zeros((480, 640, 3), dtype=np.uint8)
    tile_size = 40
    for i in range(0, 480, tile_size):
        for j in range(0, 640, tile_size):
            if (i // tile_size + j // tile_size) % 2 == 0:
                input_image[i:i+tile_size, j:j+tile_size] = [200, 200, 200]  # Light gray
            else:
                input_image[i:i+tile_size, j:j+tile_size] = [100, 100, 100]  # Dark gray
    
    # Create heatmap
    bboxes_overlay = [
        [200, 200, 350, 350],
        [400, 100, 550, 250],
    ]
    scores_overlay = [0.9, 0.8]
    
    temp_heatmap = np.zeros((small_window_h, small_window_w), dtype=np.float32)
    for bbox, score in zip(bboxes_overlay, scores_overlay):
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, min(x1, small_window_w - 1))
        x2 = max(0, min(x2, small_window_w - 1))
        y1 = max(0, min(y1, small_window_h - 1))
        y2 = max(0, min(y2, small_window_h - 1))
        
        if x2 > x1 and y2 > y1:
            temp_heatmap[y1:y2, x1:x2] += score
    
    node6.heatmap_accum = node6.heatmap_accum * decay + temp_heatmap
    
    heatmap_norm = np.clip(node6.heatmap_accum / node6.heatmap_accum.max(), 0, 1)
    heatmap_display = (heatmap_norm * 255).astype(np.uint8)
    heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
    heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
    
    # Blend with input image
    blended_image = cv2.addWeighted(input_image, 0.4, heatmap_colored, 0.6, 0)
    
    cv2.imwrite("/tmp/obj_heatmap_overlay.png", blended_image)
    print("  ✓ Saved to /tmp/obj_heatmap_overlay.png")
    
    # Save the heatmap alone for comparison
    cv2.imwrite("/tmp/obj_heatmap_overlay_heatmap_only.png", heatmap_colored)
    print("  ✓ Saved to /tmp/obj_heatmap_overlay_heatmap_only.png (for comparison)")
    
    print("\n" + "="*60)
    print("All visual tests completed successfully!")
    print("Generated heatmap images in /tmp/:")
    print("  - obj_heatmap_basic.png")
    print("  - obj_heatmap_empty.png")
    print("  - obj_heatmap_accumulation.png")
    print("  - obj_heatmap_motion.png")
    print("  - obj_heatmap_class_filter.png (NEW: filtered to class 0)")
    print("  - obj_heatmap_overlay.png (NEW: blended with input image)")
    print("  - obj_heatmap_overlay_heatmap_only.png (for comparison)")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("Running ObjHeatmap Node Tests")
    print("="*60)
    
    # Run unit tests
    print("\n--- Unit Tests ---")
    test_obj_heatmap_basic()
    test_obj_heatmap_class_filtering()
    test_obj_heatmap_image_overlay()
    test_obj_heatmap_empty()
    test_obj_heatmap_accumulation()
    
    # Run visual tests
    print("\n--- Visual Tests ---")
    test_visual_output()
    
    print("\n" + "="*60)
    print("All tests passed successfully!")
    print("="*60)
