#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lightweight tests for JIT spectrogram generation functionality.
Tests the structure and documentation without requiring full dependencies.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_file_structure():
    """Test that the video node file has the required JIT structure"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check header documentation
    assert 'spectrogram generation modes' in content.lower() or 'two modes' in content.lower(), \
        "Should have header documentation about modes"
    assert "'precompute'" in content, "Should reference precompute mode"
    assert "'jit'" in content, "Should reference JIT mode"
    assert 'just-in-time' in content, "Should explain JIT terminology"
    
    # Check class attributes
    assert "self._spectrogram_mode = 'precompute'" in content, \
        "Should initialize _spectrogram_mode to 'precompute'"
    assert "self._audio_y = {}" in content, \
        "Should have _audio_y attribute for storing full audio signal"
    
    # Check new methods
    assert "def _get_audio_chunk_for_frame" in content, \
        "Should have _get_audio_chunk_for_frame method"
    assert "def _get_spectrogram_for_frame" in content, \
        "Should have _get_spectrogram_for_frame method"
    assert "def _get_precomputed_spectrogram" in content, \
        "Should have _get_precomputed_spectrogram method"
    assert "def _generate_spectrogram_jit" in content, \
        "Should have _generate_spectrogram_jit method"
    
    # Check that audio is stored during preprocessing
    assert "self._audio_y[node_id] = y" in content, \
        "Should store full audio signal in _audio_y during preprocessing"
    
    # Check mode switching logic in _get_spectrogram_for_frame
    assert "if self._spectrogram_mode == 'jit':" in content, \
        "Should check mode in _get_spectrogram_for_frame"
    
    # Check docstrings
    assert "Example behavior:" in content or "Example" in content, \
        "Should have example in docstring"
    
    print("✓ File structure checks passed")


def test_audio_chunk_method_signature():
    """Test _get_audio_chunk_for_frame method signature and documentation"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        lines = f.readlines()
    
    # Find the method definition
    method_start = None
    for i, line in enumerate(lines):
        if 'def _get_audio_chunk_for_frame' in line:
            method_start = i
            break
    
    assert method_start is not None, "_get_audio_chunk_for_frame method should exist"
    
    # Check method signature
    method_def = lines[method_start]
    assert 'node_id' in method_def, "Should have node_id parameter"
    assert 'frame_number' in method_def, "Should have frame_number parameter"
    
    # Check for documentation within reasonable range
    docstring_section = ''.join(lines[method_start:method_start + 30])
    assert '"""' in docstring_section, "Should have docstring"
    assert 'frame' in docstring_section.lower(), "Docstring should mention frames"
    assert 'audio' in docstring_section.lower(), "Docstring should mention audio"
    
    print("✓ Audio chunk method signature checks passed")


def test_spectrogram_for_frame_docstring():
    """Test _get_spectrogram_for_frame has proper docstring with examples"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        lines = f.readlines()
    
    # Find the method definition
    method_start = None
    for i, line in enumerate(lines):
        if 'def _get_spectrogram_for_frame' in line:
            method_start = i
            break
    
    assert method_start is not None, "_get_spectrogram_for_frame method should exist"
    
    # Check for comprehensive documentation
    docstring_section = ''.join(lines[method_start:method_start + 50])
    
    assert '"""' in docstring_section, "Should have docstring"
    assert 'precompute' in docstring_section, "Should document precompute mode"
    assert 'jit' in docstring_section, "Should document JIT mode"
    assert 'Example' in docstring_section, "Should have example section"
    assert '>>>' in docstring_section, "Should have Python example code"
    
    print("✓ Spectrogram for frame docstring checks passed")


def test_mode_switching_logic():
    """Test that mode switching logic is properly implemented"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that _get_spectrogram_for_frame delegates to appropriate method
    assert "_generate_spectrogram_jit" in content, \
        "Should call _generate_spectrogram_jit for JIT mode"
    assert "_get_precomputed_spectrogram" in content, \
        "Should call _get_precomputed_spectrogram for precompute mode"
    
    # Verify JIT method uses audio chunk extraction
    assert "self._get_audio_chunk_for_frame" in content, \
        "JIT method should use _get_audio_chunk_for_frame"
    
    # Verify JIT method uses same processing pipeline
    assert "fourier_transformation" in content, \
        "Should use fourier_transformation in processing"
    assert "make_logscale" in content, \
        "Should use make_logscale in processing"
    assert "apply_colormap_to_spectrogram" in content, \
        "Should use apply_colormap_to_spectrogram"
    
    print("✓ Mode switching logic checks passed")


def test_edge_case_handling():
    """Test that edge cases are documented and handled"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for overflow/underflow handling
    assert "overflow" in content.lower() or "beyond" in content.lower() or "truncate" in content.lower(), \
        "Should document handling of audio bounds"
    
    # Check for None return handling
    assert "return None" in content, \
        "Should return None for invalid cases"
    
    # Check for negative frame handling
    assert "< 0" in content or "negative" in content.lower(), \
        "Should handle negative frame numbers"
    
    print("✓ Edge case handling checks passed")


def test_backward_compatibility():
    """Test that existing code paths are maintained"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that precompute mode preserves existing behavior
    assert "_spectrogram_chunks" in content, \
        "Should still support pre-computed spectrogram chunks"
    assert "_chunk_metadata" in content, \
        "Should still maintain chunk metadata"
    
    # Check that update method still calls _get_spectrogram_for_frame
    assert "self._get_spectrogram_for_frame" in content, \
        "update method should call _get_spectrogram_for_frame"
    
    print("✓ Backward compatibility checks passed")


if __name__ == '__main__':
    print("Running JIT Spectrogram Structure Tests...\n")
    
    test_file_structure()
    test_audio_chunk_method_signature()
    test_spectrogram_for_frame_docstring()
    test_mode_switching_logic()
    test_edge_case_handling()
    test_backward_compatibility()
    
    print("\n✅ All JIT spectrogram structure tests passed successfully!")
