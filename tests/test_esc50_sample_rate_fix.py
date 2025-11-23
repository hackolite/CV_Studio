#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test to verify ESC-50 sample rate fix for improved classification accuracy.

This test verifies that:
1. Audio extraction uses 44100 Hz (ESC-50 native sample rate)
2. Spectrogram generation uses 44100 Hz by default
3. Parameters match the user's working training code
"""

import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_video_node_sample_rate():
    """Test that video node extracts audio at 44100 Hz (ESC-50 native)"""
    video_node_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'InputNode', 
        'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check ffmpeg sample rate is 44100
    ffmpeg_pattern = r'"-ar",\s*"44100"'
    assert re.search(ffmpeg_pattern, content), \
        "Video node should use -ar 44100 for ffmpeg audio extraction (ESC-50 native)"
    
    # Check librosa fallback uses 44100
    librosa_pattern = r'librosa\.load\([^,]+,\s*sr=44100\)'
    assert re.search(librosa_pattern, content), \
        "Video node should use sr=44100 for librosa fallback (ESC-50 native)"
    
    print("✓ Video node extracts audio at 44100 Hz (ESC-50 native sample rate)")


def test_spectrogram_node_default_sample_rate():
    """Test that spectrogram node uses 44100 Hz default sample rate"""
    spectrogram_node_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'AudioProcessNode', 
        'node_spectrogram.py'
    )
    
    with open(spectrogram_node_path, 'r') as f:
        content = f.read()
    
    # Check create_spectrogram_custom default
    custom_pattern = r'def create_spectrogram_custom\([^)]*sample_rate=44100'
    assert re.search(custom_pattern, content), \
        "create_spectrogram_custom should default to sample_rate=44100 (ESC-50 native)"
    
    # Check default in update method
    update_pattern = r'audio_data,\s*sample_rate\s*=\s*None,\s*44100'
    # Look for the default fallback value
    assert '44100' in content, \
        "Spectrogram node should use 44100 Hz default"
    
    print("✓ Spectrogram node uses 44100 Hz default sample rate")


def test_spectrogram_utils_sample_rate():
    """Test that spectrogram_utils uses 44100 Hz default"""
    utils_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'InputNode', 
        'spectrogram_utils.py'
    )
    
    with open(utils_path, 'r') as f:
        content = f.read()
    
    # Check create_spectrogram_from_audio default
    pattern = r'def create_spectrogram_from_audio\([^)]*sample_rate=44100'
    assert re.search(pattern, content), \
        "create_spectrogram_from_audio should default to sample_rate=44100 (ESC-50 native)"
    
    print("✓ spectrogram_utils uses 44100 Hz default sample rate")


def test_spectrogram_parameters():
    """Test that spectrogram uses correct parameters matching training code"""
    utils_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'InputNode', 
        'spectrogram_utils.py'
    )
    
    with open(utils_path, 'r') as f:
        content = f.read()
    
    # Check binsize default (2**10 = 1024)
    binsize_pattern = r'binsize=2\*\*10'
    assert re.search(binsize_pattern, content), \
        "create_spectrogram_from_audio should use binsize=2**10 (1024, matching training code)"
    
    # Check factor=1.0 for log scale
    factor_pattern = r'factor=1\.0'
    assert re.search(factor_pattern, content), \
        "make_logscale should use factor=1.0 (matching training code)"
    
    # Check JET colormap is used
    jet_pattern = r"colormap=['\"]jet['\"]"
    assert re.search(jet_pattern, content, re.IGNORECASE), \
        "Default colormap should be 'jet' (matching training code)"
    
    print("✓ Spectrogram parameters match training code (binsize=1024, factor=1.0, jet colormap)")


def test_n_fft_parameter():
    """Test that n_fft=1024 is used in spectrogram node"""
    spectrogram_node_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'AudioProcessNode', 
        'node_spectrogram.py'
    )
    
    with open(spectrogram_node_path, 'r') as f:
        content = f.read()
    
    # Check n_fft default
    nfft_pattern = r'n_fft=1024'
    assert re.search(nfft_pattern, content), \
        "create_spectrogram_custom should use n_fft=1024 (matching training code binsize=2**10)"
    
    print("✓ Spectrogram node uses n_fft=1024 (matching training code)")


def test_audio_dict_default_sample_rate():
    """Test that audio_dict defaults are consistent"""
    spectrogram_node_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'AudioProcessNode', 
        'node_spectrogram.py'
    )
    
    with open(spectrogram_node_path, 'r') as f:
        content = f.read()
    
    # Check get() method defaults
    get_pattern = r"\.get\(['\"]sample_rate['\"],\s*44100\)"
    assert re.search(get_pattern, content), \
        "audio_dict.get('sample_rate', ...) should default to 44100"
    
    print("✓ Audio dictionary defaults to 44100 Hz sample rate")


if __name__ == '__main__':
    print("Testing ESC-50 Sample Rate Fix...\n")
    print("="*70)
    
    try:
        test_video_node_sample_rate()
        test_spectrogram_node_default_sample_rate()
        test_spectrogram_utils_sample_rate()
        test_spectrogram_parameters()
        test_n_fft_parameter()
        test_audio_dict_default_sample_rate()
        
        print("="*70)
        print("\n✅ All tests passed!\n")
        print("Summary:")
        print("- Audio extraction: 44100 Hz (ESC-50 native)")
        print("- Spectrogram generation: 44100 Hz default")
        print("- FFT parameters: n_fft=1024, factor=1.0")
        print("- Colormap: JET (matching training code)")
        print("\nThe ESC-50 classification should now work better because:")
        print("1. Sample rate matches the ESC-50 dataset (44100 Hz)")
        print("2. Spectrogram parameters match the training code")
        print("3. No resampling artifacts that could affect classification")
        
    except AssertionError as e:
        print("="*70)
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print("="*70)
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
