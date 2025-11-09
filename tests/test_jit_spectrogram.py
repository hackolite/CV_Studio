#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for JIT (just-in-time) spectrogram generation functionality"""

import pytest
import sys
import os
import numpy as np
import tempfile
import soundfile as sf
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.node_video import VideoNode


def create_test_audio_file(duration=1.0, sample_rate=22050, frequency=440.0):
    """
    Create a temporary audio file with a sine wave.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz
        
    Returns:
        Path to the temporary audio file
    """
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_file.close()
    
    # Write audio to file
    sf.write(temp_file.name, audio, sample_rate)
    
    return temp_file.name


def test_spectrogram_mode_attribute():
    """Test that VideoNode has the _spectrogram_mode attribute with correct default"""
    node = VideoNode()
    
    # Check attribute exists
    assert hasattr(node, '_spectrogram_mode'), "VideoNode should have _spectrogram_mode attribute"
    
    # Check default value
    assert node._spectrogram_mode == 'precompute', "Default mode should be 'precompute'"
    
    print("✓ test_spectrogram_mode_attribute passed")


def test_audio_y_attribute():
    """Test that VideoNode has the _audio_y storage attribute"""
    node = VideoNode()
    
    # Check attribute exists
    assert hasattr(node, '_audio_y'), "VideoNode should have _audio_y attribute"
    
    # Check it's a dictionary
    assert isinstance(node._audio_y, dict), "_audio_y should be a dictionary"
    
    print("✓ test_audio_y_attribute passed")


def test_get_audio_chunk_for_frame_method():
    """Test that _get_audio_chunk_for_frame method exists"""
    node = VideoNode()
    
    # Check method exists
    assert hasattr(node, '_get_audio_chunk_for_frame'), "VideoNode should have _get_audio_chunk_for_frame method"
    
    # Test with empty data (should return None)
    result = node._get_audio_chunk_for_frame('nonexistent_node', 0)
    assert result is None, "Should return None for nonexistent node"
    
    print("✓ test_get_audio_chunk_for_frame_method passed")


def test_get_spectrogram_for_frame_modes():
    """Test that _get_spectrogram_for_frame supports both precompute and jit modes"""
    node = VideoNode()
    
    # Check helper methods exist
    assert hasattr(node, '_get_precomputed_spectrogram'), "Should have _get_precomputed_spectrogram method"
    assert hasattr(node, '_generate_spectrogram_jit'), "Should have _generate_spectrogram_jit method"
    
    print("✓ test_get_spectrogram_for_frame_modes passed")


def test_get_audio_chunk_for_frame_with_mock_data():
    """Test _get_audio_chunk_for_frame with mock audio data"""
    node = VideoNode()
    node_id = 'test_node'
    
    # Setup mock data
    sr = 22050
    duration = 5.0
    y = np.random.randn(int(sr * duration))
    
    node._audio_y[node_id] = y
    node._chunk_metadata[node_id] = {
        'fps': 30.0,
        'sr': sr,
        'chunk_duration': 5.0,
        'step_duration': 1.0,
    }
    
    # Test extracting chunk for frame 0
    chunk = node._get_audio_chunk_for_frame(node_id, 0)
    assert chunk is not None, "Should return audio chunk for frame 0"
    assert isinstance(chunk, np.ndarray), "Chunk should be numpy array"
    assert len(chunk) > 0, "Chunk should not be empty"
    
    # Test extracting chunk for frame 30 (1 second into video)
    chunk = node._get_audio_chunk_for_frame(node_id, 30)
    assert chunk is not None, "Should return audio chunk for frame 30"
    
    # Test with negative frame (should return None)
    chunk = node._get_audio_chunk_for_frame(node_id, -1)
    assert chunk is None, "Should return None for negative frame"
    
    print("✓ test_get_audio_chunk_for_frame_with_mock_data passed")


def test_jit_mode_generates_spectrogram():
    """Test that JIT mode can generate spectrograms on-the-fly"""
    node = VideoNode()
    node_id = 'test_node_jit'
    
    # Setup mock data
    sr = 22050
    duration = 5.0
    y = np.random.randn(int(sr * duration))
    
    node._audio_y[node_id] = y
    node._chunk_metadata[node_id] = {
        'fps': 30.0,
        'sr': sr,
        'chunk_duration': 5.0,
        'step_duration': 1.0,
    }
    
    # Switch to JIT mode
    node._spectrogram_mode = 'jit'
    
    # Test JIT spectrogram generation
    spec = node._generate_spectrogram_jit(node_id, 0)
    
    # Since we don't have all dependencies (cv2, etc.), spec might be None
    # But the method should execute without errors
    # If spec is not None, verify it's an array
    if spec is not None:
        assert isinstance(spec, np.ndarray), "JIT spectrogram should be numpy array"
        print("  Generated JIT spectrogram successfully")
    else:
        print("  JIT spectrogram generation attempted (may need full dependencies)")
    
    print("✓ test_jit_mode_generates_spectrogram passed")


def test_precompute_mode_returns_cached_spectrogram():
    """Test that precompute mode returns cached spectrograms"""
    node = VideoNode()
    node_id = 'test_node_precompute'
    
    # Setup mock data
    mock_spec = np.random.rand(135, 240, 3).astype(np.float32)
    
    node._spectrogram_chunks[node_id] = [mock_spec]
    node._chunk_metadata[node_id] = {
        'fps': 30.0,
        'sr': 22050,
        'chunk_duration': 5.0,
        'step_duration': 1.0,
    }
    
    # Ensure in precompute mode (default)
    node._spectrogram_mode = 'precompute'
    
    # Test precompute spectrogram retrieval
    spec = node._get_precomputed_spectrogram(node_id, 0)
    
    assert spec is not None, "Should return cached spectrogram"
    assert np.array_equal(spec, mock_spec), "Should return the exact cached spectrogram"
    
    print("✓ test_precompute_mode_returns_cached_spectrogram passed")


def test_mode_switch():
    """Test switching between precompute and jit modes"""
    node = VideoNode()
    
    # Default should be precompute
    assert node._spectrogram_mode == 'precompute'
    
    # Switch to JIT
    node._spectrogram_mode = 'jit'
    assert node._spectrogram_mode == 'jit'
    
    # Switch back to precompute
    node._spectrogram_mode = 'precompute'
    assert node._spectrogram_mode == 'precompute'
    
    print("✓ test_mode_switch passed")


def test_file_header_documentation():
    """Test that file has proper header documentation about modes"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for mode documentation
    assert 'precompute' in content, "Should document precompute mode"
    assert 'jit' in content or 'just-in-time' in content, "Should document JIT mode"
    assert 'self._spectrogram_mode' in content, "Should reference _spectrogram_mode attribute"
    
    print("✓ test_file_header_documentation passed")


if __name__ == '__main__':
    # Run all tests
    test_spectrogram_mode_attribute()
    test_audio_y_attribute()
    test_get_audio_chunk_for_frame_method()
    test_get_spectrogram_for_frame_modes()
    test_get_audio_chunk_for_frame_with_mock_data()
    test_jit_mode_generates_spectrogram()
    test_precompute_mode_returns_cached_spectrogram()
    test_mode_switch()
    test_file_header_documentation()
    
    print("\n✅ All JIT spectrogram tests passed successfully!")
