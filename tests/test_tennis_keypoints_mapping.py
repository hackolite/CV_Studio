#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the tennis keypoint mapping is correct between:
1. TennisKeyPoints model output (14 keypoints in specific order)
2. Homography node template (14 keypoints matching model order)
3. TennisCourt visualization node (draws correctly with new names)
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_template_keypoint_order():
    """Verify that the template keypoints match the expected model output order"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    template = node.TENNIS_COURT_TEMPLATE
    
    # Expected keypoint names in order (from problem statement)
    expected_names = [
        "far_baseline_left_single_corner",      # 0
        "far_baseline_right_single_corner",     # 1
        "near_baseline_left_double_corner",     # 2
        "near_baseline_right_double_corner",    # 3
        "far_baseline_left_service_projection", # 4
        "near_baseline_left_single_corner",     # 5
        "far_baseline_right_service_projection",# 6
        "near_baseline_right_single_corner",    # 7
        "service_box_left_top_corner",          # 8
        "service_box_right_top_corner",         # 9
        "left_singles_sideline_midpoint",       # 10
        "right_singles_sideline_midpoint",      # 11
        "center_service_line_top_T",            # 12
        "center_service_line_bottom_T"          # 13
    ]
    
    print("✓ Testing template keypoint order")
    print(f"  Template has {len(template['keypoints'])} keypoints")
    assert len(template['keypoints']) == 14, "Template should have 14 keypoints"
    
    # Verify order matches
    for i, kp in enumerate(template['keypoints']):
        actual_name = kp['name']
        expected_name = expected_names[i]
        print(f"  [{i:2d}] {actual_name:45s} == {expected_name}")
        assert actual_name == expected_name, f"Keypoint {i} mismatch: {actual_name} != {expected_name}"
    
    print("  ✓ All keypoints in correct order")
    return True


def test_template_coordinates():
    """Verify that the template coordinates are correct for a tennis court"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    template = node.TENNIS_COURT_TEMPLATE
    keypoints = template['keypoints']
    
    # Tennis court dimensions
    COURT_WIDTH = 10.97  # Doubles court width
    COURT_LENGTH = 23.77  # Full court length
    SINGLES_MARGIN = 1.37  # Distance from doubles to singles line
    SERVICE_LINE_DIST = 5.485  # Distance from baseline to service line
    
    print("✓ Testing template coordinates")
    
    # Test doubles corners
    assert keypoints[2]['x'] == 0.00 and keypoints[2]['y'] == 0.00, "Near baseline left doubles corner should be at origin"
    assert keypoints[3]['x'] == COURT_WIDTH and keypoints[3]['y'] == 0.00, "Near baseline right doubles corner should be at (10.97, 0)"
    
    # Test singles corners
    assert keypoints[5]['x'] == SINGLES_MARGIN and keypoints[5]['y'] == 0.00, "Near baseline left singles corner"
    assert keypoints[7]['x'] == (COURT_WIDTH - SINGLES_MARGIN) and keypoints[7]['y'] == 0.00, "Near baseline right singles corner"
    assert keypoints[0]['x'] == SINGLES_MARGIN and keypoints[0]['y'] == COURT_LENGTH, "Far baseline left singles corner"
    assert keypoints[1]['x'] == (COURT_WIDTH - SINGLES_MARGIN) and keypoints[1]['y'] == COURT_LENGTH, "Far baseline right singles corner"
    
    # Test service lines
    assert keypoints[8]['y'] == SERVICE_LINE_DIST, "Near service line at 5.485m"
    assert keypoints[9]['y'] == SERVICE_LINE_DIST, "Near service line at 5.485m"
    assert keypoints[4]['y'] == (COURT_LENGTH - SERVICE_LINE_DIST), "Far service line at 18.285m"
    assert keypoints[6]['y'] == (COURT_LENGTH - SERVICE_LINE_DIST), "Far service line at 18.285m"
    
    # Test center points
    assert keypoints[12]['x'] == COURT_WIDTH / 2, "Center T should be at court center X"
    assert keypoints[13]['x'] == COURT_WIDTH / 2, "Center T should be at court center X"
    
    # Test net position (midpoints should be at half court)
    assert keypoints[10]['y'] == COURT_LENGTH / 2, "Left midpoint should be at net (11.885m)"
    assert keypoints[11]['y'] == COURT_LENGTH / 2, "Right midpoint should be at net (11.885m)"
    
    print("  ✓ All coordinates are correct")
    return True


