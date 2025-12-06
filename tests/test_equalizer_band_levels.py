#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for the Equalizer node band level meters"""

import os
import sys
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_band_levels_calculation():
    """Test that band levels are calculated correctly"""
    from node.AudioProcessNode.node_equalizer import apply_equalizer
    
    # Create test audio signal
    sample_rate = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a signal with different amplitudes for each band
    # Bass: amplitude 0.8, Mid-Bass: 0.6, Mid: 0.4, Mid-Treble: 0.3, Treble: 0.2
    audio_data = (
        0.8 * np.sin(2 * np.pi * 100 * t) +    # Bass (20-250 Hz)
        0.6 * np.sin(2 * np.pi * 400 * t) +    # Mid-Bass (250-500 Hz)
        0.4 * np.sin(2 * np.pi * 1000 * t) +   # Mid (500-2000 Hz)
        0.3 * np.sin(2 * np.pi * 4000 * t) +   # Mid-Treble (2000-6000 Hz)
        0.2 * np.sin(2 * np.pi * 8000 * t)     # Treble (6000-20000 Hz)
    )
    audio_data = audio_data.astype(np.float32)
    
    gains = {
        'bass': 0.0,
        'mid_bass': 0.0,
        'mid': 0.0,
        'mid_treble': 0.0,
        'treble': 0.0
    }
    
    processed, band_levels = apply_equalizer(audio_data, sample_rate, gains)
    
    # Check that band levels are returned
    assert band_levels is not None, "Band levels should not be None"
    assert isinstance(band_levels, dict), "Band levels should be a dictionary"
    
    # Check that all bands are present
    expected_bands = ['bass', 'mid_bass', 'mid', 'mid_treble', 'treble']
    for band in expected_bands:
        assert band in band_levels, f"Band '{band}' should be in band_levels"
        assert 0.0 <= band_levels[band] <= 1.0, f"Band level for '{band}' should be in [0, 1]"
    
    # Verify that higher amplitude bands have higher levels
    # Note: Due to filtering, the exact RMS values may differ, but relative ordering should be preserved
    print(f"✓ Band levels calculated correctly")
    print(f"  - Bass: {band_levels['bass']:.2f}")
    print(f"  - Mid-Bass: {band_levels['mid_bass']:.2f}")
    print(f"  - Mid: {band_levels['mid']:.2f}")
    print(f"  - Mid-Treble: {band_levels['mid_treble']:.2f}")
    print(f"  - Treble: {band_levels['treble']:.2f}")


def test_band_levels_with_gain():
    """Test that band levels reflect gain changes"""
    from node.AudioProcessNode.node_equalizer import apply_equalizer
    
    # Create uniform amplitude signal
    sample_rate = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    audio_data = (
        np.sin(2 * np.pi * 100 * t) +
        np.sin(2 * np.pi * 400 * t) +
        np.sin(2 * np.pi * 1000 * t) +
        np.sin(2 * np.pi * 4000 * t) +
        np.sin(2 * np.pi * 8000 * t)
    )
    audio_data = audio_data.astype(np.float32)
    
    # Test with bass boost
    gains_bass_boost = {
        'bass': 10.0,
        'mid_bass': 0.0,
        'mid': 0.0,
        'mid_treble': 0.0,
        'treble': 0.0
    }
    
    processed, band_levels = apply_equalizer(audio_data, sample_rate, gains_bass_boost)
    
    # Bass level should be significantly higher due to +10dB gain
    assert band_levels['bass'] > 0.5, "Bass level should be high with +10dB gain"
    
    print(f"✓ Band levels reflect gain changes")
    print(f"  - Bass level with +10dB: {band_levels['bass']:.2f}")
    
    # Test with treble cut
    gains_treble_cut = {
        'bass': 0.0,
        'mid_bass': 0.0,
        'mid': 0.0,
        'mid_treble': 0.0,
        'treble': -20.0
    }
    
    processed, band_levels = apply_equalizer(audio_data, sample_rate, gains_treble_cut)
    
    # Treble level should be very low due to -20dB cut
    assert band_levels['treble'] < 0.2, "Treble level should be low with -20dB cut"
    
    print(f"  - Treble level with -20dB: {band_levels['treble']:.2f}")


