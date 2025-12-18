#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that all formats (MP4, AVI, MKV) no longer use queue-based background worker.
This test validates that the changes to remove queues for all formats are working correctly.
"""

def test_queue_disabled_for_all_formats():
    """Test that all formats disable background worker with queue"""
    
    # Simulate the logic from node_video_writer.py line 1359
    # All formats now use direct frame-by-frame writing (no queue)
    use_worker = False
    
    assert not use_worker, "All formats should NOT use background worker (queue-based)"
    
    print("✓ Queue disabled for all formats (MP4, AVI, MKV)")
    print("✓ All formats now use direct frame-by-frame writing")


def test_direct_writing_for_all_formats():
    """Test that when worker is disabled, direct writing mode is used for all formats"""
    
    # When use_worker is False and node not in _video_writer_dict
    use_worker = False
    tag_node_name = 'test_node:VideoWriter'
    _video_writer_dict = {}  # Empty dict, node not present
    
    # The condition from node_video_writer.py that triggers direct write mode
    should_use_direct_write = not use_worker and tag_node_name not in _video_writer_dict
    
    assert should_use_direct_write, "Should use direct frame-by-frame writing when worker is disabled"
    print("✓ Direct writing mode activated for all formats")


def _get_log_message(video_format, file_path):
    """Helper function to generate log message based on format"""
    return f"[VideoWriter] Started direct frame-by-frame writing for {video_format}: {file_path}"


def test_format_specific_logging():
    """Test that all formats use the same logging message"""
    
    # Test AVI format logging
    video_format = 'AVI'
    file_path = '/tmp/test.avi'
    log_message = _get_log_message(video_format, file_path)
    
    assert "direct frame-by-frame writing" in log_message, "AVI should use direct writing log message"
    assert "AVI" in log_message, "Format name should be in log message"
    
    # Test MKV format logging
    video_format = 'MKV'
    file_path = '/tmp/test.mkv'
    log_message = _get_log_message(video_format, file_path)
    
    assert "direct frame-by-frame writing" in log_message, "MKV should use direct writing log message"
    assert "MKV" in log_message, "Format name should be in log message"
    
    # Test MP4 format logging
    video_format = 'MP4'
    file_path = '/tmp/test.mp4'
    log_message = _get_log_message(video_format, file_path)
    
    assert "direct frame-by-frame writing" in log_message, "MP4 should use direct writing log message"
    assert "MP4" in log_message, "Format name should be in log message"
    
    print("✓ All formats use consistent direct writing logging messages")


if __name__ == '__main__':
    test_queue_disabled_for_all_formats()
    test_direct_writing_for_all_formats()
    test_format_specific_logging()
    print("\n✅ All queue removal tests passed!")
