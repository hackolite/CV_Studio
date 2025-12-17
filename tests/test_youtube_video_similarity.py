#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that YouTube and Video nodes have similar structure and behavior.
This ensures consistency between the two input nodes.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.InputNode.node_youtube import YoutubeNode
from node.InputNode.node_video import VideoNode


def test_both_nodes_have_update_method():
    """Test that both nodes have the update method"""
    youtube_node = YoutubeNode()
    video_node = VideoNode()
    
    assert hasattr(youtube_node, 'update'), "YouTube node should have update method"
    assert hasattr(video_node, 'update'), "Video node should have update method"
    
    # Check method signature
    import inspect
    youtube_sig = inspect.signature(youtube_node.update)
    video_sig = inspect.signature(video_node.update)
    
    # Both should have the same parameters
    youtube_params = list(youtube_sig.parameters.keys())
    video_params = list(video_sig.parameters.keys())
    
    assert youtube_params == video_params, \
        f"Update method parameters should match. YouTube: {youtube_params}, Video: {video_params}"


def test_both_nodes_have_state_management():
    """Test that both nodes have state management attributes"""
    youtube_node = YoutubeNode()
    video_node = VideoNode()
    
    # Check for state management attributes
    assert hasattr(youtube_node, '_is_playing'), "YouTube node should have _is_playing"
    assert hasattr(video_node, '_is_playing'), "Video node should have _is_playing"
    
    assert isinstance(youtube_node._is_playing, dict), "YouTube _is_playing should be a dict"
    assert isinstance(video_node._is_playing, dict), "Video _is_playing should be a dict"


def test_both_nodes_have_close_method():
    """Test that both nodes have close method for cleanup"""
    youtube_node = YoutubeNode()
    video_node = VideoNode()
    
    assert hasattr(youtube_node, 'close'), "YouTube node should have close method"
    assert hasattr(video_node, 'close'), "Video node should have close method"


def test_both_nodes_have_settings_methods():
    """Test that both nodes have get_setting_dict and set_setting_dict methods"""
    youtube_node = YoutubeNode()
    video_node = VideoNode()
    
    assert hasattr(youtube_node, 'get_setting_dict'), "YouTube node should have get_setting_dict"
    assert hasattr(video_node, 'get_setting_dict'), "Video node should have get_setting_dict"
    
    assert hasattr(youtube_node, 'set_setting_dict'), "YouTube node should have set_setting_dict"
    assert hasattr(video_node, 'set_setting_dict'), "Video node should have set_setting_dict"


def test_update_returns_same_structure():
    """Test that update methods have the same return structure"""
    import inspect
    
    youtube_node = YoutubeNode()
    video_node = VideoNode()
    
    # Check the source code to verify return structure
    # (we can't call update without DearPyGUI initialization)
    youtube_source = inspect.getsource(youtube_node.update)
    video_source = inspect.getsource(video_node.update)
    
    # Both should return dictionaries with 'image', 'json', and 'audio' keys
    assert 'return' in youtube_source, "YouTube update should have return statement"
    assert 'return' in video_source, "Video update should have return statement"
    
    # Check for expected keys in return statements
    assert '"image"' in youtube_source or "'image'" in youtube_source, \
        "YouTube update should return 'image' key"
    assert '"image"' in video_source or "'image'" in video_source, \
        "Video update should return 'image' key"
    
    assert '"json"' in youtube_source or "'json'" in youtube_source, \
        "YouTube update should return 'json' key"
    assert '"json"' in video_source or "'json'" in video_source, \
        "Video update should return 'json' key"
    
    assert '"audio"' in youtube_source or "'audio'" in youtube_source, \
        "YouTube update should return 'audio' key"
    assert '"audio"' in video_source or "'audio'" in video_source, \
        "Video update should return 'audio' key"


def test_both_nodes_have_label_constants():
    """Test that both nodes have start/stop label constants"""
    youtube_node = YoutubeNode()
    video_node = VideoNode()
    
    assert hasattr(youtube_node, '_start_label'), "YouTube node should have _start_label"
    assert hasattr(video_node, '_start_label'), "Video node should have _start_label"
    
    assert hasattr(youtube_node, '_stop_label'), "YouTube node should have _stop_label"
    assert hasattr(video_node, '_stop_label'), "Video node should have _stop_label"


def test_no_deprecated_methods_in_youtube():
    """Test that YouTube node doesn't have deprecated _update method"""
    youtube_node = YoutubeNode()
    
    # YouTube node should NOT have _update method anymore
    assert not hasattr(youtube_node, '_update'), \
        "YouTube node should not have deprecated _update method"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
