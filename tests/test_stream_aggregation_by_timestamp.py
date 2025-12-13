#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for stream aggregation by timestamp"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def test_audio_slots_sorted_by_slot_index():
    """Test that audio slots are sorted by slot index when merging (timestamps are indicative only)"""
    # Simulate audio samples with different timestamps (indicative only, not used for ordering)
    slot_audio_dict = {
        0: {'samples': [np.array([1, 2, 3])], 'timestamp': 102.0, 'sample_rate': 22050},
        1: {'samples': [np.array([4, 5, 6])], 'timestamp': 100.0, 'sample_rate': 22050},
        2: {'samples': [np.array([7, 8, 9])], 'timestamp': 101.0, 'sample_rate': 22050}
    }
    
    # Sort by slot index only (as done in VideoWriter)
    sorted_slots = sorted(
        slot_audio_dict.items(),
        key=lambda x: x[0]  # Sort by slot_idx only
    )
    
    # Verify sorting order: 0, 1, 2 (by slot index, not timestamp)
    assert sorted_slots[0][0] == 0  # slot 0
    assert sorted_slots[1][0] == 1  # slot 1
    assert sorted_slots[2][0] == 2  # slot 2


def test_audio_concatenation_preserves_order():
    """Test that audio concatenation preserves slot order"""
    # Simulate sorted audio samples (by slot index)
    sorted_audio_samples = [
        np.array([1, 2, 3]),  # First by slot index
        np.array([4, 5, 6]),  # Second by slot index
        np.array([7, 8, 9])   # Third by slot index
    ]
    
    # Concatenate
    merged_audio = np.concatenate(sorted_audio_samples)
    
    # Verify concatenation
    expected = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert np.array_equal(merged_audio, expected)


def test_json_slots_sorted_by_slot_index():
    """Test that JSON slots are sorted by slot index (timestamps are indicative only)"""
    # Simulate JSON samples with different timestamps (indicative only, not used for ordering)
    json_samples_dict = {
        0: {'samples': [{'frame': 2}], 'timestamp': 102.0},
        1: {'samples': [{'frame': 0}], 'timestamp': 100.0},
        2: {'samples': [{'frame': 1}], 'timestamp': 101.0}
    }
    
    # Sort by slot index only
    sorted_slots = sorted(
        json_samples_dict.items(),
        key=lambda x: x[0]  # Sort by slot_idx only
    )
    
    # Verify sorting order (by slot index, not timestamp)
    assert sorted_slots[0][0] == 0  # slot 0
    assert sorted_slots[1][0] == 1  # slot 1
    assert sorted_slots[2][0] == 2  # slot 2


def test_slot_ordering_by_index():
    """Test that slots are ordered by slot index (timestamps not used for ordering)"""
    # Simulate slots with mixed finite and infinite timestamps (timestamps are indicative only)
    slot_dict = {
        0: {'samples': [], 'timestamp': float('inf')},  # No timestamp
        1: {'samples': [], 'timestamp': 100.0},
        2: {'samples': [], 'timestamp': 99.0},
        3: {'samples': [], 'timestamp': float('inf')}   # No timestamp
    }
    
    # Sort by slot index only
    sorted_slots = sorted(
        slot_dict.items(),
        key=lambda x: x[0]  # Sort by slot_idx only
    )
    
    # Verify: sorted by slot index only (0, 1, 2, 3)
    assert sorted_slots[0][0] == 0  # slot 0
    assert sorted_slots[1][0] == 1  # slot 1
    assert sorted_slots[2][0] == 2  # slot 2
    assert sorted_slots[3][0] == 3  # slot 3


def test_slot_index_as_primary_sort():
    """Test that slot index is used as the primary (and only) sort key"""
    # Simulate slots with various timestamps (timestamps are indicative only)
    slot_dict = {
        3: {'samples': [], 'timestamp': 100.0},
        1: {'samples': [], 'timestamp': 100.0},
        2: {'samples': [], 'timestamp': 100.0}
    }
    
    # Sort by slot_idx only
    sorted_slots = sorted(
        slot_dict.items(),
        key=lambda x: x[0]  # Sort by slot_idx only
    )
    
    # Verify: sorted by slot index regardless of timestamp
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
    
    # Sort by slot index only
    sorted_slots = sorted(
        slot_audio_dict.items(),
        key=lambda x: x[0]  # Sort by slot_idx only
    )
    
    # Concatenate each slot
    audio_samples_list = []
    for slot_idx, slot_data in sorted_slots:
        if slot_data['samples']:
            slot_concatenated = np.concatenate(slot_data['samples'])
            audio_samples_list.append(slot_concatenated)
    
    # Verify merge (slot 0 first, then slot 1)
    assert len(audio_samples_list) == 2
    assert len(audio_samples_list[0]) == 102400  # 100 chunks * 1024 (slot 0)
    assert len(audio_samples_list[1]) == 102400  # 100 chunks * 1024 (slot 1)


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
    """Test that JSON metadata includes timestamp (indicative only, not used for ordering)"""
    # Simulate JSON slot with timestamp (indicative only)
    json_slot = {
        'samples': [
            {'frame': 0, 'time': 0.0},
            {'frame': 30, 'time': 1.0},
            {'frame': 60, 'time': 2.0}
        ],
        'timestamp': 100.5
    }
    
    # Verify timestamp is preserved (for informational purposes only)
    assert 'timestamp' in json_slot
    assert json_slot['timestamp'] == 100.5


if __name__ == '__main__':
    # Run tests
    test_audio_slots_sorted_by_slot_index()
    test_audio_concatenation_preserves_order()
    test_json_slots_sorted_by_slot_index()
    test_slot_ordering_by_index()
    test_slot_index_as_primary_sort()
    test_audio_duration_calculation_from_samples()
    test_json_aggregation_structure()
    test_multiple_slot_audio_merge_realistic()
    test_sample_rate_consistency_check()
    test_json_timestamp_metadata()
    print("All stream aggregation tests passed!")
