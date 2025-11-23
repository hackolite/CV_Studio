#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for ObjHeatmap coordinate scaling fix"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from node.VisualNode.node_obj_heatmap import Node
import cv2
import numpy as np


def test_coordinate_scaling_fullhd_to_vga():
    """Test coordinate scaling from Full HD (1920x1080) to VGA (640x480)"""
    
    # Create node with VGA processing window
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Mock dpg functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        # Setup mock return values
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "All"
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        # Create Full HD input image (1920x1080)
        input_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        input_image[:, :] = [100, 100, 100]
        
        # Detection at center of Full HD image
        # Center is at (960, 540), create a 200x100 box
        detection_data = {
            'bboxes': [[860, 490, 1060, 590]],  # Center of 1920x1080
            'scores': [0.9],
            'class_ids': [0]
        }
        
        # Expected scaled bbox for 640x480
        # scale_x = 640/1920 = 1/3
        # scale_y = 480/1080 = 4/9
        expected_x1 = int(860 * 640 / 1920)  # ~287
        expected_y1 = int(490 * 480 / 1080)  # ~218
        expected_x2 = int(1060 * 640 / 1920)  # ~354
        expected_y2 = int(590 * 480 / 1080)  # ~262
        
        # Run update
        result = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': input_image},
            node_result_dict={'2:JsonNode': detection_data},
            node_audio_dict={}
        )
        
        # Verify output was generated
        assert result['image'] is not None, "Should generate output"
        assert result['image'].shape == (480, 640, 3), f"Expected (480, 640, 3), got {result['image'].shape}"
        
        # Verify heatmap has intensity in the expected region (center)
        # The heatmap accumulator should have values in the scaled bbox region
        center_region = node.heatmap_accum[expected_y1:expected_y2, expected_x1:expected_x2]
        assert center_region.max() > 0, "Heatmap should have intensity in scaled bbox region"
        
        # Verify that edges don't have intensity (they would if scaling wasn't applied)
        right_edge = node.heatmap_accum[:, 630:]
        assert right_edge.max() < center_region.max() * 0.1, "Right edge should not have significant intensity"
        
        print("✓ Test Full HD to VGA scaling passed")


def test_coordinate_scaling_4k_to_hd():
    """Test coordinate scaling from 4K (3840x2160) to HD (1920x1080)"""
    
    # Create node with HD processing window
    node = Node(opencv_setting_dict={
        'process_height': 1080,
        'process_width': 1920,
        'use_pref_counter': False
    })
    
    # Mock dpg functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "All"
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        # Create 4K input image (3840x2160)
        input_image = np.zeros((2160, 3840, 3), dtype=np.uint8)
        input_image[:, :] = [100, 100, 100]
        
        # Detection at top-left quadrant of 4K image
        detection_data = {
            'bboxes': [[400, 300, 800, 600]],  # Top-left area of 4K
            'scores': [0.8],
            'class_ids': [1]
        }
        
        # Expected scaled bbox for 1920x1080 (everything divided by 2)
        expected_x1 = int(400 * 1920 / 3840)  # 200
        expected_y1 = int(300 * 1080 / 2160)  # 150
        expected_x2 = int(800 * 1920 / 3840)  # 400
        expected_y2 = int(600 * 1080 / 2160)  # 300
        
        # Run update
        result = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': input_image},
            node_result_dict={'2:JsonNode': detection_data},
            node_audio_dict={}
        )
        
        # Verify output
        assert result['image'] is not None
        assert result['image'].shape == (1080, 1920, 3)
        
        # Verify heatmap has intensity in the expected region
        topleft_region = node.heatmap_accum[expected_y1:expected_y2, expected_x1:expected_x2]
        assert topleft_region.max() > 0, "Heatmap should have intensity in scaled bbox region"
        
        print("✓ Test 4K to HD scaling passed")


