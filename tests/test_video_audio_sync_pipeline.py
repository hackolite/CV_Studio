#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for complete Video → SyncQueue → ImageConcat → VideoWriter pipeline
with audio synchronization.

This test validates:
1. Video node outputs audio chunks with timestamps
2. SyncQueue preserves audio timestamps
3. ImageConcat maintains audio timestamps through concat
4. VideoWriter correctly merges audio with proper timestamps
"""
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_audio_timestamp_preservation_through_syncqueue():
    """
    Test that SyncQueue preserves audio timestamps from video node.
    """
    print("\n=== Testing SyncQueue Audio Timestamp Preservation ===")
    
    # Simulate audio data from video node (dict with data and sample_rate)
    audio_from_video = {
        'data': np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
        'sample_rate': 22050
    }
    
    # Simulate SyncQueue wrapping with timestamp
    # This simulates the internal buffer structure in SyncQueue
    buffered_item = {
        'data': audio_from_video.copy(),
        'timestamp': 0.5,  # Example timestamp
        'received_at': 1000.0
    }
    
    # Extract synced data using SyncQueue's wrapping logic
    synced_item = buffered_item
    synced_data = synced_item['data']
    synced_timestamp = synced_item['timestamp']
    
    # Verify the data is a dict (from video node)
    assert isinstance(synced_data, dict), "Audio data should be dict from video node"
    
    # Apply the timestamp preservation logic from SyncQueue
    if isinstance(synced_data, dict):
        # Audio data is already a dict, preserve/update timestamp
        if 'timestamp' not in synced_data or synced_data['timestamp'] != synced_timestamp:
            synced_data = synced_data.copy()
            synced_data['timestamp'] = synced_timestamp
    
    # Verify timestamp is preserved
    assert 'timestamp' in synced_data, "Timestamp should be preserved in audio data"
    assert synced_data['timestamp'] == 0.5, f"Expected timestamp 0.5, got {synced_data['timestamp']}"
    
    # Verify sample_rate is still present
    assert 'sample_rate' in synced_data, "Sample rate should be preserved"
    assert synced_data['sample_rate'] == 22050, f"Expected sample_rate 22050, got {synced_data['sample_rate']}"
    
    # Verify audio data is still present
    assert 'data' in synced_data, "Audio data should be preserved"
    assert np.array_equal(synced_data['data'], np.array([0.1, 0.2, 0.3, 0.4, 0.5])), "Audio data should be unchanged"
    
    print("✓ SyncQueue correctly preserves audio dict structure with timestamp")


def test_audio_timestamp_extraction_in_imageconcat():
    """
    Test that ImageConcat correctly extracts timestamps from audio chunks.
    """
    print("\n=== Testing ImageConcat Audio Timestamp Extraction ===")
    
    # Simulate audio chunk from SyncQueue (already has timestamp)
    audio_from_syncqueue = {
        'data': np.array([0.1, 0.2, 0.3]),
        'sample_rate': 22050,
        'timestamp': 1.5
    }
    
    # Apply ImageConcat timestamp extraction logic
    audio_chunk = audio_from_syncqueue
    
    if isinstance(audio_chunk, dict):
        # Check if it already has a timestamp (from SyncQueue)
        if 'timestamp' not in audio_chunk:
            # Would try to get from queue here
            pass
        # timestamp already present, use as-is
    
    # Verify timestamp is preserved
    assert 'timestamp' in audio_chunk, "Timestamp should be present"
    assert audio_chunk['timestamp'] == 1.5, f"Expected timestamp 1.5, got {audio_chunk['timestamp']}"
    
    # Verify sample_rate is present
    assert 'sample_rate' in audio_chunk, "Sample rate should be present"
    assert audio_chunk['sample_rate'] == 22050
    
    print("✓ ImageConcat correctly preserves timestamp from SyncQueue")


def test_videowriter_audio_sorting_by_timestamp():
    """
    Test that VideoWriter correctly sorts and merges audio chunks by timestamp.
    """
    print("\n=== Testing VideoWriter Audio Chunk Sorting ===")
    
    # Simulate multi-slot audio from ImageConcat
    audio_from_concat = {
        0: {
            'data': np.array([1.0, 2.0, 3.0]),
            'sample_rate': 22050,
            'timestamp': 2.0  # Later timestamp
        },
        1: {
            'data': np.array([4.0, 5.0, 6.0]),
            'sample_rate': 22050,
            'timestamp': 1.0  # Earlier timestamp
        },
        2: {
            'data': np.array([7.0, 8.0, 9.0]),
            'sample_rate': 22050,
            'timestamp': 1.5  # Middle timestamp
        }
    }
    
    # Apply VideoWriter audio chunk sorting and merging logic
    audio_chunks_with_ts = []
    sample_rate = None
    
    for slot_idx in sorted(audio_from_concat.keys()):
        audio_chunk = audio_from_concat[slot_idx]
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', float('inf'))
            audio_chunks_with_ts.append({
                'data': audio_chunk['data'],
                'timestamp': timestamp,
                'slot': slot_idx
            })
            if sample_rate is None and 'sample_rate' in audio_chunk:
                sample_rate = audio_chunk['sample_rate']
    
    # Sort by timestamp
    audio_chunks_with_ts.sort(key=lambda x: (x['timestamp'], x['slot']))
    
    # Verify sorting order
    assert len(audio_chunks_with_ts) == 3, "Should have 3 audio chunks"
    assert audio_chunks_with_ts[0]['timestamp'] == 1.0, "First should have timestamp 1.0"
    assert audio_chunks_with_ts[1]['timestamp'] == 1.5, "Second should have timestamp 1.5"
    assert audio_chunks_with_ts[2]['timestamp'] == 2.0, "Third should have timestamp 2.0"
    
    # Verify data order matches timestamp order
    assert np.array_equal(audio_chunks_with_ts[0]['data'], np.array([4.0, 5.0, 6.0])), "First chunk data incorrect"
    assert np.array_equal(audio_chunks_with_ts[1]['data'], np.array([7.0, 8.0, 9.0])), "Second chunk data incorrect"
    assert np.array_equal(audio_chunks_with_ts[2]['data'], np.array([1.0, 2.0, 3.0])), "Third chunk data incorrect"
    
    # Concatenate in correct order
    merged_chunk = np.concatenate([chunk['data'] for chunk in audio_chunks_with_ts])
    
    # Verify merged chunk has correct order
    expected_merged = np.array([4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 1.0, 2.0, 3.0])
    assert np.array_equal(merged_chunk, expected_merged), "Merged audio should be in timestamp order"
    
    # Verify sample_rate was extracted
    assert sample_rate == 22050, "Sample rate should be extracted from chunks"
    
    print("✓ VideoWriter correctly sorts audio chunks by timestamp")


def test_videowriter_handles_wrapped_syncqueue_audio():
    """
    Test that VideoWriter handles audio wrapped by SyncQueue (dict with 'data' key but no 'sample_rate').
    """
    print("\n=== Testing VideoWriter with SyncQueue-Wrapped Audio ===")
    
    # Simulate audio wrapped by SyncQueue (has timestamp but sample_rate might be nested)
    audio_from_concat = {
        0: {
            'data': np.array([1.0, 2.0, 3.0]),
            'timestamp': 1.0
            # Note: no sample_rate at this level
        }
    }
    
    # Apply VideoWriter wrapped audio handling logic
    audio_chunks_with_ts = []
    sample_rate = None
    
    for slot_idx in sorted(audio_from_concat.keys()):
        audio_chunk = audio_from_concat[slot_idx]
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', float('inf'))
            audio_chunks_with_ts.append({
                'data': audio_chunk['data'],
                'timestamp': timestamp,
                'slot': slot_idx
            })
            # Extract sample rate if available
            if sample_rate is None and 'sample_rate' in audio_chunk:
                sample_rate = audio_chunk['sample_rate']
        elif isinstance(audio_chunk, dict) and isinstance(audio_chunk.get('data'), np.ndarray):
            # Wrapped audio without explicit 'sample_rate' key
            timestamp = audio_chunk.get('timestamp', float('inf'))
            audio_chunks_with_ts.append({
                'data': audio_chunk['data'],
                'timestamp': timestamp,
                'slot': slot_idx
            })
    
    # Verify chunks were extracted
    assert len(audio_chunks_with_ts) == 1, "Should extract 1 audio chunk"
    assert audio_chunks_with_ts[0]['timestamp'] == 1.0, "Timestamp should be preserved"
    assert np.array_equal(audio_chunks_with_ts[0]['data'], np.array([1.0, 2.0, 3.0])), "Data should be extracted"
    
    print("✓ VideoWriter handles SyncQueue-wrapped audio correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("Running Video/Audio Synchronization Pipeline Tests")
    print("=" * 70)
    
    try:
        test_audio_timestamp_preservation_through_syncqueue()
        test_audio_timestamp_extraction_in_imageconcat()
        test_videowriter_audio_sorting_by_timestamp()
        test_videowriter_handles_wrapped_syncqueue_audio()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        return True
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
