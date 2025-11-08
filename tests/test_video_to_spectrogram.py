#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for video to spectrogram conversion utilities.
"""

import os
import sys
import tempfile
import numpy as np
import scipy.io.wavfile as wav

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_video_to_spectrogram import fourier_transformation, make_logscale, plot_spectrogram


def test_fourier_transformation():
    """Test the fourier_transformation function."""
    # Create a simple test signal (440 Hz sine wave)
    sample_rate = 22050
    duration = 1.0  # seconds
    frequency = 440  # Hz
    
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = np.sin(2 * np.pi * frequency * t)
    
    # Apply fourier transformation
    frameSize = 1024
    result = fourier_transformation(signal, frameSize)
    
    # Check that result is not None and has expected shape
    assert result is not None, "fourier_transformation returned None"
    assert result.ndim == 2, "Result should be 2D array"
    
    print("✓ fourier_transformation test passed")


def test_make_logscale():
    """Test the make_logscale function."""
    # Create a simple spectrogram
    timebins = 100
    freqbins = 513  # typical for 1024 FFT
    spec = np.random.rand(timebins, freqbins) + 1j * np.random.rand(timebins, freqbins)
    
    # Apply logarithmic scaling
    newspec, freqs = make_logscale(spec, sr=22050, factor=1.0)
    
    # Check results
    assert newspec is not None, "make_logscale returned None for newspec"
    assert freqs is not None, "make_logscale returned None for freqs"
    assert len(freqs) == newspec.shape[1], "Frequency array length should match spectrogram width"
    
    print("✓ make_logscale test passed")


def test_plot_spectrogram():
    """Test the plot_spectrogram function with a synthetic audio file."""
    # Create a temporary WAV file
    sample_rate = 22050
    duration = 0.5  # seconds
    frequency = 440  # Hz
    
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
        wav_path = temp_wav.name
        wav.write(wav_path, sample_rate, signal)
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_jpg:
        jpg_path = temp_jpg.name
    
    try:
        # Generate spectrogram
        result = plot_spectrogram(wav_path, plotpath=jpg_path, binsize=1024, colormap='jet')
        
        # Check that result is valid
        assert result is not None, "plot_spectrogram returned None"
        assert result.ndim == 2, "Result should be 2D array"
        
        # Check that output file was created
        assert os.path.exists(jpg_path), "Output JPG file was not created"
        assert os.path.getsize(jpg_path) > 0, "Output JPG file is empty"
        
        print("✓ plot_spectrogram test passed")
        
    finally:
        # Clean up temporary files
        if os.path.exists(wav_path):
            os.remove(wav_path)
        if os.path.exists(jpg_path):
            os.remove(jpg_path)


def test_integration():
    """Integration test for the full pipeline."""
    print("\nRunning integration tests...")
    
    # Test each function
    test_fourier_transformation()
    test_make_logscale()
    test_plot_spectrogram()
    
    print("\n✓ All integration tests passed successfully!")


if __name__ == '__main__':
    test_integration()
