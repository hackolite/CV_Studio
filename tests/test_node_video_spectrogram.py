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
    assert 'import subprocess' in content, "Should import subprocess"
    assert 'import tempfile' in content, "Should import tempfile"
    assert 'import soundfile as sf' in content, "Should import soundfile for WAV operations"
    
    # Check method exists - _preprocess_video now handles WAV chunking
    assert 'def _preprocess_video' in content, "Should have _preprocess_video method"
    
    # Check storage attributes for WAV-based chunking
    assert '_audio_chunk_paths' in content, "Should have WAV chunk paths storage dict"
    assert '_chunk_metadata' in content, "Should have chunk metadata dict"
    assert '_chunk_temp_dirs' in content, "Should track temporary directories for cleanup"
    
    # Check WAV file operations
    assert 'sf.write(chunk_path,' in content, "Should save audio chunks as WAV files"
    assert 'sf.read(chunk_path)' in content, "Should load audio chunks from WAV files"
    
    # Check ffmpeg usage for efficient audio extraction
    assert 'pcm_s16le' in content, "Should use WAV codec for audio extraction"
    
    # Check audio processing
    assert 'chunk_samples' in content, "Should process audio in chunks"
    assert 'sr=22050' in content or 'sr = 22050' in content or 'sr=None' in content, "Should use sample rate"
    
    # Check cleanup
    assert 'def _cleanup_audio_chunks' in content, "Should have cleanup method for WAV files"
    
    print("✓ All structure checks passed")
    print("  - WAV-based audio chunking implemented")
    print("  - ffmpeg used for efficient audio extraction")
    print("  - Proper cleanup methods in place")


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
