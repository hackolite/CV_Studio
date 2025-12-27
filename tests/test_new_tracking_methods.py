#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify that the new SORT and CenterTrack trackers work correctly
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

# Test imports
print("Testing new tracker imports...")

from node.TrackerNode.mot.sort.mc_sort import MultiClassSORT
print("✓ SORT imported successfully")

from node.TrackerNode.mot.centertrack.mc_centertrack import MultiClassCenterTrack
print("✓ CenterTrack imported successfully")

print("\nBoth new trackers imported successfully!")

# Test instantiation
print("\nTesting tracker instantiation...")

trackers = {
    'SORT': MultiClassSORT(),
    'CenterTrack': MultiClassCenterTrack(),
}

print("✓ Both new trackers instantiated successfully")

# Test with sample data
print("\nTesting tracker calls with sample data...")

# Create dummy frame
frame = np.zeros((480, 640, 3), dtype=np.uint8)

# Create dummy detections (format: [x1, y1, x2, y2])
bboxes = [
    [100, 100, 200, 200],
    [300, 150, 400, 250],
]
scores = [0.9, 0.85]
class_ids = [0, 1]

success_count = 0
for tracker_name, tracker in trackers.items():
    print(f"\nTesting {tracker_name}...")
    try:
        track_ids, track_bboxes, track_scores, track_class_ids = tracker(
            frame, bboxes, scores, class_ids
        )
        print(f"  ✓ {tracker_name} returned {len(track_ids)} tracks")
        print(f"    Track IDs: {track_ids}")
        print(f"    Track bboxes: {track_bboxes}")
        success_count += 1
    except Exception as e:
        print(f"  ✗ {tracker_name} failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
if success_count == len(trackers):
    print("✓ SUCCESS: All new tracking methods are working correctly!")
    print(f"Available new trackers: {', '.join(trackers.keys())}")
    print("="*60)
    sys.exit(0)
else:
    print(f"✗ FAILED: Only {success_count}/{len(trackers)} trackers passed")
    print("="*60)
    sys.exit(1)
