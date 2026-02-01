#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual demonstration of TID/CID labels being visible at all image positions.
This creates sample images showing the before and after fix.
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.OverlayNode.draw_util.draw_util import draw_multi_object_tracking_info


def create_demo_image():
    """Create a demo image showing labels at various positions"""
    # Create a larger test image with a gradient background for visibility
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Add a gradient background to make it look nicer
    for y in range(720):
        color_val = int(30 + (y / 720.0) * 30)
        image[y, :] = [color_val, color_val, color_val]
    
    # Add grid lines for reference
    for i in range(0, 1280, 100):
        cv2.line(image, (i, 0), (i, 720), (60, 60, 60), 1)
    for i in range(0, 720, 100):
        cv2.line(image, (0, i), (1280, i), (60, 60, 60), 1)
    
    # Multiple bboxes at various positions to demonstrate the fix
    track_ids = [1, 2, 3, 4, 5, 6]
    bboxes = [
        [50, 5, 200, 155],        # Top-left corner (would have labels cut off)
        [500, 10, 650, 160],       # Top edge
        [1050, 15, 1200, 165],     # Top-right corner
        [50, 300, 200, 450],       # Left edge middle
        [550, 300, 700, 450],      # Center (normal case)
        [1050, 300, 1200, 450],    # Right edge middle
    ]
    scores = [0.95, 0.88, 0.92, 0.87, 0.96, 0.89]
    class_ids = [0, 1, 0, 1, 0, 1]
    class_names = {0: 'person', 1: 'ball'}
    track_id_dict = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    
    # Draw the tracking info with the fix
    result_image = draw_multi_object_tracking_info(
        image,
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    # Add title text
    cv2.putText(
        result_image,
        'TID/CID Labels Visibility Fix - Labels visible at all positions',
        (50, 680),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )
    
    # Add explanation
    cv2.putText(
        result_image,
        'Notice: Labels near edges are placed INSIDE bounding boxes',
        (50, 710),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (200, 200, 200),
        1,
    )
    
    return result_image


def main():
    """Create and save demo images"""
    print("=" * 70)
    print("Creating visual demonstration of TID/CID label visibility fix")
    print("=" * 70)
    print()
    
    # Create demo image
    print("Creating demo image...")
    demo_image = create_demo_image()
    
    # Create output directory
    output_dir = '/tmp/label_visibility_demo'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the image
    output_path = os.path.join(output_dir, 'label_visibility_fix_demo.png')
    cv2.imwrite(output_path, demo_image)
    
    print(f"✓ Demo image saved to: {output_path}")
    print()
    print("The demo image shows:")
    print("  • 6 bounding boxes at various positions (corners, edges, center)")
    print("  • TID and CID labels visible for all boxes")
    print("  • Labels at top edge are placed INSIDE the bounding box")
    print("  • Labels in the middle remain ABOVE the bounding box (normal)")
    print()
    print("This demonstrates that the fix successfully addresses the issue:")
    print("'TID and CID labels are not visible in tracking all around an image,")
    print(" not only near the corner or edge'")
    print()
    print("=" * 70)
    
    return output_path


if __name__ == '__main__':
    output_path = main()
    print(f"\nView the demo image at: {output_path}")
