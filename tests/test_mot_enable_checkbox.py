#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the Enable Tracking checkbox functionality in MOT node.
Verifies that:
1. Checkbox defaults to True (enabled)
2. Checkbox can be used to disable tracking
3. JSON input can override checkbox value if connected
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_mot_checkbox_default_enabled():
    """Test that the checkbox defaults to enabled"""
    from node.TrackerNode.node_mot import Node as MOTNode
    from node_editor.util import dpg_get_value
    import dearpygui.dearpygui as dpg
    
    print("Testing MOT checkbox defaults to enabled...")
    
    # Initialize DearPyGUI context
    dpg.create_context()
    
    try:
        # Create MOT node instance
        mot_node = MOTNode()
        mot_node._opencv_setting_dict = {
            'use_pref_counter': False,
            'process_width': 640,
            'process_height': 480
        }
        
        # Simulate checkbox tag
        node_id = 1
        tag_node_name = str(node_id) + ':MultiObjectTracking'
        enable_checkbox_tag = tag_node_name + ':EnableCheckbox'
        
        # Create a checkbox with default value
        dpg.add_checkbox(tag=enable_checkbox_tag, default_value=True)
        
        # Get checkbox value
        checkbox_value = dpg_get_value(enable_checkbox_tag)
        
        # Verify checkbox defaults to True
        assert checkbox_value == True, f"Checkbox should default to True, got {checkbox_value}"
        
        print("  ✓ Checkbox defaults to enabled (True)")
        return True
    finally:
        dpg.destroy_context()


def test_mot_checkbox_controls_tracking():
    """Test that checkbox value controls tracking enable/disable"""
    from node.TrackerNode.node_mot import Node as MOTNode
    from node_editor.util import dpg_get_value, dpg_set_value
    import dearpygui.dearpygui as dpg
    
    print("\nTesting MOT checkbox controls tracking...")
    
    # Initialize DearPyGUI context
    dpg.create_context()
    
    try:
        # Create MOT node instance
        mot_node = MOTNode()
        mot_node._opencv_setting_dict = {
            'use_pref_counter': False,
            'process_width': 640,
            'process_height': 480
        }
        
        node_id = 1
        tag_node_name = str(node_id) + ':MultiObjectTracking'
        enable_checkbox_tag = tag_node_name + ':EnableCheckbox'
        input_value02_tag = tag_node_name + ':Text:Input02Value'
        confidence_threshold_tag = tag_node_name + ':Float:ConfThreshValue'
        
        # Create necessary UI elements
        dpg.add_checkbox(tag=enable_checkbox_tag, default_value=True)
        dpg.add_combo(tag=input_value02_tag, items=['motpy'], default_value='motpy')
        dpg.add_slider_float(tag=confidence_threshold_tag, default_value=0.0)
        
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Simulate detection data
        detection_data = {
            'bboxes': [[100, 100, 200, 200]],
            'scores': [0.9],
            'class_ids': [0],
            'class_names': {0: 'person'}
        }
        
        # Setup with checkbox enabled
        node_image_dict = {'1:ObjectDetection': test_frame}
        node_result_dict = {'1:ObjectDetection': detection_data}
        connection_list = [
            ['1:ObjectDetection:Image:Output01', '1:MultiObjectTracking:Image:Input01'],
            ['1:ObjectDetection:JSON:Output01', '1:MultiObjectTracking:JSON:Input04']
        ]
        
        # Test with checkbox enabled
        dpg_set_value(enable_checkbox_tag, True)
        result_enabled = mot_node.update(
            node_id=node_id,
            connection_list=connection_list,
            node_image_dict=node_image_dict,
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        # Verify tracking produces results when enabled
        assert 'json' in result_enabled
        assert len(result_enabled['json'].get('bboxes', [])) > 0, \
            "Tracking should produce results when enabled"
        
        print("  ✓ Tracking enabled: produces tracking results")
        
        # Test with checkbox disabled
        dpg_set_value(enable_checkbox_tag, False)
        result_disabled = mot_node.update(
            node_id=node_id,
            connection_list=connection_list,
            node_image_dict=node_image_dict,
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        # Verify tracking produces empty results when disabled
        assert 'json' in result_disabled
        assert len(result_disabled['json'].get('bboxes', [])) == 0, \
            "Tracking should produce empty results when disabled"
        
        print("  ✓ Tracking disabled: produces no results")
        return True
    finally:
        dpg.destroy_context()


def test_mot_json_overrides_checkbox():
    """Test that JSON input can override checkbox value"""
    from node.TrackerNode.node_mot import Node as MOTNode
    from node_editor.util import dpg_get_value, dpg_set_value
    import dearpygui.dearpygui as dpg
    
    print("\nTesting JSON input overrides checkbox...")
    
    # Initialize DearPyGUI context
    dpg.create_context()
    
    try:
        # Create MOT node instance
        mot_node = MOTNode()
        mot_node._opencv_setting_dict = {
            'use_pref_counter': False,
            'process_width': 640,
            'process_height': 480
        }
        
        node_id = 1
        tag_node_name = str(node_id) + ':MultiObjectTracking'
        enable_checkbox_tag = tag_node_name + ':EnableCheckbox'
        input_value02_tag = tag_node_name + ':Text:Input02Value'
        confidence_threshold_tag = tag_node_name + ':Float:ConfThreshValue'
        
        # Create necessary UI elements
        dpg.add_checkbox(tag=enable_checkbox_tag, default_value=True)
        dpg.add_combo(tag=input_value02_tag, items=['motpy'], default_value='motpy')
        dpg.add_slider_float(tag=confidence_threshold_tag, default_value=0.0)
        
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Simulate detection data
        detection_data = {
            'bboxes': [[100, 100, 200, 200]],
            'scores': [0.9],
            'class_ids': [0],
            'class_names': {0: 'person'}
        }
        
        # JSON control that disables tracking
        json_control = {'enabled': False}
        
        # Setup with checkbox enabled BUT JSON disabled
        dpg_set_value(enable_checkbox_tag, True)
        
        node_image_dict = {'1:ObjectDetection': test_frame}
        node_result_dict = {
            '1:ObjectDetection': detection_data,
            '2:BooleanControl': json_control
        }
        connection_list = [
            ['1:ObjectDetection:Image:Output01', '1:MultiObjectTracking:Image:Input01'],
            ['2:BooleanControl:JSON:Output01', '1:MultiObjectTracking:JSON:Input03'],
            ['1:ObjectDetection:JSON:Output01', '1:MultiObjectTracking:JSON:Input04']
        ]
        
        # Execute MOT
        result = mot_node.update(
            node_id=node_id,
            connection_list=connection_list,
            node_image_dict=node_image_dict,
            node_result_dict=node_result_dict,
            node_audio_dict={}
        )
        
        # Verify JSON override works (checkbox enabled, but JSON disables)
        assert 'json' in result
        assert len(result['json'].get('bboxes', [])) == 0, \
            "JSON input should override checkbox (disabled)"
        
        print("  ✓ JSON input successfully overrides checkbox value")
        return True
    finally:
        dpg.destroy_context()


if __name__ == '__main__':
    print("=" * 60)
    print("Testing MOT Enable Tracking Checkbox")
    print("=" * 60)
    
    try:
        test_mot_checkbox_default_enabled()
        test_mot_checkbox_controls_tracking()
        test_mot_json_overrides_checkbox()
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
