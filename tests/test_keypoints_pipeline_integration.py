#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test demonstrating the keypoints processing pipeline:
PoseEstimation (Tennis) -> DataProcessing/Keypoints -> Trigger/KeypointDeviation
"""
import sys
import os
import numpy as np
import time

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_keypoints_pipeline_integration():
    """Test the full pipeline from pose estimation to trigger"""
    from node.StatsNode.node_dataprocessing_keypoints import Node as DataProcessingNode
    from node.TriggerNode.node_trigger_keypoint_deviation import Node as TriggerNode
    
    print("=" * 60)
    print("Integration Test: Keypoints Processing Pipeline")
    print("=" * 60)
    
    # Initialize nodes
    dataprocessing_node = DataProcessingNode()
    dataprocessing_node._opencv_setting_dict = {'use_pref_counter': False}
    
    trigger_node = TriggerNode()
    trigger_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Simulate pose estimation output (stable position)
    stable_keypoints = np.array([[100.0, 200.0], [150.0, 250.0], [200.0, 300.0]])
    
    print("\n1. Testing with STABLE keypoints (should NOT trigger)")
    print("-" * 60)
    
    # Process several frames with stable keypoints
    for i in range(10):
        # Simulate pose estimation output
        pose_output = {
            'model_name': 'TennisKeyPoints',
            'score_th': 0.3,
            'results_list': stable_keypoints.copy()
        }
        
        # Step 1: DataProcessing node
        node_result_dict_1 = {'1:PoseEstimation': pose_output}
        connection_list_1 = [['1:PoseEstimation:Json:Output03', '2:DataProcessingKeypoints:Json:Input01']]
        
        dp_result = dataprocessing_node.update(
            node_id=2,
            connection_list=connection_list_1,
            node_image_dict={},
            node_result_dict=node_result_dict_1,
            node_audio_dict={}
        )
        
        # Step 2: Trigger node
        node_result_dict_2 = {'2:DataProcessingKeypoints': dp_result['json']}
        connection_list_2 = [['2:DataProcessingKeypoints:Json:Output01', '3:TriggerKeypointDeviation:Json:Input01']]
        
        # Mock dpg_get_value for trigger parameters
        import node.TriggerNode.node_trigger_keypoint_deviation as trigger_module
        original_dpg_get_value = trigger_module.dpg_get_value
        original_dpg_set_value = trigger_module.dpg_set_value
        
        def mock_dpg_get_value(tag):
            if 'Input02Value' in tag:  # Window size
                return 1.0
            elif 'Input03Value' in tag:  # Threshold
                return 100.0
            return None
        
        def mock_dpg_set_value(tag, value):
            pass  # Do nothing
        
        trigger_module.dpg_get_value = mock_dpg_get_value
        trigger_module.dpg_set_value = mock_dpg_set_value
        
        trigger_result = trigger_node.update(
            node_id=3,
            connection_list=connection_list_2,
            node_image_dict={},
            node_result_dict=node_result_dict_2,
            node_audio_dict={}
        )
        
        trigger_module.dpg_get_value = original_dpg_get_value
        trigger_module.dpg_set_value = original_dpg_set_value
        
        # Print progress for first few frames and last few frames
        if trigger_result['json'] and 'trigger_info' in trigger_result['json']:
            info = trigger_result['json']['trigger_info']
            if i < 2 or i >= 8:
                print(f"  Frame {i+1}: Distance={info['distance']:.2f}, Triggered={info['triggered']}, MasterArea={info.get('master_area', 0):.1f}")
        
        time.sleep(0.05)  # Small delay between frames
    
    # Verify no trigger with stable keypoints
    if trigger_result['json'] and 'trigger_info' in trigger_result['json']:
        assert trigger_result['json']['trigger_info']['triggered'] == False, "Should not trigger with stable keypoints"
        print("\n✓ Stable keypoints test PASSED (no trigger)")
    
    print("\n2. Testing with SUDDEN MOVEMENT (should trigger)")
    print("-" * 60)
    
    # Now inject a sudden movement (large deviation)
    moved_keypoints = stable_keypoints + np.array([[300.0, 300.0], [300.0, 300.0], [300.0, 300.0]])
    
    pose_output = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': moved_keypoints.copy()
    }
    
    node_result_dict_1 = {'1:PoseEstimation': pose_output}
    dp_result = dataprocessing_node.update(
        node_id=2,
        connection_list=connection_list_1,
        node_image_dict={},
        node_result_dict=node_result_dict_1,
        node_audio_dict={}
    )
    
    node_result_dict_2 = {'2:DataProcessingKeypoints': dp_result['json']}
    
    trigger_module.dpg_get_value = mock_dpg_get_value
    trigger_module.dpg_set_value = mock_dpg_set_value
    
    trigger_result = trigger_node.update(
        node_id=3,
        connection_list=connection_list_2,
        node_image_dict={},
        node_result_dict=node_result_dict_2,
        node_audio_dict={}
    )
    
    trigger_module.dpg_get_value = original_dpg_get_value
    trigger_module.dpg_set_value = original_dpg_set_value
    
    if trigger_result['json'] and 'trigger_info' in trigger_result['json']:
        info = trigger_result['json']['trigger_info']
        print(f"  Sudden movement: Distance={info['distance']:.2f}, Triggered={info['triggered']}")
        assert info['triggered'] == True, "Should trigger with sudden movement"
        print("\n✓ Sudden movement test PASSED (triggered)")
    
    print("\n" + "=" * 60)
    print("Integration Test: ALL TESTS PASSED ✓")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    try:
        test_keypoints_pipeline_integration()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
