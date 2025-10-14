#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for frame-based spectrogram generation in video node.

This test verifies that the video node can generate a spectrogram
directly from a video frame (using 2D FFT) instead of from audio.
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
import numpy as np


def test_frame_spectrogram_generation():
    """Test that frame-based spectrogram can be generated from a video frame."""
    from node.InputNode.node_video import VideoNode
    
    # Create a test node
    node = VideoNode()
    
    # Create a test frame (random image simulating a video frame)
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Generate spectrogram from the frame
    spectrogram = node._generate_frame_spectrogram(test_frame)
    
    # Verify the spectrogram was generated
    assert spectrogram is not None, "Spectrogram should not be None"
    assert isinstance(spectrogram, np.ndarray), "Spectrogram should be a numpy array"
    assert len(spectrogram.shape) == 3, "Spectrogram should be a 3D array (BGR image)"
    assert spectrogram.shape[2] == 3, "Spectrogram should have 3 channels (BGR)"
    assert spectrogram.dtype == np.uint8, "Spectrogram should be uint8"
    
    print(f"✓ Spectrogram generated successfully with shape {spectrogram.shape}")


def test_frame_spectrogram_with_none():
    """Test that _generate_frame_spectrogram handles None input gracefully."""
    from node.InputNode.node_video import VideoNode
    
    node = VideoNode()
    spectrogram = node._generate_frame_spectrogram(None)
    
    assert spectrogram is None, "Spectrogram should be None when input is None"
    print("✓ None input handled correctly")


def test_frame_spectrogram_different_sizes():
    """Test that spectrogram can be generated from frames of different sizes."""
    from node.InputNode.node_video import VideoNode
    
    node = VideoNode()
    
    # Test with different frame sizes
    sizes = [(240, 320, 3), (480, 640, 3), (720, 1280, 3)]
    
    for size in sizes:
        test_frame = np.random.randint(0, 255, size, dtype=np.uint8)
        spectrogram = node._generate_frame_spectrogram(test_frame)
        
        assert spectrogram is not None, f"Spectrogram should be generated for size {size}"
        assert spectrogram.shape == size, f"Spectrogram shape should match input {size}"
        print(f"✓ Spectrogram generated for size {size}")


def test_spectrogram_is_different_from_frame():
    """Test that the spectrogram is actually different from the input frame."""
    from node.InputNode.node_video import VideoNode
    
    node = VideoNode()
    
    # Create a test frame with a specific pattern
    test_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    test_frame[100:140, 140:180] = [255, 0, 0]  # Blue square
    
    spectrogram = node._generate_frame_spectrogram(test_frame)
    
    # The spectrogram should be different from the original frame
    # (it's a frequency representation, not the spatial image)
    assert not np.array_equal(spectrogram, test_frame), \
        "Spectrogram should be different from input frame"
    
    print("✓ Spectrogram is correctly transformed from input frame")


def test_no_audio_dependency():
    """Test that the new implementation doesn't require audio extraction."""
    from node.InputNode.node_video import VideoNode
    
    node = VideoNode()
    
    # Create a simple frame
    test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    
    # This should work without any audio-related attributes
    spectrogram = node._generate_frame_spectrogram(test_frame)
    
    assert spectrogram is not None, "Spectrogram generation should not depend on audio"
    print("✓ Frame-based spectrogram works independently of audio")


if __name__ == '__main__':
    print("Testing frame-based spectrogram generation...\n")
    
    test_frame_spectrogram_generation()
    test_frame_spectrogram_with_none()
    test_frame_spectrogram_different_sizes()
    test_spectrogram_is_different_from_frame()
    test_no_audio_dependency()
    
    print("\n✓ All tests passed!")
