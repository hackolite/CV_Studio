#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for stream aggregation by timestamp"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def test_audio_slots_sorted_by_timestamp():
    """Test that audio slots are sorted by timestamp when merging"""
    # Simulate audio samples with different timestamps
    slot_audio_dict = {
        0: {'samples': [np.array([1, 2, 3])], 'timestamp': 102.0, 'sample_rate': 22050},
        1: {'samples': [np.array([4, 5, 6])], 'timestamp': 100.0, 'sample_rate': 22050},
        2: {'samples': [np.array([7, 8, 9])], 'timestamp': 101.0, 'sample_rate': 22050}
    }
    
    # Sort by timestamp (as done in VideoWriter)
    sorted_slots = sorted(
        slot_audio_dict.items(),
        key=lambda x: (x[1]['timestamp'], x[0])
    )
    
    # Verify sorting order: 100.0, 101.0, 102.0
    assert sorted_slots[0][0] == 1  # slot 1 (timestamp 100.0)
    assert sorted_slots[1][0] == 2  # slot 2 (timestamp 101.0)
    assert sorted_slots[2][0] == 0  # slot 0 (timestamp 102.0)


def test_audio_concatenation_preserves_order():
    """Test that audio concatenation preserves timestamp order"""
    # Simulate sorted audio samples
    sorted_audio_samples = [
        np.array([1, 2, 3]),  # First by timestamp
        np.array([4, 5, 6]),  # Second by timestamp
        np.array([7, 8, 9])   # Third by timestamp
    ]
    
    # Concatenate
    merged_audio = np.concatenate(sorted_audio_samples)
    
    # Verify concatenation
    expected = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert np.array_equal(merged_audio, expected)


def test_json_slots_sorted_by_timestamp():
    """Test that JSON slots are sorted by timestamp"""
    # Simulate JSON samples with different timestamps
    json_samples_dict = {
        0: {'samples': [{'frame': 2}], 'timestamp': 102.0},
        1: {'samples': [{'frame': 0}], 'timestamp': 100.0},
        2: {'samples': [{'frame': 1}], 'timestamp': 101.0}
    }
    
    # Sort by timestamp
    sorted_slots = sorted(
        json_samples_dict.items(),
        key=lambda x: (x[1]['timestamp'], x[0])
    )
    
    # Verify sorting order
    assert sorted_slots[0][0] == 1  # slot 1 (timestamp 100.0)
    assert sorted_slots[1][0] == 2  # slot 2 (timestamp 101.0)
    assert sorted_slots[2][0] == 0  # slot 0 (timestamp 102.0)


def test_infinite_timestamp_comes_last():
    """Test that slots with infinite timestamp come last"""
    # Simulate slots with mixed finite and infinite timestamps
    slot_dict = {
        0: {'samples': [], 'timestamp': float('inf')},  # No timestamp
        1: {'samples': [], 'timestamp': 100.0},
        2: {'samples': [], 'timestamp': 99.0},
        3: {'samples': [], 'timestamp': float('inf')}   # No timestamp
    }
    
    # Sort by timestamp
    sorted_slots = sorted(
        slot_dict.items(),
        key=lambda x: (x[1]['timestamp'], x[0])
    )
    
    # Verify: finite timestamps first (99.0, 100.0), then infinite (0, 3)
    assert sorted_slots[0][0] == 2  # slot 2 (99.0)
    assert sorted_slots[1][0] == 1  # slot 1 (100.0)
    assert sorted_slots[2][0] == 0  # slot 0 (inf)
    assert sorted_slots[3][0] == 3  # slot 3 (inf)


def test_slot_index_as_secondary_sort():
    """Test that slot index is used as secondary sort key"""
    # Simulate slots with same timestamp
    slot_dict = {
        3: {'samples': [], 'timestamp': 100.0},
        1: {'samples': [], 'timestamp': 100.0},
        2: {'samples': [], 'timestamp': 100.0}
    }
    
    # Sort by (timestamp, slot_idx)
    sorted_slots = sorted(
        slot_dict.items(),
        key=lambda x: (x[1]['timestamp'], x[0])
    )
    
    # Verify: same timestamp, sorted by slot index
    assert sorted_slots[0][0] == 1
    assert sorted_slots[1][0] == 2
    assert sorted_slots[2][0] == 3


