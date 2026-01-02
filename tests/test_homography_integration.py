#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for Homography node with PoseEstimation pipeline.
This test simulates the complete workflow from pose estimation to homography transformation.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_pose_estimation_to_homography_pipeline():
    """Test the complete pipeline from pose estimation to homography transformation"""
    print("Testing PoseEstimation → Homography pipeline")
    
    from node.StatsNode.node_homography import Node as HomographyNode
    
    # Step 1: Simulate PoseEstimation output
    # This simulates the TennisKeyPoints model detecting court lines
    print("\n1. Simulating PoseEstimation output...")
    detected_court_keypoints = np.array([
        [120, 480],   # doubles_bl (bottom-left)
        [680, 490],   # doubles_br (bottom-right)
        [670, 60],    # doubles_tr (top-right)
        [130, 55],    # doubles_tl (top-left)
        [180, 480],   # singles_bl
        [620, 490],   # singles_br
        [610, 60],    # singles_tr
        [190, 55],    # singles_tl
        [180, 390],   # service_bl
        [620, 395],   # service_br
        [190, 165],   # service_tl
        [610, 160],   # service_tr
        [400, 392],   # center_t_bottom
        [400, 163],   # center_t_top
    ], dtype=np.float32)
    
    pose_estimation_output = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': detected_court_keypoints
    }
    print(f"   ✓ Detected {len(detected_court_keypoints)} court keypoints")
    
    # Step 2: Simulate player tracking output
    # This could come from ObjectDetection or MOT node
    print("\n2. Simulating player position tracking...")
    player_positions_image = [
        [250, 350],  # Player 1 position in image
        [550, 250],  # Player 2 position in image
    ]
    
    player_tracking_output = {
        'keypoints': [
            {'id': 1, 'x': player_positions_image[0][0], 'y': player_positions_image[0][1]},
            {'id': 2, 'x': player_positions_image[1][0], 'y': player_positions_image[1][1]},
        ]
    }
    print(f"   ✓ Tracking {len(player_positions_image)} players")
    print(f"   Player 1 image coords: {player_positions_image[0]}")
    print(f"   Player 2 image coords: {player_positions_image[1]}")
    
    # Step 3: Initialize Homography node
    print("\n3. Initializing Homography node...")
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    print("   ✓ Homography node initialized")
    
    # Step 4: Simulate node connections and data flow
    print("\n4. Processing data through Homography node...")
    node_result_dict = {
        '1:PoseEstimation': pose_estimation_output,
        '2:PlayerTracker': player_tracking_output
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:PlayerTracker:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    print("   ✓ Homography processing complete")
    
    # Step 5: Verify output
    print("\n5. Verifying output...")
    assert 'json' in result, "Output missing 'json' key"
    assert result['json'] is not None, "Output json is None"
    
    output = result['json']
    
    # Check required fields
    required_fields = ['homography_matrix', 'template', 'detected_keypoints', 
                      'input_points', 'transformed_points']
    for field in required_fields:
        assert field in output, f"Output missing required field: {field}"
        print(f"   ✓ Field '{field}' present")
    
    # Verify homography matrix
    assert output['homography_matrix'] is not None, "Homography matrix is None"
    H = np.array(output['homography_matrix'])
    assert H.shape == (3, 3), f"Invalid homography matrix shape: {H.shape}"
    print(f"   ✓ Homography matrix calculated: {H.shape}")
    
    # Verify template
    template = output['template']
    assert template['units'] == 'meters', "Invalid template units"
    assert len(template['keypoints']) == 14, f"Expected 14 keypoints, got {len(template['keypoints'])}"
    print(f"   ✓ Template loaded: {len(template['keypoints'])} keypoints in {template['units']}")
    
    # Verify transformed points
    transformed = output['transformed_points']
    assert len(transformed) == len(player_positions_image), "Transformed points count mismatch"
    print(f"   ✓ Transformed {len(transformed)} player positions")
    
    # Display results
    print("\n6. Transformation Results:")
    print("   " + "=" * 70)
    print("   Player Positions:")
    print("   " + "-" * 70)
    for i, (img_pos, world_pos) in enumerate(zip(player_positions_image, transformed)):
        print(f"   Player {i+1}:")
        print(f"     Image coordinates:  ({img_pos[0]:.1f}, {img_pos[1]:.1f}) pixels")
        print(f"     Court coordinates:  ({world_pos[0]:.2f}, {world_pos[1]:.2f}) meters")
    print("   " + "=" * 70)
    
    # Sanity check on coordinates
    # Transformed coordinates should be within tennis court bounds
    for i, pos in enumerate(transformed):
        x, y = pos
        assert 0 <= x <= 10.97, f"Player {i+1} X coordinate out of court bounds: {x}"
        assert 0 <= y <= 23.77, f"Player {i+1} Y coordinate out of court bounds: {y}"
    print("   ✓ All transformed coordinates within court bounds")
    
    return True


def test_homography_with_only_master_input():
    """Test homography node with only master keypoints (no points to transform)"""
    print("\nTesting Homography with only master keypoints...")
    
    from node.StatsNode.node_homography import Node as HomographyNode
    
    detected_keypoints = np.array([
        [100, 500], [700, 500], [700, 50], [100, 50],
        [200, 500], [600, 500], [600, 50], [200, 50],
        [200, 400], [600, 400], [200, 150], [600, 150],
        [400, 400], [400, 150],
    ], dtype=np.float32)
    
    pose_estimation_output = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': detected_keypoints
    }
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    node_result_dict = {
        '1:PoseEstimation': pose_estimation_output,
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
    ]
    
    result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    assert result['json'] is not None
    assert result['json']['homography_matrix'] is not None
    assert result['json']['transformed_points'] is None  # No points to transform
    print("   ✓ Homography calculated without transformation points")
    
    return True


