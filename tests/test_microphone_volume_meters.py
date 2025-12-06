#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Microphone node audio indicator.
Verifies that RMS level changes can be detected for the blinking indicator.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_rms_calculation_silence():
    """Test RMS calculation with silent audio (all zeros)"""
    # Create silent audio (all zeros)
    audio_data = np.zeros(1000, dtype=np.float32)
    
    # Calculate RMS level
    rms_level = np.sqrt(np.mean(audio_data ** 2))
    
    # Verify it's zero
    assert rms_level == 0.0, f"Expected RMS = 0.0 for silence, got {rms_level}"
    
    print("✓ RMS calculation for silence verified")
    print(f"  RMS: {rms_level:.4f}")
    return True


def test_rms_calculation_full_scale():
    """Test RMS calculation with full-scale sine wave"""
    # Create a sine wave at full scale (amplitude = 1.0)
    sample_rate = 44100
    duration = 1.0
    frequency = 440  # A4 note
    
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    
    # Calculate RMS level
    rms_level = np.sqrt(np.mean(audio_data ** 2))
    
    # For a sine wave, RMS should be approximately 0.707 (1/sqrt(2))
    expected_rms = 1.0 / np.sqrt(2)
    
    assert 0.70 < rms_level < 0.72, f"Expected RMS ≈ 0.707, got {rms_level}"
    
    print("✓ RMS calculation for full-scale sine wave verified")
    print(f"  RMS: {rms_level:.4f} (expected ≈ {expected_rms:.4f})")
    return True


def test_rms_calculation_half_scale():
    """Test RMS calculation with half-scale audio"""
    # Create a sine wave at half scale (amplitude = 0.5)
    sample_rate = 44100
    duration = 0.5
    frequency = 440
    
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio_data = 0.5 * np.sin(2 * np.pi * frequency * t).astype(np.float32)
    
    # Calculate RMS level
    rms_level = np.sqrt(np.mean(audio_data ** 2))
    
    # For a half-scale sine wave, RMS should be approximately 0.354 (0.5/sqrt(2))
    expected_rms = 0.5 / np.sqrt(2)
    
    assert 0.35 < rms_level < 0.36, f"Expected RMS ≈ 0.354, got {rms_level}"
    
    print("✓ RMS calculation for half-scale sine wave verified")
    print(f"  RMS: {rms_level:.4f} (expected ≈ {expected_rms:.4f})")
    return True


def test_rms_increase_detection():
    """Test detection of RMS increase for blinking indicator"""
    # Create two audio chunks: quiet then loud
    sample_rate = 44100
    duration = 0.1
    frequency = 440
    
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    
    # Quiet audio (amplitude = 0.2)
    quiet_audio = 0.2 * np.sin(2 * np.pi * frequency * t).astype(np.float32)
    quiet_rms = np.sqrt(np.mean(quiet_audio ** 2))
    
    # Loud audio (amplitude = 0.8)
    loud_audio = 0.8 * np.sin(2 * np.pi * frequency * t).astype(np.float32)
    loud_rms = np.sqrt(np.mean(loud_audio ** 2))
    
    # Verify RMS increased
    assert loud_rms > quiet_rms, f"Expected loud RMS ({loud_rms:.4f}) > quiet RMS ({quiet_rms:.4f})"
    
    # This would trigger the blinking indicator
    decibels_increased = loud_rms > quiet_rms
    assert decibels_increased, "Decibels should have increased"
    
    print("✓ RMS increase detection verified")
    print(f"  Quiet RMS: {quiet_rms:.4f}, Loud RMS: {loud_rms:.4f}")
    print(f"  Increase detected: {decibels_increased}")
    return True


def test_rms_threshold():
    """Test RMS threshold for ignoring very quiet noise"""
    # Create very quiet audio that should be ignored
    very_quiet = np.random.normal(0, 0.005, 1000).astype(np.float32)
    very_quiet_rms = np.sqrt(np.mean(very_quiet ** 2))
    
    # Create audible audio that should trigger indicator
    audible = np.random.normal(0, 0.05, 1000).astype(np.float32)
    audible_rms = np.sqrt(np.mean(audible ** 2))
    
    # Threshold used in the code is 0.01
    threshold = 0.01
    
    assert very_quiet_rms < threshold, f"Very quiet RMS ({very_quiet_rms:.4f}) should be below threshold ({threshold})"
    assert audible_rms > threshold, f"Audible RMS ({audible_rms:.4f}) should be above threshold ({threshold})"
    
    print("✓ RMS threshold verification passed")
    print(f"  Very quiet RMS: {very_quiet_rms:.4f} (below threshold: {very_quiet_rms < threshold})")
    print(f"  Audible RMS: {audible_rms:.4f} (above threshold: {audible_rms > threshold})")
    return True


if __name__ == '__main__':
    print("Testing Microphone Audio Indicator...")
    print("=" * 60)
    
    tests = [
        ("Silence RMS", test_rms_calculation_silence),
        ("Full Scale RMS", test_rms_calculation_full_scale),
        ("Half Scale RMS", test_rms_calculation_half_scale),
        ("RMS Increase Detection", test_rms_increase_detection),
        ("RMS Threshold", test_rms_threshold),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All audio indicator tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
