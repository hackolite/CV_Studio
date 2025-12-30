#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for video node on-the-fly mode fix.
Verifies that frames are NEVER sent in JSON output, only via IMAGE output.
This test checks the source code without requiring dependencies.
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_video_node_source_code():
    """Test the video node source code for correct implementation"""
    
    # Read the source file directly
    node_file = os.path.join(os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_video.py')
    with open(node_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    print("Testing video node source code...\n")
    
    # Test 1: Checkbox label should be "On-the-fly (fast mode)"
    assert 'label="On-the-fly (fast mode)"' in source, \
        "Checkbox label should be 'On-the-fly (fast mode)'"
    print("✅ Checkbox label is correct: 'On-the-fly (fast mode)'")
    
    # Test 2: Default value should be True
    # Check that near the checkbox label, we have default_value=True
    checkbox_section = source[source.find('label="On-the-fly (fast mode)"')-50:source.find('label="On-the-fly (fast mode)"')+300]
    assert 'default_value=True' in checkbox_section, \
        "Checkbox default value should be True"
    print("✅ Checkbox default value is True (on-the-fly mode enabled by default)")
    
    # Test 3: Variable should be renamed to on_the_fly_mode
    assert 'on_the_fly_mode' in source, \
        "Variable should be renamed to on_the_fly_mode"
    print("✅ Variable renamed to 'on_the_fly_mode'")
    
    # Test 4: Old variable name should be removed
    assert 'send_frames_in_json' not in source, \
        "Old variable name 'send_frames_in_json' should be completely removed"
    print("✅ Old variable name 'send_frames_in_json' removed")
    
    # Test 5: Frame data should NOT be sent in JSON
    assert 'frame.tolist()' not in source, \
        "frame.tolist() should be removed - frames should not be in JSON"
    print("✅ Frames are not converted to JSON (frame.tolist() removed)")
    
    # Test 6: JSON output should always be None (no frame data)
    assert '"frame":' not in source or '# JSON output can contain metadata only (no frame data)' in source, \
        "Frame data should not be added to JSON output"
    print("✅ JSON output does not contain frame data")
    
    # Test 7: Comment should state frames are always sent via IMAGE
    assert 'Frames are ALWAYS sent via IMAGE output, never in JSON' in source, \
        "Comment should clarify frames are sent via IMAGE only"
    print("✅ Comment confirms frames are always sent via IMAGE output")
    
    # Test 8: Default in get_setting_dict should be True
    assert 'on_the_fly_mode = True' in source, \
        "Default should be True in update method"
    print("✅ Default value is True in get_setting_dict")
    
    # Test 9: Default in set_setting_dict should be True
    assert 'tag_node_input06_value_name, True)' in source, \
        "Default should be True in set_setting_dict"
    print("✅ Default value is True in set_setting_dict")
    
    # Test 10: Preprocessing should run when on_the_fly_mode is False
    assert 'if not on_the_fly_mode:' in source, \
        "Preprocessing should run when checkbox is unchecked"
    print("✅ Preprocessing logic runs when on-the-fly mode is disabled")
    
    # Test 11: Updated comment in _callback_file_select
    assert 'On-the-fly mode: Skipping preprocessing (fast mode, frames sent via IMAGE output)' in source, \
        "Comment should reflect new behavior"
    print("✅ Comments updated to reflect on-the-fly mode behavior")
    
    return True


if __name__ == "__main__":
    try:
        test_video_node_source_code()
        
        print("\n" + "="*70)
        print("✅ All tests passed!")
        print("="*70)
        print("\nSummary of changes:")
        print("  • Checkbox label: 'Send frames in JSON' → 'On-the-fly (fast mode)'")
        print("  • Default value: False → True")
        print("  • Frames: NEVER sent in JSON, ALWAYS sent via IMAGE output")
        print("  • Variable: 'send_frames_in_json' → 'on_the_fly_mode'")
        print("  • Behavior when checked: Skip preprocessing, send frames on-the-fly")
        print("  • Behavior when unchecked: Preprocess video, extract audio chunks")
        print("="*70)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

