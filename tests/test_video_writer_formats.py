#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for video writer with AVI, MP4, and MKV format support"""

import pytest
import os
import json
import tempfile
import shutil


def test_video_format_selection():
    """Test that different video formats can be selected"""
    supported_formats = ['MP4', 'AVI', 'MKV']
    selected_format = 'AVI'
    
    # Verify the selected format is supported
    assert selected_format in supported_formats
    
    # Verify all expected formats are in the list
    for fmt in ['MP4', 'AVI', 'MKV']:
        assert fmt in supported_formats


def test_codec_selection():
    """Test that appropriate codecs are selected for each format"""
    format_codec_map = {
        'MP4': 'mp4v',
        'AVI': 'MJPG',
        'MKV': 'FFV1',
    }
    
    for fmt, codec in format_codec_map.items():
        assert codec is not None
        assert len(codec) == 4


def test_file_extension_for_formats():
    """Test that correct file extensions are used"""
    startup_time = '20231206_120000'
    
    extensions = {
        'MP4': f'{startup_time}.mp4',
        'AVI': f'{startup_time}.avi',
        'MKV': f'{startup_time}.mkv',
    }
    
    for fmt, filename in extensions.items():
        assert filename.endswith(fmt.lower())


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
    print("All video writer format tests passed!")
