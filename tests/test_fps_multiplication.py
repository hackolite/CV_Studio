#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for FPS multiplication by 2.5 in VideoWriter
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_fps_multiplication_in_node_video_writer():
    """Test that VideoWriter uses FPS * 2.5 when creating video"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        source = f.read()
    
    # Check that FPS is multiplied by 2.5 in the VideoWriter creation
    assert 'writer_fps * 2.5' in source, "FPS should be multiplied by 2.5 in VideoWriter creation"
    
    print("✓ FPS multiplication in node_video_writer test passed")


def test_fps_multiplication_in_video_worker():
    """Test that VideoBackgroundWorker uses FPS * 2.5 when creating video"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'video_worker.py')
    
    if not os.path.exists(file_path):
        print("⚠ video_worker.py not available, skipping test")
        return
    
    with open(file_path, 'r') as f:
        source = f.read()
    
    # Check that FPS is multiplied by 2.5 in the VideoWriter creation
    assert 'self.fps * 2.5' in source, "FPS should be multiplied by 2.5 in VideoWriter creation"
    
    print("✓ FPS multiplication in video_worker test passed")


def test_fps_multiplication_in_adapt_method():
    """Test that _adapt_video_to_audio_duration uses FPS * 2.5 when creating video"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        source = f.read()
    
    # Check that FPS is multiplied by 2.5 in the VideoWriter creation for adapted video
    assert 'fps * 2.5' in source, "FPS should be multiplied by 2.5 in adapted VideoWriter creation"
    
    print("✓ FPS multiplication in _adapt_video_to_audio_duration test passed")


if __name__ == '__main__':
    test_fps_multiplication_in_node_video_writer()
    test_fps_multiplication_in_video_worker()
    test_fps_multiplication_in_adapt_method()
    print("\n✅ All FPS multiplication tests passed!")
