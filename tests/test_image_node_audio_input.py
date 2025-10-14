#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test that the image node can accept audio spectrograms as image inputs."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_image_node_structure():
    """Test that ImageNode has the required audio input attributes."""
    # Check that the file exists and can be parsed
    image_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_image.py'
    )
    
    assert os.path.exists(image_node_path), "node_image.py file should exist"
    
    # Read the file and check for required components
    with open(image_node_path, 'r') as f:
        content = f.read()
    
    # Check audio input tags
    assert 'tag_node_input_audio_name' in content, "Should have audio input tag"
    assert 'tag_node_input_audio_value_name' in content, "Should have audio input value tag"
    
    # Check audio input UI element
    assert 'Input Audio Spectrogram' in content, "Should have audio input text"
    assert 'mvNode_Attr_Input' in content, "Should have input attribute type"
    
    # Check that audio frame is processed in update method
    assert 'audio_frame' in content, "Should check for audio_frame"
    assert 'node_audio_dict.get' in content, "Should get audio from node_audio_dict"
    assert 'TYPE_AUDIO' in content, "Should check for TYPE_AUDIO connection"
    
    # Check return format is dict
    assert 'return {"image":' in content or "return {'image':" in content, \
        "Should return dict with 'image' key"
    
    print("✓ All structure checks passed")


def test_image_node_audio_processing_logic():
    """Test that ImageNode has the correct logic to process audio as image."""
    image_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_image.py'
    )
    
    with open(image_node_path, 'r') as f:
        content = f.read()
    
    # Check that audio frame takes priority when connected
    assert 'if audio_frame is not None:' in content, \
        "Should check if audio_frame is not None"
    assert 'frame = audio_frame' in content, \
        "Should use audio_frame as frame when audio is connected"
    
    # Check dict return format
    assert '"audio": None' in content or "'audio': None" in content, \
        "Should return audio as None in dict"
    assert '"json": None' in content or "'json': None" in content, \
        "Should return json as None in dict"
    
    print("✓ Audio processing logic checks passed")


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Image Node Audio Input Support")
    print("=" * 60)
    print()
    
    try:
        test_image_node_structure()
        print()
        test_image_node_audio_processing_logic()
        print()
        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
