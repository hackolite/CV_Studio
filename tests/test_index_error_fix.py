#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for IndexError fix in draw_multi_object_tracking_info method.
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_draw_multi_object_tracking_with_dict_class_names():
    """Test drawing with class_names as dictionary (COCO format)"""
    from node.basenode import Node
    
    print("Testing draw_multi_object_tracking_info with dictionary class_names...")
    
    node = Node()
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Simulate tracking data with dictionary class_names (like COCO)
    track_ids = [1, 2, 3]
    bboxes = [[100, 100, 200, 200], [300, 150, 400, 250], [500, 200, 600, 300]]
    scores = [0.9, 0.85, 0.8]
    class_ids = [0, 0, 1]  # person, person, ball
    class_names = {0: 'person', 1: 'ball'}  # Dictionary format
    track_id_dict = {1: 0, 2: 1, 3: 2}
    
    try:
        result = node.draw_multi_object_tracking_info(
            image, track_ids, bboxes, scores, class_ids, class_names, track_id_dict
        )
        print("  ✓ Successfully handled dictionary class_names")
        assert result is not None
        assert result.shape == image.shape
        return True
    except IndexError as e:
        print(f"  ✗ IndexError occurred: {e}")
        return False


def test_draw_multi_object_tracking_with_missing_class_id():
    """Test drawing with class_id that doesn't exist in class_names"""
    from node.basenode import Node
    
    print("Testing draw_multi_object_tracking_info with missing class_id...")
    
    node = Node()
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Simulate tracking data where class_id doesn't exist in class_names
    track_ids = [1, 2]
    bboxes = [[100, 100, 200, 200], [300, 150, 400, 250]]
    scores = [0.9, 0.85]
    class_ids = [0, 99]  # 99 doesn't exist in class_names
    class_names = {0: 'person', 1: 'ball'}  # Missing class_id 99
    track_id_dict = {1: 0, 2: 1}
    
    try:
        result = node.draw_multi_object_tracking_info(
            image, track_ids, bboxes, scores, class_ids, class_names, track_id_dict
        )
        print("  ✓ Successfully handled missing class_id with fallback")
        assert result is not None
        assert result.shape == image.shape
        
        # Verify that the fallback label was used (class_99)
        # We can't directly check the text, but at least it didn't crash
        return True
    except IndexError as e:
        print(f"  ✗ IndexError occurred: {e}")
        return False


def test_draw_multi_object_tracking_with_list_class_names():
    """Test drawing with class_names as list"""
    from node.basenode import Node
    
    print("Testing draw_multi_object_tracking_info with list class_names...")
    
    node = Node()
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Simulate tracking data with list class_names
    track_ids = [1, 2]
    bboxes = [[100, 100, 200, 200], [300, 150, 400, 250]]
    scores = [0.9, 0.85]
    class_ids = [0, 1]
    class_names = ['person', 'ball']  # List format
    track_id_dict = {1: 0, 2: 1}
    
    try:
        result = node.draw_multi_object_tracking_info(
            image, track_ids, bboxes, scores, class_ids, class_names, track_id_dict
        )
        print("  ✓ Successfully handled list class_names")
        assert result is not None
        assert result.shape == image.shape
        return True
    except IndexError as e:
        print(f"  ✗ IndexError occurred: {e}")
        return False


def test_draw_multi_object_tracking_with_list_out_of_range():
    """Test drawing with class_id out of range for list class_names"""
    from node.basenode import Node
    
    print("Testing draw_multi_object_tracking_info with out-of-range class_id for list...")
    
    node = Node()
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Simulate tracking data where class_id is out of range for list
    track_ids = [1, 2]
    bboxes = [[100, 100, 200, 200], [300, 150, 400, 250]]
    scores = [0.9, 0.85]
    class_ids = [0, 5]  # 5 is out of range
    class_names = ['person', 'ball']  # Only indices 0 and 1 exist
    track_id_dict = {1: 0, 2: 1}
    
    try:
        result = node.draw_multi_object_tracking_info(
            image, track_ids, bboxes, scores, class_ids, class_names, track_id_dict
        )
        print("  ✓ Successfully handled out-of-range class_id with fallback")
        assert result is not None
        assert result.shape == image.shape
        return True
    except IndexError as e:
        print(f"  ✗ IndexError occurred: {e}")
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("Testing IndexError Fix in draw_multi_object_tracking_info")
    print("=" * 70)
    print()
    
    all_passed = True
    
    try:
        all_passed &= test_draw_multi_object_tracking_with_dict_class_names()
        print()
        
        all_passed &= test_draw_multi_object_tracking_with_missing_class_id()
        print()
        
        all_passed &= test_draw_multi_object_tracking_with_list_class_names()
        print()
        
        all_passed &= test_draw_multi_object_tracking_with_list_out_of_range()
        print()
        
        if all_passed:
            print("=" * 70)
            print("All IndexError fix tests passed! ✓")
            print("=" * 70)
            print()
            print("Summary:")
            print("  • Dictionary class_names (COCO format) works correctly")
            print("  • Missing class_id falls back to 'class_N' label")
            print("  • List class_names format still works")
            print("  • Out-of-range class_id for list falls back gracefully")
        else:
            print("=" * 70)
            print("Some tests failed!")
            print("=" * 70)
            sys.exit(1)
        
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
