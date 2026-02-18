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
    assert "Default Buzzer" in sound_types, "Should include Default Buzzer"
    assert "Airplane Seatbelt Chime" in sound_types, "Should include Airplane Seatbelt Chime"
    assert "Gentle Beep" in sound_types, "Should include Gentle Beep"
    assert "Soft Chime" in sound_types, "Should include Soft Chime"
    assert "Ambient Tone" in sound_types, "Should include Ambient Tone"
    
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
        assert len(audio) == int(samplerate * 1.0), f"Audio length should match duration for {sound_type}"
        assert audio.dtype == np.float64, f"Audio should be float64 for {sound_type}"
        
        # Verify audio is normalized (amplitude <= 1.0)
        max_amplitude = np.max(np.abs(audio))
        assert max_amplitude <= 1.0, f"Audio amplitude should be normalized for {sound_type}, got {max_amplitude}"
        
        # Verify audio is not all zeros (actually has sound)
        assert max_amplitude > 0.0, f"Audio should have non-zero values for {sound_type}"
        
        print(f"    ✓ Max amplitude: {max_amplitude:.3f}")
    
    print(f"\n✓ Successfully tested {len(BuzzerNode.SOUND_TYPES)} sound types")
    
    return True


def test_airplane_seatbelt_chime_characteristics():
    """Test that airplane seatbelt chime has expected characteristics"""
    print("\nTesting airplane seatbelt chime characteristics...")
    
    # Mock dependencies
    import unittest.mock as mock
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['sounddevice'] = mock.MagicMock()
    
    from node.ActionNode.node_buzzer import BuzzerNode
    
    node = BuzzerNode()
    
    # Generate airplane seatbelt chime
    audio, samplerate = node._generate_buzz_sound(
        duration=2.0, 
        sound_type="Airplane Seatbelt Chime"
    )
    
    # The airplane chime should be a two-tone sound (ding-dong)
    # It should have lower amplitude (non-stressful) compared to default buzzer
    max_amplitude = np.max(np.abs(audio))
    
    print(f"  Amplitude: {max_amplitude:.3f}")
    print(f"  Duration: {len(audio) / samplerate:.1f}s")
    print(f"  Sample rate: {samplerate} Hz")
    
    # Verify it's not too loud (non-stressful)
    assert max_amplitude <= 0.6, "Airplane chime should be gentle (amplitude <= 0.6)"
    assert max_amplitude > 0.0, "Airplane chime should have sound"
    
    print("✓ Airplane seatbelt chime has appropriate characteristics")
    
    return True


if __name__ == '__main__':
    print("Testing Buzzer Sound Types...")
    print("=" * 60)
    
    tests = [
        ("Sound Types Available", test_sound_types_available),
        ("Sound Generation for Each Type", test_sound_generation_for_each_type),
        ("Airplane Seatbelt Chime Characteristics", test_airplane_seatbelt_chime_characteristics),
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
