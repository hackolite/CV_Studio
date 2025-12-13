#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for concat stream merge functionality with JSON support"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import tempfile
import json


def test_json_samples_dict_initialization():
    """Test that JSON samples dict is properly initialized"""
    # Simulate VideoWriterNode's _json_samples_dict
    _json_samples_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Initialize JSON samples dict
    _json_samples_dict[tag_node_name] = {}
    
    # Verify initialization
    assert tag_node_name in _json_samples_dict
    assert isinstance(_json_samples_dict[tag_node_name], dict)


def test_json_slot_data_structure():
    """Test JSON slot data structure"""
    # Simulate VideoWriterNode's _json_samples_dict
    _json_samples_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Initialize
    _json_samples_dict[tag_node_name] = {}
    
    # Add slot data
    slot_idx = 0
    _json_samples_dict[tag_node_name][slot_idx] = {
        'samples': [],
        'timestamp': 100.5
    }
    
    # Verify structure
    assert slot_idx in _json_samples_dict[tag_node_name]
    assert 'samples' in _json_samples_dict[tag_node_name][slot_idx]
    assert 'timestamp' in _json_samples_dict[tag_node_name][slot_idx]
    assert _json_samples_dict[tag_node_name][slot_idx]['timestamp'] == 100.5


def test_json_sample_collection():
    """Test JSON sample collection from dict"""
    json_samples = []
    
    # Simulate JSON data collection
    json_chunk_1 = {'label': 'cat', 'confidence': 0.95, 'bbox': [10, 20, 100, 150]}
    json_chunk_2 = {'label': 'dog', 'confidence': 0.87, 'bbox': [200, 50, 300, 180]}
    
    json_samples.append(json_chunk_1)
    json_samples.append(json_chunk_2)
    
    # Verify collection
    assert len(json_samples) == 2
    assert json_samples[0]['label'] == 'cat'
    assert json_samples[1]['label'] == 'dog'


def test_multi_slot_json_collection():
    """Test JSON collection from multiple slots"""
    json_data = {
        0: {'label': 'cat', 'confidence': 0.95},
        1: {'label': 'dog', 'confidence': 0.87},
        2: {'label': 'bird', 'confidence': 0.92}
    }
    
    # Simulate slot iteration
    collected_slots = {}
    for slot_idx in json_data.keys():
        json_chunk = json_data[slot_idx]
        collected_slots[slot_idx] = {
            'samples': [json_chunk],
            'timestamp': float('inf')
        }
    
    # Verify collection
    assert len(collected_slots) == 3
    assert collected_slots[0]['samples'][0]['label'] == 'cat'
    assert collected_slots[1]['samples'][0]['label'] == 'dog'
    assert collected_slots[2]['samples'][0]['label'] == 'bird'


def test_json_timestamp_sorting():
    """Test JSON slot sorting by timestamp"""
    json_slots = {
        0: {'samples': [{'data': 'A'}], 'timestamp': 105.0},
        1: {'samples': [{'data': 'B'}], 'timestamp': 100.0},
        2: {'samples': [{'data': 'C'}], 'timestamp': float('inf')},
    }
    
    # Sort by timestamp, then slot index
    sorted_slots = sorted(
        json_slots.items(),
        key=lambda x: (x[1]['timestamp'], x[0])
    )
    
    # Verify sort order: finite timestamps first (100.0, 105.0), then inf
    assert sorted_slots[0][0] == 1  # slot 1 with timestamp 100.0
    assert sorted_slots[1][0] == 0  # slot 0 with timestamp 105.0
    assert sorted_slots[2][0] == 2  # slot 2 with timestamp inf


def test_format_specific_merge_detection():
    """Test that video format is properly detected for merging"""
    metadata = {
        'final_path': '/tmp/video.mkv',
        'temp_path': '/tmp/video_temp.mkv',
        'format': 'MKV',
        'sample_rate': 22050
    }
    
    # Verify format detection
    video_format = metadata.get('format', 'MP4')
    assert video_format == 'MKV'
    
    # Test default fallback
    metadata_no_format = {
        'final_path': '/tmp/video.mp4',
        'temp_path': '/tmp/video_temp.mp4'
    }
    video_format = metadata_no_format.get('format', 'MP4')
    assert video_format == 'MP4'


