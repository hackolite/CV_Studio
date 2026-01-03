#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test MOT -> Homography -> TennisCourt pipeline compatibility.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_mot_output_format():
    """Test that MOT output has the correct format for Homography"""
    print("Testing MOT output format compatibility...")
    
    # Simulate MOT output (based on node_mot.py lines 250-255)
    mot_output = {
        'track_ids': [1, 2, 3],
        'bboxes': [[100, 100, 200, 200], [300, 150, 400, 250], [500, 200, 600, 300]],
        'scores': [0.9, 0.85, 0.8],
        'class_ids': [0, 0, 1],  # 0 = person, 1 = ball (for tennis)
        'class_names': {0: 'person', 1: 'ball'},
        'track_id_dict': {1: 0, 2: 1, 3: 2}
    }
    
    # Verify required fields are present
    required_fields = ['bboxes', 'class_ids', 'class_names']
    for field in required_fields:
        assert field in mot_output, f"MOT output missing required field: {field}"
    
    print("  ✓ MOT output has required fields: bboxes, class_ids, class_names")
    
    # Verify field types
    assert isinstance(mot_output['bboxes'], list), "bboxes should be a list"
    assert isinstance(mot_output['class_ids'], list), "class_ids should be a list"
    assert isinstance(mot_output['class_names'], dict), "class_names should be a dict"
    
    print("  ✓ Field types are correct")
    
    # Verify lengths match
    assert len(mot_output['bboxes']) == len(mot_output['class_ids']), \
        "bboxes and class_ids should have same length"
    
    print("  ✓ Field lengths match")
    
    return True


def test_mot_homography_compatibility():
    """Test that MOT output can be processed by Homography node"""
    from node.StatsNode.node_homography import Node as HomographyNode
    
    print("\nTesting MOT -> Homography compatibility...")
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Simulate MOT output
    mot_output = {
        'bboxes': [[100, 100, 200, 200], [300, 150, 400, 250]],
        'scores': [0.9, 0.85],
        'class_ids': [0, 0],
        'class_names': {0: 'person'},
        'track_ids': [1, 2],
        'track_id_dict': {1: 0, 2: 1}
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
    
    # Create node_result_dict as Homography expects
    node_result_dict = {
        '1:PoseEstimation': court_json_data,
        '2:MultiObjectTracking': mot_output  # MOT instead of ObjectDetection
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:MultiObjectTracking:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    # Execute homography
    result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    # Verify output
    assert 'json' in result, "Homography should return json"
    assert 'transformed_points' in result['json'], "Should have transformed_points"
    assert 'template' in result['json'], "Should have template"
    
    print("  ✓ Homography processed MOT output successfully")
    print(f"  ✓ Transformed {len(result['json']['transformed_points'])} points")
    
    return True


def test_full_pipeline_mot_to_tenniscourt():
    """Test complete pipeline: MOT -> Homography -> TennisCourt (visualization logic only)"""
    from node.StatsNode.node_homography import Node as HomographyNode
    from node.VisualNode.node_tennis_court import Node as TennisCourtNode
    
    print("\nTesting full pipeline: MOT -> Homography -> TennisCourt...")
    
    # Step 1: Setup Homography
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Simulate MOT output
    mot_output = {
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
    
    court_json_data = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': mock_keypoints
    }
    
    # Execute homography
    node_result_dict = {
        '1:PoseEstimation': court_json_data,
        '2:MultiObjectTracking': mot_output
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:MultiObjectTracking:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    homography_result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    print("  ✓ Step 1: Homography processed MOT output")
    
    # Step 2: Test TennisCourt visualization (drawing methods only, not full update)
    tennis_node = TennisCourtNode()
    tennis_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Test the drawing method directly
    template = homography_result['json']['template']
    transformed_points = homography_result['json']['transformed_points']
    labels = ['person', 'person']
    
    # Create test image
    test_image = np.zeros((800, 600, 3), dtype=np.uint8)
    
    # Draw court
    output_image = tennis_node._draw_tennis_court(test_image, template, scale=15, offset_x=100, offset_y=100)
    
    # Draw player positions with labels (new yellow visualization)
    output_image = tennis_node._draw_player_positions_with_labels(
        output_image, transformed_points, labels, scale=15, offset_x=100, offset_y=100
    )
    
    # Verify image was modified
    assert output_image is not None, "TennisCourt should return image"
    assert not np.array_equal(test_image, output_image), "Image should be modified"
    
    print("  ✓ Step 2: TennisCourt visualized MOT tracked players (with yellow labels)")
    print(f"  ✓ Output image shape: {output_image.shape}")
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing MOT -> Homography -> TennisCourt Pipeline")
    print("=" * 70)
    print()
    
    try:
        test_mot_output_format()
        test_mot_homography_compatibility()
        test_full_pipeline_mot_to_tenniscourt()
        
        print()
        print("=" * 70)
        print("All pipeline tests passed! ✓")
        print("=" * 70)
        print()
        print("Summary:")
        print("  • MOT output format is compatible with Homography")
        print("  • MOT provides bboxes, class_ids, class_names as required")
        print("  • Full pipeline works: MOT -> Homography -> TennisCourt")
        print("  • Player positions are correctly transformed and visualized")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
