#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the new keypoints data processing and trigger nodes.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_dataprocessing_keypoints_import():
    """Test that DataProcessing Keypoints node can be imported"""
    from node.ProcessNode.node_dataprocessing_keypoints import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ DataProcessing Keypoints Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    print(f"  FactoryNode.node_label: {factory.node_label}")
    
    assert factory.node_tag == "DataProcessingKeypoints"
    assert factory.node_label == "DataProcessing/Keypoints"
    
    return True


def test_trigger_keypoint_deviation_import():
    """Test that Trigger Keypoint Deviation node can be imported"""
    from node.TriggerNode.node_trigger_keypoint_deviation import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ Trigger Keypoint Deviation Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    print(f"  FactoryNode.node_label: {factory.node_label}")
    
    assert factory.node_tag == "TriggerKeypointDeviation"
    assert factory.node_label == "Trigger/KeypointDeviation"
    
    return True


def test_dataprocessing_keypoints_logic():
    """Test the logic of DataProcessing Keypoints node"""
    from node.ProcessNode.node_dataprocessing_keypoints import Node
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create mock data simulating pose estimation output
    mock_keypoints = np.array([[100.0, 200.0], [150.0, 250.0], [200.0, 300.0]])
    mock_json_data = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': mock_keypoints
    }
    
    # Create mock result dict
    node_result_dict = {'1:PoseEstimation': mock_json_data}
    
    # Simulate connection
    connection_list = [['1:PoseEstimation:Json:Output03', '2:DataProcessingKeypoints:Json:Input01']]
    
    # Run update
    result = node.update(
        node_id=2,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    print("✓ DataProcessing Keypoints logic test passed")
    print(f"  Output has 'json' key: {'json' in result}")
    
    if result['json'] is not None:
        print(f"  Output json has 'processed' key: {'processed' in result['json']}")
        print(f"  Output json has 'processing_node' key: {'processing_node' in result['json']}")
        assert result['json']['processed'] == True
        assert result['json']['processing_node'] == 'DataProcessingKeypoints'
    
    return True


def test_trigger_keypoint_deviation_logic():
    """Test the logic of Trigger Keypoint Deviation node (basic structure only)"""
    from node.TriggerNode.node_trigger_keypoint_deviation import Node
    
    node = Node()
    
    print("✓ Trigger Keypoint Deviation node instantiated successfully")
    print(f"  Node has _keypoints_buffer: {hasattr(node, '_keypoints_buffer')}")
    print(f"  Node has _last_trigger_state: {hasattr(node, '_last_trigger_state')}")
    
    assert hasattr(node, '_keypoints_buffer')
    assert hasattr(node, '_last_trigger_state')
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Keypoints Data Processing and Trigger Nodes")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Test imports
    try:
        test_dataprocessing_keypoints_import()
        print()
    except Exception as e:
        print(f"✗ DataProcessing Keypoints import test failed: {e}")
        all_tests_passed = False
    
    try:
        test_trigger_keypoint_deviation_import()
        print()
    except Exception as e:
        print(f"✗ Trigger Keypoint Deviation import test failed: {e}")
        all_tests_passed = False
    
    # Test logic (without dpg)
    try:
        test_dataprocessing_keypoints_logic()
        print()
    except Exception as e:
        print(f"✗ DataProcessing Keypoints logic test failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    try:
        test_trigger_keypoint_deviation_logic()
        print()
    except Exception as e:
        print(f"✗ Trigger Keypoint Deviation logic test failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    print("=" * 60)
    if all_tests_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
    print("=" * 60)
    
    sys.exit(0 if all_tests_passed else 1)