def test_homography_with_ball_tracking():
    """Test homography with ball tracking data"""
    print("\nTesting Homography with ball tracking...")
    
    from node.StatsNode.node_homography import Node as HomographyNode
    
    # Court keypoints
    detected_keypoints = np.array([
        [100, 500], [700, 500], [700, 50], [100, 50],
        [200, 500], [600, 500], [600, 50], [200, 50],
        [200, 400], [600, 400], [200, 150], [600, 150],
        [400, 400], [400, 150],
    ], dtype=np.float32)
    
    pose_estimation_output = {
        'model_name': 'TennisKeyPoints',
        'results_list': detected_keypoints
    }
    
    # Ball positions over time (trajectory)
    ball_trajectory = {
        'points': [
            [300, 280],  # Ball position 1
            [320, 260],  # Ball position 2
            [340, 240],  # Ball position 3
            [360, 220],  # Ball position 4
            [380, 200],  # Ball position 5
        ]
    }
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    node_result_dict = {
        '1:PoseEstimation': pose_estimation_output,
        '2:BallTracker': ball_trajectory
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:BallTracker:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    assert result['json'] is not None
    assert result['json']['homography_matrix'] is not None
    assert result['json']['transformed_points'] is not None
    assert len(result['json']['transformed_points']) == 5
    
    print(f"   ✓ Transformed {len(result['json']['transformed_points'])} ball positions")
    print("   Ball trajectory in court coordinates:")
    for i, pos in enumerate(result['json']['transformed_points']):
        print(f"     Position {i+1}: ({pos[0]:.2f}, {pos[1]:.2f}) meters")
    
    return True


def test_output_format_compatibility():
    """Test that output format is compatible with downstream nodes"""
    print("\nTesting output format compatibility...")
    
    from node.StatsNode.node_homography import Node as HomographyNode
    
    detected_keypoints = np.array([
        [100, 500], [700, 500], [700, 50], [100, 50],
        [200, 500], [600, 500], [600, 50], [200, 50],
        [200, 400], [600, 400], [200, 150], [600, 150],
        [400, 400], [400, 150],
    ], dtype=np.float32)
    
    pose_estimation_output = {
        'model_name': 'TennisKeyPoints',
        'results_list': detected_keypoints
    }
    
    player_positions = {
        'keypoints': [{'x': 350, 'y': 300}]
    }
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    node_result_dict = {
        '1:PoseEstimation': pose_estimation_output,
        '2:PlayerTracker': player_positions
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:PlayerTracker:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Check that output can be serialized (important for JSON export)
    import json
    try:
        json_str = json.dumps(result['json'])
        print("   ✓ Output is JSON serializable")
    except Exception as e:
        print(f"   ✗ Output is NOT JSON serializable: {e}")
        return False
    
    # Check that output has standard node format
    assert 'image' in result, "Missing 'image' in result"
    assert 'json' in result, "Missing 'json' in result"
    assert 'audio' in result, "Missing 'audio' in result"
    print("   ✓ Output follows standard node format")
    
    return True


if __name__ == '__main__':
    print("=" * 80)
    print("Homography Integration Tests")
    print("=" * 80)
    
    try:
        test_pose_estimation_to_homography_pipeline()
        print("\n" + "=" * 80)
        
        test_homography_with_only_master_input()
        print("\n" + "=" * 80)
        
        test_homography_with_ball_tracking()
        print("\n" + "=" * 80)
        
        test_output_format_compatibility()
        print("\n" + "=" * 80)
        
        print("\n" + "=" * 80)
        print("✓ All integration tests passed!")
        print("=" * 80)
    except Exception as e:
        print(f"\n✗ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
