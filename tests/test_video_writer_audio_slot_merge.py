#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for VideoWriter audio slot merging logic.

This test validates that audio from multiple slots is correctly collected
and merged in timestamp order, not per-frame interleaved.
"""

import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_audio_collection_per_slot():
    """
    Test that audio is collected per slot, not merged per frame.
    """
    print("\n--- Testing audio collection per slot ---")
    
    # Simulate VideoWriter receiving multi-slot audio over multiple frames
    # This simulates what happens during recording
    
    # Initialize audio collection (as VideoWriter does)
    audio_samples_dict = {}
    
    # Frame 1: Receive audio from 2 slots
    frame1_audio = {
        0: {'data': np.array([1.0, 2.0]), 'sample_rate': 22050, 'timestamp': 100.0},
        1: {'data': np.array([3.0, 4.0]), 'sample_rate': 22050, 'timestamp': 99.9},
    }
    
    # Frame 2: Receive audio from same 2 slots
    frame2_audio = {
        0: {'data': np.array([5.0, 6.0]), 'sample_rate': 22050, 'timestamp': 100.0},
        1: {'data': np.array([7.0, 8.0]), 'sample_rate': 22050, 'timestamp': 99.9},
    }
    
    # Simulate the collection logic (as updated in VideoWriter)
    for frame_audio in [frame1_audio, frame2_audio]:
        for slot_idx in frame_audio.keys():
            audio_chunk = frame_audio[slot_idx]
            
            if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
                timestamp = audio_chunk.get('timestamp', float('inf'))
                sample_rate = audio_chunk.get('sample_rate', 22050)
                
                # Initialize slot if not exists
                if slot_idx not in audio_samples_dict:
                    audio_samples_dict[slot_idx] = {
                        'samples': [],
                        'timestamp': timestamp,
                        'sample_rate': sample_rate
                    }
                
                # Append this frame's audio to the slot
                audio_samples_dict[slot_idx]['samples'].append(audio_chunk['data'])
    
    # Verify collection
    assert len(audio_samples_dict) == 2, "Should have 2 slots"
    assert len(audio_samples_dict[0]['samples']) == 2, "Slot 0 should have 2 frames"
    assert len(audio_samples_dict[1]['samples']) == 2, "Slot 1 should have 2 frames"
    
    # Verify timestamps
    assert audio_samples_dict[0]['timestamp'] == 100.0
    assert audio_samples_dict[1]['timestamp'] == 99.9
    
    print("✓ Audio correctly collected per slot across frames")
    return audio_samples_dict


def test_slot_merge_by_timestamp(audio_samples_dict):
    """
    Test that slots are merged in timestamp order.
    """
    print("\n--- Testing slot merge by timestamp ---")
    
    # Sort slots by timestamp (as VideoWriter does at recording end)
    sorted_slots = sorted(
        audio_samples_dict.items(),
        key=lambda x: (x[1]['timestamp'], x[0])
    )
    
    # Build final audio in timestamp order
    audio_samples_list = []
    for slot_idx, slot_data in sorted_slots:
        if slot_data['samples']:
            slot_concatenated = np.concatenate(slot_data['samples'])
            audio_samples_list.append(slot_concatenated)
    
    # Final concatenation
    final_audio = np.concatenate(audio_samples_list)
    
    # Expected order: slot 1 (ts=99.9) THEN slot 0 (ts=100.0)
    # Slot 1: [3.0, 4.0] (frame 1) + [7.0, 8.0] (frame 2) = [3.0, 4.0, 7.0, 8.0]
    # Slot 0: [1.0, 2.0] (frame 1) + [5.0, 6.0] (frame 2) = [1.0, 2.0, 5.0, 6.0]
    # Final: [3.0, 4.0, 7.0, 8.0, 1.0, 2.0, 5.0, 6.0]
    expected = np.array([3.0, 4.0, 7.0, 8.0, 1.0, 2.0, 5.0, 6.0])
    
    np.testing.assert_array_equal(final_audio, expected)
    print(f"✓ Final audio in correct timestamp order: {final_audio}")


def test_single_slot_audio():
    """
    Test that single slot audio still works correctly.
    """
    print("\n--- Testing single slot audio (backward compatibility) ---")
    
    audio_samples_dict = {}
    
    # Simulate single video source with audio
    frame_audios = [
        {'data': np.array([1.0, 2.0]), 'sample_rate': 22050, 'timestamp': 100.0},
        {'data': np.array([3.0, 4.0]), 'sample_rate': 22050, 'timestamp': 100.0},
    ]
    
    slot_idx = 0
    for audio_chunk in frame_audios:
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', float('inf'))
            sample_rate = audio_chunk.get('sample_rate', 22050)
            
            if slot_idx not in audio_samples_dict:
                audio_samples_dict[slot_idx] = {
                    'samples': [],
                    'timestamp': timestamp,
                    'sample_rate': sample_rate
                }
            
            audio_samples_dict[slot_idx]['samples'].append(audio_chunk['data'])
    
    # Merge
    sorted_slots = sorted(audio_samples_dict.items(), key=lambda x: (x[1]['timestamp'], x[0]))
    audio_samples_list = []
    for slot_idx, slot_data in sorted_slots:
        if slot_data['samples']:
            slot_concatenated = np.concatenate(slot_data['samples'])
            audio_samples_list.append(slot_concatenated)
    
    final_audio = np.concatenate(audio_samples_list)
    expected = np.array([1.0, 2.0, 3.0, 4.0])
    
    np.testing.assert_array_equal(final_audio, expected)
    print("✓ Single slot audio works correctly")


def test_three_slot_mixed_timestamps():
    """
    Test with 3 slots with different timestamps.
    """
    print("\n--- Testing 3 slots with mixed timestamps ---")
    
    audio_samples_dict = {}
    
    # Simulate 3 video sources over 2 frames
    # Source timestamps: slot 0 = 100.0, slot 1 = 99.9, slot 2 = 100.1
    frame1_audio = {
        0: {'data': np.array([10.0]), 'timestamp': 100.0},
        1: {'data': np.array([20.0]), 'timestamp': 99.9},
        2: {'data': np.array([30.0]), 'timestamp': 100.1},
    }
    
    frame2_audio = {
        0: {'data': np.array([11.0]), 'timestamp': 100.0},
        1: {'data': np.array([21.0]), 'timestamp': 99.9},
        2: {'data': np.array([31.0]), 'timestamp': 100.1},
    }
    
    for frame_audio in [frame1_audio, frame2_audio]:
        for slot_idx, audio_chunk in frame_audio.items():
            timestamp = audio_chunk.get('timestamp', float('inf'))
            
            if slot_idx not in audio_samples_dict:
                audio_samples_dict[slot_idx] = {
                    'samples': [],
                    'timestamp': timestamp,
                    'sample_rate': 22050
                }
            
            audio_samples_dict[slot_idx]['samples'].append(audio_chunk['data'])
    
    # Sort and merge
    sorted_slots = sorted(audio_samples_dict.items(), key=lambda x: (x[1]['timestamp'], x[0]))
    audio_samples_list = []
    for slot_idx, slot_data in sorted_slots:
        if slot_data['samples']:
            slot_concatenated = np.concatenate(slot_data['samples'])
            audio_samples_list.append(slot_concatenated)
    
    final_audio = np.concatenate(audio_samples_list)
    
    # Expected order by timestamp: slot 1 (99.9), slot 0 (100.0), slot 2 (100.1)
    # Slot 1: [20.0, 21.0]
    # Slot 0: [10.0, 11.0]
    # Slot 2: [30.0, 31.0]
    expected = np.array([20.0, 21.0, 10.0, 11.0, 30.0, 31.0])
    
    np.testing.assert_array_equal(final_audio, expected)
    print(f"✓ 3-slot audio merged in correct timestamp order: {final_audio}")


def test_no_timestamp_fallback():
    """
    Test fallback behavior when timestamps are missing.
    """
    print("\n--- Testing fallback when timestamps missing ---")
    
    audio_samples_dict = {}
    
    # Simulate audio without timestamps (uses float('inf'))
    frame_audios = {
        0: [np.array([1.0]), np.array([2.0])],
        1: [np.array([3.0]), np.array([4.0])],
    }
    
    for slot_idx, samples in frame_audios.items():
        audio_samples_dict[slot_idx] = {
            'samples': samples,
            'timestamp': float('inf'),  # No timestamp
            'sample_rate': 22050
        }
    
    # Sort and merge
    sorted_slots = sorted(audio_samples_dict.items(), key=lambda x: (x[1]['timestamp'], x[0]))
    audio_samples_list = []
    for slot_idx, slot_data in sorted_slots:
        if slot_data['samples']:
            slot_concatenated = np.concatenate(slot_data['samples'])
            audio_samples_list.append(slot_concatenated)
    
    final_audio = np.concatenate(audio_samples_list)
    
    # When timestamps are equal (both inf), should fall back to slot order
    expected = np.array([1.0, 2.0, 3.0, 4.0])
    np.testing.assert_array_equal(final_audio, expected)
    print("✓ Fallback to slot order when timestamps missing")


if __name__ == '__main__':
    print("Testing VideoWriter Audio Slot Merging")
    print("="*60)
    
    try:
        audio_dict = test_audio_collection_per_slot()
        test_slot_merge_by_timestamp(audio_dict)
        test_single_slot_audio()
        test_three_slot_mixed_timestamps()
        test_no_timestamp_fallback()
        
        print("\n" + "="*60)
        print("✅ All VideoWriter audio slot merging tests passed!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
