#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo script showing the complete audio spectrogram workflow.

This script demonstrates:
1. Downloading or using sample audio
2. Chunking audio into overlapping segments
3. Generating spectrograms from chunks
4. Creating a video from spectrograms
5. Optional: Annotating spectrograms with YOLO classification results
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.audio_processing import (
    chunk_audio_wav_or_mp3,
    process_chunks_to_spectrograms,
    create_video_from_spectrograms,
    create_video_with_audio_sync,
    annotate_image_with_classification
)


def demo_basic_workflow():
    """
    Demonstrate basic audio-to-spectrogram-to-video workflow.
    
    This workflow:
    1. Takes an audio file
    2. Chunks it into 5-second segments with 0.25s overlap
    3. Generates spectrograms for each chunk
    4. Creates a video from the spectrograms
    """
    print("="*70)
    print("DEMO: Basic Audio Spectrogram Workflow")
    print("="*70)
    print()
    
    # Configuration
    input_audio = "path/to/your/audio.wav"  # Replace with actual audio file
    chunks_folder = "./demo_chunks_audio"
    spectro_folder = "./demo_spectrograms"
    output_video = "./demo_output.mp4"
    
    # Check if audio file exists
    if not os.path.exists(input_audio):
        print(f"⚠️  Audio file not found: {input_audio}")
        print("Please provide a valid audio file path.")
        print()
        print("Example usage:")
        print(f"  python {__file__} /path/to/audio.wav")
        return
    
    print(f"Input audio: {input_audio}")
    print()
    
    # Step 1: Chunk the audio
    print("Step 1: Chunking audio...")
    print("-" * 70)
    num_chunks = chunk_audio_wav_or_mp3(
        input_audio=input_audio,
        output_folder=chunks_folder,
        chunk_duration=5.0,     # 5 seconds per chunk
        step_duration=0.25      # 0.25 second step (high overlap)
    )
    print()
    
    # Step 2: Generate spectrograms
    print("Step 2: Generating spectrograms...")
    print("-" * 70)
    num_spectros = process_chunks_to_spectrograms(
        chunks_folder=chunks_folder,
        spectro_output_folder=spectro_folder
    )
    print()
    
    # Step 3: Create video
    print("Step 3: Creating video from spectrograms...")
    print("-" * 70)
    video_path = create_video_from_spectrograms(
        input_folder=spectro_folder,
        output_video_path=output_video,
        fps=4  # 4 frames per second
    )
    print()
    
    print("="*70)
    print("✅ Demo completed successfully!")
    print("="*70)
    print(f"Output video: {video_path}")
    print(f"Chunks folder: {chunks_folder}")
    print(f"Spectrograms folder: {spectro_folder}")
    print()


def demo_with_audio_sync():
    """
    Demonstrate creating a video with synchronized audio.
    """
    print("="*70)
    print("DEMO: Spectrogram Video with Audio Sync")
    print("="*70)
    print()
    
    input_audio = "path/to/your/audio.wav"
    chunks_folder = "./demo_chunks_audio"
    spectro_folder = "./demo_spectrograms"
    output_video = "./demo_output_with_audio.mp4"
    
    if not os.path.exists(input_audio):
        print(f"⚠️  Audio file not found: {input_audio}")
        return
    
    # Chunk and generate spectrograms (same as basic workflow)
    print("Processing audio...")
    chunk_audio_wav_or_mp3(input_audio, chunks_folder, 5.0, 0.25)
    process_chunks_to_spectrograms(chunks_folder, spectro_folder)
    
    # Create video with audio sync
    print("\nCreating video with synchronized audio...")
    print("-" * 70)
    video_path = create_video_with_audio_sync(
        input_folder=spectro_folder,
        output_video_path=output_video,
        audio_file=input_audio,  # Original audio file
        fps=4
    )
    
    print()
    print("="*70)
    print("✅ Video with audio created!")
    print("="*70)
    print(f"Output: {video_path}")
    print()


def demo_with_classification():
    """
    Demonstrate annotating spectrograms with classification results.
    
    This would typically be used after running YOLO classification on spectrograms.
    """
    print("="*70)
    print("DEMO: Annotating Spectrograms with Classifications")
    print("="*70)
    print()
    
    # Example: Annotate a single spectrogram
    input_image = "./demo_spectrograms/chunk_1.png"
    output_image = "./demo_spectrograms_annotated/chunk_1.png"
    
    if not os.path.exists(input_image):
        print(f"⚠️  Spectrogram not found: {input_image}")
        print("Run the basic workflow first to generate spectrograms.")
        return
    
    # Mock predictions (in real usage, these would come from YOLO model)
    predictions = [
        ("Dog", 0.95),
        ("Cat", 0.03),
        ("Rain", 0.01)
    ]
    
    os.makedirs(os.path.dirname(output_image), exist_ok=True)
    
    print(f"Annotating: {input_image}")
    print(f"Predictions: {predictions}")
    annotate_image_with_classification(input_image, output_image, predictions)
    
    print()
    print("="*70)
    print("✅ Annotation completed!")
    print("="*70)
    print(f"Annotated image: {output_image}")
    print()


def print_usage():
    """Print usage information"""
    print("="*70)
    print("Audio Spectrogram Processing Demo")
    print("="*70)
    print()
    print("This demo shows how to:")
    print("  1. Chunk audio files into overlapping segments")
    print("  2. Generate spectrograms from audio chunks")
    print("  3. Create videos from spectrogram sequences")
    print("  4. Add audio synchronization to videos")
    print("  5. Annotate spectrograms with classification results")
    print()
    print("Usage:")
    print(f"  python {__file__} [audio_file]")
    print()
    print("Examples:")
    print(f"  python {__file__} myaudio.wav")
    print(f"  python {__file__} /path/to/audio.mp3")
    print()
    print("Workflow:")
    print("  1. Audio → Chunks (5s segments, 0.25s step)")
    print("  2. Chunks → Spectrograms (PNG images)")
    print("  3. Spectrograms → Video (MP4)")
    print()
    print("For ESC-50 dataset workflow:")
    print("  1. Download ESC-50 dataset")
    print("  2. Generate spectrograms for all audio files")
    print("  3. Train YOLO classifier on spectrograms")
    print("  4. Use trained model to classify new audio")
    print()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Run with provided audio file
        audio_file = sys.argv[1]
        
        if not os.path.exists(audio_file):
            print(f"❌ Error: Audio file not found: {audio_file}")
            sys.exit(1)
        
        # Override the demo configuration
        print(f"Using audio file: {audio_file}\n")
        
        # You can modify the demo functions to accept parameters
        # For now, just show usage
        print_usage()
        
    else:
        # Show usage and demos
        print_usage()
        
        print("Available demos:")
        print("  1. demo_basic_workflow()")
        print("  2. demo_with_audio_sync()")
        print("  3. demo_with_classification()")
        print()
        print("To run a demo, edit this file and call the desired function,")
        print("or import and use the functions from audio_processing module.")
        print()
