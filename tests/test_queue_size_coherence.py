#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify queue size coherence with SyncQueue, VideoWriter, and ImageConcat.

This test ensures that the default queue size is sufficient for:
1. SyncQueue synchronization with maximum retention time
2. VideoWriter multi-slot audio collection
3. ImageConcat multi-slot frame concatenation
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the default queue size constant
from node.timestamped_queue import DEFAULT_QUEUE_SIZE


def test_queue_size_calculation():
    """Test that queue size is calculated correctly for worst-case scenarios"""
    
    # SyncQueue parameters (from node_sync_queue.py)
    MAX_RETENTION_TIME = 10.0  # seconds (max_value in UI)
    BUFFER_OVERHEAD = 1.0  # seconds (from max_buffer_age calculation)
    MIN_BUFFER_TIME = 2.0  # seconds (minimum in max_buffer_age)
    
    # Calculate maximum buffer age (from node_sync_queue.py line 232)
    max_buffer_age = max(MAX_RETENTION_TIME + BUFFER_OVERHEAD, MIN_BUFFER_TIME)
    
    # Video parameters - use 60 FPS as worst case for high frame rate
    HIGH_FPS = 60
    
    # Calculate minimum frames needed
    min_frames_needed = int(max_buffer_age * HIGH_FPS)
    
    # Add safety margin (20%)
    SAFETY_MARGIN = 1.2
    recommended_size = int(min_frames_needed * SAFETY_MARGIN)
    
    print(f"Max buffer age: {max_buffer_age}s")
    print(f"At {HIGH_FPS} FPS: {min_frames_needed} frames minimum")
    print(f"With 20% margin: {recommended_size} frames")
    
    # Verify that the default size is sufficient
    assert DEFAULT_QUEUE_SIZE >= recommended_size, \
        f"Queue size {DEFAULT_QUEUE_SIZE} is insufficient! Need at least {recommended_size} frames"
    
    assert DEFAULT_QUEUE_SIZE >= min_frames_needed, \
        f"Queue size {DEFAULT_QUEUE_SIZE} is insufficient! Need at least {min_frames_needed} frames (without margin)"
    
    print(f"✓ Queue size {DEFAULT_QUEUE_SIZE} is sufficient (minimum needed: {recommended_size})")
    return True


def test_syncqueue_retention_coherence():
    """Verify queue size supports SyncQueue's maximum retention time"""
    
    # SyncQueue max retention from node_sync_queue.py line 72
    SYNCQUEUE_MAX_RETENTION = 10.0  # seconds
    BUFFER_OVERHEAD = 1.0  # seconds
    
    # Typical video FPS
    TYPICAL_FPS = 30
    
    # Calculate frames needed for max retention
    frames_for_retention = int((SYNCQUEUE_MAX_RETENTION + BUFFER_OVERHEAD) * TYPICAL_FPS)
    
    assert DEFAULT_QUEUE_SIZE >= frames_for_retention, \
        f"Queue size {DEFAULT_QUEUE_SIZE} insufficient for SyncQueue retention! " \
        f"Need {frames_for_retention} frames at {TYPICAL_FPS} FPS"
    
    print(f"✓ Queue size {DEFAULT_QUEUE_SIZE} supports SyncQueue retention time")
    print(f"  (Retention needs {frames_for_retention} frames at {TYPICAL_FPS} FPS)")
    return True


def test_multi_slot_support():
    """Verify queue size supports multi-slot operations in VideoWriter and ImageConcat"""
    
    # Maximum slots from node_sync_queue.py and node_image_concat.py
    MAX_SLOTS = 10
    
    # Typical processing delay per slot (assume worst case)
    # If each slot takes 100ms to process, 10 slots = 1 second delay
    PROCESSING_DELAY = 1.0  # seconds
    TYPICAL_FPS = 30
    
    # Frames needed to buffer during multi-slot processing
    frames_during_processing = int(PROCESSING_DELAY * TYPICAL_FPS)
    
    # Add buffer for SyncQueue retention
    SYNCQUEUE_RETENTION = 11.0  # max 10s + 1s overhead
    total_frames_needed = int((SYNCQUEUE_RETENTION + PROCESSING_DELAY) * TYPICAL_FPS)
    
    assert DEFAULT_QUEUE_SIZE >= total_frames_needed, \
        f"Queue size {DEFAULT_QUEUE_SIZE} insufficient for multi-slot processing! " \
        f"Need {total_frames_needed} frames"
    
    print(f"✓ Queue size {DEFAULT_QUEUE_SIZE} supports {MAX_SLOTS} slots with processing")
    print(f"  (Processing needs {total_frames_needed} frames)")
    return True


def test_memory_impact():
    """Verify that the increased queue size has acceptable memory impact"""
    
    # Estimate memory per frame (rough estimates)
    # These are upper bounds - actual sizes may be smaller
    IMAGE_SIZE_MB = 1.0  # ~1 MB for 1920x1080 RGB image
    AUDIO_SIZE_KB = 10.0  # ~10 KB per audio chunk
    JSON_SIZE_KB = 1.0   # ~1 KB per JSON metadata
    
    # Calculate total memory per queue (in MB)
    image_queue_mb = DEFAULT_QUEUE_SIZE * IMAGE_SIZE_MB
    audio_queue_mb = DEFAULT_QUEUE_SIZE * (AUDIO_SIZE_KB / 1024)
    json_queue_mb = DEFAULT_QUEUE_SIZE * (JSON_SIZE_KB / 1024)
    
    total_per_node_mb = image_queue_mb + audio_queue_mb + json_queue_mb
    
    # Assume up to 10 nodes with queues active simultaneously
    MAX_ACTIVE_NODES = 10
    total_system_mb = total_per_node_mb * MAX_ACTIVE_NODES
    
    # Memory threshold - should be reasonable for modern systems (< 10 GB)
    MEMORY_THRESHOLD_MB = 10 * 1024  # 10 GB
    
    print(f"Memory impact per node: ~{int(total_per_node_mb)} MB")
    print(f"  - Image queue: ~{int(image_queue_mb)} MB")
    print(f"  - Audio queue: ~{int(audio_queue_mb)} MB")
    print(f"  - JSON queue: ~{int(json_queue_mb)} MB")
    print(f"Total for {MAX_ACTIVE_NODES} nodes: ~{int(total_system_mb)} MB ({int(total_system_mb/1024)} GB)")
    
    assert total_system_mb < MEMORY_THRESHOLD_MB, \
        f"Memory impact too high! {total_system_mb} MB exceeds threshold {MEMORY_THRESHOLD_MB} MB"
    
    print(f"✓ Memory impact acceptable (< {MEMORY_THRESHOLD_MB/1024} GB)")
    return True


if __name__ == '__main__':
    print("Running Queue Size Coherence Tests\n")
    print("=" * 70)
    
    tests = [
        ("Queue size calculation", test_queue_size_calculation),
        ("SyncQueue retention coherence", test_syncqueue_retention_coherence),
        ("Multi-slot support", test_multi_slot_support),
        ("Memory impact", test_memory_impact),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 70)
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except AssertionError as e:
            failed += 1
            print(f"✗ {test_name} FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 70)
    print(f"Tests Passed: {passed}/{len(tests)}")
    print(f"Tests Failed: {failed}/{len(tests)}")
    print("=" * 70)
    
    sys.exit(0 if failed == 0 else 1)
