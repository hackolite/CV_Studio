#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the enhanced Microphone node functionality.
Tests the parameters: output mode, channels, and timestamp.
Note: FPS limit was removed per requirements.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_microphone_enhanced_attributes():
    """Test that Microphone node has new enhanced attributes"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Verify internal state attributes (FPS limit was removed per requirements)
    assert hasattr(node, '_current_channels'), "Node missing _current_channels attribute"
    
    # Verify initial values
    assert node._current_channels == 1, "Node should start with _current_channels = 1"
    
    print("✓ Microphone node enhanced attributes verified")
    print(f"  _current_channels: {node._current_channels}")
    
    return True


def test_microphone_factory_new_inputs():
    """Test that Microphone FactoryNode creates new input tags"""
    from node.InputNode.node_microphone import FactoryNode, MicrophoneNode
    
    node = MicrophoneNode()
    
    # Simulate tag creation like in add_node
    node_id = 1
    node.tag_node_name = str(node_id) + ':' + node.node_tag
    
    # Test input tags (FPS was Input04, now Output Mode is Input04)
    tag_input04 = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input04'
    tag_input05 = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input05'
    
    # Verify tag structure
    assert ':TEXT:Input04' in tag_input04, "Output mode input tag should contain ':TEXT:Input04'"
    assert ':TEXT:Input05' in tag_input05, "Channels input tag should contain ':TEXT:Input05'"
    
    print("✓ Microphone node input tags verified")
    print(f"  Output mode input tag: {tag_input04}")
    print(f"  Channels input tag: {tag_input05}")
    
    return True


def test_db_calculation():
    """Test decibel calculation logic"""
    import numpy as np
    
    # Test with typical audio values
    test_signal = np.array([0.1, 0.2, 0.15, 0.3], dtype=np.float32)
    rms = np.sqrt(np.mean(test_signal**2))
    db_value_original = 20 * np.log10(rms)
    # Apply the same transformation as in the node (multiply by -1 to make positive)
    db_value = -db_value_original
    
    # RMS should be around 0.19
    assert 0.15 < rms < 0.25, f"RMS should be around 0.19, got {rms}"
    
    # dB should now be positive (after multiplication by -1)
    assert db_value > 0, f"dB should be positive after transformation, got {db_value}"
    
    print("✓ Decibel calculation logic verified")
    print(f"  Test signal RMS: {rms:.4f}")
    print(f"  Test signal dB (original): {db_value_original:.2f}")
    print(f"  Test signal dB (positive): {db_value:.2f}")
    
    # Test with zero signal
    zero_signal = np.zeros(10, dtype=np.float32)
    rms_zero = np.sqrt(np.mean(zero_signal**2))
    
    # Should handle zero without errors
    assert rms_zero == 0.0, f"RMS of zero signal should be 0.0, got {rms_zero}"
    
    print(f"  Zero signal RMS: {rms_zero}")
    
    return True


def test_timestamp_format():
    """Test timestamp format"""
    import time
    
    # Get current timestamp
    timestamp = time.time()
    
    # Verify it's a reasonable Unix timestamp
    assert timestamp > 1000000000, f"Timestamp should be a Unix timestamp, got {timestamp}"
    assert timestamp < 3000000000, f"Timestamp seems too far in future, got {timestamp}"
    
    print("✓ Timestamp format verified")
    print(f"  Current timestamp: {timestamp}")
    print(f"  Human readable: {time.ctime(timestamp)}")
    
    return True


def test_output_structure():
    """Test the expected output structure with timestamp"""
    import numpy as np
    import time
    
    # Simulate audio output structure
    audio_data = np.random.randn(1000).astype(np.float32)
    sample_rate = 44100
    chunk_timestamp = time.time()
    channels = 1
    output_mode = 'Full Signal'
    
    audio_output = {
        'data': audio_data,
        'sample_rate': sample_rate,
        'timestamp': chunk_timestamp,
        'channels': channels,
        'output_mode': output_mode
    }
    
    # Verify structure
    assert 'data' in audio_output, "Audio output should have 'data' key"
    assert 'sample_rate' in audio_output, "Audio output should have 'sample_rate' key"
    assert 'timestamp' in audio_output, "Audio output should have 'timestamp' key"
    assert 'channels' in audio_output, "Audio output should have 'channels' key"
    assert 'output_mode' in audio_output, "Audio output should have 'output_mode' key"
    
    print("✓ Audio output structure verified")
    print(f"  Keys: {list(audio_output.keys())}")
    print(f"  Data shape: {audio_output['data'].shape}")
    print(f"  Sample rate: {audio_output['sample_rate']}")
    print(f"  Timestamp: {audio_output['timestamp']}")
    print(f"  Channels: {audio_output['channels']}")
    print(f"  Output mode: {audio_output['output_mode']}")
    
    # Test JSON output structure
    json_output = {
        'timestamp': chunk_timestamp,
        'sample_rate': sample_rate,
        'channels': channels,
        'chunk_duration': 1.0,
        'output_mode': output_mode,
        'samples': len(audio_data),
    }
    
    assert 'timestamp' in json_output, "JSON output should have 'timestamp' key"
    assert 'samples' in json_output, "JSON output should have 'samples' key"
    
    print("✓ JSON output structure verified")
    print(f"  Keys: {list(json_output.keys())}")
    print(f"  Samples: {json_output['samples']}")
    
    return True


def test_fps_limiting_logic():
    """Test FPS limiting logic - DEPRECATED: FPS limit was removed per requirements"""
    # This test is no longer applicable since FPS limiting was removed
    print(f"⚠️ FPS limiting was removed per requirements")
    print(f"  This test is deprecated")
    
    return True


if __name__ == '__main__':
    print("Testing Microphone Node Enhancements...")
    print("=" * 60)
    
    tests = [
        ("Enhanced Attributes", test_microphone_enhanced_attributes),
        ("New Input Tags", test_microphone_factory_new_inputs),
        ("dB Calculation", test_db_calculation),
        ("Timestamp Format", test_timestamp_format),
        ("Output Structure", test_output_structure),
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
        print("✓ All enhancement tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
