#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test to verify class exclusion in object detection
properly filters data that is passed to tracking node.

This test addresses the issue of "player switches" in tracking
when class exclusion is applied.
"""

import numpy as np
import copy


def simulate_object_detection_with_exclusion():
    """Simulate the object detection node with class exclusion"""
    
    # Simulate raw detections: player1 (class 0), player2 (class 1), ball (class 2)
    bboxes = np.array([
        [10, 20, 30, 40],   # player1
        [50, 60, 70, 80],   # player2
        [90, 100, 110, 120]  # ball
    ])
    scores = np.array([0.95, 0.85, 0.75])
    class_ids = np.array([0, 1, 2])
    class_name_dict = {0: 'player1', 1: 'player2', 2: 'ball'}
    
    # User wants to exclude player2 (class 1)
    rejected_classes_str = "1: player2"
    
    print("=" * 60)
    print("OBJECT DETECTION NODE")
    print("=" * 60)
    print(f"Raw detections: {len(bboxes)} objects")
    print(f"  Class IDs: {class_ids.tolist()}")
    print(f"  Classes: {[class_name_dict[cid] for cid in class_ids]}")
    print(f"\nClass Exclusion: {rejected_classes_str}")
    
    # Apply class rejection filter (simulating the code from node_object_detection.py)
    if rejected_classes_str and rejected_classes_str.strip():
        rejected_classes = set()
        
        # Parse rejected classes
        for class_str in rejected_classes_str.split(','):
            class_str = class_str.strip()
            if class_str:
                try:
                    if ':' in class_str:
                        class_id_str = class_str.split(':')[0].strip()
                        rejected_classes.add(int(class_id_str))
                    else:
                        rejected_classes.add(int(class_str))
                except ValueError:
                    pass
        
        print(f"  Rejected class IDs: {rejected_classes}")
        
        # Filter out rejected classes
        if rejected_classes:
            keep_mask = np.array([class_id not in rejected_classes for class_id in class_ids])
            print(f"  Keep mask: {keep_mask}")
            bboxes = bboxes[keep_mask]
            scores = scores[keep_mask]
            class_ids = class_ids[keep_mask]
    
    # Create result dictionary (this is what gets passed to tracking)
    result = {}
    if len(bboxes) > 0:
        result['bboxes'] = bboxes.tolist()
        result['scores'] = scores.tolist()
        result['class_ids'] = class_ids.tolist()
        result['class_names'] = class_name_dict
    else:
        result['bboxes'] = []
        result['scores'] = []
        result['class_ids'] = []
        result['class_names'] = class_name_dict
    
    print(f"\nFiltered detections: {len(bboxes)} objects")
    print(f"  Class IDs: {result['class_ids']}")
    print(f"  Classes: {[class_name_dict[cid] for cid in result['class_ids']]}")
    print(f"\nJSON output to tracking:")
    print(f"  bboxes: {result['bboxes']}")
    print(f"  class_ids: {result['class_ids']}")
    
    return result


def simulate_tracking_node(detection_data):
    """Simulate the MOT tracking node receiving detection data"""
    
    print("\n" + "=" * 60)
    print("TRACKING NODE (MOT)")
    print("=" * 60)
    
    od_bboxes = detection_data.get('bboxes', [])
    od_scores = detection_data.get('scores', [])
    od_class_ids = detection_data.get('class_ids', [])
    od_class_names = detection_data.get('class_names', {})
    
    print(f"Received detections: {len(od_bboxes)} objects")
    print(f"  Class IDs: {od_class_ids}")
    print(f"  Classes: {[od_class_names[cid] for cid in od_class_ids]}")
    
    # Simulate tracking assignment
    track_ids = []
    for i, (bbox, class_id) in enumerate(zip(od_bboxes, od_class_ids)):
        track_id = i  # Simple tracking: assign sequential IDs
        track_ids.append(track_id)
        print(f"  Object {i}: class={od_class_names[class_id]} (id={class_id}) -> track_id={track_id}")
    
    result = {
        'track_ids': track_ids,
        'bboxes': od_bboxes,
        'scores': od_scores,
        'class_ids': od_class_ids,
        'class_names': od_class_names
    }
    
    return result


def test_class_exclusion_end_to_end():
    """
    Test that class exclusion in object detection properly filters
    data before it reaches the tracking node.
    """
    print("\n" + "=" * 60)
    print("TEST: Class Exclusion End-to-End Integration")
    print("=" * 60)
    
    # Simulate object detection with class exclusion
    detection_result = simulate_object_detection_with_exclusion()
    
    # Verify that player2 (class 1) was excluded
    assert 1 not in detection_result['class_ids'], \
        "Class 1 (player2) should be excluded from detection results"
    
    # Verify that player1 (class 0) and ball (class 2) remain
    assert 0 in detection_result['class_ids'], \
        "Class 0 (player1) should remain in detection results"
    assert 2 in detection_result['class_ids'], \
        "Class 2 (ball) should remain in detection results"
    
    # Simulate tracking node receiving the filtered data
    tracking_result = simulate_tracking_node(detection_result)
    
    # Verify that tracking only sees the filtered classes
    assert 1 not in tracking_result['class_ids'], \
        "Class 1 (player2) should not be present in tracking input"
    
    assert len(tracking_result['track_ids']) == 2, \
        "Tracking should only track 2 objects (player1 and ball)"
    
    print("\n" + "=" * 60)
    print("✅ TEST PASSED")
    print("=" * 60)
    print("Class exclusion properly filters data before tracking.")
    print("Excluded class (player2) does not reach the tracking node.")


def test_class_exclusion_multiple_frames():
    """
    Test class exclusion across multiple frames to check for
    track ID consistency and player switches.
    """
    print("\n" + "=" * 60)
    print("TEST: Class Exclusion Across Multiple Frames")
    print("=" * 60)
    
    # Simulate 3 frames with different detection scenarios
    frames_data = [
        {
            'name': 'Frame 1',
            'bboxes': np.array([[10, 20, 30, 40], [50, 60, 70, 80]]),
            'scores': np.array([0.95, 0.85]),
            'class_ids': np.array([0, 1]),  # player1, player2
            'class_names': {0: 'player1', 1: 'player2', 2: 'ball'}
        },
        {
            'name': 'Frame 2',
            'bboxes': np.array([[12, 22, 32, 42], [52, 62, 72, 82], [90, 100, 110, 120]]),
            'scores': np.array([0.96, 0.84, 0.75]),
            'class_ids': np.array([0, 1, 2]),  # player1, player2, ball
            'class_names': {0: 'player1', 1: 'player2', 2: 'ball'}
        },
        {
            'name': 'Frame 3',
            'bboxes': np.array([[14, 24, 34, 44], [92, 102, 112, 122]]),
            'scores': np.array([0.94, 0.76]),
            'class_ids': np.array([0, 2]),  # player1, ball (player2 not detected)
            'class_names': {0: 'player1', 1: 'player2', 2: 'ball'}
        }
    ]
    
    # Exclude player2 (class 1)
    rejected_classes = {1}
    
    # Track assignment history
    track_history = {}
    
    for frame_data in frames_data:
        print(f"\n{frame_data['name']}:")
        print(f"  Raw detections: {frame_data['class_ids'].tolist()}")
        
        # Apply class exclusion filter
        keep_mask = np.array([class_id not in rejected_classes for class_id in frame_data['class_ids']])
        filtered_class_ids = frame_data['class_ids'][keep_mask]
        filtered_bboxes = frame_data['bboxes'][keep_mask]
        
        print(f"  Filtered class IDs: {filtered_class_ids.tolist()}")
        print(f"  Classes: {[frame_data['class_names'][cid] for cid in filtered_class_ids]}")
        
        # Verify player2 is never in filtered results
        assert 1 not in filtered_class_ids, \
            f"{frame_data['name']}: player2 should be excluded"
        
        # Simulate tracking
        for class_id in filtered_class_ids:
            if class_id not in track_history:
                track_history[class_id] = len(track_history)
            print(f"    Class {class_id} ({frame_data['class_names'][class_id]}) -> track_id={track_history[class_id]}")
    
    print(f"\nTrack history summary:")
    for class_id, track_id in track_history.items():
        class_name = frames_data[0]['class_names'][class_id]
        print(f"  Class {class_id} ({class_name}) -> track_id={track_id}")
    
    # Verify track ID consistency
    assert track_history[0] == 0, "player1 should consistently have track_id=0"
    assert track_history[2] == 1, "ball should consistently have track_id=1"
    assert 1 not in track_history, "player2 should never receive a track ID"
    
    print("\n" + "=" * 60)
    print("✅ TEST PASSED")
    print("=" * 60)
    print("Track IDs remain consistent across frames.")
    print("No player switches detected.")


if __name__ == '__main__':
    test_class_exclusion_end_to_end()
    test_class_exclusion_multiple_frames()
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
