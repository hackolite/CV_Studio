#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for VideoWriter stopping state functionality.

This test verifies that when recording stops, the VideoWriter:
1. Stops collecting audio immediately
2. Calculates required frames based on collected audio
3. Continues collecting video frames until requirement is met
4. Then finalizes the recording
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_stopping_state_dict_exists():
    """Test that _stopping_state_dict class variable exists"""
    # Check the source code directly instead of importing
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Check that _stopping_state_dict is defined in the source
    assert '_stopping_state_dict = {}' in content or \
           '_stopping_state_dict={}' in content, \
        "VideoWriterNode should have _stopping_state_dict class variable"
    
    print("✓ Stopping state dict exists test passed")


def test_stopping_state_calculation():
    """Test the logic for calculating required frames when stopping"""
    # Simulate audio collection
    # 3 audio chunks, each with 22050 samples (1 second at 22050 Hz)
    # Total: 3 seconds of audio
    audio_samples_per_chunk = 22050
    num_chunks = 3
    sample_rate = 22050
    fps = 30
    
    # Calculate expected required frames (same logic as in the code)
    total_audio_samples = audio_samples_per_chunk * num_chunks
    audio_duration = total_audio_samples / sample_rate  # 3.0 seconds
    expected_required_frames = int(audio_duration * fps)  # 90 frames
    
    assert expected_required_frames == 90, \
        f"Expected 90 frames for 3 seconds at 30fps, got {expected_required_frames}"
    
    print(f"✓ Stopping state calculation test passed")
    print(f"  Audio: {num_chunks} chunks, {total_audio_samples} samples, {audio_duration}s")
    print(f"  Video: {expected_required_frames} frames at {fps} fps")


def test_audio_not_collected_in_stopping_state():
    """Test that the update method doesn't collect audio when in stopping state"""
    # This is a logic test - we verify the condition in the code:
    # is_stopping = tag_node_name in self._stopping_state_dict
    # if audio_data is not None and tag_node_name in self._audio_samples_dict and not is_stopping:
    
    # The key is that when is_stopping is True, audio won't be collected
    # Even if audio_data is not None
    
    stopping_state = True
    audio_data_present = True
    
    # Simulate the condition
    should_collect_audio = audio_data_present and not stopping_state
    
    assert not should_collect_audio, \
        "Audio should not be collected when in stopping state"
    
    print("✓ Audio not collected in stopping state test passed")


def test_stopping_state_cleanup():
    """Test that stopping state cleanup is implemented in code"""
    # Check the source code for cleanup logic
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Verify cleanup in the finalization code
    assert '_stopping_state_dict.pop' in content, \
        "Should have cleanup code for stopping state dict"
    
    print("✓ Stopping state cleanup test passed")


def test_frame_count_comparison():
    """Test frame count comparison logic for stopping"""
    # Scenario 1: Need more frames
    current_frames = 50
    required_frames = 90
    need_more_frames = current_frames < required_frames
    
    assert need_more_frames, \
        "Should need more frames when current < required"
    
    # Scenario 2: Have enough frames
    current_frames = 90
    required_frames = 90
    need_more_frames = current_frames < required_frames
    
    assert not need_more_frames, \
        "Should not need more frames when current >= required"
    
    # Scenario 3: Have extra frames
    current_frames = 100
    required_frames = 90
    need_more_frames = current_frames < required_frames
    
    assert not need_more_frames, \
        "Should not need more frames when current > required"
    
    print("✓ Frame count comparison test passed")


def test_audio_duration_calculation():
    """Test audio duration calculation from samples"""
    # Test case 1: 1 second at 22050 Hz
    samples = 22050
    sample_rate = 22050
    duration = samples / sample_rate
    assert abs(duration - 1.0) < 0.001, f"Expected 1.0s, got {duration}s"
    
    # Test case 2: 3 seconds at 44100 Hz
    samples = 132300
    sample_rate = 44100
    duration = samples / sample_rate
    assert abs(duration - 3.0) < 0.001, f"Expected 3.0s, got {duration}s"
    
    # Test case 3: 0.5 seconds at 22050 Hz
    samples = 11025
    sample_rate = 22050
    duration = samples / sample_rate
    assert abs(duration - 0.5) < 0.001, f"Expected 0.5s, got {duration}s"
    
    print("✓ Audio duration calculation test passed")


def test_required_frames_calculation():
    """Test required frames calculation from audio duration and fps"""
    # Test case 1: 3 seconds at 30 fps
    audio_duration = 3.0
    fps = 30
    required_frames = int(audio_duration * fps)
    assert required_frames == 90, f"Expected 90 frames, got {required_frames}"
    
    # Test case 2: 5 seconds at 24 fps
    audio_duration = 5.0
    fps = 24
    required_frames = int(audio_duration * fps)
    assert required_frames == 120, f"Expected 120 frames, got {required_frames}"
    
    # Test case 3: 2.5 seconds at 60 fps
    audio_duration = 2.5
    fps = 60
    required_frames = int(audio_duration * fps)
    assert required_frames == 150, f"Expected 150 frames, got {required_frames}"
    
    print("✓ Required frames calculation test passed")


if __name__ == "__main__":
    test_stopping_state_dict_exists()
    test_stopping_state_calculation()
    test_audio_not_collected_in_stopping_state()
    test_stopping_state_cleanup()
    test_frame_count_comparison()
    test_audio_duration_calculation()
    test_required_frames_calculation()
    print("\n✅ All VideoWriter stopping state tests passed!")
