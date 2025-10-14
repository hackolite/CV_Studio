#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration of spectrogram scrolling behavior
This script simulates the scrolling logic without requiring actual video files
"""

import numpy as np


def simulate_spectrogram_scrolling():
    """Simulate and demonstrate the spectrogram scrolling logic"""
    
    # Simulate a 5-minute video
    fps = 30
    duration = 300  # 5 minutes
    sr = 22050
    hop_length = 512
    
    # Calculate total spectrogram dimensions
    total_samples = duration * sr
    total_columns = int(total_samples / hop_length)
    
    # Display window size
    window_width = 240
    half_window = window_width // 2
    
    print("=" * 70)
    print("SPECTROGRAM SCROLLING DEMONSTRATION")
    print("=" * 70)
    print(f"\nVideo Configuration:")
    print(f"  Duration: {duration} seconds ({duration/60:.1f} minutes)")
    print(f"  Frame rate: {fps} FPS")
    print(f"  Total frames: {fps * duration}")
    print(f"\nAudio Configuration:")
    print(f"  Sample rate: {sr} Hz")
    print(f"  Hop length: {hop_length} samples")
    print(f"\nSpectrogram Dimensions:")
    print(f"  Total columns: {total_columns}")
    print(f"  Display window: {window_width} columns")
    print(f"  Compression ratio (old): {total_columns / window_width:.1f}:1")
    print(f"  Compression ratio (new): 1:1 (no compression!)")
    print("\n" + "=" * 70)
    
    # Simulate playback at different positions
    test_positions = [
        (0, "Video start"),
        (30, "30 seconds in"),
        (150, "2.5 minutes in"),
        (270, "4.5 minutes in"),
        (299, "Near end"),
    ]
    
    for time_seconds, description in test_positions:
        current_frame = int(time_seconds * fps)
        current_sample = int(time_seconds * sr)
        spectrogram_col = int(current_sample / hop_length)
        
        # Calculate window boundaries (same logic as in node_video.py)
        start_col = max(0, spectrogram_col - half_window)
        end_col = min(total_columns, start_col + window_width)
        
        # Adjust start if at the end
        if end_col == total_columns:
            start_col = max(0, end_col - window_width)
        
        # Calculate indicator position within window
        indicator_col = spectrogram_col - start_col
        
        # Check if padding is needed
        window_cols = end_col - start_col
        needs_padding = window_cols < window_width
        pad_width = window_width - window_cols if needs_padding else 0
        
        print(f"\n{description} (t={time_seconds}s, frame {current_frame}):")
        print(f"  Spectrogram position: column {spectrogram_col}/{total_columns}")
        print(f"  Window range: [{start_col} - {end_col}]")
        print(f"  Indicator position in window: column {indicator_col}")
        print(f"  Padding needed: {'Yes' if needs_padding else 'No'}", end="")
        if needs_padding:
            print(f" ({pad_width} columns on {'left' if start_col > 0 else 'right'})")
        else:
            print()
        
        # Visual representation
        progress_pct = (spectrogram_col / total_columns) * 100
        window_pct = (start_col / total_columns) * 100
        print(f"  Progress: {progress_pct:.1f}%")
        
        # Simple ASCII visualization
        bar_width = 60
        bar_pos = int((spectrogram_col / total_columns) * bar_width)
        window_start = int((start_col / total_columns) * bar_width)
        window_end = min(bar_width, int((end_col / total_columns) * bar_width))
        
        bar = ['-'] * bar_width
        for i in range(window_start, window_end):
            bar[i] = '█'
        if 0 <= bar_pos < bar_width:
            bar[bar_pos] = '|'
        
        print(f"  Visual: [{''.join(bar)}]")
        print(f"          {' ' * window_start}^{' ' * max(0, bar_pos - window_start)}^")
        spacing = max(0, bar_pos - window_start - 12)
        print(f"          {' ' * window_start}Window start{' ' * spacing}Indicator")
    
    print("\n" + "=" * 70)
    print("\nKEY FEATURES:")
    print("  ✓ Window follows playback position smoothly")
    print("  ✓ Indicator stays centered (except at edges)")
    print("  ✓ Full resolution: 1:1 pixel mapping, no compression")
    print("  ✓ Frame-by-frame updates for smooth scrolling")
    print("=" * 70)


if __name__ == '__main__':
    simulate_spectrogram_scrolling()
