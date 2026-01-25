#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that when MOT tracking is stopped (tracking_enabled = False):
1. MOT outputs empty result (no tracking data)
2. Homography receives empty data and doesn't transform points
3. Tennis court displays empty (no players)
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_mot_stop_outputs_empty_result():
    """Test that MOT outputs empty result when tracking is stopped"""
    from node.TrackerNode.node_mot import Node as MOTNode
    
    print("Testing MOT stop state outputs empty result...")
    
    # Create MOT node
    mot_node = MOTNode()
    mot_node._opencv_setting_dict = {'use_pref_counter': False, 'process_width': 640, 'process_height': 480}
    
    # Create test frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Simulate detection data from object detection
    detection_data = {
        'bboxes': [[100, 100, 200, 200], [300, 150, 400, 250]],
        'scores': [0.9, 0.85],
        'class_ids': [0, 0],
        'class_names': {0: 'person'}
    }
    
    # Simulate tracking disabled (stop state)
    tracking_control = {'enabled': False}
    
    # Setup node connections and data
    node_image_dict = {
        '1:ObjectDetection': test_frame
    }
    
    node_result_dict = {
        '1:ObjectDetection': detection_data,
        '2:BooleanControl': tracking_control
    }
    
    connection_list = [
        ['1:ObjectDetection:Image:Output01', '3:MultiObjectTracking:Image:Input01'],
        ['2:BooleanControl:JSON:Output01', '3:MultiObjectTracking:JSON:Input03'],
        ['1:ObjectDetection:JSON:Output01', '3:MultiObjectTracking:JSON:Input04']
    ]
    
    # Execute MOT with tracking disabled
    result = mot_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Verify MOT returns empty result
    assert 'json' in result, "MOT should return json"
    json_result = result['json']
    
    # When tracking is stopped, result should be empty (no bboxes, no tracking data)
    assert json_result == {} or len(json_result.get('bboxes', [])) == 0, \
        f"MOT should output empty result when stopped, got: {json_result}"
    
    print("  ✓ MOT outputs empty result when tracking is stopped")
    print(f"  ✓ Result: {json_result}")
    
    return True


