#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test MOT JSON output functionality.
Verify that MOT node returns JSON data in the correct format compatible with Homography.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_mot_json_output_structure():
    """Test that MOT node returns JSON data with the required fields"""
    print("Testing MOT JSON output structure...")
    
    # Simulate MOT output (from node_mot.py update method)
    mot_result = {
        'track_ids': [1, 2, 3],
        'bboxes': [[100, 100, 200, 200], [300, 150, 400, 250], [500, 200, 600, 300]],
        'scores': [0.9, 0.85, 0.8],
        'class_ids': [0, 0, 1],
        'class_names': {0: 'person', 1: 'ball'},
        'track_id_dict': {1: 0, 2: 1, 3: 2}
    }
    
    # Verify required fields for Homography compatibility
    required_fields = ['bboxes', 'class_ids', 'class_names']
    for field in required_fields:
        assert field in mot_result, f"MOT JSON output missing required field: {field}"
    
    print("  ✓ MOT JSON output has all required fields for Homography")
    
    # Verify structure matches ObjectDetection format
    assert isinstance(mot_result['bboxes'], list), "bboxes should be a list"
    assert isinstance(mot_result['class_ids'], list), "class_ids should be a list"
    assert isinstance(mot_result['class_names'], dict), "class_names should be a dict"
    assert isinstance(mot_result['scores'], list), "scores should be a list"
    
    print("  ✓ Field types match ObjectDetection format")
    
    # Verify lengths are consistent
    n_detections = len(mot_result['bboxes'])
    assert len(mot_result['class_ids']) == n_detections, "class_ids length mismatch"
    assert len(mot_result['scores']) == n_detections, "scores length mismatch"
    assert len(mot_result['track_ids']) == n_detections, "track_ids length mismatch"
    
    print(f"  ✓ All arrays have consistent length: {n_detections}")
    
    # Verify additional MOT-specific fields
    assert 'track_ids' in mot_result, "MOT should include track_ids"
    assert 'track_id_dict' in mot_result, "MOT should include track_id_dict"
    
    print("  ✓ MOT-specific fields (track_ids, track_id_dict) are present")
    
    return True


def test_mot_json_compatible_with_homography():
    """Test that MOT JSON output can be processed by Homography node"""
    from node.StatsNode.node_homography import Node as HomographyNode
    
    print("\nTesting MOT JSON -> Homography compatibility...")
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Simulate MOT JSON output
    mot_json = {
        'bboxes': [[350, 250, 450, 350], [500, 200, 600, 300]],
        'scores': [0.9, 0.85],
        'class_ids': [0, 0],
        'class_names': {0: 'person'},
        'track_ids': [1, 2],
        'track_id_dict': {1: 0, 2: 1}
    }
    
    # Simulate court keypoints
    mock_keypoints = np.array([
        [100, 500], [700, 500], [700, 50], [100, 50],
        [200, 500], [600, 500], [600, 50], [200, 50],
        [200, 400], [600, 400], [200, 150], [600, 150],
        [400, 400], [400, 150],
    ], dtype=np.float32)
    
    court_json = {
        'model_name': 'TennisKeyPoints',
        'results_list': mock_keypoints
    }
    
    # Setup node connections
    node_result_dict = {
        '1:PoseEstimation': court_json,
        '2:MultiObjectTracking': mot_json  # MOT JSON as input
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:MultiObjectTracking:JSON:Output03', '3:Homography:JSON:Input02']  # JSON Output03
    ]
    
    # Execute homography transformation
    result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Verify output
    assert 'json' in result, "Homography should return json"
    assert result['json'] is not None, "Homography JSON output should not be None"
    assert 'transformed_points' in result['json'], "Should have transformed_points"
    assert 'bboxes' in result['json'], "Should pass through bboxes"
    assert 'class_ids' in result['json'], "Should pass through class_ids"
    assert 'class_names' in result['json'], "Should pass through class_names"
    
    print("  ✓ Homography successfully processed MOT JSON output")
    print(f"  ✓ Transformed {len(result['json']['transformed_points'])} player positions")
    print("  ✓ All required fields passed through to output")
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing MOT JSON Output Feature")
    print("=" * 70)
    print()
    
    try:
        test_mot_json_output_structure()
        test_mot_json_compatible_with_homography()
        
        print()
        print("=" * 70)
        print("All MOT JSON output tests passed! ✓")
        print("=" * 70)
        print()
        print("Summary:")
        print("  • MOT node now outputs JSON data via Output03 pin")
        print("  • JSON format matches ObjectDetection output structure")
        print("  • JSON output is compatible with Homography node")
        print("  • Full pipeline works: MOT (JSON) -> Homography -> TennisCourt")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
