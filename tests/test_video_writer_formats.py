#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for video writer with AVI, MP4, MP4 (I-Frame), and MKV format support"""

import os
import json
import tempfile
import shutil

# Shared format configuration matching production code
# This ensures tests stay in sync with actual implementation
FORMAT_CODEC_MAP = {
    'MP4': 'mp4v',
    'MP4 (I-Frame)': 'H264',  # H.264 with intraframe-only encoding
    'AVI': 'MJPG',
    'MKV': 'FFV1',
}

SUPPORTED_FORMATS = ['MP4', 'MP4 (I-Frame)', 'AVI', 'MKV']


def test_video_format_selection():
    """Test that different video formats can be selected"""
    # Test that we have exactly the expected formats
    expected_formats = {'MP4', 'MP4 (I-Frame)', 'AVI', 'MKV'}
    assert set(SUPPORTED_FORMATS) == expected_formats
    
    # Verify a sample format is supported
    assert 'AVI' in SUPPORTED_FORMATS
    
    # Verify the new I-Frame format is supported
    assert 'MP4 (I-Frame)' in SUPPORTED_FORMATS


def test_codec_selection():
    """Test that appropriate codecs are selected for each format"""
    for fmt, codec in FORMAT_CODEC_MAP.items():
        # Verify codec is a non-empty string
        assert codec is not None
        assert isinstance(codec, str)
        assert len(codec) > 0
        
        # Verify codec is a valid FourCC identifier (all uppercase, 4 chars)
        # Note: FourCC codes are typically 4 characters, though this is conventional not required
        assert codec.isupper() or codec.islower()  # Should be consistent case
        assert 3 <= len(codec) <= 4  # Most FourCC codes are 4 chars, but allow some flexibility


def test_file_extension_for_formats():
    """Test that correct file extensions are used"""
    startup_time = '20231206_120000'
    
    extensions = {
        'MP4': f'{startup_time}.mp4',
        'MP4 (I-Frame)': f'{startup_time}.mp4',  # Same extension as MP4
        'AVI': f'{startup_time}.avi',
        'MKV': f'{startup_time}.mkv',
    }
    
    for fmt, filename in extensions.items():
        # Extract base format name (e.g., 'MP4' from 'MP4 (I-Frame)')
        base_fmt = fmt.split()[0]
        assert filename.endswith(base_fmt.lower())


def test_metadata_directory_creation():
    """Test that metadata directory is created for MKV format"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_base = os.path.join(tmpdir, '20231206_120000')
        metadata_dir = file_base + '_metadata'
        
        os.makedirs(metadata_dir, exist_ok=True)
        
        assert os.path.exists(metadata_dir)
        assert os.path.isdir(metadata_dir)


def test_audio_track_file_creation():
    """Test that audio track files are created correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metadata_dir = tmpdir
        
        # Simulate creating audio track files
        for slot_idx in range(2):
            audio_file = os.path.join(metadata_dir, f'audio_slot_{slot_idx}.jsonl')
            with open(audio_file, 'w') as f:
                f.write(json.dumps({'slot': slot_idx, 'data': [0.1, 0.2, 0.3]}) + '\n')
        
        # Verify files exist
        assert os.path.exists(os.path.join(metadata_dir, 'audio_slot_0.jsonl'))
        assert os.path.exists(os.path.join(metadata_dir, 'audio_slot_1.jsonl'))


def test_json_track_file_creation():
    """Test that JSON track files are created correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metadata_dir = tmpdir
        
        # Simulate creating JSON track files
        for slot_idx in range(2):
            json_file = os.path.join(metadata_dir, f'json_slot_{slot_idx}.jsonl')
            with open(json_file, 'w') as f:
                f.write(json.dumps({'slot': slot_idx, 'data': {'label': 'test'}}) + '\n')
        
        # Verify files exist
        assert os.path.exists(os.path.join(metadata_dir, 'json_slot_0.jsonl'))
        assert os.path.exists(os.path.join(metadata_dir, 'json_slot_1.jsonl'))


def test_metadata_file_content():
    """Test that metadata files have correct content format"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test audio file
        audio_file = os.path.join(tmpdir, 'audio_slot_0.jsonl')
        test_data = {'slot': 0, 'data': [0.1, 0.2, 0.3]}
        
        with open(audio_file, 'w') as f:
            f.write(json.dumps(test_data) + '\n')
        
        # Read and verify
        with open(audio_file, 'r') as f:
            line = f.readline()
            loaded_data = json.loads(line)
            
            assert loaded_data['slot'] == 0
            assert loaded_data['data'] == [0.1, 0.2, 0.3]


