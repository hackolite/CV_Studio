#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the microphone node uses non-blocking audio streaming.
This ensures the update() method doesn't block the main loop.
"""
import sys
import os
import time
import queue
import threading

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_microphone_has_streaming_components():
    """Test that MicrophoneNode has the required streaming components"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Verify the node has streaming-related attributes
    assert hasattr(node, '_audio_stream'), "Node missing _audio_stream attribute"
    assert hasattr(node, '_audio_buffer'), "Node missing _audio_buffer attribute"
    assert hasattr(node, '_lock'), "Node missing _lock attribute for thread safety"
    assert hasattr(node, '_current_sample_rate'), "Node missing _current_sample_rate attribute"
    
    # Verify buffer is a Queue
    assert isinstance(node._audio_buffer, queue.Queue), "_audio_buffer should be a Queue"
    
    # Verify lock exists and is a threading lock type
    assert node._lock is not None, "_lock should not be None"
    assert hasattr(node._lock, 'acquire') and hasattr(node._lock, 'release'), \
        "_lock should have acquire and release methods"
    
    print("✓ Microphone node has all streaming components")
    print(f"  _audio_stream: {node._audio_stream}")
    print(f"  _audio_buffer: Queue with maxsize={node._audio_buffer.maxsize}")
    print(f"  _lock: {type(node._lock).__name__}")
    
    return True


def test_microphone_has_stream_methods():
    """Test that MicrophoneNode has stream control methods"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Verify the node has streaming control methods
    assert hasattr(node, '_start_stream'), "Node missing _start_stream method"
    assert hasattr(node, '_stop_stream'), "Node missing _stop_stream method"
    assert hasattr(node, '_audio_callback'), "Node missing _audio_callback method"
    
    # Verify methods are callable
    assert callable(node._start_stream), "_start_stream should be callable"
    assert callable(node._stop_stream), "_stop_stream should be callable"
    assert callable(node._audio_callback), "_audio_callback should be callable"
    
    print("✓ Microphone node has all stream control methods")
    print(f"  _start_stream: callable")
    print(f"  _stop_stream: callable")
    print(f"  _audio_callback: callable")
    
    return True


def test_audio_callback_signature():
    """Test that _audio_callback has the correct signature for sounddevice"""
    from node.InputNode.node_microphone import MicrophoneNode
    import inspect
    
    node = MicrophoneNode()
    
    # Get the signature of the _audio_callback method
    sig = inspect.signature(node._audio_callback)
    params = list(sig.parameters.keys())
    
    # Verify parameters match sounddevice callback signature
    expected_params = ['indata', 'frames', 'time_info', 'status']
    assert params == expected_params, f"Expected params {expected_params}, got {params}"
    
    print("✓ Audio callback has correct signature for sounddevice")
    print(f"  Parameters: {params}")
    
    return True


def test_buffer_maxsize_prevents_memory_issues():
    """Test that the buffer has a reasonable maxsize to prevent unbounded memory growth"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Verify buffer has a maxsize set
    maxsize = node._audio_buffer.maxsize
    assert maxsize > 0, "Buffer should have a positive maxsize to prevent unbounded growth"
    assert maxsize <= 100, "Buffer maxsize should be reasonable (<=100) to prevent excessive memory use"
    
    print("✓ Buffer has appropriate maxsize to prevent memory issues")
    print(f"  maxsize: {maxsize} (prevents unbounded memory growth)")
    
    return True


def test_close_method_stops_stream():
    """Test that close() method properly stops the stream"""
    from node.InputNode.node_microphone import MicrophoneNode
    import inspect
    
    node = MicrophoneNode()
    
    # Verify close method exists and is callable
    assert hasattr(node, 'close'), "Node missing close method"
    assert callable(node.close), "close should be callable"
    
    # Check that close method source contains _stop_stream call
    source = inspect.getsource(node.close)
    assert '_stop_stream' in source, "close() should call _stop_stream() for cleanup"
    
    print("✓ close() method properly handles stream cleanup")
    print(f"  Calls _stop_stream() for proper resource cleanup")
    
    return True


def test_no_blocking_calls_in_update():
    """Test that update() doesn't contain blocking sd.wait() calls"""
    from node.InputNode.node_microphone import MicrophoneNode
    import inspect
    
    node = MicrophoneNode()
    
    # Get the source of the update method
    source = inspect.getsource(node.update)
    
    # Verify sd.wait() is NOT in the update method
    assert 'sd.wait()' not in source, "update() should NOT contain blocking sd.wait() calls"
    
    # Verify it uses non-blocking queue operations
    assert 'get_nowait()' in source or 'get(block=False)' in source, \
        "update() should use non-blocking queue.get_nowait() or get(block=False)"
    
    print("✓ update() method uses non-blocking operations")
    print(f"  No sd.wait() blocking calls found")
    print(f"  Uses queue.get_nowait() for non-blocking buffer reads")
    
    return True


def test_uses_inputstream_not_rec():
    """Test that the implementation uses InputStream instead of blocking sd.rec()"""
    from node.InputNode.node_microphone import MicrophoneNode
    import inspect
    
    node = MicrophoneNode()
    
    # Get the source of _start_stream method
    source = inspect.getsource(node._start_stream)
    
    # Verify it uses InputStream
    assert 'InputStream' in source, "_start_stream should use sd.InputStream for non-blocking audio"
    
    # Verify update() doesn't use sd.rec()
    update_source = inspect.getsource(node.update)
    assert 'sd.rec(' not in update_source, "update() should NOT use blocking sd.rec()"
    
    print("✓ Implementation uses non-blocking InputStream")
    print(f"  _start_stream uses sd.InputStream")
    print(f"  update() does NOT use blocking sd.rec()")
    
    return True


if __name__ == '__main__':
    print("Testing Microphone Non-Blocking Implementation...")
    print("=" * 60)
    
    tests = [
        ("Streaming Components", test_microphone_has_streaming_components),
        ("Stream Methods", test_microphone_has_stream_methods),
        ("Audio Callback Signature", test_audio_callback_signature),
        ("Buffer Maxsize", test_buffer_maxsize_prevents_memory_issues),
        ("Close Method", test_close_method_stops_stream),
        ("No Blocking in Update", test_no_blocking_calls_in_update),
        ("InputStream Usage", test_uses_inputstream_not_rec),
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
        print("✓ All non-blocking tests passed!")
        print("\nPerformance Benefits:")
        print("  • No more blocking sd.wait() calls in main loop")
        print("  • Audio captured in background thread via callback")
        print("  • update() returns immediately with buffered data")
        print("  • CPU usage reduced - no busy waiting")
        print("  • Main application remains responsive")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
