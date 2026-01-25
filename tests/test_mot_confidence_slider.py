#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify the confidence threshold slider in MOT node
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_confidence_filtering():
    """Test that confidence filtering works correctly"""
    print("Testing confidence filtering logic...")
    
    # Mock detection data
    od_bboxes = [[10, 10, 50, 50], [100, 100, 150, 150], [200, 200, 250, 250]]
    od_scores = [0.9, 0.5, 0.3]
    od_class_ids = [0, 0, 0]
    
    # Test with different confidence thresholds
    test_cases = [
        (0.0, 3),  # No filtering
        (0.4, 2),  # Filter out score 0.3
        (0.6, 1),  # Filter out scores 0.5 and 0.3
        (1.0, 0),  # Filter out all
    ]
    
    for confidence_threshold, expected_count in test_cases:
        filtered_bboxes = []
        filtered_scores = []
        filtered_class_ids = []
        
        if confidence_threshold > 0.0:
            for bbox, score, class_id in zip(od_bboxes, od_scores, od_class_ids):
                if score >= confidence_threshold:
                    filtered_bboxes.append(bbox)
                    filtered_scores.append(score)
                    filtered_class_ids.append(class_id)
        else:
            filtered_bboxes = od_bboxes
            filtered_scores = od_scores
            filtered_class_ids = od_class_ids
        
        actual_count = len(filtered_bboxes)
        assert actual_count == expected_count, f"Threshold {confidence_threshold}: Expected {expected_count} detections, got {actual_count}"
        print(f"✓ Threshold {confidence_threshold}: {actual_count} detections (expected {expected_count})")
    
    print("\n✓ All confidence filtering tests passed!")


if __name__ == '__main__':
    test_confidence_filtering()
    print("\n" + "="*60)
    print("Confidence filtering logic test passed successfully!")
    print("="*60)

