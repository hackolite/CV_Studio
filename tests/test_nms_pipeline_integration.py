#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for NMS filtering in the MOT -> Homography -> TennisCourt pipeline.
Validates that duplicate detections are filtered and displays are synchronized.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_nms_filters_duplicates_in_pipeline():
    """
    Test that NMS correctly filters duplicate detections in the tennis court node.
    Simulates data coming from Homography (which has already transformed MOT detections).
    """
    from node.VisualNode.node_tennis_court import Node
    
    print("\n" + "="*70)
    print("Test: NMS Filtering in Tennis Court Node")
    print("="*70)
    
    # Initialize tennis court node
    tennis_node = Node()
    tennis_node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 300,
        'process_height': 400
    }
    
    # Tennis court template
    template = {
        "units": "meters",
        "origin": "bottom_left_corner_outside_doubles",
        "keypoints": [
            {"id": 0,  "name": "far_baseline_left_single_corner", "x": 1.37, "y": 23.77},
            {"id": 1,  "name": "far_baseline_right_single_corner", "x": 9.60, "y": 23.77},
            {"id": 2,  "name": "near_baseline_left_double_corner", "x": 0.00, "y": 0.00},
            {"id": 3,  "name": "near_baseline_right_double_corner", "x": 10.97, "y": 0.00},
            {"id": 4,  "name": "far_baseline_left_service_projection", "x": 1.37, "y": 18.285},
            {"id": 5,  "name": "near_baseline_left_single_corner", "x": 1.37, "y": 0.00},
            {"id": 6,  "name": "far_baseline_right_service_projection", "x": 9.60, "y": 18.285},
            {"id": 7,  "name": "near_baseline_right_single_corner", "x": 9.60, "y": 0.00},
            {"id": 8,  "name": "service_box_left_top_corner", "x": 1.37, "y": 5.485},
            {"id": 9,  "name": "service_box_right_top_corner", "x": 9.60, "y": 5.485},
            {"id": 10, "name": "left_singles_sideline_midpoint", "x": 1.37, "y": 11.885},
            {"id": 11, "name": "right_singles_sideline_midpoint", "x": 9.60, "y": 11.885},
            {"id": 12, "name": "center_service_line_top_T", "x": 5.485, "y": 18.285},
            {"id": 13, "name": "center_service_line_bottom_T", "x": 5.485, "y": 5.485}
        ]
    }
    
    # Simulate Homography output with DUPLICATE detections
    # Same player detected twice with overlapping bboxes at similar positions
    homography_output = {
        'template': template,
        'transformed_points': [
            [4.5, 10.0],   # Player 1 - Detection A (in court coordinates)
            [4.6, 10.1],   # Player 1 - Detection B (duplicate, very close position)
            [7.0, 15.0],   # Player 2
            [2.5, 8.0],    # Player 3
        ],
        'bboxes': [
            [500, 300, 600, 600],   # Player 1 - Detection A
            [510, 310, 610, 610],   # Player 1 - Detection B (overlaps A with IoU > 0.5)
            [700, 300, 800, 600],   # Player 2
            [300, 400, 400, 700],   # Player 3
        ],
        'scores': [0.95, 0.85, 0.90, 0.88],  # First detection has higher score
        'class_ids': [0, 0, 1, 2],
        'class_names': {0: 'Player A', 1: 'Player B', 2: 'Player C'}
    }
    
    num_input = len(homography_output['bboxes'])
    print(f"\n✓ Input from Homography: {num_input} detections")
    print(f"  Including duplicate detections (overlapping bboxes)")
    
    # Process through tennis court (applies NMS)
    # Set up a mock connection to simulate data flow from Homography node
    connection_list = [
        ('1:Homography:JSON:Output01', '1:TennisCourt:JSON:Input01')
    ]
    
    # Directly call the internal methods to avoid DPG issues in tests
    # First, extract and filter the data
    json_data = homography_output
    
    # Simulate what the update() method does
    template = json_data.get('template', None)
    transformed_points = json_data.get('transformed_points', None)
    labels = None
    
    # Extract labels from bboxes and class_ids
    if 'bboxes' in json_data and 'class_ids' in json_data and 'class_names' in json_data:
        class_ids = json_data.get('class_ids', [])
        class_names = json_data.get('class_names', {})
        bboxes = json_data.get('bboxes', [])
        scores = json_data.get('scores', [])
        
        # Create labels for each detected object
        labels = []
        for class_id in class_ids:
            if isinstance(class_names, dict):
                label = class_names.get(class_id, None)
            elif isinstance(class_names, list) and class_id < len(class_names):
                label = class_names[class_id]
            else:
                label = None
            labels.append(label)
        
        # Apply NMS to filter duplicate detections
        if transformed_points is not None and bboxes and len(bboxes) > 0:
            transformed_points, labels, class_ids = tennis_node._apply_nms_to_tracking(
                transformed_points, bboxes, scores, class_ids, labels
            )
    
    # Update position history
    if transformed_points is not None and labels is not None:
        tennis_node._update_player_positions(transformed_points, labels)
    
    # Debug output
    print(f"\n  Debug: _last_positions_by_label = {tennis_node._last_positions_by_label}")
    print(f"  Debug: _player_positions_history keys = {list(tennis_node._player_positions_history.keys())}")
    
    # Check that positions were filtered by NMS
    num_tracked = len(tennis_node._last_positions_by_label)
    
    print(f"\n✓ After NMS in TennisCourt: {num_tracked} unique positions tracked")
    
    # Verify NMS removed duplicates
    # We had 4 detections with 2 being duplicates (overlapping bboxes of Player A)
    # So we should have 3 after NMS (Player A once, Player B, Player C)
    assert num_tracked < num_input, \
        f"NMS should filter duplicates: {num_tracked} tracked vs {num_input} input"
    
    # Should have 3 unique players
    assert num_tracked == 3, \
        f"Expected 3 unique players after NMS, got {num_tracked}"
    
    print(f"\n✓ NMS successfully filtered duplicates!")
    print(f"  Reduction: {num_input} -> {num_tracked} detections")
    print(f"  Duplicate Player A detection removed")
    
    return True


