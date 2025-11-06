#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for audio diagnostic agent utilities.
"""

import sys
import os
import pytest
import numpy as np
import tempfile
import json
import soundfile as sf

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from scripts.utils_audio import (
    get_sample_rate,
    extract_audio_wav,
    compute_mel_spectrogram,
    measure_energy_in_band,
    save_spectrogram_image
)


def test_get_sample_rate_invalid_file():
    """Test get_sample_rate with an invalid file path."""
    result = get_sample_rate('/nonexistent/file.mp4')
    assert result is None, "Should return None for non-existent file"


def test_get_sample_rate_text_file():
    """Test get_sample_rate with a non-video file."""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'This is not a video file')
        temp_path = f.name
    
    try:
        result = get_sample_rate(temp_path)
        assert result is None, "Should return None for non-video file"
    finally:
        os.unlink(temp_path)


def test_extract_audio_wav_invalid_file():
    """Test extract_audio_wav with an invalid input file."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        output_path = f.name
    
    try:
        result = extract_audio_wav('/nonexistent/video.mp4', output_path)
        assert result is False, "Should return False for non-existent input file"
        
        # Output file should not be created or should not exist
        if os.path.exists(output_path):
            # If it exists, it should be empty or very small
            assert os.path.getsize(output_path) < 100, "Output file should be empty/invalid"
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_compute_mel_spectrogram_with_synthetic_audio():
    """Test compute_mel_spectrogram with synthetic audio data."""
    # Create a temporary WAV file with synthetic audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_wav = f.name
    
    try:
        # Generate a simple sine wave
        sample_rate = 22050
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio_data = 0.5 * np.sin(2 * np.pi * frequency * t)
        
        # Save to WAV file
        sf.write(temp_wav, audio_data, sample_rate)
        
        # Compute Mel spectrogram
        mel_spec_db, used_sr = compute_mel_spectrogram(
            temp_wav,
            sr=sample_rate,
            n_fft=2048,
            hop_length=512,
            n_mels=128
        )
        
        assert mel_spec_db is not None, "Mel spectrogram should not be None"
        assert used_sr == sample_rate, f"Sample rate should match: expected {sample_rate}, got {used_sr}"
        assert mel_spec_db.shape[0] == 128, "Should have 128 Mel bands"
        assert mel_spec_db.shape[1] > 0, "Should have time frames"
        assert np.all(np.isfinite(mel_spec_db)), "All values should be finite"
        
        print(f"✓ Mel spectrogram computed successfully: shape={mel_spec_db.shape}")
        
    finally:
        if os.path.exists(temp_wav):
            os.unlink(temp_wav)


def test_compute_mel_spectrogram_invalid_file():
    """Test compute_mel_spectrogram with an invalid audio file."""
    mel_spec_db, used_sr = compute_mel_spectrogram('/nonexistent/audio.wav')
    assert mel_spec_db is None, "Should return None for non-existent file"
    assert used_sr is None, "Should return None for non-existent file"


def test_measure_energy_in_band():
    """Test measure_energy_in_band with synthetic spectrogram."""
    # Create a synthetic Mel spectrogram
    n_mels = 128
    n_frames = 100
    mel_spec_db = np.random.randn(n_mels, n_frames) * 10 - 40  # Random values around -40 dB
    
    sr = 22050
    fmin = 0.0
    fmax = sr / 2.0
    
    # Measure energy in a frequency band
    energy = measure_energy_in_band(
        mel_spec_db,
        freq_min=1000.0,
        freq_max=2000.0,
        sr=sr,
        n_mels=n_mels,
        fmin=fmin,
        fmax=fmax
    )
    
    assert isinstance(energy, float), "Energy should be a float"
    assert np.isfinite(energy), "Energy should be finite"
    assert -80 <= energy <= 0, f"Energy should be in reasonable dB range, got {energy}"
    
    print(f"✓ Energy measured successfully: {energy:.2f} dB")


def test_measure_energy_in_band_full_range():
    """Test measure_energy_in_band across full frequency range."""
    # Create a synthetic Mel spectrogram with a gradient
    n_mels = 128
    n_frames = 100
    # Create gradient from low to high energy
    mel_spec_db = np.tile(np.linspace(-60, -20, n_mels), (n_frames, 1)).T
    
    sr = 22050
    fmin = 0.0
    fmax = sr / 2.0
    
    # Measure energy in low frequency band
    energy_low = measure_energy_in_band(
        mel_spec_db, 0.0, 500.0, sr, n_mels, fmin, fmax
    )
    
    # Measure energy in high frequency band
    energy_high = measure_energy_in_band(
        mel_spec_db, 8000.0, 11025.0, sr, n_mels, fmin, fmax
    )
    
    # High frequency should have higher energy due to gradient
    assert energy_high > energy_low, "High frequency band should have higher energy"
    
    print(f"✓ Energy gradient test passed: low={energy_low:.2f} dB, high={energy_high:.2f} dB")


def test_save_spectrogram_image():
    """Test save_spectrogram_image with synthetic spectrogram."""
    # Create a synthetic Mel spectrogram
    n_mels = 128
    n_frames = 100
    mel_spec_db = np.random.randn(n_mels, n_frames) * 10 - 40
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        output_path = f.name
    
    try:
        result = save_spectrogram_image(
            mel_spec_db,
            output_path,
            sr=22050,
            hop_length=512,
            title="Test Spectrogram"
        )
        
        assert result is True, "Should return True on success"
        assert os.path.exists(output_path), "PNG file should be created"
        assert os.path.getsize(output_path) > 1000, "PNG file should have reasonable size"
        
        print(f"✓ Spectrogram image saved successfully: {output_path}")
        
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_spectrogram_parameters():
    """Test compute_mel_spectrogram with different parameters."""
    # Create a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_wav = f.name
    
    try:
        sample_rate = 16000
        duration = 0.5
        frequency = 1000.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio_data = 0.5 * np.sin(2 * np.pi * frequency * t)
        sf.write(temp_wav, audio_data, sample_rate)
        
        # Test with different n_mels
        for n_mels in [64, 128, 256]:
            mel_spec_db, used_sr = compute_mel_spectrogram(
                temp_wav,
                sr=sample_rate,
                n_mels=n_mels
            )
            assert mel_spec_db.shape[0] == n_mels, f"Should have {n_mels} Mel bands"
        
        # Test with different hop_length
        for hop_length in [256, 512, 1024]:
            mel_spec_db, used_sr = compute_mel_spectrogram(
                temp_wav,
                sr=sample_rate,
                hop_length=hop_length
            )
            assert mel_spec_db is not None, f"Should compute with hop_length={hop_length}"
        
        print("✓ Spectrogram parameter variations tested successfully")
        
    finally:
        if os.path.exists(temp_wav):
            os.unlink(temp_wav)


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    # Test with very small spectrogram
    mel_spec_db = np.array([[-40.0], [-50.0], [-60.0]])
    
    energy = measure_energy_in_band(
        mel_spec_db,
        freq_min=100.0,
        freq_max=200.0,
        sr=8000,
        n_mels=3,
        fmin=0.0,
        fmax=4000.0
    )
    
    assert isinstance(energy, float), "Should return float even for small spectrogram"
    assert np.isfinite(energy), "Should return finite value"
    
    print("✓ Edge cases handled successfully")


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s'])
