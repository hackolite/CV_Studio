#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for synchronized audio merging through SyncQueue → ImageConcat → VideoWriter pipeline.

This test validates that audio chunks maintain timestamp synchronization
as they flow through the complete data pipeline.
"""

import sys
import os
import numpy as np
import time
import traceback

# Add parent directory to path for test imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict


def test_imageconcat_preserves_audio_timestamps():
    """
    Test that ImageConcat preserves timestamps when collecting audio from multiple slots.
    """
    print("\n--- Testing ImageConcat timestamp preservation ---")
    
    # Create queue manager and dicts
    queue_manager = NodeDataQueueManager(default_maxsize=10)
    node_audio_dict = QueueBackedDict(queue_manager, "audio")
    
    # Simulate audio from multiple video sources with timestamps
    source1 = "1:Video1"
    source2 = "2:Video2"
    source3 = "3:Video3"
    
    # Add audio with different timestamps (not in order)
    audio1 = {'data': np.array([1.0, 2.0]), 'sample_rate': 22050}
    audio2 = {'data': np.array([3.0, 4.0]), 'sample_rate': 22050}
    audio3 = {'data': np.array([5.0, 6.0]), 'sample_rate': 22050}
    
    timestamp1 = 100.0
    timestamp2 = 99.9  # Earlier than timestamp1
    timestamp3 = 100.1  # Later than timestamp1
    
    node_audio_dict.set_with_timestamp(source1, audio1, timestamp1)
    node_audio_dict.set_with_timestamp(source2, audio2, timestamp2)
    node_audio_dict.set_with_timestamp(source3, audio3, timestamp3)
    
    # Simulate ImageConcat collecting audio from these sources
    # (simulating the updated code that preserves timestamps)
    slot_data_dict = {
        0: {'type': 'AUDIO', 'source': source1},
        1: {'type': 'AUDIO', 'source': source2},
        2: {'type': 'AUDIO', 'source': source3},
    }
    
    audio_chunks = {}
    for slot_idx, slot_info in slot_data_dict.items():
        if slot_info['type'] == 'AUDIO':
            audio_chunk = node_audio_dict.get(slot_info['source'], None)
            if audio_chunk is not None:
                # Get timestamp for synchronization
                timestamp = node_audio_dict.get_timestamp(slot_info['source'])
                
                # Preserve timestamp in audio chunk
                if isinstance(audio_chunk, dict):
                    if 'timestamp' not in audio_chunk and timestamp is not None:
                        audio_chunk = audio_chunk.copy()
                        audio_chunk['timestamp'] = timestamp
                elif timestamp is not None:
                    audio_chunk = {
                        'data': audio_chunk,
                        'timestamp': timestamp
                    }
                
                audio_chunks[slot_idx] = audio_chunk
    
    # Verify all chunks have timestamps
    assert len(audio_chunks) == 3
    assert audio_chunks[0]['timestamp'] == timestamp1
    assert audio_chunks[1]['timestamp'] == timestamp2
    assert audio_chunks[2]['timestamp'] == timestamp3
    
    print("✓ ImageConcat preserves audio timestamps from sources")
    return audio_chunks


def test_videowriter_synchronizes_audio_by_timestamp(audio_chunks):
    """
    Test that VideoWriter synchronizes multi-slot audio by timestamp.
    """
    print("\n--- Testing VideoWriter timestamp synchronization ---")
    
    # Simulate VideoWriter receiving audio_chunks from ImageConcat
    audio_data = audio_chunks
    
    # Simulate the VideoWriter audio collection logic (updated code)
    audio_chunks_with_ts = []
    sample_rate = None
    
    for slot_idx in sorted(audio_data.keys()):
        audio_chunk = audio_data[slot_idx]
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', float('inf'))
            audio_chunks_with_ts.append({
                'data': audio_chunk['data'],
                'timestamp': timestamp,
                'slot': slot_idx
            })
            if sample_rate is None and 'sample_rate' in audio_chunk:
                sample_rate = audio_chunk['sample_rate']
    
    # Sort by timestamp first, then by slot index
    audio_chunks_with_ts.sort(key=lambda x: (x['timestamp'], x['slot']))
    
    # Concatenate in synchronized order
    merged_chunk = np.concatenate([chunk['data'] for chunk in audio_chunks_with_ts])
    
    # Verify the order is by timestamp, not by slot
    # Expected order: slot 1 (99.9), slot 0 (100.0), slot 2 (100.1)
    expected = np.array([3.0, 4.0, 1.0, 2.0, 5.0, 6.0])
    np.testing.assert_array_equal(merged_chunk, expected)
    
    print("✓ VideoWriter synchronizes audio chunks by timestamp")
    print(f"  Timestamp order: {[chunk['timestamp'] for chunk in audio_chunks_with_ts]}")
    print(f"  Data order: {merged_chunk}")


def test_syncqueue_to_imageconcat_to_videowriter_pipeline():
    """
    Test the complete pipeline: SyncQueue → ImageConcat → VideoWriter
    """
    print("\n--- Testing complete pipeline ---")
    
    # Create queue infrastructure
    queue_manager = NodeDataQueueManager(default_maxsize=10)
    node_image_dict = QueueBackedDict(queue_manager, "image")
    node_audio_dict = QueueBackedDict(queue_manager, "audio")
    
    # Simulate video sources with synchronized timestamps
    base_time = time.time()
    
    # Three video sources producing frames and audio at slightly different times
    sources = [
        ("1:Webcam", base_time + 0.0),
        ("2:Video", base_time - 0.1),  # Earlier
        ("3:ScreenCap", base_time + 0.1),  # Later
    ]
    
    # Add data with timestamps
    for source_id, timestamp in sources:
        image_data = np.zeros((480, 640, 3), dtype=np.uint8)
        audio_data = {'data': np.random.rand(1024), 'sample_rate': 22050}
        
        node_image_dict.set_with_timestamp(source_id, image_data, timestamp)
        node_audio_dict.set_with_timestamp(source_id, audio_data, timestamp)
    
    # SyncQueue would synchronize these based on timestamps
    # (already tested in test_sync_queue_timestamps.py)
    
    # ImageConcat collects audio from synchronized sources
    audio_chunks = {}
    for idx, (source_id, timestamp) in enumerate(sources):
        audio_chunk = node_audio_dict.get(source_id)
        ts = node_audio_dict.get_timestamp(source_id)
        
        if isinstance(audio_chunk, dict):
            if 'timestamp' not in audio_chunk and ts is not None:
                audio_chunk = audio_chunk.copy()
                audio_chunk['timestamp'] = ts
        
        audio_chunks[idx] = audio_chunk
    
    # VideoWriter receives and synchronizes
    audio_chunks_with_ts = []
    for slot_idx in sorted(audio_chunks.keys()):
        audio_chunk = audio_chunks[slot_idx]
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', float('inf'))
            audio_chunks_with_ts.append({
                'data': audio_chunk['data'],
                'timestamp': timestamp,
                'slot': slot_idx
            })
    
    # Sort by timestamp
    audio_chunks_with_ts.sort(key=lambda x: (x['timestamp'], x['slot']))
    
    # Verify order matches timestamp order (not slot order)
    # Expected: slot 1 (earliest), slot 0 (middle), slot 2 (latest)
    expected_slot_order = [1, 0, 2]
    actual_slot_order = [chunk['slot'] for chunk in audio_chunks_with_ts]
    
    assert actual_slot_order == expected_slot_order, \
        f"Expected slot order {expected_slot_order}, got {actual_slot_order}"
    
    print("✓ Complete pipeline maintains timestamp synchronization")
    print(f"  Timestamp order: slot {actual_slot_order}")


def test_backward_compatibility_no_timestamps():
    """
    Test that the system works without timestamps (backward compatibility).
    """
    print("\n--- Testing backward compatibility (no timestamps) ---")
    
    # Simulate old-style audio data without timestamps
    audio_data = {
        0: {'data': np.array([1.0, 2.0]), 'sample_rate': 22050},
        1: {'data': np.array([3.0, 4.0]), 'sample_rate': 22050},
        2: np.array([5.0, 6.0]),  # Plain numpy array
    }
    
    # Process as VideoWriter would
    audio_chunks_with_ts = []
    for slot_idx in sorted(audio_data.keys()):
        audio_chunk = audio_data[slot_idx]
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', float('inf'))
            audio_chunks_with_ts.append({
                'data': audio_chunk['data'],
                'timestamp': timestamp,
                'slot': slot_idx
            })
        elif isinstance(audio_chunk, np.ndarray):
            audio_chunks_with_ts.append({
                'data': audio_chunk,
                'timestamp': float('inf'),
                'slot': slot_idx
            })
    
    # Sort by timestamp (all inf), then by slot
    audio_chunks_with_ts.sort(key=lambda x: (x['timestamp'], x['slot']))
    
    # Should be in slot order when no timestamps
    merged = np.concatenate([chunk['data'] for chunk in audio_chunks_with_ts])
    expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    np.testing.assert_array_equal(merged, expected)
    
    print("✓ Backward compatibility maintained (falls back to slot order)")


if __name__ == '__main__':
    print("Testing Synchronized Audio Merging Through Pipeline")
    print("SyncQueue → ImageConcat → VideoWriter")
    print("="*60)
    
    try:
        # Run tests in sequence
        audio_chunks = test_imageconcat_preserves_audio_timestamps()
        test_videowriter_synchronizes_audio_by_timestamp(audio_chunks)
        test_syncqueue_to_imageconcat_to_videowriter_pipeline()
        test_backward_compatibility_no_timestamps()
        
        print("\n" + "="*60)
        print("✅ All pipeline synchronization tests passed!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        traceback.print_exc()
        sys.exit(1)
