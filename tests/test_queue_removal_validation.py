#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to validate that queue-based implementation has been removed from node_video_writer.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_queue_import_removed():
    """Test that queue module is not imported"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that queue is not imported
    assert 'import queue' not in content, "queue module should not be imported"
    assert 'from queue import' not in content, "queue module should not be imported"
    
    print("✓ Queue import removed test passed")


def test_queue_related_dicts_removed():
    """Test that queue-related dictionaries have been removed"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that queue-related dictionaries are removed
    assert '_write_queues_dict = {}' not in content, "_write_queues_dict should be removed"
    assert '_write_threads_dict = {}' not in content, "_write_threads_dict should be removed"
    assert '_stop_flags_dict = {}' not in content, "_stop_flags_dict should be removed"
    assert '_dropped_frames_dict = {}' not in content, "_dropped_frames_dict should be removed"
    
    print("✓ Queue-related dictionaries removed test passed")


def test_writer_thread_removed():
    """Test that _writer_thread method has been removed"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that _writer_thread method is removed
    assert 'def _writer_thread(' not in content, "_writer_thread method should be removed"
    assert 'write_queue.get(' not in content, "queue.get() should not be used"
    assert 'write_queue.put(' not in content, "queue.put() should not be used"
    assert 'queue.Empty' not in content, "queue.Empty exception should not be used"
    
    print("✓ Writer thread removed test passed")


def test_direct_frame_writing():
    """Test that direct frame writing is implemented"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that direct writing is implemented
    assert 'video_writer.write(' in content, "Direct video_writer.write() should be present"
    assert 'cv2.resize(' in content, "Frame resizing should be present"
    assert 'Direct frame-by-frame writing' in content, "Documentation should mention direct writing"
    
    print("✓ Direct frame writing test passed")


def test_dimension_tracking_added():
    """Test that dimension tracking dictionaries have been added"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that dimension tracking dictionaries are present
    assert '_writer_width_dict' in content, "_writer_width_dict should be present"
    assert '_writer_height_dict' in content, "_writer_height_dict should be present"
    
    print("✓ Dimension tracking added test passed")


def test_background_finalization_kept():
    """Test that background finalization thread is still present (prevents UI freeze)"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that background finalization is kept
    assert '_release_video_writer_async' in content, "Background finalization should be kept"
    assert '_release_threads_dict' in content, "Release threads dict should be kept"
    assert 'video_writer.release()' in content, "video_writer.release() should be present"
    
    print("✓ Background finalization kept test passed")


def test_code_simplification():
    """Test that code has been simplified (line count reduced)"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    line_count = len(lines)
    
    # The original had 727 lines, we should have significantly less
    assert line_count < 700, f"Code should be simplified (got {line_count} lines, expected < 700)"
    
    print(f"✓ Code simplification test passed - {line_count} lines (was 727, reduced by {727 - line_count} lines)")


def test_no_queue_usage():
    """Test that Queue() constructor is not used"""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that Queue() constructor is not used
    assert 'queue.Queue(' not in content, "queue.Queue() constructor should not be used"
    assert 'Queue(maxsize=' not in content, "Queue(maxsize=) should not be used"
    
    print("✓ No queue usage test passed")


if __name__ == "__main__":
    test_queue_import_removed()
    test_queue_related_dicts_removed()
    test_writer_thread_removed()
    test_direct_frame_writing()
    test_dimension_tracking_added()
    test_background_finalization_kept()
    test_code_simplification()
    test_no_queue_usage()
    print("\n✅ All queue removal validation tests passed!")
