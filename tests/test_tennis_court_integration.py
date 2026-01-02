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
    
    # Step 2: Test TennisCourt drawing functions directly (without DPG)
    from node.VisualNode.node_tennis_court import Node as TennisCourtNode
    
    tennis_court_node = TennisCourtNode()
    
    # Create blank image
    output_image = np.zeros((800, 600, 3), dtype=np.uint8)
    
    # Get template and transformed points from homography output
    template = homography_result['json']['template']
    transformed_points = homography_result['json']['transformed_points']
    
    # Calculate scale to fit court in image
    scale_x = (600 - 100) / 11.0
    scale_y = (800 - 100) / 24.0
    scale = min(scale_x, scale_y)
    
    # Center the court
    court_width_px = int(10.97 * scale)
    court_length_px = int(23.77 * scale)
    offset_x = (600 - court_width_px) // 2
    offset_y = (800 - court_length_px) // 2
    
    # Draw tennis court
    output_image = tennis_court_node._draw_tennis_court(output_image, template, scale, offset_x, offset_y)
    
    # Draw transformed points
    output_image = tennis_court_node._draw_transformed_points(output_image, transformed_points, scale, offset_x, offset_y)
    
    print("✓ Step 2: TennisCourt visualization created (without DPG)")
    print(f"  Visualization image shape: {output_image.shape}")
    print(f"  Non-zero pixels in visualization: {np.count_nonzero(output_image)}")
    
    # Validate visualization
    assert output_image.shape == (800, 600, 3)
    assert np.count_nonzero(output_image) > 10000
    
    # Step 3: Save visualization for manual inspection
    output_path = '/tmp/tennis_court_visualization_test.png'
    cv2.imwrite(output_path, output_image)
    print(f"✓ Step 3: Visualization saved to {output_path}")
    
    print()
    print("=" * 60)
    print("Integration test PASSED! ✓")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Homography calculated from {len(detected_keypoints)} court keypoints")
    print(f"  - Transformed {len(homography_result['json']['transformed_points'])} player positions")
    print(f"  - Generated {output_image.shape} visualization")
    print(f"  - Drew {len(transformed_points)} transformed points on court")
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
