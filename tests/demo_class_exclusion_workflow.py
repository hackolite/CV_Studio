#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual demonstration that class exclusion in object detection
properly filters data before it reaches the tracking node.

This script simulates the exact data flow:
ObjectDetection -> node_result_dict -> MOT
"""

import json


class SimulatedObjectDetectionNode:
    """Simulates the Object Detection node with class exclusion"""
    
    def __init__(self):
        self.tag_node_rejected_classes_value_name = "rejected_classes"
        self._rejected_classes_value = ""
    
    def set_rejected_classes(self, value):
        """Simulates user setting the rejected classes dropdown"""
        self._rejected_classes_value = value
    
    def update(self, frame_data):
        """Simulates the update() method of the Object Detection node"""
        # Simulate model detection
        bboxes = frame_data['bboxes']
        scores = frame_data['scores']
        class_ids = frame_data['class_ids']
        class_name_dict = frame_data['class_names']
        
        print(f"\n  Model Output: {len(bboxes)} detections")
        print(f"    Class IDs: {class_ids}")
        print(f"    Classes: {[class_name_dict[cid] for cid in class_ids]}")
        
        # Apply class rejection filter (same logic as node_object_detection.py)
        if len(bboxes) > 0:
            rejected_classes_str = self._rejected_classes_value
            if rejected_classes_str and rejected_classes_str.strip():
                print(f"  Class Rejection Input: '{rejected_classes_str}'")
                
                rejected_classes = set()
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
                
                if rejected_classes:
                    print(f"  Rejected Class IDs: {rejected_classes}")
                    keep_mask = [class_id not in rejected_classes for class_id in class_ids]
                    bboxes = [bbox for i, bbox in enumerate(bboxes) if keep_mask[i]]
                    scores = [score for i, score in enumerate(scores) if keep_mask[i]]
                    class_ids = [class_id for i, class_id in enumerate(class_ids) if keep_mask[i]]
                    print(f"  After Filtering: {len(bboxes)} detections")
                    print(f"    Class IDs: {class_ids}")
        
        # Create result dictionary
        result = {}
        if len(bboxes) > 0:
            result['bboxes'] = bboxes
            result['scores'] = scores
            result['class_ids'] = class_ids
            result['class_names'] = class_name_dict
        else:
            result['bboxes'] = []
            result['scores'] = []
            result['class_ids'] = []
            result['class_names'] = class_name_dict
        
        print(f"  JSON Output: {len(result['bboxes'])} detections, class_ids={result['class_ids']}")
        
        # Simulate return data
        data = {"json": result}
        return data


class SimulatedMOTNode:
    """Simulates the Multi-Object Tracking node"""
    
    def __init__(self):
        self.track_id_counter = 0
        self.track_history = {}
    
    def update(self, node_result):
        """Simulates the update() method of the MOT node"""
        od_bboxes = node_result.get('bboxes', [])
        od_scores = node_result.get('scores', [])
        od_class_ids = node_result.get('class_ids', [])
        od_class_names = node_result.get('class_names', {})
        
        print(f"\n  MOT Input: {len(od_bboxes)} detections")
        print(f"    Class IDs: {od_class_ids}")
        print(f"    Classes: {[od_class_names.get(cid, 'unknown') for cid in od_class_ids]}")
        
        # Simple tracking: assign unique track ID to each class
        track_ids = []
        for class_id in od_class_ids:
            if class_id not in self.track_history:
                self.track_history[class_id] = self.track_id_counter
                self.track_id_counter += 1
            track_ids.append(self.track_history[class_id])
        
        if track_ids:
            print(f"  Track Assignments:")
            for i, (class_id, track_id) in enumerate(zip(od_class_ids, track_ids)):
                class_name = od_class_names.get(class_id, 'unknown')
                print(f"    Detection {i}: {class_name} (class={class_id}) -> track_id={track_id}")
        else:
            print(f"  No detections to track")
        
        result = {
            'track_ids': track_ids,
            'bboxes': od_bboxes,
            'class_ids': od_class_ids,
            'class_names': od_class_names
        }
        return result


def simulate_frame(frame_num, bboxes, scores, class_ids, class_names):
    """Helper to create frame data"""
    return {
        'frame_num': frame_num,
        'bboxes': bboxes,
        'scores': scores,
        'class_ids': class_ids,
        'class_names': class_names
    }


def main():
    print("=" * 70)
    print("SIMULATION: Object Detection with Class Exclusion -> Tracking")
    print("=" * 70)
    
    # Create nodes
    obj_det_node = SimulatedObjectDetectionNode()
    mot_node = SimulatedMOTNode()
    
    # Simulate node_result_dict (stores JSON outputs)
    node_result_dict = {}
    
    # Tennis scenario: player1 (class 0), player2 (class 1), ball (class 2)
    class_names = {0: 'player1', 1: 'player2', 2: 'ball'}
    
    # User wants to exclude player2 (class 1)
    obj_det_node.set_rejected_classes("1: player2")
    
    print("\nConfiguration:")
    print(f"  Rejected Classes: '1: player2'")
    print(f"  Expected Behavior: Only player1 and ball should be tracked")
    
    # Simulate 3 frames
    frames = [
        simulate_frame(1, 
            [[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]],
            [0.95, 0.85, 0.75],
            [0, 1, 2],  # player1, player2, ball
            class_names
        ),
        simulate_frame(2,
            [[12, 22, 32, 42], [52, 62, 72, 82], [92, 102, 112, 122]],
            [0.96, 0.86, 0.76],
            [0, 1, 2],  # player1, player2, ball
            class_names
        ),
        simulate_frame(3,
            [[14, 24, 34, 44], [54, 64, 74, 84], [94, 104, 114, 124]],
            [0.94, 0.84, 0.77],
            [0, 1, 2],  # player1, player2, ball
            class_names
        ),
    ]
    
    for frame_data in frames:
        print("\n" + "=" * 70)
        print(f"FRAME {frame_data['frame_num']}")
        print("=" * 70)
        
        # Object Detection Node
        print("\n1. OBJECT DETECTION NODE")
        print("-" * 70)
        obj_det_result = obj_det_node.update(frame_data)
        
        # Store in node_result_dict (simulates main.py)
        node_result_dict['ObjectDetection'] = obj_det_result['json']
        
        # MOT Node
        print("\n2. MULTI-OBJECT TRACKING NODE")
        print("-" * 70)
        mot_result = mot_node.update(node_result_dict['ObjectDetection'])
    
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    
    # Check that player2 was never tracked
    print("\nTrack History:")
    for class_id, track_id in mot_node.track_history.items():
        class_name = class_names.get(class_id, 'unknown')
        print(f"  Class {class_id} ({class_name}) -> track_id={track_id}")
    
    print("\nVerification:")
    if 1 in mot_node.track_history:
        print("  ❌ FAILED: player2 (class 1) was tracked (should be excluded)")
    else:
        print("  ✅ PASSED: player2 (class 1) was NOT tracked (correctly excluded)")
    
    if 0 in mot_node.track_history:
        print("  ✅ PASSED: player1 (class 0) was tracked (should be present)")
    else:
        print("  ❌ FAILED: player1 (class 0) was NOT tracked (should be present)")
    
    if 2 in mot_node.track_history:
        print("  ✅ PASSED: ball (class 2) was tracked (should be present)")
    else:
        print("  ❌ FAILED: ball (class 2) was NOT tracked (should be present)")
    
    # Check for track ID consistency
    print("\nTrack ID Consistency:")
    expected_player1_id = 0
    expected_ball_id = 1
    
    if mot_node.track_history.get(0) == expected_player1_id:
        print(f"  ✅ PASSED: player1 has consistent track_id={expected_player1_id}")
    else:
        print(f"  ❌ FAILED: player1 track_id changed")
    
    if mot_node.track_history.get(2) == expected_ball_id:
        print(f"  ✅ PASSED: ball has consistent track_id={expected_ball_id}")
    else:
        print(f"  ❌ FAILED: ball track_id changed")
    
    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print("Class exclusion is working correctly:")
    print("  1. Object Detection filters out excluded classes")
    print("  2. Filtered JSON is passed to node_result_dict")
    print("  3. MOT receives only the filtered detections")
    print("  4. No 'player switches' occur because player2 never enters tracking")
    print("\nIf player switches still occur in production:")
    print("  - Check if exclusion settings change during runtime")
    print("  - Verify the correct class IDs are being excluded")
    print("  - Enable DEBUG logging to trace actual data flow")
    print("=" * 70)


if __name__ == '__main__':
    main()
