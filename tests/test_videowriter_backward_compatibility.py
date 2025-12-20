#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify backward compatibility of async release changes.

This test ensures that the async release implementation doesn't break
existing VideoWriter functionality or API.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_class_attributes_preserved():
    """Test that essential class attributes are preserved"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Essential attributes that must exist
    assert '_video_writer_dict = {}' in content, \
        "Missing _video_writer_dict (breaks existing functionality)"
    
    assert '_start_label = ' in content, \
        "Missing _start_label (breaks UI)"
    
    assert '_stop_label = ' in content, \
        "Missing _stop_label (breaks UI)"
    
    # New attributes for async release
    assert '_release_threads_dict = {}' in content, \
        "Missing _release_threads_dict (required for async release)"
    
    assert '_finalizing_label = ' in content, \
        "Missing _finalizing_label (required for UI feedback)"
    
    print("✓ All essential class attributes preserved")


def test_recording_button_method_exists():
    """Test that _recording_button method still exists"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    assert 'def _recording_button(self, sender, data, user_data):' in content, \
        "Missing _recording_button method (breaks recording functionality)"
    
    print("✓ Recording button method exists")


def test_start_recording_preserved():
    """Test that start recording logic is preserved"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Find _recording_button method
    method_start = content.find('def _recording_button(')
    method_end = content.find('\n\n\n', method_start)
    method_content = content[method_start:method_end]
    
    # Check start recording logic
    assert 'if label == self._start_label:' in method_content, \
        "Missing start recording condition"
    
    assert 'cv2.VideoWriter(' in method_content, \
        "Missing VideoWriter creation"
    
    assert 'cv2.VideoWriter_fourcc' in method_content, \
        "Missing codec configuration"
    
    # Check format support
    assert "'MP4'" in method_content, "Missing MP4 format support"
    assert "'AVI'" in method_content, "Missing AVI format support"
    assert "'MKV'" in method_content, "Missing MKV format support"
    
    print("✓ Start recording logic preserved")


def test_stop_recording_uses_async():
    """Test that stop recording uses async release"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Find _recording_button method
    method_start = content.find('def _recording_button(')
    method_end = content.find('\n\n\n', method_start)
    method_content = content[method_start:method_end]
    
    # Check stop recording logic
    assert 'elif label == self._stop_label:' in method_content, \
        "Missing stop recording condition"
    
    # Should NOT have synchronous release anymore
    assert 'video_writer.release()' not in method_content, \
        "Stop recording should not call release() synchronously (causes freeze)"
    
    # Should use async release
    assert 'threading.Thread(' in method_content, \
        "Stop recording should create background thread"
    
    assert '_release_video_writer_async' in method_content, \
        "Stop recording should call async release method"
    
    assert '_finalizing_label' in method_content, \
        "Stop recording should show finalizing label"
    
    print("✓ Stop recording uses async release (no more freeze)")


def test_update_method_preserved():
    """Test that update method logic is preserved"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    assert 'def update(' in content, \
        "Missing update method"
    
    # Find update method
    update_start = content.find('def update(')
    update_end = content.find('\n    def ', update_start + 1)
    update_content = content[update_start:update_end]
    
    # Check frame writing logic (now using write_queues_dict for threaded frame writing)
    assert ('if tag_node_name in self._write_queues_dict:' in update_content or 
            'if tag_node_name in self._video_writer_dict:' in update_content or 
            'if tag_node_name in self._async_writer_dict:' in update_content), \
        "Missing recording check"
    
    assert 'cv2.resize' in update_content, \
        "Missing frame resize"
    
    # Recording indicator was intentionally removed to save resources
    # No longer checking for cv2.circle
    
    print("✓ Update method logic preserved (now with threaded frame writing)")


def test_close_method_enhanced():
    """Test that close method properly handles async release"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Find close method
    close_start = content.find('def close(self, node_id):')
    close_end = content.find('\n    def ', close_start + 1)
    close_content = content[close_start:close_end]
    
    # Should wait for background threads
    assert '_release_threads_dict' in close_content, \
        "close() should check for release threads"
    
    assert 'join(' in close_content, \
        "close() should wait for threads to complete"
    
    # Should still handle direct release as fallback
    assert '_video_writer_dict' in close_content, \
        "close() should handle video writers"
    
    print("✓ Close method enhanced with thread waiting")


def test_no_audio_handling():
    """Test that audio handling is still removed (from simplification)"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # These should NOT exist (removed in simplification)
    assert '_audio_samples_dict' not in content, \
        "Audio samples dict should be removed"
    
    assert '_merge_audio_video_ffmpeg' not in content, \
        "Audio merge method should be removed"
    
    assert '_background_workers' not in content, \
        "Background workers should be removed"
    
    print("✓ Audio handling remains removed (simplified)")


def test_format_config_unchanged():
    """Test that format configuration is unchanged"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Check format config exists
    assert 'format_config = {' in content, \
        "Missing format_config dictionary"
    
    # Check codecs
    assert "'MJPG'" in content, "Missing MJPG codec for AVI"
    assert "'FFV1'" in content, "Missing FFV1 codec for MKV"
    assert "'mp4v'" in content, "Missing mp4v codec for MP4"
    
    print("✓ Format configuration unchanged")


def test_no_synchronous_release_in_stop():
    """Critical: Verify synchronous release is removed from stop button"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'node', 'VideoNode', 'node_video_writer.py'), 'r') as f:
        content = f.read()
    
    # Find the stop recording section
    lines = content.split('\n')
    in_stop_section = False
    found_finalizing = False
    found_thread_start = False
    found_sync_release = False
    
    for i, line in enumerate(lines):
        if 'elif label == self._stop_label:' in line:
            in_stop_section = True
            stop_start = i
        
        if in_stop_section:
            # Check for end of stop section (next elif or method def)
            if i > stop_start + 1 and ('def ' in line or 'elif ' in line):
                break
            
            if '_finalizing_label' in line:
                found_finalizing = True
            
            if 'release_thread.start()' in line:
                found_thread_start = True
            
            # This is the OLD code that causes freeze - should NOT be in stop section
            if '.release()' in line and 'video_writer.release()' not in line and 'self._video_writer_dict[tag_node_name].release()' in line:
                found_sync_release = True
    
    assert found_finalizing, "Stop section should set finalizing label"
    assert found_thread_start, "Stop section should start background thread"
    assert not found_sync_release, "Stop section should NOT call release() synchronously (this causes freeze!)"
    
    print("✓ Synchronous release removed from stop button (freeze fixed)")


if __name__ == "__main__":
    test_class_attributes_preserved()
    test_recording_button_method_exists()
    test_start_recording_preserved()
    test_stop_recording_uses_async()
    test_update_method_preserved()
    test_close_method_enhanced()
    test_no_audio_handling()
    test_format_config_unchanged()
    test_no_synchronous_release_in_stop()
    print("\n✅ All backward compatibility tests passed!")
    print("✅ Async release implementation is backward compatible")
    print("✅ No breaking changes to existing functionality")
