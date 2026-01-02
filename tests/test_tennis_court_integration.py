#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for TennisCourt node with Homography node.
Tests the complete data flow without DPG GUI.
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_complete_integration():
    """Test complete data flow from Homography to TennisCourt visualization"""
    from node.StatsNode.node_homography import Node as HomographyNode
    from node.VisualNode.node_tennis_court import Node as TennisCourtNode
    
    print("Testing complete integration pipeline")
    print("-" * 60)
    
    # Step 1: Setup Homography node
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create mock detected keypoints (court corners/lines in image space)
    detected_keypoints = np.array([
        [100, 500], [700, 500], [700, 50], [100, 50],
        [200, 500], [600, 500], [600, 50], [200, 50],
        [200, 400], [600, 400], [200, 150], [600, 150],
        [400, 400], [400, 150],
    ], dtype=np.float32)
    
    master_json_data = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': detected_keypoints
    }
    
    # Create mock player positions (in image space)
    points_to_transform_data = {
        'keypoints': [
            {'x': 350, 'y': 300},  # Player 1
            {'x': 450, 'y': 200},  # Player 2
        ]
    }
    
    node_result_dict = {
        '1:PoseEstimation': master_json_data,
        '2:PointsSource': points_to_transform_data
    }
    
    connection_list_homography = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:PointsSource:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    # Execute Homography node
    homography_result = homography_node.update(
        node_id=3,
        connection_list=connection_list_homography,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    print("✓ Step 1: Homography node executed")
    print(f"  Homography matrix calculated: {homography_result['json']['homography_matrix'] is not None}")
    print(f"  Transformed points available: {homography_result['json']['transformed_points'] is not None}")
    print(f"  Number of transformed points: {len(homography_result['json']['transformed_points'])}")
    
    # Validate Homography output
    assert homography_result['json'] is not None
    assert 'transformed_points' in homography_result['json']
    assert 'template' in homography_result['json']
    assert len(homography_result['json']['transformed_points']) == 2
    
    # Step 2: Setup TennisCourt node
    tennis_court_node = TennisCourtNode()
    tennis_court_node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    node_result_dict_tennis = {
        '3:Homography': homography_result['json']
    }
    
    connection_list_tennis = [
        ['3:Homography:JSON:Output01', '4:TennisCourt:JSON:Input01']
    ]
    
    # Execute TennisCourt node
    tennis_court_result = tennis_court_node.update(
        node_id=4,
        connection_list=connection_list_tennis,
        node_image_dict={},
        node_result_dict=node_result_dict_tennis,
        node_audio_dict={}
    )
    
    print("✓ Step 2: TennisCourt visualization node executed")
    print(f"  Visualization image created: {tennis_court_result['image'] is not None}")
    print(f"  Image shape: {tennis_court_result['image'].shape if tennis_court_result['image'] is not None else 'None'}")
    print(f"  JSON output available: {tennis_court_result['json'] is not None}")
    
    # Validate TennisCourt output
    assert tennis_court_result['image'] is not None
    assert tennis_court_result['json'] is not None
    assert tennis_court_result['image'].shape == (800, 600, 3)
    
    # Check JSON output structure
    output_json = tennis_court_result['json']
    assert 'template' in output_json
    assert 'transformed_points' in output_json
    assert 'visualization' in output_json
    assert 'scale' in output_json['visualization']
    assert 'offset_x' in output_json['visualization']
    assert 'offset_y' in output_json['visualization']
    
    print(f"  Visualization metadata: scale={output_json['visualization']['scale']:.2f}, " +
          f"offset=({output_json['visualization']['offset_x']}, {output_json['visualization']['offset_y']})")
    
    # Check that the image has content (court and points drawn)
    non_zero = np.count_nonzero(tennis_court_result['image'])
    print(f"  Non-zero pixels in visualization: {non_zero}")
    assert non_zero > 10000  # Should have court lines and points
    
    # Step 3: Save visualization for manual inspection
    output_path = '/tmp/tennis_court_visualization_test.png'
    cv2.imwrite(output_path, tennis_court_result['image'])
    print(f"✓ Step 3: Visualization saved to {output_path}")
    
    print()
    print("=" * 60)
    print("Integration test PASSED! ✓")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Homography calculated from {len(detected_keypoints)} court keypoints")
    print(f"  - Transformed {len(homography_result['json']['transformed_points'])} player positions")
    print(f"  - Generated {tennis_court_result['image'].shape} visualization")
    print(f"  - Passed {len(homography_result['json']['transformed_points'])} transformed points through")
    print()
    
    return True


if __name__ == '__main__':
    try:
        test_complete_integration()
    except Exception as e:
        print(f"\n✗ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
