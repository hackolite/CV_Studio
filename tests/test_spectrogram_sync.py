#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for spectrogram synchronization with video playback - Frame-by-Frame Architecture"""

import pytest
import sys
import os
import ast

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_new_architecture_data_structures():
    """Test that the new pre-processing data structures exist"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check new data structures (video frames removed to prevent memory issues)
    assert "_audio_chunks = {}" in content, "Should have _audio_chunks dict"
    assert "_chunk_metadata = {}" in content, "Should have _chunk_metadata dict"
    
    # Verify that _video_frames has been removed to prevent memory issues
    assert "_video_frames = {}" not in content, "_video_frames should be removed to prevent memory issues"
    
    print("✓ New architecture data structures are present")


def test_preprocess_video_method():
    """Test that _preprocess_video method exists and has expected structure"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check method exists
    assert "def _preprocess_video" in content, "Should have _preprocess_video method"
    
    # Check parameters
    assert "chunk_duration=5.0" in content, "Should have chunk_duration parameter with default 5.0"
    assert "step_duration=1.0" in content, "Should have step_duration parameter with default 1.0"
    
    # Check it extracts metadata only (not all frames to prevent memory issues)
    assert "cv2.VideoCapture" in content, "Should use cv2.VideoCapture to extract metadata"
    
    # Check it extracts audio
    assert "librosa.load" in content, "Should use librosa.load to extract audio"
    
    # Check it chunks audio
    assert "chunk_samples" in content, "Should calculate chunk_samples"
    assert "step_samples" in content, "Should calculate step_samples"
    
    print("✓ _preprocess_video method has correct structure")


def test_get_audio_chunk_for_frame_method():
    """Test that _get_audio_chunk_for_frame method exists (spectrogram removed)"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check method exists
    assert "def _get_audio_chunk_for_frame" in content, "Should have _get_audio_chunk_for_frame method"
    
    # Check it uses chunk_index calculation
    assert "chunk_index" in content, "Should calculate chunk_index"
    
    # Check it accesses audio chunks
    assert "self._audio_chunks" in content, "Should access _audio_chunks"
    
    print("✓ _get_audio_chunk_for_frame method exists")


def test_callback_uses_preprocess():
    """Test that _callback_file_select calls _preprocess_video"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that callback calls _preprocess_video
    assert "self._preprocess_video" in content, "Should call _preprocess_video"
    
    # Verify it's in the callback
    lines = content.split('\n')
    found_in_callback = False
    in_callback = False
    
    for line in lines:
        if 'def _callback_file_select' in line:
            in_callback = True
        elif in_callback and 'def ' in line and '_callback_file_select' not in line:
            in_callback = False
        elif in_callback and '_preprocess_video' in line:
            found_in_callback = True
            break
    
    assert found_in_callback, "_preprocess_video should be called in _callback_file_select"
    
    print("✓ _callback_file_select calls _preprocess_video")


def test_update_method_simplified():
    """Test that update method uses simplified audio lookup (spectrogram removed)"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check simplified logic
    assert "_get_audio_chunk_for_frame" in content, "Should call _get_audio_chunk_for_frame"
    
    # Check it uses _audio_chunks
    lines = content.split('\n')
    found_chunks_check = False
    
    for line in lines:
        if "str(node_id) in self._audio_chunks" in line:
            found_chunks_check = True
            break
    
    assert found_chunks_check, "Should check if node_id in _audio_chunks"
    
    print("✓ update method uses simplified lookup")


def test_old_prepare_method_removed():
    """Test that spectrogram methods have been removed"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # The old spectrogram methods should be removed
    assert "def _prepare_spectrogram" not in content, "_prepare_spectrogram method should be removed"
    assert "def _get_spectrogram_for_frame" not in content, "_get_spectrogram_for_frame method should be removed"
    
    print("✓ Old spectrogram methods are removed")


def test_python_syntax_valid():
    """Test that the Python syntax is valid"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    try:
        ast.parse(content)
        print("✓ Python syntax is valid")
    except SyntaxError as e:
        pytest.fail(f"Syntax error in node_video.py: {e}")


def test_memory_efficiency():
    """Test that video node doesn't store all frames in memory"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Verify that frames are not being stored in memory
    assert "_video_frames[node_id] = frames" not in content, "Should NOT store all frames in _video_frames"
    assert "frames.append(frame)" not in content, "Should NOT append frames to a list during preprocessing"
    
    # Verify that frames are read on-demand via VideoCapture
    assert "video_capture.read()" in content, "Should read frames on-demand from VideoCapture"
    
    print("✓ Video node is memory efficient")


if __name__ == '__main__':
    test_new_architecture_data_structures()
    test_preprocess_video_method()
    test_get_audio_chunk_for_frame_method()
    test_callback_uses_preprocess()
    test_update_method_simplified()
    test_old_prepare_method_removed()
    test_python_syntax_valid()
    test_memory_efficiency()
    print("\n✓ All frame-by-frame architecture tests passed successfully!")

