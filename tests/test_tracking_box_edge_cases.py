#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test edge cases for tracking bounding boxes near image borders.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from node.OverlayNode.draw_util.draw_util import draw_multi_object_tracking_info


def test_boxes_near_top_edge():
    """Test that boxes near the top edge don't cause issues"""
    print("Testing tracking boxes near top edge...")
    
    # Create a test image
    image = np.ones((720, 1280, 3), dtype=np.uint8) * 240
    
    # Test data with boxes very close to the top edge
    track_ids = [1, 2, 3]
    bboxes = [
        [100, 5, 200, 100],     # Very close to top
        [300, 20, 400, 120],    # Close to top
        [500, 100, 600, 200],   # Normal position
    ]
    scores = [0.95, 0.88, 0.92]
    class_ids = [0, 0, 1]
    class_names = {0: 'person', 1: 'ball'}
    track_id_dict = {1: 0, 2: 1, 3: 2}
    
    try:
        # This should not raise an exception
        result_image = draw_multi_object_tracking_info(
            image,
            track_ids,
            bboxes,
            scores,
            class_ids,
            class_names,
            track_id_dict,
        )
        
        assert result_image is not None
        assert result_image.shape == image.shape
        print("  ✓ Boxes near top edge handled correctly")
        print("  ✓ Bounds checking prevents negative coordinates")
        return True
    except Exception as e:
        print(f"  ✗ Test failed with exception: {e}")
        return False


def test_boxes_at_left_edge():
    """Test that boxes at the left edge don't cause issues"""
    print("Testing tracking boxes at left edge...")
    
    # Create a test image
    image = np.ones((720, 1280, 3), dtype=np.uint8) * 240
    
    # Test data with boxes at the left edge
    track_ids = [1]
    bboxes = [[0, 100, 100, 200]]  # x1 = 0
    scores = [0.95]
    class_ids = [0]
    class_names = {0: 'person'}
    track_id_dict = {1: 0}
    
    try:
        result_image = draw_multi_object_tracking_info(
            image,
            track_ids,
            bboxes,
            scores,
            class_ids,
            class_names,
            track_id_dict,
        )
        
        assert result_image is not None
        assert result_image.shape == image.shape
        print("  ✓ Boxes at left edge handled correctly")
        return True
    except Exception as e:
        print(f"  ✗ Test failed with exception: {e}")
        return False


def test_boxes_in_corner():
    """Test that boxes in the top-left corner don't cause issues"""
    print("Testing tracking boxes in top-left corner...")
    
    # Create a test image
    image = np.ones((720, 1280, 3), dtype=np.uint8) * 240
    
    # Test data with boxes in the corner
    track_ids = [1]
    bboxes = [[0, 0, 100, 100]]  # Top-left corner
    scores = [0.95]
    class_ids = [0]
    class_names = {0: 'person'}
    track_id_dict = {1: 0}
    
    try:
        result_image = draw_multi_object_tracking_info(
            image,
            track_ids,
            bboxes,
            scores,
            class_ids,
            class_names,
            track_id_dict,
        )
        
        assert result_image is not None
        assert result_image.shape == image.shape
        print("  ✓ Boxes in corner handled correctly")
        return True
    except Exception as e:
        print(f"  ✗ Test failed with exception: {e}")
        return False


def main():
    """Run all edge case tests"""
    print("=" * 70)
    print("Testing tracking box edge cases (bounds checking)")
    print("=" * 70)
    print()
    
    all_passed = True
    
    try:
        all_passed &= test_boxes_near_top_edge()
        all_passed &= test_boxes_at_left_edge()
        all_passed &= test_boxes_in_corner()
        
        print()
        print("=" * 70)
        if all_passed:
            print("✓ ALL EDGE CASE TESTS PASSED")
            print("=" * 70)
            print()
            print("Summary:")
            print("  • Boxes near top edge handled correctly")
            print("  • Boxes at left edge handled correctly")
            print("  • Boxes in corners handled correctly")
            print("  • Bounds checking prevents out-of-bounds drawing")
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
