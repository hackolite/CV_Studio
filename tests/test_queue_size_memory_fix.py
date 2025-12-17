#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify queue size memory fix for VideoWriter lag issue.

This test ensures that the VideoBackgroundWorker doesn't allocate 
excessive memory when starting, which was causing system lag and crashes.

Original issue: "quand je fais videowriter, start, ça commence à lagguer 
terriblement et à planter la machine, pourquoi ?"
(When I start videowriter, it starts to lag terribly and crash the machine, why?)

Root cause: Queue size was calculated as fps * chunk_duration * audio_queue_size,
which could result in 360+ frames (~2.2 GB at 1080p), causing immediate memory
allocation issues on start.

Fix: Changed calculation to fps * chunk_duration (without audio_queue_size multiplier)
and reduced MAX_FRAME_QUEUE_SIZE from 300 to 100.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from node.VideoNode.video_worker import VideoBackgroundWorker


def test_queue_size_reasonable_for_typical_settings():
    """
    Test that queue size is reasonable for typical video settings.
    
    Typical settings:
    - 30 fps
    - 3 second chunk duration
    - 1920x1080 resolution
    
    Expected queue size: ~90 frames (not 360)
    Expected memory: ~558 MB (not 2.2 GB)
    """
    fps = 30
    chunk_duration = 3.0
    width = 1920
    height = 1080
    
    # Create worker
    worker = VideoBackgroundWorker(
        output_path="/tmp/test_video.mp4",
        width=width,
        height=height,
        fps=fps,
        sample_rate=44100,
        total_frames=None,
        progress_callback=None,
        chunk_duration=chunk_duration
    )
    
    # Get queue size
    queue_size = worker.queue_frames.get_max_size()
    
    # Calculate expected memory per frame (1920x1080x3 bytes = ~6.2 MB)
    bytes_per_frame = width * height * 3
    total_memory_mb = (queue_size * bytes_per_frame) / (1024 * 1024)
    
    # Verify queue size is reasonable
    print(f"Queue size: {queue_size} frames")
    print(f"Estimated memory: {total_memory_mb:.1f} MB")
    
    # Should be less than 100 frames (old max was 300)
    assert queue_size <= 100, f"Queue size {queue_size} exceeds safe limit of 100"
    
    # Should be around 90 for typical settings (30 fps * 3s)
    assert 30 <= queue_size <= 100, f"Queue size {queue_size} outside expected range [30, 100]"
    
    # Should use less than 700 MB (old logic would use ~1.8-2.2 GB)
    assert total_memory_mb < 700, f"Queue memory {total_memory_mb:.1f} MB exceeds safe limit of 700 MB"
    
    print(f"✓ Queue size is reasonable: {queue_size} frames (~{total_memory_mb:.1f} MB)")


def test_queue_size_high_fps():
    """
    Test that queue size is capped even at high FPS.
    
    High FPS settings:
    - 120 fps
    - 3 second chunk duration
    
    Old calculation: 120 * 3 * 4 = 1440 frames (capped at 300) = ~1.8 GB
    New calculation: 120 * 3 = 360 frames (capped at 100) = ~620 MB
    """
    fps = 120
    chunk_duration = 3.0
    width = 1920
    height = 1080
    
    worker = VideoBackgroundWorker(
        output_path="/tmp/test_video.mp4",
        width=width,
        height=height,
        fps=fps,
        sample_rate=44100,
        total_frames=None,
        progress_callback=None,
        chunk_duration=chunk_duration
    )
    
    queue_size = worker.queue_frames.get_max_size()
    bytes_per_frame = width * height * 3
    total_memory_mb = (queue_size * bytes_per_frame) / (1024 * 1024)
    
    print(f"High FPS queue size: {queue_size} frames")
    print(f"High FPS estimated memory: {total_memory_mb:.1f} MB")
    
    # Should be capped at MAX_FRAME_QUEUE_SIZE (100)
    assert queue_size == 100, f"Queue size {queue_size} should be capped at 100 for high FPS"
    
    # Should use less than 700 MB even at high FPS
    assert total_memory_mb < 700, f"Queue memory {total_memory_mb:.1f} MB exceeds safe limit even at high FPS"
    
    print(f"✓ High FPS queue size is safely capped: {queue_size} frames (~{total_memory_mb:.1f} MB)")


