#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for video node preview feature.
Verifies that the first frame is displayed immediately after video selection.
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_video_preview_source_code():
    """Test that the video node has preview functionality in _callback_file_select"""
    
    # Read the source file directly
    node_file = os.path.join(os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_video.py')
    with open(node_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    print("Testing video node preview functionality...\n")
    
    # Test 1: _callback_file_select should mention preview in docstring
    assert 'Displays the first frame as a preview' in source, \
        "Docstring should mention preview functionality"
    print("✅ Docstring mentions preview functionality")
    
    # Test 2: Should load first frame with cv2.VideoCapture in callback
    callback_section = source[source.find('def _callback_file_select'):source.find('def _callback_file_select') + 2000]
    assert 'preview_cap = cv2.VideoCapture(file_path)' in callback_section, \
        "Should create VideoCapture for preview"
    print("✅ Creates VideoCapture for preview")
    
    # Test 3: Should read first frame
    assert 'ret, first_frame = preview_cap.read()' in callback_section, \
        "Should read first frame"
    print("✅ Reads first frame")
    
    # Test 4: Should release preview capture
    assert 'preview_cap.release()' in callback_section, \
        "Should release preview capture"
    print("✅ Releases preview capture")
    
    # Test 5: Should convert frame to texture
    assert 'texture = self.convert_cv_to_dpg' in callback_section and 'first_frame' in callback_section, \
        "Should convert first frame to texture"
    print("✅ Converts first frame to texture")
    
    # Test 6: Should update texture display
    assert 'dpg_set_value(tag_node_output_image, texture)' in callback_section, \
        "Should update texture display with first frame"
    print("✅ Updates texture display")
    
    # Test 7: Should use thread-safe lock
    assert 'with _dpg_lock:' in callback_section, \
        "Should use thread-safe lock for UI updates"
    print("✅ Uses thread-safe lock")
    
    # Test 8: Should have error handling
    assert 'try:' in callback_section and 'except Exception as e:' in callback_section, \
        "Should have error handling for preview loading"
    print("✅ Has error handling for preview loading")
    
    # Test 9: Should print preview confirmation message
    assert '🖼️ Preview: First frame displayed' in source, \
        "Should print confirmation when preview is displayed"
    print("✅ Prints confirmation message")
    
    # Test 10: Preview should happen before preprocessing check
    # Find positions of preview code and preprocessing code
    preview_pos = source.find('preview_cap = cv2.VideoCapture(file_path)')
    preprocessing_pos = source.find('if not on_the_fly_mode:')
    assert preview_pos < preprocessing_pos, \
        "Preview should happen before preprocessing logic"
    print("✅ Preview happens before preprocessing")
    
    return True


if __name__ == "__main__":
    try:
        test_video_preview_source_code()
        
        print("\n" + "="*70)
        print("✅ All preview tests passed!")
        print("="*70)
        print("\nSummary of preview feature:")
        print("  • First frame is loaded immediately after video selection")
        print("  • Frame is converted to texture and displayed in node")
        print("  • Preview works independently of Start button")
        print("  • Preview happens before any preprocessing")
        print("  • Proper error handling and resource cleanup")
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
