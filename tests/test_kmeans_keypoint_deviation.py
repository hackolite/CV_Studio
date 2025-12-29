#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the K-means based keypoint deviation trigger node.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_kmeans_trigger_basic():
    """Test basic K-means trigger node functionality"""
    from node.TriggerNode.node_trigger_keypoint_deviation import Node
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Mock dpg functions
    def mock_dpg_get_value(tag):
        if 'Input02Value' in tag or 'Threshold' in tag:
            return 100.0
        elif 'SampleCountValue' in tag or 'SampleCount' in tag:
            return "100"
        return 100.0  # Default fallback
    
    def mock_dpg_set_value(tag, value):
        pass
    
    # Replace dpg functions
    import node.TriggerNode.node_trigger_keypoint_deviation as module
    original_get = module.dpg_get_value
    original_set = module.dpg_set_value
    module.dpg_get_value = mock_dpg_get_value
    module.dpg_set_value = mock_dpg_set_value
    
    try:
        # Create two clusters of keypoints - one stable (court), one variable (out-of-play)
        # Court cluster: keypoints around (100, 100)
        court_keypoints = []
        for i in range(60):
            kp = np.array([[100.0 + np.random.randn()*5, 100.0 + np.random.randn()*5],
                          [150.0 + np.random.randn()*5, 150.0 + np.random.randn()*5]])
            court_keypoints.append(kp)
        
        # Out-of-play cluster: keypoints with high variation
        out_keypoints = []
        for i in range(40):
            kp = np.array([[200.0 + np.random.randn()*50, 200.0 + np.random.randn()*50],
                          [250.0 + np.random.randn()*50, 250.0 + np.random.randn()*50]])
            out_keypoints.append(kp)
        
        # Mix them together
        all_training = court_keypoints + out_keypoints
        np.random.shuffle(all_training)
        
        # Simulate connections
        connection_list = [['1:PoseEstimation:Json:Output03', '2:TriggerKeypointDeviation:Json:Input01']]
        
        # Phase 1: Training phase - feed 100 samples
        print("Phase 1: Training K-means with 100 samples...")
        for i, keypoints in enumerate(all_training):
            mock_json_data = {
                'model_name': 'TennisKeyPoints',
                'score_th': 0.3,
                'results_list': keypoints
            }
            node_result_dict = {'1:PoseEstimation': mock_json_data}
            
            result = node.update(
                node_id=2,
                connection_list=connection_list,
                node_image_dict={},
                node_result_dict=node_result_dict,
                node_audio_dict={}
            )
            
            if i == 0:
                assert 'json' in result
                assert result['json'] is not None
                assert 'kmeans_info' in result['json']
                assert result['json']['kmeans_info']['training_complete'] == False
            
            if i == 99:
                # Training should be complete after 100 samples
                assert result['json']['kmeans_info']['training_complete'] == True
                assert 'court_cluster_id' in result['json']['kmeans_info']
                print(f"  Training complete. Court cluster ID: {result['json']['kmeans_info']['court_cluster_id']}")
                print(f"  Variance cluster 0: {result['json']['kmeans_info']['variance_cluster_0']:.2f}")
                print(f"  Variance cluster 1: {result['json']['kmeans_info']['variance_cluster_1']:.2f}")
        
        assert node._training_complete == True
        assert node._kmeans_model is not None
        assert node._court_cluster_id is not None
        
        print("✓ Training phase completed successfully")
        
        # Phase 2: Test classification
        print("\nPhase 2: Testing classification...")
        
        # Test with court keypoint (should not trigger)
        court_kp = np.array([[100.0, 100.0], [150.0, 150.0]])
        mock_json_data = {
            'model_name': 'TennisKeyPoints',
            'score_th': 0.3,
            'results_list': court_kp
        }
        node_result_dict = {'1:PoseEstimation': mock_json_data}
        
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        assert 'json' in result
        assert result['json'] is not None
        assert 'BOOL' in result['json']
        assert 'kmeans_info' in result['json']
        
        print(f"  Court keypoint - BOOL: {result['json']['BOOL']}, is_court: {result['json']['kmeans_info']['is_court']}")
        
        # Test with out-of-play keypoint (should trigger)
        out_kp = np.array([[200.0, 200.0], [250.0, 250.0]])
        mock_json_data = {
            'model_name': 'TennisKeyPoints',
            'score_th': 0.3,
            'results_list': out_kp
        }
        node_result_dict = {'1:PoseEstimation': mock_json_data}
        
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        assert 'json' in result
        assert result['json'] is not None
        assert 'BOOL' in result['json']
        assert 'kmeans_info' in result['json']
        
        print(f"  Out-of-play keypoint - BOOL: {result['json']['BOOL']}, is_court: {result['json']['kmeans_info']['is_court']}")
        
        print("✓ Classification phase completed successfully")
        
        return True
        
    finally:
        # Restore original functions
        module.dpg_get_value = original_get
        module.dpg_set_value = original_set


