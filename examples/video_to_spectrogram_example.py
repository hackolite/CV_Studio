#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example: Converting Video Chunks to Spectrograms

This example demonstrates how to use the video to spectrogram conversion utilities
to process audio from video files or audio files directly into spectrogram images.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_video_to_spectrogram import plot_spectrogram, process_video_chunks_to_spectrograms


def example_single_file():
    """Example 1: Convert a single audio file to spectrogram."""
    print("Example 1: Single File Conversion")
    print("-" * 50)
    
    # NOTE: You need to provide your own audio file path
    audio_file = "path/to/your/audio.wav"
    output_file = "path/to/output/spectrogram.jpg"
    
    if os.path.exists(audio_file):
        plot_spectrogram(
            location=audio_file,
            plotpath=output_file,
            binsize=1024,  # FFT bin size
            colormap="jet"  # Colormap: jet, viridis, inferno, plasma, etc.
        )
        print(f"✓ Spectrogram saved to: {output_file}")
    else:
        print(f"⚠ Audio file not found: {audio_file}")
        print("Please update the audio_file path in this script")
    print()


def example_batch_processing():
    """Example 2: Batch process multiple files using CSV metadata."""
    print("Example 2: Batch Processing with CSV")
    print("-" * 50)
    
    # NOTE: You need to provide your own paths
    csv_file = "path/to/metadata.csv"
    audio_directory = "path/to/audio_files/"
    output_directory = "path/to/spectrograms/"
    
    # CSV should have columns: filename, category
    # Example CSV content:
    # filename,category
    # audio1.wav,class_a
    # audio2.wav,class_b
    # video1.mp4,class_a
    
    if os.path.exists(csv_file):
        process_video_chunks_to_spectrograms(
            csv_path=csv_file,
            audio_root=audio_directory,
            spectrogram_root=output_directory
        )
        print(f"✓ All spectrograms saved to: {output_directory}")
    else:
        print(f"⚠ CSV file not found: {csv_file}")
        print("Please update the paths in this script")
    print()


def example_esc50_dataset():
    """Example 3: Process ESC-50 dataset (if you have it)."""
    print("Example 3: ESC-50 Dataset Processing")
    print("-" * 50)
    
    # Example paths for ESC-50 dataset
    # Download from: https://github.com/karolpiczak/ESC-50
    csv_file = "/path/to/ESC-50-master/meta/esc50.csv"
    audio_directory = "/path/to/ESC-50-master/audio"
    output_directory = "/path/to/ESC-50-master/spectrogram"
    
    if os.path.exists(csv_file):
        process_video_chunks_to_spectrograms(
            csv_path=csv_file,
            audio_root=audio_directory,
            spectrogram_root=output_directory
        )
        print(f"✓ ESC-50 spectrograms saved to: {output_directory}")
    else:
        print(f"⚠ ESC-50 dataset not found at: {csv_file}")
        print("Download ESC-50 from: https://github.com/karolpiczak/ESC-50")
    print()


def example_custom_parameters():
    """Example 4: Using custom parameters for spectrogram generation."""
    print("Example 4: Custom Parameters")
    print("-" * 50)
    
    audio_file = "path/to/your/audio.wav"
    output_file = "path/to/output/spectrogram_custom.jpg"
    
    if os.path.exists(audio_file):
        plot_spectrogram(
            location=audio_file,
            plotpath=output_file,
            binsize=2048,      # Larger binsize = better frequency resolution
            colormap="viridis" # Different colormap for better visualization
        )
        print(f"✓ Custom spectrogram saved to: {output_file}")
        print("  Parameters: binsize=2048, colormap=viridis")
    else:
        print(f"⚠ Audio file not found: {audio_file}")
    print()


def main():
    """Run all examples."""
    print("=" * 50)
    print("Video to Spectrogram Conversion Examples")
    print("=" * 50)
    print()
    
    # Run examples
    example_single_file()
    example_batch_processing()
    example_esc50_dataset()
    example_custom_parameters()
    
    print("=" * 50)
    print("Examples completed!")
    print()
    print("To use these examples:")
    print("1. Update the file paths in this script")
    print("2. Ensure you have the required dependencies installed:")
    print("   pip install numpy scipy matplotlib pandas")
    print("3. Run: python examples/video_to_spectrogram_example.py")
    print()
    print("For more information, see VIDEO_TO_SPECTROGRAM_README.md")
    print("=" * 50)


if __name__ == '__main__':
    main()
