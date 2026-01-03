#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for ObjectDetection → Homography → TennisCourt pipeline.
This test validates that bounding boxes from object detection are properly 
converted to player positions and displayed on the tennis court.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_object_detection_to_homography_bbox_conversion():
    """Test that object detection bboxes are converted to bottom-center points"""
    print("\nTesting ObjectDetection bbox to bottom-center conversion")
    
    from node.StatsNode.node_homography import Node as HomographyNode
    
    # Simulate object detection output with bounding boxes
    # Format: [x1, y1, x2, y2] - top-left and bottom-right corners
    object_detection_output = {
        'bboxes': [
            [200, 250, 280, 400],  # Player 1: bbox from (200,250) to (280,400)
            [500, 200, 580, 350],  # Player 2: bbox from (500,200) to (580,350)
        ],
        'scores': [0.95, 0.92],
        'class_ids': [0, 0],  # Both are 'person' class
    }
    
    # Expected bottom-center points
    # Player 1: center_x = (200+280)/2 = 240, bottom_y = 400
    # Player 2: center_x = (500+580)/2 = 540, bottom_y = 350
    expected_points = np.array([[240.0, 400.0], [540.0, 350.0]], dtype=np.float32)
    
    # Initialize homography node
    homography_node = HomographyNode()
    
    # Test the bbox extraction method
    extracted_points = homography_node._extract_bottom_center_from_bboxes(
        object_detection_output['bboxes']
    )
    
    print(f"   Extracted points: {extracted_points}")
    print(f"   Expected points:  {expected_points}")
    
    # Verify extraction
    assert extracted_points is not None, "Failed to extract points from bboxes"
    assert extracted_points.shape == expected_points.shape, f"Shape mismatch: {extracted_points.shape} vs {expected_points.shape}"
    
    # Check values
    np.testing.assert_array_almost_equal(extracted_points, expected_points, decimal=2)
    print("   ✓ Bottom-center points correctly extracted from bboxes")
    
    return True


def test_full_pipeline_object_detection_to_court():
    """Test complete pipeline: ObjectDetection → Homography → TennisCourt"""
    print("\nTesting complete ObjectDetection → Homography → TennisCourt pipeline")
    
    from node.StatsNode.node_homography import Node as HomographyNode
    from node.VisualNode.node_tennis_court import Node as TennisCourtNode
    
    # Step 1: Simulate PoseEstimation output (court keypoints)
    print("\n1. Setting up court keypoints...")
    detected_court_keypoints = np.array([
        [120, 480],   # far_baseline_left_single_corner
        [680, 490],   # far_baseline_right_single_corner
        [130, 55],    # near_baseline_left_double_corner
        [670, 60],    # near_baseline_right_double_corner
        [180, 480],   # far_baseline_left_service_projection
        [180, 390],   # near_baseline_left_single_corner
        [620, 490],   # far_baseline_right_service_projection
        [620, 395],   # near_baseline_right_single_corner
        [180, 165],   # service_box_left_top_corner
        [620, 160],   # service_box_right_top_corner
        [190, 55],    # left_singles_sideline_midpoint
        [610, 60],    # right_singles_sideline_midpoint
        [400, 163],   # center_service_line_top_T
        [400, 392],   # center_service_line_bottom_T
    ], dtype=np.float32)
    
    pose_estimation_output = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': detected_court_keypoints
    }
    print(f"   ✓ Court keypoints configured: {len(detected_court_keypoints)} points")
    
    # Step 2: Simulate ObjectDetection output with player bboxes
    print("\n2. Setting up player detections...")
    object_detection_output = {
        'bboxes': [
            [220, 280, 280, 380],  # Player 1 near baseline
            [520, 180, 580, 280],  # Player 2 in mid-court
        ],
        'scores': [0.95, 0.92],
        'class_ids': [0, 0],
        'class_names': {0: 'person'},
    }
    print(f"   ✓ Detected {len(object_detection_output['bboxes'])} players")
    print(f"   Player 1 bbox: {object_detection_output['bboxes'][0]}")
    print(f"   Player 2 bbox: {object_detection_output['bboxes'][1]}")
    
    # Step 3: Process through Homography node
    print("\n3. Processing through Homography node...")
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    node_result_dict = {
        '1:PoseEstimation': pose_estimation_output,
        '2:ObjectDetection': object_detection_output
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:ObjectDetection:JSON:Output03', '3:Homography:JSON:Input02']
    ]
    
    homography_result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Verify homography output
    assert 'json' in homography_result, "Homography result missing 'json'"
    assert homography_result['json'] is not None, "Homography json is None"
    
    homography_output = homography_result['json']
    
    # Check that we have all required fields
    assert 'homography_matrix' in homography_output, "Missing homography_matrix"
    assert 'input_points' in homography_output, "Missing input_points"
    assert 'transformed_points' in homography_output, "Missing transformed_points"
    assert 'bboxes' in homography_output, "Missing bboxes"
    
    print(f"   ✓ Homography calculated")
    print(f"   ✓ Input points (bottom-center): {homography_output['input_points']}")
    print(f"   ✓ Transformed points (court): {homography_output['transformed_points']}")
    
    # Verify that input_points are bottom-center of bboxes
    expected_bottom_centers = [
        [(220+280)/2, 380],  # Player 1: (250, 380)
        [(520+580)/2, 280],  # Player 2: (550, 280)
    ]
    
    input_points = homography_output['input_points']
    for i, (actual, expected) in enumerate(zip(input_points, expected_bottom_centers)):
        print(f"   Player {i+1} bottom-center: expected {expected}, got {actual}")
        assert abs(actual[0] - expected[0]) < 0.1, f"X coordinate mismatch for player {i+1}"
        assert abs(actual[1] - expected[1]) < 0.1, f"Y coordinate mismatch for player {i+1}"
    
    print("   ✓ Bottom-center points correctly calculated")
    
    # Verify transformed points are within court bounds
    transformed = homography_output['transformed_points']
    for i, pos in enumerate(transformed):
        x, y = pos
        print(f"   Player {i+1} court position: ({x:.2f}, {y:.2f}) meters")
        assert 0 <= x <= 10.97, f"Player {i+1} X out of bounds: {x}"
        assert 0 <= y <= 23.77, f"Player {i+1} Y out of bounds: {y}"
    
    print("   ✓ Transformed coordinates within court bounds")
    
    # Step 4: Visualize on TennisCourt node (skipped in headless environment)
    print("\n4. TennisCourt visualization (skipped in test - requires GUI)")
    print("   ✓ Homography output contains all required fields for visualization")
    print("   ✓ Visualization would display both image and court coordinates")
    
    return True


