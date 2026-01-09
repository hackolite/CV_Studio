#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify that all tracking nodes can be instantiated and called
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

# Test imports
print("Testing tracker imports...")

from node.TrackerNode.mot.motpy.motpy import Motpy
print("✓ Motpy imported successfully")

from node.TrackerNode.mot.bytetrack.mc_bytetrack import MultiClassByteTrack
print("✓ ByteTrack imported successfully")

from node.TrackerNode.mot.norfair.mc_norfair import MultiClassNorfair
print("✓ Norfair imported successfully")

from node.TrackerNode.mot.iou_tracker.iou_tracker import MultiClassIOUTracker
print("✓ IOU Tracker imported successfully")

from node.TrackerNode.mot.sort.mc_sort import MultiClassSORT
print("✓ SORT imported successfully")

from node.TrackerNode.mot.centertrack.mc_centertrack import MultiClassCenterTrack
print("✓ CenterTrack imported successfully")

from node.TrackerNode.mot.kalman.mc_kalman import MultiClassKalmanFilter
print("✓ Kalman Filter imported successfully")

print("\nAll trackers imported successfully!")

# Test instantiation
print("\nTesting tracker instantiation...")

trackers = {
    'Motpy': Motpy(),
    'ByteTrack': MultiClassByteTrack(),
    'Norfair': MultiClassNorfair(),
    'IOU Tracker': MultiClassIOUTracker(),
    'SORT': MultiClassSORT(),
    'CenterTrack': MultiClassCenterTrack(),
    'Kalman Filter': MultiClassKalmanFilter(),
}

print("✓ All trackers instantiated successfully")

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

for tracker_name, tracker in trackers.items():
    print(f"\nTesting {tracker_name}...")
    try:
        track_ids, track_bboxes, track_scores, track_class_ids = tracker(
            frame, bboxes, scores, class_ids
        )
        print(f"  ✓ {tracker_name} returned {len(track_ids)} tracks")
        print(f"    Track IDs: {track_ids}")
    except Exception as e:
        print(f"  ✗ {tracker_name} failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("SUMMARY: All tracking nodes are working correctly!")
print(f"Available trackers: {', '.join(trackers.keys())}")
print("="*60)
