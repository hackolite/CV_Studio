#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test spectrogram zero division fix"""

import pytest
import sys
import os
import numpy as np
import tempfile
import soundfile as sf
import warnings
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.node_video import VideoNode


def create_test_audio_file(duration=1.0, sample_rate=22050, frequency=440.0, amplitude=1.0):
    """
    Create a temporary audio file with a sine wave.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz
        amplitude: Amplitude of the sine wave (0.0 to 1.0)
        
    Returns:
        Path to the temporary audio file
    """
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_file.close()
    
    # Write audio to file
    sf.write(temp_file.name, audio, sample_rate)
    
    return temp_file.name


def create_silent_audio_file(duration=1.0, sample_rate=22050):
    """
    Create a temporary silent audio file (all zeros).
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        
    Returns:
        Path to the temporary audio file
    """
    # Generate silence
    audio = np.zeros(int(sample_rate * duration))
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_file.close()
    
    # Write audio to file
    sf.write(temp_file.name, audio, sample_rate)
    
    return temp_file.name


def test_spectrogram_no_warnings_normal_audio():
    """Test that normal audio does not produce warnings"""
    # Create a test audio file with normal amplitude
    audio_file = create_test_audio_file(duration=1.0, amplitude=0.5)
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_normal'
        
        # Mock convert_cv_to_dpg to avoid numpy 2.0 compatibility issue
        with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
            # Capture warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                
                # Call _prepare_spectrogram
                node._prepare_spectrogram(node_id, audio_file, fmin=None, fmax=None)
                
                # Check for division by zero warnings
                division_warnings = [warning for warning in w 
                                   if 'divide by zero' in str(warning.message)]
                assert len(division_warnings) == 0, \
                    "Should not have division by zero warnings for normal audio"
                
                # Check for invalid value warnings
                invalid_warnings = [warning for warning in w 
                                  if 'invalid value' in str(warning.message)]
                assert len(invalid_warnings) == 0, \
                    "Should not have invalid value warnings for normal audio"
        
        # Check that spectrogram was generated
        assert node_id in node._spectrogram_texture, "Spectrogram texture should be stored"
        assert node_id in node._spectrogram_array, "Spectrogram array should be stored"
        
        # Check that spectrogram has valid values (no NaN or inf)
        spec_array = node._spectrogram_array[node_id]
        assert not np.any(np.isnan(spec_array)), "Spectrogram should not contain NaN"
        assert not np.any(np.isinf(spec_array)), "Spectrogram should not contain inf"
        
        print("✓ test_spectrogram_no_warnings_normal_audio passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


def test_spectrogram_no_warnings_silent_audio():
    """Test that silent audio (zeros) does not produce warnings"""
    # Create a silent audio file
    audio_file = create_silent_audio_file(duration=1.0)
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_silent'
        
        # Mock convert_cv_to_dpg
        with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
            # Capture warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                
                # Call _prepare_spectrogram
                node._prepare_spectrogram(node_id, audio_file, fmin=None, fmax=None)
                
                # Check for division by zero warnings
                division_warnings = [warning for warning in w 
                                   if 'divide by zero' in str(warning.message)]
                assert len(division_warnings) == 0, \
                    "Should not have division by zero warnings for silent audio"
                
                # Check for invalid value warnings
                invalid_warnings = [warning for warning in w 
                                  if 'invalid value' in str(warning.message)]
                assert len(invalid_warnings) == 0, \
                    "Should not have invalid value warnings for silent audio"
        
        # Check that spectrogram was generated
        assert node_id in node._spectrogram_texture, "Spectrogram texture should be stored"
        assert node_id in node._spectrogram_array, "Spectrogram array should be stored"
        
        # Check that spectrogram has valid values (no NaN or inf)
        spec_array = node._spectrogram_array[node_id]
        assert not np.any(np.isnan(spec_array)), "Spectrogram should not contain NaN"
        assert not np.any(np.isinf(spec_array)), "Spectrogram should not contain inf"
        
        print("✓ test_spectrogram_no_warnings_silent_audio passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


def test_spectrogram_no_warnings_very_quiet_audio():
    """Test that very quiet audio does not produce warnings"""
    # Create a test audio file with very low amplitude
    audio_file = create_test_audio_file(duration=1.0, amplitude=1e-8)
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_quiet'
        
        # Mock convert_cv_to_dpg
        with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
            # Capture warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                
                # Call _prepare_spectrogram
                node._prepare_spectrogram(node_id, audio_file, fmin=None, fmax=None)
                
                # Check for division by zero warnings
                division_warnings = [warning for warning in w 
                                   if 'divide by zero' in str(warning.message)]
                assert len(division_warnings) == 0, \
                    "Should not have division by zero warnings for very quiet audio"
                
                # Check for invalid value warnings
                invalid_warnings = [warning for warning in w 
                                  if 'invalid value' in str(warning.message)]
                assert len(invalid_warnings) == 0, \
                    "Should not have invalid value warnings for very quiet audio"
        
        # Check that spectrogram was generated
        assert node_id in node._spectrogram_texture, "Spectrogram texture should be stored"
        assert node_id in node._spectrogram_array, "Spectrogram array should be stored"
        
        # Check that spectrogram has valid values (no NaN or inf)
        spec_array = node._spectrogram_array[node_id]
        assert not np.any(np.isnan(spec_array)), "Spectrogram should not contain NaN"
        assert not np.any(np.isinf(spec_array)), "Spectrogram should not contain inf"
        
        print("✓ test_spectrogram_no_warnings_very_quiet_audio passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


def test_spectrogram_valid_output_range():
    """Test that spectrogram output is in valid range [0, 255]"""
    # Create a test audio file
    audio_file = create_test_audio_file(duration=1.0)
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_range'
        
        # Mock convert_cv_to_dpg
        with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
            # Call _prepare_spectrogram
            node._prepare_spectrogram(node_id, audio_file, fmin=None, fmax=None)
        
        # Check that spectrogram array values are in valid range
        spec_array = node._spectrogram_array[node_id]
        assert spec_array.min() >= 0, "Spectrogram minimum should be >= 0"
        assert spec_array.max() <= 255, "Spectrogram maximum should be <= 255"
        
        print("✓ test_spectrogram_valid_output_range passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
