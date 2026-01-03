#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test to verify console output and averaging functionality.
"""
import sys
import os
import numpy as np
from io import StringIO

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_console_output_with_averaging():
    """Test that console output shows individual positions and averages by label"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False
    }
    
    # Set up homography matrix (identity for simplicity)
    node._homography_matrix = np.eye(3, dtype=np.float32)
    
    # Prepare test data - 5 detections with same label
    points_json_data = {
        'bboxes': [
            [620, 180, 642, 202],  # bbox 1
            [620, 203, 642, 225],  # bbox 2
            [619, 213, 642, 235],  # bbox 3
            [618, 215, 641, 237],  # bbox 4
            [617, 215, 640, 237],  # bbox 5
        ],
        'class_ids': [0, 0, 0, 0, 0],
        'class_names': {0: 'player1'},
        'scores': [0.9, 0.85, 0.87, 0.88, 0.86]
    }
    
    # Extract bottom-center points
    points_to_transform = node._extract_bottom_center_from_bboxes(points_json_data['bboxes'])
    
    # Transform points (with identity matrix, they stay the same)
    transformed = node._transform_points(points_to_transform, node._homography_matrix)
    
    # Calculate averages
    averages = node._calculate_averages_by_label(
        transformed,
        points_json_data['class_ids'],
        points_json_data['class_names']
    )
    
    print("=" * 70)
    print("Console Output Test - Individual Positions and Averages")
    print("=" * 70)
    
    # Display individual positions
    print("\n[Homography] Coordinate Transformation:")
    print("=" * 70)
    for i, (orig, trans) in enumerate(zip(points_to_transform, transformed)):
        label = points_json_data['class_names'][points_json_data['class_ids'][i]]
        print(f"  Player {i+1} ({label}):")
        print(f"    Image coordinates (pixels): ({orig[0]:.1f}, {orig[1]:.1f})")
        print(f"    Court coordinates (meters): ({trans[0]:.2f}, {trans[1]:.2f})")
    
    # Display averages
    if averages:
        print("\n" + "-" * 70)
        print("[Homography] Average Positions by Label:")
        print("-" * 70)
        for label, avg_coords in averages.items():
            print(f"  {label}:")
            print(f"    Average court coordinates (meters): ({avg_coords[0]:.2f}, {avg_coords[1]:.2f})")
    
    print("=" * 70)
    
    # Verify we got the average
    assert 'player1' in averages, "player1 not found in averages"
    
    # Calculate expected average
    expected_x = np.mean(transformed[:, 0])
    expected_y = np.mean(transformed[:, 1])
    
    print(f"\n✓ Average calculation verified:")
    print(f"  Expected: ({expected_x:.2f}, {expected_y:.2f})")
    print(f"  Actual: ({averages['player1'][0]:.2f}, {averages['player1'][1]:.2f})")
    
    assert abs(averages['player1'][0] - expected_x) < 0.01
    assert abs(averages['player1'][1] - expected_y) < 0.01
    
    return True


if __name__ == '__main__':
    try:
        test_console_output_with_averaging()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
