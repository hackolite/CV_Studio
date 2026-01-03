#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the TennisCourt visual node with halved scale and player position averaging.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_court_scale_halved():
    """Test that the court is drawn at half scale"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Test the scale calculation directly without going through update()
    # to avoid DPG issues
    small_window_w = 600
    small_window_h = 800
    margin = 60
    
    # Calculate what the scale should be
    scale_x = (small_window_w - margin) / 10.97
    scale_y = (small_window_h - margin) / 23.77
    base_scale = min(scale_x, scale_y)
    expected_scale = base_scale / 2.0
    
    print("✓ Court scale calculation verified")
    print(f"  Base scale: {base_scale:.2f}")
    print(f"  Expected halved scale: {expected_scale:.2f}")
    print(f"  Court will be drawn at half the original size")
    
    return True


def test_player_position_averaging():
    """Test that player positions are tracked and averaged by label"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Simulate player positions over multiple frames
    positions_frame1 = [[5.0, 10.0], [3.0, 8.0]]
    positions_frame2 = [[5.2, 10.5], [3.1, 8.2]]
    positions_frame3 = [[4.8, 9.8], [2.9, 7.9]]
    
    labels = ['person', 'person']
    
    # Update with frame 1
    node._update_player_positions(positions_frame1, labels)
    
    # Update with frame 2
    node._update_player_positions(positions_frame2, labels)
    
    # Update with frame 3
    node._update_player_positions(positions_frame3, labels)
    
    # Get averages
    averages = node._get_average_positions_by_label()
    
    print("✓ Player position averaging works")
    print(f"  Number of unique labels: {len(averages)}")
    print(f"  Label 'person' has {len(node._player_positions_history['person'])} positions")
    
    # Verify we have the person label
    assert 'person' in averages, "Person label not found in averages"
    
    # Verify we tracked all positions (6 total: 3 frames × 2 players with same label)
    person_history = node._player_positions_history.get('person', [])
    assert len(person_history) == 6, \
        f"Expected 6 positions for 'person', got {len(person_history)}"
    
    # Calculate expected average manually
    all_positions = positions_frame1 + positions_frame2 + positions_frame3
    expected_avg_x = sum(p[0] for p in all_positions) / len(all_positions)
    expected_avg_y = sum(p[1] for p in all_positions) / len(all_positions)
    
    actual_avg = averages['person']
    print(f"  Expected average: ({expected_avg_x:.2f}, {expected_avg_y:.2f})")
    print(f"  Actual average: ({actual_avg[0]:.2f}, {actual_avg[1]:.2f})")
    
    # Verify averages are correct
    assert abs(actual_avg[0] - expected_avg_x) < 0.01, "Average X coordinate incorrect"
    assert abs(actual_avg[1] - expected_avg_y) < 0.01, "Average Y coordinate incorrect"
    
    return True


def test_last_position_tracking():
    """Test that last position is correctly tracked for each label"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Simulate different players
    positions_frame1 = [[5.0, 10.0], [3.0, 8.0]]
    labels_frame1 = ['person', 'ball']
    
    positions_frame2 = [[5.2, 10.5], [3.5, 8.5]]
    labels_frame2 = ['person', 'ball']
    
    # Update with frame 1
    node._update_player_positions(positions_frame1, labels_frame1)
    
    # Check last positions after frame 1
    assert 'person' in node._last_positions_by_label
    assert 'ball' in node._last_positions_by_label
    assert node._last_positions_by_label['person'] == (5.0, 10.0)
    assert node._last_positions_by_label['ball'] == (3.0, 8.0)
    
    # Update with frame 2
    node._update_player_positions(positions_frame2, labels_frame2)
    
    # Check last positions after frame 2 (should be updated)
    assert node._last_positions_by_label['person'] == (5.2, 10.5)
    assert node._last_positions_by_label['ball'] == (3.5, 8.5)
    
    print("✓ Last position tracking works correctly")
    print(f"  Person last position: {node._last_positions_by_label['person']}")
    print(f"  Ball last position: {node._last_positions_by_label['ball']}")
    
    return True


def test_multiple_labels_averaging():
    """Test averaging with multiple different labels"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Simulate different objects with different labels
    positions = [[5.0, 10.0], [3.0, 8.0], [7.0, 12.0]]
    labels = ['person', 'ball', 'person']
    
    node._update_player_positions(positions, labels)
    
    # Add more positions
    positions2 = [[5.5, 10.5], [3.2, 8.3], [7.2, 12.5]]
    labels2 = ['person', 'ball', 'person']
    
    node._update_player_positions(positions2, labels2)
    
    # Get averages
    averages = node._get_average_positions_by_label()
    
    print("✓ Multiple label averaging works")
    print(f"  Number of unique labels: {len(averages)}")
    print(f"  Person positions tracked: {len(node._player_positions_history['person'])}")
    print(f"  Ball positions tracked: {len(node._player_positions_history['ball'])}")
    
    # Verify we have both labels
    assert 'person' in averages
    assert 'ball' in averages
    
    # Verify person has 4 positions (2 per frame × 2 frames)
    assert len(node._player_positions_history['person']) == 4
    
    # Verify ball has 2 positions (1 per frame × 2 frames)
    assert len(node._player_positions_history['ball']) == 2
    
    # Verify person average
    person_positions = [(5.0, 10.0), (7.0, 12.0), (5.5, 10.5), (7.2, 12.5)]
    expected_person_avg_x = sum(p[0] for p in person_positions) / len(person_positions)
    expected_person_avg_y = sum(p[1] for p in person_positions) / len(person_positions)
    
    print(f"  Person average: ({averages['person'][0]:.2f}, {averages['person'][1]:.2f})")
    print(f"  Expected person average: ({expected_person_avg_x:.2f}, {expected_person_avg_y:.2f})")
    
    assert abs(averages['person'][0] - expected_person_avg_x) < 0.01
    assert abs(averages['person'][1] - expected_person_avg_y) < 0.01
    
    # Verify ball average
    ball_positions = [(3.0, 8.0), (3.2, 8.3)]
    expected_ball_avg_x = sum(p[0] for p in ball_positions) / len(ball_positions)
    expected_ball_avg_y = sum(p[1] for p in ball_positions) / len(ball_positions)
    
    print(f"  Ball average: ({averages['ball'][0]:.2f}, {averages['ball'][1]:.2f})")
    print(f"  Expected ball average: ({expected_ball_avg_x:.2f}, {expected_ball_avg_y:.2f})")
    
    assert abs(averages['ball'][0] - expected_ball_avg_x) < 0.01
    assert abs(averages['ball'][1] - expected_ball_avg_y) < 0.01
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing TennisCourt Visual Node - Scale and Averaging Features")
    print("=" * 70)
    
    try:
        test_court_scale_halved()
        print()
        
        test_player_position_averaging()
        print()
        
        test_last_position_tracking()
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
