#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test to verify that all audio chunks are exactly 5 seconds in duration"""

import sys
import os
import tempfile
import numpy as np
import soundfile as sf
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_video_with_audio(duration_seconds=12.5, fps=24, sample_rate=22050):
    """Create a test video file with audio for testing purposes
    
    Args:
        duration_seconds: Duration of the video in seconds
        fps: Frames per second
        sample_rate: Audio sample rate
        
    Returns:
        Path to the temporary video file
    """
    # Create temporary file
    temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_video.close()
    
    # Generate synthetic audio (sine wave at 440 Hz)
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples)
    audio_data = np.sin(2 * np.pi * 440 * t) * 0.3  # 440 Hz tone at 30% volume
    
    # Save audio to temporary WAV file
    temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_audio.name, audio_data, sample_rate)
    temp_audio.close()
    
    try:
        # Create video with ffmpeg
        # Create a simple black video with the audio
        subprocess.run([
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=black:s=640x480:r={fps}:d={duration_seconds}',
            '-i', temp_audio.name,
            '-c:v', 'libx264', '-c:a', 'aac',
            '-shortest',
            temp_video.name
        ], check=True, capture_output=True)
        
    finally:
        # Clean up temporary audio file
        if os.path.exists(temp_audio.name):
            os.unlink(temp_audio.name)
    
    return temp_video.name


def test_audio_chunks_are_5_seconds():
    """Test that the video node creates chunks that are all exactly 5 seconds"""
    from node.InputNode.node_video import VideoNode
    
    # Create a test video with 12.5 seconds of audio
    # With 5s chunks and 5s steps (no overlap): chunks at 0s, 5s, 10s (3 chunks)
    # Chunk 0: 0-5s (full)
    # Chunk 1: 5-10s (full)
    # Chunk 2: 10-12.5s (2.5s padded to 5s)
    video_path = create_test_video_with_audio(duration_seconds=12.5)
    
    try:
        node = VideoNode()
        node_id = "test_node_123"
        
        # Mock the opencv_setting_dict
        node._opencv_setting_dict = {
            'input_window_width': 240,
            'input_window_height': 135,
            'use_pref_counter': False
        }
        
        # Preprocess the video with no overlap
        node._preprocess_video(node_id, video_path, chunk_duration=5.0, step_duration=5.0)
        
        # Check that chunk paths were created (WAV-based storage)
        assert node_id in node._audio_chunk_paths, "Audio chunk paths should be created"
        assert node_id in node._chunk_metadata, "Chunk metadata should be created"
        
        chunk_paths = node._audio_chunk_paths[node_id]
        metadata = node._chunk_metadata[node_id]
        
        # Get the sample rate from metadata
        sr = metadata['sr']
        expected_chunk_samples = int(5.0 * sr)
        
        print(f"\nTest Results:")
        print(f"  Total chunks created: {len(chunk_paths)}")
        print(f"  Sample rate: {sr} Hz")
        print(f"  Expected samples per chunk: {expected_chunk_samples}")
        
        # Verify each chunk WAV file is exactly 5 seconds
        all_chunks_valid = True
        for idx, chunk_path in enumerate(chunk_paths):
            # Load WAV file
            chunk, _ = sf.read(chunk_path)
            chunk_duration = len(chunk) / sr
            is_valid = len(chunk) == expected_chunk_samples
            
            if not is_valid:
                print(f"  ❌ Chunk {idx}: {len(chunk)} samples ({chunk_duration:.3f}s) - INVALID")
                all_chunks_valid = False
            else:
                print(f"  ✅ Chunk {idx}: {len(chunk)} samples ({chunk_duration:.3f}s) [WAV file]")
        
        # Assert all chunks are valid
        assert all_chunks_valid, "All chunks should be exactly 5 seconds"
        
        # For 12.5 seconds of audio with 5s chunks and 5s steps (no overlap):
        # Chunk 0: 0-5s (full)
        # Chunk 1: 5-10s (full)
        # Chunk 2: 10-12.5s (2.5s padded to 5s)
        # Total: 3 chunks
        expected_num_chunks = 3
        assert len(chunk_paths) == expected_num_chunks, \
            f"Expected {expected_num_chunks} chunks for 12.5s audio with no overlap, got {len(chunk_paths)}"
        
        print(f"\n✅ All {len(chunk_paths)} audio chunks are exactly 5 seconds (saved as WAV files)!")
        
        # Clean up audio chunks
        node._cleanup_audio_chunks(node_id)
        
    finally:
        # Clean up the temporary video file
        if os.path.exists(video_path):
            os.unlink(video_path)


