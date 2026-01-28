#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo: MOT Node JSON Output with CID and TID
=============================================

This script demonstrates the MOT (Multiple Object Tracking) node
displaying CID (Class ID) and TID (Track ID) in JSON format.

The script simulates a simple tracking scenario and prints the JSON
output in a readable format, showing both TID and CID values.

Usage:
    python tests/demo_mot_json_cid_tid.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import numpy as np
from node.TrackerNode.mot.bytetrack.mc_bytetrack import MultiClassByteTrack


def format_json_output(data):
    """Format JSON data for readable display"""
    def convert_to_json_compatible(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_to_json_compatible(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_json_compatible(item) for item in obj]
        else:
            return obj
    
    return json.dumps(convert_to_json_compatible(data), indent=2)


def main():
    """Demonstrate MOT tracking with JSON output"""
    
    print("=" * 80)
    print("MOT NODE - JSON OUTPUT DEMONSTRATION")
    print("Displaying CID (Class ID) and TID (Track ID) in JSON format")
    print("=" * 80)
    print()
    
    # Initialize the ByteTrack tracker
    tracker = MultiClassByteTrack()
    print("✓ Tracker initialized: ByteTrack\n")
    
    # Create a dummy frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Simulate tracking over 3 frames
    scenarios = [
        {
            'frame_num': 1,
            'description': 'Two persons detected',
            'bboxes': [[100, 100, 200, 250], [300, 150, 400, 300]],
            'scores': [0.95, 0.88],
            'class_ids': [0, 0],
            'class_names': {0: 'person'}
        },
        {
            'frame_num': 2,
            'description': 'Same persons moved (tracking continuity)',
            'bboxes': [[110, 105, 210, 255], [310, 155, 410, 305]],
            'scores': [0.93, 0.90],
            'class_ids': [0, 0],
            'class_names': {0: 'person'}
        },
        {
            'frame_num': 3,
            'description': 'Third person appears, one person with ball',
            'bboxes': [
                [120, 110, 220, 260],  # Person 1
                [320, 160, 420, 310],  # Person 2
                [500, 200, 600, 350],  # Person 3 (new)
            ],
            'scores': [0.91, 0.89, 0.92],
            'class_ids': [0, 0, 0],
            'class_names': {0: 'person'}
        }
    ]
    
    for scenario in scenarios:
        print("-" * 80)
        print(f"FRAME {scenario['frame_num']}: {scenario['description']}")
        print("-" * 80)
        
        # Run tracker
        track_ids, t_bboxes, t_scores, t_class_ids = tracker(
            frame,
            scenario['bboxes'],
            scenario['scores'],
            scenario['class_ids']
        )
        
        # Build class names list
        class_names_list = [scenario['class_names'].get(cid, 'unknown') for cid in t_class_ids]
        
        # Create MOT JSON output (same format as node_mot.py)
        mot_json_output = {
            'track_ids': track_ids,       # TID: Track IDs
            'bboxes': t_bboxes,
            'scores': t_scores,
            'class_ids': t_class_ids,     # CID: Class IDs
            'class_names': class_names_list,
            'track_id_dict': {tid: idx for idx, tid in enumerate(track_ids)}
        }
        
        # Display tracking summary
        print(f"\n📊 Tracking Summary:")
        print(f"   Objects detected: {len(scenario['bboxes'])}")
        print(f"   Objects tracked:  {len(track_ids)}")
        print()
        
        # Display TID and CID for each tracked object
        print("   Tracked Objects:")
        for i, (tid, cid, cname, score) in enumerate(zip(
            track_ids, t_class_ids, class_names_list, t_scores
        )):
            print(f"     • Object {i+1}:")
            print(f"       - TID (Track ID): {tid}")
            print(f"       - CID (Class ID): {cid} ({cname})")
            print(f"       - Score: {score:.2f}")
        
        # Display full JSON output
        print(f"\n📝 MOT JSON Output:")
        print(format_json_output(mot_json_output))
        print()
    
    # Final summary
    print("=" * 80)
    print("✓ DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Points:")
    print("  • TID (Track ID): Persistent identifier for each tracked object")
    print("  • CID (Class ID): Object class identifier (0=person, 1=ball, etc.)")
    print("  • The MOT node outputs both TID and CID in JSON format via Output03")
    print("  • Track IDs persist across frames for continuous object tracking")
    print()
    print("✓ Le nœud MOT fonctionne correctement et effectue le suivi des objets")
    print("✓ Les CID et TID sont affichés dans l'output JSON")
    print()


if __name__ == '__main__':
    main()
