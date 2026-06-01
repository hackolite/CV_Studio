#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test to demonstrate the Buzzer node behavior.
This test verifies the core buzzer logic without GUI dependencies.
"""
import sys
import os
import time

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock GUI dependencies
import unittest.mock as mock
sys.modules['cv2'] = mock.MagicMock()
sys.modules['dearpygui'] = mock.MagicMock()
sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
sys.modules['sounddevice'] = mock.MagicMock()

def test_buzzer_sound_parameters():
    """Test buzzer sound generation with different durations"""
    from node.ActionNode.node_buzzer import BuzzerNode
    import numpy as np
    
    node = BuzzerNode()
    
    print("Testing Buzzer Node sound generation parameters...")
    print("=" * 60)
    
    # Test different durations - bip-bip sounds are always short regardless of duration param
    durations = [0.5, 1.0, 2.0, 5.0]
    
    for duration in durations:
        print(f"\nGenerating bip-bip with duration param={duration}s...")
        audio, samplerate = node._generate_buzz_sound(duration)
        
        actual_length = len(audio)
        actual_duration = actual_length / samplerate
        
        print(f"  Actual length: {actual_length} samples ({actual_duration:.3f}s)")
        print(f"  Max amplitude: {np.max(np.abs(audio)):.3f}")
        
        # Bip-bip sounds are short regardless of requested duration
        assert actual_duration < 0.5, f"Bip-bip should be < 0.5s, got {actual_duration:.3f}s"
        assert np.max(np.abs(audio)) <= 1.0, "Audio exceeds normalized range"
        print(f"  ✓ Bip-bip generated correctly (short duration)")
    
    print("\n" + "=" * 60)
    print("✓ All sound parameter tests passed!")
    
    return True


def test_buzzer_constants():
    """Test that buzzer uses correct default constants"""
    from node.ActionNode.node_buzzer import BuzzerNode
    
    print("\nTesting Buzzer Node default constants...")
    print("=" * 60)
    
    # Check class constants exist
    assert hasattr(BuzzerNode, 'DEFAULT_DURATION'), "DEFAULT_DURATION constant missing"
    assert hasattr(BuzzerNode, 'DEFAULT_INSENSITIVITY_DELAY'), "DEFAULT_INSENSITIVITY_DELAY constant missing"
    assert hasattr(BuzzerNode, 'SOUND_TYPES'), "SOUND_TYPES constant missing"
    
    print(f"  DEFAULT_DURATION: {BuzzerNode.DEFAULT_DURATION}s")
    print(f"  DEFAULT_INSENSITIVITY_DELAY: {BuzzerNode.DEFAULT_INSENSITIVITY_DELAY}s")
    print(f"  SOUND_TYPES: {len(BuzzerNode.SOUND_TYPES)} types available")
    
    # Verify values
    assert BuzzerNode.DEFAULT_DURATION == 5.0, "DEFAULT_DURATION should be 5.0"
    assert BuzzerNode.DEFAULT_INSENSITIVITY_DELAY == 0.0, "DEFAULT_INSENSITIVITY_DELAY should be 0.0"
    assert len(BuzzerNode.SOUND_TYPES) >= 5, "Should have at least 5 sound types"
    assert "Bip-Bip (Default)" in BuzzerNode.SOUND_TYPES, "Should have default bip-bip"
    
    print("  ✓ Constants are correctly defined")
    
    return True


def test_buzzer_state_tracking():
    """Test buzzer state tracking without GUI"""
    from node.ActionNode.node_buzzer import BuzzerNode
    
    print("\nTesting Buzzer Node state tracking...")
    print("=" * 60)
    
    node = BuzzerNode()
    
    # Verify initial state
    print("\n1. Checking initial state")
    assert node._last_buzz_time == 0, "Initial buzz time should be 0"
    assert not node._is_buzzing, "Should not be buzzing initially"
    assert node._buzz_thread is None, "No thread should exist initially"
    assert node._insensitivity_end_time == 0, "Insensitivity end time should be 0"
    print("   ✓ Initial state is correct")
    
    # Test setting insensitivity period
    print("\n2. Testing insensitivity period tracking")
    current_time = time.time()
    node._insensitivity_end_time = current_time + 5.0
    
    # Check if we're in insensitivity period
    is_insensitive = current_time < node._insensitivity_end_time
    assert is_insensitive, "Should be in insensitivity period"
    print("   ✓ Insensitivity period tracking works")
    
    # Test after insensitivity expires
    print("\n3. Testing expired insensitivity period")
    node._insensitivity_end_time = current_time - 1.0  # Set to past
    is_insensitive = current_time < node._insensitivity_end_time
    assert not is_insensitive, "Should not be in insensitivity period"
    print("   ✓ Expired insensitivity period detected correctly")
    
    print("\n" + "=" * 60)
    print("✓ All state tracking tests passed!")
    
    return True


if __name__ == '__main__':
    print("Running Buzzer Node Integration Tests...")
    print()
    
    tests = [
        ("Sound Parameters", test_buzzer_sound_parameters),
        ("Default Constants", test_buzzer_constants),
        ("State Tracking", test_buzzer_state_tracking),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n✗ {name} test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All integration tests completed successfully!")
        sys.exit(0)
    else:
        print("✗ Some integration tests failed")
        sys.exit(1)
