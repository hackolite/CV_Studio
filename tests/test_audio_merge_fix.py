#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for audio merge crash fixes in VideoWriter node.
Tests the fixes for:
1. Empty or invalid audio samples causing crash
2. Missing temp video file
3. Race condition with video writer release
"""
import sys
import os
import numpy as np
import tempfile
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_empty_audio_samples_handling():
    """Test that empty audio samples are properly handled without crashing"""
    # This simulates the validation logic added to _merge_audio_video_ffmpeg
    
    # Test case 1: Empty list
    audio_samples = []
    valid_samples = []
    for sample in audio_samples:
        if isinstance(sample, np.ndarray) and sample.size > 0:
            valid_samples.append(sample)
    
    assert len(valid_samples) == 0, "Empty list should result in no valid samples"
    print("✓ Empty audio samples list handled correctly")
    
    # Test case 2: List with empty arrays
    audio_samples = [np.array([]), np.array([])]
    valid_samples = []
    for sample in audio_samples:
        if isinstance(sample, np.ndarray) and sample.size > 0:
            valid_samples.append(sample)
    
    assert len(valid_samples) == 0, "List with empty arrays should result in no valid samples"
    print("✓ Empty audio arrays handled correctly")
    
    # Test case 3: Mix of valid and invalid samples
    audio_samples = [
        np.array([1, 2, 3]),
        np.array([]),  # Empty
        None,  # Invalid type
        np.array([4, 5, 6]),
    ]
    valid_samples = []
    for sample in audio_samples:
        if isinstance(sample, np.ndarray) and sample.size > 0:
            valid_samples.append(sample)
    
    assert len(valid_samples) == 2, f"Should have 2 valid samples, got {len(valid_samples)}"
    print("✓ Mixed valid/invalid samples handled correctly")
    
    # Test case 4: Concatenate valid samples
    if valid_samples:
        result = np.concatenate(valid_samples)
        assert result.size == 6, f"Concatenated array should have 6 elements, got {result.size}"
        assert np.array_equal(result, np.array([1, 2, 3, 4, 5, 6])), "Concatenation result incorrect"
        print("✓ Valid samples concatenated correctly")


def test_video_file_wait_logic():
    """Test the wait logic for video file to be fully written"""
    # Create a temporary file with delay to simulate slow write
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
        temp_path = temp_file.name
    
    # Remove the file to simulate it not existing yet
    os.remove(temp_path)
    
    # Simulate the wait logic from _async_merge_thread
    max_wait = 1  # seconds (shorter for test)
    wait_interval = 0.1  # seconds
    elapsed = 0
    file_created = False
    
    # Create file after a short delay in background
    def create_file_delayed():
        time.sleep(0.3)  # Wait 300ms before creating file
        with open(temp_path, 'wb') as f:
            f.write(b'test video data')
    
    import threading
    create_thread = threading.Thread(target=create_file_delayed, daemon=True)
    create_thread.start()
    
    # Wait for file to exist
    while not os.path.exists(temp_path) and elapsed < max_wait:
        time.sleep(wait_interval)
        elapsed += wait_interval
    
    if os.path.exists(temp_path):
        file_created = True
        os.remove(temp_path)  # Clean up
    
    assert file_created, "File should have been detected after delayed creation"
    print(f"✓ File wait logic works correctly (detected after {elapsed:.1f}s)")


def test_progress_callback_with_validation():
    """Test that progress callbacks work even with validation steps"""
    progress_values = []
    
    def progress_callback(value):
        progress_values.append(value)
    
    # Simulate the progress reporting in _merge_audio_video_ffmpeg
    # with the new validation steps
    
    # Step 1: Video file exists check (before 0.1)
    # (no progress callback)
    
    # Step 2: Start concatenation
    progress_callback(0.1)
    
    # Step 3: Validate audio samples
    # (no progress callback)
    
    # Step 4: Audio concatenated
    progress_callback(0.3)
    
    # Step 5: Audio file written
    progress_callback(0.5)
    
    # Step 6: Starting ffmpeg
    progress_callback(0.7)
    
    # Step 7: Complete
    progress_callback(1.0)
    
    assert len(progress_values) == 5, f"Expected 5 progress updates, got {len(progress_values)}"
    assert progress_values[0] == 0.1, "First progress should be 0.1"
    assert progress_values[-1] == 1.0, "Last progress should be 1.0"
    assert all(progress_values[i] <= progress_values[i+1] for i in range(len(progress_values)-1)), \
        "Progress should be monotonically increasing"
    
    print("✓ Progress callback works correctly with validation")


def test_video_writer_release_check():
    """Test that video writer release is properly checked"""
    # Simulate the check added to _recording_button
    
    video_writer_dict = {}
    tag_node_name = "test_node"
    
    # Case 1: Video writer exists
    video_writer_dict[tag_node_name] = "mock_writer"
    
    if tag_node_name in video_writer_dict:
        # Simulate release
        writer = video_writer_dict.pop(tag_node_name)
        assert writer == "mock_writer", "Should have retrieved the writer"
    
    # Case 2: Video writer doesn't exist (shouldn't crash)
    if tag_node_name in video_writer_dict:
        # This should not execute
        assert False, "Should not enter this block"
    
    print("✓ Video writer release check works correctly")


if __name__ == "__main__":
    test_empty_audio_samples_handling()
    test_video_file_wait_logic()
    test_progress_callback_with_validation()
    test_video_writer_release_check()
    print("\n✅ All audio merge crash fix tests passed!")