def test_mot_stop_homography_no_transform():
    """Test that Homography doesn't transform points when MOT is stopped"""
    from node.TrackerNode.node_mot import Node as MOTNode
    from node.StatsNode.node_homography import Node as HomographyNode
    
    print("\nTesting Homography with MOT stopped...")
    
    # Create nodes
    mot_node = MOTNode()
    mot_node._opencv_setting_dict = {'use_pref_counter': False, 'process_width': 640, 'process_height': 480}
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create test frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Simulate detection data
    detection_data = {
        'bboxes': [[350, 250, 450, 350], [500, 200, 600, 300]],
        'scores': [0.9, 0.85],
        'class_ids': [0, 0],
        'class_names': {0: 'person'}
    }
    
    # Simulate court keypoints (from pose estimation)
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
    
    # Tracking disabled (stop state)
    tracking_control = {'enabled': False}
    
    # Step 1: Run MOT with tracking disabled
    node_image_dict = {
        '1:ObjectDetection': test_frame
    }
    
    node_result_dict = {
        '1:ObjectDetection': detection_data,
        '2:BooleanControl': tracking_control,
        '3:PoseEstimation': court_json_data
    }
    
    mot_connection_list = [
        ['1:ObjectDetection:Image:Output01', '4:MultiObjectTracking:Image:Input01'],
        ['2:BooleanControl:JSON:Output01', '4:MultiObjectTracking:JSON:Input03'],
        ['1:ObjectDetection:JSON:Output01', '4:MultiObjectTracking:JSON:Input04']
    ]
    
    mot_result = mot_node.update(
        node_id=4,
        connection_list=mot_connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Add MOT result to node_result_dict
    node_result_dict['4:MultiObjectTracking'] = mot_result['json']
    
    print(f"  MOT output when stopped: {mot_result['json']}")
    
    # Step 2: Run Homography with MOT output (empty)
    homography_connection_list = [
        ['3:PoseEstimation:JSON:Output03', '5:Homography:JSON:Input01'],
        ['4:MultiObjectTracking:JSON:Output03', '5:Homography:JSON:Input02']
    ]
    
    homography_result = homography_node.update(
        node_id=5,
        connection_list=homography_connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Verify Homography output
    assert 'json' in homography_result, "Homography should return json"
    homography_json = homography_result['json']
    
    print(f"  Homography output: {homography_json}")
    
    # When MOT is stopped (empty output), homography should either:
    # 1. Return None (no output), or
    # 2. Return data with template but no transformed_points
    if homography_json is not None:
        # If homography returns data, it should have template but no transformed_points
        # or transformed_points should be None or empty
        transformed_points = homography_json.get('transformed_points', None)
        assert transformed_points is None or len(transformed_points) == 0, \
            f"Homography should not transform points when MOT is stopped, got: {transformed_points}"
    
    print("  ✓ Homography correctly handles empty MOT output (no points transformed)")
    
    return True


def test_mot_stop_tennis_court_empty():
    """Test that Tennis Court displays empty when MOT is stopped"""
    from node.TrackerNode.node_mot import Node as MOTNode
    from node.StatsNode.node_homography import Node as HomographyNode
    from node.VisualNode.node_tennis_court import Node as TennisCourtNode
    
    print("\nTesting Tennis Court with MOT stopped...")
    
    # Create nodes
    mot_node = MOTNode()
    mot_node._opencv_setting_dict = {'use_pref_counter': False, 'process_width': 640, 'process_height': 480}
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    tennis_node = TennisCourtNode()
    tennis_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create test frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Simulate detection data
    detection_data = {
        'bboxes': [[350, 250, 450, 350], [500, 200, 600, 300]],
        'scores': [0.9, 0.85],
        'class_ids': [0, 0],
        'class_names': {0: 'person'}
    }
    
    # Simulate court keypoints
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
    
    # Step 1: Run with tracking ENABLED first to populate tennis court
    tracking_enabled = {'enabled': True}
    
    node_image_dict = {
        '1:ObjectDetection': test_frame
    }
    
    node_result_dict = {
        '1:ObjectDetection': detection_data,
        '2:BooleanControl': tracking_enabled,
        '3:PoseEstimation': court_json_data
    }
    
    # Run MOT with tracking enabled
    mot_connection_list = [
        ['1:ObjectDetection:Image:Output01', '4:MultiObjectTracking:Image:Input01'],
        ['2:BooleanControl:JSON:Output01', '4:MultiObjectTracking:JSON:Input03'],
        ['1:ObjectDetection:JSON:Output01', '4:MultiObjectTracking:JSON:Input04']
    ]
    
    mot_result_enabled = mot_node.update(
        node_id=4,
        connection_list=mot_connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    node_result_dict['4:MultiObjectTracking'] = mot_result_enabled['json']
    
    # Run Homography
    homography_connection_list = [
        ['3:PoseEstimation:JSON:Output03', '5:Homography:JSON:Input01'],
        ['4:MultiObjectTracking:JSON:Output03', '5:Homography:JSON:Input02']
    ]
    
    homography_result_enabled = homography_node.update(
        node_id=5,
        connection_list=homography_connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    node_result_dict['5:Homography'] = homography_result_enabled['json']
    
    # Run Tennis Court (should show players)
    tennis_connection_list = [
        ['5:Homography:JSON:Output01', '6:TennisCourt:JSON:Input01']
    ]
    
    tennis_result_enabled = tennis_node.update(
        node_id=6,
        connection_list=tennis_connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Verify tennis court has positions
    assert tennis_node._last_positions_by_label, "Tennis court should have player positions when tracking is enabled"
    print(f"  ✓ Tennis court has {len(tennis_node._last_positions_by_label)} player positions when tracking enabled")
    
    # Step 2: Now STOP tracking
    tracking_disabled = {'enabled': False}
    node_result_dict['2:BooleanControl'] = tracking_disabled
    
    # Run MOT with tracking disabled
    mot_result_disabled = mot_node.update(
        node_id=4,
        connection_list=mot_connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    node_result_dict['4:MultiObjectTracking'] = mot_result_disabled['json']
    
    print(f"  MOT output when stopped: {mot_result_disabled['json']}")
    
    # Run Homography with empty MOT output
    homography_result_disabled = homography_node.update(
        node_id=5,
        connection_list=homography_connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    node_result_dict['5:Homography'] = homography_result_disabled['json']
    
    print(f"  Homography output when MOT stopped: {homography_result_disabled['json']}")
    
    # Run Tennis Court with empty/no transformed points
    tennis_result_disabled = tennis_node.update(
        node_id=6,
        connection_list=tennis_connection_list,
        node_image_dict=node_image_dict,
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Verify tennis court cleared positions (no players displayed)
    assert not tennis_node._last_positions_by_label, \
        f"Tennis court should have no player positions when tracking is stopped, got: {tennis_node._last_positions_by_label}"
    
    print("  ✓ Tennis court cleared player positions when tracking stopped")
    print("  ✓ Tennis court displays empty (no players)")
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing MOT Stop State Behavior")
    print("=" * 70)
    print()
    
    try:
        test_mot_stop_outputs_empty_result()
        test_mot_stop_homography_no_transform()
        test_mot_stop_tennis_court_empty()
        
        print()
        print("=" * 70)
        print("All stop state tests passed! ✓")
        print("=" * 70)
        print()
        print("Summary:")
        print("  • MOT outputs empty result when tracking is stopped")
        print("  • Homography doesn't transform points with empty MOT output")
        print("  • Tennis Court clears display when tracking is stopped")
        print("  • Pipeline correctly handles stop state: no players displayed")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
