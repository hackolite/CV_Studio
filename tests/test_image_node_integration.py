#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test complete workflow: Audio spectrogram treated as image."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_image_node_returns_dict():
    """Verify that image node returns dict format compatible with main.py."""
    image_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_image.py'
    )
    
    with open(image_node_path, 'r') as f:
        content = f.read()
    
    # Verify dict return format (required by main.py)
    assert 'return {"image":' in content or "return {'image':" in content, \
        "Image node must return dict with 'image' key"
    
    # Verify all three keys are present
    in_return_statement = False
    has_image_key = False
    has_audio_key = False
    has_json_key = False
    
    for line in content.split('\n'):
        if 'return {' in line:
            in_return_statement = True
        if in_return_statement:
            if '"image"' in line or "'image'" in line:
                has_image_key = True
            if '"audio"' in line or "'audio'" in line:
                has_audio_key = True
            if '"json"' in line or "'json'" in line:
                has_json_key = True
            if '}' in line and in_return_statement:
                break
    
    assert has_image_key, "Return dict must have 'image' key"
    assert has_audio_key, "Return dict must have 'audio' key"
    assert has_json_key, "Return dict must have 'json' key"
    
    print("✓ Image node returns correct dict format")


def test_audio_input_connection_logic():
    """Test the logic for connecting audio input."""
    image_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_image.py'
    )
    
    with open(image_node_path, 'r') as f:
        content = f.read()
    
    # Check connection parsing logic
    assert 'for connection_info in connection_list:' in content, \
        "Must iterate through connection_list"
    assert 'connection_type = connection_info.split' in content, \
        "Must parse connection type from connection_info"
    assert 'if connection_type == self.TYPE_AUDIO:' in content, \
        "Must check for AUDIO connection type"
    
    # Check audio dict access
    assert 'node_audio_dict.get(' in content, \
        "Must get audio from node_audio_dict"
    
    # Check priority logic: audio takes priority when connected
    assert 'if audio_frame is not None:' in content, \
        "Must check if audio_frame is not None"
    assert 'frame = audio_frame' in content, \
        "Must assign audio_frame to frame when audio is connected"
    
    print("✓ Audio input connection logic is correct")


def test_backward_compatibility():
    """Test that image node maintains backward compatibility."""
    image_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_image.py'
    )
    
    with open(image_node_path, 'r') as f:
        content = f.read()
    
    # Verify old image loading logic still exists
    assert '_image_filepath' in content, \
        "Must keep _image_filepath storage"
    assert 'cv2.imread' in content, \
        "Must still support loading images from files"
    assert 'else:' in content and 'image_path' in content, \
        "Must fallback to image file when no audio is connected"
    
    # Verify update signature is compatible
    assert 'def update(' in content, \
        "Must have update method"
    assert 'node_audio_dict=None' in content, \
        "node_audio_dict parameter must default to None for backward compatibility"
    
    print("✓ Backward compatibility maintained")


def test_ui_elements():
    """Test that UI elements for audio input are present."""
    image_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_image.py'
    )
    
    with open(image_node_path, 'r') as f:
        content = f.read()
    
    # Check audio input pin exists
    assert 'tag_node_input_audio_name' in content, \
        "Must define audio input tag"
    assert 'mvNode_Attr_Input' in content, \
        "Must create input attribute for audio"
    assert 'Input Audio Spectrogram' in content, \
        "Must have descriptive text for audio input"
    
    print("✓ UI elements are correct")


def test_consistency_with_other_nodes():
    """Test that image node follows same pattern as other nodes."""
    image_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_image.py'
    )
    
    # Compare with video node structure
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    if os.path.exists(video_node_path):
        with open(image_node_path, 'r') as f:
            image_content = f.read()
        with open(video_node_path, 'r') as f:
            video_content = f.read()
        
        # Both should return dicts with same structure
        image_has_dict_return = 'return {' in image_content and '"image"' in image_content
        video_has_dict_return = 'return {' in video_content and '"image"' in video_content
        
        if video_has_dict_return:
            assert image_has_dict_return, \
                "Image node should use same dict return format as video node"
            print("✓ Consistent with video node return format")
    
    print("✓ Pattern consistency verified")


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Image Node Audio Integration")
    print("=" * 60)
    print()
    
    all_passed = True
    
    try:
        test_image_node_returns_dict()
        print()
        test_audio_input_connection_logic()
        print()
        test_backward_compatibility()
        print()
        test_ui_elements()
        print()
        test_consistency_with_other_nodes()
        print()
        print("=" * 60)
        print("All integration tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        all_passed = False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        all_passed = False
    
    if not all_passed:
        sys.exit(1)
