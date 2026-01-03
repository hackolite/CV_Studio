#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the Homography node label-based averaging functionality.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_averaging_by_label():
    """Test that homography correctly calculates averages by label"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False
    }
    
    # Simulate transformed points (in meters)
    transformed_points = np.array([
        [4.80, 20.55],  # player1 - position 1
        [4.80, 18.68],  # player1 - position 2
        [4.80, 17.89],  # player1 - position 3
        [4.78, 17.73],  # player1 - position 4
        [4.76, 17.73],  # player1 - position 5
    ])
    
    # All detections have the same label (player1)
    class_ids = [0, 0, 0, 0, 0]
    class_names = {0: 'player1'}
    
    # Calculate averages
    averages = node._calculate_averages_by_label(transformed_points, class_ids, class_names)
    
    print("✓ Homography averaging calculation works")
    print(f"  Number of unique labels: {len(averages)}")
    print(f"  Label 'player1' detected")
    
    # Verify we have the player1 label
    assert 'player1' in averages, "player1 label not found in averages"
    
    # Calculate expected average manually
    expected_avg_x = np.mean(transformed_points[:, 0])
    expected_avg_y = np.mean(transformed_points[:, 1])
    
    actual_avg = averages['player1']
    print(f"  Expected average: ({expected_avg_x:.2f}, {expected_avg_y:.2f})")
    print(f"  Actual average: ({actual_avg[0]:.2f}, {actual_avg[1]:.2f})")
    
    # Verify averages are correct
    assert abs(actual_avg[0] - expected_avg_x) < 0.01, "Average X coordinate incorrect"
    assert abs(actual_avg[1] - expected_avg_y) < 0.01, "Average Y coordinate incorrect"
    
    return True


def test_multiple_labels_averaging():
    """Test averaging with multiple different labels"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False
    }
    
    # Simulate transformed points with different labels
    transformed_points = np.array([
        [5.0, 10.0],  # person - position 1
        [3.0, 8.0],   # ball
        [5.5, 10.5],  # person - position 2
    ])
    
    class_ids = [0, 1, 0]
    class_names = {0: 'person', 1: 'ball'}
    
    # Calculate averages
    averages = node._calculate_averages_by_label(transformed_points, class_ids, class_names)
    
    print("✓ Multiple label averaging works")
    print(f"  Number of unique labels: {len(averages)}")
    
    # Verify we have both labels
    assert 'person' in averages, "person label not found"
    assert 'ball' in averages, "ball label not found"
    
    # Verify person average (2 positions)
    expected_person_x = (5.0 + 5.5) / 2
    expected_person_y = (10.0 + 10.5) / 2
    
    print(f"  Person average: ({averages['person'][0]:.2f}, {averages['person'][1]:.2f})")
    print(f"  Expected person average: ({expected_person_x:.2f}, {expected_person_y:.2f})")
    
    assert abs(averages['person'][0] - expected_person_x) < 0.01
    assert abs(averages['person'][1] - expected_person_y) < 0.01
    
    # Verify ball average (1 position)
    expected_ball_x = 3.0
    expected_ball_y = 8.0
    
    print(f"  Ball average: ({averages['ball'][0]:.2f}, {averages['ball'][1]:.2f})")
    print(f"  Expected ball average: ({expected_ball_x:.2f}, {expected_ball_y:.2f})")
    
    assert abs(averages['ball'][0] - expected_ball_x) < 0.01
    assert abs(averages['ball'][1] - expected_ball_y) < 0.01
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Homography Node - Label-based Averaging")
    print("=" * 70)
    
    try:
        test_averaging_by_label()
        print()
        
        test_multiple_labels_averaging()
        print()
        
        print("=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