def test_homography_with_correct_mapping():
    """Test homography calculation with correctly ordered keypoints"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create mock detected keypoints in the SAME ORDER as template
    # These would come from TennisKeyPoints model detection
    # Using a simple perspective transformation (camera viewing from one end)
    detected_keypoints = np.array([
        # 0: far_baseline_left_single_corner (far from camera, appears small and high)
        [250, 100],
        # 1: far_baseline_right_single_corner
        [550, 100],
        # 2: near_baseline_left_double_corner (near camera, appears large and low)
        [100, 700],
        # 3: near_baseline_right_double_corner
        [700, 700],
        # 4: far_baseline_left_service_projection
        [250, 200],
        # 5: near_baseline_left_single_corner
        [200, 700],
        # 6: far_baseline_right_service_projection
        [550, 200],
        # 7: near_baseline_right_single_corner
        [600, 700],
        # 8: service_box_left_top_corner
        [200, 500],
        # 9: service_box_right_top_corner
        [600, 500],
        # 10: left_singles_sideline_midpoint
        [220, 350],
        # 11: right_singles_sideline_midpoint
        [580, 350],
        # 12: center_service_line_top_T
        [400, 200],
        # 13: center_service_line_bottom_T
        [400, 500],
    ], dtype=np.float32)
    
    # Calculate homography
    H = node._calculate_homography(detected_keypoints)
    
    print("✓ Testing homography with correct mapping")
    print(f"  Homography matrix calculated: {H is not None}")
    assert H is not None, "Homography matrix should be calculated"
    assert H.shape == (3, 3), "Homography should be 3x3 matrix"
    
    # Test that we can transform a point
    # Test point at approximate center of court in image
    test_point = np.array([[400, 350]], dtype=np.float32)
    transformed = node._transform_points(test_point, H)
    
    print(f"  Test point transformed: {transformed is not None}")
    assert transformed is not None, "Point transformation should work"
    
    # The transformed point should be somewhere near the center of the court
    # Center of court is approximately (5.485, 11.885)
    x, y = transformed[0]
    print(f"  Transformed center point: ({x:.2f}, {y:.2f}) meters")
    print(f"  Expected near: (5.485, 11.885) meters")
    
    # Allow some tolerance since this is with mock data
    assert 0 <= x <= 11, f"Transformed X should be within court width: {x}"
    assert 0 <= y <= 24, f"Transformed Y should be within court length: {y}"
    
    print("  ✓ Homography calculation works correctly")
    return True


def test_visualization_with_new_names():
    """Test that TennisCourt visualization node can draw with new keypoint names"""
    from node.VisualNode.node_tennis_court import Node
    from node.StatsNode.node_homography import Node as HomographyNode
    
    tennis_court_node = Node()
    homography_node = HomographyNode()
    
    # Get the template
    template = homography_node.TENNIS_COURT_TEMPLATE
    
    # Create blank image
    image = np.zeros((800, 600, 3), dtype=np.uint8)
    
    # Try to draw the court
    result_image = tennis_court_node._draw_tennis_court(image, template, scale=20, offset_x=100, offset_y=50)
    
    print("✓ Testing TennisCourt visualization with new keypoint names")
    print(f"  Image shape: {result_image.shape}")
    print(f"  Non-zero pixels: {np.count_nonzero(result_image)}")
    
    assert result_image.shape == image.shape, "Output image should have same shape"
    assert np.count_nonzero(result_image) > 0, "Court should be drawn (non-zero pixels)"
    
    # The image should have court lines drawn
    # Green background should be present
    green_pixels = np.sum((result_image[:,:,0] == 0) & (result_image[:,:,1] == 150) & (result_image[:,:,2] == 0))
    print(f"  Green court pixels: {green_pixels}")
    assert green_pixels > 0, "Court should have green background"
    
    print("  ✓ Court visualization works with new keypoint names")
    return True


def test_end_to_end_pipeline():
    """Test the complete pipeline from model output to visualization"""
    from node.StatsNode.node_homography import Node as HomographyNode
    from node.VisualNode.node_tennis_court import Node as TennisCourtNode
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    tennis_court_node = TennisCourtNode()
    tennis_court_node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Simulate TennisKeyPoints model output
    detected_keypoints = np.array([
        [250, 100], [550, 100], [100, 700], [700, 700],
        [250, 200], [200, 700], [550, 200], [600, 700],
        [200, 500], [600, 500], [220, 350], [580, 350],
        [400, 200], [400, 500],
    ], dtype=np.float32)
    
    # Simulate PoseEstimation output format
    pose_output = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': detected_keypoints
    }
    
    # Simulate some player positions to transform
    player_positions = np.array([[400, 450], [350, 300]], dtype=np.float32)
    points_data = {'points': player_positions.tolist()}
    
    # Test homography node
    node_result_dict = {
        '1:PoseEstimation': pose_output,
        '2:PlayerDetection': points_data
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:PlayerDetection:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    homography_result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    print("✓ Testing end-to-end pipeline")
    print(f"  Homography output: {homography_result['json'] is not None}")
    assert homography_result['json'] is not None, "Homography should produce output"
    
    homography_output = homography_result['json']
    assert 'homography_matrix' in homography_output, "Output should have homography matrix"
    assert 'template' in homography_output, "Output should have template"
    assert 'transformed_points' in homography_output, "Output should have transformed points"
    
    print(f"  Homography matrix: {homography_output['homography_matrix'] is not None}")
    print(f"  Transformed points: {homography_output['transformed_points']}")
    
    # Test TennisCourt node with homography output
    tennis_result_dict = {'3:Homography': homography_output}
    tennis_connection_list = [['3:Homography:JSON:Output01', '4:TennisCourt:JSON:Input01']]
    
    tennis_result = tennis_court_node.update(
        node_id=4,
        connection_list=tennis_connection_list,
        node_image_dict={},
        node_result_dict=tennis_result_dict,
        node_audio_dict={}
    )
    
    print(f"  TennisCourt visualization: {tennis_result['image'] is not None}")
    assert tennis_result['image'] is not None, "TennisCourt should produce image"
    assert np.count_nonzero(tennis_result['image']) > 0, "Court should be drawn"
    
    print("  ✓ Complete pipeline works correctly")
    return True


if __name__ == '__main__':
    print("=" * 80)
    print("Testing Tennis Keypoints Mapping")
    print("=" * 80)
    print()
    
    try:
        test_template_keypoint_order()
        print()
        
        test_template_coordinates()
        print()
        
        test_homography_with_correct_mapping()
        print()
        
        test_visualization_with_new_names()
        print()
        
        test_end_to_end_pipeline()
        print()
        
        print("=" * 80)
        print("All mapping tests passed! ✓")
        print("=" * 80)
        print()
        print("Summary:")
        print("  ✓ Template keypoints match TennisKeyPoints model output order")
        print("  ✓ Template coordinates are correct for tennis court")
        print("  ✓ Homography calculation works with correct mapping")
        print("  ✓ TennisCourt visualization draws correctly with new names")
        print("  ✓ Complete pipeline (PoseEstimation → Homography → TennisCourt) works")
        print()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
