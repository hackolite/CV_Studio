#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Basic tests for Video Node spectrogram functionality"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_video_node_structure():
    """Test that VideoNode has the required spectrogram attributes"""
    # This is a basic structure test that doesn't require DearPyGUI or OpenCV
    
    # Check that the file exists and can be parsed
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    # Read the file and check for required components
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check imports
    assert 'import librosa' in content, "Should import librosa"
    assert 'import matplotlib.cm' in content, "Should import matplotlib.cm"
    assert 'import subprocess' in content, "Should import subprocess"
    assert 'import tempfile' in content, "Should import tempfile"
    
    # Check method exists (now it's _preprocess_video instead of _prepare_spectrogram)
    assert 'def _preprocess_video' in content, "Should have _preprocess_video method"
    
    # Check storage attributes (updated for new architecture)
    assert '_spectrogram_texture = {}' in content or '_spectrogram_chunks = {}' in content, "Should have spectrogram storage dict"
    assert '_spectrogram_array = {}' in content or '_spectrogram_chunks = {}' in content, "Should have spectrogram data dict"
    assert '_spectrogram_params = {}' in content or '_chunk_metadata = {}' in content, "Should have spectrogram params/metadata dict"
    assert '_spectrogram_meta = {}' in content or '_chunk_metadata = {}' in content, "Should have metadata dict"
    
    # Check UI elements
    assert 'Show Spectrogram' in content, "Should have Show Spectrogram checkbox"
    assert 'SpectrogramToggle' in content, "Should have spectrogram toggle tag"
    
    # Check STFT parameters (new approach)
    assert 'binsize = 2**10' in content or 'frameSize' in content, "Should use STFT with frame size"
    # hop_length is not needed in new chunking architecture, so we just check for audio processing
    assert 'chunk_samples' in content or 'hop_length' in content, "Should process audio in chunks"
    assert 'sr=22050' in content or 'sr = 22050' in content or 'sr=None' in content, "Should use sample rate"
    
    # Check for new STFT functions
    assert 'def fourier_transformation' in content, "Should have fourier_transformation function"
    assert 'def make_logscale' in content, "Should have make_logscale function"
    
    # Check colormap - now uses configurable colormap via utility function
    assert 'apply_colormap_to_spectrogram' in content, "Should use apply_colormap_to_spectrogram function"
    assert 'SPECTROGRAM_COLORMAP' in content, "Should have configurable colormap constant"
    
    print("✓ All structure checks passed")


def test_requirements_updated():
    """Test that requirements.txt includes the new dependencies"""
    requirements_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'requirements.txt'
    )
    
    assert os.path.exists(requirements_path), "requirements.txt should exist"
    
    with open(requirements_path, 'r') as f:
        content = f.read()
    
    assert 'librosa' in content, "Should include librosa in requirements"
    assert 'matplotlib' in content, "Should include matplotlib in requirements"
    assert 'soundfile' in content, "Should include soundfile in requirements"
    
    print("✓ All requirements checks passed")


if __name__ == '__main__':
    test_video_node_structure()
    test_requirements_updated()
    print("\n✓ All tests passed successfully!")
