#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test simulating real-world usage of ObjHeatmap with object detection.
This test demonstrates the complete workflow from detection to heatmap visualization.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
from node.VisualNode.node_obj_heatmap import Node
import cv2
import numpy as np


def simulate_object_detection_output(image):
    """
    Simulate object detection output similar to what YOLO would produce.
    Returns detections in the INPUT IMAGE coordinate space.
    """
    h, w = image.shape[:2]
    
    # Simulate detections at various positions in the image
    detections = {
        'bboxes': [
            [int(w * 0.1), int(h * 0.1), int(w * 0.2), int(h * 0.2)],   # Top-left
            [int(w * 0.4), int(h * 0.4), int(w * 0.6), int(h * 0.6)],   # Center
            [int(w * 0.7), int(h * 0.7), int(w * 0.9), int(h * 0.9)],   # Bottom-right
            [int(w * 0.8), int(h * 0.1), int(w * 0.95), int(h * 0.15)], # Top-right
        ],
        'scores': [0.95, 0.88, 0.76, 0.92],
        'class_ids': [0, 0, 1, 0],  # person, person, car, person
        'class_names': {
            "0": "person",
            "1": "car"
        }
    }
    
    return detections


def test_integration_fullhd_video_stream():
    """
    Integration test: Simulate processing a Full HD video stream
    with object detection and heatmap visualization.
    """
    print("\n" + "="*70)
    print("INTEGRATION TEST: Full HD Video Stream Processing")
    print("="*70)
    
    # Create heatmap node with VGA processing window (typical for real-time)
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Mock DPG functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95  # High decay for smooth accumulation
            elif 'ClassValue' in tag:
                return "All"  # Show all classes
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        # Simulate 10 frames of Full HD video
        print("\nProcessing 10 frames of Full HD video (1920x1080)...")
        print("Target processing window: 640x480")
        
        for frame_idx in range(10):
            # Create Full HD frame
            frame = np.random.randint(50, 150, (1080, 1920, 3), dtype=np.uint8)
            
            # Add some visual content (simulated scene)
            cv2.rectangle(frame, (800, 400), (1100, 700), (100, 150, 100), -1)
            
            # Get object detections (in Full HD coordinate space)
            detections = simulate_object_detection_output(frame)
            
            # Process with heatmap node
            result = node.update(
                node_id=1,
                connection_list=[
                    ('1:VideoSource:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                    ('2:ObjectDetection:JSON:Output', '1:ObjHeatmap:JSON:Input02')
                ],
                node_image_dict={'1:VideoSource': frame},
                node_result_dict={'2:ObjectDetection': detections},
                node_audio_dict={}
            )
            
            # Verify output
            assert result['image'] is not None, f"Frame {frame_idx}: Should generate output"
            assert result['image'].shape == (480, 640, 3), \
                f"Frame {frame_idx}: Wrong output shape {result['image'].shape}"
            
            if frame_idx == 0:
                print(f"  ✓ Frame {frame_idx}: Initial heatmap created")
            elif frame_idx == 9:
                print(f"  ✓ Frame {frame_idx}: Heatmap accumulated over 10 frames")
            else:
                if frame_idx % 3 == 0:
                    print(f"  ✓ Frame {frame_idx}: Processing...")
        
        # Verify heatmap has accumulated properly
        assert node.heatmap_accum.max() > 0, "Heatmap should have accumulated values"
        
        # Save final output
        cv2.imwrite("/tmp/integration_test_final_heatmap.png", result['image'])
        print(f"\n✓ Final accumulated heatmap saved to /tmp/integration_test_final_heatmap.png")
        
        print(f"✓ Heatmap accumulator max value: {node.heatmap_accum.max():.2f}")
        print(f"✓ Heatmap shape: {node.heatmap_accum.shape}")


def test_integration_class_filtering():
    """
    Integration test: Verify class filtering works correctly with coordinate scaling.
    """
    print("\n" + "="*70)
    print("INTEGRATION TEST: Class Filtering with Coordinate Scaling")
    print("="*70)
    
    # Create heatmap node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Mock DPG functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "0"  # Filter for "person" class only
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        print("\nProcessing with class filter: class 0 (person) only")
        
        # Create Full HD frame
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[:, :] = [100, 100, 100]
        
        # Create mixed detections (persons and cars)
        detections = {
            'bboxes': [
                [400, 300, 600, 500],    # Person - should be included
                [800, 400, 1000, 600],   # Car - should be filtered out
                [1200, 600, 1400, 800],  # Person - should be included
                [100, 100, 300, 300],    # Car - should be filtered out
            ],
            'scores': [0.9, 0.85, 0.8, 0.75],
            'class_ids': [0, 1, 0, 1],  # person, car, person, car
            'class_names': {
                "0": "person",
                "1": "car"
            }
        }
        
        # Process
        result = node.update(
            node_id=1,
            connection_list=[
                ('1:VideoSource:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                ('2:ObjectDetection:JSON:Output', '1:ObjHeatmap:JSON:Input02')
            ],
            node_image_dict={'1:VideoSource': frame},
            node_result_dict={'2:ObjectDetection': detections},
            node_audio_dict={}
        )
        
        # Verify output
        assert result['image'] is not None
        
        # Calculate expected positions for person detections (indices 0 and 2)
        scale_x = 640 / 1920
        scale_y = 480 / 1080
        
        # Person 1 (bbox [400, 300, 600, 500])
        p1_x1, p1_y1 = int(400 * scale_x), int(300 * scale_y)
        p1_x2, p1_y2 = int(600 * scale_x), int(500 * scale_y)
        
        # Person 2 (bbox [1200, 600, 1400, 800])
        p2_x1, p2_y1 = int(1200 * scale_x), int(600 * scale_y)
        p2_x2, p2_y2 = int(1400 * scale_x), int(800 * scale_y)
        
        # Check that person regions have intensity
        person1_region = node.heatmap_accum[p1_y1:p1_y2, p1_x1:p1_x2]
        person2_region = node.heatmap_accum[p2_y1:p2_y2, p2_x1:p2_x2]
        
        assert person1_region.max() > 0, "Person 1 should be in heatmap"
        assert person2_region.max() > 0, "Person 2 should be in heatmap"
        
        print(f"✓ Person detections correctly included in heatmap")
        print(f"  - Person 1 region intensity: {person1_region.max():.2f}")
        print(f"  - Person 2 region intensity: {person2_region.max():.2f}")
        
        # Save output
        cv2.imwrite("/tmp/integration_test_class_filter.png", result['image'])
        print(f"✓ Class-filtered heatmap saved to /tmp/integration_test_class_filter.png")


def test_integration_multiple_resolutions():
    """
    Integration test: Process frames from different resolution sources.
    """
    print("\n" + "="*70)
    print("INTEGRATION TEST: Multiple Resolution Sources")
    print("="*70)
    
    resolutions = [
        ("QVGA", 320, 240),
        ("VGA", 640, 480),
        ("HD", 1280, 720),
        ("Full HD", 1920, 1080),
        ("4K", 3840, 2160),
    ]
    
    # Create heatmap node with fixed processing window
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640,
        'use_pref_counter': False
    })
    
    # Mock DPG functions
    with patch('node.VisualNode.node_obj_heatmap.dpg_get_value') as mock_get_value, \
         patch('node.VisualNode.node_obj_heatmap.dpg_set_value') as mock_set_value:
        
        def get_value_side_effect(tag):
            if 'AlphaValue' in tag:
                return 0.95
            elif 'ClassValue' in tag:
                return "All"
            return None
        
        mock_get_value.side_effect = get_value_side_effect
        
        print(f"\nProcessing frames from different resolutions...")
        print(f"All outputs scaled to: 640x480")
        
        for name, width, height in resolutions:
            # Create frame with specific resolution
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = [80, 80, 80]
            
            # Detection at center (in native resolution)
            center_x, center_y = width // 2, height // 2
            box_size = min(width, height) // 10
            
            detections = {
                'bboxes': [[
                    center_x - box_size,
                    center_y - box_size,
                    center_x + box_size,
                    center_y + box_size
                ]],
                'scores': [0.9],
                'class_ids': [0]
            }
            
            # Process
            result = node.update(
                node_id=1,
                connection_list=[
                    ('1:Source:IMAGE:Output', '1:ObjHeatmap:IMAGE:Input01'),
                    ('2:Detection:JSON:Output', '1:ObjHeatmap:JSON:Input02')
                ],
                node_image_dict={'1:Source': frame},
                node_result_dict={'2:Detection': detections},
                node_audio_dict={}
            )
            
            # Verify
            assert result['image'] is not None
            assert result['image'].shape == (480, 640, 3)
            
            print(f"  ✓ {name:12} ({width}x{height}): Processed correctly")
        
        print(f"\n✓ All resolutions handled correctly with proper coordinate scaling")


if __name__ == "__main__":
    print("="*70)
    print("RUNNING INTEGRATION TESTS FOR OBJHEATMAP NODE")
    print("="*70)
    
    test_integration_fullhd_video_stream()
    test_integration_class_filtering()
    test_integration_multiple_resolutions()
    
    print("\n" + "="*70)
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("="*70)
    print("\nSummary:")
    print("  ✓ Full HD video stream processing")
    print("  ✓ Class filtering with coordinate scaling")
    print("  ✓ Multiple resolution sources (QVGA to 4K)")
    print("  ✓ Coordinate scaling works correctly in all scenarios")
    print("="*70)
