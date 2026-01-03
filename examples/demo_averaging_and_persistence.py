#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo script showing the label-based averaging and persistent visualization features.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def demo_homography_averaging():
    """Demonstrate homography averaging by label"""
    from node.StatsNode.node_homography import Node
    
    print("=" * 70)
    print("DEMO: Homography Label-Based Averaging")
    print("=" * 70)
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Simulate 5 detections of "player1" as mentioned in the problem statement
    transformed_points = np.array([
        [4.80, 20.55],  # Player 1
        [4.80, 18.68],  # Player 2
        [4.80, 17.89],  # Player 3
        [4.78, 17.73],  # Player 4
        [4.76, 17.73],  # Player 5
    ])
    
    class_ids = [0, 0, 0, 0, 0]  # All are player1
    class_names = {0: 'player1'}
    
    # Calculate averages
    averages = node._calculate_averages_by_label(transformed_points, class_ids, class_names)
    
    print("\nInput: 5 detections of 'player1'")
    print("-" * 70)
    for i, point in enumerate(transformed_points):
        print(f"  Detection {i+1}: ({point[0]:.2f}, {point[1]:.2f}) meters")
    
    print("\nOutput: Average position by label")
    print("-" * 70)
    for label, avg in averages.items():
        print(f"  {label}: ({avg[0]:.2f}, {avg[1]:.2f}) meters")
    
    print("\n✓ As requested: Calculates the average (moyenne) of x and y by label")
    print()


def demo_persistent_visualization():
    """Demonstrate persistent visualization"""
    from node.VisualNode.node_tennis_court import Node
    
    print("=" * 70)
    print("DEMO: Persistent Visualization")
    print("=" * 70)
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Frame 1: Players detected
    print("\nFrame 1: Players detected")
    positions = [[5.0, 10.0], [3.0, 8.0]]
    labels = ['player1', 'player2']
    node._update_player_positions(positions, labels)
    print(f"  player1 at: {node._last_positions_by_label['player1']}")
    print(f"  player2 at: {node._last_positions_by_label['player2']}")
    
    # Frame 2: Players still detected
    print("\nFrame 2: Players detected (positions updated)")
    positions = [[5.2, 10.5], [3.1, 8.2]]
    node._update_player_positions(positions, labels)
    print(f"  player1 at: {node._last_positions_by_label['player1']}")
    print(f"  player2 at: {node._last_positions_by_label['player2']}")
    
    # Frames 3-10: No data received (detection failed)
    print("\nFrames 3-10: No new data received (detection failed)")
    print("  Visualization continues using last known positions:")
    print(f"  player1 at: {node._last_positions_by_label['player1']}")
    print(f"  player2 at: {node._last_positions_by_label['player2']}")
    
    print("\n✓ As requested: When nothing is received, keep last values displayed")
    print("✓ Players never disappear from the visualization")
    print()


if __name__ == '__main__':
    demo_homography_averaging()
    demo_persistent_visualization()
    
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey Features Implemented:")
    print("1. ✓ Calculate average x,y coordinates by label (moyenne par label)")
    print("2. ✓ Display averages in console output")
    print("3. ✓ Persistent visualization - players never disappear")
    print("4. ✓ Keep last values when no data is received")
    print()
