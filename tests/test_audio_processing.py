#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for audio processing utilities.

This module tests:
- Audio chunking functionality
- Spectrogram generation from chunks
- Video creation from spectrograms
- Image annotation with classifications
"""

import pytest
import sys
import os
import numpy as np
import tempfile
import shutil
import soundfile as sf

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.audio_processing import (
    chunk_audio_wav_or_mp3,
    fourier_transformation,
    make_logscale,
    plot_spectrogram,
    process_chunks_to_spectrograms,
    annotate_image_with_classification,
    create_video_from_spectrograms,
    get_linux_font
)


def create_test_audio_file(duration=2.0, sample_rate=22050, frequency=440.0):
    """
    Create a temporary audio file with a sine wave.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz
        
    Returns:
        Path to the temporary audio file
    """
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_file.close()
    
    # Write audio to file
    sf.write(temp_file.name, audio, sample_rate)
    
    return temp_file.name


def test_fourier_transformation():
    """Test the Short-Time Fourier Transform implementation"""
    # Create a simple signal
    sample_rate = 22050
    duration = 1.0
    frequency = 440.0
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * frequency * t)
    
    # Apply STFT
    frameSize = 1024
    result = fourier_transformation(signal, frameSize)
    
    # Check output shape
    assert result.ndim == 2, "STFT should return 2D array"
    assert result.shape[1] == frameSize // 2 + 1, "Frequency bins should be frameSize/2 + 1"
    
    print("✓ fourier_transformation test passed")


def test_make_logscale():
    """Test logarithmic frequency scaling"""
    # Create a test spectrogram
    timebins = 100
    freqbins = 513  # Typical for 1024 FFT
    spec = np.random.randn(timebins, freqbins) + 1j * np.random.randn(timebins, freqbins)
    
    # Apply log scaling
    newspec, freqs = make_logscale(spec, sr=22050, factor=20.0)
    
    # Check output
    assert newspec.ndim == 2, "Output should be 2D"
    assert newspec.shape[0] == timebins, "Time bins should be preserved"
    assert len(freqs) == newspec.shape[1], "Frequency list should match new bins"
    
    print("✓ make_logscale test passed")


def test_chunk_audio_wav_or_mp3():
    """Test audio chunking functionality"""
    # Create a test audio file (2 seconds)
    audio_file = create_test_audio_file(duration=2.0)
    output_folder = tempfile.mkdtemp()
    
    try:
        # Chunk the audio
        num_chunks = chunk_audio_wav_or_mp3(
            audio_file, 
            output_folder, 
            chunk_duration=0.5,  # 0.5 second chunks
            step_duration=0.25   # 0.25 second steps
        )
        
        # Check that chunks were created
        assert num_chunks > 0, "Should create at least one chunk"
        
        # Check that chunk files exist
        chunk_files = [f for f in os.listdir(output_folder) if f.startswith('chunk_')]
        assert len(chunk_files) == num_chunks, f"Expected {num_chunks} files, found {len(chunk_files)}"
        
        # Check chunk file content
        first_chunk = os.path.join(output_folder, 'chunk_1.wav')
        assert os.path.exists(first_chunk), "First chunk should exist"
        
        # Load and verify chunk
        data, rate = sf.read(first_chunk)
        assert len(data) > 0, "Chunk should contain audio data"
        assert rate == 22050, "Sample rate should be preserved"
        
        print(f"✓ chunk_audio_wav_or_mp3 test passed ({num_chunks} chunks created)")
        
    finally:
        # Clean up
        if os.path.exists(audio_file):
            os.unlink(audio_file)
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)


def test_plot_spectrogram():
    """Test spectrogram plotting functionality"""
    # Create a test audio file
    audio_file = create_test_audio_file(duration=1.0)
    output_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    output_image.close()
    
    try:
        # Generate spectrogram
        ims = plot_spectrogram(audio_file, plotpath=output_image.name, binsize=1024, colormap="jet")
        
        # Check that output was created
        assert os.path.exists(output_image.name), "Spectrogram image should be created"
        assert os.path.getsize(output_image.name) > 0, "Spectrogram image should not be empty"
        
        # Check spectrogram matrix
        assert ims.ndim == 2, "Spectrogram should be 2D array"
        assert ims.shape[0] > 0 and ims.shape[1] > 0, "Spectrogram should have non-zero dimensions"
        
        print("✓ plot_spectrogram test passed")
        
    finally:
        # Clean up
        if os.path.exists(audio_file):
            os.unlink(audio_file)
        if os.path.exists(output_image.name):
            os.unlink(output_image.name)


def test_process_chunks_to_spectrograms():
    """Test batch spectrogram generation from chunks"""
    # Create audio chunks folder
    chunks_folder = tempfile.mkdtemp()
    spectro_folder = tempfile.mkdtemp()
    
    try:
        # Create a few test audio chunks
        for i in range(1, 4):
            audio_file = create_test_audio_file(duration=0.5)
            chunk_path = os.path.join(chunks_folder, f'chunk_{i}.wav')
            os.rename(audio_file, chunk_path)
        
        # Process chunks to spectrograms
        num_spectros = process_chunks_to_spectrograms(chunks_folder, spectro_folder)
        
        # Check results
        assert num_spectros == 3, f"Expected 3 spectrograms, got {num_spectros}"
        
        # Verify spectrogram files exist
        for i in range(1, 4):
            spectro_path = os.path.join(spectro_folder, f'chunk_{i}.png')
            assert os.path.exists(spectro_path), f"Spectrogram {i} should exist"
            assert os.path.getsize(spectro_path) > 0, f"Spectrogram {i} should not be empty"
        
        print("✓ process_chunks_to_spectrograms test passed")
        
    finally:
        # Clean up
        if os.path.exists(chunks_folder):
            shutil.rmtree(chunks_folder)
        if os.path.exists(spectro_folder):
            shutil.rmtree(spectro_folder)


def test_get_linux_font():
    """Test Linux font loading"""
    font = get_linux_font(size=24)
    
    # Font should not be None
    assert font is not None, "Font should be loaded"
    
    print("✓ get_linux_font test passed")


def test_annotate_image_with_classification():
    """Test image annotation with classification results"""
    # Create a simple test image
    from PIL import Image
    test_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    test_image.close()
    
    output_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    output_image.close()
    
    try:
        # Create a simple test image (640x480 white)
        img = Image.new('RGB', (640, 480), color='white')
        img.save(test_image.name)
        
        # Mock predictions
        predictions = [
            ("Dog", 0.95),
            ("Cat", 0.03),
            ("Bird", 0.01)
        ]
        
        # Annotate image
        annotate_image_with_classification(test_image.name, output_image.name, predictions)
        
        # Check that output was created
        assert os.path.exists(output_image.name), "Annotated image should be created"
        assert os.path.getsize(output_image.name) > 0, "Annotated image should not be empty"
        
        # Verify output is larger (due to text)
        original_size = os.path.getsize(test_image.name)
        annotated_size = os.path.getsize(output_image.name)
        # Annotated image should be different size (not necessarily larger due to compression)
        assert annotated_size > 0, "Annotated image should have content"
        
        print("✓ annotate_image_with_classification test passed")
        
    finally:
        # Clean up
        if os.path.exists(test_image.name):
            os.unlink(test_image.name)
        if os.path.exists(output_image.name):
            os.unlink(output_image.name)


def test_create_video_from_spectrograms():
    """Test video creation from spectrogram images"""
    # Create temp folder with test images
    spectro_folder = tempfile.mkdtemp()
    output_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    output_video.close()
    
    try:
        # Create a few test spectrogram images
        from PIL import Image
        for i in range(1, 6):
            img = Image.new('RGB', (640, 480), color=(i*50, 100, 150))
            img.save(os.path.join(spectro_folder, f'chunk_{i}.png'))
        
        # Create video
        video_path = create_video_from_spectrograms(spectro_folder, output_video.name, fps=4)
        
        # Check that video was created
        assert video_path is not None, "Video path should not be None"
        assert os.path.exists(video_path), "Video file should be created"
        assert os.path.getsize(video_path) > 0, "Video file should not be empty"
        
        print("✓ create_video_from_spectrograms test passed")
        
    finally:
        # Clean up
        if os.path.exists(spectro_folder):
            shutil.rmtree(spectro_folder)
        if os.path.exists(output_video.name):
            os.unlink(output_video.name)


def test_full_workflow():
    """Test the complete audio-to-video workflow"""
    # Create temporary directories
    audio_file = create_test_audio_file(duration=2.0)
    chunks_folder = tempfile.mkdtemp()
    spectro_folder = tempfile.mkdtemp()
    output_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    output_video.close()
    
    try:
        print("\n--- Full Workflow Test ---")
        
        # Step 1: Chunk audio
        print("Step 1: Chunking audio...")
        num_chunks = chunk_audio_wav_or_mp3(
            audio_file, 
            chunks_folder, 
            chunk_duration=0.5,
            step_duration=0.25
        )
        assert num_chunks > 0, "Should create chunks"
        print(f"  Created {num_chunks} chunks")
        
        # Step 2: Generate spectrograms
        print("Step 2: Generating spectrograms...")
        num_spectros = process_chunks_to_spectrograms(chunks_folder, spectro_folder)
        assert num_spectros == num_chunks, "Should create one spectrogram per chunk"
        print(f"  Created {num_spectros} spectrograms")
        
        # Step 3: Create video
        print("Step 3: Creating video...")
        video_path = create_video_from_spectrograms(spectro_folder, output_video.name, fps=4)
        assert video_path is not None, "Should create video"
        assert os.path.exists(video_path), "Video file should exist"
        print(f"  Created video: {video_path}")
        
        print("✓ Full workflow test passed")
        
    finally:
        # Clean up
        if os.path.exists(audio_file):
            os.unlink(audio_file)
        if os.path.exists(chunks_folder):
            shutil.rmtree(chunks_folder)
        if os.path.exists(spectro_folder):
            shutil.rmtree(spectro_folder)
        if os.path.exists(output_video.name):
            os.unlink(output_video.name)


if __name__ == '__main__':
    print("Running audio processing tests...\n")
    
    try:
        test_fourier_transformation()
        test_make_logscale()
        test_chunk_audio_wav_or_mp3()
        test_plot_spectrogram()
        test_process_chunks_to_spectrograms()
        test_get_linux_font()
        test_annotate_image_with_classification()
        test_create_video_from_spectrograms()
        test_full_workflow()
        
        print("\n" + "="*60)
        print("All audio processing tests passed! ✓")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
