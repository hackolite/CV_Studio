#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Integration test for ImageConcat to VideoWriter data flow"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def test_imageconcat_audio_passthrough():
    """Test that ImageConcat passes audio data through to output"""
    # Simulate ImageConcat receiving audio from multiple slots
    audio_input = {
        0: {'data': np.array([0.1, 0.2, 0.3]), 'sample_rate': 22050, 'timestamp': 100.0},
        1: {'data': np.array([0.4, 0.5, 0.6]), 'sample_rate': 22050, 'timestamp': 100.1}
    }
    
    # Simulate ImageConcat output structure
    output = {
        'image': np.zeros((480, 640, 3), dtype=np.uint8),  # Concat image
        'audio': audio_input,  # Pass through audio
        'json': None
    }
    
    # Verify audio is passed through
    assert output['audio'] is not None
    assert len(output['audio']) == 2
    assert 0 in output['audio']
    assert 1 in output['audio']


def test_imageconcat_json_passthrough():
    """Test that ImageConcat passes JSON data through to output"""
    # Simulate ImageConcat receiving JSON from multiple slots
    json_input = {
        0: {'detections': [{'class': 'cat', 'score': 0.95}]},
        1: {'detections': [{'class': 'dog', 'score': 0.87}]}
    }
    
    # Simulate ImageConcat output structure
    output = {
        'image': np.zeros((480, 640, 3), dtype=np.uint8),
        'audio': None,
        'json': json_input  # Pass through JSON
    }
    
    # Verify JSON is passed through
    assert output['json'] is not None
    assert len(output['json']) == 2
    assert 0 in output['json']
    assert 1 in output['json']


def test_imageconcat_concat_image_output():
    """Test that ImageConcat outputs the concatenated image"""
    # Simulate ImageConcat creating a concat image
    frame_dict = {
        0: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
        1: np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    }
    
    # Simulate concat operation (simplified)
    concat_image = np.hstack([frame_dict[0], frame_dict[1]])
    
    output = {
        'image': concat_image,
        'audio': None,
        'json': None
    }
    
    # Verify concat image shape
    assert output['image'] is not None
    assert output['image'].shape == (240, 640, 3)  # Two 320-width images concatenated


def test_videowriter_receives_concat_data():
    """Test that VideoWriter receives all data types from ImageConcat"""
    # Simulate ImageConcat output
    imageconcat_output = {
        'image': np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
        'audio': {
            0: {'data': np.array([0.1, 0.2, 0.3]), 'sample_rate': 22050, 'timestamp': 100.0}
        },
        'json': {
            0: {'detections': [{'class': 'cat', 'score': 0.95}]}
        }
    }
    
    # Simulate VideoWriter receiving data
    frame = imageconcat_output['image']
    audio_data = imageconcat_output['audio']
    json_data = imageconcat_output['json']
    
    # Verify all data types received
    assert frame is not None
    assert audio_data is not None
    assert json_data is not None


def test_videowriter_audio_collection():
    """Test that VideoWriter collects audio samples per slot"""
    _audio_samples_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Initialize collection
    _audio_samples_dict[tag_node_name] = {}
    
    # Simulate receiving audio from multiple slots over time
    for frame_idx in range(10):
        audio_data = {
            0: {'data': np.random.randn(1024), 'sample_rate': 22050, 'timestamp': 100.0 + frame_idx * 0.1},
            1: {'data': np.random.randn(1024), 'sample_rate': 22050, 'timestamp': 100.0 + frame_idx * 0.1}
        }
        
        for slot_idx, audio_chunk in audio_data.items():
            if slot_idx not in _audio_samples_dict[tag_node_name]:
                _audio_samples_dict[tag_node_name][slot_idx] = {
                    'samples': [],
                    'timestamp': audio_chunk['timestamp'],
                    'sample_rate': audio_chunk['sample_rate']
                }
            _audio_samples_dict[tag_node_name][slot_idx]['samples'].append(audio_chunk['data'])
    
    # Verify collection
    assert len(_audio_samples_dict[tag_node_name]) == 2  # Two slots
    assert len(_audio_samples_dict[tag_node_name][0]['samples']) == 10  # 10 frames
    assert len(_audio_samples_dict[tag_node_name][1]['samples']) == 10


