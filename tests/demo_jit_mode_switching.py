#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration of JIT vs Precompute Spectrogram Modes

This script shows how to switch between 'precompute' and 'jit' modes
for spectrogram generation in the VideoNode.

Usage:
    python demo_jit_mode_switching.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def demo_mode_switching():
    """
    Demonstrate how to switch between precompute and JIT modes.
    
    This is a documentation example - actual usage would require
    a valid video file and full dependencies (cv2, DearPyGUI, etc.)
    """
    print("=" * 70)
    print("JIT vs Precompute Spectrogram Mode Demonstration")
    print("=" * 70)
    print()
    
    print("Overview:")
    print("-" * 70)
    print("The VideoNode supports two spectrogram generation modes:")
    print()
    print("1. PRECOMPUTE MODE (default):")
    print("   - All spectrograms are generated during video preprocessing")
    print("   - Faster playback (no real-time generation needed)")
    print("   - Higher memory usage (stores all spectrograms)")
    print("   - Longer initial loading time")
    print()
    print("2. JIT MODE (just-in-time):")
    print("   - Spectrograms are generated on-the-fly for each frame")
    print("   - Lower memory usage (no pre-computed storage)")
    print("   - Faster initial loading (no pre-generation)")
    print("   - Slightly slower playback (real-time generation overhead)")
    print()
    print("=" * 70)
    print()
    
    print("Code Example:")
    print("-" * 70)
    print("""
from node.InputNode.node_video import VideoNode

# Create a VideoNode instance
node = VideoNode()

# --- MODE 1: PRECOMPUTE (DEFAULT) ---
print("Using PRECOMPUTE mode:")
node._spectrogram_mode = 'precompute'  # This is the default

# When you load a video, spectrograms are pre-computed
# node._preprocess_video('node_1', 'path/to/video.mp4')
# All spectrograms are generated and cached during preprocessing

# During playback, spectrograms are retrieved from cache (fast)
# spec = node._get_spectrogram_for_frame('node_1', frame_number)


# --- MODE 2: JIT ---
print("\\nSwitching to JIT mode:")
node._spectrogram_mode = 'jit'

# When you load a video, only the audio is stored
# node._preprocess_video('node_1', 'path/to/video.mp4')
# No spectrograms are pre-computed (faster preprocessing)

# During playback, spectrograms are generated on-the-fly
# spec = node._get_spectrogram_for_frame('node_1', frame_number)
# This calls _generate_spectrogram_jit() internally


# --- SWITCHING MODES ---
print("\\nYou can switch modes at any time:")
node._spectrogram_mode = 'precompute'  # Switch back to precompute
node._spectrogram_mode = 'jit'         # Switch to JIT


# --- TECHNICAL DETAILS ---
print("\\nBoth modes use the same processing pipeline:")
print("  1. fourier_transformation() - STFT with Hanning window")
print("  2. make_logscale() - Logarithmic frequency scaling")
print("  3. apply_colormap_to_spectrogram() - Colorization")
print("\\nThis ensures identical spectrogram quality in both modes.")
""")
    print()
    print("=" * 70)
    print()
    
    print("When to use each mode:")
    print("-" * 70)
    print()
    print("Use PRECOMPUTE mode when:")
    print("  ✓ You have enough memory")
    print("  ✓ You need smooth, real-time playback")
    print("  ✓ You're playing the same video multiple times")
    print("  ✓ Initial loading time is not a concern")
    print()
    print("Use JIT mode when:")
    print("  ✓ Memory is limited")
    print("  ✓ You're working with very long videos")
    print("  ✓ You need fast initial loading")
    print("  ✓ You're seeking to specific frames (not continuous playback)")
    print()
    print("=" * 70)
    print()
    
    print("Implementation Notes:")
    print("-" * 70)
    print("• Default mode is 'precompute' for backward compatibility")
    print("• Mode can be changed by setting node._spectrogram_mode")
    print("• Full audio signal is always stored in node._audio_y")
    print("• The update() method automatically uses the selected mode")
    print("• No code changes needed in update() - it just works!")
    print()
    print("=" * 70)
    print()
    
    print("✅ Demonstration complete!")
    print()


if __name__ == '__main__':
    demo_mode_switching()