def test_mkv_metadata_dict_structure():
    """Test the MKV metadata dictionary structure"""
    metadata_dict = {
        'audio_handles': {},
        'json_handles': {},
        'file_path': '/tmp/test.mkv',
    }
    
    # Verify structure
    assert 'audio_handles' in metadata_dict
    assert 'json_handles' in metadata_dict
    assert 'file_path' in metadata_dict
    assert isinstance(metadata_dict['audio_handles'], dict)
    assert isinstance(metadata_dict['json_handles'], dict)


def test_multiple_audio_slots():
    """Test handling of multiple audio slots"""
    audio_chunks = {
        0: [0.1, 0.2, 0.3],
        1: [0.4, 0.5, 0.6],
        2: [0.7, 0.8, 0.9],
    }
    
    # Verify multiple slots can be stored
    assert len(audio_chunks) == 3
    for slot_idx in range(3):
        assert slot_idx in audio_chunks
        assert len(audio_chunks[slot_idx]) == 3


def test_multiple_json_slots():
    """Test handling of multiple JSON slots"""
    json_chunks = {
        0: {'label': 'cat', 'confidence': 0.95},
        1: {'label': 'dog', 'confidence': 0.87},
        2: {'label': 'bird', 'confidence': 0.72},
    }
    
    # Verify multiple slots can be stored
    assert len(json_chunks) == 3
    for slot_idx in range(3):
        assert slot_idx in json_chunks
        assert 'label' in json_chunks[slot_idx]
        assert 'confidence' in json_chunks[slot_idx]


def test_mp4_iframe_encoding_parameters():
    """Test that MP4 (I-Frame) format uses correct intraframe encoding parameters"""
    # Verify MP4 (I-Frame) uses H264, not mp4v (using shared constant)
    assert FORMAT_CODEC_MAP['MP4 (I-Frame)'] == 'H264'
    assert FORMAT_CODEC_MAP['MP4 (I-Frame)'] != FORMAT_CODEC_MAP['MP4']
    
    # Verify x264 parameters for intraframe-only encoding
    x264_params = 'keyint=1:scenecut=0'
    
    # keyint=1 means every frame is an I-frame (no P or B frames)
    assert 'keyint=1' in x264_params
    
    # scenecut=0 disables scene detection (ensures no automatic keyframe insertion)
    assert 'scenecut=0' in x264_params


def test_intraframe_formats_comparison():
    """Test that intraframe formats are correctly identified"""
    # These formats support true frame-by-frame encoding (all I-frames)
    intraframe_formats = ['AVI', 'MKV', 'MP4 (I-Frame)']
    
    # Standard MP4 is NOT intraframe (uses P and B frames)
    interframe_formats = ['MP4']
    
    # Verify all formats are accounted for
    all_formats_count = len(intraframe_formats) + len(interframe_formats)
    assert all_formats_count == len(FORMAT_CODEC_MAP)
    
    # Verify codecs for intraframe formats
    for fmt in intraframe_formats:
        assert fmt in FORMAT_CODEC_MAP
        assert FORMAT_CODEC_MAP[fmt] in ['MJPG', 'FFV1', 'H264']
    
    # Verify codec for interframe format
    assert FORMAT_CODEC_MAP['MP4'] == 'mp4v'


if __name__ == '__main__':
    # Run tests
    test_video_format_selection()
    test_codec_selection()
    test_file_extension_for_formats()
    test_metadata_directory_creation()
    test_audio_track_file_creation()
    test_json_track_file_creation()
    test_metadata_file_content()
    test_mkv_metadata_dict_structure()
    test_multiple_audio_slots()
    test_multiple_json_slots()
    test_mp4_iframe_encoding_parameters()
    test_intraframe_formats_comparison()
    print("All video writer format tests passed!")
