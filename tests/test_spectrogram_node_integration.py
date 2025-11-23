#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for Spectrogram Node with audio processing
"""
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_audio_signal(duration=1.0, sample_rate=44100, frequency=440.0):
    """
    Create a test audio signal (sine wave).
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz
        
    Returns:
        Dictionary with 'samples' and 'sample_rate'
    """
    t = np.linspace(0, duration, int(sample_rate * duration))
    samples = np.sin(2 * np.pi * frequency * t)
    
    # Convert to int16 format (as expected by audio processing)
    samples_int16 = (samples * 32767).astype(np.int16)
    
    return {
        'samples': samples_int16,
        'sample_rate': sample_rate
    }


def test_spectrogram_generation():
    """Test that the SpectrogramNode can generate a spectrogram from audio"""
    from node.AudioProcessNode.node_spectrogram_node import SpectrogramNode
    
    # Create a test audio signal
    audio_data = create_test_audio_signal(duration=1.0, sample_rate=44100, frequency=440.0)
    
    # Instantiate node
    node = SpectrogramNode()
    
    # Test spectrogram generation
    try:
        spectrogram_image = node._generate_spectrogram(
            audio_data,
            fft_size=1024,
            colormap='jet'
        )
        
        assert spectrogram_image is not None, "Spectrogram image should not be None"
        assert isinstance(spectrogram_image, np.ndarray), "Spectrogram should be a numpy array"
        assert len(spectrogram_image.shape) == 3, "Spectrogram should be a 3D array (H, W, C)"
        assert spectrogram_image.shape[2] == 3, "Spectrogram should have 3 color channels (BGR)"
        
        print(f"✓ Spectrogram generated successfully")
        print(f"  Shape: {spectrogram_image.shape}")
        print(f"  Dtype: {spectrogram_image.dtype}")
        
        return True
    except Exception as e:
        print(f"✗ Error generating spectrogram: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_spectrogram_different_fft_sizes():
    """Test spectrogram generation with different FFT sizes"""
    from node.AudioProcessNode.node_spectrogram_node import SpectrogramNode
    
    audio_data = create_test_audio_signal(duration=1.0, sample_rate=44100, frequency=440.0)
    node = SpectrogramNode()
    
    fft_sizes = [512, 1024, 2048, 4096]
    
    for fft_size in fft_sizes:
        try:
            spectrogram_image = node._generate_spectrogram(
                audio_data,
                fft_size=fft_size,
                colormap='jet'
            )
            assert spectrogram_image is not None, f"FFT size {fft_size} failed"
            print(f"✓ FFT size {fft_size}: OK")
        except Exception as e:
            print(f"✗ FFT size {fft_size}: Failed - {e}")
            return False
    
    return True


def test_spectrogram_different_colormaps():
    """Test spectrogram generation with different colormaps"""
    from node.AudioProcessNode.node_spectrogram_node import SpectrogramNode
    
    audio_data = create_test_audio_signal(duration=1.0, sample_rate=44100, frequency=440.0)
    node = SpectrogramNode()
    
    colormaps = ['jet', 'viridis', 'plasma', 'inferno', 'magma', 'hot', 'cool']
    
    for colormap in colormaps:
        try:
            spectrogram_image = node._generate_spectrogram(
                audio_data,
                fft_size=1024,
                colormap=colormap
            )
            assert spectrogram_image is not None, f"Colormap {colormap} failed"
            print(f"✓ Colormap {colormap}: OK")
        except Exception as e:
            print(f"✗ Colormap {colormap}: Failed - {e}")
            return False
    
    return True


def test_spectrogram_with_empty_audio():
    """Test that the node handles empty audio gracefully"""
    from node.AudioProcessNode.node_spectrogram_node import SpectrogramNode
    
    node = SpectrogramNode()
    
    # Test with None
    result = node._generate_spectrogram(None)
    assert result is None, "Should return None for None input"
    
    # Test with empty audio data
    empty_audio = {
        'samples': np.array([]),
        'sample_rate': 44100
    }
    result = node._generate_spectrogram(empty_audio)
    assert result is None, "Should return None for empty samples"
    
    print("✓ Empty audio handling: OK")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Spectrogram Node Audio Processing")
    print("=" * 60)
    
    all_passed = True
    
    print("\n1. Testing basic spectrogram generation...")
    all_passed &= test_spectrogram_generation()
    
    print("\n2. Testing different FFT sizes...")
    all_passed &= test_spectrogram_different_fft_sizes()
    
    print("\n3. Testing different colormaps...")
    all_passed &= test_spectrogram_different_colormaps()
    
    print("\n4. Testing empty audio handling...")
    all_passed &= test_spectrogram_with_empty_audio()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All spectrogram node integration tests passed!")
        print("=" * 60)
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        sys.exit(1)
