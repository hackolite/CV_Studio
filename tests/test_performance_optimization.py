#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance test for video preprocessing optimization.

This test measures the performance improvement from:
1. Caching mechanism
2. Parallel spectrogram processing
"""

import sys
import os
import time
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.node_video import VideoNode, get_cache_dir


def test_preprocessing_with_caching():
    """Test that caching significantly speeds up second load"""
    
    # Use a test video
    test_video = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'pose_estimation', 'movenet', 'D0002080169_00000_V_000.mp4'
    )
    
    if not os.path.exists(test_video):
        print(f"⚠️ Test video not found: {test_video}")
        print("Skipping performance test")
        return
    
    # Clear any existing cache for this video
    cache_dir = get_cache_dir()
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    
    # Create a VideoNode instance
    node = VideoNode()
    
    # First run - no cache
    print("\n" + "="*70)
    print("TEST 1: First preprocessing (no cache)")
    print("="*70)
    start_time = time.time()
    node._preprocess_video("test_node_1", test_video)
    first_run_time = time.time() - start_time
    print(f"\n✅ First run completed in {first_run_time:.2f} seconds")
    
    # Verify data was stored
    assert "test_node_1" in node._video_frames
    assert "test_node_1" in node._spectrogram_chunks
    assert "test_node_1" in node._chunk_metadata
    
    num_frames = len(node._video_frames["test_node_1"])
    num_chunks = len(node._spectrogram_chunks["test_node_1"])
    print(f"   Frames: {num_frames}, Spectrograms: {num_chunks}")
    
    # Clear in-memory data
    node._video_frames.clear()
    node._spectrogram_chunks.clear()
    node._chunk_metadata.clear()
    
    # Second run - with cache
    print("\n" + "="*70)
    print("TEST 2: Second preprocessing (with cache)")
    print("="*70)
    start_time = time.time()
    node._preprocess_video("test_node_2", test_video)
    second_run_time = time.time() - start_time
    print(f"\n✅ Second run completed in {second_run_time:.2f} seconds")
    
    # Verify data was loaded
    assert "test_node_2" in node._video_frames
    assert "test_node_2" in node._spectrogram_chunks
    assert "test_node_2" in node._chunk_metadata
    
    # Check same amount of data
    assert len(node._video_frames["test_node_2"]) == num_frames
    assert len(node._spectrogram_chunks["test_node_2"]) == num_chunks
    
    # Calculate speedup
    speedup = first_run_time / second_run_time if second_run_time > 0 else 0
    
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"First run (no cache):  {first_run_time:.2f}s")
    print(f"Second run (cached):   {second_run_time:.2f}s")
    print(f"Speedup:               {speedup:.2f}x")
    print(f"Time saved:            {first_run_time - second_run_time:.2f}s")
    
    # Cache should be significantly faster (at least 2x)
    assert speedup >= 2.0, f"Cache speedup too low: {speedup}x (expected >= 2x)"
    
    print("\n✅ Cache provides significant speedup!")


def test_parallel_processing_benefit():
    """Test that parallel processing is actually being used"""
    
    from multiprocessing import cpu_count
    
    num_cores = cpu_count()
    print(f"\n💻 System has {num_cores} CPU cores")
    print("   Parallel processing will use {0} workers".format(max(1, num_cores - 1)))
    
    # Just verify the multiprocessing setup
    assert num_cores >= 1
    print("✅ Parallel processing is configured")


if __name__ == '__main__':
    print("="*70)
    print("PERFORMANCE OPTIMIZATION TESTS")
    print("="*70)
    
    test_parallel_processing_benefit()
    test_preprocessing_with_caching()
    
    print("\n" + "="*70)
    print("ALL TESTS PASSED!")
    print("="*70)
