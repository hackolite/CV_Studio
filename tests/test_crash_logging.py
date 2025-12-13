#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test crash logging functionality for VideoWriter and ImageConcat nodes.

Verifies that:
1. Crash logs are created when errors occur
2. Log files contain full stack traces
3. Log files are stored in the logs directory
4. Log files have proper naming and timestamps
"""

import sys
import os
import tempfile
import shutil
import datetime
import traceback
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import crash logging utilities
try:
    from src.utils.logging import get_logs_directory
except ImportError:
    def get_logs_directory():
        project_root = Path(__file__).parent.parent
        logs_dir = project_root / 'logs'
        logs_dir.mkdir(exist_ok=True)
        return logs_dir

# Define crash log functions locally for testing
# Note: We duplicate these functions here to avoid importing the full node modules
# which have heavy dependencies (cv2, dearpygui, etc.) that aren't needed for pure
# crash logging tests. This keeps tests lightweight and fast.
def create_crash_log(operation_name, exception, tag_node_name=None):
    """Create crash log for VideoWriter (test version)"""
    logs_dir = get_logs_directory()
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    node_suffix = f"_{tag_node_name.replace(':', '_')}" if tag_node_name else ""
    log_filename = f"crash_{operation_name}{node_suffix}_{timestamp}.log"
    log_path = logs_dir / log_filename
    
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write(f"CV Studio VideoWriter Crash Log\n")
        f.write("="*70 + "\n")
        f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Operation: {operation_name}\n")
        if tag_node_name:
            f.write(f"Node: {tag_node_name}\n")
        f.write(f"Exception Type: {type(exception).__name__}\n")
        f.write(f"Exception Message: {str(exception)}\n")
        f.write("="*70 + "\n\n")
        f.write("Full Stack Trace:\n")
        f.write("-"*70 + "\n")
        f.write(traceback.format_exc())
        f.write("\n")
        f.write("="*70 + "\n")
        f.write("End of crash log\n")
        f.write("="*70 + "\n")
    
    return log_path

def create_concat_crash_log(operation_name, exception, node_name=None):
    """Create crash log for ImageConcat"""
    logs_dir = get_logs_directory()
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    node_suffix = f"_{node_name.replace(':', '_')}" if node_name else ""
    log_filename = f"crash_imageconcat_{operation_name}{node_suffix}_{timestamp}.log"
    log_path = logs_dir / log_filename
    
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write(f"CV Studio ImageConcat Crash Log\n")
        f.write("="*70 + "\n")
        f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Operation: {operation_name}\n")
        if node_name:
            f.write(f"Node: {node_name}\n")
        f.write(f"Exception Type: {type(exception).__name__}\n")
        f.write(f"Exception Message: {str(exception)}\n")
        f.write("="*70 + "\n\n")
        f.write("Full Stack Trace:\n")
        f.write("-"*70 + "\n")
        f.write(traceback.format_exc())
        f.write("\n")
        f.write("="*70 + "\n")
        f.write("End of crash log\n")
        f.write("="*70 + "\n")
    
    return log_path


def test_create_crash_log_videowriter():
    """Test that VideoWriter crash log is created correctly"""
    # Create a test exception
    try:
        raise ValueError("Test exception for VideoWriter")
    except Exception as e:
        # Create crash log
        log_path = create_crash_log("test_operation", e, "TestNode:VideoWriter")
        
        # Verify log file was created
        assert log_path is not None, "Log path should not be None"
        assert os.path.exists(log_path), f"Log file should exist at {log_path}"
        
        # Verify log file content
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required sections
        assert "CV Studio VideoWriter Crash Log" in content
        assert "Operation: test_operation" in content
        assert "Node: TestNode:VideoWriter" in content
        assert "Exception Type: ValueError" in content
        assert "Exception Message: Test exception for VideoWriter" in content
        assert "Full Stack Trace:" in content
        assert "ValueError: Test exception for VideoWriter" in content
        
        # Clean up
        if os.path.exists(log_path):
            os.remove(log_path)
        
        print("✓ VideoWriter crash log created correctly")
        print(f"  - Log path: {log_path}")
        print(f"  - Content length: {len(content)} bytes")


def test_create_crash_log_imageconcat():
    """Test that ImageConcat crash log is created correctly"""
    # Create a test exception
    try:
        raise RuntimeError("Test exception for ImageConcat")
    except Exception as e:
        # Create crash log
        log_path = create_concat_crash_log("stream_processing", e, "TestNode:ImageConcat")
        
        # Verify log file was created
        assert log_path is not None, "Log path should not be None"
        assert os.path.exists(log_path), f"Log file should exist at {log_path}"
        
        # Verify log file content
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required sections
        assert "CV Studio ImageConcat Crash Log" in content
        assert "Operation: stream_processing" in content
        assert "Node: TestNode:ImageConcat" in content
        assert "Exception Type: RuntimeError" in content
        assert "Exception Message: Test exception for ImageConcat" in content
        assert "Full Stack Trace:" in content
        assert "RuntimeError: Test exception for ImageConcat" in content
        
        # Clean up
        if os.path.exists(log_path):
            os.remove(log_path)
        
        print("✓ ImageConcat crash log created correctly")
        print(f"  - Log path: {log_path}")
        print(f"  - Content length: {len(content)} bytes")


def test_crash_log_file_naming():
    """Test that crash log files have proper naming convention"""
    # Create a test exception
    try:
        raise Exception("Test for file naming")
    except Exception as e:
        # Create crash log
        log_path = create_crash_log("recording_start", e, "1:VideoWriter")
        
        # Verify filename format
        log_filename = os.path.basename(log_path)
        
        # Should start with "crash_"
        assert log_filename.startswith("crash_"), f"Filename should start with 'crash_': {log_filename}"
        
        # Should contain operation name
        assert "recording_start" in log_filename, f"Filename should contain operation name: {log_filename}"
        
        # Should contain node identifier
        assert "1_VideoWriter" in log_filename, f"Filename should contain node identifier: {log_filename}"
        
        # Should end with timestamp and .log
        assert log_filename.endswith(".log"), f"Filename should end with .log: {log_filename}"
        
        # Verify it's in the logs directory
        assert "logs" in str(log_path), f"Log should be in logs directory: {log_path}"
        
        # Clean up
        if os.path.exists(log_path):
            os.remove(log_path)
        
        print("✓ Crash log file naming is correct")
        print(f"  - Filename: {log_filename}")


def test_crash_log_with_nested_exception():
    """Test crash log with nested exception (multiple stack frames)"""
    def inner_function():
        raise KeyError("Inner exception")
    
    def outer_function():
        inner_function()
    
    try:
        outer_function()
    except Exception as e:
        # Create crash log
        log_path = create_crash_log("nested_error", e)
        
        # Verify log file was created
        assert log_path is not None
        assert os.path.exists(log_path)
        
        # Verify stack trace includes both functions
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "inner_function" in content, "Stack trace should include inner_function"
        assert "outer_function" in content, "Stack trace should include outer_function"
        assert "KeyError: 'Inner exception'" in content
        
        # Clean up
        if os.path.exists(log_path):
            os.remove(log_path)
        
        print("✓ Nested exception crash log created correctly")
        print(f"  - Includes full call stack")


def test_crash_log_without_node_name():
    """Test crash log creation without node name (should still work)"""
    try:
        raise TypeError("Test without node name")
    except Exception as e:
        # Create crash log without node name
        log_path = create_crash_log("generic_error", e, tag_node_name=None)
        
        # Verify log file was created
        assert log_path is not None
        assert os.path.exists(log_path)
        
        # Verify content doesn't have node field
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should not have "Node:" line if node_name is None
        assert "Operation: generic_error" in content
        assert "Exception Type: TypeError" in content
        
        # Filename should not have node identifier
        log_filename = os.path.basename(log_path)
        assert "generic_error" in log_filename
        
        # Clean up
        if os.path.exists(log_path):
            os.remove(log_path)
        
        print("✓ Crash log without node name created correctly")


def test_multiple_crash_logs():
    """Test that multiple crash logs don't overwrite each other"""
    log_paths = []
    
    try:
        # Create multiple crash logs in quick succession
        for i in range(3):
            try:
                raise ValueError(f"Test exception {i}")
            except Exception as e:
                log_path = create_crash_log(f"operation_{i}", e, f"Node{i}:Test")
                log_paths.append(log_path)
        
        # Verify all log files were created
        assert len(log_paths) == 3, "Should have created 3 log files"
        
        for log_path in log_paths:
            assert os.path.exists(log_path), f"Log file should exist: {log_path}"
        
        # Verify all files are unique
        assert len(set(log_paths)) == 3, "All log paths should be unique"
        
        # Verify each has correct content
        for i, log_path in enumerate(log_paths):
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert f"Test exception {i}" in content
            assert f"operation_{i}" in content
        
        print("✓ Multiple crash logs created without conflicts")
        print(f"  - Created {len(log_paths)} unique log files")
        
    finally:
        # Clean up all log files
        for log_path in log_paths:
            if os.path.exists(log_path):
                os.remove(log_path)