def test_coordinate_scaling_same_size():
    """Test that scaling works correctly when input size matches processing size"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Mock dpg functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "All"
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        # Input image same size as processing window
        input_image = np.zeros((480, 640, 3), dtype=np.uint8)
        input_image[:, :] = [100, 100, 100]
        
        # Detection coordinates
        detection_data = {
            'bboxes': [[100, 100, 200, 200]],
            'scores': [0.9],
            'class_ids': [0]
        }
        
        # Run update
        result = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': input_image},
            node_result_dict={'2:JsonNode': detection_data},
            node_audio_dict={}
        )
        
        # When input size = processing size, scale = 1.0, so coords should be unchanged
        assert result['image'] is not None
        
        # Verify heatmap has intensity in the exact region
        region = node.heatmap_accum[100:200, 100:200]
        assert region.max() > 0, "Heatmap should have intensity at bbox location"
        
        print("✓ Test same size (no scaling needed) passed")


def test_coordinate_scaling_with_class_filter():
    """Test that coordinate scaling works correctly with class filtering"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Mock dpg functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "0"  # Filter for class 0 only
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        # Full HD input image
        input_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        input_image[:, :] = [100, 100, 100]
        
        # Multiple detections with different classes
        detection_data = {
            'bboxes': [
                [860, 490, 1060, 590],   # Center - class 0
                [100, 100, 300, 300],     # Top-left - class 1
                [1620, 780, 1820, 980],  # Bottom-right - class 0
            ],
            'scores': [0.9, 0.8, 0.7],
            'class_ids': [0, 1, 0]
        }
        
        # Run update
        result = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': input_image},
            node_result_dict={'2:JsonNode': detection_data},
            node_audio_dict={}
        )
        
        # Verify output
        assert result['image'] is not None
        
        # Only class 0 detections should be in heatmap (indices 0 and 2)
        # Class 1 detection (index 1) should be filtered out
        
        # Check center region (class 0 - should have intensity)
        center_x1 = int(860 * 640 / 1920)
        center_y1 = int(490 * 480 / 1080)
        center_x2 = int(1060 * 640 / 1920)
        center_y2 = int(590 * 480 / 1080)
        center_region = node.heatmap_accum[center_y1:center_y2, center_x1:center_x2]
        assert center_region.max() > 0, "Class 0 center detection should be in heatmap"
        
        # Check top-left region (class 1 - should NOT have intensity)
        topleft_x1 = int(100 * 640 / 1920)
        topleft_y1 = int(100 * 480 / 1080)
        topleft_x2 = int(300 * 640 / 1920)
        topleft_y2 = int(300 * 480 / 1080)
        topleft_region = node.heatmap_accum[topleft_y1:topleft_y2, topleft_x1:topleft_x2]
        assert topleft_region.max() == 0, "Class 1 detection should be filtered out"
        
        print("✓ Test coordinate scaling with class filter passed")


def test_visual_coordinate_scaling():
    """Generate visual outputs to demonstrate coordinate scaling fix"""
    
    print("\nGenerating visual validation outputs...")
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Mock dpg functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "All"
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        # Create Full HD input image with visual markers
        input_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        input_image[:, :] = [50, 50, 50]  # Dark gray background
        
        # Draw colored rectangles at specific positions
        # Center (green)
        cv2.rectangle(input_image, (860, 490), (1060, 590), (0, 255, 0), -1)
        # Top-left (red)
        cv2.rectangle(input_image, (100, 100), (300, 300), (0, 0, 255), -1)
        # Bottom-right (blue)
        cv2.rectangle(input_image, (1620, 780), (1820, 980), (255, 0, 0), -1)
        
        # Detections matching the visual markers
        detection_data = {
            'bboxes': [
                [860, 490, 1060, 590],   # Center - green
                [100, 100, 300, 300],     # Top-left - red
                [1620, 780, 1820, 980],  # Bottom-right - blue
            ],
            'scores': [0.9, 0.8, 0.7],
            'class_ids': [0, 1, 2]
        }
        
        # Run update
        result = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': input_image},
            node_result_dict={'2:JsonNode': detection_data},
            node_audio_dict={}
        )
        
        # Save outputs
        cv2.imwrite("/tmp/coord_scaling_input_fullhd.png", input_image)
        print("  ✓ Saved Full HD input with colored markers to /tmp/coord_scaling_input_fullhd.png")
        
        # Resize input to processing size for comparison
        input_resized = cv2.resize(input_image, (640, 480))
        cv2.imwrite("/tmp/coord_scaling_input_resized.png", input_resized)
        print("  ✓ Saved resized input (640x480) to /tmp/coord_scaling_input_resized.png")
        
        # Save heatmap overlay
        if result['image'] is not None:
            cv2.imwrite("/tmp/coord_scaling_heatmap_overlay.png", result['image'])
            print("  ✓ Saved heatmap overlay to /tmp/coord_scaling_heatmap_overlay.png")
            print("    → Heatmap hotspots should align with colored rectangles in resized input")
        
        print("\n" + "="*60)
        print("Visual validation complete!")
        print("Compare the files to verify heatmap positions match markers:")
        print("  1. coord_scaling_input_resized.png - has colored rectangles")
        print("  2. coord_scaling_heatmap_overlay.png - heatmap should align")
        print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("Running ObjHeatmap Coordinate Scaling Tests")
    print("="*60)
    
    print("\n--- Unit Tests ---")
    test_coordinate_scaling_fullhd_to_vga()
    test_coordinate_scaling_4k_to_hd()
    test_coordinate_scaling_same_size()
    test_coordinate_scaling_with_class_filter()
    
    print("\n--- Visual Validation ---")
    test_visual_coordinate_scaling()
    
    print("\n" + "="*60)
    print("All coordinate scaling tests passed successfully!")
    print("="*60)
