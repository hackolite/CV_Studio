#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for spectrogram preparation functionality"""

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


def test_prepare_spectrogram_defaults():
    """Test _prepare_spectrogram with default parameters (fmin=None, fmax=None)"""
    # Create a test audio file
    audio_file = create_test_audio_file(duration=1.0)
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_1'
        
        # Mock convert_cv_to_dpg to avoid numpy 2.0 compatibility issue (unrelated to this fix)
        with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
            # Call _prepare_spectrogram with default parameters
            # This should not raise any TypeError
            node._prepare_spectrogram(node_id, audio_file, fmin=None, fmax=None)
        
        # Check that spectrogram was generated
        assert node_id in node._spectrogram_meta, "Spectrogram metadata should be stored"
        assert 'y' in node._spectrogram_meta[node_id], "Audio signal should be stored"
        assert 'sr' in node._spectrogram_meta[node_id], "Sample rate should be stored"
        
        # Check that the stored audio has expected properties
        y = node._spectrogram_meta[node_id]['y']
        sr = node._spectrogram_meta[node_id]['sr']
        assert len(y) > 0, "Audio signal should not be empty"
        assert sr == 22050, "Sample rate should be 22050"
        
        print("✓ test_prepare_spectrogram_defaults passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


def test_prepare_spectrogram_with_fmin_fmax():
    """Test _prepare_spectrogram with numeric fmin and fmax values"""
    # Create a test audio file
    audio_file = create_test_audio_file(duration=1.0)
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_2'
        
        # Mock convert_cv_to_dpg to avoid numpy 2.0 compatibility issue (unrelated to this fix)
        with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
            # Call _prepare_spectrogram with specific fmin and fmax
            # This should not raise any TypeError
            fmin = 100.0  # 100 Hz
            fmax = 8000.0  # 8000 Hz (below Nyquist frequency of 11025 Hz)
            
            node._prepare_spectrogram(node_id, audio_file, fmin=fmin, fmax=fmax)
        
        # Check that spectrogram was generated
        assert node_id in node._spectrogram_meta, "Spectrogram metadata should be stored"
        assert 'y' in node._spectrogram_meta[node_id], "Audio signal should be stored"
        assert 'sr' in node._spectrogram_meta[node_id], "Sample rate should be stored"
        
        # Check that the stored audio has expected properties
        y = node._spectrogram_meta[node_id]['y']
        sr = node._spectrogram_meta[node_id]['sr']
        assert len(y) > 0, "Audio signal should not be empty"
        assert sr == 22050, "Sample rate should be 22050"
        
        print("✓ test_prepare_spectrogram_with_fmin_fmax passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


def test_prepare_spectrogram_only_fmin():
    """Test _prepare_spectrogram with only fmin specified"""
    # Create a test audio file
    audio_file = create_test_audio_file(duration=1.0)
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_3'
        
        # Mock convert_cv_to_dpg to avoid numpy 2.0 compatibility issue (unrelated to this fix)
        with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
            # Call _prepare_spectrogram with only fmin
            fmin = 200.0  # 200 Hz
            
            node._prepare_spectrogram(node_id, audio_file, fmin=fmin, fmax=None)
        
        # Check that spectrogram was generated
        assert node_id in node._spectrogram_meta, "Spectrogram metadata should be stored"
        
        print("✓ test_prepare_spectrogram_only_fmin passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


def test_prepare_spectrogram_only_fmax():
    """Test _prepare_spectrogram with only fmax specified"""
    # Create a test audio file
    audio_file = create_test_audio_file(duration=1.0)
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_4'
        
        # Mock convert_cv_to_dpg to avoid numpy 2.0 compatibility issue (unrelated to this fix)
        with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
            # Call _prepare_spectrogram with only fmax
            fmax = 8000.0  # 8000 Hz
            
            node._prepare_spectrogram(node_id, audio_file, fmin=None, fmax=fmax)
        
        # Check that spectrogram was generated
        assert node_id in node._spectrogram_meta, "Spectrogram metadata should be stored"
        
        print("✓ test_prepare_spectrogram_only_fmax passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

