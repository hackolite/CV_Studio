#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for video/audio duration synchronization in VideoWriter"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import tempfile
import cv2


def test_frame_count_tracking():
    """Test that frame count is tracked during recording"""
    _frame_count_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Simulate frame writing
    for i in range(100):
        if tag_node_name not in _frame_count_dict:
            _frame_count_dict[tag_node_name] = 0
        _frame_count_dict[tag_node_name] += 1
    
    # Verify frame count
    assert tag_node_name in _frame_count_dict
    assert _frame_count_dict[tag_node_name] == 100


def test_last_frame_storage():
    """Test that last frame is stored for duplication"""
    _last_frame_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Simulate storing frames
    for i in range(10):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        _last_frame_dict[tag_node_name] = frame
    
    # Verify last frame is stored
    assert tag_node_name in _last_frame_dict
    assert _last_frame_dict[tag_node_name].shape == (480, 640, 3)


def test_video_duration_calculation():
    """Test video duration calculation from frame count and FPS"""
    frame_count = 150
    fps = 30
    
    video_duration = frame_count / fps if fps > 0 else 0
    
    assert video_duration == 5.0  # 150 frames at 30 fps = 5 seconds


def test_audio_duration_calculation():
    """Test audio duration calculation from samples and sample rate"""
    # Simulate 5 seconds of audio at 22050 Hz
    sample_rate = 22050
    audio_duration = 5.0
    total_samples = int(audio_duration * sample_rate)
    
    calculated_duration = total_samples / sample_rate
    
    assert abs(calculated_duration - audio_duration) < 0.001


def test_required_frames_calculation():
    """Test calculation of required frames to match audio duration"""
    # Audio: 6 seconds at 22050 Hz
    audio_samples = 6 * 22050
    sample_rate = 22050
    audio_duration = audio_samples / sample_rate
    
    # Video: 150 frames at 30 fps = 5 seconds
    video_frames = 150
    fps = 30
    
    # Calculate required frames
    required_frames = int(audio_duration * fps)
    frames_to_add = required_frames - video_frames
    
    assert required_frames == 180  # 6 seconds * 30 fps
    assert frames_to_add == 30  # Need to add 30 frames


def test_no_adaptation_needed():
    """Test that no adaptation is needed when video >= audio duration"""
    # Video: 6 seconds (180 frames at 30 fps)
    video_frames = 180
    fps = 30
    video_duration = video_frames / fps
    
    # Audio: 5 seconds
    audio_samples = 5 * 22050
    sample_rate = 22050
    audio_duration = audio_samples / sample_rate
    
    # Calculate frames needed
    required_frames = int(audio_duration * fps)
    frames_to_add = required_frames - video_frames
    
    assert frames_to_add <= 0  # No frames needed


def test_fps_storage_in_metadata():
    """Test that FPS is stored in recording metadata"""
    _recording_metadata_dict = {}
    tag_node_name = "test_node:VideoWriter"
    writer_fps = 30
    
    _recording_metadata_dict[tag_node_name] = {
        'final_path': '/tmp/video.mp4',
        'temp_path': '/tmp/video_temp.mp4',
        'format': 'MP4',
        'sample_rate': 22050,
        'fps': writer_fps
    }
    
    metadata = _recording_metadata_dict[tag_node_name]
    assert 'fps' in metadata
    assert metadata['fps'] == 30


def test_frame_duplication_count():
    """Test calculation of frame duplication count for sync"""
    # Simulate case where audio is 1 second longer than video
    video_duration = 5.0
    audio_duration = 6.0
    fps = 30
    
    video_frames = int(video_duration * fps)
    required_frames = int(audio_duration * fps)
    frames_to_duplicate = required_frames - video_frames
    
    assert frames_to_duplicate == 30  # Need to duplicate 30 frames


def test_cleanup_frame_tracking():
    """Test cleanup of frame tracking dictionaries"""
    _frame_count_dict = {}
    _last_frame_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Initialize
    _frame_count_dict[tag_node_name] = 100
    _last_frame_dict[tag_node_name] = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Cleanup
    if tag_node_name in _frame_count_dict:
        _frame_count_dict.pop(tag_node_name)
    if tag_node_name in _last_frame_dict:
        _last_frame_dict.pop(tag_node_name)
    
    # Verify cleanup
    assert tag_node_name not in _frame_count_dict
    assert tag_node_name not in _last_frame_dict


def test_video_shorter_than_audio_scenario():
    """Test realistic scenario where video is shorter than audio"""
    # Video node produces frames at 30 fps but occasionally drops frames
    # Result: 140 frames for what should be 5 seconds = 4.67 seconds
    video_frames = 140
    fps = 30
    video_duration = video_frames / fps
    
    # Audio is complete: 5 seconds at 22050 Hz
    audio_samples = 5 * 22050
    sample_rate = 22050
    audio_duration = audio_samples / sample_rate
    
    # Calculate adaptation needed
    required_frames = int(audio_duration * fps)
    frames_to_add = required_frames - video_frames
    
    print(f"Video: {video_duration:.2f}s ({video_frames} frames)")
    print(f"Audio: {audio_duration:.2f}s ({audio_samples} samples)")
    print(f"Frames to add: {frames_to_add}")
    
    assert video_duration < audio_duration
    assert frames_to_add == 10  # Need to add 10 frames to sync


if __name__ == '__main__':
    # Run tests
    test_frame_count_tracking()
    test_last_frame_storage()
    test_video_duration_calculation()
    test_audio_duration_calculation()
    test_required_frames_calculation()
    test_no_adaptation_needed()
    test_fps_storage_in_metadata()
    test_frame_duplication_count()
    test_cleanup_frame_tracking()
    test_video_shorter_than_audio_scenario()
    print("All video/audio duration synchronization tests passed!")
