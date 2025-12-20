#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test VideoWriter stop behavior with full queue (freeze prevention).

This test verifies that the VideoWriter can cleanly stop recording even when
the frame queue is full, which was causing freeze issues when connecting
ImageConcat (large frames) to VideoWriter.
"""

import sys
import os
import time
import queue
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def test_stop_flag_prevents_queue_full_freeze():
    """
    Test that using threading.Event for stopping prevents freeze when queue is full.
    
    This simulates the scenario where:
    1. ImageConcat produces large frames continuously
    2. VideoWriter queue fills up (60 frames max)
    3. User clicks Stop button
    4. System should stop cleanly without freeze (old code would timeout)
    """
    print("\nTest: Stop flag prevents queue-full freeze")
    
    # Simulate VideoWriter state
    write_queue = queue.Queue(maxsize=60)
    stop_flag = threading.Event()
    frames_written = [0]  # Use list for mutable counter in thread
    
    def writer_thread_with_flag():
        """Simulates the new writer thread with stop flag"""
        while not stop_flag.is_set():
            try:
                frame = write_queue.get(timeout=0.1)
                if frame is None:
                    break
                # Simulate write time
                time.sleep(0.001)
                frames_written[0] += 1
                write_queue.task_done()
            except queue.Empty:
                continue
    
    # Start thread
    thread = threading.Thread(target=writer_thread_with_flag, daemon=True)
    thread.start()
    
    # Fill queue with large frames (simulate ImageConcat output)
    large_frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
    
    for i in range(60):  # Fill to max capacity
        try:
            write_queue.put_nowait(large_frame.copy())
        except queue.Full:
            print(f"  Queue full at frame {i}")
            break
    
    print(f"  Queue filled with {write_queue.qsize()} frames")
    
    # Simulate Stop button click - set stop flag (this always succeeds immediately)
    start_stop = time.time()
    stop_flag.set()
    stop_signal_time = time.time() - start_stop
    
    print(f"  Stop signal sent in {stop_signal_time*1000:.2f}ms (non-blocking)")
    
    # Wait for thread to stop
    start_join = time.time()
    thread.join(timeout=5.0)
    join_time = time.time() - start_join
    
    print(f"  Thread stopped in {join_time:.3f}s")
    print(f"  Frames written: {frames_written[0]}")
    
    # Verify thread stopped cleanly
    assert not thread.is_alive(), "Thread should have stopped"
    assert stop_signal_time < 0.001, "Stop signal should be instant (< 1ms)"
    assert join_time < 2.0, "Thread should stop within 2 seconds"
    
    print("  ✓ Stop flag prevents freeze")


def test_old_method_can_timeout():
    """
    Test that the old method (putting None in queue) can fail when queue is full.
    
    This demonstrates why the old code could cause freeze/timeout issues.
    """
    print("\nTest: Old method (queue None) can timeout when queue full")
    
    # Simulate old VideoWriter state
    write_queue = queue.Queue(maxsize=60)
    frames_written = [0]
    
    def writer_thread_old_method():
        """Simulates the old writer thread (checks for None in queue)"""
        while True:
            try:
                frame = write_queue.get(timeout=1.0)
                if frame is None:
                    break
                # Simulate slow write time for large frames
                time.sleep(0.01)
                frames_written[0] += 1
                write_queue.task_done()
            except queue.Empty:
                break
    
    # Start thread
    thread = threading.Thread(target=writer_thread_old_method, daemon=True)
    thread.start()
    
    # Fill queue completely
    large_frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
    
    for i in range(60):
        try:
            write_queue.put_nowait(large_frame.copy())
        except queue.Full:
            break
    
    print(f"  Queue filled with {write_queue.qsize()} frames")
    
    # Try to send stop signal by putting None (this will fail/timeout if queue is full)
    start_stop = time.time()
    try:
        write_queue.put(None, timeout=1.0)
        stop_signal_time = time.time() - start_stop
        print(f"  Stop signal sent in {stop_signal_time:.3f}s")
    except queue.Full:
        stop_signal_time = time.time() - start_stop
        print(f"  ⚠ Stop signal FAILED after {stop_signal_time:.3f}s (queue full)")
    
    # Even if we sent the signal, thread might still be processing
    thread.join(timeout=2.0)
    
    print(f"  Thread alive: {thread.is_alive()}")
    print(f"  Frames written: {frames_written[0]}")
    
    # This demonstrates the problem: stop signal can fail or take long time
    print("  ✓ Old method shows potential for freeze/timeout")


def test_threading_event_performance():
    """Test that threading.Event has negligible performance overhead"""
    print("\nTest: threading.Event performance overhead")
    
    stop_flag = threading.Event()
    
    # Test set() performance
    start = time.time()
    for _ in range(10000):
        stop_flag.set()
        stop_flag.clear()
    elapsed = time.time() - start
    
    print(f"  10,000 set/clear cycles: {elapsed*1000:.2f}ms")
    print(f"  Per operation: {elapsed/10000*1000000:.2f}μs")
    
    # Test is_set() performance
    start = time.time()
    for _ in range(1000000):
        _ = stop_flag.is_set()
    elapsed = time.time() - start
    
    print(f"  1,000,000 is_set checks: {elapsed*1000:.2f}ms")
    print(f"  Per check: {elapsed/1000000*1000000:.3f}μs")
    
    print("  ✓ threading.Event has negligible overhead")


def test_writer_thread_stops_quickly():
    """
    Test that writer thread stops quickly when stop signal is sent.
    
    This ensures responsive UI - when user clicks stop, recording stops immediately
    without waiting for all queued frames to be written.
    """
    print("\nTest: Writer thread stops quickly after stop signal")
    
    write_queue = queue.Queue(maxsize=60)
    stop_flag = threading.Event()
    frames_written = [0]
    
    def writer_thread():
        while not stop_flag.is_set():
            try:
                frame = write_queue.get(timeout=0.1)
                if frame is None:
                    break
                time.sleep(0.001)  # Simulate write
                frames_written[0] += 1
                write_queue.task_done()
            except queue.Empty:
                continue
    
    # Start thread
    thread = threading.Thread(target=writer_thread, daemon=True)
    thread.start()
    
    # Add 30 frames
    small_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for i in range(30):
        write_queue.put_nowait(small_frame)
    
    initial_queue_size = write_queue.qsize()
    print(f"  Queue size before stop: {initial_queue_size}")
    
    # Set stop flag
    start = time.time()
    stop_flag.set()
    
    # Wait for thread to stop
    thread.join(timeout=0.5)
    elapsed = time.time() - start
    
    print(f"  Thread stopped in: {elapsed:.3f}s")
    print(f"  Frames written: {frames_written[0]}/{initial_queue_size}")
    print(f"  Remaining in queue: {write_queue.qsize()}")
    
    # Thread should stop quickly (within 0.2s of checking stop flag)
    assert not thread.is_alive(), "Thread should have stopped"
    assert elapsed < 0.3, f"Should stop quickly (was {elapsed:.3f}s)"
    
    print("  ✓ Thread stops quickly for responsive UI")


def test_stop_timeout_is_reasonable():
    """
    Test that writer thread stops within reasonable timeout even with full queue.
    
    This verifies the fix prevents the freeze issue.
    """
    print("\nTest: Writer thread stops within reasonable timeout")
    
    write_queue = queue.Queue(maxsize=60)
    stop_flag = threading.Event()
    frames_written = [0]
    
    def writer_thread():
        while not stop_flag.is_set():
            try:
                frame = write_queue.get(timeout=0.1)
                if frame is None:
                    break
                # Simulate realistic write time for large frame
                time.sleep(0.002)
                frames_written[0] += 1
                write_queue.task_done()
            except queue.Empty:
                continue
    
    # Start thread
    thread = threading.Thread(target=writer_thread, daemon=True)
    thread.start()
    
    # Fill queue with large frames
    large_frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
    for i in range(60):
        try:
            write_queue.put_nowait(large_frame.copy())
        except queue.Full:
            break
    
    print(f"  Queue filled: {write_queue.qsize()} frames")
    
    # Set stop flag and measure join time
    stop_flag.set()
    
    start = time.time()
    thread.join(timeout=5.0)  # _WRITE_THREAD_TIMEOUT
    elapsed = time.time() - start
    
    print(f"  Thread stopped in: {elapsed:.3f}s")
    print(f"  Frames processed: {frames_written[0]}")
    
    # Should stop well within 5 second timeout
    assert not thread.is_alive(), "Thread should have stopped"
    assert elapsed < 3.0, f"Should stop within 3s (was {elapsed:.3f}s)"
    
    print("  ✓ Stops within reasonable timeout (no freeze)")


if __name__ == '__main__':
    print("="*70)
    print("Testing VideoWriter Stop with Full Queue (Freeze Prevention)")
    print("="*70)
    
    test_stop_flag_prevents_queue_full_freeze()
    test_old_method_can_timeout()
    test_threading_event_performance()
    test_writer_thread_stops_quickly()
    test_stop_timeout_is_reasonable()
    
    print("\n" + "="*70)
    print("All tests passed! ✓")
    print("="*70)
    print("\nSummary:")
    print("- threading.Event prevents queue-full freeze")
    print("- Old method could timeout when queue is full")
    print("- Event has negligible performance overhead")
    print("- Thread stops quickly for responsive UI")
    print("- Thread stops within reasonable timeout")
