#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for VideoWriter node with async merge functionality.
"""
import sys
import os
import tempfile
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_videowriter_node_instantiation():
    """Test that VideoWriterNode can be instantiated with new async features"""
    from node.VideoNode.node_video_writer import VideoWriterNode, FactoryNode
    
    # Test VideoWriterNode class attributes
    assert hasattr(VideoWriterNode, '_merge_threads_dict'), "Missing _merge_threads_dict attribute"
    assert hasattr(VideoWriterNode, '_merge_progress_dict'), "Missing _merge_progress_dict attribute"
    
    # Test that the class can be instantiated
    node = VideoWriterNode()
    assert node is not None, "Failed to instantiate VideoWriterNode"
    
    # Test that the async merge method exists
    assert hasattr(node, '_async_merge_thread'), "Missing _async_merge_thread method"
    
    print("✓ VideoWriterNode instantiation test passed")


def test_progress_callback_signature():
    """Test that _merge_audio_video_ffmpeg accepts progress_callback parameter"""
    from node.VideoNode.node_video_writer import VideoWriterNode
    import inspect
    
    node = VideoWriterNode()
    
    # Get the signature of _merge_audio_video_ffmpeg
    sig = inspect.signature(node._merge_audio_video_ffmpeg)
    params = list(sig.parameters.keys())
    
    # Verify progress_callback parameter exists
    assert 'progress_callback' in params, "Missing progress_callback parameter"
    
    # Verify it has a default value (should be None)
    assert sig.parameters['progress_callback'].default is None, \
        "progress_callback should default to None"
    
    print("✓ Progress callback signature test passed")


def test_async_merge_thread_method():
    """Test that _async_merge_thread method has correct signature"""
    from node.VideoNode.node_video_writer import VideoWriterNode
    import inspect
    
    node = VideoWriterNode()
    
    # Get the signature of _async_merge_thread
    sig = inspect.signature(node._async_merge_thread)
    params = list(sig.parameters.keys())
    
    # Verify expected parameters
    expected_params = ['tag_node_name', 'temp_path', 'audio_samples', 'sample_rate', 'final_path']
    for param in expected_params:
        assert param in params, f"Missing parameter: {param}"
    
    print("✓ Async merge thread method test passed")


def test_class_level_dicts_exist():
    """Test that class-level dictionaries for tracking are properly initialized"""
    from node.VideoNode.node_video_writer import VideoWriterNode
    
    # These should be class-level dictionaries
    assert isinstance(VideoWriterNode._merge_threads_dict, dict), \
        "_merge_threads_dict should be a dictionary"
    assert isinstance(VideoWriterNode._merge_progress_dict, dict), \
        "_merge_progress_dict should be a dictionary"
    
    # They should start empty
    assert len(VideoWriterNode._merge_threads_dict) == 0, \
        "_merge_threads_dict should start empty"
    assert len(VideoWriterNode._merge_progress_dict) == 0, \
        "_merge_progress_dict should start empty"
    
    print("✓ Class-level dictionaries test passed")


if __name__ == "__main__":
    test_videowriter_node_instantiation()
    test_progress_callback_signature()
    test_async_merge_thread_method()
    test_class_level_dicts_exist()
    print("\n✅ All VideoWriter integration tests passed!")
