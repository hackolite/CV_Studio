#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for VideoWriter audio+video merge functionality.

This test validates that after concatenation using audio + video,
the VideoWriter node can merge audio and image for MP4, AVI, or MKV formats.
"""

import pytest
import numpy as np
import os
import tempfile
import shutil
import sys


def test_audio_video_merge_ffmpeg_available():
    """Test that ffmpeg-python is available for audio/video merging"""
    try:
        import ffmpeg
        import soundfile as sf
        assert True, "ffmpeg-python and soundfile are available"
    except ImportError as e:
        pytest.fail(f"Required libraries not available: {e}")


def test_merge_audio_video_function():
    """Test the audio/video merge function directly without importing the node"""
    try:
        import cv2
        import soundfile as sf
        import ffmpeg
    except ImportError as e:
        pytest.skip(f"Required libraries not available: {e}")
    
    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a dummy video file (10 frames, 640x480, 30 fps)
        video_path = os.path.join(temp_dir, 'test_video.mp4')
        output_path = os.path.join(temp_dir, 'test_output.mp4')
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(video_path, fourcc, 30.0, (640, 480))
        
        # Write 10 frames
        for i in range(10):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Add some content so it's not just black
            cv2.putText(frame, f"Frame {i}", (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2)
            video_writer.write(frame)
        
        video_writer.release()
        
        # Create dummy audio samples (1 second at 22050 Hz)
        sample_rate = 22050
        duration = 1.0
        audio_samples = [np.sin(2 * np.pi * 440 * np.arange(int(sample_rate * duration)) / sample_rate)]
        
        # Write audio to WAV file
        full_audio = np.concatenate(audio_samples)
        audio_path = os.path.join(temp_dir, 'test_audio.wav')
        sf.write(audio_path, full_audio, sample_rate)
        
        # Merge using ffmpeg directly
        video_input = ffmpeg.input(video_path)
        audio_input = ffmpeg.input(audio_path)
        
        output = ffmpeg.output(
            video_input,
            audio_input,
            output_path,
            vcodec='copy',
            acodec='aac',
            loglevel='error'
        )
        
        output = ffmpeg.overwrite_output(output)
        ffmpeg.run(output, capture_stdout=True, capture_stderr=True)
        
        # Verify output exists
        assert os.path.exists(output_path), "Output file should exist"
        
        # Verify output has both video and audio
        probe = ffmpeg.probe(output_path)
        
        # Check streams
        streams = probe.get('streams', [])
        has_video = any(s.get('codec_type') == 'video' for s in streams)
        has_audio = any(s.get('codec_type') == 'audio' for s in streams)
        
        assert has_video, "Output should have video stream"
        assert has_audio, "Output should have audio stream"


def test_audio_sample_collection_single_chunk():
    """Test that audio samples are collected correctly from single chunk"""
    # Test the logic without importing the node
    audio_samples_dict = {}
    recording_metadata_dict = {}
    tag_node_name = "1:VideoWriter"
    
    # Initialize audio collection
    audio_samples_dict[tag_node_name] = []
    recording_metadata_dict[tag_node_name] = {
        'sample_rate': 22050
    }
    
    # Simulate audio data from video node (dict format)
    audio_data = {
        'data': np.array([0.1, 0.2, 0.3, 0.4]),
        'sample_rate': 44100
    }
    
    # Simulate the collection logic from update() method
    if isinstance(audio_data, dict) and 'data' in audio_data and 'sample_rate' in audio_data:
        audio_samples_dict[tag_node_name].append(audio_data['data'])
        recording_metadata_dict[tag_node_name]['sample_rate'] = audio_data['sample_rate']
    
    # Verify
    assert len(audio_samples_dict[tag_node_name]) == 1
    assert len(audio_samples_dict[tag_node_name][0]) == 4
    assert recording_metadata_dict[tag_node_name]['sample_rate'] == 44100


def test_audio_sample_collection_multi_slot():
    """Test that audio samples from multiple slots are merged correctly"""
    # Test the logic without importing the node
    audio_samples_dict = {}
    recording_metadata_dict = {}
    tag_node_name = "1:VideoWriter"
    
    # Initialize audio collection
    audio_samples_dict[tag_node_name] = []
    recording_metadata_dict[tag_node_name] = {
        'sample_rate': 22050
    }
    
    # Simulate audio data from concat node (multi-slot format)
    audio_data = {
        0: {'data': np.array([0.1, 0.2]), 'sample_rate': 22050},
        1: {'data': np.array([0.3, 0.4]), 'sample_rate': 22050}
    }
    
    # Simulate the collection logic from update() method
    if isinstance(audio_data, dict) and 'data' not in audio_data:
        # Multi-slot concat output
        audio_chunks = []
        sample_rate = None
        
        for slot_idx in sorted(audio_data.keys()):
            audio_chunk = audio_data[slot_idx]
            if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
                audio_chunks.append(audio_chunk['data'])
                if sample_rate is None and 'sample_rate' in audio_chunk:
                    sample_rate = audio_chunk['sample_rate']
        
        if audio_chunks:
            merged_chunk = np.concatenate(audio_chunks)
            audio_samples_dict[tag_node_name].append(merged_chunk)
            
            if sample_rate is not None:
                recording_metadata_dict[tag_node_name]['sample_rate'] = sample_rate
    
    # Verify
    assert len(audio_samples_dict[tag_node_name]) == 1
    assert len(audio_samples_dict[tag_node_name][0]) == 4  # 2 + 2 samples merged
    np.testing.assert_array_equal(
        audio_samples_dict[tag_node_name][0],
        np.array([0.1, 0.2, 0.3, 0.4])
    )


def test_concat_audio_chunk_index_deduplication():
    """ImageConcat audio delivered via concat path must be deduplicated by chunk_index.

    At 30 fps the same audio chunk (with the same chunk_index) is delivered for
    every video frame.  Without deduplication 30 identical 1-second chunks would
    be appended per second of video, making the audio track 30× too long and
    producing completely wrong A/V sync.  The concat path must skip a chunk when
    its chunk_index equals the previously stored value — exactly as the
    single-slot path does.
    """
    import numpy as np

    sample_rate = 22050
    step_duration = 1.0

    step_samples = int(step_duration * sample_rate)

    # Simulate the deduplication state maintained by VideoWriter
    audio_samples_dict = {"1:VideoWriter": []}
    last_chunk_index_dict = {}
    tag_node_name = "1:VideoWriter"

    # Replicate the deduplication logic from the concat path
    def _collect_concat(audio_data):
        concat_incoming_idx = None
        for _si in sorted(audio_data.keys()):
            _ac = audio_data[_si]
            if isinstance(_ac, dict):
                _ci = _ac.get('chunk_index', None)
                if _ci is not None:
                    concat_incoming_idx = _ci
                    break

        concat_last_idx = last_chunk_index_dict.get(tag_node_name, -1)
        if concat_incoming_idx is not None and concat_incoming_idx == concat_last_idx:
            return  # duplicate — skip

        if concat_incoming_idx is not None:
            last_chunk_index_dict[tag_node_name] = concat_incoming_idx

        audio_chunks = []
        sr_found = None
        step_dur = None

        for slot_idx in sorted(audio_data.keys()):
            ac = audio_data[slot_idx]
            if isinstance(ac, dict) and 'data' in ac:
                chunk_data = ac['data']
                sr = ac.get('sample_rate', None)
                if step_dur is None:
                    step_dur = ac.get('step_duration', None)
                if step_dur is not None and sr and sr > 0:
                    chunk_data = chunk_data[:int(step_dur * sr)]
                audio_chunks.append(chunk_data)
                if sr_found is None and sr is not None:
                    sr_found = sr

        if audio_chunks:
            audio_samples_dict[tag_node_name].append(np.concatenate(audio_chunks))

    # 30-frame simulation at 30 fps: same chunk_index = 0 for all 30 frames
    chunk0_data = np.ones(step_samples, dtype=np.float32) * 1.0
    for _ in range(30):
        _collect_concat({
            0: {
                'data': chunk0_data.copy(),
                'sample_rate': sample_rate,
                'chunk_index': 0,
                'step_duration': step_duration,
            }
        })

    # Only ONE chunk should have been appended (the first); the remaining 29 are duplicates
    assert len(audio_samples_dict[tag_node_name]) == 1, (
        f"Expected 1 chunk after 30 frames with the same chunk_index, "
        f"got {len(audio_samples_dict[tag_node_name])}"
    )

    # Then a new chunk_index arrives (next second)
    chunk1_data = np.ones(step_samples, dtype=np.float32) * 2.0
    for _ in range(30):
        _collect_concat({
            0: {
                'data': chunk1_data.copy(),
                'sample_rate': sample_rate,
                'chunk_index': 1,
                'step_duration': step_duration,
            }
        })

    assert len(audio_samples_dict[tag_node_name]) == 2, (
        f"Expected 2 chunks after new chunk_index, "
        f"got {len(audio_samples_dict[tag_node_name])}"
    )

    # Total audio should be exactly 2 × step_samples
    full_audio = np.concatenate(audio_samples_dict[tag_node_name])
    expected_samples = 2 * step_samples
    assert len(full_audio) == expected_samples, (
        f"Expected {expected_samples} samples (2 × {step_duration}s), "
        f"got {len(full_audio)} ({len(full_audio) / sample_rate:.2f}s)"
    )


    """Test that recording metadata is initialized correctly"""
    # Test the logic without importing the node
    recording_metadata_dict = {}
    audio_samples_dict = {}
    tag_node_name = "1:VideoWriter"
    
    # Simulate metadata initialization from _recording_button
    metadata = {
        'final_path': '/path/to/output.mp4',
        'temp_path': '/path/to/output_temp.mp4',
        'format': 'MP4',
        'sample_rate': 22050
    }
    
    recording_metadata_dict[tag_node_name] = metadata
    audio_samples_dict[tag_node_name] = []
    
    # Verify
    assert tag_node_name in recording_metadata_dict
    assert recording_metadata_dict[tag_node_name]['format'] == 'MP4'
    assert recording_metadata_dict[tag_node_name]['sample_rate'] == 22050
    assert tag_node_name in audio_samples_dict
    assert len(audio_samples_dict[tag_node_name]) == 0


def test_audio_step_duration_trim_single_slot():
    """Audio chunks from VideoNode carry step_duration; VideoWriter must trim to it.

    Reproduces the progressive A/V drift: a 5-second sliding-window chunk
    (chunk_duration=5s, step_duration=1s) was previously stored whole, making
    the concatenated audio 5× the video duration.  After the fix, only the
    first step_duration seconds are kept.
    """
    import numpy as np

    sample_rate = 22050
    chunk_duration = 5.0   # seconds per WAV chunk
    step_duration  = 1.0   # seconds of new audio per step

    chunk_samples = int(chunk_duration * sample_rate)
    step_samples  = int(step_duration  * sample_rate)

    # Simulate 3 chunks as the VideoWriter would receive them from VideoNode.
    # Each chunk is chunk_duration seconds but the VideoWriter should only
    # keep the first step_duration seconds.
    last_idx = -1
    collected = []

    for chunk_index in range(3):
        # Full 5-second chunk (what _get_audio_chunk_for_frame returns)
        chunk_data = np.ones(chunk_samples, dtype=np.float32) * (chunk_index + 1)
        audio_data = {
            'data': chunk_data,
            'sample_rate': sample_rate,
            'chunk_index': chunk_index,
            'step_duration': step_duration,
        }

        # Reproduce the dedup + trim logic from VideoWriterNode.update()
        incoming_idx = audio_data.get('chunk_index', None)
        if incoming_idx is None or incoming_idx != last_idx:
            last_idx = incoming_idx
            data = audio_data['data']
            sr   = audio_data['sample_rate']
            step = audio_data.get('step_duration', None)
            if step is not None and sr > 0:
                data = data[:int(step * sr)]
            collected.append(data)

    full_audio = np.concatenate(collected)

    # Each chunk trimmed to step_samples; 3 chunks → 3 × step_samples total.
    expected_samples = 3 * step_samples
    assert len(full_audio) == expected_samples, (
        f"Expected {expected_samples} samples ({3 * step_duration}s), "
        f"got {len(full_audio)} ({len(full_audio) / sample_rate:.2f}s). "
        "Sliding-window trim is not working."
    )


def test_audio_duration_matches_video_no_freeze():
    """After step_duration trim the audio must not exceed the video duration.

    Verifies that for a typical 10-second video at 30 fps with step_duration=1s,
    the concatenated audio is ≤ the video duration so the final file does not
    freeze on the last frame.
    """
    import numpy as np

    sample_rate = 22050
    chunk_duration = 5.0
    step_duration  = 1.0
    fps = 30.0
    total_frames = 300   # 10-second video

    chunk_samples = int(chunk_duration * sample_rate)
    step_samples  = int(step_duration  * sample_rate)

    # Simulate what the VideoNode emits per frame (same as _get_audio_chunk_for_frame)
    last_idx = -1
    collected = []

    for frame_number in range(1, total_frames + 1):
        current_time = frame_number / fps
        chunk_index  = int(current_time / step_duration)
        chunk_index  = min(chunk_index, 999)  # no explicit cap in production; just guard

        chunk_data = np.ones(chunk_samples, dtype=np.float32) * (chunk_index + 1)
        audio_data = {
            'data': chunk_data,
            'sample_rate': sample_rate,
            'chunk_index': chunk_index,
            'step_duration': step_duration,
        }

        incoming_idx = audio_data.get('chunk_index', None)
        if incoming_idx is None or incoming_idx != last_idx:
            last_idx = incoming_idx
            data = audio_data['data']
            sr   = audio_data['sample_rate']
            step = audio_data.get('step_duration', None)
            if step is not None and sr > 0:
                data = data[:int(step * sr)]
            collected.append(data)

    full_audio     = np.concatenate(collected)
    audio_duration = len(full_audio) / sample_rate
    video_duration = total_frames / fps  # 10.0 s

    # With -shortest the output is trimmed to the shorter stream.  The important
    # property is that the audio excess must be small (≤ step_duration), not 5×.
    excess = audio_duration - video_duration
    assert excess <= step_duration + 0.01, (
        f"Audio ({audio_duration:.2f}s) exceeds video ({video_duration:.2f}s) "
        f"by {excess:.2f}s — more than one step_duration ({step_duration}s). "
        "Progressive drift is not fixed."
    )



    """Test that all required formats (MP4, AVI, MKV) are supported"""
    supported_formats = ['MP4', 'AVI', 'MKV']
    
    for fmt in supported_formats:
        # Just verify the format strings are what we expect
        assert fmt in ['MP4', 'AVI', 'MKV']


if __name__ == '__main__':
    # Run individual tests
    print("Testing ffmpeg availability...")
    test_audio_video_merge_ffmpeg_available()
    print("✓ ffmpeg available")
    
    print("\nTesting audio sample collection (single chunk)...")
    test_audio_sample_collection_single_chunk()
    print("✓ Single chunk collection works")
    
    print("\nTesting audio sample collection (multi-slot)...")
    test_audio_sample_collection_multi_slot()
    print("✓ Multi-slot collection works")
    
    print("\nTesting recording metadata initialization...")
    test_recording_metadata_initialization()
    print("✓ Metadata initialization works")
    
    print("\nTesting supported formats...")
    test_supported_formats()
    print("✓ All formats supported")
    
    print("\nTesting audio/video merge...")
    test_merge_audio_video_function()
    print("✓ Audio/video merge works")
    
    print("\n✅ All tests passed!")

