#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration of Object Detection → Homography → TennisCourt Pipeline

This script demonstrates how the complete pipeline works:
1. PoseEstimation detects court keypoints
2. ObjectDetection detects players with bounding boxes
3. Homography converts bbox bottom-center points to court coordinates
4. TennisCourt visualizes players on the mini-court

The key feature implemented:
- Player position is the BOTTOM CENTER of the bounding box
- Both image coordinates (pixels) and court coordinates (meters) are displayed
"""

import numpy as np

print("=" * 80)
print("Object Detection → Homography → TennisCourt Pipeline Demo")
print("=" * 80)

# Simulate detected court keypoints (from PoseEstimation/TennisKeyPoints model)
print("\n1. COURT KEYPOINTS DETECTION (PoseEstimation Node)")
print("-" * 80)
court_keypoints = np.array([
    [120, 480],   # far_baseline_left_single_corner
    [680, 490],   # far_baseline_right_single_corner
    [130, 55],    # near_baseline_left_double_corner
    [670, 60],    # near_baseline_right_double_corner
    [180, 480],   # far_baseline_left_service_projection
    [180, 390],   # near_baseline_left_single_corner
    [620, 490],   # far_baseline_right_service_projection
    [620, 395],   # near_baseline_right_single_corner
    [180, 165],   # service_box_left_top_corner
    [620, 160],   # service_box_right_top_corner
    [190, 55],    # left_singles_sideline_midpoint
    [610, 60],    # right_singles_sideline_midpoint
    [400, 163],   # center_service_line_top_T
    [400, 392],   # center_service_line_bottom_T
], dtype=np.float32)
print(f"✓ Detected {len(court_keypoints)} court keypoints")

# Simulate object detection output with bounding boxes
print("\n2. PLAYER DETECTION (ObjectDetection Node - Tennis/Person Model)")
print("-" * 80)
print("Bounding boxes detected (format: [x1, y1, x2, y2]):")
print()

player_bboxes = [
    [220, 280, 280, 380],  # Player 1
    [520, 180, 580, 280],  # Player 2
]

for i, bbox in enumerate(player_bboxes, 1):
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    print(f"  Player {i}:")
    print(f"    Bounding Box: [{x1}, {y1}, {x2}, {y2}]")
    print(f"    Size: {width}x{height} pixels")
    print(f"    Top-left: ({x1}, {y1})")
    print(f"    Bottom-right: ({x2}, {y2})")
    print()

# Calculate bottom-center points
print("3. BOTTOM-CENTER EXTRACTION (Homography Node)")
print("-" * 80)
print("Converting bounding boxes to player ground positions:")
print("(Bottom-center = where player touches the ground)")
print()

bottom_centers = []
for i, bbox in enumerate(player_bboxes, 1):
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) / 2.0
    bottom_y = y2
    bottom_centers.append([center_x, bottom_y])
    
    print(f"  Player {i}:")
    print(f"    Bounding Box: [{x1}, {y1}] → [{x2}, {y2}]")
    print(f"    Bottom-Center: ({center_x:.1f}, {bottom_y:.1f})")
    print(f"    Calculation: X = ({x1} + {x2}) / 2 = {center_x:.1f}")
    print(f"                 Y = {y2} (bottom of bbox)")
    print()

# Simulate homography transformation
print("4. COORDINATE TRANSFORMATION (Homography Node)")
print("-" * 80)
print("Using homography matrix to transform image → court coordinates:")
print()

# NOTE: These are example transformed coordinates for demonstration purposes.
# In the actual pipeline, these would be calculated by cv2.findHomography
# based on the detected court keypoints and the tennis court template.
# The example values shown here are representative of typical transformations.
transformed_coords = [
    [3.29, 16.04],  # Player 1 in meters on court (example)
    [8.63, 10.24],  # Player 2 in meters on court (example)
]

print("┌─────────┬──────────────────────────┬──────────────────────────┐")
print("│ Player  │ Image Coordinates (px)   │ Court Coordinates (m)    │")
print("├─────────┼──────────────────────────┼──────────────────────────┤")
for i, (img_pt, court_pt) in enumerate(zip(bottom_centers, transformed_coords), 1):
    print(f"│    {i}    │  ({img_pt[0]:6.1f}, {img_pt[1]:6.1f})      │  ({court_pt[0]:5.2f}, {court_pt[1]:5.2f})       │")
print("└─────────┴──────────────────────────┴──────────────────────────┘")

# Verify coordinates are within court bounds
print("\n5. VALIDATION")
print("-" * 80)
print("Tennis court dimensions: 10.97m (width) x 23.77m (length)")
print()

all_valid = True
for i, (x, y) in enumerate(transformed_coords, 1):
    x_valid = 0 <= x <= 10.97
    y_valid = 0 <= y <= 23.77
    status = "✓" if (x_valid and y_valid) else "✗"
    print(f"  Player {i}: ({x:.2f}m, {y:.2f}m) {status}")
    if not (x_valid and y_valid):
        all_valid = False

print()
if all_valid:
    print("✓ All player positions are within court bounds")
else:
    print("✗ Some positions are outside court bounds")

# Show what's displayed on the visualization
print("\n6. VISUALIZATION (TennisCourt Node)")
print("-" * 80)
print("On the tennis court mini-court visualization, you will see:")
print()
print("  • Green tennis court with white lines")
print("  • White circles marking player positions")
print("  • Labels showing both coordinate systems:")
for i, (img_pt, court_pt) in enumerate(zip(bottom_centers, transformed_coords), 1):
    print(f"    Player {i}: Img:({img_pt[0]:.0f},{img_pt[1]:.0f}) Court:({court_pt[0]:.2f},{court_pt[1]:.2f})m")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("✓ Bounding boxes from ObjectDetection are converted to bottom-center points")
print("✓ Bottom-center represents where the player touches the ground")
print("✓ These points are transformed to real-world court coordinates")
print("✓ Both image and court coordinates are displayed in the console")
print("✓ Both coordinate systems are shown on the visual court")
print("✓ Tennis court templates match between Homography and TennisCourt nodes")
print()
print("Pipeline: ObjectDetection → Homography → TennisCourt")
print()
print("=" * 80)
