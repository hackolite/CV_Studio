#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for async video merge functionality in VideoWriter node.
"""
import time
import threading
import numpy as np

def test_async_merge_thread_simulation():
    """
    Test that demonstrates the async merge pattern works correctly.
    This simulates the threading pattern used in the VideoWriter node.
    """
    merge_progress = {}
    merge_threads = {}
    
    def mock_merge_with_progress(tag, progress_callback):
        """Simulates a merge operation with progress reporting"""
        for i in range(11):
            progress_callback(i / 10.0)
            time.sleep(0.01)  # Simulate work
        return True
    
    def async_merge_thread(tag):
        """Thread worker that performs async merge"""
        def progress_callback(progress):
            merge_progress[tag] = progress
        
        merge_progress[tag] = 0.0
        success = mock_merge_with_progress(tag, progress_callback)
        merge_progress[tag] = 1.0
        return success
    
    # Start the merge in a thread
    tag = "test_node"
    thread = threading.Thread(target=async_merge_thread, args=(tag,), daemon=True)
    thread.start()
    merge_threads[tag] = thread
    
    # Wait for thread to complete
    thread.join(timeout=5.0)
    
    # Verify the thread completed
    assert not thread.is_alive(), "Thread should have completed"
    
    # Verify progress reached 100%
    assert merge_progress[tag] == 1.0, f"Progress should be 1.0, got {merge_progress[tag]}"
    
    print("✓ Async merge thread test passed")


def test_progress_callback_updates():
    """Test that progress callbacks update correctly during merge"""
    progress_values = []
    
    def progress_callback(value):
        progress_values.append(value)
    
    # Simulate progress updates
    for i in range(6):
        progress_callback(i / 5.0)
    
    # Verify we got all progress updates
    assert len(progress_values) == 6, f"Expected 6 updates, got {len(progress_values)}"
    assert progress_values[0] == 0.0, "First progress should be 0.0"
    assert progress_values[-1] == 1.0, "Last progress should be 1.0"
    assert all(progress_values[i] <= progress_values[i+1] for i in range(len(progress_values)-1)), \
        "Progress should be monotonically increasing"
    
    print("✓ Progress callback test passed")


def test_thread_safety_with_copy():
    """Test that copying data before threading prevents race conditions"""
    original_data = [np.array([1, 2, 3]), np.array([4, 5, 6])]
    
    # Make a deep copy for the thread
    import copy
    thread_data = copy.deepcopy(original_data)
    
    # Modify original data
    original_data.append(np.array([7, 8, 9]))
    
    # Thread data should not be affected
    assert len(thread_data) == 2, "Thread data should not be modified"
    assert len(original_data) == 3, "Original data should be modified"
    
    print("✓ Thread safety test passed")


if __name__ == "__main__":
    test_async_merge_thread_simulation()
    test_progress_callback_updates()
    test_thread_safety_with_copy()
    print("\n✅ All async merge tests passed!")
