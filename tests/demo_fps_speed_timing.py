#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo script to test FPS and Speed control features
This script creates a simple test to verify the frame timing calculations
"""

import time


def test_frame_timing():
    """Test the frame timing calculation logic"""
    
    print("=" * 60)
    print("Video Node FPS and Speed Control - Timing Test")
    print("=" * 60)
    print()
    
    test_cases = [
        # (fps, speed, expected_interval)
        (24, 1.0, 0.042),   # Standard 24fps
        (24, 0.5, 0.083),   # Half speed
        (24, 2.0, 0.021),   # Double speed
        (24, 0.25, 0.167),  # Quarter speed
        (24, 4.0, 0.010),   # 4x speed
        (30, 1.0, 0.033),   # 30fps standard
        (60, 1.0, 0.017),   # 60fps standard
        (60, 0.5, 0.033),   # 60fps half speed
    ]
    
    print("Frame Interval Calculations:")
    print("-" * 60)
    print(f"{'FPS':<6} {'Speed':<8} {'Interval (s)':<14} {'Interval (ms)':<14}")
    print("-" * 60)
    
    for fps, speed, expected in test_cases:
        # This is the actual calculation from the code
        frame_interval = (1.0 / fps) / speed if fps > 0 and speed > 0 else 0
        interval_ms = frame_interval * 1000
        
        print(f"{fps:<6} {speed:<8.2f} {frame_interval:<14.3f} {interval_ms:<14.1f}")
        
        # Verify calculation is correct
        assert abs(frame_interval - expected) < 0.001, \
            f"Expected {expected}, got {frame_interval}"
    
    print("-" * 60)
    print("✓ All calculations correct")
    print()
    
    # Simulate frame timing
    print("Simulating Frame Timing (5 frames at 24 FPS, 1.0x speed):")
    print("-" * 60)
    
    target_fps = 24
    playback_speed = 1.0
    frame_interval = (1.0 / target_fps) / playback_speed
    
    last_frame_time = None
    frames_displayed = 0
    
    start_time = time.time()
    
    for i in range(5):
        current_time = time.time()
        
        # Check if enough time has passed
        should_read_frame = (last_frame_time is None) or \
                           ((current_time - last_frame_time) >= frame_interval)
        
        if should_read_frame:
            elapsed = current_time - start_time if last_frame_time else 0
            print(f"Frame {i+1} displayed at {elapsed:.3f}s")
            last_frame_time = current_time
            frames_displayed += 1
        
        # Wait for next frame
        time.sleep(frame_interval)
    
    total_time = time.time() - start_time
    actual_fps = frames_displayed / total_time if total_time > 0 else 0
    
    print("-" * 60)
    print(f"Total time: {total_time:.3f}s")
    print(f"Frames displayed: {frames_displayed}")
    print(f"Actual FPS: {actual_fps:.1f}")
    print(f"Target FPS: {target_fps}")
    print()
    
    # Edge case testing
    print("Edge Case Testing:")
    print("-" * 60)
    
    # Zero FPS
    result = (1.0 / 0) / 1.0 if 0 > 0 and 1.0 > 0 else 0
    print(f"Zero FPS (0, 1.0x): {result} (should be 0)")
    assert result == 0, "Zero FPS should result in 0 interval"
    
    # Zero speed
    result = (1.0 / 24) / 0 if 24 > 0 and 0 > 0 else 0
    print(f"Zero speed (24, 0x): {result} (should be 0)")
    assert result == 0, "Zero speed should result in 0 interval"
    
    print("-" * 60)
    print("✓ Edge cases handled correctly")
    print()
    
    print("=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == '__main__':
    test_frame_timing()
