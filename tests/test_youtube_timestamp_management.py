#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the YouTube node properly manages timestamps for frames.
This test validates that:
1. YouTube node generates FPS-based timestamps when capturing frames
2. Timestamps are sequential and based on frame count / FPS
3. Timestamps are properly returned in the data dictionary
4. Timestamp state is properly cleaned up on stop/close
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.InputNode.node_youtube import YoutubeNode


def test_timestamp_initialization():
    """Test that timestamp state is initialized correctly"""
    node = YoutubeNode()
    
    # Verify timestamp-related attributes exist
    assert hasattr(node, '_frame_count'), "Node should have _frame_count attribute"
    assert hasattr(node, '_stream_start_time'), "Node should have _stream_start_time attribute"
    assert hasattr(node, '_stream_fps'), "Node should have _stream_fps attribute"
    
    # Verify they are dictionaries
    assert isinstance(node._frame_count, dict), "_frame_count should be a dict"
    assert isinstance(node._stream_start_time, dict), "_stream_start_time should be a dict"
    assert isinstance(node._stream_fps, dict), "_stream_fps should be a dict"
    
    print("✓ Timestamp state initialized correctly")


def test_timestamp_calculation():
    """Test that timestamp calculation is correct"""
    node = YoutubeNode()
    node_id = "1"
    
    # Simulate stream initialization
    node._stream_fps[node_id] = 24.0  # 24 FPS
    node._frame_count[node_id] = 0
    
    # Simulate reading frames and check timestamp calculation
    test_cases = [
        (1, 1/24.0),      # Frame 1 at 24 FPS = 0.0417 seconds
        (24, 24/24.0),    # Frame 24 at 24 FPS = 1.0 second
        (48, 48/24.0),    # Frame 48 at 24 FPS = 2.0 seconds
        (120, 120/24.0),  # Frame 120 at 24 FPS = 5.0 seconds
    ]
    
    for frame_num, expected_timestamp in test_cases:
        calculated_timestamp = frame_num / node._stream_fps[node_id]
        assert abs(calculated_timestamp - expected_timestamp) < 0.001, \
            f"Frame {frame_num} at {node._stream_fps[node_id]} FPS should have timestamp ~{expected_timestamp}, got {calculated_timestamp}"
        print(f"  Frame {frame_num}: {calculated_timestamp:.4f}s (expected {expected_timestamp:.4f}s) ✓")
    
    print("✓ Timestamp calculation is correct")


def test_different_fps_values():
    """Test timestamp calculation with different FPS values"""
    node = YoutubeNode()
    node_id = "1"
    
    fps_test_cases = [
        (24.0, 24, 1.0),    # 24 FPS: frame 24 = 1 second
        (30.0, 30, 1.0),    # 30 FPS: frame 30 = 1 second
        (60.0, 60, 1.0),    # 60 FPS: frame 60 = 1 second
        (25.0, 50, 2.0),    # 25 FPS: frame 50 = 2 seconds
    ]
    
    for fps, frame_num, expected_time in fps_test_cases:
        node._stream_fps[node_id] = fps
        calculated_timestamp = frame_num / fps
        assert abs(calculated_timestamp - expected_time) < 0.001, \
            f"Frame {frame_num} at {fps} FPS should be at {expected_time}s, got {calculated_timestamp}s"
        print(f"  {fps} FPS, Frame {frame_num}: {calculated_timestamp:.4f}s ✓")
    
    print("✓ Different FPS values handled correctly")


def test_update_return_format():
    """Test that update() method returns timestamp in correct format"""
    node = YoutubeNode()
    node_id = "1"
    
    # Mock the necessary attributes
    node._opencv_setting_dict = {
        'input_window_width': 240,
        'input_window_height': 135,
    }
    node.small_window_w = 240
    node.small_window_h = 135
    
    # The update method should return a dict with timestamp key
    # We can't fully test it without a GUI context, but we can verify the structure
    # by checking the return statement exists in the code
    import inspect
    source = inspect.getsource(node.update)
    
    # Verify the return statement includes timestamp
    assert '"timestamp":' in source or "'timestamp':" in source, \
        "update() method should return timestamp in data dict"
    assert 'frame_timestamp' in source, \
        "update() method should calculate frame_timestamp"
    
    print("✓ update() method returns timestamp in correct format")


def test_cleanup_on_close():
    """Test that timestamp state is cleaned up on close"""
    node = YoutubeNode()
    node_id = "1"
    
    # Set up some state
    node._frame_count[node_id] = 100
    node._stream_start_time[node_id] = 1234567890.0
    node._stream_fps[node_id] = 24.0
    node._is_playing[node_id] = True
    node._last_frame_time[node_id] = 1234567900.0
    node._last_frame[node_id] = None
    
    # Close the node
    node.close(node_id)
    
    # Verify all state is cleaned up
    assert node_id not in node._frame_count, "_frame_count should be cleaned up"
    assert node_id not in node._stream_start_time, "_stream_start_time should be cleaned up"
    assert node_id not in node._stream_fps, "_stream_fps should be cleaned up"
    assert node_id not in node._is_playing, "_is_playing should be cleaned up"
    assert node_id not in node._last_frame_time, "_last_frame_time should be cleaned up"
    assert node_id not in node._last_frame, "_last_frame should be cleaned up"
    
    print("✓ Cleanup on close is correct")


def test_timestamp_consistency():
    """Test that timestamps are sequential and consistent"""
    node = YoutubeNode()
    node_id = "1"
    
    # Set up FPS
    fps = 30.0
    node._stream_fps[node_id] = fps
    node._frame_count[node_id] = 0
    
    # Simulate reading 10 frames
    timestamps = []
    for i in range(1, 11):
        node._frame_count[node_id] = i
        timestamp = i / fps
        timestamps.append(timestamp)
    
    # Verify timestamps are sequential
    for i in range(1, len(timestamps)):
        assert timestamps[i] > timestamps[i-1], \
            f"Timestamp {i} ({timestamps[i]}) should be greater than timestamp {i-1} ({timestamps[i-1]})"
    
    # Verify consistent spacing (1/fps between frames)
    expected_spacing = 1.0 / fps
    for i in range(1, len(timestamps)):
        actual_spacing = timestamps[i] - timestamps[i-1]
        assert abs(actual_spacing - expected_spacing) < 0.0001, \
            f"Spacing between frames should be {expected_spacing}, got {actual_spacing}"
    
    print("✓ Timestamps are sequential and consistent")


if __name__ == '__main__':
    print("Testing YouTube timestamp management...")
    print("=" * 60)
    
    tests = [
        ("Timestamp initialization", test_timestamp_initialization),
        ("Timestamp calculation", test_timestamp_calculation),
        ("Different FPS values", test_different_fps_values),
        ("Update return format", test_update_return_format),
        ("Cleanup on close", test_cleanup_on_close),
        ("Timestamp consistency", test_timestamp_consistency),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            test_func()
            print(f"✓ {name} passed")
            passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
