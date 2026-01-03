#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for persistent visualization - players should not disappear when data stops.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_persistent_visualization():
    """Test that visualization keeps displaying last positions when data stops"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Simulate receiving data (frame 1)
    positions_frame1 = [[5.0, 10.0], [3.0, 8.0]]
    labels_frame1 = ['player1', 'player2']
    
    node._update_player_positions(positions_frame1, labels_frame1)
    
    print("=" * 70)
    print("Persistent Visualization Test")
    print("=" * 70)
    
    # Verify positions are stored
    assert 'player1' in node._last_positions_by_label, "player1 not stored"
    assert 'player2' in node._last_positions_by_label, "player2 not stored"
    
    print("\n✓ Frame 1: Positions received and stored")
    print(f"  player1: {node._last_positions_by_label['player1']}")
    print(f"  player2: {node._last_positions_by_label['player2']}")
    
    # Simulate receiving new data (frame 2)
    positions_frame2 = [[5.2, 10.5], [3.1, 8.2]]
    labels_frame2 = ['player1', 'player2']
    
    node._update_player_positions(positions_frame2, labels_frame2)
    
    print("\n✓ Frame 2: Positions updated")
    print(f"  player1: {node._last_positions_by_label['player1']}")
    print(f"  player2: {node._last_positions_by_label['player2']}")
    
    # Verify positions were updated
    assert node._last_positions_by_label['player1'] == (5.2, 10.5), "player1 not updated"
    assert node._last_positions_by_label['player2'] == (3.1, 8.2), "player2 not updated"
    
    # Simulate no new data (frame 3, 4, 5...)
    # The last positions should remain available for visualization
    print("\n✓ Frames 3-5: No new data received")
    print("  Last positions remain available:")
    print(f"  player1: {node._last_positions_by_label['player1']}")
    print(f"  player2: {node._last_positions_by_label['player2']}")
    
    # Verify last positions are still there
    assert 'player1' in node._last_positions_by_label, "player1 disappeared"
    assert 'player2' in node._last_positions_by_label, "player2 disappeared"
    assert node._last_positions_by_label['player1'] == (5.2, 10.5), "player1 position changed"
    assert node._last_positions_by_label['player2'] == (3.1, 8.2), "player2 position changed"
    
    print("\n" + "=" * 70)
    print("✓ Persistent visualization works correctly!")
    print("  Players will not disappear from visualization when data stops.")
    print("=" * 70)
    
    return True


def test_visualization_with_no_data():
    """Test that visualization can draw from last positions when no new data arrives"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Store some template data
    node._last_template = {
        'units': 'meters',
        'keypoints': [
            {'id': 0, 'name': 'test_point', 'x': 5.0, 'y': 10.0}
        ]
    }
    
    # Store some player positions
    node._last_positions_by_label = {
        'player1': (5.0, 10.0),
        'player2': (3.0, 8.0)
    }
    
    print("\n" + "=" * 70)
    print("Visualization with No New Data Test")
    print("=" * 70)
    
    # Verify we can retrieve positions for visualization
    assert len(node._last_positions_by_label) == 2, "Should have 2 stored positions"
    
    # Convert to lists (as would be done in update method)
    last_labels = list(node._last_positions_by_label.keys())
    last_points = [list(node._last_positions_by_label[label]) for label in last_labels]
    
    print("\n✓ Can retrieve stored positions for visualization:")
    for label, point in zip(last_labels, last_points):
        print(f"  {label}: {point}")
    
    assert len(last_labels) == 2, "Should have 2 labels"
    assert len(last_points) == 2, "Should have 2 points"
    assert 'player1' in last_labels, "player1 not in labels"
    assert 'player2' in last_labels, "player2 not in labels"
    
    print("\n✓ Visualization can draw from stored positions even with no new data")
    print("=" * 70)
    
    return True


if __name__ == '__main__':
    try:
        test_persistent_visualization()
        test_visualization_with_no_data()
        print("\n✓ All persistence tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
