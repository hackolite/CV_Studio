#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for MOT -> Homography pipeline.

Verifies that only displayed bounding boxes from the tracker are sent to homography.
Tests the fix for: "vérifie que seules données affichées (boundings box), par le tracker, sont envoyées à l'homographie"
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.TrackerNode.node_mot import Node as MOTNode
from node.StatsNode.node_homography import Node as HomographyNode


def test_mot_sends_only_when_bboxes_displayed():
    """
    Test that MOT node only sends data when bboxes are actually displayed.
    """
    print("\n" + "="*70)
    print("Integration Test: MOT only sends displayed bboxes to Homography")
    print("="*70)
    
    # Initialize MOT node
    mot_node = MOTNode()
    mot_node._opencv_setting_dict = {
        'process_width': 640,
        'process_height': 480,
        'use_pref_counter': False
    }
    
    # Test case 1: Tracking enabled with valid detections (should display and send)
    print("\nTest Case 1: Tracking enabled with valid detections")
    print("-" * 70)
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    node_result_dict = {
        '1:ObjectDetection': {
            'bboxes': [[100, 100, 200, 200], [300, 150, 400, 250]],
            'scores': [0.9, 0.85],
            'class_ids': [0, 0],
            'class_names': {0: 'person'}
        }
    }
    
    connection_list = [
        ['1:ObjectDetection:IMAGE:Output01', '2:MultiObjectTracking:IMAGE:Input01']
    ]
    
    result = mot_node.update(
        node_id=2,
        connection_list=connection_list,
        node_image_dict={'1:ObjectDetection': frame},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    assert 'json' in result, "Should return json"
    assert 'bboxes' in result['json'], "Should have bboxes in output"
    assert len(result['json']['bboxes']) > 0, "Should have non-empty bboxes"
    print(f"  ✓ MOT sent {len(result['json']['bboxes'])} bboxes to downstream (displayed on screen)")
    
    # Test case 2: Tracking enabled but NO detections (should NOT send data)
    print("\nTest Case 2: Tracking enabled but NO detections")
    print("-" * 70)
    
    node_result_dict_empty = {
        '1:ObjectDetection': {
            'bboxes': [],
            'scores': [],
            'class_ids': [],
            'class_names': {}
        }
    }
    
    result_empty = mot_node.update(
        node_id=2,
        connection_list=connection_list,
        node_image_dict={'1:ObjectDetection': frame},
        node_result_dict=node_result_dict_empty,
        node_audio_dict={}
    )
    
    assert 'json' in result_empty, "Should return json"
    # After fix: should be empty dict when no bboxes to display
    assert result_empty['json'] == {} or len(result_empty['json'].get('bboxes', [])) == 0, \
        "Should send empty result when no bboxes to display"
    print(f"  ✓ MOT sent empty result (no bboxes displayed on screen)")
    
    # Test case 3: Tracking disabled (should NOT send data)
    print("\nTest Case 3: Tracking disabled")
    print("-" * 70)
    
    node_result_dict_with_stop = {
        '1:ObjectDetection': {
            'bboxes': [[100, 100, 200, 200]],
            'scores': [0.9],
            'class_ids': [0],
            'class_names': {0: 'person'}
        },
        '0:TriggerNode': False  # Tracking disabled
    }
    
    connection_list_with_stop = [
        ['1:ObjectDetection:IMAGE:Output01', '2:MultiObjectTracking:IMAGE:Input01'],
        ['0:TriggerNode:JSON:Output01', '2:MultiObjectTracking:JSON:Input03']
    ]
    
    result_disabled = mot_node.update(
        node_id=2,
        connection_list=connection_list_with_stop,
        node_image_dict={'1:ObjectDetection': frame},
        node_result_dict=node_result_dict_with_stop,
        node_audio_dict={}
    )
    
    assert 'json' in result_disabled, "Should return json"
    assert result_disabled['json'] == {}, "Should send empty result when tracking disabled"
    print(f"  ✓ MOT sent empty result (tracking disabled, nothing displayed)")
    
    print("\n" + "="*70)
    print("✓ All integration tests passed!")
    print("="*70)
    return True


def test_homography_handles_empty_mot_output():
    """
    Test that homography correctly handles empty output from MOT.
    """
    print("\n" + "="*70)
    print("Integration Test: Homography handles empty MOT output")
    print("="*70)
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Setup court keypoints (required for homography calculation)
    mock_keypoints = np.array([
        [100, 500], [700, 500], [700, 50], [100, 50],
        [200, 500], [600, 500], [600, 50], [200, 50],
        [200, 400], [600, 400], [200, 150], [600, 150],
        [400, 400], [400, 150],
    ], dtype=np.float32)
    
    court_json_data = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': mock_keypoints
    }
    
    # Test case 1: Empty MOT output (no bboxes)
    print("\nTest Case 1: Empty MOT output")
    print("-" * 70)
    
    empty_mot_output = {}  # What MOT now sends when no bboxes to display
    
    node_result_dict = {
        '1:PoseEstimation': court_json_data,
        '2:MultiObjectTracking': empty_mot_output
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:MultiObjectTracking:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    assert 'json' in result, "Should return json"
    # Homography should handle empty input gracefully
    if result['json'] is not None:
        assert result['json'].get('transformed_points') is None or \
               len(result['json'].get('transformed_points', [])) == 0, \
               "Should not transform points when input is empty"
    print("  ✓ Homography correctly handled empty MOT output (no crash, no phantom data)")
    
    # Test case 2: MOT output with actual bboxes
    print("\nTest Case 2: MOT output with actual bboxes")
    print("-" * 70)
    
    mot_output_with_data = {
        'bboxes': [[350, 250, 450, 350], [500, 200, 600, 300]],
        'scores': [0.9, 0.85],
        'class_ids': [0, 0],
        'class_names': {0: 'person'},
        'track_ids': [1, 2],
        'track_id_dict': {1: 0, 2: 1}
    }
    
    node_result_dict_with_data = {
        '1:PoseEstimation': court_json_data,
        '2:MultiObjectTracking': mot_output_with_data
    }
    
    result_with_data = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict_with_data,
        node_audio_dict={}
    )
    
    assert 'json' in result_with_data, "Should return json"
    assert result_with_data['json'] is not None, "Should have output"
    assert 'transformed_points' in result_with_data['json'], "Should have transformed_points"
    assert len(result_with_data['json']['transformed_points']) == 2, \
        "Should transform 2 points (2 bboxes)"
    print(f"  ✓ Homography transformed {len(result_with_data['json']['transformed_points'])} points")
    
    print("\n" + "="*70)
    print("✓ All homography integration tests passed!")
    print("="*70)
    return True


if __name__ == '__main__':
    print("="*70)
    print("Integration Tests: MOT Display/Send Synchronization")
    print("="*70)
    
    try:
        test_mot_sends_only_when_bboxes_displayed()
        test_homography_handles_empty_mot_output()
        
        print("\n" + "="*70)
        print("ALL INTEGRATION TESTS PASSED! ✓")
        print("="*70)
        print()
        print("Verification Summary:")
        print("  ✓ MOT only sends data when bboxes are displayed on screen")
        print("  ✓ Empty bbox lists result in empty output to homography")
        print("  ✓ Homography correctly handles empty MOT output")
        print("  ✓ Full pipeline works with actual tracking data")
        print()
        print("Issue resolved: 'vérifie que seules données affichées")
        print("                (bounding boxes), par le tracker, sont")
        print("                envoyées à l\\'homographie'")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
