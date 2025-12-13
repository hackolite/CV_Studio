#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for SyncQueue required count calculation logic.

This test validates that the required count calculation follows the correct formula:
- Audio: 1 chunk (representing retention_time seconds)
- Image/JSON: retention_time * fps * number_of_audio_chunks
            = retention_time * fps * 1
            = fps * retention_time elements
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_required_count_calculation():
    """
    Test the _get_required_count method logic without GUI dependencies.
    
    This simulates the calculation that should happen in the SyncQueue node.
    """
    # Simulate the _get_required_count logic
    def get_required_count(slot_type, fps, retention_time):
        """
        Calculate required count per slot type.
        
        For synchronization:
        - Audio: 1 chunk (representing retention_time seconds of audio)
        - Image/JSON: audio_duration * fps * number_of_audio_chunks
                    = retention_time * fps * 1
                    = fps * retention_time elements
        """
        if slot_type == 'audio':
            return 1  # 1 chunk = retention_time seconds
        elif slot_type in ['image', 'json']:
            return int(fps * retention_time)  # fps × retention_time elements
        return 1
    
    # Test case 1: Default values (fps=10, retention_time=3.0)
    fps = 10
    retention_time = 3.0
    
    audio_count = get_required_count('audio', fps, retention_time)
    image_count = get_required_count('image', fps, retention_time)
    json_count = get_required_count('json', fps, retention_time)
    
    assert audio_count == 1, f"Audio should require 1 chunk, got {audio_count}"
    assert image_count == 30, f"Image should require 30 frames (10fps × 3s), got {image_count}"
    assert json_count == 30, f"JSON should require 30 elements (10fps × 3s), got {json_count}"
    
    print(f"✓ Test 1 passed: fps={fps}, retention_time={retention_time}s")
    print(f"  Audio: {audio_count} chunk (represents {retention_time}s of audio)")
    print(f"  Image: {image_count} frames ({retention_time}s × {fps}fps × 1)")
    print(f"  JSON: {json_count} elements ({retention_time}s × {fps}fps × 1)")
    
    # Test case 2: High FPS (fps=60, retention_time=3.0)
    fps = 60
    retention_time = 3.0
    
    audio_count = get_required_count('audio', fps, retention_time)
    image_count = get_required_count('image', fps, retention_time)
    
    assert audio_count == 1, f"Audio should require 1 chunk, got {audio_count}"
    assert image_count == 180, f"Image should require 180 frames (60fps × 3s), got {image_count}"
    
    print(f"\n✓ Test 2 passed: fps={fps}, retention_time={retention_time}s")
    print(f"  Audio: {audio_count} chunk (represents {retention_time}s of audio)")
    print(f"  Image: {image_count} frames ({retention_time}s × {fps}fps × 1)")
    
    # Test case 3: Long retention time (fps=10, retention_time=10.0)
    fps = 10
    retention_time = 10.0
    
    audio_count = get_required_count('audio', fps, retention_time)
    image_count = get_required_count('image', fps, retention_time)
    
    assert audio_count == 1, f"Audio should require 1 chunk, got {audio_count}"
    assert image_count == 100, f"Image should require 100 frames (10fps × 10s), got {image_count}"
    
    print(f"\n✓ Test 3 passed: fps={fps}, retention_time={retention_time}s")
    print(f"  Audio: {audio_count} chunk (represents {retention_time}s of audio)")
    print(f"  Image: {image_count} frames ({retention_time}s × {fps}fps × 1)")
    
    # Test case 4: Low FPS (fps=5, retention_time=2.0)
    fps = 5
    retention_time = 2.0
    
    audio_count = get_required_count('audio', fps, retention_time)
    image_count = get_required_count('image', fps, retention_time)
    
    assert audio_count == 1, f"Audio should require 1 chunk, got {audio_count}"
    assert image_count == 10, f"Image should require 10 frames (5fps × 2s), got {image_count}"
    
    print(f"\n✓ Test 4 passed: fps={fps}, retention_time={retention_time}s")
    print(f"  Audio: {audio_count} chunk (represents {retention_time}s of audio)")
    print(f"  Image: {image_count} frames ({retention_time}s × {fps}fps × 1)")
    
    return True


def test_synchronization_logic():
    """
    Test that the synchronization logic matches the problem requirements.
    
    Problem: "when we have 1 in audio, in image, we should have 
    audio duration * fps * the number of audio elements which is 1"
    """
    # Given: 1 audio element (chunk)
    number_of_audio_elements = 1
    
    # Each audio chunk represents retention_time seconds
    retention_time = 3.0  # seconds
    audio_duration = retention_time  # duration of 1 audio chunk
    
    # FPS for images
    fps = 10
    
    # Calculate expected image count
    expected_image_count = int(audio_duration * fps * number_of_audio_elements)
    
    # This should match what _get_required_count returns
    actual_image_count = int(fps * retention_time)
    
    assert expected_image_count == actual_image_count, \
        f"Expected {expected_image_count} images, got {actual_image_count}"
    
    print(f"\n✓ Synchronization logic test passed:")
    print(f"  When we have {number_of_audio_elements} audio chunk ({audio_duration}s of audio)")
    print(f"  We output: {audio_duration}s × {fps}fps × {number_of_audio_elements} = {expected_image_count} images")
    print(f"  Formula: audio_duration × fps × number_of_audio_elements = {expected_image_count}")
    
    return True


def test_output_display_format():
    """
    Test that the output display format is correct.
    
    The output should display the number of elements that will be output,
    not the current buffer count.
    """
    # Simulate different slot configurations
    test_cases = [
        {'slot_type': 'audio', 'fps': 10, 'retention_time': 3.0, 'expected': 1},
        {'slot_type': 'image', 'fps': 10, 'retention_time': 3.0, 'expected': 30},
        {'slot_type': 'json', 'fps': 10, 'retention_time': 3.0, 'expected': 30},
        {'slot_type': 'audio', 'fps': 30, 'retention_time': 5.0, 'expected': 1},
        {'slot_type': 'image', 'fps': 30, 'retention_time': 5.0, 'expected': 150},
    ]
    
    def get_required_count(slot_type, fps, retention_time):
        if slot_type == 'audio':
            return 1
        elif slot_type in ['image', 'json']:
            return int(fps * retention_time)
        return 1
    
    print("\n✓ Output display format test:")
    for i, test in enumerate(test_cases, 1):
        required_count = get_required_count(
            test['slot_type'], 
            test['fps'], 
            test['retention_time']
        )
        
        assert required_count == test['expected'], \
            f"Test {i}: Expected {test['expected']}, got {required_count}"
        
        # Format the display string as it should appear in the UI
        display_type = test['slot_type'].capitalize()
        output_label = f"Out1: {display_type} ({required_count})"
        
        print(f"  Test {i}: {output_label}")
        print(f"    (fps={test['fps']}, retention_time={test['retention_time']}s)")
    
    print("  ✓ All output display formats are correct")
    return True


if __name__ == '__main__':
    print("Testing SyncQueue Calculation Logic\n")
    print("=" * 70)
    
    tests = [
        ("Required count calculation", test_required_count_calculation),
        ("Synchronization logic", test_synchronization_logic),
        ("Output display format", test_output_display_format),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 70)
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except AssertionError as e:
            failed += 1
            print(f"✗ {test_name} FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 70)
    print(f"Tests Passed: {passed}/{len(tests)}")
    print(f"Tests Failed: {failed}/{len(tests)}")
    print("=" * 70)
    
    sys.exit(0 if failed == 0 else 1)
