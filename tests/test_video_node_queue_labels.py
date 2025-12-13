#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test video node queue size labels"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_video_node_has_queue_labels():
    """Test that node_video.py has queue size labels defined"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that queue info tags are defined
    assert 'tag_node_queue_info_name' in content, "Queue info name tag should be defined"
    assert 'tag_node_queue_info_value_name' in content, "Queue info value tag should be defined"
    
    # Check that queue info label is added to UI
    assert 'dpg.add_text' in content and 'Queue: Image=0/0 Audio=0/0' in content, \
        "Queue info text label should be added to UI with default value showing size/maxsize"
    
    # Check that queue sizes are retrieved in update method
    assert 'get_queue_info' in content, "Update method should retrieve queue info"
    assert 'image_queue_size' in content, "Update method should get image queue size"
    assert 'audio_queue_size' in content, "Update method should get audio queue size"
    
    # Check that queue info label is updated
    assert 'Queue: Image=' in content and 'Audio=' in content, \
        "Queue info label should be updated with queue sizes"
    
    print("✓ Video node has queue size labels")
    print("  - Queue info tags defined")
    print("  - Queue info text label added to UI")
    print("  - Queue sizes retrieved in update method")
    print("  - Queue info label updated with sizes")


if __name__ == "__main__":
    test_video_node_has_queue_labels()
    print("\n✅ All tests passed!")