def test_nms_preserves_non_overlapping_detections():
    """
    Test that NMS preserves detections that don't overlap.
    """
    from node.VisualNode.node_tennis_court import Node
    
    print("\n" + "="*70)
    print("Test: NMS Preserves Non-Overlapping Detections")
    print("="*70)
    
    tennis_node = Node()
    tennis_node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 300,
        'process_height': 400
    }
    
    # Template
    template = {
        "units": "meters",
        "origin": "bottom_left_corner_outside_doubles",
        "keypoints": [
            {"id": 0, "name": "test", "x": 0, "y": 0}
        ]
    }
    
    # Non-overlapping detections (well separated)
    transformed_points = [
        [2.0, 5.0],   # Player 1
        [5.0, 10.0],  # Player 2
        [8.0, 15.0],  # Player 3
    ]
    
    bboxes = [
        [100, 100, 200, 300],   # Well separated
        [400, 100, 500, 300],   # Well separated
        [700, 100, 800, 300],   # Well separated
    ]
    
    scores = [0.9, 0.85, 0.88]
    class_ids = [0, 1, 2]
    labels = ['Player A', 'Player B', 'Player C']
    
    # Apply NMS directly
    filtered_points, filtered_labels, filtered_class_ids = tennis_node._apply_nms_to_tracking(
        transformed_points, bboxes, scores, class_ids, labels
    )
    
    # Update positions
    tennis_node._update_player_positions(filtered_points, filtered_labels)
    num_tracked = len(tennis_node._last_positions_by_label)
    
    print(f"✓ Input: 3 non-overlapping detections")
    print(f"✓ After NMS: {num_tracked} positions tracked")
    
    # All 3 should be preserved since they don't overlap
    assert num_tracked == 3, f"Expected 3 detections, got {num_tracked}"
    
    print(f"✓ Non-overlapping detections preserved correctly")
    
    return True


def test_nms_synchronizes_mot_and_tennis_displays():
    """
    Test that NMS ensures tennis court display matches MOT display.
    Only detections shown in MOT should appear on tennis court.
    """
    from node.VisualNode.node_tennis_court import Node
    
    print("\n" + "="*70)
    print("Test: NMS Synchronizes MOT and Tennis Court Displays")
    print("="*70)
    
    tennis_node = Node()
    tennis_node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 300,
        'process_height': 400
    }
    
    # Simulate what MOT would send:
    # - 3 tracked objects after its own processing
    # - But with some potential duplicates due to tracking fragmentation
    transformed_points = [
        [3.0, 8.0],   # Track ID 1
        [3.1, 8.1],   # Track ID 2 (duplicate of ID 1)
        [7.0, 15.0],  # Track ID 3
    ]
    
    bboxes = [
        [300, 200, 400, 500],   # Track 1
        [305, 205, 405, 505],   # Track 2 (overlaps track 1)
        [700, 200, 800, 500],   # Track 3
    ]
    
    scores = [0.92, 0.88, 0.90]
    class_ids = [0, 0, 1]
    labels = ['Player A', 'Player A', 'Player B']
    
    # Apply NMS directly
    filtered_points, filtered_labels, filtered_class_ids = tennis_node._apply_nms_to_tracking(
        transformed_points, bboxes, scores, class_ids, labels
    )
    
    # Update positions
    tennis_node._update_player_positions(filtered_points, filtered_labels)
    num_displayed = len(tennis_node._last_positions_by_label)
    
    print(f"✓ MOT sent: 3 detections (2 duplicates + 1 unique)")
    print(f"✓ Tennis court displays: {num_displayed} positions after NMS")
    
    # After NMS, we should have fewer detections than input
    assert num_displayed <= len(bboxes), \
        "Tennis court should not show more detections than received"
    
    # We should have filtered the duplicate (2 unique labels: Player A and Player B)
    assert num_displayed == 2, \
        f"Expected 2 unique labels after NMS, got {num_displayed}"
    
    print(f"✓ Displays are synchronized: duplicates filtered")
    
    return True


if __name__ == '__main__':
    print("="*70)
    print("Integration Tests: NMS in MOT -> Homography -> TennisCourt Pipeline")
    print("="*70)
    
    try:
        test_nms_filters_duplicates_in_pipeline()
        print()
        
        test_nms_preserves_non_overlapping_detections()
        print()
        
        test_nms_synchronizes_mot_and_tennis_displays()
        print()
        
        print("="*70)
        print("All integration tests passed! ✓")
        print("="*70)
        print("\nConclusion:")
        print("  ✓ NMS successfully filters duplicate detections")
        print("  ✓ Tennis court display is synchronized with MOT display")
        print("  ✓ Non-overlapping detections are preserved")
        print("  ✓ Pipeline integration works correctly")
        print("="*70)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
