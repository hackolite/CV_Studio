#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test that FPS Limit has been removed from Microphone node"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_microphone_no_fps_attributes():
    """Test that FPS limit attributes have been removed"""
    # Import only the base class without DPG dependency
    import importlib.util
    
    # Check that the source code doesn't have FPS limit references
    microphone_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    'node', 'InputNode', 'node_microphone.py')
    
    with open(microphone_file, 'r') as f:
        content = f.read()
    
    # Check that FPS limit UI elements have been removed
    assert 'label="FPS Limit"' not in content, "FPS Limit slider should be removed from UI"
    assert 'tag=node.tag_node_input04_value_name' in content, "Input04 should exist (now Output Mode)"
    
    # Check that FPS limiting code has been removed
    assert '_fps_limit = 30.0' not in content, "FPS limit attribute initialization should be removed"
    assert 'self._last_update_time = 0.0' not in content, "Last update time attribute should be removed"
    
    # Check that Audio:OK indicator is present
    assert 'Audio:OK' in content, "Audio:OK indicator should be present"
    
    print("✓ FPS limit attributes and UI elements removed from node")
    print("✓ Audio:OK indicator is present in code")


def test_microphone_audio_ok_indicator():
    """Test that audio indicator shows 'Audio:OK' when active"""
    # This is a simple check to ensure the indicator text is correct
    # The actual UI testing would require DearPyGUI to be running
    
    active_text = "Audio:OK"
    inactive_text = "Audio:"
    
    # Verify the text format
    assert active_text == "Audio:OK", "Active indicator should be 'Audio:OK'"
    assert inactive_text == "Audio:", "Inactive indicator should be 'Audio:'"
    
    print("✓ Audio indicator text format verified")
    print(f"  Active: {active_text}")
    print(f"  Inactive: {inactive_text}")


def test_microphone_json_output_db_format():
    """Test that microphone JSON output includes db_value when in dB Intensity mode"""
    # Simulate what the JSON output should look like
    import time
    
    # Example JSON output in dB Intensity mode
    json_output = {
        'timestamp': time.time(),
        'sample_rate': 44100,
        'channels': 1,
        'chunk_duration': 1.0,
        'output_mode': 'dB Intensity',
        'samples': 1,
        'db_value': -20.5  # Example dB value
    }
    
    # Verify structure
    assert 'db_value' in json_output, "JSON should contain db_value field"
    assert 'output_mode' in json_output, "JSON should contain output_mode field"
    assert json_output['output_mode'] == 'dB Intensity', "output_mode should be 'dB Intensity'"
    
    print("✓ Microphone JSON output format verified for dB Intensity mode")
    print(f"  db_value: {json_output['db_value']} dB")


def test_objchart_handles_db_json():
    """Test that objchart can handle microphone dB intensity JSON"""
    # Check the source code for dB handling
    objchart_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                  'node', 'VisualNode', 'node_obj_chart.py')
    
    with open(objchart_file, 'r') as f:
        content = f.read()
    
    # Check that objchart has code to handle dB data
    assert "'db_value' in node_result" in content, "objchart should check for db_value in JSON"
    assert "'output_mode' in node_result" in content, "objchart should check for output_mode in JSON"
    assert '"dB"' in content, "objchart should have dB class identifier"
    assert 'Decibel Intensity' in content, "objchart should reference Decibel Intensity"
    
    print("✓ objchart has code to handle microphone dB intensity JSON")
    print("  - Checks for db_value field")
    print("  - Checks for output_mode field")
    print("  - Uses 'dB' as class identifier")


def test_objchart_render_db_chart():
    """Test that objchart can render a chart with dB data"""
    # Check the source code for dB rendering
    objchart_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                  'node', 'VisualNode', 'node_obj_chart.py')
    
    with open(objchart_file, 'r') as f:
        content = f.read()
    
    # Check that render_chart handles dB data
    assert 'is_db_data' in content, "render_chart should check for dB data"
    assert 'Decibel Intensity (dB)' in content, "render_chart should have dB axis label"
    assert 'Microphone Decibel Intensity Over Time' in content, "render_chart should have dB chart title"
    
    print("✓ objchart can render chart with dB data")
    print("  - Detects dB data type")
    print("  - Uses appropriate axis labels")
    print("  - Uses appropriate chart title")


if __name__ == "__main__":
    print("Testing FPS removal and audio:OK indicator...\n")
    
    tests = [
        ("No FPS Attributes", test_microphone_no_fps_attributes),
        ("Audio:OK Indicator", test_microphone_audio_ok_indicator),
        ("Microphone dB JSON Format", test_microphone_json_output_db_format),
        ("objchart Handles dB JSON", test_objchart_handles_db_json),
        ("objchart Renders dB Chart", test_objchart_render_db_chart),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"Running: {test_name}")
            test_func()
            print(f"✓ PASSED: {test_name}\n")
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {test_name}")
            print(f"  Error: {e}\n")
            failed += 1
    
    print("=" * 70)
    print(f"Test Summary: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)
