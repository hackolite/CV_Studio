#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the Webcam input node audio capture.
Verifies that the webcam node exposes an audio output and its internal
audio-streaming infrastructure is properly wired.
"""
import sys
import os
import inspect
import queue
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_webcam_node_import():
    """Test that Webcam node can be imported and exposes SOUNDDEVICE_AVAILABLE."""
    from node.InputNode.node_webcam import FactoryNode, WebcamNode, SOUNDDEVICE_AVAILABLE

    print("✓ Webcam node imported successfully")
    print(f"  sounddevice available: {SOUNDDEVICE_AVAILABLE}")
    return True


def test_webcam_node_audio_attributes():
    """Test that WebcamNode has the audio-stream state attributes."""
    from node.InputNode.node_webcam import WebcamNode

    node = WebcamNode()

    assert hasattr(node, '_audio_stream'), "Missing _audio_stream"
    assert node._audio_stream is None, "_audio_stream should start as None"

    assert hasattr(node, '_audio_buffer'), "Missing _audio_buffer"
    assert isinstance(node._audio_buffer, queue.Queue), "_audio_buffer should be a Queue"

    assert hasattr(node, '_current_audio_device'), "Missing _current_audio_device"
    assert node._current_audio_device is None, "_current_audio_device should start as None"

    assert hasattr(node, '_lock'), "Missing _lock"
    assert isinstance(node._lock, type(threading.Lock())), "_lock should be a Lock"

    assert hasattr(node, '_SAMPLE_RATE'), "Missing _SAMPLE_RATE class constant"
    assert hasattr(node, '_CHUNK_DURATION'), "Missing _CHUNK_DURATION class constant"

    print("✓ WebcamNode audio attributes verified")
    return True


def test_webcam_node_audio_methods():
    """Test that WebcamNode has the required audio-stream methods."""
    from node.InputNode.node_webcam import WebcamNode

    node = WebcamNode()

    assert callable(getattr(node, '_audio_callback', None)), "Missing _audio_callback"
    assert callable(getattr(node, '_start_audio_stream', None)), "Missing _start_audio_stream"
    assert callable(getattr(node, '_stop_audio_stream', None)), "Missing _stop_audio_stream"

    print("✓ WebcamNode audio methods verified")
    return True


def test_webcam_node_update_signature():
    """Test that WebcamNode.update has the correct signature."""
    from node.InputNode.node_webcam import WebcamNode

    node = WebcamNode()
    sig = inspect.signature(node.update)
    params = list(sig.parameters.keys())

    expected = ['node_id', 'connection_list', 'node_image_dict', 'node_result_dict', 'node_audio_dict']
    assert params == expected, f"Expected params {expected}, got {params}"

    print("✓ WebcamNode.update signature verified")
    return True


def test_webcam_node_close_stops_audio():
    """Test that _stop_audio_stream does not crash when no stream is active."""
    from node.InputNode.node_webcam import WebcamNode

    node = WebcamNode()
    # Should not raise even when no stream was ever started
    node._stop_audio_stream()

    assert node._audio_stream is None, "_audio_stream should remain None after stop"
    print("✓ _stop_audio_stream is safe with no active stream")
    return True


def test_webcam_audio_callback_buffers_data():
    """Test that _audio_callback correctly pushes data into _audio_buffer."""
    import numpy as np
    from node.InputNode.node_webcam import WebcamNode

    node = WebcamNode()

    # Simulate a callback invocation with a dummy audio chunk
    fake_chunk = np.zeros((1600, 1), dtype='float32')
    fake_chunk[0, 0] = 0.5  # non-zero sentinel
    node._audio_callback(fake_chunk, 1600, None, None)

    assert not node._audio_buffer.empty(), "Buffer should contain the pushed chunk"
    data = node._audio_buffer.get_nowait()
    assert data[0, 0] == 0.5, "Buffer should contain the correct audio data"

    print("✓ _audio_callback correctly buffers audio data")
    return True


def test_webcam_audio_callback_drops_oldest_when_full():
    """Test that _audio_callback drops oldest chunk when buffer is full."""
    import numpy as np
    from node.InputNode.node_webcam import WebcamNode

    node = WebcamNode()

    # Fill the buffer to capacity (maxsize=10)
    for i in range(10):
        chunk = np.full((16, 1), float(i), dtype='float32')
        node._audio_buffer.put_nowait(chunk)

    # Now push one more – should drop oldest (0.0) and keep newest (10.0)
    newest_chunk = np.full((16, 1), 10.0, dtype='float32')
    node._audio_callback(newest_chunk, 16, None, None)

    items = []
    while not node._audio_buffer.empty():
        items.append(node._audio_buffer.get_nowait()[0, 0])

    assert 0.0 not in items, "Oldest chunk should have been dropped"
    assert 10.0 in items, "Newest chunk should be present"

    print("✓ _audio_callback correctly drops oldest chunk when buffer is full")
    return True


def test_factory_node_structure():
    """Test that FactoryNode has correct structure."""
    from node.InputNode.node_webcam import FactoryNode

    factory = FactoryNode()
    assert factory.node_label == 'Webcam'
    assert factory.node_tag == 'Webcam'
    assert callable(getattr(factory, 'add_node', None))

    print("✓ FactoryNode structure verified")
    return True


if __name__ == '__main__':
    print("Testing Webcam Node Audio...")
    print("=" * 60)

    tests = [
        ("Import", test_webcam_node_import),
        ("Audio Attributes", test_webcam_node_audio_attributes),
        ("Audio Methods", test_webcam_node_audio_methods),
        ("Update Signature", test_webcam_node_update_signature),
        ("Close Safety", test_webcam_node_close_stops_audio),
        ("Callback Buffers Data", test_webcam_audio_callback_buffers_data),
        ("Callback Drops Oldest", test_webcam_audio_callback_drops_oldest_when_full),
        ("Factory Structure", test_factory_node_structure),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    sys.exit(0 if failed == 0 else 1)
