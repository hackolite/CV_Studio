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
    
    # Check method exists
    assert 'def _prepare_spectrogram' in content, "Should have _prepare_spectrogram method"
    
    # Check storage attributes
    assert '_spectrogram_texture = {}' in content, "Should have _spectrogram_texture dict"
    assert '_spectrogram_array = {}' in content, "Should have _spectrogram_array dict"
    assert '_spectrogram_params = {}' in content, "Should have _spectrogram_params dict"
    assert '_spectrogram_meta = {}' in content, "Should have _spectrogram_meta dict"
    
    # Check UI elements
    assert 'Show Spectrogram' in content, "Should have Show Spectrogram checkbox"
    assert 'SpectrogramToggle' in content, "Should have spectrogram toggle tag"
    assert 'SpectrogramValue' in content, "Should have spectrogram value tag"
    
    # Check mel-spectrogram parameters (now in kwargs dict)
    assert "'n_fft': 2048" in content, "Should use n_fft=2048"
    assert "'hop_length': 512" in content, "Should use hop_length=512"
    assert "'n_mels': 128" in content, "Should use n_mels=128"
    assert 'sr=22050' in content, "Should use sr=22050"
    
    # Check colormap
    assert "'magma'" in content, "Should use magma colormap"
    
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
