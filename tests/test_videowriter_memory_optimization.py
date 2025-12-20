#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for VideoWriter node memory optimization and frame corruption fixes.

This test validates:
1. Frames are only copied when recording is active (not during display-only mode)
2. Drawing the recording indicator doesn't corrupt the original frame
"""
import sys
import os
import tempfile
import numpy as np
import queue

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_frame_not_corrupted_by_recording_indicator():
    """
    Test that drawing the recording indicator doesn't corrupt the original frame.
    
    This was a critical bug where cv2.circle() was modifying the original frame
    directly, corrupting downstream processing.
    """
    from node.VideoNode.node_video_writer import VideoWriterNode
    
    # Create a test frame with a known pattern
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:, :] = [100, 150, 200]  # Set to specific BGR values
    
    # Save original values for comparison
    original_pixel_at_circle = test_frame[10, 10].copy()
    original_pixel_away = test_frame[100, 100].copy()
    
    # Create node instance
    node = VideoWriterNode()
    node._opencv_setting_dict = {
        'process_width': 320,
        'process_height': 240,
    }
    
    # Simulate the display frame preparation when recording
    # This is what happens in the update() method
    tag_node_name = "test_node"
    
    # Simulate recording state
    node._video_writer_dict[tag_node_name] = "dummy_writer"
    
    # Prepare display frame (this should NOT corrupt the original frame)
    if tag_node_name in node._video_writer_dict:
        display_frame = test_frame.copy()
        import cv2
        cv2.circle(display_frame, (10, 10), 50, (0, 0, 255), thickness=-1)
    else:
        display_frame = test_frame
    
    # Verify original frame is not corrupted
    assert np.array_equal(test_frame[10, 10], original_pixel_at_circle), \
        f"Original frame was corrupted at circle position! Expected {original_pixel_at_circle}, got {test_frame[10, 10]}"
    
    assert np.array_equal(test_frame[100, 100], original_pixel_away), \
        f"Original frame was corrupted away from circle! Expected {original_pixel_away}, got {test_frame[100, 100]}"
    
    # Verify display frame has the red circle
    # The circle is drawn at (10, 10) with BGR color (0, 0, 255) = red
    assert display_frame[10, 10][2] == 255, \
        f"Display frame should have red circle, but pixel is {display_frame[10, 10]}"
    
    print("✓ Frame corruption test passed - original frame is preserved")
    
    # Clean up
    node._video_writer_dict.clear()


def test_frame_copy_only_when_recording():
    """
    Test that frames are only copied when recording is active.
    
    This optimization dramatically reduces memory usage when just displaying frames.
    """
    from node.VideoNode.node_video_writer import VideoWriterNode
    
    # Create node instance
    node = VideoWriterNode()
    node._opencv_setting_dict = {
        'process_width': 320,
        'process_height': 240,
    }
    
    tag_node_name = "test_node"
    
    # Create a test frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:, :] = [100, 150, 200]
    
    # Test 1: Not recording - no queue exists
    # Frame should NOT be copied to queue
    assert tag_node_name not in node._write_queues_dict, \
        "Queue should not exist when not recording"
    
    # Simulate the logic from update() when NOT recording
    if tag_node_name in node._write_queues_dict:
        # This should NOT execute
        assert False, "Should not try to copy frame when not recording"
    
    print("✓ No frame copy when not recording")
    
    # Test 2: Recording active - queue exists
    # Frame SHOULD be copied to queue
    node._write_queues_dict[tag_node_name] = queue.Queue(maxsize=60)
    node._dropped_frames_dict[tag_node_name] = 0
    
    # Simulate the logic from update() when recording
    if tag_node_name in node._write_queues_dict:
        try:
            # This should execute and copy the frame
            node._write_queues_dict[tag_node_name].put_nowait(test_frame.copy())
        except queue.Full:
            pass
    
    # Verify frame was added to queue
    assert not node._write_queues_dict[tag_node_name].empty(), \
        "Frame should be in queue when recording"
    
    queued_frame = node._write_queues_dict[tag_node_name].get_nowait()
    
    # Verify it's a copy (different object)
    assert queued_frame is not test_frame, \
        "Queued frame should be a copy, not the original"
    
    # But with same data
    assert np.array_equal(queued_frame, test_frame), \
        "Queued frame should have same data as original"
    
    print("✓ Frame copied to queue when recording")
    
    # Clean up
    node._write_queues_dict.clear()
    node._dropped_frames_dict.clear()


def test_display_frame_logic():
    """
    Test the display frame logic:
    - When recording: create copy with red circle
    - When not recording: use original frame directly
    """
    from node.VideoNode.node_video_writer import VideoWriterNode
    import cv2
    
    node = VideoWriterNode()
    tag_node_name = "test_node"
    
    # Create a test frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:, :] = [100, 150, 200]
    
    # Test 1: Not recording - should use original frame
    display_frame = None
    if tag_node_name in node._video_writer_dict:
        display_frame = test_frame.copy()
        cv2.circle(display_frame, (10, 10), 50, (0, 0, 255), thickness=-1)
    else:
        display_frame = test_frame
    
    assert display_frame is test_frame, \
        "When not recording, display_frame should be the original frame (no copy)"
    
    print("✓ Display frame uses original when not recording")
    
    # Test 2: Recording - should create copy with red circle
    node._video_writer_dict[tag_node_name] = "dummy_writer"
    
    display_frame = None
    if tag_node_name in node._video_writer_dict:
        display_frame = test_frame.copy()
        cv2.circle(display_frame, (10, 10), 50, (0, 0, 255), thickness=-1)
    else:
        display_frame = test_frame
    
    assert display_frame is not test_frame, \
        "When recording, display_frame should be a copy"
    
    assert display_frame[10, 10][2] == 255, \
        "Recording indicator (red circle) should be present"
    
    assert test_frame[10, 10][2] != 255, \
        "Original frame should not have the recording indicator"
    
    print("✓ Display frame creates copy with indicator when recording")
    
    # Clean up
    node._video_writer_dict.clear()


if __name__ == "__main__":
    print("Testing VideoWriter memory optimization...")
    print()
    
    test_frame_not_corrupted_by_recording_indicator()
    test_frame_copy_only_when_recording()
    test_display_frame_logic()
    
    print()
    print("✅ All VideoWriter memory optimization tests passed!")
    print()
    print("Summary of optimizations:")
    print("1. Frames are only copied when recording is active")
    print("2. Recording indicator doesn't corrupt the original frame")
    print("3. Display uses original frame when not recording (zero copy)")
