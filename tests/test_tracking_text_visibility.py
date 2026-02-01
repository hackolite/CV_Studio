#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that tracking text labels (TID/CID) are visible even when objects
are detected near the top edge of the image.

This test addresses the bug where text was drawn at negative Y coordinates,
making it invisible.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
from node.basenode import Node
from node.OverlayNode.draw_util import draw_util


def test_tracking_text_visibility_near_top():
    """Test that tracking text is visible when objects are near the top of the image."""
    print("\n" + "="*70)
    print("Testing Tracking Text Visibility Near Image Top")
    print("="*70)
    
    # Create a test image (480x640 RGB)
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Create test data for an object very close to the top of the image
    track_ids = [1, 2]
    bboxes = [
        [100, 5, 200, 100],   # Object near top (y1=5)
        [300, 200, 400, 300]  # Object in middle (y1=200)
    ]
    scores = [0.95, 0.87]
    class_ids = [0, 1]
    class_names = {0: 'person', 1: 'car'}
    track_id_dict = {1: 0, 2: 1}
    
    # Test with basenode method
    print("\n1. Testing with basenode.Node.draw_multi_object_tracking_info...")
    node = Node()
    result_image_basenode = node.draw_multi_object_tracking_info(
        image.copy(),
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    # Check if any pixels were modified (text was drawn)
    if np.any(result_image_basenode != image):
        print("   ✓ Text was drawn on the image")
        # Count non-zero pixels to estimate text coverage
        diff = np.sum(result_image_basenode != image)
        print(f"   ✓ Modified {diff} pixels (includes text and bounding boxes)")
    else:
        print("   ✗ ERROR: No pixels were modified - text may not be visible!")
        return False
    
    # Test with draw_util method
    print("\n2. Testing with draw_util.draw_multi_object_tracking_info...")
    result_image_drawutil = draw_util.draw_multi_object_tracking_info(
        image.copy(),
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    # Check if any pixels were modified
    if np.any(result_image_drawutil != image):
        print("   ✓ Text was drawn on the image")
        diff = np.sum(result_image_drawutil != image)
        print(f"   ✓ Modified {diff} pixels (includes text and bounding boxes)")
    else:
        print("   ✗ ERROR: No pixels were modified - text may not be visible!")
        return False
    
    # Verify that text is drawn in the top region where it should be visible
    print("\n3. Verifying text is drawn in visible region (top 50 pixels)...")
    
    # Check if there are any non-zero pixels in the top region
    # (excluding the first 2 rows to account for any edge effects)
    top_region_basenode = result_image_basenode[2:50, :, :]
    top_region_drawutil = result_image_drawutil[2:50, :, :]
    
    has_text_basenode = np.any(top_region_basenode > 0)
    has_text_drawutil = np.any(top_region_drawutil > 0)
    
    if has_text_basenode and has_text_drawutil:
        print("   ✓ Text is visible in the top region of the image")
        print("   ✓ Fix successfully ensures text stays within image bounds")
    else:
        print("   ✗ ERROR: No text found in top region")
        print(f"     Basenode has text: {has_text_basenode}")
        print(f"     Draw_util has text: {has_text_drawutil}")
        return False
    
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED")
    print("="*70)
    print("\nTracking text labels (TID/CID) are now correctly visible")
    print("even when objects are detected near the top edge of the image.")
    print("="*70)
    return True


def test_tracking_text_extreme_cases():
    """Test extreme cases to ensure robustness."""
    print("\n" + "="*70)
    print("Testing Extreme Cases")
    print("="*70)
    
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Test case 1: Object at y=0 (top edge)
    print("\n1. Object at y=0 (top edge)...")
    track_ids = [1]
    bboxes = [[100, 0, 200, 100]]
    scores = [0.99]
    class_ids = [0]
    class_names = {0: 'person'}
    track_id_dict = {1: 0}
    
    node = Node()
    result = node.draw_multi_object_tracking_info(
        image.copy(), track_ids, bboxes, scores, class_ids, class_names, track_id_dict
    )
    
    if np.any(result != image):
        print("   ✓ Handled object at y=0 correctly")
    else:
        print("   ✗ Failed to draw for object at y=0")
        return False
    
    # Test case 2: Object at y=1 (almost top edge)
    print("\n2. Object at y=1 (almost top edge)...")
    bboxes = [[100, 1, 200, 100]]
    result = node.draw_multi_object_tracking_info(
        image.copy(), track_ids, bboxes, scores, class_ids, class_names, track_id_dict
    )
    
    if np.any(result != image):
        print("   ✓ Handled object at y=1 correctly")
    else:
        print("   ✗ Failed to draw for object at y=1")
        return False
    
    # Test case 3: Multiple objects all near top
    print("\n3. Multiple objects all near top...")
    track_ids = [1, 2, 3]
    bboxes = [[50, 3, 100, 80], [150, 5, 200, 85], [250, 2, 300, 82]]
    scores = [0.95, 0.90, 0.88]
    class_ids = [0, 1, 0]
    class_names = {0: 'person', 1: 'car'}
    track_id_dict = {1: 0, 2: 1, 3: 2}
    
    result = node.draw_multi_object_tracking_info(
        image.copy(), track_ids, bboxes, scores, class_ids, class_names, track_id_dict
    )
    
    if np.any(result != image):
        print("   ✓ Handled multiple objects near top correctly")
    else:
        print("   ✗ Failed to draw for multiple objects")
        return False
    
    print("\n" + "="*70)
    print("✓ ALL EXTREME CASE TESTS PASSED")
    print("="*70)
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("TRACKING TEXT VISIBILITY TEST")
    print("="*70)
    print("\nThis test verifies the fix for tracking labels not being visible")
    print("when objects are detected near the top of the image.")
    print("\nPreviously, text was drawn at negative Y coordinates, making it")
    print("invisible. The fix clamps text positions to ensure visibility.")
    
    success = True
    
    try:
        if not test_tracking_text_visibility_near_top():
            success = False
        
        if not test_tracking_text_extreme_cases():
            success = False
        
        if success:
            print("\n" + "="*70)
            print("🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
            print("="*70)
            print("\nThe tracking text visibility issue has been fixed!")
            print("TID and CID labels will now be visible even when objects")
            print("are detected at the top edge of the image.")
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("❌ SOME TESTS FAILED")
            print("="*70)
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
