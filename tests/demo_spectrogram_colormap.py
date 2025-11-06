#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration script for spectrogram colormap feature.

This script generates synthetic audio signals, computes spectrograms, 
applies different colormaps, and saves the results for visual comparison.
"""

import sys
import os
import numpy as np
import cv2
import librosa
import tempfile
import soundfile as sf

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.spectrogram_utils import apply_colormap_to_spectrogram


def generate_test_signal(duration=3.0, sr=22050):
    """
    Generate a test signal with multiple frequency components.
    
    Args:
        duration: Duration in seconds
        sr: Sample rate in Hz
    
    Returns:
        np.ndarray: Audio signal
    """
    t = np.linspace(0, duration, int(sr * duration))
    
    # Create a signal with multiple frequency components
    signal = np.zeros_like(t)
    
    # Add a chirp (frequency sweep)
    f_start = 200  # Hz
    f_end = 2000   # Hz
    chirp = np.sin(2 * np.pi * (f_start + (f_end - f_start) * t / duration) * t)
    signal += chirp * 0.5
    
    # Add some harmonic tones
    for freq in [440, 880, 1320]:  # A4 and harmonics
        segment_start = int(sr * 0.5)
        segment_end = int(sr * 2.0)
        signal[segment_start:segment_end] += 0.3 * np.sin(2 * np.pi * freq * t[segment_start:segment_end])
    
    # Add some noise
    signal += 0.05 * np.random.randn(len(t))
    
    # Normalize
    signal = signal / np.max(np.abs(signal))
    
    return signal


def compute_spectrogram(signal, sr=22050):
    """
    Compute a spectrogram from audio signal using librosa.
    
    Args:
        signal: Audio signal
        sr: Sample rate
    
    Returns:
        np.ndarray: 2D spectrogram in dB scale
    """
    # Compute STFT
    D = librosa.stft(signal, n_fft=2048, hop_length=512)
    
    # Convert to dB scale
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
    
    return S_db


def main():
    """Generate and save colored spectrograms with different colormaps."""
    print("Generating test signal...")
    signal = generate_test_signal(duration=3.0)
    sr = 22050
    
    # Save audio file for reference
    audio_path = os.path.join(tempfile.gettempdir(), 'demo_signal.wav')
    sf.write(audio_path, signal, sr)
    print(f"Saved test audio to: {audio_path}")
    
    print("\nComputing spectrogram...")
    spectrogram = compute_spectrogram(signal, sr)
    print(f"Spectrogram shape: {spectrogram.shape}")
    
    # Test different colormaps
    colormaps = ['INFERNO', 'VIRIDIS', 'JET', 'MAGMA', 'PLASMA', 'HOT']
    
    print("\nApplying colormaps and saving images:")
    for cmap_name in colormaps:
        print(f"  - {cmap_name}...", end=' ')
        
        # Apply colormap
        colored_img = apply_colormap_to_spectrogram(
            spectrogram, 
            method='cv2', 
            cmap=cmap_name
        )
        
        # Verify output
        assert colored_img.shape[2] == 3, "Should have 3 channels (RGB)"
        assert colored_img.dtype == np.uint8, "Should be uint8"
        
        # Check that channels are not identical (truly colored)
        r, g, b = colored_img[..., 0], colored_img[..., 1], colored_img[..., 2]
        assert not np.all(r == g), "Red and Green channels should differ"
        
        # Convert RGB to BGR for saving with OpenCV
        colored_bgr = cv2.cvtColor(colored_img, cv2.COLOR_RGB2BGR)
        
        # Save image
        output_path = os.path.join(
            tempfile.gettempdir(), 
            f'demo_spectrogram_{cmap_name.lower()}.png'
        )
        cv2.imwrite(output_path, colored_bgr)
        
        print(f"✓ Saved to {output_path}")
    
    print("\n" + "="*70)
    print("Demo completed successfully!")
    print("="*70)
    print("\nKey features demonstrated:")
    print("  ✓ Synthetic audio signal generation with multiple frequency components")
    print("  ✓ Spectrogram computation using librosa STFT")
    print("  ✓ Colormap application with multiple OpenCV colormaps")
    print("  ✓ RGB output validation (shape, dtype, non-grayscale)")
    print("  ✓ Image file export for visual inspection")
    print("\nColormap comparison:")
    print("  - INFERNO: Perceptually uniform, good for data visualization")
    print("  - VIRIDIS: Colorblind-friendly, perceptually uniform")
    print("  - JET: Classic rainbow colormap (not perceptually uniform)")
    print("  - MAGMA: Similar to INFERNO but with more purple tones")
    print("  - PLASMA: Bright, high-contrast perceptually uniform colormap")
    print("  - HOT: Red-yellow-white progression, good for thermal-like data")
    print("\nYou can now visually compare the spectrograms in:")
    print(f"  {tempfile.gettempdir()}/demo_spectrogram_*.png")


if __name__ == '__main__':
    main()
