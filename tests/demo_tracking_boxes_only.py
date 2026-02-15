#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo: Visual demonstration of "Tracking Boxes Only" feature
============================================================

This script demonstrates the difference between:
1. Default mode: Shows both detection and tracking boxes
2. Tracking-only mode: Shows only tracking boxes on black background

Usage:
    python tests/demo_tracking_boxes_only.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import cv2


def create_demo_frames():
    """Create demo frames showing the difference between modes"""
    
    # Create a sample video frame (simulating a scene)
    base_frame = np.ones((480, 640, 3), dtype=np.uint8) * 240  # Light gray background
    
    # Add some visual context (simulating a scene with objects)
    cv2.rectangle(base_frame, (50, 100), (300, 400), (200, 200, 200), -1)
    cv2.rectangle(base_frame, (400, 150), (600, 350), (210, 210, 210), -1)
    
    # Simulate detection boxes (green) drawn by object detection node
    frame_with_detections = base_frame.copy()
    cv2.rectangle(frame_with_detections, (100, 150), (250, 350), (0, 255, 0), 3)  # Green detection box
    cv2.putText(frame_with_detections, "Detection: person", (100, 140), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.rectangle(frame_with_detections, (450, 200), (550, 300), (0, 255, 0), 3)  # Another detection
    cv2.putText(frame_with_detections, "Detection: ball", (450, 190), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Mode 1: Default (tracking boxes on top of frame with detections)
    # This shows BOTH detection and tracking boxes
    frame_mode_default = frame_with_detections.copy()
    # Draw tracking boxes (red) on top
    cv2.rectangle(frame_mode_default, (110, 160), (240, 340), (0, 0, 255), 4)  # Red tracking box
    cv2.putText(frame_mode_default, "TID:0(0.95)", (110, 150), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame_mode_default, "CID:0(person)", (110, 380), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    cv2.rectangle(frame_mode_default, (455, 210), (545, 290), (0, 0, 255), 4)  # Another tracking box
    cv2.putText(frame_mode_default, "TID:1(0.88)", (455, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame_mode_default, "CID:1(ball)", (455, 330), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Mode 2: Tracking-only (tracking boxes on clean black frame)
    # This shows ONLY tracking boxes
    frame_mode_tracking_only = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw only tracking boxes (red)
    cv2.rectangle(frame_mode_tracking_only, (110, 160), (240, 340), (0, 0, 255), 4)  # Red tracking box
    cv2.putText(frame_mode_tracking_only, "TID:0(0.95)", (110, 150), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame_mode_tracking_only, "CID:0(person)", (110, 380), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    cv2.rectangle(frame_mode_tracking_only, (455, 210), (545, 290), (0, 0, 255), 4)  # Another tracking box
    cv2.putText(frame_mode_tracking_only, "TID:1(0.88)", (455, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame_mode_tracking_only, "CID:1(ball)", (455, 330), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return frame_mode_default, frame_mode_tracking_only


def main():
    """Create and save demo images"""
    print("=" * 80)
    print("DEMO: Tracking Boxes Only Feature")
    print("=" * 80)
    print()
    print("Creating demo frames...")
    
    frame_default, frame_tracking_only = create_demo_frames()
    
    # Add labels to the images
    cv2.putText(frame_default, "Mode: Default (shows both detection & tracking)", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame_default, "Green = Detection boxes, Red = Tracking boxes", 
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    cv2.putText(frame_tracking_only, "Mode: Tracking Boxes Only (checkbox enabled)", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame_tracking_only, "Red = Tracking boxes only (no detection boxes)", 
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Save the images
    output_dir = '/tmp'
    default_path = os.path.join(output_dir, 'mot_default_mode.png')
    tracking_only_path = os.path.join(output_dir, 'mot_tracking_only_mode.png')
    
    cv2.imwrite(default_path, frame_default)
    cv2.imwrite(tracking_only_path, frame_tracking_only)
    
    print(f"✓ Default mode image saved: {default_path}")
    print(f"✓ Tracking-only mode image saved: {tracking_only_path}")
    print()
    
    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print()
    print("Default Mode (Checkbox Unchecked):")
    print("  • Shows video frame with all pre-drawn content")
    print("  • Detection boxes visible (green)")
    print("  • Tracking boxes drawn on top (red)")
    print("  • Result: Both types of boxes are visible")
    print("  • Use case: General visualization with full context")
    print()
    print("Tracking-Only Mode (Checkbox Checked):")
    print("  • Starts with clean black background")
    print("  • Only tracking boxes visible (red)")
    print("  • No detection boxes (they're on the original frame we didn't use)")
    print("  • Result: Clear view of only tracking information")
    print("  • Use case: Focus on tracking performance, debugging")
    print()
    
    print("=" * 80)
    print("✓ DEMO COMPLETE")
    print("=" * 80)
    print()
    print(f"View the results:")
    print(f"  1. Default mode: {default_path}")
    print(f"  2. Tracking-only mode: {tracking_only_path}")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
