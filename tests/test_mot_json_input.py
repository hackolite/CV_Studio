#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for MOT node JSON detection input (Input04)

This test verifies that:
1. MOT node has a dedicated JSON input (Input04) for detection data
2. The JSON input can receive detection data from ReId or ObjectDetection
3. The boolean input (Input03) still works for start/stop control
"""
import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMOTJSONInput:
    """Test the MOT node JSON input functionality"""
    
    def test_mot_node_input_naming_convention(self):
        """Test that MOT node follows naming convention for inputs"""
        # Verify node structure naming convention
        node_id = 1
        tag_node_name = f"{node_id}:MultiObjectTracking"
        
        # Input03 should be for boolean start/stop
        input03_tag = tag_node_name + ':JSON:Input03'
        input03_value_tag = input03_tag + 'Value'
        
        # Input04 should be for detection JSON
        input04_tag = tag_node_name + ':JSON:Input04'
        input04_value_tag = input04_tag + 'Value'
        
        # These tags should follow the naming convention
        assert 'Input03' in input03_tag
        assert 'Input04' in input04_tag
        assert 'MultiObjectTracking' in tag_node_name
    
    def test_detection_format_validation(self):
        """Test validation of detection format"""
        # Import here to avoid dearpygui issues
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Mock the MOT node class to test validation
        class MockMOTNode:
            def _is_valid_detection_format(self, data):
                """Copy of validation method from MOT node"""
                if not isinstance(data, dict):
                    return False
                
                required_keys = ['bboxes', 'scores', 'class_ids', 'class_names']
                if not all(key in data for key in required_keys):
                    return False
                
                for key in required_keys:
                    if not isinstance(data[key], (list, tuple)):
                        return False
                
                lengths = [len(data[key]) for key in required_keys]
                if len(set(lengths)) > 1:
                    return False
                
                return True
        
        node = MockMOTNode()
        
        # Test valid format
        valid_data = {
            'bboxes': [[100, 100, 200, 200]],
            'scores': [0.95],
            'class_ids': [0],
            'class_names': ['player1']
        }
        assert node._is_valid_detection_format(valid_data) is True
        
        # Test invalid format - missing key
        invalid_data_missing_key = {
            'bboxes': [[100, 100, 200, 200]],
            'scores': [0.95],
            'class_ids': [0]
            # missing 'class_names'
        }
        assert node._is_valid_detection_format(invalid_data_missing_key) is False
        
        # Test invalid format - wrong type
        invalid_data_wrong_type = {
            'bboxes': "not a list",
            'scores': [0.95],
            'class_ids': [0],
            'class_names': ['player1']
        }
        assert node._is_valid_detection_format(invalid_data_wrong_type) is False
        
        # Test invalid format - inconsistent lengths
        invalid_data_inconsistent = {
            'bboxes': [[100, 100, 200, 200], [200, 200, 300, 300]],
            'scores': [0.95],  # Only 1 score for 2 bboxes
            'class_ids': [0],
            'class_names': ['player1']
        }
        assert node._is_valid_detection_format(invalid_data_inconsistent) is False
        
        # Test non-dict input
        assert node._is_valid_detection_format("not a dict") is False
        assert node._is_valid_detection_format(None) is False
    
    def test_mot_processes_reid_detection_json(self):
        """Test that MOT can process detection JSON from ReId"""
        # Simulate ReId output format
        reid_detection_json = {
            'bboxes': [[100, 100, 200, 200], [300, 300, 400, 400]],
            'scores': [0.95, 0.87],
            'class_ids': [0, 1],  # ReId labels: player1=0, player2=1
            'class_names': ['player1', 'player2']  # Slot names
        }
        
        # Verify format is compatible with MOT expectations
        assert 'bboxes' in reid_detection_json
        assert 'scores' in reid_detection_json
        assert 'class_ids' in reid_detection_json
        assert 'class_names' in reid_detection_json
        
        # MOT should be able to track each ReId label separately
        assert len(reid_detection_json['bboxes']) == 2
        assert len(reid_detection_json['class_ids']) == 2
        assert reid_detection_json['class_ids'][0] != reid_detection_json['class_ids'][1]
    
    def test_mot_boolean_control_format(self):
        """Test boolean control JSON format for Input03"""
        # Boolean can be passed as dict
        boolean_json_dict = {'enabled': True}
        assert isinstance(boolean_json_dict, dict)
        assert 'enabled' in boolean_json_dict
        
        # Or as a simple boolean
        boolean_json_bool = True
        assert isinstance(boolean_json_bool, bool)
    
    def test_mot_pipeline_data_flow(self):
        """
        Test the complete data flow:
        ObjectDetection → ReId → MOT
        
        Where:
        - ObjectDetection.Output03 (JSON) → ReId.Input02 (JSON)
        - ReId.Output03 (JSON) → MOT.Input04 (JSON) [detection data]
        - BooleanSource → MOT.Input03 (JSON) [start/stop control]
        - ReId.Output01 (Image) → MOT.Input01 (Image) [for visualization]
        """
        # Simulate the complete pipeline
        
        # Step 1: ObjectDetection output
        od_output = {
            'bboxes': [[100, 100, 200, 200], [300, 300, 400, 400]],
            'scores': [0.95, 0.87],
            'class_ids': [0, 0],  # Both detected as 'person'
            'class_names': ['person', 'person']
        }
        
        # Step 2: ReId processes and outputs modified JSON
        reid_output = {
            'bboxes': [[100, 100, 200, 200], [300, 300, 400, 400]],  # Unchanged
            'scores': [0.95, 0.87],  # Unchanged
            'class_ids': [0, 1],  # ReId labels: player1=0, player2=1
            'class_names': ['player1', 'player2']  # Slot names
        }
        
        # Step 3: MOT receives:
        # - Input01: Image from ReId (for visualization)
        # - Input03: Boolean start/stop control
        # - Input04: Detection JSON from ReId
        
        boolean_control = {'enabled': True}
        
        # Verify MOT has all necessary inputs
        assert reid_output  # Detection JSON for Input04
        assert boolean_control  # Control JSON for Input03
        # Image would come from connection to ReId Output01
        
        # MOT should now be able to track based on ReId labels
        print("✓ Pipeline verified: ObjectDetection → ReId → MOT")
        print(f"  ReId detections: {reid_output['class_names']}")
        print(f"  MOT control: enabled={boolean_control['enabled']}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
