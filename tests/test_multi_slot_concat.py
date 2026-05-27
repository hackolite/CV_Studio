#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for multi-slot concat node with IMAGE, AUDIO, and JSON support"""

import pytest
import numpy as np
from unittest.mock import patch


def test_slot_type_initialization():
    """Test that slot types are properly initialized"""
    from node.VideoNode.node_image_concat import Node
    
    node = Node()
    tag_node_name = "test_node:ImageConcat"
    
    # Initialize slot tracking
    node._slot_id[tag_node_name] = 1
    node._slot_types[tag_node_name] = {1: node.TYPE_IMAGE}
    
    # Verify initialization
    assert node._slot_id[tag_node_name] == 1
    assert node._slot_types[tag_node_name][1] == node.TYPE_IMAGE


def test_slot_type_storage():
    """Test that different slot types can be stored"""
    from node.VideoNode.node_image_concat import Node
    
    node = Node()
    tag_node_name = "test_node:ImageConcat"
    
    # Initialize
    node._slot_id[tag_node_name] = 3
    node._slot_types[tag_node_name] = {
        1: node.TYPE_IMAGE,
        2: node.TYPE_AUDIO,
        3: node.TYPE_JSON,
    }
    
    # Verify all types are stored correctly
    assert node._slot_types[tag_node_name][1] == node.TYPE_IMAGE
    assert node._slot_types[tag_node_name][2] == node.TYPE_AUDIO
    assert node._slot_types[tag_node_name][3] == node.TYPE_JSON


def test_connection_type_handling():
    """Test that connection types are properly identified"""
    from node.VideoNode.node_image_concat import Node
    
    node = Node()
    
    # Test connection info parsing
    connection_types = [
        ('test:node:IMAGE:Output01', 'IMAGE'),
        ('test:node:AUDIO:Output01', 'AUDIO'),
        ('test:node:JSON:Output01', 'JSON'),
    ]
    
    for connection_info, expected_type in connection_types:
        connection_type = connection_info.split(':')[2]
        assert connection_type == expected_type


def test_slot_data_dict_structure():
    """Test the slot_data_dict structure used in update()"""
    slot_data_dict = {}
    
    # Add IMAGE slot
    slot_data_dict[0] = {
        'type': 'IMAGE',
        'source': '1:TestNode'
    }
    
    # Add AUDIO slot
    slot_data_dict[1] = {
        'type': 'AUDIO',
        'source': '2:AudioNode'
    }
    
    # Add JSON slot
    slot_data_dict[2] = {
        'type': 'JSON',
        'source': '3:DataNode'
    }
    
    # Verify structure
    assert len(slot_data_dict) == 3
    assert slot_data_dict[0]['type'] == 'IMAGE'
    assert slot_data_dict[1]['type'] == 'AUDIO'
    assert slot_data_dict[2]['type'] == 'JSON'


def test_audio_chunks_collection():
    """Test audio chunks collection from slots"""
    audio_chunks = {}
    
    # Simulate audio data from different slots
    audio_chunks[0] = np.array([0.1, 0.2, 0.3])
    audio_chunks[1] = np.array([0.4, 0.5, 0.6])
    
    # Verify collection
    assert len(audio_chunks) == 2
    assert isinstance(audio_chunks[0], np.ndarray)
    assert len(audio_chunks[0]) == 3


def test_json_chunks_collection():
    """Test JSON chunks collection from slots"""
    json_chunks = {}
    
    # Simulate JSON data from different slots
    json_chunks[0] = {'label': 'cat', 'confidence': 0.95}
    json_chunks[1] = {'label': 'dog', 'confidence': 0.87}
    
    # Verify collection
    assert len(json_chunks) == 2
    assert json_chunks[0]['label'] == 'cat'
    assert json_chunks[1]['label'] == 'dog'


def test_output_data_structure():
    """Test the output data structure from concat node"""
    # Simulate return value from update()
    output = {
        "image": np.zeros((480, 640, 3), dtype=np.uint8),
        "json": {0: {'data': 'test'}, 1: {'data': 'test2'}},
        "audio": {0: np.array([0.1, 0.2])}
    }
    
    # Verify structure
    assert 'image' in output
    assert 'json' in output
    assert 'audio' in output
    assert isinstance(output['image'], np.ndarray)
    assert isinstance(output['json'], dict)
    assert isinstance(output['audio'], dict)


