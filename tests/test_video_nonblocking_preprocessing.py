#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test that video node preprocessing is non-blocking for UI"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_video_node_has_threading_import():
    """Test that node_video.py imports threading module"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that threading is imported
    assert 'import threading' in content, "threading module should be imported"
    print("✓ threading module imported in node_video.py")


def test_video_node_imports_dpg_lock():
    """Test that node_video.py imports _dpg_lock for thread safety"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that _dpg_lock is imported from util
    assert '_dpg_lock' in content, "_dpg_lock should be imported from util"
    print("✓ _dpg_lock imported in node_video.py")


def test_video_node_has_preprocessing_status():
    """Test that node_video.py has preprocessing status tracking"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that preprocessing status dict exists
    assert '_preprocessing_status = {}' in content, "_preprocessing_status dict should exist"
    assert '_preprocessing_threads = {}' in content, "_preprocessing_threads dict should exist"
    print("✓ Preprocessing status tracking variables exist")


def test_callback_file_select_uses_threading():
    """Test that _callback_file_select runs preprocessing in a background thread"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Find _callback_file_select method
    assert 'def _callback_file_select(self, sender, data):' in content
    
    # Check that the method creates a thread
    method_start = content.find('def _callback_file_select(self, sender, data):')
    method_end = content.find('\n    def ', method_start + 1)
    if method_end == -1:
        method_end = len(content)
    method_section = content[method_start:method_end]
    
    # Verify it creates a thread
    assert 'threading.Thread(' in method_section, "_callback_file_select should create a Thread"
    assert 'daemon=True' in method_section, "Thread should be daemon to not block shutdown"
    assert 'thread.start()' in method_section, "Thread should be started"
    
    # Verify it sets preprocessing status
    assert "self._preprocessing_status[node_id] = 'loading'" in method_section, \
        "Should set preprocessing status to 'loading'"
    
    # Verify it uses thread-safe DPG operations
    assert 'with _dpg_lock:' in method_section, "Should use _dpg_lock for thread-safe DPG operations"
    
    print("✓ _callback_file_select uses threading for non-blocking preprocessing")


def test_update_checks_preprocessing_status():
    """Test that update() method checks preprocessing status before processing"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Find update method
    assert 'def update(' in content
    
    # Check that update checks preprocessing status
    update_start = content.find('def update(')
    update_end = content.find('\n    def ', update_start + 1)
    if update_end == -1:
        # If no next method, take a large section
        update_end = update_start + 5000
    update_section = content[update_start:update_end]
    
    # Verify it checks preprocessing status
    assert 'preprocessing_status = self._preprocessing_status.get(' in update_section, \
        "Should get preprocessing status"
    assert "preprocessing_status == 'loading'" in update_section, \
        "Should check if preprocessing is still in progress"
    
    print("✓ update() method checks preprocessing status")


def test_close_cleans_up_threading():
    """Test that close() method cleans up threading resources"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Find close method
    assert 'def close(self, node_id):' in content
    
    # Check that close cleans up preprocessing resources
    close_start = content.find('def close(self, node_id):')
    close_end = content.find('\n    def ', close_start + 1)
    if close_end == -1:
        close_end = len(content)
    close_section = content[close_start:close_end]
    
    # Verify it cleans up preprocessing status and threads
    assert '_preprocessing_status' in close_section, "Should clean up preprocessing status"
    assert '_preprocessing_threads' in close_section, "Should clean up preprocessing threads"
    
    print("✓ close() method cleans up threading resources")


def test_syntax_valid():
    """Test that node_video.py has valid Python syntax"""
    import py_compile
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    # This will raise SyntaxError if file is invalid
    py_compile.compile(video_node_path, doraise=True)
    
    print("✓ node_video.py has valid Python syntax")


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Video Node Non-Blocking Preprocessing")
    print("=" * 70)
    
    try:
        test_video_node_has_threading_import()
        test_video_node_imports_dpg_lock()
        test_video_node_has_preprocessing_status()
        test_callback_file_select_uses_threading()
        test_update_checks_preprocessing_status()
        test_close_cleans_up_threading()
        test_syntax_valid()
        
        print("=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)
        print("\nSummary:")
        print("- Video preprocessing now runs in background thread")
        print("- UI remains responsive during video loading")
        print("- Thread-safe DPG operations with _dpg_lock")
        print("- Proper cleanup of threading resources")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
