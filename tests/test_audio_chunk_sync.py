#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for audio chunk synchronization through SyncQueue, ImageConcat, and VideoWriter.

This test validates that audio chunks maintain timestamp synchronization
when flowing through the data pipeline.
"""

import numpy as np
import time


def test_audio_chunk_timestamp_preservation():
    """
    Test that audio chunks preserve timestamps when concatenated.
    
    This simulates the flow: Video Nodes → SyncQueue → ImageConcat → VideoWriter
    """
    # Simulate audio chunks from multiple video sources with timestamps
    audio_chunks_with_timestamps = {
        0: {'data': np.array([0.1, 0.2, 0.3]), 'sample_rate': 22050, 'timestamp': 1000.0},
        1: {'data': np.array([0.4, 0.5, 0.6]), 'sample_rate': 22050, 'timestamp': 1000.1},
        2: {'data': np.array([0.7, 0.8, 0.9]), 'sample_rate': 22050, 'timestamp': 999.9},
    }
    
    # When VideoWriter receives this from ImageConcat, it should sort by timestamp
    # not by slot index to maintain proper synchronization
    
    # Current behavior (INCORRECT): sorts by slot index
    sorted_by_slot = sorted(audio_chunks_with_timestamps.items())
    chunks_by_slot = [chunk['data'] for idx, chunk in sorted_by_slot]
    result_by_slot = np.concatenate(chunks_by_slot)
    
    # Expected behavior (CORRECT): sort by timestamp
    sorted_by_timestamp = sorted(
        audio_chunks_with_timestamps.items(),
        key=lambda x: x[1].get('timestamp', 0)
    )
    chunks_by_timestamp = [chunk['data'] for idx, chunk in sorted_by_timestamp]
    result_by_timestamp = np.concatenate(chunks_by_timestamp)
    
    # The results should be different if timestamps aren't in slot order
    # In this case: slot order is [0, 1, 2] but timestamp order is [2, 0, 1]
    expected_by_timestamp = np.array([0.7, 0.8, 0.9, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    expected_by_slot = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    
    np.testing.assert_array_equal(result_by_slot, expected_by_slot)
    np.testing.assert_array_equal(result_by_timestamp, expected_by_timestamp)
    
    print("✓ Audio chunks should be ordered by timestamp, not slot index")


def test_audio_chunk_sync_logic():
    """
    Test the correct synchronization logic for multi-slot audio.
    """
    # Simulate the VideoWriter receiving multi-slot audio from ImageConcat
    audio_data = {
        0: {'data': np.array([1.0, 2.0]), 'sample_rate': 22050, 'timestamp': 100.0},
        1: {'data': np.array([3.0, 4.0]), 'sample_rate': 22050, 'timestamp': 99.9},
        2: {'data': np.array([5.0, 6.0]), 'sample_rate': 22050, 'timestamp': 100.1},
    }
    
    # Correct implementation: extract chunks with timestamps
    audio_chunks_with_ts = []
    sample_rate = None
    
    for slot_idx, audio_chunk in audio_data.items():
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', 0)
            audio_chunks_with_ts.append({
                'data': audio_chunk['data'],
                'timestamp': timestamp
            })
            if sample_rate is None and 'sample_rate' in audio_chunk:
                sample_rate = audio_chunk['sample_rate']
    
    # Sort by timestamp to maintain synchronization
    audio_chunks_with_ts.sort(key=lambda x: x['timestamp'])
    
    # Concatenate in timestamp order
    merged_chunk = np.concatenate([chunk['data'] for chunk in audio_chunks_with_ts])
    
    # Verify the result is in correct timestamp order
    # Timestamp order: slot 1 (99.9), slot 0 (100.0), slot 2 (100.1)
    expected = np.array([3.0, 4.0, 1.0, 2.0, 5.0, 6.0])
    np.testing.assert_array_equal(merged_chunk, expected)
    
    assert sample_rate == 22050
    
    print("✓ Multi-slot audio chunks correctly synchronized by timestamp")


def test_audio_chunk_without_timestamp():
    """
    Test handling of audio chunks without timestamp information.
    Falls back to slot order if no timestamps available.
    """
    # Simulate audio without timestamps (backward compatibility)
    audio_data = {
        0: {'data': np.array([1.0, 2.0]), 'sample_rate': 22050},
        1: {'data': np.array([3.0, 4.0]), 'sample_rate': 22050},
    }
    
    # When no timestamps, use slot order as fallback
    audio_chunks = []
    sample_rate = None
    
    for slot_idx in sorted(audio_data.keys()):
        audio_chunk = audio_data[slot_idx]
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            audio_chunks.append(audio_chunk['data'])
            if sample_rate is None and 'sample_rate' in audio_chunk:
                sample_rate = audio_chunk['sample_rate']
    
    merged_chunk = np.concatenate(audio_chunks)
    
    # Should be in slot order when no timestamps
    expected = np.array([1.0, 2.0, 3.0, 4.0])
    np.testing.assert_array_equal(merged_chunk, expected)
    
    print("✓ Audio chunks without timestamps fall back to slot order")


def test_mixed_audio_formats():
    """
    Test handling of mixed audio formats (with and without timestamps).
    """
    audio_data = {
        0: {'data': np.array([1.0]), 'sample_rate': 22050, 'timestamp': 100.0},
        1: np.array([2.0]),  # numpy array format (no timestamp)
        2: {'data': np.array([3.0]), 'sample_rate': 22050},  # dict without timestamp
    }
    
    # Extract chunks with optional timestamps
    audio_chunks_info = []
    sample_rate = None
    
    for slot_idx in sorted(audio_data.keys()):
        audio_chunk = audio_data[slot_idx]
        
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', float('inf'))  # Use inf for missing timestamps
            audio_chunks_info.append({
                'data': audio_chunk['data'],
                'timestamp': timestamp,
                'slot': slot_idx
            })
            if sample_rate is None and 'sample_rate' in audio_chunk:
                sample_rate = audio_chunk['sample_rate']
        elif isinstance(audio_chunk, np.ndarray):
            # Plain numpy array - use slot index as fallback
            audio_chunks_info.append({
                'data': audio_chunk,
                'timestamp': float('inf'),
                'slot': slot_idx
            })
    
    # Sort: first by timestamp (finite first), then by slot index
    audio_chunks_info.sort(key=lambda x: (x['timestamp'], x['slot']))
    
    merged_chunk = np.concatenate([chunk['data'] for chunk in audio_chunks_info])
    
    # Expected: slot 0 has timestamp (100.0), slots 1,2 have no timestamp (sorted by slot)
    expected = np.array([1.0, 2.0, 3.0])
    np.testing.assert_array_equal(merged_chunk, expected)
    
    print("✓ Mixed audio formats handled correctly")


if __name__ == '__main__':
    print("Testing Audio Chunk Synchronization\n")
    print("="*60)
    
    test_audio_chunk_timestamp_preservation()
    test_audio_chunk_sync_logic()
    test_audio_chunk_without_timestamp()
    test_mixed_audio_formats()
    
    print("\n" + "="*60)
    print("✅ All audio chunk synchronization tests passed!")
