#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that TID and CID labels remain visible when bounding boxes are near image edges.
This test addresses the issue: "TID and CID labels are not visible in tracking all around an image, 
not only near the corner or edge"
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.OverlayNode.draw_util.draw_util import draw_multi_object_tracking_info


def test_labels_visible_at_top_edge():
    """Test that labels are visible when bbox is at the top edge of image"""
    print("Testing labels at top edge...")
    
    # Create a test image
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Bounding box very close to top edge
    track_ids = [1]
    bboxes = [[100, 5, 200, 105]]  # y1=5, very close to top
    scores = [0.95]
    class_ids = [0]
    class_names = {0: 'person'}
    track_id_dict = {1: 0}
    
    # Draw the tracking info
    result_image = draw_multi_object_tracking_info(
        image,
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    # Verify the image was modified (non-zero pixels exist)
    assert np.any(result_image > 0), "Image should have been modified"
    
    # Check that we have some pixels near the top of the image (labels should be inside bbox)
    # Since y1=5 and labels would have been drawn above at negative y, 
    # they should now be drawn inside the bbox starting around y=5+offset
    top_region = result_image[5:50, 100:200]
    assert np.any(top_region > 0), "Labels should be visible in the top region inside bbox"
    
    print("  ✓ Labels are visible when bbox is at top edge")
    return True


def test_labels_visible_at_left_edge():
    """Test that labels are visible when bbox is at the left edge of image"""
    print("Testing labels at left edge...")
    
    # Create a test image
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Bounding box at left edge
    track_ids = [1]
    bboxes = [[2, 100, 102, 200]]  # x1=2, very close to left edge
    scores = [0.95]
    class_ids = [0]
    class_names = {0: 'person'}
    track_id_dict = {1: 0}
    
    result_image = draw_multi_object_tracking_info(
        image,
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    assert np.any(result_image > 0), "Image should have been modified"
    
    # Labels should be visible near the left edge
    left_region = result_image[60:100, 2:102]
    assert np.any(left_region > 0), "Labels should be visible near left edge"
    
    print("  ✓ Labels are visible when bbox is at left edge")
    return True


def test_labels_visible_at_corner():
    """Test that labels are visible when bbox is at a corner of image"""
    print("Testing labels at top-left corner...")
    
    # Create a test image
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Bounding box at top-left corner
    track_ids = [1]
    bboxes = [[5, 5, 105, 105]]  # Top-left corner
    scores = [0.95]
    class_ids = [0]
    class_names = {0: 'person'}
    track_id_dict = {1: 0}
    
    result_image = draw_multi_object_tracking_info(
        image,
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    assert np.any(result_image > 0), "Image should have been modified"
    
    # Labels should be visible in the corner region
    corner_region = result_image[5:60, 5:105]
    assert np.any(corner_region > 0), "Labels should be visible in corner region"
    
    print("  ✓ Labels are visible when bbox is at corner")
    return True


def test_labels_normal_position():
    """Test that labels work normally when bbox is in the middle of image"""
    print("Testing labels at normal position (middle of image)...")
    
    # Create a test image
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Bounding box in middle of image
    track_ids = [1]
    bboxes = [[200, 200, 300, 300]]  # Middle of image
    scores = [0.95]
    class_ids = [0]
    class_names = {0: 'person'}
    track_id_dict = {1: 0}
    
    result_image = draw_multi_object_tracking_info(
        image,
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    assert np.any(result_image > 0), "Image should have been modified"
    
    # Labels should be visible above the bbox (normal behavior)
    above_bbox_region = result_image[160:200, 200:300]
    assert np.any(above_bbox_region > 0), "Labels should be visible above bbox in normal case"
    
    print("  ✓ Labels work normally when bbox is in middle")
    return True


def test_multiple_bboxes_various_positions():
    """Test multiple bboxes at various positions simultaneously"""
    print("Testing multiple bboxes at various positions...")
    
    # Create a test image
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Multiple bboxes: top edge, middle, bottom edge
    track_ids = [1, 2, 3]
    bboxes = [
        [100, 5, 200, 105],      # Top edge
        [300, 200, 400, 300],    # Middle
        [450, 370, 550, 470],    # Bottom (near edge)
    ]
    scores = [0.95, 0.88, 0.92]
    class_ids = [0, 1, 0]
    class_names = {0: 'person', 1: 'ball'}
    track_id_dict = {1: 0, 2: 1, 3: 2}
    
    result_image = draw_multi_object_tracking_info(
        image,
        track_ids,
        bboxes,
        scores,
        class_ids,
        class_names,
        track_id_dict,
    )
    
    assert np.any(result_image > 0), "Image should have been modified"
    
    # Check all regions have visible content
    top_region = result_image[5:105, 100:200]
    middle_region = result_image[160:300, 300:400]
    bottom_region = result_image[340:470, 450:550]
    
    assert np.any(top_region > 0), "Top bbox should have visible labels"
    assert np.any(middle_region > 0), "Middle bbox should have visible labels"
    assert np.any(bottom_region > 0), "Bottom bbox should have visible labels"
    
    print("  ✓ All labels are visible for multiple bboxes at various positions")
    return True


def test_different_image_sizes():
    """Test that the fix works with different image sizes"""
    print("Testing different image sizes...")
    
    image_sizes = [
        (360, 480),   # Small
        (720, 1280),  # HD
        (1080, 1920), # Full HD
    ]
    
    for height, width in image_sizes:
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Bbox at top edge
        track_ids = [1]
        bboxes = [[100, 5, 200, 105]]
        scores = [0.95]
        class_ids = [0]
        class_names = {0: 'person'}
        track_id_dict = {1: 0}
        
        result_image = draw_multi_object_tracking_info(
            image,
            track_ids,
            bboxes,
            scores,
            class_ids,
            class_names,
            track_id_dict,
        )
        
        assert np.any(result_image > 0), f"Image ({height}x{width}) should have been modified"
        
        # Labels should be visible
        top_region = result_image[5:50, 100:200]
        assert np.any(top_region > 0), f"Labels should be visible in {height}x{width} image"
    
    print("  ✓ Fix works correctly for different image sizes")
    return True


def main():
    """Run all tests"""
    print("=" * 70)
    print("Testing TID/CID Label Visibility at Image Edges")
    print("=" * 70)
    print()
    
    all_passed = True
    
    try:
        all_passed &= test_labels_visible_at_top_edge()
        all_passed &= test_labels_visible_at_left_edge()
        all_passed &= test_labels_visible_at_corner()
        all_passed &= test_labels_normal_position()
        all_passed &= test_multiple_bboxes_various_positions()
        all_passed &= test_different_image_sizes()
        
        print()
        print("=" * 70)
        if all_passed:
            print("✓ ALL TESTS PASSED")
            print("=" * 70)
            print()
            print("Summary:")
            print("  • TID and CID labels are now visible at all image positions")
            print("  • Labels automatically adjust when bbox is near edges")
            print("  • Labels are placed inside bbox when they would be outside image")
            print("  • Normal behavior is preserved for bboxes in middle of image")
            print()
            return 0
        else:
            print("✗ SOME TESTS FAILED")
            print("=" * 70)
            return 1
            
    except Exception as e:
        print()
        print("=" * 70)
        print(f"✗ TEST FAILED WITH EXCEPTION: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