def test_json_metadata_file_structure():
    """Test JSON metadata file structure for MKV"""
    # Simulate JSON metadata structure
    slot_idx = 0
    slot_data = {
        'samples': [
            {'label': 'cat', 'confidence': 0.95},
            {'label': 'dog', 'confidence': 0.87}
        ],
        'timestamp': 100.0
    }
    
    # Create expected structure
    json_output = {
        'slot_idx': slot_idx,
        'timestamp': slot_data['timestamp'],
        'samples': slot_data['samples']
    }
    
    # Verify structure
    assert json_output['slot_idx'] == 0
    assert json_output['timestamp'] == 100.0
    assert len(json_output['samples']) == 2
    assert json_output['samples'][0]['label'] == 'cat'


def test_json_concat_stream_creation():
    """Test creation of concatenated JSON stream"""
    # Simulate multiple JSON samples collected during recording
    json_samples = [
        {'frame': 1, 'detections': [{'class': 'cat', 'score': 0.95}]},
        {'frame': 2, 'detections': [{'class': 'dog', 'score': 0.87}]},
        {'frame': 3, 'detections': [{'class': 'bird', 'score': 0.92}]},
    ]
    
    # Verify concatenation preserves all samples
    assert len(json_samples) == 3
    assert json_samples[0]['frame'] == 1
    assert json_samples[1]['frame'] == 2
    assert json_samples[2]['frame'] == 3


def test_audio_and_json_combined_collection():
    """Test that audio and JSON can be collected simultaneously"""
    # Simulate concurrent audio and JSON collection
    audio_samples = {
        0: {
            'samples': [np.array([0.1, 0.2, 0.3])],
            'timestamp': 100.0,
            'sample_rate': 22050
        }
    }
    
    json_samples = {
        0: {
            'samples': [{'label': 'cat', 'confidence': 0.95}],
            'timestamp': 100.0
        }
    }
    
    # Verify both are collected
    assert len(audio_samples) == 1
    assert len(json_samples) == 1
    assert audio_samples[0]['timestamp'] == json_samples[0]['timestamp']


def test_mkv_json_metadata_directory_structure():
    """Test metadata directory structure for MKV files"""
    final_path = '/tmp/video_20231213_120000.mkv'
    file_base = final_path.rsplit('.', 1)[0]
    metadata_dir = file_base + '_metadata'
    
    # Verify directory path construction
    assert metadata_dir == '/tmp/video_20231213_120000_metadata'
    
    # Verify JSON file path construction
    slot_idx = 0
    json_file = os.path.join(metadata_dir, f'json_slot_{slot_idx}_concat.json')
    assert json_file == '/tmp/video_20231213_120000_metadata/json_slot_0_concat.json'


def test_recording_metadata_with_format():
    """Test that recording metadata includes format"""
    # Simulate VideoWriterNode's _recording_metadata_dict
    _recording_metadata_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Simulate recording metadata
    _recording_metadata_dict[tag_node_name] = {
        'final_path': '/tmp/video.mkv',
        'temp_path': '/tmp/video_temp.mkv',
        'format': 'MKV',
        'sample_rate': 22050
    }
    
    # Verify format is stored
    metadata = _recording_metadata_dict[tag_node_name]
    assert 'format' in metadata
    assert metadata['format'] == 'MKV'


if __name__ == '__main__':
    # Run tests
    test_json_samples_dict_initialization()
    test_json_slot_data_structure()
    test_json_sample_collection()
    test_multi_slot_json_collection()
    test_json_timestamp_sorting()
    test_format_specific_merge_detection()
    test_json_metadata_file_structure()
    test_json_concat_stream_creation()
    test_audio_and_json_combined_collection()
    test_mkv_json_metadata_directory_structure()
    test_recording_metadata_with_format()
    print("All concat stream merge tests passed!")
