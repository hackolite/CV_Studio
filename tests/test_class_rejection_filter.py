#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for class rejection filter in object detection
Tests the functionality of filtering out (rejecting) specific classes from detection results
"""
import numpy as np


def parse_rejected_classes(rejected_classes_str):
    """Parse the rejected classes string into a set of integers"""
    rejected_classes = set()
    if rejected_classes_str and rejected_classes_str.strip():
        for class_str in rejected_classes_str.split(','):
            class_str = class_str.strip()
            if class_str:
                try:
                    rejected_classes.add(int(class_str))
                except ValueError:
                    # Skip invalid class IDs
                    pass
    return rejected_classes


def apply_class_rejection_filter(bboxes, scores, class_ids, rejected_classes):
    """Apply class rejection filter to detection results"""
    if len(bboxes) == 0 or not rejected_classes:
        return bboxes, scores, class_ids
    
    keep_mask = np.array([class_id not in rejected_classes for class_id in class_ids])
    return bboxes[keep_mask], scores[keep_mask], class_ids[keep_mask]


def test_parse_rejected_classes_single():
    """Test parsing a single rejected class"""
    result = parse_rejected_classes("0")
    assert result == {0}


def test_parse_rejected_classes_multiple():
    """Test parsing multiple rejected classes"""
    result = parse_rejected_classes("0,1,2")
    assert result == {0, 1, 2}


def test_parse_rejected_classes_with_spaces():
    """Test parsing with spaces around commas"""
    result = parse_rejected_classes("0, 1, 2")
    assert result == {0, 1, 2}


def test_parse_rejected_classes_empty():
    """Test parsing empty string"""
    result = parse_rejected_classes("")
    assert result == set()


def test_parse_rejected_classes_invalid():
    """Test parsing with invalid values"""
    result = parse_rejected_classes("0,invalid,2")
    assert result == {0, 2}


def test_parse_rejected_classes_with_extra_commas():
    """Test parsing with extra commas"""
    result = parse_rejected_classes("0,,2,")
    assert result == {0, 2}


def test_filter_no_rejection():
    """Test filter with no rejected classes"""
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80]])
    scores = np.array([0.9, 0.8])
    class_ids = np.array([0, 1])
    
    filtered_bboxes, filtered_scores, filtered_class_ids = apply_class_rejection_filter(
        bboxes, scores, class_ids, set()
    )
    
    assert len(filtered_bboxes) == 2
    assert len(filtered_scores) == 2
    assert len(filtered_class_ids) == 2


def test_filter_reject_single_class():
    """Test rejecting a single class"""
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]])
    scores = np.array([0.9, 0.8, 0.7])
    class_ids = np.array([0, 1, 2])
    
    # Reject class 1
    filtered_bboxes, filtered_scores, filtered_class_ids = apply_class_rejection_filter(
        bboxes, scores, class_ids, {1}
    )
    
    assert len(filtered_bboxes) == 2
    assert len(filtered_scores) == 2
    assert len(filtered_class_ids) == 2
    assert 1 not in filtered_class_ids
    assert np.array_equal(filtered_class_ids, [0, 2])


def test_filter_reject_multiple_classes():
    """Test rejecting multiple classes"""
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120], [130, 140, 150, 160]])
    scores = np.array([0.9, 0.8, 0.7, 0.6])
    class_ids = np.array([0, 1, 2, 3])
    
    # Reject classes 0 and 2
    filtered_bboxes, filtered_scores, filtered_class_ids = apply_class_rejection_filter(
        bboxes, scores, class_ids, {0, 2}
    )
    
    assert len(filtered_bboxes) == 2
    assert len(filtered_scores) == 2
    assert len(filtered_class_ids) == 2
    assert 0 not in filtered_class_ids
    assert 2 not in filtered_class_ids
    assert np.array_equal(filtered_class_ids, [1, 3])


def test_filter_reject_all_classes():
    """Test rejecting all classes"""
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80]])
    scores = np.array([0.9, 0.8])
    class_ids = np.array([0, 1])
    
    # Reject both classes
    filtered_bboxes, filtered_scores, filtered_class_ids = apply_class_rejection_filter(
        bboxes, scores, class_ids, {0, 1}
    )
    
    assert len(filtered_bboxes) == 0
    assert len(filtered_scores) == 0
    assert len(filtered_class_ids) == 0


def test_filter_empty_detections():
    """Test filter with empty detections"""
    bboxes = np.array([]).reshape(0, 4)  # Empty array with shape (0, 4)
    scores = np.array([])
    class_ids = np.array([])
    
    filtered_bboxes, filtered_scores, filtered_class_ids = apply_class_rejection_filter(
        bboxes, scores, class_ids, {0, 1}
    )
    
    assert len(filtered_bboxes) == 0
    assert len(filtered_scores) == 0
    assert len(filtered_class_ids) == 0


def test_filter_preserves_order():
    """Test that filter preserves the order of detections"""
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]])
    scores = np.array([0.9, 0.8, 0.7])
    class_ids = np.array([2, 0, 1])
    
    # Reject class 0
    filtered_bboxes, filtered_scores, filtered_class_ids = apply_class_rejection_filter(
        bboxes, scores, class_ids, {0}
    )
    
    assert len(filtered_bboxes) == 2
    # Should preserve order: class 2 first, then class 1
    assert np.array_equal(filtered_class_ids, [2, 1])
    assert np.array_equal(filtered_scores, [0.9, 0.7])


def test_filter_with_duplicate_classes():
    """Test filter when multiple detections have the same class"""
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]])
    scores = np.array([0.9, 0.8, 0.7])
    class_ids = np.array([0, 0, 1])
    
    # Reject class 0 (should remove both instances)
    filtered_bboxes, filtered_scores, filtered_class_ids = apply_class_rejection_filter(
        bboxes, scores, class_ids, {0}
    )
    
    assert len(filtered_bboxes) == 1
    assert len(filtered_scores) == 1
    assert len(filtered_class_ids) == 1
    assert filtered_class_ids[0] == 1


def test_end_to_end_scenario():
    """Test a complete end-to-end scenario"""
    # Simulate detections: 2 persons (0), 1 car (2), 1 bicycle (1)
    bboxes = np.array([
        [10, 20, 30, 40],   # person
        [50, 60, 70, 80],   # person
        [90, 100, 110, 120], # car
        [130, 140, 150, 160] # bicycle
    ])
    scores = np.array([0.95, 0.85, 0.75, 0.65])
    class_ids = np.array([0, 0, 2, 1])
    
    # User wants to reject persons (class 0)
    rejected_str = "0"
    rejected_classes = parse_rejected_classes(rejected_str)
    
    filtered_bboxes, filtered_scores, filtered_class_ids = apply_class_rejection_filter(
        bboxes, scores, class_ids, rejected_classes
    )
    
    # Should only have car and bicycle
    assert len(filtered_bboxes) == 2
    assert 0 not in filtered_class_ids
    assert 2 in filtered_class_ids
    assert 1 in filtered_class_ids


if __name__ == '__main__':
    # Run all tests
    test_parse_rejected_classes_single()
    print("✓ test_parse_rejected_classes_single passed")
    
    test_parse_rejected_classes_multiple()
    print("✓ test_parse_rejected_classes_multiple passed")
    
    test_parse_rejected_classes_with_spaces()
    print("✓ test_parse_rejected_classes_with_spaces passed")
    
    test_parse_rejected_classes_empty()
    print("✓ test_parse_rejected_classes_empty passed")
    
    test_parse_rejected_classes_invalid()
    print("✓ test_parse_rejected_classes_invalid passed")
    
    test_parse_rejected_classes_with_extra_commas()
    print("✓ test_parse_rejected_classes_with_extra_commas passed")
    
    test_filter_no_rejection()
    print("✓ test_filter_no_rejection passed")
    
    test_filter_reject_single_class()
    print("✓ test_filter_reject_single_class passed")
    
    test_filter_reject_multiple_classes()
    print("✓ test_filter_reject_multiple_classes passed")
    
    test_filter_reject_all_classes()
    print("✓ test_filter_reject_all_classes passed")
    
    test_filter_empty_detections()
    print("✓ test_filter_empty_detections passed")
    
    test_filter_preserves_order()
    print("✓ test_filter_preserves_order passed")
    
    test_filter_with_duplicate_classes()
    print("✓ test_filter_with_duplicate_classes passed")
    
    test_end_to_end_scenario()
    print("✓ test_end_to_end_scenario passed")
    
    print("\n✅ All tests passed!")
