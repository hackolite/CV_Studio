#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that class exclusion validates against the model's class labels.

This test ensures that when users select class IDs to exclude, the system
validates that those IDs actually exist in the current model's class dictionary.
"""

import numpy as np


def parse_rejected_classes(rejected_classes_str):
    """Helper function to parse rejected classes string.
    
    Args:
        rejected_classes_str: String with rejected classes (e.g., "1: player2, 5")
        
    Returns:
        Set of rejected class IDs
    """
    rejected_classes = set()
    for class_str in rejected_classes_str.split(','):
        class_str = class_str.strip()
        if class_str:
            try:
                if ':' in class_str:
                    class_id_str = class_str.split(':')[0].strip()
                    rejected_classes.add(int(class_id_str))
                else:
                    rejected_classes.add(int(class_str))
            except ValueError:
                pass
    return rejected_classes


def validate_rejected_classes(rejected_classes, class_name_dict):
    """Helper function to validate rejected classes against model's class dictionary.
    
    Args:
        rejected_classes: Set of rejected class IDs
        class_name_dict: Dictionary mapping class IDs to class names
        
    Returns:
        Tuple of (validated_rejected_classes, invalid_classes)
    """
    valid_class_ids = set(class_name_dict.keys())
    invalid_classes = rejected_classes - valid_class_ids
    validated_rejected_classes = rejected_classes & valid_class_ids
    return validated_rejected_classes, invalid_classes


def apply_class_filter(bboxes, scores, class_ids, rejected_classes):
    """Helper function to apply class rejection filter.
    
    Args:
        bboxes: Array of bounding boxes
        scores: Array of scores
        class_ids: Array of class IDs
        rejected_classes: Set of class IDs to reject
        
    Returns:
        Tuple of (filtered_bboxes, filtered_scores, filtered_class_ids)
    """
    if rejected_classes:
        keep_mask = np.array([class_id not in rejected_classes for class_id in class_ids])
        bboxes = bboxes[keep_mask]
        scores = scores[keep_mask]
        class_ids = class_ids[keep_mask]
    return bboxes, scores, class_ids


def test_exclusion_validation_valid_classes():
    """
    Test that valid class IDs are properly accepted and filtered.
    """
    # Simulate model with 3 classes (tennis model)
    class_name_dict = {0: 'player1', 1: 'player2', 2: 'ball'}
    
    # Simulate detections
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]])
    scores = np.array([0.95, 0.85, 0.75])
    class_ids = np.array([0, 1, 2])
    
    # User wants to exclude player2 (class 1) - this is valid
    rejected_classes_str = "1: player2"
    
    # Parse rejected classes
    rejected_classes = parse_rejected_classes(rejected_classes_str)
    
    # Validate rejected classes against model's class dictionary
    rejected_classes, invalid_classes = validate_rejected_classes(rejected_classes, class_name_dict)
    
    # Assert no invalid classes
    assert len(invalid_classes) == 0, f"Should have no invalid classes, but found: {invalid_classes}"
    
    # Apply filtering
    bboxes, scores, class_ids = apply_class_filter(bboxes, scores, class_ids, rejected_classes)
    
    # Verify results
    assert len(bboxes) == 2, "Should have 2 detections after filtering"
    assert 1 not in class_ids, "Class 1 should be excluded"
    assert 0 in class_ids, "Class 0 should remain"
    assert 2 in class_ids, "Class 2 should remain"
    
    print("✅ Test passed: Valid class IDs are properly filtered")


def test_exclusion_validation_invalid_classes():
    """
    Test that invalid class IDs are detected and filtered out.
    """
    # Simulate model with 3 classes (tennis model)
    class_name_dict = {0: 'player1', 1: 'player2', 2: 'ball'}
    
    # Simulate detections
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]])
    scores = np.array([0.95, 0.85, 0.75])
    class_ids = np.array([0, 1, 2])
    
    # User tries to exclude class IDs from a different model (e.g., COCO classes)
    # Class IDs 5 and 10 don't exist in the tennis model
    rejected_classes_str = "1: player2, 5, 10"
    
    # Parse rejected classes
    rejected_classes = parse_rejected_classes(rejected_classes_str)
    
    # Verify that rejected_classes contains both valid and invalid IDs
    assert 1 in rejected_classes, "Should include valid class 1"
    assert 5 in rejected_classes, "Should include invalid class 5"
    assert 10 in rejected_classes, "Should include invalid class 10"
    
    # Validate rejected classes against model's class dictionary
    rejected_classes, invalid_classes = validate_rejected_classes(rejected_classes, class_name_dict)
    
    # Assert that invalid classes are detected
    assert len(invalid_classes) == 2, f"Should have 2 invalid classes, but found: {len(invalid_classes)}"
    assert 5 in invalid_classes, "Class 5 should be invalid"
    assert 10 in invalid_classes, "Class 10 should be invalid"
    
    print(f"⚠️  Detected invalid class IDs: {invalid_classes}")
    print(f"   Valid class IDs for this model: {sorted(class_name_dict.keys())}")
    
    # Now rejected_classes should only contain valid IDs
    assert rejected_classes == {1}, f"Should only contain class 1, but got: {rejected_classes}"
    
    # Apply filtering
    bboxes, scores, class_ids = apply_class_filter(bboxes, scores, class_ids, rejected_classes)
    
    # Verify results - only class 1 should be excluded
    assert len(bboxes) == 2, "Should have 2 detections after filtering"
    assert 1 not in class_ids, "Class 1 should be excluded"
    assert 0 in class_ids, "Class 0 should remain"
    assert 2 in class_ids, "Class 2 should remain"
    
    print("✅ Test passed: Invalid class IDs are detected and filtered out")


def test_exclusion_validation_all_invalid_classes():
    """
    Test that when all rejected class IDs are invalid, no filtering occurs.
    """
    # Simulate model with 3 classes (tennis model)
    class_name_dict = {0: 'player1', 1: 'player2', 2: 'ball'}
    
    # Simulate detections
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]])
    scores = np.array([0.95, 0.85, 0.75])
    class_ids = np.array([0, 1, 2])
    
    # User tries to exclude class IDs that don't exist in the tennis model
    rejected_classes_str = "5, 10, 20"
    
    # Parse rejected classes
    rejected_classes = parse_rejected_classes(rejected_classes_str)
    
    # Validate rejected classes against model's class dictionary
    rejected_classes, invalid_classes = validate_rejected_classes(rejected_classes, class_name_dict)
    
    # Assert that all classes are invalid
    assert len(invalid_classes) == 3, f"Should have 3 invalid classes"
    assert invalid_classes == {5, 10, 20}, f"Wrong invalid classes detected"
    
    print(f"⚠️  All rejected class IDs are invalid: {invalid_classes}")
    
    # Now rejected_classes should be empty
    assert len(rejected_classes) == 0, f"Should have no valid rejected classes"
    
    # Apply filtering (should not filter anything)
    bboxes, scores, class_ids = apply_class_filter(bboxes, scores, class_ids, rejected_classes)
    
    # Verify results - nothing should be filtered
    assert len(bboxes) == 3, "Should still have all 3 detections"
    assert 0 in class_ids, "Class 0 should remain"
    assert 1 in class_ids, "Class 1 should remain"
    assert 2 in class_ids, "Class 2 should remain"
    
    print("✅ Test passed: When all class IDs are invalid, no filtering occurs")


def test_exclusion_validation_coco_to_tennis_switch():
    """
    Test realistic scenario: switching from COCO model to Tennis model.
    """
    # Initially using COCO model (80 classes)
    coco_class_name_dict = {
        0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorbike', 4: 'aeroplane',
        5: 'bus', 10: 'fire hydrant', 20: 'elephant'
        # ... (simplified, normally 80 classes)
    }
    
    # User excludes some COCO classes
    rejected_classes_str = "1: bicycle, 5: bus, 10: fire hydrant"
    
    # Parse rejected classes
    rejected_classes = parse_rejected_classes(rejected_classes_str)
    
    assert rejected_classes == {1, 5, 10}, "Should have parsed COCO class IDs"
    
    # Now user switches to Tennis model (only 3 classes)
    tennis_class_name_dict = {0: 'player1', 1: 'player2', 2: 'ball'}
    
    # The UI should clear the selection when model changes (line 89 in node_object_detection.py)
    # But let's test what happens if the user somehow has the old rejected_classes
    
    # Simulate detections from tennis model
    bboxes = np.array([[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]])
    scores = np.array([0.95, 0.85, 0.75])
    class_ids = np.array([0, 1, 2])
    
    # Validate rejected classes against tennis model
    rejected_classes, invalid_classes = validate_rejected_classes(rejected_classes, tennis_class_name_dict)
    
    # Most classes are invalid for tennis model
    print(f"⚠️  Switching COCO → Tennis: Invalid class IDs: {invalid_classes}")
    assert 5 in invalid_classes, "Class 5 (bus) is invalid for tennis model"
    assert 10 in invalid_classes, "Class 10 (fire hydrant) is invalid for tennis model"
    
    # Only class 1 is valid in both models (bicycle in COCO, player2 in tennis)
    assert rejected_classes == {1}, f"Only class 1 should be valid in tennis model"
    
    # Apply filtering
    bboxes, scores, class_ids = apply_class_filter(bboxes, scores, class_ids, rejected_classes)
    
    # Verify results - only class 1 (player2) should be excluded
    assert len(bboxes) == 2, "Should have 2 detections after filtering"
    assert 1 not in class_ids, "Class 1 (player2) should be excluded"
    assert 0 in class_ids, "Class 0 (player1) should remain"
    assert 2 in class_ids, "Class 2 (ball) should remain"
    
    print("✅ Test passed: Model switch scenario handled correctly")


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Class Exclusion Validation")
    print("=" * 60)
    
    test_exclusion_validation_valid_classes()
    print()
    
    test_exclusion_validation_invalid_classes()
    print()
    
    test_exclusion_validation_all_invalid_classes()
    print()
    
    test_exclusion_validation_coco_to_tennis_switch()
    print()
    
    print("=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
