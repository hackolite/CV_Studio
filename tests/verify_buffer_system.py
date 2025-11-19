#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verification script for the timestamped buffer system.

This script demonstrates that:
1. Buffer holds 10 values in memory
2. Each element has a timestamp
3. Values can be synchronized using timestamps
4. Reading doesn't consume items (not FIFO)
"""

import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict


def print_separator(title=""):
    """Print a nice separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"{'='*60}")


def test_buffer_holds_10_values():
    """Test 1: Verify buffer holds exactly 10 values."""
    print_separator("TEST 1: Buffer holds 10 values maximum")
    
    manager = NodeDataQueueManager()
    image_dict = QueueBackedDict(manager, "image")
    
    # Add 15 items
    print("Adding 15 items to the buffer...")
    for i in range(15):
        image_dict["1:Camera"] = f"frame_{i}"
        time.sleep(0.001)
    
    # Check buffer size
    info = image_dict.get_queue_info("1:Camera")
    print(f"✓ Buffer size: {info['size']} (expected: 10)")
    assert info['size'] == 10, f"Expected 10 items, got {info['size']}"
    
    # Verify we have the last 10 items
    queue = manager.get_queue("1:Camera", "image")
    all_items = queue.get_all()
    
    print(f"✓ Buffered items: {[item.data for item in all_items]}")
    print(f"✓ Oldest item: {all_items[0].data} (expected: frame_5)")
    print(f"✓ Latest item: {all_items[-1].data} (expected: frame_14)")
    
    assert all_items[0].data == "frame_5", "Oldest item should be frame_5"
    assert all_items[-1].data == "frame_14", "Latest item should be frame_14"
    
    print("\n✅ TEST 1 PASSED: Buffer correctly maintains 10 items\n")


def test_timestamps_present():
    """Test 2: Verify each element has a timestamp."""
    print_separator("TEST 2: Each element has a timestamp")
    
    manager = NodeDataQueueManager()
    image_dict = QueueBackedDict(manager, "image")
    
    # Add 5 items
    print("Adding 5 items with timestamps...")
    for i in range(5):
        image_dict["1:Camera"] = f"frame_{i}"
        time.sleep(0.01)
    
    # Get all items and check timestamps
    queue = manager.get_queue("1:Camera", "image")
    all_items = queue.get_all()
    
    print(f"\nItems with timestamps:")
    for i, item in enumerate(all_items):
        print(f"  {i+1}. Data: {item.data:15} | Timestamp: {item.timestamp:.6f} | Node: {item.node_id}")
        assert item.timestamp is not None, "Timestamp should not be None"
        assert isinstance(item.timestamp, float), "Timestamp should be a float"
    
    # Verify timestamps are in chronological order
    for i in range(len(all_items) - 1):
        assert all_items[i].timestamp <= all_items[i+1].timestamp, \
            "Timestamps should be in chronological order"
    
    print("\n✅ TEST 2 PASSED: All elements have valid timestamps in chronological order\n")


def test_synchronization():
    """Test 3: Verify synchronization using timestamps."""
    print_separator("TEST 3: Synchronization using timestamps")
    
    manager = NodeDataQueueManager()
    video_dict = QueueBackedDict(manager, "image")
    audio_dict = QueueBackedDict(manager, "audio")
    
    # Simulate video and audio streams
    print("Simulating video and audio streams...")
    base_time = time.time()
    
    for i in range(5):
        video_dict["1:Camera"] = f"video_frame_{i}"
        audio_dict["1:Microphone"] = f"audio_chunk_{i}"
        time.sleep(0.01)
    
    # Get all items from both buffers
    video_queue = manager.get_queue("1:Camera", "image")
    audio_queue = manager.get_queue("1:Microphone", "audio")
    
    video_items = video_queue.get_all()
    audio_items = audio_queue.get_all()
    
    print(f"\nVideo buffer has {len(video_items)} items")
    print(f"Audio buffer has {len(audio_items)} items")
    
    # Synchronize by timestamp
    print("\nSynchronized pairs (by timestamp):")
    for i, (v_item, a_item) in enumerate(zip(video_items, audio_items)):
        time_diff = abs(v_item.timestamp - a_item.timestamp)
        print(f"  {i+1}. Video: {v_item.data:20} | Audio: {a_item.data:20} | "
              f"Time diff: {time_diff*1000:.2f}ms")
        # They should be very close in time
        assert time_diff < 0.1, f"Timestamps too far apart: {time_diff}s"
    
    print("\n✅ TEST 3 PASSED: Can synchronize streams using timestamps\n")


def test_non_consuming_reads():
    """Test 4: Verify reading doesn't consume items (not FIFO)."""
    print_separator("TEST 4: Reading doesn't consume items (not FIFO)")
    
    manager = NodeDataQueueManager()
    image_dict = QueueBackedDict(manager, "image")
    
    # Add 3 items
    print("Adding 3 items to buffer...")
    image_dict["1:Camera"] = "frame_1"
    time.sleep(0.01)
    image_dict["1:Camera"] = "frame_2"
    time.sleep(0.01)
    image_dict["1:Camera"] = "frame_3"
    
    # Get queue info
    info_before = image_dict.get_queue_info("1:Camera")
    print(f"Buffer size before reads: {info_before['size']}")
    
    # Read latest multiple times
    print("\nReading latest item 5 times...")
    for i in range(5):
        latest = image_dict["1:Camera"]
        print(f"  Read {i+1}: {latest}")
        assert latest == "frame_3", "Should always get the latest item"
    
    # Check buffer size after reads
    info_after = image_dict.get_queue_info("1:Camera")
    print(f"\nBuffer size after reads: {info_after['size']}")
    
    # Size should be unchanged
    assert info_before['size'] == info_after['size'], \
        "Buffer size should not change after reads"
    
    # All items should still be accessible
    queue = manager.get_queue("1:Camera", "image")
    all_items = queue.get_all()
    print(f"All items still in buffer: {[item.data for item in all_items]}")
    assert len(all_items) == 3, "All 3 items should still be in buffer"
    
    print("\n✅ TEST 4 PASSED: Reading doesn't consume items from buffer\n")


def main():
    """Run all verification tests."""
    print_separator("TIMESTAMPED BUFFER SYSTEM VERIFICATION")
    
    print("""
This script verifies that the buffer system:
1. Holds exactly 10 values in memory
2. Each element has a timestamp for synchronization
3. Can synchronize multiple streams using timestamps
4. Reading doesn't consume items (not FIFO behavior)
    """)
    
    try:
        test_buffer_holds_10_values()
        test_timestamps_present()
        test_synchronization()
        test_non_consuming_reads()
        
        print_separator()
        print("✅ ALL VERIFICATION TESTS PASSED!")
        print("\nThe buffer system correctly:")
        print("  ✓ Maintains a rolling buffer of 10 timestamped items")
        print("  ✓ Provides timestamps for synchronization")
        print("  ✓ Supports multi-stream synchronization")
        print("  ✓ Uses buffer behavior (not FIFO consumption)")
        print_separator()
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
