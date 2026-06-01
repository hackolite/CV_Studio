#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the Buzzer node supports multiple sound types.
This test focuses on sound generation without GUI dependencies.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_sound_types_available():
    """Test that multiple sound types are available"""
    # Mock all GUI and CV dependencies before importing
    import unittest.mock as mock
    
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['sounddevice'] = mock.MagicMock()
    
    # Import just the class definition without GUI
    import importlib.util
    buzzer_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'ActionNode', 
        'node_buzzer.py'
    )
    spec = importlib.util.spec_from_file_location(
        "node_buzzer",
        buzzer_path
    )
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    BuzzerNode = module.BuzzerNode
    
    # Verify SOUND_TYPES exist
    assert hasattr(BuzzerNode, 'SOUND_TYPES'), "BuzzerNode should have SOUND_TYPES"
    sound_types = BuzzerNode.SOUND_TYPES
    
    print(f"✓ Found {len(sound_types)} sound types")
    
    # Verify required sound types
    assert len(sound_types) >= 5, "Should have at least 5 sound types"
    assert "Bip-Bip (Default)" in sound_types, "Should include Bip-Bip (Default)"
    assert "Bip-Bip (High)" in sound_types, "Should include Bip-Bip (High)"
    assert "Bip-Bip (Low)" in sound_types, "Should include Bip-Bip (Low)"
    assert "Bip-Bip (Double)" in sound_types, "Should include Bip-Bip (Double)"
    assert "Bip-Bip (Triple)" in sound_types, "Should include Bip-Bip (Triple)"
    
    print("  Available sound types:")
    for sound_type in sound_types:
        print(f"    - {sound_type}")
    
    print("✓ All required sound types are present")
    
    return True


def test_sound_generation_for_each_type():
    """Test sound generation for each type"""
    print("\nTesting sound generation for each type...")
    
    # Mock the GUI dependencies
    import unittest.mock as mock
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    
    # Create a mock for sounddevice that won't try to use audio hardware
    mock_sd = mock.MagicMock()
    sys.modules['sounddevice'] = mock_sd
    
    # Now import the module
    from node.ActionNode.node_buzzer import BuzzerNode
    
    node = BuzzerNode()
    
    # Test each sound type
    for sound_type in BuzzerNode.SOUND_TYPES:
        print(f"  Testing: {sound_type}")
        
        # Generate sound
        audio, samplerate = node._generate_buzz_sound(duration=1.0, sound_type=sound_type)
        
        # Verify audio properties
        assert isinstance(audio, np.ndarray), f"Audio should be numpy array for {sound_type}"
        assert samplerate == 44100, f"Sample rate should be 44100 for {sound_type}"
        # Bip-bip sounds are short (< 0.5s) regardless of requested duration
        assert len(audio) > 0, f"Audio should have samples for {sound_type}"
        assert len(audio) < int(samplerate * 0.6), f"Bip-bip should be short (< 0.6s) for {sound_type}"
        assert audio.dtype == np.float64, f"Audio should be float64 for {sound_type}"
        
        # Verify audio is normalized (amplitude <= 1.0)
        max_amplitude = np.max(np.abs(audio))
        assert max_amplitude <= 1.0, f"Audio amplitude should be normalized for {sound_type}, got {max_amplitude}"
        
        # Verify audio is not all zeros (actually has sound)
        assert max_amplitude > 0.0, f"Audio should have non-zero values for {sound_type}"
        
        print(f"    ✓ Max amplitude: {max_amplitude:.3f}")
    
    print(f"\n✓ Successfully tested {len(BuzzerNode.SOUND_TYPES)} sound types")
    
    return True


def test_bip_bip_short_duration():
    """Test that bip-bip sounds are short to release lock quickly"""
    print("\nTesting bip-bip short duration...")
    
    # Mock dependencies
    import unittest.mock as mock
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['sounddevice'] = mock.MagicMock()
    
    from node.ActionNode.node_buzzer import BuzzerNode
    
    node = BuzzerNode()
    
    # Generate each bip-bip type with a long requested duration
    for sound_type in BuzzerNode.SOUND_TYPES:
        audio, samplerate = node._generate_buzz_sound(
            duration=10.0,  # Request 10s but bip-bip should be much shorter
            sound_type=sound_type
        )
        
        actual_duration = len(audio) / samplerate
        max_amplitude = np.max(np.abs(audio))
        
        print(f"  {sound_type}: {actual_duration:.3f}s, amp={max_amplitude:.3f}")
        
        # All bip-bip sounds should be < 0.5s actual audio
        assert actual_duration < 0.5, (
            f"{sound_type} should be < 0.5s, got {actual_duration:.3f}s"
        )
        # Should have audible content
        assert max_amplitude > 0.2, f"{sound_type} should be audible"
        assert max_amplitude <= 0.5, f"{sound_type} should not be too loud"
    
    print("✓ All bip-bip sounds are short (< 0.5s)")
    
    return True


if __name__ == '__main__':
    print("Testing Buzzer Sound Types...")
    print("=" * 60)
    
    tests = [
        ("Sound Types Available", test_sound_types_available),
        ("Sound Generation for Each Type", test_sound_generation_for_each_type),
        ("Bip-Bip Short Duration", test_bip_bip_short_duration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} test failed: {e}")
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
