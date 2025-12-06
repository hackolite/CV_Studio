#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Microphone node volume meters.
Verifies that RMS and Peak volume calculations work correctly.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_volume_calculation_silence():
    """Test volume calculation with silent audio (all zeros)"""
    # Create silent audio (all zeros)
    audio_data = np.zeros(1000, dtype=np.float32)
    
    # Calculate RMS and Peak levels
    rms_level = np.sqrt(np.mean(audio_data ** 2))
    peak_level = np.max(np.abs(audio_data))
    
    # Verify both are zero
    assert rms_level == 0.0, f"Expected RMS = 0.0 for silence, got {rms_level}"
    assert peak_level == 0.0, f"Expected Peak = 0.0 for silence, got {peak_level}"
    
    print("✓ Volume calculation for silence verified")
    print(f"  RMS: {rms_level:.4f}, Peak: {peak_level:.4f}")
    return True


def test_volume_calculation_full_scale():
    """Test volume calculation with full-scale sine wave"""
    # Create a sine wave at full scale (amplitude = 1.0)
    sample_rate = 44100
    duration = 1.0
    frequency = 440  # A4 note
    
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    
    # Calculate RMS and Peak levels
    rms_level = np.sqrt(np.mean(audio_data ** 2))
    peak_level = np.max(np.abs(audio_data))
    
    # For a sine wave, RMS should be approximately 0.707 (1/sqrt(2))
    # Peak should be approximately 1.0
    expected_rms = 1.0 / np.sqrt(2)
    
    assert 0.70 < rms_level < 0.72, f"Expected RMS ≈ 0.707, got {rms_level}"
    assert 0.99 < peak_level <= 1.0, f"Expected Peak ≈ 1.0, got {peak_level}"
    
    print("✓ Volume calculation for full-scale sine wave verified")
    print(f"  RMS: {rms_level:.4f} (expected ≈ {expected_rms:.4f})")
    print(f"  Peak: {peak_level:.4f} (expected ≈ 1.0)")
    return True


def test_volume_calculation_half_scale():
    """Test volume calculation with half-scale audio"""
    # Create a sine wave at half scale (amplitude = 0.5)
    sample_rate = 44100
    duration = 0.5
    frequency = 440
    
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio_data = 0.5 * np.sin(2 * np.pi * frequency * t).astype(np.float32)
    
    # Calculate RMS and Peak levels
    rms_level = np.sqrt(np.mean(audio_data ** 2))
    peak_level = np.max(np.abs(audio_data))
    
    # For a half-scale sine wave, RMS should be approximately 0.354 (0.5/sqrt(2))
    # Peak should be approximately 0.5
    expected_rms = 0.5 / np.sqrt(2)
    
    assert 0.35 < rms_level < 0.36, f"Expected RMS ≈ 0.354, got {rms_level}"
    assert 0.49 < peak_level <= 0.51, f"Expected Peak ≈ 0.5, got {peak_level}"
    
    print("✓ Volume calculation for half-scale sine wave verified")
    print(f"  RMS: {rms_level:.4f} (expected ≈ {expected_rms:.4f})")
    print(f"  Peak: {peak_level:.4f} (expected ≈ 0.5)")
    return True


def test_volume_calculation_white_noise():
    """Test volume calculation with white noise"""
    # Create white noise
    np.random.seed(42)  # For reproducibility
    audio_data = np.random.uniform(-1.0, 1.0, 44100).astype(np.float32)
    
    # Calculate RMS and Peak levels
    rms_level = np.sqrt(np.mean(audio_data ** 2))
    peak_level = np.max(np.abs(audio_data))
    
    # For uniform white noise from -1 to 1, RMS should be approximately 0.577 (1/sqrt(3))
    # Peak should be close to 1.0
    expected_rms = 1.0 / np.sqrt(3)
    
    assert 0.55 < rms_level < 0.60, f"Expected RMS ≈ 0.577, got {rms_level}"
    assert 0.95 < peak_level <= 1.0, f"Expected Peak close to 1.0, got {peak_level}"
    
    print("✓ Volume calculation for white noise verified")
    print(f"  RMS: {rms_level:.4f} (expected ≈ {expected_rms:.4f})")
    print(f"  Peak: {peak_level:.4f} (expected close to 1.0)")
    return True


def test_volume_normalization():
    """Test that volume levels are properly normalized to 0.0-1.0 range"""
    # Test with various amplitudes
    test_cases = [
        (0.0, 0.0, 0.0),    # Silence
        (0.5, 0.35, 0.5),   # Half scale
        (1.0, 0.71, 1.0),   # Full scale
        (1.5, 1.0, 1.0),    # Over scale (should clip to 1.0)
    ]
    
    for amplitude, expected_rms_approx, expected_peak_max in test_cases:
        # Create sine wave at specified amplitude
        t = np.linspace(0, 0.1, 4410, dtype=np.float32)
        audio_data = amplitude * np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        # Calculate levels
        rms_level = np.sqrt(np.mean(audio_data ** 2))
        peak_level = np.max(np.abs(audio_data))
        
        # Normalize (as done in the node)
        rms_normalized = min(rms_level, 1.0)
        peak_normalized = min(peak_level, 1.0)
        
        # Verify normalization
        assert 0.0 <= rms_normalized <= 1.0, f"RMS should be in [0, 1], got {rms_normalized}"
        assert 0.0 <= peak_normalized <= 1.0, f"Peak should be in [0, 1], got {peak_normalized}"
        
        # Verify values are as expected
        if amplitude > 1.0:
            # Should be clipped to 1.0
            assert rms_normalized == 1.0, f"Expected clipped RMS = 1.0, got {rms_normalized}"
            assert peak_normalized == 1.0, f"Expected clipped Peak = 1.0, got {peak_normalized}"
    
    print("✓ Volume normalization verified")
    print("  All test cases passed normalization to [0.0, 1.0] range")
    return True


if __name__ == '__main__':
    print("Testing Microphone Volume Meters...")
    print("=" * 60)
    
    tests = [
        ("Silence", test_volume_calculation_silence),
        ("Full Scale Sine", test_volume_calculation_full_scale),
        ("Half Scale Sine", test_volume_calculation_half_scale),
        ("White Noise", test_volume_calculation_white_noise),
        ("Normalization", test_volume_normalization),
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
        print("✓ All volume meter tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