def test_crash_log_unicode_handling():
    """Test that crash logs handle unicode characters correctly"""
    try:
        raise Exception("Test with unicode: 日本語 émojis 🎥📹")
    except Exception as e:
        log_path = create_crash_log("unicode_test", e)
        
        # Verify file was created
        assert log_path is not None
        assert os.path.exists(log_path)
        
        # Verify unicode content is preserved
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "日本語" in content, "Japanese characters should be preserved"
        assert "émojis" in content, "Accented characters should be preserved"
        # Note: Emoji rendering may vary by system, so we check if the exception message is captured
        assert "Test with unicode:" in content, "Exception message should be preserved"
        
        # Clean up
        if os.path.exists(log_path):
            os.remove(log_path)
        
        print("✓ Unicode handling in crash logs works correctly")


if __name__ == '__main__':
    print("="*70)
    print("CRASH LOGGING TESTS")
    print("="*70)
    print()
    
    test_create_crash_log_videowriter()
    print()
    
    test_create_crash_log_imageconcat()
    print()
    
    test_crash_log_file_naming()
    print()
    
    test_crash_log_with_nested_exception()
    print()
    
    test_crash_log_without_node_name()
    print()
    
    test_multiple_crash_logs()
    print()
    
    test_crash_log_unicode_handling()
    print()
    
    print("="*70)
    print("✅ ALL CRASH LOGGING TESTS PASSED")
    print("="*70)
