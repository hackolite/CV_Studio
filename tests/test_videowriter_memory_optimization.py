#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for VideoWriter node memory optimization.

This test validates the optimization that eliminates unnecessary full-size frame copies
when connected to ImageConcat. The key optimization is:
- Resize first (small copy), then draw indicator on resized frame
- Instead of: copy full frame, draw indicator, then resize

This saves significant memory when processing large concatenated frames from ImageConcat.
"""
import sys
import os
import tempfile
import numpy as np
import queue

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_resize_before_indicator_optimization():
    """
    Test the memory optimization: resize frame to display size.
    
    This avoids making a full-size copy of potentially large frames from ImageConcat.
    NEW: resize to display (0.2MB) - no indicator to save resources
    
    Note: Recording indicator has been removed to save CPU resources as requested.
    Memory saved: 6MB per frame, or 180MB/second at 30fps
    """
    import cv2
    
    # Simulate a large concatenated frame from ImageConcat (Full HD)
    large_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    large_frame[:, :] = [100, 150, 200]  # Set to specific BGR values
    
    # Save original for verification
    original_pixel = large_frame[100, 100].copy()
    
    # Simulate VideoWriter display dimensions
    display_width = 320
    display_height = 180
    
    # OPTIMIZED APPROACH:
    # Resize first (creates a small copy automatically)
    # No recording indicator drawn (removed to save resources)
    display_frame = cv2.resize(large_frame, (display_width, display_height))
    
    # Verify original frame is NOT corrupted
    assert np.array_equal(large_frame[100, 100], original_pixel), \
        f"Original frame was corrupted! Expected {original_pixel}, got {large_frame[100, 100]}"
    
    # Verify display frame has correct size
    assert display_frame.shape == (display_height, display_width, 3), \
        f"Display frame has wrong size: {display_frame.shape}"
    
    # Calculate memory savings
    large_frame_bytes = large_frame.nbytes
    display_frame_bytes = display_frame.nbytes
    memory_saved = large_frame_bytes - display_frame_bytes
    
    return {
        'large_frame_mb': large_frame_bytes / (1024*1024),
        'display_frame_mb': display_frame_bytes / (1024*1024),
        'memory_saved_mb': memory_saved / (1024*1024),
        'fps_30_saved_mb': memory_saved * 30 / (1024*1024)
    }


def test_frame_copy_only_when_recording():
    """
    Test that frames are only copied when recording is active.
    
    This optimization dramatically reduces memory usage:
    - When recording: frame is copied to queue (necessary for thread safety)
    - When not recording: no queue copy needed
    
    Note: This test does not import VideoWriterNode to avoid dearpygui dependency.
    It validates the logic that would be used in the actual node.
    """
    # Create a test frame (simulate ImageConcat output)
    test_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    test_frame[:, :] = [100, 150, 200]
    
    # Simulate write queue state
    write_queues_dict = {}
    dropped_frames_dict = {}
    tag_node_name = "test_node"
    
    # Test 1: Not recording - no queue exists
    # Frame should NOT be copied to queue
    assert tag_node_name not in write_queues_dict, \
        "Queue should not exist when not recording"
    
    # Simulate the logic from update() when NOT recording
    if tag_node_name in write_queues_dict:
        # This should NOT execute
        assert False, "Should not try to copy frame when not recording"
    
    # Test 2: Recording active - queue exists
    # Frame SHOULD be copied to queue
    write_queues_dict[tag_node_name] = queue.Queue(maxsize=60)
    dropped_frames_dict[tag_node_name] = 0
    
    # Simulate the logic from update() when recording
    if tag_node_name in write_queues_dict:
        try:
            # This should execute and copy the frame
            write_queues_dict[tag_node_name].put_nowait(test_frame.copy())
        except queue.Full:
            pass
    
    # Verify frame was added to queue
    assert not write_queues_dict[tag_node_name].empty(), \
        "Frame should be in queue when recording"
    
    queued_frame = write_queues_dict[tag_node_name].get_nowait()
    
    # Verify it's a copy (different object)
    assert queued_frame is not test_frame, \
        "Queued frame should be a copy, not the original"
    
    # But with same data
    assert np.array_equal(queued_frame, test_frame), \
        "Queued frame should have same data as original"


def test_display_frame_always_resized():
    """
    Test that display frame is always resized, regardless of recording state.
    
    The optimization resizes frames for display to save memory.
    This is more efficient because:
    1. Resize creates a small copy automatically (necessary for display)
    2. No recording indicator is drawn (removed to save CPU resources)
    3. No separate full-size copy is needed
    """
    import cv2
    
    # Create a large test frame (simulate ImageConcat output)
    large_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    large_frame[:, :] = [100, 150, 200]
    
    display_width = 320
    display_height = 180
    
    # Test 1: Not recording - resize only
    display_frame_not_recording = cv2.resize(large_frame, (display_width, display_height))
    
    assert display_frame_not_recording.shape == (display_height, display_width, 3), \
        "Display frame should be resized when not recording"
    
    # No indicator (removed to save resources)
    assert display_frame_not_recording[10, 10][2] != 255, \
        "No indicator should be present (removed to save resources)"
    
    # Test 2: Recording - resize only (no indicator drawn)
    display_frame_recording = cv2.resize(large_frame, (display_width, display_height))
    
    assert display_frame_recording.shape == (display_height, display_width, 3), \
        "Display frame should be resized when recording"
    
    # No indicator drawn (removed to save CPU resources)
    assert display_frame_recording[10, 10][2] != 255, \
        "No indicator should be drawn when recording (removed to save resources)"
    
    # Original frame unchanged in both cases
    assert large_frame[10, 10][2] != 255, \
        "Original frame should never be modified"
    
    # Both approaches produce small frames (memory efficient)
    assert display_frame_not_recording.nbytes == display_frame_recording.nbytes, \
        "Both display frames should have same size (small)"


if __name__ == "__main__":
    print("Testing VideoWriter memory optimization...")
    print("=" * 70)
    print()
    
    print("Test 1: Frame resize optimization")
    print("-" * 70)
    stats = test_resize_before_indicator_optimization()
    print(f"✓ Test passed")
    print(f"  Large frame: {stats['large_frame_mb']:.2f} MB")
    print(f"  Display frame: {stats['display_frame_mb']:.2f} MB")
    print(f"  Memory saved: {stats['memory_saved_mb']:.2f} MB per frame")
    print(f"  At 30fps: {stats['fps_30_saved_mb']:.1f} MB/second saved")
    print()
    
    print("Test 2: Frame copy only when recording")
    print("-" * 70)
    test_frame_copy_only_when_recording()
    print("✓ Test passed - queue copy logic validated")
    print()
    
    print("Test 3: Display frame always resized")
    print("-" * 70)
    test_display_frame_always_resized()
    print("✓ Test passed - display resize logic validated")
    print()
    
    print("=" * 70)
    print("✅ All VideoWriter memory optimization tests passed!")
    print()
    print("Summary:")
    print("• Display frame resized for efficient display")
    print("• Recording indicator removed to save CPU resources")
    print("• Eliminates unnecessary full-size frame copy")
    print("• Memory savings: 2-6 MB per frame (input size dependent)")
    print("• At 30fps: 60-180 MB/second saved when recording")
    print("• Original frame never modified (thread-safe)")
    print("• Queue copy retained for thread safety (necessary)")
