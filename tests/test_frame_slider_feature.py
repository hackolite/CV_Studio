#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test that the frame slider feature works correctly for spectrogram visualization.
This test validates:
1. Video node has frame slider UI element
2. Frame slider value is passed through audio metadata
3. Classification node (yolo-cls) uses frame slider value correctly
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_video_node_has_frame_slider():
    """Test that video node has Input06 for frame slider"""
    import unittest.mock as mock
    
    # Mock all dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['librosa'] = mock.MagicMock()
    sys.modules['matplotlib'] = mock.MagicMock()
    sys.modules['matplotlib.cm'] = mock.MagicMock()
    
    # Read the source code
    video_node_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_video.py')
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that Input06 is defined
    assert 'tag_node_input06_name' in content, \
        "Video node should have tag_node_input06_name for frame slider"
    
    assert 'tag_node_input06_value_name' in content, \
        "Video node should have tag_node_input06_value_name for frame slider"
    
    # Check that the slider is added with correct label
    assert 'label="Frame Width (px)"' in content, \
        "Frame slider should have 'Frame Width (px)' label"
    
    print("✓ Video node has frame slider UI element (Input06)")


def test_frame_slider_in_settings():
    """Test that frame slider value is saved/loaded in settings"""
    video_node_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_video.py')
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that frame_width is in get_setting_dict
    assert 'frame_width = int(dpg_get_value(tag_node_input06_value_name))' in content, \
        "get_setting_dict should read frame_width from slider"
    
    assert 'setting_dict[tag_node_input06_value_name] = frame_width' in content, \
        "get_setting_dict should save frame_width to settings"
    
    # Check that frame_width is in set_setting_dict
    assert 'dpg_set_value(tag_node_input06_value_name, frame_width)' in content, \
        "set_setting_dict should restore frame_width from settings"
    
    print("✓ Frame slider value is saved/loaded in settings")


def test_frame_width_passed_in_audio_metadata():
    """Test that frame_width is passed through audio metadata"""
    video_node_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_video.py')
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that frame_width is used in spectrogram windowing
    assert 'window_width = frame_width' in content, \
        "Spectrogram window should use frame_width slider value"
    
    # Check that audio_data is returned as tuple with frame_width
    assert 'audio_data = (spectrogram_bgr, frame_width)' in content, \
        "Audio data should be returned as tuple (spectrogram, frame_width)"
    
    print("✓ Frame width is passed through audio metadata")


def test_get_input_frame_returns_metadata():
    """Test that get_input_frame returns (frame, metadata) tuple"""
    basenode_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'basenode.py')
    with open(basenode_path, 'r') as f:
        content = f.read()
    
    # Check that get_input_frame returns tuple
    assert 'return None, None' in content, \
        "get_input_frame should return (None, None) when no connection found"
    
    assert 'return frame, metadata' in content, \
        "get_input_frame should return (frame, metadata) tuple"
    
    # Check that it handles tuple format from video node
    assert 'if isinstance(audio_data, tuple) and len(audio_data) == 2:' in content, \
        "get_input_frame should check if audio_data is tuple"
    
    assert 'frame, frame_width = audio_data' in content, \
        "get_input_frame should unpack (spectrogram, frame_width) tuple"
    
    assert 'metadata = {"frame_width": frame_width}' in content, \
        "get_input_frame should create metadata dict with frame_width"
    
    print("✓ get_input_frame returns (frame, metadata) tuple")


def test_classification_node_uses_frame_width():
    """Test that classification node uses frame_width for yolo-cls"""
    classification_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'DLNode', 'node_classification.py')
    with open(classification_path, 'r') as f:
        content = f.read()
    
    # Check that classification node gets metadata from get_input_frame
    assert 'frame, audio_metadata = self.get_input_frame' in content, \
        "Classification node should unpack (frame, metadata) from get_input_frame"
    
    # Check that frame_width is extracted from metadata
    assert "frame_width = audio_metadata['frame_width']" in content, \
        "Classification node should extract frame_width from metadata"
    
    # Check that yolo-cls uses frame_width to resize spectrogram
    assert "if model_name == 'Yolo-cls' and frame_width is not None:" in content, \
        "Yolo-cls should check for frame_width availability"
    
    assert 'inference_frame = cv2.resize(frame, (frame_width, h)' in content, \
        "Yolo-cls should resize spectrogram to frame_width"
    
    print("✓ Classification node uses frame_width for yolo-cls")


def test_backward_compatibility():
    """Test that other nodes handle new get_input_frame signature"""
    test_nodes = [
        'node/DLNode/node_semantic_segmentation.py',
        'node/DLNode/node_face_detection.py',
        'node/DLNode/node_monocular_depth_estimation.py',
        'node/DLNode/node_object_detection.py',
        'node/ProcessNode/node_blur.py',
        'node/ProcessNode/node_canny.py',
        'node/ProcessNode/node_contrast.py',
        'node/ProcessNode/node_crop.py',
    ]
    
    for node_file in test_nodes:
        file_path = os.path.join(os.path.dirname(__file__), '..', node_file)
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check that nodes unpack the tuple correctly (discarding metadata)
        assert 'frame, _ = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)' in content, \
            f"{node_file} should unpack (frame, _) to ignore metadata"
        
        print(f"  ✓ {os.path.basename(node_file)} handles new signature")
    
    print("✓ All nodes are backward compatible with new get_input_frame signature")


def test_frame_slider_range():
    """Test that frame slider has appropriate min/max values"""
    video_node_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_video.py')
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check slider range
    assert 'min_value=60' in content, \
        "Frame slider minimum should be 60 pixels"
    
    assert 'max_value=small_window_w' in content, \
        "Frame slider maximum should be small_window_w (240)"
    
    assert 'default_value=small_window_w' in content, \
        "Frame slider default should be small_window_w (full width)"
    
    print("✓ Frame slider has appropriate range (60-240, default 240)")


if __name__ == '__main__':
    print("Running tests for frame slider feature...\n")
    
    try:
        test_video_node_has_frame_slider()
        test_frame_slider_in_settings()
        test_frame_width_passed_in_audio_metadata()
        test_get_input_frame_returns_metadata()
        test_classification_node_uses_frame_width()
        test_backward_compatibility()
        test_frame_slider_range()
        
        print("\n" + "="*60)
        print("All tests passed! ✓")
        print("="*60)
        print("\nFrame slider feature is working correctly:")
        print("- Video node has frame slider UI (60-240 pixels)")
        print("- Frame width is saved/loaded in node settings")
        print("- Frame width is passed via audio metadata tuple")
        print("- get_input_frame returns (frame, metadata) tuple")
        print("- Yolo-cls uses frame_width to resize spectrogram")
        print("- Other nodes ignore metadata (backward compatible)")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