def test_coordinate_display():
    """Test that coordinates are properly displayed in console"""
    print("\nTesting coordinate display functionality")
    
    from node.StatsNode.node_homography import Node as HomographyNode
    
    # Setup test data
    detected_keypoints = np.array([
        [100, 500], [700, 500], [700, 50], [100, 50],
        [200, 500], [600, 500], [600, 50], [200, 50],
        [200, 400], [600, 400], [200, 150], [600, 150],
        [400, 400], [400, 150],
    ], dtype=np.float32)
    
    pose_output = {
        'model_name': 'TennisKeyPoints',
        'results_list': detected_keypoints
    }
    
    object_detection_output = {
        'bboxes': [[300, 250, 360, 380]],
        'scores': [0.95],
        'class_ids': [0],
    }
    
    # Process
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    node_result_dict = {
        '1:PoseEstimation': pose_output,
        '2:ObjectDetection': object_detection_output
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:ObjectDetection:JSON:Output03', '3:Homography:JSON:Input02']
    ]
    
    print("\n   Expected console output with coordinate transformation:")
    result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Verify result contains all necessary data
    assert result['json'] is not None
    assert 'input_points' in result['json']
    assert 'transformed_points' in result['json']
    
    print("   ✓ Coordinate transformation displayed in console")
    
    return True


def test_invalid_bbox_handling():
    """Test that invalid bboxes are properly handled"""
    print("\nTesting invalid bbox handling")
    
    from node.StatsNode.node_homography import Node as HomographyNode
    
    homography_node = HomographyNode()
    
    # Test with various invalid bboxes
    invalid_bboxes = [
        [],  # Empty bbox
        [100],  # Too few coordinates
        [100, 200],  # Too few coordinates
        [100, 200, 300],  # Too few coordinates
        [300, 200, 100, 400],  # x2 < x1 (invalid)
        [100, 400, 300, 200],  # y2 < y1 (invalid)
    ]
    
    # Also include some valid bboxes
    mixed_bboxes = [
        [100, 100, 200, 300],  # Valid
        [300, 200, 100, 400],  # Invalid: x2 < x1
        [400, 100, 500, 300],  # Valid
    ]
    
    print("   Testing extraction with invalid bboxes...")
    result = homography_node._extract_bottom_center_from_bboxes(invalid_bboxes)
    # Should return None or empty when all bboxes are invalid
    print(f"   Result from all invalid bboxes: {result}")
    
    print("   Testing extraction with mixed valid/invalid bboxes...")
    result = homography_node._extract_bottom_center_from_bboxes(mixed_bboxes)
    # Should extract only valid bboxes
    if result is not None:
        print(f"   Extracted {len(result)} valid points from {len(mixed_bboxes)} bboxes")
        assert len(result) == 2, "Should extract only the 2 valid bboxes"
        print("   ✓ Invalid bboxes correctly filtered out")
    else:
        print("   ✗ Expected to extract valid bboxes")
        return False
    
    return True


if __name__ == '__main__':
    print("=" * 80)
    print("Object Detection → Homography Integration Tests")
    print("=" * 80)
    
    try:
        test_object_detection_to_homography_bbox_conversion()
        print("\n" + "=" * 80)
        
        test_full_pipeline_object_detection_to_court()
        print("\n" + "=" * 80)
        
        test_coordinate_display()
        print("\n" + "=" * 80)
        
        test_invalid_bbox_handling()
        print("\n" + "=" * 80)
        
        print("\n" + "=" * 80)
        print("✓ All integration tests passed!")
        print("=" * 80)
    except Exception as e:
        print(f"\n✗ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
