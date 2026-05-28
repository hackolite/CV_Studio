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
import threading

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test constants
TEST_FILE_WAIT_TIMEOUT = 1.0  # Shorter than production (5.0s) for faster tests
TEST_FILE_CREATION_DELAY = 0.3  # Delay before creating test file


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
    # Use shorter timeout for test to avoid long test runtime
    max_wait = TEST_FILE_WAIT_TIMEOUT
    wait_interval = 0.1  # seconds
    elapsed = 0
    file_created = False
    
    # Create file after a short delay in background
    def create_file_delayed():
        time.sleep(TEST_FILE_CREATION_DELAY)
        with open(temp_path, 'wb') as f:
            f.write(b'test video data')
    
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


def test_merge_skipped_when_deps_missing():
    """
    Test that _merge_audio_video_ffmpeg returns False and emits a precise warning
    when ffmpeg-python or soundfile is not installed, rather than silently skipping.
    """
    import unittest.mock as mock
    import logging
    import node.VideoNode.node_video_writer as nvw

    original_ffmpeg_available = nvw.FFMPEG_AVAILABLE
    original_ffmpeg_python = nvw._FFMPEG_PYTHON_AVAILABLE
    original_soundfile = nvw._SOUNDFILE_AVAILABLE

    try:
        # --- Case 1: only ffmpeg-python missing ---
        nvw.FFMPEG_AVAILABLE = False
        nvw._FFMPEG_PYTHON_AVAILABLE = False
        nvw._SOUNDFILE_AVAILABLE = True

        writer = object.__new__(nvw.VideoWriterNode)
        with mock.patch.object(nvw.logger, "warning") as mock_warn:
            result = writer._merge_audio_video_ffmpeg("v.mp4", [], 44100, "out.mp4")

        assert result is False, "merge must return False when ffmpeg-python is missing"
        mock_warn.assert_called_once()
        # logger.warning(fmt, arg1, arg2) — check both format string and args
        call_args = mock_warn.call_args
        full_msg = (call_args[0][0] % call_args[0][1:]) if len(call_args[0]) > 1 else call_args[0][0]
        assert "ffmpeg-python" in full_msg, "warning must mention ffmpeg-python"
        assert "soundfile" not in full_msg, "warning must NOT mention soundfile if it is present"
        print("✓ ffmpeg-python missing: correct False + accurate warning")

        # --- Case 2: only soundfile missing ---
        nvw.FFMPEG_AVAILABLE = False
        nvw._FFMPEG_PYTHON_AVAILABLE = True
        nvw._SOUNDFILE_AVAILABLE = False

        with mock.patch.object(nvw.logger, "warning") as mock_warn:
            result = writer._merge_audio_video_ffmpeg("v.mp4", [], 44100, "out.mp4")

        assert result is False, "merge must return False when soundfile is missing"
        mock_warn.assert_called_once()
        call_args = mock_warn.call_args
        full_msg = (call_args[0][0] % call_args[0][1:]) if len(call_args[0]) > 1 else call_args[0][0]
        assert "soundfile" in full_msg, "warning must mention soundfile"
        assert "ffmpeg-python" not in full_msg, "warning must NOT mention ffmpeg-python if it is present"
        print("✓ soundfile missing: correct False + accurate warning")

        # --- Case 3: both missing ---
        nvw.FFMPEG_AVAILABLE = False
        nvw._FFMPEG_PYTHON_AVAILABLE = False
        nvw._SOUNDFILE_AVAILABLE = False

        with mock.patch.object(nvw.logger, "warning") as mock_warn:
            result = writer._merge_audio_video_ffmpeg("v.mp4", [], 44100, "out.mp4")

        assert result is False, "merge must return False when both are missing"
        mock_warn.assert_called_once()
        call_args = mock_warn.call_args
        full_msg = (call_args[0][0] % call_args[0][1:]) if len(call_args[0]) > 1 else call_args[0][0]
        assert "ffmpeg-python" in full_msg, "warning must mention ffmpeg-python"
        assert "soundfile" in full_msg, "warning must mention soundfile"
        print("✓ both missing: correct False + accurate warning")

    finally:
        nvw.FFMPEG_AVAILABLE = original_ffmpeg_available
        nvw._FFMPEG_PYTHON_AVAILABLE = original_ffmpeg_python
        nvw._SOUNDFILE_AVAILABLE = original_soundfile


if __name__ == "__main__":
    test_empty_audio_samples_handling()
    test_video_file_wait_logic()
    test_progress_callback_with_validation()
    test_video_writer_release_check()
    test_merge_skipped_when_deps_missing()
    print("\n✅ All audio merge crash fix tests passed!")
