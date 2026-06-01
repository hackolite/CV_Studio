#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the Buzzer node structure is correct.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_buzzer_node_structure():
    """Test that Buzzer node has correct structure"""
    from node.ActionNode.node_buzzer import FactoryNode, BuzzerNode
    
    factory = FactoryNode()
    node = BuzzerNode()
    
    print("✓ Buzzer Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  Node.node_label: {node.node_label}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    print(f"  FactoryNode.node_label: {factory.node_label}")
    
    # Verify attributes
    assert node.node_tag == "Buzzer", "Node tag should be 'Buzzer'"
    assert node.node_label == "Buzzer", "Node label should be 'Buzzer'"
    assert factory.node_tag == "Buzzer", "Factory tag should be 'Buzzer'"
    assert factory.node_label == "Buzzer", "Factory label should be 'Buzzer'"
    
    # Verify sound types are defined
    assert hasattr(BuzzerNode, 'SOUND_TYPES'), "BuzzerNode should have SOUND_TYPES"
    assert len(BuzzerNode.SOUND_TYPES) >= 5, "Should have at least 5 sound types"
    assert "Bip-Bip (Default)" in BuzzerNode.SOUND_TYPES, "Should include default bip-bip"
    print(f"  Sound types available: {len(BuzzerNode.SOUND_TYPES)}")
    for sound_type in BuzzerNode.SOUND_TYPES:
        print(f"    - {sound_type}")
    
    # Verify methods exist
    assert hasattr(node, 'update'), "Node should have 'update' method"
    assert hasattr(node, 'close'), "Node should have 'close' method"
    assert hasattr(node, 'get_setting_dict'), "Node should have 'get_setting_dict' method"
    assert hasattr(node, 'set_setting_dict'), "Node should have 'set_setting_dict' method"
    assert hasattr(factory, 'add_node'), "Factory should have 'add_node' method"
    
    # Verify internal methods
    assert hasattr(node, '_generate_buzz_sound'), "Node should have '_generate_buzz_sound' method"
    assert hasattr(node, '_play_buzz_thread'), "Node should have '_play_buzz_thread' method"
    
    print("✓ All methods exist")
    
    return True


def test_buzzer_sound_generation():
    """Test that buzzer sound generation works"""
    from node.ActionNode.node_buzzer import BuzzerNode
    import numpy as np
    
    node = BuzzerNode()
    
    # Test all sound types
    for sound_type in BuzzerNode.SOUND_TYPES:
        print(f"  Testing sound type: {sound_type}")
        audio, samplerate = node._generate_buzz_sound(duration=1.0, sound_type=sound_type)
        
        # Verify audio properties
        assert isinstance(audio, np.ndarray), f"Audio should be numpy array for {sound_type}"
        assert samplerate == 44100, f"Sample rate should be 44100 for {sound_type}"
        # Bip-bip sounds are intentionally short (< 0.5s) for quick lock release
        assert len(audio) > 0, f"Audio should have samples for {sound_type}"
        assert len(audio) < int(samplerate * 0.6), f"Bip-bip should be short for {sound_type}"
        assert audio.dtype == np.float64, f"Audio should be float64 for {sound_type}"
        assert np.max(np.abs(audio)) <= 1.0, f"Audio amplitude should be normalized for {sound_type}"
    
    print("✓ Sound generation successful for all types")
    print(f"  Sample rate: {samplerate}")
    print(f"  Audio array length: {len(audio)}")
    print(f"  Expected length: {int(samplerate * 1.0)}")
    print(f"  Tested {len(BuzzerNode.SOUND_TYPES)} sound types")
    
    print("✓ Audio properties verified")
    
    return True


if __name__ == '__main__':
    print("Testing Buzzer Node...")
    print("=" * 60)
    
    tests = [
        ("Buzzer Node Structure", test_buzzer_node_structure),
        ("Buzzer Sound Generation", test_buzzer_sound_generation),
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
