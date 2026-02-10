#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo: Visual demonstration of tracking bounding box improvements
=================================================================

This script demonstrates the improved tracking bounding box drawing with:
- Thicker rectangles (4px instead of 2px)
- Filled backgrounds for CID and TID labels
- White text on colored backgrounds for better visibility

Usage:
    python tests/demo_tracking_box_visual.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import cv2
from node.OverlayNode.draw_util.draw_util import draw_multi_object_tracking_info


def create_demo_image():
    """Create a demo image with tracking boxes"""
    # Create a sample image (simulating a scene with multiple objects)
    image = np.ones((720, 1280, 3), dtype=np.uint8) * 240  # Light gray background
    
    # Add some visual context (simulating a scene)
    # Draw some rectangles as "background objects"
    cv2.rectangle(image, (50, 100), (300, 400), (200, 200, 200), -1)
    cv2.rectangle(image, (500, 200), (700, 500), (210, 210, 210), -1)
    cv2.rectangle(image, (900, 150), (1150, 450), (205, 205, 205), -1)
    
    # Test data for tracking
    track_ids = [1, 2, 3]
    bboxes = [
        [100, 150, 250, 350],   # Person 1
        [550, 250, 650, 450],   # Person 2  
        [950, 200, 1100, 400],  # Ball
    ]
    scores = [0.95, 0.88, 0.92]
    class_ids = [0, 0, 1]
    class_names = {0: 'person', 1: 'ball'}
    track_id_dict = {1: 0, 2: 1, 3: 2}
    
    # Draw tracking boxes with the new improvements
    result_image = draw_multi_object_tracking_info(
        image,
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    return result_image


def main():
    """Create and save the demo image"""
    print("=" * 80)
    print("TRACKING BOUNDING BOX VISUAL IMPROVEMENTS DEMO")
    print("=" * 80)
    print()
    print("Changes implemented:")
    print("  ✓ Thicker bounding box rectangles (4px instead of 2px)")
    print("  ✓ Filled backgrounds for TID and CID labels")
    print("  ✓ White text on colored backgrounds for better visibility")
    print()
    print("Creating demo image...")
    
    # Create the demo image
    demo_image = create_demo_image()
    
    # Save the image
    output_path = '/tmp/tracking_box_demo.png'
    cv2.imwrite(output_path, demo_image)
    
    print(f"✓ Demo image saved to: {output_path}")
    print()
    
    # Add annotations explaining the improvements
    print("Visual Improvements:")
    print("  • Rectangle thickness: 4px (more visible)")
    print("  • TID label: Filled colored background with white text")
    print("  • CID label: Filled colored background with white text")
    print("  • Each tracked object has a unique color")
    print()
    
    print("=" * 80)
    print("✓ DEMO COMPLETE")
    print("=" * 80)
    print()
    print(f"View the result: {output_path}")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