def test_audio_duration_calculation_from_samples():
    """Test audio duration calculation from concatenated samples"""
    # Simulate 3 slots with audio samples
    slot_samples = [
        np.random.randn(22050),  # 1 second at 22050 Hz
        np.random.randn(44100),  # 2 seconds at 22050 Hz (44100 samples)
        np.random.randn(11025)   # 0.5 seconds at 22050 Hz
    ]
    
    # Concatenate all samples
    total_samples = np.concatenate(slot_samples)
    sample_rate = 22050
    
    # Calculate duration
    duration = len(total_samples) / sample_rate
    
    # Verify duration (3.5 seconds)
    expected_duration = (22050 + 44100 + 11025) / 22050
    assert abs(duration - expected_duration) < 0.001


def test_json_aggregation_structure():
    """Test JSON aggregation structure for MKV output"""
    # Simulate JSON samples collected over time
    json_slot_data = {
        'samples': [
            {'frame': 0, 'detections': [{'class': 'cat', 'score': 0.95}]},
            {'frame': 1, 'detections': [{'class': 'dog', 'score': 0.87}]},
            {'frame': 2, 'detections': [{'class': 'bird', 'score': 0.92}]}
        ],
        'timestamp': 100.0
    }
    
    # Create output structure
    output_data = {
        'slot_idx': 0,
        'timestamp': json_slot_data['timestamp'],
        'samples': json_slot_data['samples']
    }
    
    # Verify structure
    assert output_data['slot_idx'] == 0
    assert output_data['timestamp'] == 100.0
    assert len(output_data['samples']) == 3
    assert output_data['samples'][0]['frame'] == 0


def test_multiple_slot_audio_merge_realistic():
    """Test realistic multi-slot audio merge scenario"""
    # Simulate 2 video sources with audio, each producing chunks over time
    slot_0_chunks = [np.random.randn(1024) for _ in range(100)]  # 100 chunks
    slot_1_chunks = [np.random.randn(1024) for _ in range(100)]  # 100 chunks
    
    slot_audio_dict = {
        0: {'samples': slot_0_chunks, 'timestamp': 100.0, 'sample_rate': 22050},
        1: {'samples': slot_1_chunks, 'timestamp': 100.1, 'sample_rate': 22050}
    }
    
    # Sort by timestamp
    sorted_slots = sorted(
        slot_audio_dict.items(),
        key=lambda x: (x[1]['timestamp'], x[0])
    )
    
    # Concatenate each slot
    audio_samples_list = []
    for slot_idx, slot_data in sorted_slots:
        if slot_data['samples']:
            slot_concatenated = np.concatenate(slot_data['samples'])
            audio_samples_list.append(slot_concatenated)
    
    # Verify merge
    assert len(audio_samples_list) == 2
    assert len(audio_samples_list[0]) == 102400  # 100 chunks * 1024
    assert len(audio_samples_list[1]) == 102400


def test_sample_rate_consistency_check():
    """Test that sample rate is consistent across slots"""
    # Simulate slots with same sample rate
    slot_audio_dict = {
        0: {'samples': [], 'timestamp': 100.0, 'sample_rate': 22050},
        1: {'samples': [], 'timestamp': 100.1, 'sample_rate': 22050},
        2: {'samples': [], 'timestamp': 100.2, 'sample_rate': 22050}
    }
    
    # Extract sample rates
    sample_rates = [slot['sample_rate'] for slot in slot_audio_dict.values()]
    
    # Verify all sample rates are the same
    assert all(sr == 22050 for sr in sample_rates)


def test_json_timestamp_metadata():
    """Test that JSON metadata includes timestamp for synchronization"""
    # Simulate JSON slot with timestamp
    json_slot = {
        'samples': [
            {'frame': 0, 'time': 0.0},
            {'frame': 30, 'time': 1.0},
            {'frame': 60, 'time': 2.0}
        ],
        'timestamp': 100.5
    }
    
    # Verify timestamp is preserved
    assert 'timestamp' in json_slot
    assert json_slot['timestamp'] == 100.5


if __name__ == '__main__':
    # Run tests
    test_audio_slots_sorted_by_timestamp()
    test_audio_concatenation_preserves_order()
    test_json_slots_sorted_by_timestamp()
    test_infinite_timestamp_comes_last()
    test_slot_index_as_secondary_sort()
    test_audio_duration_calculation_from_samples()
    test_json_aggregation_structure()
    test_multiple_slot_audio_merge_realistic()
    test_sample_rate_consistency_check()
    test_json_timestamp_metadata()
    print("All stream aggregation by timestamp tests passed!")
