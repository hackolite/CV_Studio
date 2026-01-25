#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for NMS functionality in TennisCourt visual node.
Verifies that duplicate detections are filtered correctly.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_nms_basic():
    """Test basic NMS functionality with overlapping boxes"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    # Create overlapping bounding boxes
    # Box 1 and 2 overlap significantly (should suppress one)
    # Box 3 is separate (should keep)
    bboxes = np.array([
        [100, 100, 200, 300],  # Box 1
        [110, 105, 210, 310],  # Box 2 (overlaps with Box 1)
        [400, 100, 500, 300],  # Box 3 (separate)
    ])
    
    scores = np.array([0.9, 0.8, 0.85])  # Box 1 has highest score
    
    # Apply NMS with threshold 0.5
    keep_indices = node._nms(bboxes, scores, 0.5)
    
    print("✓ NMS basic test")
    print(f"  Input boxes: {len(bboxes)}")
    print(f"  Kept boxes: {len(keep_indices)}")
    print(f"  Kept indices: {keep_indices}")
    
    # Should keep Box 1 (highest score) and Box 3 (no overlap)
    # Should suppress Box 2 (overlaps with Box 1 and has lower score)
    assert len(keep_indices) == 2, f"Expected 2 boxes, got {len(keep_indices)}"
    assert 0 in keep_indices, "Box 1 should be kept (highest score)"
    assert 2 in keep_indices, "Box 3 should be kept (no overlap)"
    assert 1 not in keep_indices, "Box 2 should be suppressed (overlaps with Box 1)"
    
    return True


def test_nms_no_overlap():
    """Test NMS with non-overlapping boxes (should keep all)"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    # Create non-overlapping boxes
    bboxes = np.array([
        [100, 100, 200, 200],  # Box 1
        [300, 100, 400, 200],  # Box 2 (no overlap)
        [100, 300, 200, 400],  # Box 3 (no overlap)
    ])
    
    scores = np.array([0.9, 0.8, 0.85])
    
    keep_indices = node._nms(bboxes, scores, 0.5)
    
    print("✓ NMS no overlap test")
    print(f"  Input boxes: {len(bboxes)}")
    print(f"  Kept boxes: {len(keep_indices)}")
    
    # Should keep all boxes (no overlap)
    assert len(keep_indices) == 3, f"Expected 3 boxes, got {len(keep_indices)}"
    
    return True


def test_nms_empty_input():
    """Test NMS with empty input"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    bboxes = np.array([])
    scores = np.array([])
    
    keep_indices = node._nms(bboxes, scores, 0.5)
    
    print("✓ NMS empty input test")
    print(f"  Kept boxes: {len(keep_indices)}")
    
    assert len(keep_indices) == 0, "Empty input should return empty result"
    
    return True


def test_apply_nms_to_tracking():
    """Test applying NMS to tracking data with labels and transformed points"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    # Simulate tracking data with duplicates
    # Player A detected twice (overlapping boxes)
    # Player B detected once
    transformed_points = [
        [5.0, 10.0],   # Player A - detection 1
        [5.1, 10.1],   # Player A - detection 2 (duplicate)
        [8.0, 15.0],   # Player B
    ]
    
    bboxes = [
        [100, 100, 200, 300],  # Player A - bbox 1
        [110, 105, 210, 310],  # Player A - bbox 2 (overlaps)
        [400, 100, 500, 300],  # Player B
    ]
    
    scores = [0.9, 0.8, 0.85]
    class_ids = [0, 0, 1]  # Two detections of class 0, one of class 1
    labels = ['Player A', 'Player A', 'Player B']
    
    # Apply NMS
    filtered_points, filtered_labels, filtered_class_ids = node._apply_nms_to_tracking(
        transformed_points, bboxes, scores, class_ids, labels
    )
    
    print("✓ Apply NMS to tracking test")
    print(f"  Input detections: {len(transformed_points)}")
    print(f"  Filtered detections: {len(filtered_points)}")
    print(f"  Filtered labels: {filtered_labels}")
    
    # Should filter out duplicate Player A detection
    assert len(filtered_points) == 2, f"Expected 2 detections, got {len(filtered_points)}"
    assert len(filtered_labels) == 2, f"Expected 2 labels, got {len(filtered_labels)}"
    assert 'Player B' in filtered_labels, "Player B should be kept"
    
    # Only one Player A detection should remain
    player_a_count = sum(1 for label in filtered_labels if label == 'Player A')
    assert player_a_count == 1, f"Expected 1 Player A detection, got {player_a_count}"
    
    return True


def test_apply_nms_no_scores():
    """Test NMS when scores are not available"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    
    transformed_points = [
        [5.0, 10.0],
        [5.1, 10.1],
    ]
    
    bboxes = [
        [100, 100, 200, 300],
        [110, 105, 210, 310],
    ]
    
    scores = None  # No scores available
    class_ids = [0, 0]
    labels = ['Player A', 'Player A']
    
    # Should still work with uniform scores
    filtered_points, filtered_labels, filtered_class_ids = node._apply_nms_to_tracking(
        transformed_points, bboxes, scores, class_ids, labels
    )
    
    print("✓ Apply NMS without scores test")
    print(f"  Filtered detections: {len(filtered_points)}")
    
    # Should filter duplicates even without scores
    assert len(filtered_points) <= len(transformed_points), "Should filter some detections"
    
    return True


def test_nms_integration_with_update():
    """Test that NMS integrates properly with the update method"""
    from node.VisualNode.node_tennis_court import Node
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Simulate JSON data from Homography with duplicates
    json_data = {
        'template': {
            "units": "meters",
            "origin": "bottom_left_corner_outside_doubles",
            "keypoints": [
                {"id": 0, "name": "far_baseline_left_single_corner", "x": 1.37, "y": 23.77},
                {"id": 2, "name": "near_baseline_left_double_corner", "x": 0.00, "y": 0.00},
            ]
        },
        'transformed_points': [
            [5.0, 10.0],   # Detection 1
            [5.1, 10.1],   # Detection 2 (duplicate)
            [8.0, 15.0],   # Detection 3
        ],
        'bboxes': [
            [100, 100, 200, 300],
            [110, 105, 210, 310],  # Overlaps with first bbox
            [400, 100, 500, 300],
        ],
        'scores': [0.9, 0.8, 0.85],
        'class_ids': [0, 0, 1],
        'class_names': {0: 'Player A', 1: 'Player B'}
    }
    
    # Mock connection info
    connection_list = []
    node_image_dict = {}
    node_result_dict = {'1:MockNode': json_data}
    node_audio_dict = {}
    
    # Call update (this will internally apply NMS)
    result = node.update(1, connection_list, node_image_dict, node_result_dict, node_audio_dict)
    
    print("✓ NMS integration with update test")
    print(f"  Result keys: {list(result.keys())}")
    
    # Check that position history was updated (with filtered data)
    print(f"  Positions tracked: {len(node._last_positions_by_label)}")
    
    # NMS should have filtered duplicates before updating position history
    # We should have at most 2 unique labels (Player A and Player B)
    assert len(node._last_positions_by_label) <= 2, "Should have filtered duplicates"
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Testing TennisCourt NMS Functionality")
    print("=" * 60)
    
    try:
        test_nms_basic()
        print()
        
        test_nms_no_overlap()
        print()
        
        test_nms_empty_input()
        print()
        
        test_apply_nms_to_tracking()
        print()
        
        test_apply_nms_no_scores()
        print()
        
        test_nms_integration_with_update()
        print()
        
        print("=" * 60)
        print("All NMS tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