def test_setting_dict_with_slot_types():
    """Test that slot types are saved in settings"""
    setting_dict = {
        'ver': '0.0.2',
        'pos': [100, 200],
        'slot_id': 3,
        'slot_types': {
            1: 'IMAGE',
            2: 'AUDIO',
            3: 'JSON'
        }
    }
    
    # Verify slot types are in settings
    assert 'slot_types' in setting_dict
    assert setting_dict['slot_types'][1] == 'IMAGE'
    assert setting_dict['slot_types'][2] == 'AUDIO'
    assert setting_dict['slot_types'][3] == 'JSON'


def test_image_slot_passes_through_audio():
    """Test that IMAGE slots also forward their audio payload when available."""
    from node.VideoNode.node_image_concat import Node

    node = Node()
    tag_node_name = "1:ImageConcat"
    node.tag_node_name = tag_node_name
    node._opencv_setting_dict = {
        'process_width': 64,
        'process_height': 48,
        'result_width': 64,
        'result_height': 48,
        'draw_info_on_result': False,
    }
    node._slot_id[tag_node_name] = 1
    node._slot_types[tag_node_name] = {1: node.TYPE_IMAGE}
    node._value_history = {}

    source = "0:Video"
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    audio_chunk = {
        'data': np.array([0.1, 0.2, 0.3], dtype=np.float32),
        'sample_rate': 16000,
        'chunk_index': 7,
    }

    connection_list = [
        (f"{source}:{node.TYPE_IMAGE}:Output01", f"{tag_node_name}:{node.TYPE_IMAGE}:Input01")
    ]
    node_image_dict = {source: frame}
    node_audio_dict = {source: audio_chunk}

    with patch('node.VideoNode.node_image_concat.dpg_set_value'):
        result = node.update(
            1,
            connection_list,
            node_image_dict,
            {},
            node_audio_dict,
        )

    assert result['audio'] is not None
    assert 0 in result['audio']
    assert result['audio'][0]['sample_rate'] == 16000
    assert result['audio'][0]['chunk_index'] == 7
    np.testing.assert_array_equal(result['audio'][0]['data'], audio_chunk['data'])


def test_non_video_image_slot_does_not_pass_through_audio():
    """Test that IMAGE slots only pass audio through when source node is Video."""
    from node.VideoNode.node_image_concat import Node

    node = Node()
    tag_node_name = "1:ImageConcat"
    node.tag_node_name = tag_node_name
    node._opencv_setting_dict = {
        'process_width': 64,
        'process_height': 48,
        'result_width': 64,
        'result_height': 48,
        'draw_info_on_result': False,
    }
    node._slot_id[tag_node_name] = 1
    node._slot_types[tag_node_name] = {1: node.TYPE_IMAGE}
    node._value_history = {}

    source = "0:AudioClassification"
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    audio_chunk = {
        'data': np.array([0.1, 0.2, 0.3], dtype=np.float32),
        'sample_rate': 16000,
        'chunk_index': 7,
    }

    connection_list = [
        (f"{source}:{node.TYPE_IMAGE}:Output01", f"{tag_node_name}:{node.TYPE_IMAGE}:Input01")
    ]
    node_image_dict = {source: frame}
    node_audio_dict = {source: audio_chunk}

    with patch('node.VideoNode.node_image_concat.dpg_set_value'):
        result = node.update(
            1,
            connection_list,
            node_image_dict,
            {},
            node_audio_dict,
        )

    assert result['audio'] is None


if __name__ == '__main__':
    # Run tests
    test_slot_type_initialization()
    test_slot_type_storage()
    test_connection_type_handling()
    test_slot_data_dict_structure()
    test_audio_chunks_collection()
    test_json_chunks_collection()
    test_output_data_structure()
    test_setting_dict_with_slot_types()
    test_image_slot_passes_through_audio()
    test_non_video_image_slot_does_not_pass_through_audio()
    print("All multi-slot concat tests passed!")
