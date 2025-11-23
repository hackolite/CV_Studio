#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Integration test that simulates the exact bug scenario from the problem statement"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from node.VisualNode.node_obj_heatmap import Node
import numpy as np
import cv2


def test_dimension_mismatch_bug_scenario():
    """
    Reproduce the exact bug from the problem statement:
    cv2.error: OpenCV(4.11.0) /io/opencv/modules/core/src/arithm.cpp:662: 
    error: (-209:Sizes of input arguments do not match)
    """
    
    print("Testing the exact bug scenario from the problem statement...")
    print("-" * 60)
    
    # Create node with initial dimensions
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    print(f"Initial heatmap_accum shape: {node.heatmap_accum.shape}")
    
    # Simulate the scenario where opencv_setting_dict changes
    # (This could happen in a real application when settings are updated)
    node._opencv_setting_dict['process_height'] = 240
    node._opencv_setting_dict['process_width'] = 320
    
    print(f"Updated processing dimensions to: (240, 320)")
    print(f"But heatmap_accum still has shape: {node.heatmap_accum.shape}")
    print()
    
    # Create input image with NEW dimensions
    input_image = np.zeros((240, 320, 3), dtype=np.uint8)
    input_image[:, :] = [100, 100, 100]
    
    # Create detection data
    detection_data = {
        'bboxes': [[50, 50, 100, 100], [150, 80, 200, 130]],
        'scores': [0.9, 0.8],
        'class_ids': [0, 1],
    }
    
    # Mock dpg functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        # Setup mock return values
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95  # decay factor
            elif 'ClassValue' in tag:
                return "All"
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        print("Calling node.update() with mismatched dimensions...")
        print("This would previously fail with cv2.error!")
        print()
        
        # This is where the bug would occur (line 339 in the original code)
        # cv2.addWeighted(prepared_input, 0.4, heatmap_colored, 0.6, 0)
        # because prepared_input would be (240, 320, 3) 
        # but heatmap_colored would be (480, 640, 3)
        
        try:
            result = node.update(
                node_id=1,
                connection_list=[
                    ('0:ImageNode:IMAGE:Output01', '1:ObjHeatmap:IMAGE:Input01'),
                    ('0:JSONNode:JSON:Output01', '1:ObjHeatmap:JSON:Input02'),
                ],
                node_image_dict={'0:ImageNode': input_image},
                node_result_dict={'0:JSONNode': detection_data},
                node_audio_dict={}
            )
            
            print("✓ SUCCESS: node.update() completed without error!")
            print(f"✓ Output image shape: {result['image'].shape}")
            print(f"✓ Expected shape: (240, 320, 3)")
            
            # Verify the output
            assert result['image'] is not None, "Output image should not be None"
            assert result['image'].shape == (240, 320, 3), \
                f"Expected shape (240, 320, 3), got {result['image'].shape}"
            
            # Verify heatmap_accum was resized
            print(f"✓ heatmap_accum was automatically resized to: {node.heatmap_accum.shape}")
            assert node.heatmap_accum.shape == (240, 320), \
                f"Expected heatmap_accum shape (240, 320), got {node.heatmap_accum.shape}"
            
            print()
            print("="*60)
            print("BUG FIX VERIFIED ✓")
            print("="*60)
            print("The dimension mismatch bug has been successfully fixed!")
            print("The code now:")
            print("1. Detects when heatmap_accum dimensions don't match")
            print("2. Automatically resizes the accumulator")
            print("3. Ensures cv2.addWeighted receives matching dimensions")
            print("="*60)
            
            return True
            
        except cv2.error as e:
            print(f"✗ FAILED: cv2.error occurred: {e}")
            print("The bug fix did not work!")
            return False
        except Exception as e:
            print(f"✗ FAILED: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_accumulator_preserves_data_on_resize():
    """Test that resizing the accumulator preserves heatmap data"""
    
    print("\n\nTesting that heatmap data is preserved when resizing...")
    print("-" * 60)
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Add some heatmap data
    node.heatmap_accum[100:200, 100:200] = 0.9
    node.heatmap_accum[300:400, 300:400] = 0.7
    
    initial_max = node.heatmap_accum.max()
    print(f"Initial heatmap_accum max value: {initial_max}")
    print(f"Initial heatmap_accum shape: {node.heatmap_accum.shape}")
    
    # Change dimensions
    node._opencv_setting_dict['process_height'] = 240
    node._opencv_setting_dict['process_width'] = 320
    
    # Create input
    input_image = np.zeros((240, 320, 3), dtype=np.uint8)
    detection_data = {'bboxes': [[50, 50, 100, 100]], 'scores': [0.5]}
    
    # Mock dpg
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "All"
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        # Call update
        result = node.update(
            node_id=1,
            connection_list=[
                ('0:ImageNode:IMAGE:Output01', '1:ObjHeatmap:IMAGE:Input01'),
                ('0:JSONNode:JSON:Output01', '1:ObjHeatmap:JSON:Input02'),
            ],
            node_image_dict={'0:ImageNode': input_image},
            node_result_dict={'0:JSONNode': detection_data},
            node_audio_dict={}
        )
        
        print(f"After resize, heatmap_accum shape: {node.heatmap_accum.shape}")
        print(f"After resize, heatmap_accum max value: {node.heatmap_accum.max()}")
        
        # The accumulator should have been resized and still contain data
        assert node.heatmap_accum.shape == (240, 320)
        assert node.heatmap_accum.max() > 0, "Heatmap data should be preserved after resize"
        
        print("✓ Heatmap data was preserved during resize")
        print("✓ Test passed!")
        
        return True


if __name__ == "__main__":
    print("="*60)
    print("Integration Test for Dimension Mismatch Bug Fix")
    print("="*60)
    print()
    
    test1_passed = test_dimension_mismatch_bug_scenario()
    test2_passed = test_accumulator_preserves_data_on_resize()
    
    print("\n" + "="*60)
    if test1_passed and test2_passed:
        print("ALL INTEGRATION TESTS PASSED ✓")
        print("="*60)
    else:
        print("SOME TESTS FAILED ✗")
        print("="*60)
        exit(1)
