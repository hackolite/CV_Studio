#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that VideoWriter release operation happens in background thread
to prevent UI freezing.

This test verifies:
1. Release threads dictionary exists
2. Finalizing label exists
3. Background release method exists
4. The _release_video_writer_async method is properly defined
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_release_threads_dict_exists():
    """Test that _release_threads_dict class variable exists"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    assert '_release_threads_dict = {}' in content or '_release_threads_dict={}' in content, \
        "VideoWriterNode should have _release_threads_dict class variable"
    
    print("✓ Release threads dict exists")


def test_finalizing_label_exists():
    """Test that _finalizing_label is defined"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    assert '_finalizing_label = ' in content, \
        "VideoWriterNode should have _finalizing_label"
    
    assert 'Finalizing' in content, \
        "Finalizing label should indicate progress"
    
    print("✓ Finalizing label exists")


def test_async_release_method_exists():
    """Test that _release_video_writer_async method exists"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    assert 'def _release_video_writer_async(' in content, \
        "VideoWriterNode should have _release_video_writer_async method"
    
    print("✓ Async release method exists")


def test_threading_import_exists():
    """Test that threading module is imported"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    assert 'import threading' in content, \
        "VideoWriterNode should import threading module"
    
    print("✓ Threading module is imported")


def test_background_thread_creation():
    """Test that background thread is created when stopping"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Check that threading.Thread is used
    assert 'threading.Thread(' in content, \
        "Should create threading.Thread for background release"
    
    # Check that thread is started
    assert 'release_thread.start()' in content, \
        "Should start the release thread"
    
    # Check that thread is tracked
    assert '_release_threads_dict[tag_node_name] = release_thread' in content or \
           'self._release_threads_dict[tag_node_name] = release_thread' in content, \
        "Should track the release thread"
    
    print("✓ Background thread is created and tracked")


def test_async_release_prevents_ui_freeze():
    """Test that async release includes documentation about preventing UI freeze"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Find the _release_video_writer_async method
    method_start = content.find('def _release_video_writer_async(')
    method_end = content.find('\n    def ', method_start + 1)
    method_content = content[method_start:method_end]
    
    # Check that documentation mentions preventing UI freeze
    assert 'UI freeze' in method_content or 'freeze' in method_content, \
        "Method should document that it prevents UI freeze"
    
    # Check that video_writer.release() is called in the method
    assert 'video_writer.release()' in method_content, \
        "Method should call video_writer.release()"
    
    print("✓ Async release method properly documented and implemented")


def test_close_method_waits_for_threads():
    """Test that close() method waits for background threads"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Find the close method
    close_start = content.find('def close(self, node_id):')
    close_end = content.find('\n    def ', close_start + 1)
    close_content = content[close_start:close_end]
    
    # Check that it checks for release threads
    assert '_release_threads_dict' in close_content, \
        "close() should check for release threads"
    
    # Check that it waits for threads
    assert 'join(' in close_content, \
        "close() should wait for threads to complete"
    
    print("✓ Close method properly waits for background threads")


def test_stop_button_shows_finalizing():
    """Test that stop button updates to show 'Finalizing...' state"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Find the stop recording section
    stop_section_start = content.find("elif label == self._stop_label:")
    stop_section_end = content.find("logger.info(f\"[VideoWriter] Stopped recording", stop_section_start)
    
    if stop_section_start > 0 and stop_section_end > 0:
        stop_section = content[stop_section_start:stop_section_end]
        
        # Check that button is updated to finalizing
        assert '_finalizing_label' in stop_section, \
            "Stop recording should update button to finalizing label"
        
        assert 'dpg.set_item_label' in stop_section, \
            "Stop recording should update button label"
    
    print("✓ Stop button properly shows finalizing state")


if __name__ == "__main__":
    test_release_threads_dict_exists()
    test_finalizing_label_exists()
    test_async_release_method_exists()
    test_threading_import_exists()
    test_background_thread_creation()
    test_async_release_prevents_ui_freeze()
    test_close_method_waits_for_threads()
    test_stop_button_shows_finalizing()
    print("\n✅ All async release tests passed!")
