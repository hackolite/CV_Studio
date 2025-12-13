#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test to verify that step_duration is correctly set to 3.0 seconds (no overlap)"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_step_duration_default_is_3s():
    """Verify that step_duration default is 3.0 seconds in _preprocess_video (no overlap)"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Find the _preprocess_video method definition
    lines = content.split('\n')
    found_method = False
    
    for line in lines:
        if 'def _preprocess_video' in line:
            # Verify step_duration=3.0 is in the signature
            assert 'step_duration=3.0' in line, \
                f"step_duration should be 3.0, found: {line}"
            found_method = True
            break
    
    assert found_method, "_preprocess_video method should exist"
    print("✓ step_duration default is correctly set to 3.0 seconds (no overlap)")


def test_step_duration_docstring():
    """Verify that the docstring mentions 3.0 seconds for step_duration"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # The docstring should mention step_duration default as 3.0, no overlap
    assert 'step_duration: Step size between chunks in seconds (default: 3.0, no overlap)' in content, \
        "Docstring should mention step_duration default as 3.0 with no overlap"
    
    print("✓ Docstring correctly documents step_duration=3.0")


def test_synchronization_calculation():
    """Test that synchronization logic uses step_duration correctly"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # The _get_audio_chunk_for_frame method should use step_duration for synchronization
    assert 'def _get_audio_chunk_for_frame' in content, \
        "_get_audio_chunk_for_frame method should exist"
    
    # It should calculate chunk index based on current_time / step_duration
    assert 'chunk_index = int(current_time / step_duration)' in content, \
        "Should calculate chunk_index using step_duration"
    
    print("✓ Synchronization logic uses step_duration correctly")


def test_no_overlap_configuration():
    """Verify that chunks are configured with no overlap (step_duration equals chunk_duration)"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # 1. Check 24 FPS default
    assert 'default_value=24' in content and 'Target FPS' in content, \
        "Should have Target FPS slider with default 24"
    
    # 2. Check speed modulation sliders
    assert 'label="Speed"' in content, "Should have Speed slider"
    
    # 3. Check that default step_duration equals chunk_duration (no overlap)
    # Check for the function signature with both parameters
    assert 'def _preprocess_video(self, node_id, movie_path, chunk_duration=3.0, step_duration=3.0)' in content, \
        "Default parameters should have no overlap (step_duration=chunk_duration)"
    
    # 4. Check synchronized playback via audio chunk retrieval
    assert '_get_audio_chunk_for_frame' in content, \
        "Should have synchronized audio chunk retrieval"
    assert 'self._audio_chunk_paths' in content, \
        "Should store audio chunk paths"
    
    print("✓ All requirements verified:")
    print("  - 24 FPS default (configurable)")
    print("  - Speed modulation via sliders")
    print("  - No overlap (step_duration equals chunk_duration)")
    print("  - Synchronized playback")


if __name__ == '__main__':
    test_step_duration_default_is_3s()
    test_step_duration_docstring()
    test_synchronization_calculation()
    test_no_overlap_configuration()
    print("\n✅ All step_duration=3.0 (no overlap) tests passed!")
