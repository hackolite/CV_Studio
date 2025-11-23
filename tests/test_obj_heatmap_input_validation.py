#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for ObjHeatmap node input validation - requires both image and JSON"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from node.VisualNode.node_obj_heatmap import Node
import numpy as np


def test_no_output_without_both_inputs():
    """Test that no output is generated when either input is missing"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Mock dpg functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        # Setup mock return values for decay and class
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "All"
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        # Test Case 1: No image, no JSON - should not generate output
        result = node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={},
            node_audio_dict={}
        )
        
        assert result['image'] is None, "Should not generate output without inputs"
        print("✓ Test Case 1: No image, no JSON - correctly returns None")
        
        # Test Case 2: Image but no JSON - should not generate output
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:, :] = [255, 0, 0]  # Blue image
        
        result = node.update(
            node_id=1,
            connection_list=[('1:NodeType:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01')],
            node_image_dict={'1:NodeType': test_image},
            node_result_dict={},
            node_audio_dict={}
        )
        
        assert result['image'] is None, "Should not generate output with only image input"
        print("✓ Test Case 2: Image but no JSON - correctly returns None")
        
        # Test Case 3: JSON but no image - should not generate output
        detection_data = {
            'bboxes': [[100, 100, 200, 200]],
            'scores': [0.9],
            'class_ids': [0]
        }
        
        result = node.update(
            node_id=1,
            connection_list=[('1:NodeType:JSON:Output', '1:ObjHeatmap:JSON:Input02')],
            node_image_dict={},
            node_result_dict={'1:NodeType': detection_data},
            node_audio_dict={}
        )
        
        assert result['image'] is None, "Should not generate output with only JSON input"
        print("✓ Test Case 3: JSON but no image - correctly returns None")
        
        # Test Case 4: Both image and JSON - SHOULD generate output
        result = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': test_image},
            node_result_dict={'2:JsonNode': detection_data},
            node_audio_dict={}
        )
        
        assert result['image'] is not None, "Should generate output with both inputs"
        assert result['image'].shape == (480, 640, 3), f"Expected shape (480, 640, 3), got {result['image'].shape}"
        print("✓ Test Case 4: Both image and JSON - correctly generates output")


def test_empty_json_with_image():
    """Test that no output is generated when JSON is empty even with image"""
    
    # Create node
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
        
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:, :] = [255, 0, 0]
        
        # Test with empty bboxes
        empty_detection_data = {
            'bboxes': [],
            'scores': []
        }
        
        result = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': test_image},
            node_result_dict={'2:JsonNode': empty_detection_data},
            node_audio_dict={}
        )
        
        # With empty detection data but both inputs present, it should still process
        # (apply decay and generate output)
        assert result['image'] is not None, "Should still generate output with empty detections but both inputs"
        print("✓ Test: Empty JSON with image - correctly generates output (decay applied)")


def test_accumulation_persists_with_inputs():
    """Test that heatmap accumulation works when both inputs are present"""
    
    # Create node
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
        
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:, :] = [100, 100, 100]
        
        detection_data = {
            'bboxes': [[100, 100, 200, 200]],
            'scores': [0.9],
            'class_ids': [0]
        }
        
        # First frame with detection
        result1 = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': test_image},
            node_result_dict={'2:JsonNode': detection_data},
            node_audio_dict={}
        )
        
        max_after_frame1 = node.heatmap_accum.max()
        assert max_after_frame1 > 0, "Heatmap should accumulate on first frame"
        
        # Second frame with same detection - should accumulate
        result2 = node.update(
            node_id=1,
            connection_list=[
                ('1:ImageNode:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:JsonNode:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:ImageNode': test_image},
            node_result_dict={'2:JsonNode': detection_data},
            node_audio_dict={}
        )
        
        max_after_frame2 = node.heatmap_accum.max()
        assert max_after_frame2 > max_after_frame1, "Heatmap should accumulate over multiple frames"
        print("✓ Test: Accumulation persists with both inputs present")


if __name__ == "__main__":
    print("="*60)
    print("Running ObjHeatmap Input Validation Tests")
    print("="*60)
    
    test_no_output_without_both_inputs()
    test_empty_json_with_image()
    test_accumulation_persists_with_inputs()
    
    print("\n" + "="*60)
    print("All input validation tests passed successfully!")
    print("="*60)