def test_audio_chunks_exact_multiple():
    """Test that the video node handles audio that's exactly a multiple of chunk duration"""
    from node.InputNode.node_video import VideoNode
    
    # Create a test video with exactly 10 seconds of audio
    # With 5s chunks and 5s steps (no overlap): chunks at 0s, 5s (2 full chunks)
    # Total: 2 chunks (exactly fits with no remainder)
    video_path = create_test_video_with_audio(duration_seconds=10.0)
    
    try:
        node = VideoNode()
        node_id = "test_node_456"
        
        # Mock the opencv_setting_dict
        node._opencv_setting_dict = {
            'input_window_width': 240,
            'input_window_height': 135,
            'use_pref_counter': False
        }
        
        # Preprocess the video with no overlap
        node._preprocess_video(node_id, video_path, chunk_duration=5.0, step_duration=5.0)
        
        # Check that chunk paths were created
        assert node_id in node._audio_chunk_paths, "Audio chunk paths should be created"
        
        chunk_paths = node._audio_chunk_paths[node_id]
        metadata = node._chunk_metadata[node_id]
        sr = metadata['sr']
        expected_chunk_samples = int(5.0 * sr)
        
        print(f"\nTest Results for exact multiple:")
        print(f"  Total chunks created: {len(chunk_paths)}")
        
        # Verify each chunk WAV file is exactly 5 seconds
        for idx, chunk_path in enumerate(chunk_paths):
            chunk, _ = sf.read(chunk_path)
            assert len(chunk) == expected_chunk_samples, \
                f"Chunk {idx} should be exactly {expected_chunk_samples} samples, got {len(chunk)}"
        
        print(f"✅ All {len(chunk_paths)} audio chunks are exactly 5 seconds (saved as WAV files)!")
        
        # Clean up audio chunks
        node._cleanup_audio_chunks(node_id)
        
    finally:
        # Clean up the temporary video file
        if os.path.exists(video_path):
            os.unlink(video_path)


def test_chunk_validation_in_code():
    """Verify that the code includes validation for 5-second chunks"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that the code handles remaining audio
    assert 'remaining_samples = len(y) - start' in content, \
        "Code should check for remaining audio samples"
    
    assert 'if remaining_samples > 0:' in content, \
        "Code should handle remaining audio when present"
    
    assert 'np.pad' in content, \
        "Code should pad incomplete chunks with zeros"
    
    # Check for WAV file saving
    assert 'sf.write(chunk_path, chunk, sr)' in content or 'sf.write(chunk_path, padded_chunk, sr)' in content, \
        "Code should save chunks as WAV files"
    
    # Check for WAV-based storage
    assert '_audio_chunk_paths' in content, \
        "Code should use WAV file paths for chunk storage"
    
    print("✅ Code includes proper validation for 5-second chunks with WAV files")


if __name__ == '__main__':
    print("="*60)
    print("Testing Audio Chunk 5-Second Validation")
    print("="*60)
    
    test_chunk_validation_in_code()
    print()
    test_audio_chunks_are_5_seconds()
    print()
    test_audio_chunks_exact_multiple()
    
    print("\n" + "="*60)
    print("✅ All audio chunk validation tests passed!")
    print("="*60)
