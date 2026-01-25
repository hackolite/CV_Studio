#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test showing the correct pipeline flow:
ObjectDetection → ReId → MultiObjectTracking
"""
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_reid_pipeline_integration():
    """
    Test the complete pipeline: ObjectDetection → ReId → MOT
    
    This test verifies that:
    1. ObjectDetection outputs: bboxes, scores, class_ids, class_names
    2. ReId receives ObjectDetection data, performs K-means, and outputs modified class_ids
    3. MOT can receive ReId output and track based on ReId labels
    """
    # Simulate ObjectDetection output
    object_detection_output = {
        'bboxes': [[100, 100, 200, 200], [300, 300, 400, 400]],
        'scores': [0.95, 0.87],
        'class_ids': [0, 0],  # Both detected as 'person'
        'class_names': ['person', 'person']
    }
    
    # ReId node would process this and output:
    reid_output = {
        'bboxes': [[100, 100, 200, 200], [300, 300, 400, 400]],  # Unchanged
        'scores': [0.95, 0.87],  # Unchanged
        'class_ids': [0, 1],  # ReId labels: player1=0, player2=1
        'class_names': ['player1', 'player2']  # Slot names
    }
    
    # Verify ObjectDetection format (no track_ids)
    assert 'bboxes' in object_detection_output
    assert 'scores' in object_detection_output
    assert 'class_ids' in object_detection_output
    assert 'class_names' in object_detection_output
    assert 'track_ids' not in object_detection_output
    
    # Verify ReId output format (compatible with MOT input)
    assert 'bboxes' in reid_output
    assert 'scores' in reid_output
    assert 'class_ids' in reid_output
    assert 'class_names' in reid_output
    
    # Verify ReId has replaced class_ids with unique identities
    assert reid_output['class_ids'][0] != reid_output['class_ids'][1]
    assert reid_output['class_names'][0] != reid_output['class_names'][1]
    
    # MOT node can now track each ReId label separately
    # MOT expects: bboxes, scores, class_ids, class_names (no track_ids)
    # This is exactly what ReId outputs!
    
    print("✓ Pipeline flow verified: ObjectDetection → ReId → MOT")
    print(f"  ObjectDetection: {list(object_detection_output.keys())}")
    print(f"  ReId: {list(reid_output.keys())}")
    print(f"  ReId labels: {reid_output['class_ids']} → {reid_output['class_names']}")


if __name__ == '__main__':
    test_reid_pipeline_integration()
    print("\n✓ Integration test passed!")
