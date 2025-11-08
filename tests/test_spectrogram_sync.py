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
    
    # Check new data structures
    assert "_video_frames = {}" in content, "Should have _video_frames dict"
    assert "_audio_chunks = {}" in content, "Should have _audio_chunks dict"
    assert "_spectrogram_chunks = {}" in content, "Should have _spectrogram_chunks dict"
    assert "_chunk_metadata = {}" in content, "Should have _chunk_metadata dict"
    
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
    
    # Check it extracts frames
    assert "cv2.VideoCapture" in content, "Should use cv2.VideoCapture to extract frames"
    
    # Check it extracts audio
    assert "librosa.load" in content, "Should use librosa.load to extract audio"
    
    # Check it chunks audio
    assert "chunk_samples" in content, "Should calculate chunk_samples"
    assert "step_samples" in content, "Should calculate step_samples"
    
    # Check it generates spectrograms
    assert "fourier_transformation" in content, "Should use fourier_transformation"
    assert "make_logscale" in content, "Should use make_logscale"
    assert "apply_colormap_to_spectrogram" in content, "Should use apply_colormap_to_spectrogram"
    
    print("✓ _preprocess_video method has correct structure")


def test_get_spectrogram_for_frame_method():
    """Test that _get_spectrogram_for_frame method exists"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check method exists
    assert "def _get_spectrogram_for_frame" in content, "Should have _get_spectrogram_for_frame method"
    
    # Check it uses chunk_index calculation
    assert "chunk_index" in content, "Should calculate chunk_index"
    
    # Check it accesses pre-computed spectrograms
    assert "self._spectrogram_chunks" in content, "Should access _spectrogram_chunks"
    
    print("✓ _get_spectrogram_for_frame method exists")


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
    """Test that update method uses simplified spectrogram lookup"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check simplified logic
    assert "_get_spectrogram_for_frame" in content, "Should call _get_spectrogram_for_frame"
    
    # Check it uses _spectrogram_chunks
    lines = content.split('\n')
    found_chunks_check = False
    
    for line in lines:
        if "str(node_id) in self._spectrogram_chunks" in line:
            found_chunks_check = True
            break
    
    assert found_chunks_check, "Should check if node_id in _spectrogram_chunks"
    
    print("✓ update method uses simplified lookup")


def test_old_prepare_method_removed():
    """Test that the old _prepare_spectrogram method is removed"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # The old method should be removed
    assert "def _prepare_spectrogram" not in content, "_prepare_spectrogram method should be removed"
    
    print("✓ Old _prepare_spectrogram method is removed")


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


def test_constants_preserved():
    """Test that existing constants are preserved"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check constants
    assert "SPECTROGRAM_EPSILON" in content, "Should have SPECTROGRAM_EPSILON constant"
    assert "DEFAULT_SPECTROGRAM_COLORMAP" in content, "Should have DEFAULT_SPECTROGRAM_COLORMAP constant"
    
    print("✓ Required constants are preserved")


if __name__ == '__main__':
    test_new_architecture_data_structures()
    test_preprocess_video_method()
    test_get_spectrogram_for_frame_method()
    test_callback_uses_preprocess()
    test_update_method_simplified()
    test_old_prepare_method_removed()
    test_python_syntax_valid()
    test_constants_preserved()
    print("\n✓ All frame-by-frame architecture tests passed successfully!")

