#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple example showing audio spectrogram processing workflow.

This example demonstrates:
1. Chunking a short audio file
2. Generating spectrograms
3. Creating a video from spectrograms
"""

import sys
import os
import tempfile
import numpy as np
import soundfile as sf

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.audio_processing import (
    chunk_audio_wav_or_mp3,
    process_chunks_to_spectrograms,
    create_video_from_spectrograms
)


def create_sample_audio(duration=3.0, sample_rate=22050):
    """Create a simple test audio file with multiple frequencies"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a simple melody (440Hz, 523Hz, 659Hz - A, C, E notes)
    audio = np.zeros_like(t)
    
    # First second: 440 Hz (A note)
    mask1 = t < 1.0
    audio[mask1] = 0.5 * np.sin(2 * np.pi * 440 * t[mask1])
    
    # Second second: 523 Hz (C note)
    mask2 = (t >= 1.0) & (t < 2.0)
    audio[mask2] = 0.5 * np.sin(2 * np.pi * 523 * t[mask2])
    
    # Third second: 659 Hz (E note)
    mask3 = t >= 2.0
    audio[mask3] = 0.5 * np.sin(2 * np.pi * 659 * t[mask3])
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_file.close()
    sf.write(temp_file.name, audio, sample_rate)
    
    return temp_file.name


def main():
    """Run the simple example workflow"""
    print("="*70)
    print("Simple Audio Spectrogram Processing Example")
    print("="*70)
    print()
    
    # Create temporary directories
    temp_dir = tempfile.mkdtemp()
    chunks_dir = os.path.join(temp_dir, "chunks")
    spectro_dir = os.path.join(temp_dir, "spectrograms")
    output_video = os.path.join(temp_dir, "output.mp4")
    
    try:
        # Step 1: Create sample audio
        print("Step 1: Creating sample audio (3 seconds, A-C-E notes)...")
        audio_file = create_sample_audio(duration=3.0)
        print(f"✓ Created: {audio_file}")
        print()
        
        # Step 2: Chunk audio
        print("Step 2: Chunking audio into 1-second segments...")
        num_chunks = chunk_audio_wav_or_mp3(
            input_audio=audio_file,
            output_folder=chunks_dir,
            chunk_duration=1.0,   # 1 second chunks
            step_duration=0.5     # 0.5 second overlap
        )
        print(f"✓ Created {num_chunks} chunks")
        print()
        
        # Step 3: Generate spectrograms
        print("Step 3: Generating spectrograms...")
        num_spectros = process_chunks_to_spectrograms(
            chunks_folder=chunks_dir,
            spectro_output_folder=spectro_dir
        )
        print(f"✓ Created {num_spectros} spectrograms")
        print()
        
        # Step 4: Create video
        print("Step 4: Creating video from spectrograms...")
        video_path = create_video_from_spectrograms(
            input_folder=spectro_dir,
            output_video_path=output_video,
            fps=2  # 2 frames per second (slower playback)
        )
        print(f"✓ Created video: {video_path}")
        print()
        
        # Summary
        print("="*70)
        print("Example completed successfully!")
        print("="*70)
        print()
        print("Generated files:")
        print(f"  Audio file:     {audio_file}")
        print(f"  Chunks folder:  {chunks_dir}")
        print(f"  Spectrograms:   {spectro_dir}")
        print(f"  Output video:   {video_path}")
        print()
        print("To view the results:")
        print(f"  - Open {video_path} to see the spectrogram video")
        print(f"  - Check {spectro_dir} for individual spectrogram images")
        print()
        print("Note: Files are in a temporary directory and will be deleted")
        print("      when you close this terminal. Copy them if you want to keep them.")
        print()
        
        # Keep files until user confirms
        input("Press Enter to clean up temporary files and exit...")
        
    finally:
        # Cleanup (optional - temp files are auto-deleted on system restart)
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print("✓ Temporary files cleaned up")


if __name__ == '__main__':
    main()
