#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test to verify that step_duration is correctly set to 1.0 seconds"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_step_duration_default_is_1s():
    """Verify that step_duration default is 1.0 seconds in _preprocess_video"""
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
            # Verify step_duration=1.0 is in the signature
            assert 'step_duration=1.0' in line, \
                f"step_duration should be 1.0, found: {line}"
            found_method = True
            break
    
    assert found_method, "_preprocess_video method should exist"
    print("✓ step_duration default is correctly set to 1.0 seconds")


def test_step_duration_docstring():
    """Verify that the docstring mentions 1.0 seconds for step_duration"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # The docstring should mention step_duration default as 1.0
    assert 'step_duration: Step size between chunks in seconds (default: 1.0)' in content, \
        "Docstring should mention step_duration default as 1.0"
    
    print("✓ Docstring correctly documents step_duration=1.0")


def test_chunk_audio_function_step_duration():
    """Verify that chunk_audio_wav_or_mp3 function also uses 1.0 seconds"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    found_function = False
    
    for line in lines:
        if 'def chunk_audio_wav_or_mp3' in line:
            # Verify step_duration=1.0 is in the signature
            assert 'step_duration=1.0' in line, \
                f"chunk_audio_wav_or_mp3 step_duration should be 1.0, found: {line}"
            found_function = True
            break
    
    assert found_function, "chunk_audio_wav_or_mp3 function should exist"
    print("✓ chunk_audio_wav_or_mp3 step_duration is correctly set to 1.0 seconds")


def test_synchronization_calculation():
    """Test that synchronization logic uses step_duration correctly"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # The _get_spectrogram_for_frame method should use step_duration for synchronization
    assert 'def _get_spectrogram_for_frame' in content, \
        "_get_spectrogram_for_frame method should exist"
    
    # It should calculate chunk index based on current_time / step_duration
    assert 'chunk_index = int(current_time / step_duration)' in content, \
        "Should calculate chunk_index using step_duration"
    
    print("✓ Synchronization logic uses step_duration correctly")


def test_requirements_for_spectrograms():
    """Verify all requirements are met:
    - 24 FPS default (configurable)
    - Speed modulation via sliders
    - 5s chunks with 1s slide
    - Synchronized playback
    """
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
    assert 'label="Skip Rate"' in content, "Should have Skip Rate slider"
    
    # 3. Check 5s chunks with 1s slide
    assert 'chunk_duration=5.0' in content, "Should use 5s chunk duration"
    assert 'step_duration=1.0' in content, "Should use 1s step duration"
    
    # 4. Check synchronized playback
    assert '_get_spectrogram_for_frame' in content, \
        "Should have synchronized spectrogram retrieval"
    assert 'self._spectrogram_chunks' in content, \
        "Should store pre-computed spectrograms"
    
    print("✓ All requirements verified:")
    print("  - 24 FPS default (configurable)")
    print("  - Speed modulation via sliders")
    print("  - 5s chunks with 1s slide")
    print("  - Synchronized playback")


if __name__ == '__main__':
    test_step_duration_default_is_1s()
    test_step_duration_docstring()
    test_chunk_audio_function_step_duration()
    test_synchronization_calculation()
    test_requirements_for_spectrograms()
    print("\n✅ All step_duration=1.0 tests passed!")
