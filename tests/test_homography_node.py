#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the Homography node.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_homography_node_import():
    """Test that Homography node can be imported"""
    from node.StatsNode.node_homography import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ Homography Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    print(f"  FactoryNode.node_label: {factory.node_label}")
    
    assert factory.node_tag == "Homography"
    assert factory.node_label == "Homography"
    
    return True


def test_homography_calculation():
    """Test homography matrix calculation"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create mock detected keypoints (14 points from tennis court detection)
    # These are in image coordinates
    detected_keypoints = np.array([
        [100, 500],   # doubles_bl
        [700, 500],   # doubles_br
        [700, 50],    # doubles_tr
        [100, 50],    # doubles_tl
        [200, 500],   # singles_bl
        [600, 500],   # singles_br
        [600, 50],    # singles_tr
        [200, 50],    # singles_tl
        [200, 400],   # service_bl
        [600, 400],   # service_br
        [200, 150],   # service_tl
        [600, 150],   # service_tr
        [400, 400],   # center_t_bottom
        [400, 150],   # center_t_top
    ], dtype=np.float32)
    
    # Calculate homography
    H = node._calculate_homography(detected_keypoints)
    
    print("✓ Homography matrix calculated successfully")
    print(f"  Matrix shape: {H.shape if H is not None else 'None'}")
    print(f"  Matrix type: {type(H)}")
    
    assert H is not None
    assert H.shape == (3, 3)
    
    return H


def test_point_transformation():
    """Test transforming points using homography"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create mock detected keypoints
    detected_keypoints = np.array([
        [100, 500],   # doubles_bl
        [700, 500],   # doubles_br
        [700, 50],    # doubles_tr
        [100, 50],    # doubles_tl
        [200, 500],   # singles_bl
        [600, 500],   # singles_br
        [600, 50],    # singles_tr
        [200, 50],    # singles_tl
        [200, 400],   # service_bl
        [600, 400],   # service_br
        [200, 150],   # service_tl
        [600, 150],   # service_tr
        [400, 400],   # center_t_bottom
        [400, 150],   # center_t_top
    ], dtype=np.float32)
    
    # Calculate homography
    H = node._calculate_homography(detected_keypoints)
    
    # Test points to transform (e.g., player positions)
    test_points = np.array([
        [350, 300],  # Player 1
        [450, 200],  # Player 2
    ], dtype=np.float32)
    
    # Transform points
    transformed = node._transform_points(test_points, H)
    
    print("✓ Points transformed successfully")
    print(f"  Input points: {test_points.tolist()}")
    print(f"  Transformed points: {transformed.tolist() if transformed is not None else 'None'}")
    
    assert transformed is not None
    assert transformed.shape == test_points.shape
    
    return transformed


def test_homography_node_update():
    """Test the complete node update logic"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create mock pose estimation output (master keypoints)
    # Note: 'results_list' is the standard output format from PoseEstimation nodes
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
    
    # Create mock points to transform
    points_to_transform_data = {
        'keypoints': [
            {'x': 350, 'y': 300},  # Player 1
            {'x': 450, 'y': 200},  # Player 2
        ]
    }
    
    # Create mock result dictionaries
    node_result_dict = {
        '1:PoseEstimation': master_json_data,
        '2:PointsSource': points_to_transform_data
    }
    
    # Simulate connections
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:PointsSource:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    # Run update
    result = node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    print("✓ Homography node update test passed")
    print(f"  Output has 'json' key: {'json' in result}")
    
    if result['json'] is not None:
        output = result['json']
        print(f"  Output has 'homography_matrix': {'homography_matrix' in output}")
        print(f"  Output has 'template': {'template' in output}")
        print(f"  Output has 'transformed_points': {'transformed_points' in output}")
        print(f"  Output has 'input_points': {'input_points' in output}")
        
        assert 'homography_matrix' in output
        assert 'template' in output
        assert output['homography_matrix'] is not None
        
        if output['transformed_points'] is not None:
            print(f"  Transformed points: {output['transformed_points']}")
    
    return True


def test_tennis_court_template():
    """Test that tennis court template is correctly defined"""
    from node.StatsNode.node_homography import Node
    
    node = Node()
    template = node.TENNIS_COURT_TEMPLATE
    
    print("✓ Tennis court template test")
    print(f"  Units: {template['units']}")
    print(f"  Origin: {template['origin']}")
    print(f"  Number of keypoints: {len(template['keypoints'])}")
    
    assert template['units'] == 'meters'
    assert len(template['keypoints']) == 14
    
    # Check a few key points
    doubles_bl = template['keypoints'][0]
    assert doubles_bl['name'] == 'doubles_bl'
    assert doubles_bl['x'] == 0.00
    assert doubles_bl['y'] == 0.00
    
    print("  Sample keypoint (doubles_bl):", doubles_bl)
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Homography Node")
    print("=" * 60)
    
    try:
        test_homography_node_import()
        print()
        
        test_tennis_court_template()
        print()
        
        test_homography_calculation()
        print()
        
        test_point_transformation()
        print()
        
        test_homography_node_update()
        print()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
