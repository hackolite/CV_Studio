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
    """Test that VideoWriter uses FPS multiplier when creating video"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        source = f.read()
    
    # Check that FPS multiplier constant is defined
    assert '_FPS_MULTIPLIER = 2.5' in source, "FPS multiplier constant should be defined as 2.5"
    
    # Check that FPS is multiplied before VideoWriter creation
    assert 'writer_fps * self._FPS_MULTIPLIER' in source or 'writer_fps *= self._FPS_MULTIPLIER' in source, \
        "FPS should be multiplied by FPS_MULTIPLIER before VideoWriter creation"
    
    print("✓ FPS multiplication in node_video_writer test passed")


def test_fps_multiplication_passed_to_worker():
    """Test that multiplied FPS is passed to VideoBackgroundWorker"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        source = f.read()
    
    # Verify that the VideoBackgroundWorker receives writer_fps as its fps parameter
    # Since writer_fps is already multiplied by FPS_MULTIPLIER before this call,
    # the worker will receive the multiplied value
    assert 'fps=writer_fps' in source, \
        "VideoBackgroundWorker should receive writer_fps (which is already multiplied)"
    
    # Also verify the multiplication happens before the worker is created
    lines = source.split('\n')
    multiply_line_idx = None
    worker_create_line_idx = None
    
    for i, line in enumerate(lines):
        if 'writer_fps *= self._FPS_MULTIPLIER' in line or 'writer_fps = writer_fps * self._FPS_MULTIPLIER' in line:
            multiply_line_idx = i
        if 'VideoBackgroundWorker(' in line:
            worker_create_line_idx = i
    
    if multiply_line_idx is not None and worker_create_line_idx is not None:
        assert multiply_line_idx < worker_create_line_idx, \
            "FPS multiplication should occur before VideoBackgroundWorker is created"
    
    print("✓ FPS multiplication passed to worker test passed")


def test_fps_stored_in_metadata():
    """Test that FPS is stored correctly in recording metadata after multiplication"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        source = f.read()
    
    # The multiplied writer_fps should be stored in metadata
    # This ensures _adapt_video_to_audio_duration receives the correct FPS
    assert "'fps': writer_fps" in source, "Multiplied FPS should be stored in recording metadata"
    
    print("✓ FPS stored in metadata test passed")


if __name__ == '__main__':
    test_fps_multiplication_in_node_video_writer()
    test_fps_multiplication_passed_to_worker()
    test_fps_stored_in_metadata()
    print("\n✅ All FPS multiplication tests passed!")
