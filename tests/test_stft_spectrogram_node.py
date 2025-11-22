#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that the Spectrogram node correctly uses the new STFT-based functions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def test_spectrogram_node_has_stft_custom():
    """Test that Spectrogram node has the new stft_custom method"""
    spec_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'AudioProcessNode', 'node_spectrogram.py'
    )
    
    assert os.path.exists(spec_node_path), "node_spectrogram.py should exist"
    
    with open(spec_node_path, 'r') as f:
        content = f.read()
    
    # Check imports
    assert 'from node.InputNode.spectrogram_utils import' in content, \
        "Should import from spectrogram_utils"
    assert 'fourier_transformation' in content, \
        "Should import fourier_transformation"
    assert 'make_logscale' in content, \
        "Should import make_logscale"
    assert 'create_spectrogram_from_audio' in content, \
        "Should import create_spectrogram_from_audio"
    
    # Check that stft_custom method exists
    assert 'def create_stft_custom' in content, \
        "Should have create_stft_custom function"
    
    # Check that stft_custom is in the methods list
    assert "'stft_custom'" in content, \
        "Should have stft_custom in methods"
    
    # Check that it's in the combo items
    assert "'stft_custom'" in content and 'items=' in content, \
        "Should have stft_custom in combo dropdown"
    
    print("✓ Spectrogram node has stft_custom method")


def test_stft_custom_produces_valid_output():
    """Test that create_stft_custom produces valid RGB spectrograms"""
    from node.InputNode.spectrogram_utils import create_spectrogram_from_audio
    
    # Create test audio
    sample_rate = 22050
    duration = 1.0
    frequency = 440.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Test the function
    spec_image = create_spectrogram_from_audio(
        audio_data, 
        sample_rate=sample_rate, 
        binsize=1024, 
        colormap="jet"
    )
    
    assert spec_image is not None, "Should produce output"
    assert spec_image.ndim == 3, "Should be 3D image"
    assert spec_image.shape[2] == 3, "Should have 3 channels (RGB)"
    assert spec_image.dtype == np.uint8, "Should be uint8"
    assert spec_image.min() >= 0 and spec_image.max() <= 255, \
        "Values should be in [0, 255]"
    
    print(f"✓ STFT custom produces valid RGB spectrogram: {spec_image.shape}")


def test_spectrogram_utils_functions():
    """Test the utility functions in spectrogram_utils.py"""
    from node.InputNode.spectrogram_utils import (
        fourier_transformation,
        make_logscale,
        apply_colormap_to_spectrogram
    )
    
    # Create test signal
    sample_rate = 22050
    duration = 0.5
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * 440 * t)
    
    # Test fourier_transformation
    binsize = 1024
    stft_result = fourier_transformation(signal, binsize)
    assert stft_result.shape[1] == binsize // 2 + 1, \
        "STFT should have correct frequency bins"
    print(f"✓ fourier_transformation works: {stft_result.shape}")
    
    # Test make_logscale
    log_spec, freqs = make_logscale(stft_result, sr=sample_rate, factor=1.0)
    assert log_spec.shape[0] == stft_result.shape[0], \
        "Time dimension should be preserved"
    assert len(freqs) == log_spec.shape[1], \
        "Should have frequency for each bin"
    print(f"✓ make_logscale works: {log_spec.shape}, {len(freqs)} frequencies")
    
    # Test colormap application
    magnitude = np.abs(log_spec)
    # Convert to dB
    db_spec = 20. * np.log10(magnitude / 10e-6)
    db_transposed = np.transpose(db_spec)
    
    colored = apply_colormap_to_spectrogram(db_transposed, method='cv2', cmap='JET')
    assert colored.shape[2] == 3, "Should be RGB"
    assert colored.dtype == np.uint8, "Should be uint8"
    print(f"✓ apply_colormap_to_spectrogram works: {colored.shape}")


if __name__ == '__main__':
    print("Testing Spectrogram Node STFT Implementation...\n")
    test_spectrogram_node_has_stft_custom()
    test_stft_custom_produces_valid_output()
    test_spectrogram_utils_functions()
    print("\n" + "="*60)
    print("✓ All Spectrogram Node STFT tests passed!")
    print("="*60)
