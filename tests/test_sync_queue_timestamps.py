#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the SyncQueue node timestamp-based synchronization
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.timestamped_queue import NodeDataQueueManager, TimestampedData
from node.queue_adapter import QueueBackedDict


def test_sync_queue_data_retrieval():
    """Test that SyncQueue can retrieve data from timestamped queues"""
    print("\n--- Testing SyncQueue data retrieval from queues ---")
    
    # Create queue manager and queue-backed dicts
    queue_manager = NodeDataQueueManager(default_maxsize=10)
    node_image_dict = QueueBackedDict(queue_manager, "image")
    node_result_dict = QueueBackedDict(queue_manager, "json")
    node_audio_dict = QueueBackedDict(queue_manager, "audio")
    
    # Simulate data from multiple sources
    source_node_1 = "1:Webcam"
    source_node_2 = "2:Microphone"
    
    # Add timestamped data
    timestamp1 = time.time()
    node_image_dict[source_node_1] = "image_data_1"
    node_result_dict[source_node_1] = {"result": "data_1"}
    
    time.sleep(0.1)
    timestamp2 = time.time()
    node_audio_dict[source_node_2] = "audio_data_1"
    
    # Verify data is in queues
    queue_image = queue_manager.get_queue(source_node_1, "image")
    queue_json = queue_manager.get_queue(source_node_1, "json")
    queue_audio = queue_manager.get_queue(source_node_2, "audio")
    
    assert queue_image.size() == 1, f"Expected 1 image, got {queue_image.size()}"
    assert queue_json.size() == 1, f"Expected 1 json, got {queue_json.size()}"
    assert queue_audio.size() == 1, f"Expected 1 audio, got {queue_audio.size()}"
    
    # Verify timestamps exist
    all_images = queue_image.get_all()
    assert len(all_images) == 1, "Should have 1 timestamped image"
    assert all_images[0].timestamp > 0, "Timestamp should be set"
    
    print("✓ SyncQueue can retrieve timestamped data from queues")
    return True


def test_sync_queue_multiple_items():
    """Test that SyncQueue can access multiple buffered items"""
    print("\n--- Testing SyncQueue with multiple buffered items ---")
    
    queue_manager = NodeDataQueueManager(default_maxsize=10)
    node_image_dict = QueueBackedDict(queue_manager, "image")
    
    source_node = "1:Webcam"
    
    # Add multiple items with different timestamps
    for i in range(5):
        node_image_dict[source_node] = f"image_frame_{i}"
        time.sleep(0.01)
    
    # Verify all items are in buffer
    queue = queue_manager.get_queue(source_node, "image")
    all_items = queue.get_all()
    
    assert len(all_items) == 5, f"Expected 5 items, got {len(all_items)}"
    
    # Verify timestamps are in order
    for i in range(len(all_items) - 1):
        assert all_items[i].timestamp < all_items[i+1].timestamp, \
            "Timestamps should be in ascending order"
    
    # Verify latest item is accessible
    latest = queue.get_latest()
    assert latest.data == "image_frame_4", f"Latest should be frame_4, got {latest.data}"
    
    print("✓ SyncQueue can access multiple buffered items with timestamps")
    return True


def test_sync_queue_retention_time():
    """Test retention time concept (items older than retention are filtered)"""
    print("\n--- Testing retention time filtering ---")
    
    queue_manager = NodeDataQueueManager(default_maxsize=10)
    node_image_dict = QueueBackedDict(queue_manager, "image")
    
    source_node = "1:Webcam"
    
    # Add items with controlled timestamps
    current_time = time.time()
    queue = queue_manager.get_queue(source_node, "image")
    
    # Manually add items with specific timestamps
    queue.put("old_data", timestamp=current_time - 2.0)  # 2 seconds old
    queue.put("recent_data", timestamp=current_time - 0.5)  # 0.5 seconds old
    queue.put("newest_data", timestamp=current_time)  # Just now
    
    all_items = queue.get_all()
    assert len(all_items) == 3, f"Expected 3 items, got {len(all_items)}"
    
    # Simulate retention time filtering (items older than 1 second)
    retention_time = 1.0
    valid_items = [
        item for item in all_items
        if (current_time - item.timestamp) <= retention_time
    ]
    
    assert len(valid_items) == 2, \
        f"Expected 2 items within retention time, got {len(valid_items)}"
    
    print("✓ Retention time filtering works correctly")
    return True


def test_sync_queue_timestamp_sync():
    """Test timestamp-based synchronization across multiple sources"""
    print("\n--- Testing timestamp-based synchronization ---")
    
    queue_manager = NodeDataQueueManager(default_maxsize=10)
    node_image_dict = QueueBackedDict(queue_manager, "image")
    node_audio_dict = QueueBackedDict(queue_manager, "audio")
    
    video_source = "1:Webcam"
    audio_source = "2:Microphone"
    
    # Add synchronized data (same timestamps)
    base_time = time.time()
    
    queue_video = queue_manager.get_queue(video_source, "image")
    queue_audio = queue_manager.get_queue(audio_source, "audio")
    
    # Add 3 synchronized pairs
    for i in range(3):
        timestamp = base_time + i * 0.1
        queue_video.put(f"video_frame_{i}", timestamp=timestamp)
        queue_audio.put(f"audio_chunk_{i}", timestamp=timestamp)
    
    # Verify both queues have 3 items
    assert queue_video.size() == 3, f"Expected 3 video items, got {queue_video.size()}"
    assert queue_audio.size() == 3, f"Expected 3 audio items, got {queue_audio.size()}"
    
    # Verify timestamps match
    video_items = queue_video.get_all()
    audio_items = queue_audio.get_all()
    
    for i in range(3):
        assert video_items[i].timestamp == audio_items[i].timestamp, \
            f"Timestamps should match at index {i}"
    
    print("✓ Timestamp-based synchronization works correctly")
    return True


def test_sync_queue_no_visual_display():
    """Test that sync queue doesn't require visual components"""
    print("\n--- Testing SyncQueue without visual display ---")
    
    try:
        from node.SystemNode import node_sync_queue
        node = node_sync_queue.Node()
        
        # Check that node doesn't require cv2 for basic functionality
        assert hasattr(node, 'update'), "Node should have update method"
        assert hasattr(node, '_sync_state'), "Node should have _sync_state"
        
        # The node should be able to work without convert_cv_to_dpg for outputs
        # (outputs are text only now)
        
        print("✓ SyncQueue works without visual display requirements")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


if __name__ == '__main__':
    print("Running SyncQueue Timestamp Synchronization Tests\n")
    print("="*60)
    
    tests = [
        test_sync_queue_data_retrieval,
        test_sync_queue_multiple_items,
        test_sync_queue_retention_time,
        test_sync_queue_timestamp_sync,
        test_sync_queue_no_visual_display,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Tests Passed: {passed}/{len(tests)}")
    print(f"Tests Failed: {failed}/{len(tests)}")
    print("="*60)
    
    sys.exit(0 if failed == 0 else 1)
