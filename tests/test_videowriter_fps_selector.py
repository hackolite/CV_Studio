#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test FPS selector functionality in VideoWriter node.

This test verifies that:
1. FPS combo box code exists in the node
2. FPS options include 24, 25, 30, 60 FPS
3. Default FPS is set to 24 FPS (not 30 from config)
4. FPS value is used when creating VideoWriter
5. FPS setting is saved and restored in get/set_setting_dict
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_fps_combo_exists():
    """Test that FPS combo box is created in node"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    assert "tag_node_name + ':FPS'" in content, \
        "VideoWriter node should have FPS combo tag"
    
    assert "dpg.add_combo" in content and "FPS" in content, \
        "VideoWriter node should create FPS combo box"
    
    print("✓ FPS combo box exists in node")


def test_fps_options_available():
    """Test that FPS options include 24, 25, 30, 60"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    assert '24 FPS' in content, "24 FPS option should be available"
    assert '25 FPS' in content, "25 FPS option should be available"
    assert '30 FPS' in content, "30 FPS option should be available"
    assert '60 FPS' in content, "60 FPS option should be available"
    
    print("✓ All FPS options (24, 25, 30, 60) are available")


def test_default_fps_is_24():
    """Test that default FPS is set to 24 FPS"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Find the FPS combo definition
    assert "default_value='24 FPS'" in content, \
        "Default FPS should be 24 FPS (not 30 from config)"
    
    print("✓ Default FPS is set to 24 FPS")


def test_fps_value_used_in_recording():
    """Test that FPS value from combo is used when creating VideoWriter"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Check that FPS is retrieved from the combo
    assert "fps_tag = tag_node_name + ':FPS'" in content, \
        "FPS tag should be defined"
    
    assert "dpg_get_value(fps_tag)" in content or "dpg.get_value(fps_tag)" in content, \
        "FPS value should be retrieved from combo"
    
    # Check that FPS map exists to convert text to number
    assert "fps_map = {" in content or "fps_map={" in content, \
        "FPS map should exist to convert text to number"
    
    assert "'24 FPS': 24" in content, "FPS map should include 24 FPS"
    assert "'30 FPS': 30" in content, "FPS map should include 30 FPS"
    
    # Check that writer_fps is set from the combo, not from config
    assert "writer_fps = fps_map.get(" in content, \
        "writer_fps should be set from fps_map (combo value)"
    
    # Verify it's NOT using the config value anymore (this line should NOT exist in START section)
    lines = content.split('\n')
    in_start_section = False
    for i, line in enumerate(lines):
        if "if label == self._start_label:" in line:
            in_start_section = True
        elif "elif label == self._stop_label:" in line:
            in_start_section = False
        
        if in_start_section and "writer_fps = self._opencv_setting_dict['video_writer_fps']" in line:
            # Check if this line is before or after the fps_map line
            # It should be replaced, not alongside fps_map
            for j in range(i, min(i+20, len(lines))):
                if "writer_fps = fps_map.get(" in lines[j]:
                    break
            else:
                assert False, "writer_fps should be set from fps_map, not from config"
    
    print("✓ FPS value from combo is used in recording")


def test_fps_combo_disabled_during_recording():
    """Test that FPS combo is disabled during recording"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Check that FPS is disabled when starting
    assert "dpg.configure_item(fps_tag, enabled=False)" in content, \
        "FPS combo should be disabled during recording"
    
    # Check that FPS is re-enabled when stopping
    assert "dpg.configure_item(fps_tag, enabled=True)" in content, \
        "FPS combo should be re-enabled after stopping"
    
    print("✓ FPS combo is disabled during recording and re-enabled after")


def test_fps_setting_saved_and_restored():
    """Test that FPS setting is saved and restored"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Check get_setting_dict saves FPS
    assert "setting_dict['fps']" in content, \
        "get_setting_dict should save FPS setting"
    
    # Check set_setting_dict restores FPS
    assert "'fps' in setting_dict" in content, \
        "set_setting_dict should restore FPS setting"
    
    print("✓ FPS setting is saved and restored correctly")


def test_fps_logged():
    """Test that FPS is logged when starting recording"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Check that fps_text is in the log message
    assert "fps_text" in content, \
        "FPS value should be logged when starting recording"
    
    print("✓ FPS is logged when starting recording")


if __name__ == '__main__':
    print("\n=== Testing VideoWriter FPS Selector ===\n")
    
    try:
        test_fps_combo_exists()
        test_fps_options_available()
        test_default_fps_is_24()
        test_fps_value_used_in_recording()
        test_fps_combo_disabled_during_recording()
        test_fps_setting_saved_and_restored()
        test_fps_logged()
        
        print("\n" + "="*50)
        print("All tests passed! ✓")
        print("="*50)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
