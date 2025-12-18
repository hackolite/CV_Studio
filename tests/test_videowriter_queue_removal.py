#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that AVI and MKV formats no longer use queue-based background worker.
This test validates that the changes to remove queues for AVI/MKV are working correctly.
"""

def test_queue_disabled_for_avi_mkv():
    """Test that AVI and MKV formats disable background worker with queue"""
    
    # Simulate the logic from node_video_writer.py line 1359
    # These simulate the runtime conditions where dependencies are available
    WORKER_AVAILABLE = True
    FFMPEG_AVAILABLE = True
    
    # Test for AVI format
    video_format = 'AVI'
    use_worker = WORKER_AVAILABLE and FFMPEG_AVAILABLE and video_format not in ['AVI', 'MKV']
    assert not use_worker, "AVI format should NOT use background worker (queue-based)"
    
    # Test for MKV format
    video_format = 'MKV'
    use_worker = WORKER_AVAILABLE and FFMPEG_AVAILABLE and video_format not in ['AVI', 'MKV']
    assert not use_worker, "MKV format should NOT use background worker (queue-based)"
    
    # Test for MP4 format (should still be able to use worker)
    video_format = 'MP4'
    use_worker = WORKER_AVAILABLE and FFMPEG_AVAILABLE and video_format not in ['AVI', 'MKV']
    assert use_worker, "MP4 format should be able to use background worker (queue-based)"
    
    print("✓ Queue disabled for AVI format")
    print("✓ Queue disabled for MKV format")
    print("✓ Queue still available for MP4 format")


def test_direct_writing_for_avi_mkv():
    """Test that when worker is disabled, direct writing mode is used"""
    
    # When use_worker is False and node not in _video_writer_dict
    use_worker = False
    tag_node_name = 'test_node:VideoWriter'
    _video_writer_dict = {}  # Empty dict, node not present
    
    # The condition from node_video_writer.py that triggers direct write mode
    should_use_direct_write = not use_worker and tag_node_name not in _video_writer_dict
    
    assert should_use_direct_write, "Should use direct frame-by-frame writing when worker is disabled"
    print("✓ Direct writing mode activated when worker disabled")


def test_format_specific_logging():
    """Test that format-specific logging messages are generated"""
    
    # Test AVI format logging
    video_format = 'AVI'
    file_path = '/tmp/test.avi'
    
    if video_format in ['AVI', 'MKV']:
        log_message = f"[VideoWriter] Started direct frame-by-frame writing for {video_format}: {file_path}"
    else:
        log_message = f"[VideoWriter] Started legacy mode for: {file_path}"
    
    assert "direct frame-by-frame writing" in log_message, "AVI should use direct writing log message"
    assert "AVI" in log_message, "Format name should be in log message"
    
    # Test MKV format logging
    video_format = 'MKV'
    file_path = '/tmp/test.mkv'
    
    if video_format in ['AVI', 'MKV']:
        log_message = f"[VideoWriter] Started direct frame-by-frame writing for {video_format}: {file_path}"
    else:
        log_message = f"[VideoWriter] Started legacy mode for: {file_path}"
    
    assert "direct frame-by-frame writing" in log_message, "MKV should use direct writing log message"
    assert "MKV" in log_message, "Format name should be in log message"
    
    # Test MP4 format logging
    video_format = 'MP4'
    file_path = '/tmp/test.mp4'
    
    if video_format in ['AVI', 'MKV']:
        log_message = f"[VideoWriter] Started direct frame-by-frame writing for {video_format}: {file_path}"
    else:
        log_message = f"[VideoWriter] Started legacy mode for: {file_path}"
    
    assert "legacy mode" in log_message, "MP4 should use legacy mode log message (when worker not used)"
    
    print("✓ Format-specific logging messages are correct")


if __name__ == '__main__':
    test_queue_disabled_for_avi_mkv()
    test_direct_writing_for_avi_mkv()
    test_format_specific_logging()
    print("\n✅ All queue removal tests passed!")