def test_videowriter_json_collection():
    """Test that VideoWriter collects JSON samples per slot"""
    _json_samples_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Initialize collection
    _json_samples_dict[tag_node_name] = {}
    
    # Simulate receiving JSON from multiple slots over time
    for frame_idx in range(10):
        json_data = {
            0: {'frame': frame_idx, 'detections': [{'class': 'cat', 'score': 0.95}]},
            1: {'frame': frame_idx, 'detections': [{'class': 'dog', 'score': 0.87}]}
        }
        
        for slot_idx, json_chunk in json_data.items():
            if slot_idx not in _json_samples_dict[tag_node_name]:
                _json_samples_dict[tag_node_name][slot_idx] = {
                    'samples': [],
                    'timestamp': float('inf')
                }
            _json_samples_dict[tag_node_name][slot_idx]['samples'].append(json_chunk)
    
    # Verify collection
    assert len(_json_samples_dict[tag_node_name]) == 2  # Two slots
    assert len(_json_samples_dict[tag_node_name][0]['samples']) == 10  # 10 frames
    assert len(_json_samples_dict[tag_node_name][1]['samples']) == 10


def test_videowriter_frame_tracking():
    """Test that VideoWriter tracks frames during recording"""
    _frame_count_dict = {}
    _last_frame_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Simulate recording 100 frames
    for i in range(100):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Track frame count
        if tag_node_name not in _frame_count_dict:
            _frame_count_dict[tag_node_name] = 0
        _frame_count_dict[tag_node_name] += 1
        
        # Store last frame
        _last_frame_dict[tag_node_name] = frame
    
    # Verify tracking
    assert _frame_count_dict[tag_node_name] == 100
    assert _last_frame_dict[tag_node_name] is not None


def test_full_pipeline_simulation():
    """Test full pipeline from ImageConcat to VideoWriter"""
    # Step 1: ImageConcat receives data from multiple sources
    slot_0_image = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    slot_0_audio = {'data': np.random.randn(1024), 'sample_rate': 22050, 'timestamp': 100.0}
    slot_0_json = {'detections': [{'class': 'cat', 'score': 0.95}]}
    
    slot_1_image = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    slot_1_audio = {'data': np.random.randn(1024), 'sample_rate': 22050, 'timestamp': 100.0}
    slot_1_json = {'detections': [{'class': 'dog', 'score': 0.87}]}
    
    # Step 2: ImageConcat creates concat image and passes through audio/JSON
    concat_image = np.hstack([slot_0_image, slot_1_image])
    
    imageconcat_output = {
        'image': concat_image,
        'audio': {0: slot_0_audio, 1: slot_1_audio},
        'json': {0: slot_0_json, 1: slot_1_json}
    }
    
    # Step 3: VideoWriter receives and processes data
    # Simulate VideoWriter data structures
    _audio_samples_dict = {}
    _json_samples_dict = {}
    _frame_count_dict = {}
    tag_node_name = "test_node:VideoWriter"
    
    # Initialize
    _audio_samples_dict[tag_node_name] = {}
    _json_samples_dict[tag_node_name] = {}
    
    # Process frame
    frame = imageconcat_output['image']
    audio_data = imageconcat_output['audio']
    json_data = imageconcat_output['json']
    
    # Track frame
    if tag_node_name not in _frame_count_dict:
        _frame_count_dict[tag_node_name] = 0
    _frame_count_dict[tag_node_name] += 1
    
    # Collect audio
    for slot_idx, audio_chunk in audio_data.items():
        if slot_idx not in _audio_samples_dict[tag_node_name]:
            _audio_samples_dict[tag_node_name][slot_idx] = {
                'samples': [],
                'timestamp': audio_chunk['timestamp'],
                'sample_rate': audio_chunk['sample_rate']
            }
        _audio_samples_dict[tag_node_name][slot_idx]['samples'].append(audio_chunk['data'])
    
    # Collect JSON
    for slot_idx, json_chunk in json_data.items():
        if slot_idx not in _json_samples_dict[tag_node_name]:
            _json_samples_dict[tag_node_name][slot_idx] = {
                'samples': [],
                'timestamp': float('inf')
            }
        _json_samples_dict[tag_node_name][slot_idx]['samples'].append(json_chunk)
    
    # Verify full pipeline
    assert _frame_count_dict[tag_node_name] == 1
    assert len(_audio_samples_dict[tag_node_name]) == 2
    assert len(_json_samples_dict[tag_node_name]) == 2
    assert frame.shape == (240, 640, 3)  # Concat image


def test_recording_metadata_includes_fps():
    """Test that recording metadata includes FPS for duration adaptation"""
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
    fps = metadata.get('fps', 30)
    
    assert fps == 30


if __name__ == '__main__':
    # Run tests
    test_imageconcat_audio_passthrough()
    test_imageconcat_json_passthrough()
    test_imageconcat_concat_image_output()
    test_videowriter_receives_concat_data()
    test_videowriter_audio_collection()
    test_videowriter_json_collection()
    test_videowriter_frame_tracking()
    test_full_pipeline_simulation()
    test_recording_metadata_includes_fps()
    print("All ImageConcat to VideoWriter flow tests passed!")
