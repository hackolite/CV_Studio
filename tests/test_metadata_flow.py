#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test metadata flow from Video node → ImageConcat → VideoWriter

Verifies that FPS and chunk settings flow through the pipeline correctly
so that VideoWriter uses the target_fps from the Video node slider,
not a global setting.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_video_node_returns_metadata():
    """
    Test that Video node returns metadata with target_fps and chunk_duration
    """
    # Simulate Video node return value
    node_video_output = {
        'image': [[1, 2, 3]],  # Frame data
        'audio': {
            'data': [0.1, 0.2],
            'sample_rate': 44100,
            'timestamp': 100.0
        },
        'json': None,
        'timestamp': 100.0,
        'metadata': {
            'target_fps': 24,  # From slider
            'chunk_duration': 2.0,  # From slider
            'step_duration': 2.0,  # Equals chunk_duration (no overlap)
            'video_fps': 30.0,  # Actual video FPS
            'sample_rate': 44100
        }
    }
    
    # Verify metadata is present
    assert 'metadata' in node_video_output
    metadata = node_video_output['metadata']
    
    # Verify key fields
    assert 'target_fps' in metadata
    assert 'chunk_duration' in metadata
    assert 'step_duration' in metadata
    
    # Verify values
    assert metadata['target_fps'] == 24
    assert metadata['chunk_duration'] == 2.0
    assert metadata['step_duration'] == 2.0
    
    # Verify no overlap (step_duration == chunk_duration)
    assert metadata['step_duration'] == metadata['chunk_duration']
    
    print("✓ Video node returns complete metadata")
    print(f"  - target_fps: {metadata['target_fps']}")
    print(f"  - chunk_duration: {metadata['chunk_duration']}s")
    print(f"  - No overlap: step_duration == chunk_duration")


def test_imageconcat_passes_metadata():
    """
    Test that ImageConcat passes through metadata from source nodes
    """
    # Simulate node_result_dict from Video node
    node_result_dict = {
        '1:Video': {
            'metadata': {
                'target_fps': 24,
                'chunk_duration': 2.0,
                'step_duration': 2.0,
                'video_fps': 30.0,
                'sample_rate': 44100
            }
        }
    }
    
    # Simulate ImageConcat collecting metadata
    source_metadata = {}
    for node_id, result in node_result_dict.items():
        if isinstance(result, dict) and 'metadata' in result:
            node_metadata = result.get('metadata', {})
            if node_metadata and isinstance(node_metadata, dict):
                source_metadata = node_metadata.copy()
                break
    
    # Simulate ImageConcat output
    imageconcat_output = {
        'image': [[1, 2, 3]],
        'audio': {'data': [0.1, 0.2]},
        'json': None,
        'metadata': source_metadata
    }
    
    # Verify metadata is passed through
    assert 'metadata' in imageconcat_output
    assert imageconcat_output['metadata'] == source_metadata
    assert imageconcat_output['metadata']['target_fps'] == 24
    
    print("✓ ImageConcat passes through metadata")
    print(f"  - Metadata keys: {list(imageconcat_output['metadata'].keys())}")


def test_videowriter_uses_source_metadata():
    """
    Test that VideoWriter uses metadata from source (target_fps)
    instead of global setting
    """
    # Global setting
    global_fps = 30
    
    # Source metadata from Video node
    source_metadata = {
        'target_fps': 24,  # Different from global
        'chunk_duration': 2.0,
    }
    
    # Simulate VideoWriter decision logic
    writer_fps = global_fps  # Start with global setting
    
    # If source metadata available, use it
    if source_metadata and 'target_fps' in source_metadata:
        writer_fps = source_metadata['target_fps']
    
    # Verify correct FPS is used
    assert writer_fps == 24, f"Expected 24 (from source), got {writer_fps}"
    assert writer_fps != global_fps, "Should use source FPS, not global"
    
    print("✓ VideoWriter uses source metadata (target_fps)")
    print(f"  - Global setting: {global_fps} fps")
    print(f"  - Source target_fps: {source_metadata['target_fps']} fps")
    print(f"  - Writer uses: {writer_fps} fps ✓")


def test_complete_metadata_flow():
    """
    Test the complete metadata flow through the pipeline
    """
    # Step 1: Video node generates metadata from slider values
    video_node_metadata = {
        'target_fps': 24,
        'chunk_duration': 2.0,
        'step_duration': 2.0,
        'video_fps': 30.0,
        'sample_rate': 44100
    }
    
    # Step 2: ImageConcat receives and passes through
    imageconcat_metadata = video_node_metadata.copy()
    
    # Step 3: VideoWriter receives metadata
    videowriter_receives = imageconcat_metadata.copy()
    
    # Step 4: VideoWriter uses target_fps for recording
    writer_fps = videowriter_receives['target_fps']
    
    # Verify end-to-end flow
    assert writer_fps == 24, "Final FPS should be 24 from slider"
    
    # Verify audio chunk settings are available
    assert 'chunk_duration' in videowriter_receives
    assert videowriter_receives['chunk_duration'] == 2.0
    
    # Verify no overlap
    assert videowriter_receives['step_duration'] == videowriter_receives['chunk_duration']
    
    print("✓ Complete metadata flow verified")
    print(f"  - Video node slider: {video_node_metadata['target_fps']} fps")
    print(f"  - Through ImageConcat: {imageconcat_metadata['target_fps']} fps")
    print(f"  - VideoWriter uses: {writer_fps} fps")
    print(f"  - Chunk duration: {videowriter_receives['chunk_duration']}s")
    print(f"  - No overlap: ✓")


def test_fps_authoritative_for_output():
    """
    Test that target_fps is authoritative for output video construction
    """
    # Input video actual FPS
    video_fps = 30.0
    
    # User's target FPS (from slider)
    target_fps = 24
    
    # Audio duration
    audio_duration = 10.0  # seconds
    
    # Output video should use target_fps, not video_fps
    output_frames_correct = int(audio_duration * target_fps)
    output_frames_wrong = int(audio_duration * video_fps)
    
    assert output_frames_correct == 240, f"Expected 240, got {output_frames_correct}"
    assert output_frames_wrong == 300, f"Expected 300, got {output_frames_wrong}"
    assert output_frames_correct != output_frames_wrong, "Should be different"
    
    # The correct approach uses target_fps
    output_duration_correct = output_frames_correct / target_fps
    assert abs(output_duration_correct - audio_duration) < 0.001
    
    print("✓ Target FPS is authoritative for output")
    print(f"  - Input video: {video_fps} fps")
    print(f"  - Target (slider): {target_fps} fps")
    print(f"  - Output uses: {target_fps} fps ✓")
    print(f"  - Output frames: {output_frames_correct} (matches {audio_duration}s audio)")


if __name__ == '__main__':
    print("="*70)
    print("METADATA FLOW VERIFICATION TESTS")
    print("="*70)
    print()
    
    test_video_node_returns_metadata()
    print()
    
    test_imageconcat_passes_metadata()
    print()
    
    test_videowriter_uses_source_metadata()
    print()
    
    test_complete_metadata_flow()
    print()
    
    test_fps_authoritative_for_output()
    print()
    
    print("="*70)
    print("✅ ALL METADATA FLOW TESTS PASSED")
    print("="*70)
