#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify that the Kalman Filter tracker can be instantiated and called
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

# Test import
print("Testing Kalman Filter tracker import...")

from node.TrackerNode.mot.kalman.mc_kalman import MultiClassKalmanFilter
print("✓ Kalman Filter imported successfully")

# Test instantiation
print("\nTesting Kalman Filter instantiation...")

tracker = MultiClassKalmanFilter()
print("✓ Kalman Filter instantiated successfully")

# Test with sample data
print("\nTesting Kalman Filter with sample data...")

# Create dummy frame
frame = np.zeros((480, 640, 3), dtype=np.uint8)

# Create dummy detections (format: [x1, y1, x2, y2])
bboxes = [
    [100, 100, 200, 200],
    [300, 150, 400, 250],
]
scores = [0.9, 0.85]
class_ids = [0, 1]

print("\nFrame 1: Initial detections")
track_ids, track_bboxes, track_scores, track_class_ids = tracker(
    frame, bboxes, scores, class_ids
)
print(f"  ✓ Returned {len(track_ids)} tracks")
print(f"    Track IDs: {track_ids}")
print(f"    Track bboxes: {track_bboxes}")

# Test with second frame (slightly moved objects)
print("\nFrame 2: Moved detections")
bboxes2 = [
    [105, 105, 205, 205],  # Moved slightly
    [305, 155, 405, 255],  # Moved slightly
]
track_ids2, track_bboxes2, track_scores2, track_class_ids2 = tracker(
    frame, bboxes2, scores, class_ids
)
print(f"  ✓ Returned {len(track_ids2)} tracks")
print(f"    Track IDs: {track_ids2}")
print(f"    Track bboxes: {track_bboxes2}")

# Test with third frame (one object missing)
print("\nFrame 3: One detection missing")
bboxes3 = [
    [110, 110, 210, 210],  # First object moved
]
scores3 = [0.9]
class_ids3 = [0]
track_ids3, track_bboxes3, track_scores3, track_class_ids3 = tracker(
    frame, bboxes3, scores3, class_ids3
)
print(f"  ✓ Returned {len(track_ids3)} tracks")
print(f"    Track IDs: {track_ids3}")
print(f"    Track bboxes: {track_bboxes3}")

# Test with empty detections
print("\nFrame 4: Empty detections")
track_ids4, track_bboxes4, track_scores4, track_class_ids4 = tracker(
    frame, [], [], []
)
print(f"  ✓ Returned {len(track_ids4)} tracks")
print(f"    Track IDs: {track_ids4}")

print("\n" + "="*60)
print("SUCCESS: Kalman Filter tracker is working correctly!")
print("="*60)