def test_queue_size_low_fps():
    """
    Test that queue size has a reasonable minimum for low FPS.
    
    Low FPS settings:
    - 10 fps
    - 3 second chunk duration
    
    Calculation: 10 * 3 = 30 frames (minimum is 30)
    """
    fps = 10
    chunk_duration = 3.0
    
    worker = VideoBackgroundWorker(
        output_path="/tmp/test_video.mp4",
        width=640,
        height=480,
        fps=fps,
        sample_rate=44100,
        total_frames=None,
        progress_callback=None,
        chunk_duration=chunk_duration
    )
    
    queue_size = worker.queue_frames.get_max_size()
    
    print(f"Low FPS queue size: {queue_size} frames")
    
    # Should be at least MIN_FRAME_QUEUE_SIZE (30)
    assert queue_size >= 30, f"Queue size {queue_size} should be at least 30 for low FPS"
    
    print(f"✓ Low FPS queue size has reasonable minimum: {queue_size} frames")


def test_queue_size_various_chunk_durations():
    """
    Test that queue size scales appropriately with different chunk durations.
    """
    fps = 30
    width = 1920
    height = 1080
    
    test_cases = [
        (1.0, 30, 186),   # 1s chunks: 30 frames, ~186 MB
        (2.0, 60, 372),   # 2s chunks: 60 frames, ~372 MB
        (3.0, 90, 558),   # 3s chunks: 90 frames, ~558 MB
        (5.0, 100, 620),  # 5s chunks: capped at 100 frames, ~620 MB
    ]
    
    for chunk_duration, expected_frames, expected_mb in test_cases:
        worker = VideoBackgroundWorker(
            output_path="/tmp/test_video.mp4",
            width=width,
            height=height,
            fps=fps,
            sample_rate=44100,
            total_frames=None,
            progress_callback=None,
            chunk_duration=chunk_duration
        )
        
        queue_size = worker.queue_frames.get_max_size()
        bytes_per_frame = width * height * 3
        total_memory_mb = (queue_size * bytes_per_frame) / (1024 * 1024)
        
        print(f"Chunk duration {chunk_duration}s: {queue_size} frames (~{total_memory_mb:.1f} MB)")
        
        # Should be close to expected (within reasonable tolerance)
        assert queue_size == expected_frames, \
            f"Queue size {queue_size} doesn't match expected {expected_frames} for {chunk_duration}s chunks"
        
        # Should use less than 700 MB
        assert total_memory_mb < 700, \
            f"Queue memory {total_memory_mb:.1f} MB exceeds safe limit for {chunk_duration}s chunks"
    
    print(f"✓ Queue sizes scale appropriately with chunk duration")


def test_memory_calculation_correctness():
    """
    Verify memory calculation is correct and reasonable.
    
    This test documents the memory usage calculation for transparency.
    """
    width = 1920
    height = 1080
    channels = 3  # RGB
    
    # Calculate bytes per frame
    bytes_per_frame = width * height * channels
    mb_per_frame = bytes_per_frame / (1024 * 1024)
    
    print(f"\nMemory calculation for {width}x{height} resolution:")
    print(f"  Bytes per frame: {bytes_per_frame:,} bytes")
    print(f"  MB per frame: {mb_per_frame:.2f} MB")
    
    # Calculate for different queue sizes
    queue_sizes = [30, 50, 90, 100, 300]
    for size in queue_sizes:
        total_mb = size * mb_per_frame
        print(f"  {size} frames: {total_mb:.1f} MB")
    
    # Verify our assumptions
    assert 5.9 < mb_per_frame < 6.0, f"Expected ~5.93 MB per frame, got {mb_per_frame:.2f}"
    assert 90 * mb_per_frame < 600, "90 frames should be less than 600 MB"
    assert 100 * mb_per_frame < 700, "100 frames should be less than 700 MB"
    assert 300 * mb_per_frame > 1700, "300 frames should be more than 1.7 GB (the old problem)"
    
    print(f"✓ Memory calculations are correct")


if __name__ == "__main__":
    test_queue_size_reasonable_for_typical_settings()
    test_queue_size_high_fps()
    test_queue_size_low_fps()
    test_queue_size_various_chunk_durations()
    test_memory_calculation_correctness()
    print("\n✅ All queue size memory tests passed!")
