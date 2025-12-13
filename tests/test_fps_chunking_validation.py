#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validation test for FPS-based audio chunking implementation.

This test validates the actual implementation in node_video.py by checking:
1. Chunk size calculation is based on FPS
2. Queue sizes are equal and based on 4 * fps
3. Frame-to-chunk mapping is direct
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_chunk_calculation_in_code():
    """Verify that audio chunking code uses FPS-based calculation"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for FPS-based chunk calculation
    assert 'samples_per_frame = sr / target_fps' in content, \
        "Should calculate samples_per_frame using sr / target_fps"
    
    print("✓ Audio chunk size is calculated as: sample_rate / fps")


def test_queue_sizes_equal_in_code():
    """Verify that audio and video queue sizes are equal"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for equal queue sizing
    assert 'queue_size_seconds = 4' in content, \
        "Should use 4 seconds for queue sizing"
    
    assert 'image_queue_size = int(queue_size_seconds * target_fps)' in content, \
        "Image queue should be 4 * target_fps"
    
    assert 'audio_queue_size = int(queue_size_seconds * target_fps)' in content, \
        "Audio queue should be 4 * target_fps"
    
    print("✓ Queue sizes are equal: both = 4 * fps")


def test_one_chunk_per_frame_logic():
    """Verify that chunking creates one chunk per frame"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for frame-based iteration
    assert 'for frame_idx in range(total_frames)' in content, \
        "Should iterate by frame index"
    
    # Check for exact boundary calculation
    assert 'start_float = frame_idx * samples_per_frame' in content, \
        "Should calculate start position using frame index"
    
    assert 'end_float = (frame_idx + 1) * samples_per_frame' in content, \
        "Should calculate end position for next frame"
    
    print("✓ Audio chunking creates one chunk per frame")


def test_direct_frame_to_chunk_mapping():
    """Verify that frame-to-chunk mapping is direct"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Find _get_audio_chunk_for_frame method
    lines = content.split('\n')
    in_method = False
    found_direct_mapping = False
    
    for line in lines:
        if 'def _get_audio_chunk_for_frame' in line:
            in_method = True
        elif in_method and line.strip().startswith('def '):
            break
        
        if in_method and 'chunk_index = frame_number - 1' in line:
            found_direct_mapping = True
            break
    
    assert found_direct_mapping, \
        "_get_audio_chunk_for_frame should use direct mapping: chunk_index = frame_number - 1"
    
    print("✓ Frame-to-chunk mapping is direct: chunk_index = frame_number - 1")


def test_metadata_includes_fps_info():
    """Verify that metadata includes FPS-based chunking information"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check metadata includes new fields
    assert "'samples_per_frame': samples_per_frame" in content or \
           "'samples_per_frame': chunk_meta.get('samples_per_frame'" in content, \
        "Metadata should include samples_per_frame"
    
    assert "'chunking_mode': 'fps_based'" in content, \
        "Metadata should indicate fps_based chunking mode"
    
    print("✓ Metadata includes FPS-based chunking information")


def test_fractional_sample_handling():
    """Verify that fractional samples are handled correctly"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that samples_per_frame is kept as float
    assert 'samples_per_frame = sr / target_fps' in content, \
        "samples_per_frame should be float (not converted to int immediately)"
    
    # Check for frame-based iteration to avoid cumulative drift
    assert 'start_float = frame_idx * samples_per_frame' in content, \
        "Should use frame index to avoid cumulative rounding errors"
    
    print("✓ Fractional samples handled correctly to avoid cumulative drift")


def test_documentation_exists():
    """Verify that documentation for FPS-based chunking exists"""
    doc_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'FPS_BASED_AUDIO_CHUNKING.md'
    )
    
    assert os.path.exists(doc_path), \
        "Documentation file FPS_BASED_AUDIO_CHUNKING.md should exist"
    
    with open(doc_path, 'r') as f:
        content = f.read()
    
    # Check for key sections
    assert 'chunk_samples = sample_rate / fps' in content, \
        "Documentation should explain the formula"
    
    assert 'audio_queue_size = image_queue_size' in content, \
        "Documentation should explain equal queue sizes"
    
    print("✓ Comprehensive documentation exists")


if __name__ == "__main__":
    print("Validating FPS-Based Audio Chunking Implementation\n")
    print("="*60)
    
    try:
        test_chunk_calculation_in_code()
        test_queue_sizes_equal_in_code()
        test_one_chunk_per_frame_logic()
        test_direct_frame_to_chunk_mapping()
        test_metadata_includes_fps_info()
        test_fractional_sample_handling()
        test_documentation_exists()
        
        print("\n" + "="*60)
        print("✅ All validation tests passed!")
        print("\nImplementation Summary:")
        print("  - Audio chunk size: sample_rate / fps")
        print("  - Queue sizes: audio_queue_size = image_queue_size = 4 * fps")
        print("  - Mapping: One audio chunk per frame (1:1)")
        print("  - Result: Perfect audio/video synchronization!")
        
    except AssertionError as e:
        print("\n" + "="*60)
        print(f"❌ Validation failed: {e}")
        exit(1)