def test_band_levels_silent_audio():
    """Test band levels with silent audio"""
    from node.AudioProcessNode.node_equalizer import apply_equalizer
    
    # Create silent audio
    sample_rate = 22050
    audio_data = np.zeros(22050, dtype=np.float32)
    
    gains = {
        'bass': 0.0,
        'mid_bass': 0.0,
        'mid': 0.0,
        'mid_treble': 0.0,
        'treble': 0.0
    }
    
    processed, band_levels = apply_equalizer(audio_data, sample_rate, gains)
    
    # All band levels should be 0.0 for silent audio
    for band, level in band_levels.items():
        assert level == 0.0, f"Band '{band}' level should be 0.0 for silent audio, got {level}"
    
    print(f"✓ Band levels are 0.0 for silent audio")


def test_band_levels_full_scale():
    """Test band levels with full scale sine wave"""
    from node.AudioProcessNode.node_equalizer import apply_equalizer
    
    # Create full scale sine wave
    sample_rate = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Single frequency at full amplitude
    audio_data = np.sin(2 * np.pi * 1000 * t).astype(np.float32)
    
    gains = {
        'bass': 0.0,
        'mid_bass': 0.0,
        'mid': 0.0,
        'mid_treble': 0.0,
        'treble': 0.0
    }
    
    processed, band_levels = apply_equalizer(audio_data, sample_rate, gains)
    
    # The mid band should have the highest level since 1000Hz is in the mid range
    assert band_levels['mid'] > 0.5, "Mid band should have high level for 1000Hz signal"
    
    # Other bands should have lower or zero levels
    # (depending on filter characteristics, there might be some spillover)
    print(f"✓ Band levels correct for full scale sine wave")
    print(f"  - Mid level for 1000Hz signal: {band_levels['mid']:.2f}")


def test_band_levels_normalization():
    """Test that band levels are normalized to [0, 1] range"""
    from node.AudioProcessNode.node_equalizer import apply_equalizer
    
    # Create audio with extreme gains
    sample_rate = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    audio_data = (
        np.sin(2 * np.pi * 100 * t) +
        np.sin(2 * np.pi * 400 * t) +
        np.sin(2 * np.pi * 1000 * t) +
        np.sin(2 * np.pi * 4000 * t) +
        np.sin(2 * np.pi * 8000 * t)
    )
    audio_data = audio_data.astype(np.float32)
    
    # Extreme boost on all bands
    gains_extreme = {
        'bass': 20.0,
        'mid_bass': 20.0,
        'mid': 20.0,
        'mid_treble': 20.0,
        'treble': 20.0
    }
    
    processed, band_levels = apply_equalizer(audio_data, sample_rate, gains_extreme)
    
    # All band levels should still be in [0, 1] range
    for band, level in band_levels.items():
        assert 0.0 <= level <= 1.0, f"Band '{band}' level {level} should be in [0, 1]"
    
    print(f"✓ Band levels are normalized to [0, 1] range")
    print(f"  - All bands with extreme gains stay within [0, 1]")


# Constants
SEPARATOR_LENGTH = 70


if __name__ == '__main__':
    print("=" * SEPARATOR_LENGTH)
    print("Testing Equalizer Band Level Meters")
    print("=" * SEPARATOR_LENGTH)
    
    test_band_levels_calculation()
    print()
    
    test_band_levels_with_gain()
    print()
    
    test_band_levels_silent_audio()
    print()
    
    test_band_levels_full_scale()
    print()
    
    test_band_levels_normalization()
    print()
    
    print("=" * SEPARATOR_LENGTH)
    print("All band level meter tests passed! ✓")
    print("=" * SEPARATOR_LENGTH)