def test_json_bool_format():
    """Test that the trigger returns JSON with BOOL field as per standard"""
    from node.TriggerNode.node_trigger_keypoint_deviation import Node
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Mock dpg functions
    def mock_dpg_get_value(tag):
        if 'Input02Value' in tag or 'Threshold' in tag:
            return 100.0
        elif 'SampleCountValue' in tag or 'SampleCount' in tag:
            return "50"
        return 100.0  # Default fallback
    
    def mock_dpg_set_value(tag, value):
        pass
    
    # Replace dpg functions
    import node.TriggerNode.node_trigger_keypoint_deviation as module
    original_get = module.dpg_get_value
    original_set = module.dpg_set_value
    module.dpg_get_value = mock_dpg_get_value
    module.dpg_set_value = mock_dpg_set_value
    
    try:
        # Create training data
        training_data = []
        for i in range(50):
            kp = np.array([[100.0 + np.random.randn()*10, 100.0 + np.random.randn()*10],
                          [150.0 + np.random.randn()*10, 150.0 + np.random.randn()*10]])
            training_data.append(kp)
        
        connection_list = [['1:PoseEstimation:Json:Output03', '2:TriggerKeypointDeviation:Json:Input01']]
        
        # Train
        for keypoints in training_data:
            mock_json_data = {
                'model_name': 'TennisKeyPoints',
                'score_th': 0.3,
                'results_list': keypoints
            }
            node_result_dict = {'1:PoseEstimation': mock_json_data}
            
            result = node.update(
                node_id=2,
                connection_list=connection_list,
                node_image_dict={},
                node_result_dict=node_result_dict,
                node_audio_dict={}
            )
        
        # Now test a classification
        test_kp = np.array([[100.0, 100.0], [150.0, 150.0]])
        mock_json_data = {
            'model_name': 'TennisKeyPoints',
            'score_th': 0.3,
            'results_list': test_kp
        }
        node_result_dict = {'1:PoseEstimation': mock_json_data}
        
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        # Verify JSON BOOL format
        assert 'json' in result
        assert result['json'] is not None
        assert 'BOOL' in result['json'], "Output JSON must contain 'BOOL' field"
        assert isinstance(result['json']['BOOL'], bool), "BOOL field must be a boolean"
        
        print("✓ JSON BOOL format test passed")
        print(f"  Output JSON contains BOOL: {result['json']['BOOL']}")
        
        return True
        
    finally:
        # Restore original functions
        module.dpg_get_value = original_get
        module.dpg_set_value = original_set


if __name__ == '__main__':
    print("=" * 60)
    print("Testing K-means Keypoint Deviation Trigger")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Test K-means functionality
    try:
        test_kmeans_trigger_basic()
        print()
    except Exception as e:
        print(f"✗ K-means trigger basic test failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    # Test JSON BOOL format
    try:
        test_json_bool_format()
        print()
    except Exception as e:
        print(f"✗ JSON BOOL format test failed: {e}")
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
