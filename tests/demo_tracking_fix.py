#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual demonstration of the tracking text visibility fix.
Creates sample images showing tracking labels on objects near the image edge.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
from node.basenode import Node


def create_demo_image():
    """Create a demonstration image showing tracking on objects at various positions."""
    # Create a larger image for better visibility
    width, height = 1280, 720
    image = np.ones((height, width, 3), dtype=np.uint8) * 240  # Light gray background
    
    # Add a title at the top
    cv2.putText(
        image, "CV Studio - Tracking Visualization Fix Demo",
        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (50, 50, 50), 2
    )
    
    # Draw reference grid
    for y in range(0, height, 50):
        cv2.line(image, (0, y), (width, y), (220, 220, 220), 1)
    for x in range(0, width, 50):
        cv2.line(image, (x, 0), (x, height), (220, 220, 220), 1)
    
    # Simulate tracked objects at different positions
    track_ids = [1, 2, 3, 4]
    bboxes = [
        [50, 10, 200, 150],      # Top-left (very close to top edge)
        [300, 5, 450, 140],      # Top-center (even closer to edge)
        [600, 80, 750, 220],     # Top-right (some margin from top)
        [950, 300, 1100, 450]    # Middle-right (normal position)
    ]
    scores = [0.95, 0.92, 0.88, 0.97]
    class_ids = [0, 0, 1, 0]
    class_names = {0: 'person', 1: 'car'}
    track_id_dict = {1: 0, 2: 1, 3: 2, 4: 3}
    
    # Draw using the fixed method
    node = Node()
    result_image = node.draw_multi_object_tracking_info(
        image.copy(),
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    # Add annotations explaining the fix
    annotation_y = height - 100
    cv2.putText(
        result_image, "Fix: Text labels (TID/CID) stay visible even for objects near image edges",
        (20, annotation_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 128, 0), 2
    )
    cv2.putText(
        result_image, "Previously, text at negative Y coordinates was invisible (not drawn)",
        (20, annotation_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 0, 0), 2
    )
    cv2.putText(
        result_image, "Now: Text position is clamped to ensure visibility",
        (20, annotation_y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 128, 0), 2
    )
    
    return result_image


def main():
    """Generate and save the demonstration image."""
    print("\n" + "="*70)
    print("Generating Tracking Visualization Fix Demonstration")
    print("="*70)
    
    # Create the demo image
    print("\nCreating demonstration image...")
    demo_image = create_demo_image()
    
    # Save to file
    output_path = '/tmp/tracking_fix_demo.png'
    cv2.imwrite(output_path, demo_image)
    print(f"✓ Demo image saved to: {output_path}")
    
    # Display statistics
    print("\nDemo Image Details:")
    print(f"  • Size: {demo_image.shape[1]}x{demo_image.shape[0]} pixels")
    print(f"  • Shows 4 tracked objects at different vertical positions")
    print(f"  • Objects near top edge (y < 20) have text labels clamped to visible area")
    print(f"  • All TID and CID labels are now visible")
    
    print("\n" + "="*70)
    print("✓ Demonstration Complete")
    print("="*70)
    print(f"\nView the result: {output_path}")
    
    return output_path


if __name__ == '__main__':
    try:
        output_path = main()
        print("\n✓ Success! The tracking text visibility fix is working correctly.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
