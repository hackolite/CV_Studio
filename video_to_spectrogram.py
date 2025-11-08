#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Video to Spectrogram Converter

This script converts audio from video files into spectrogram images using
the fourier_transformation and make_logscale functions from the node_video module.
It can process individual videos or batch process multiple videos using a CSV metadata file.

Usage:
    # Single video
    python video_to_spectrogram.py --input video.mp4 --output spectrogram.jpg
    
    # Batch processing with CSV
    python video_to_spectrogram.py --csv metadata.csv --audio-dir ./audio --output-dir ./spectrograms
"""

import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.io.wavfile as wav
import tempfile
import subprocess
from pathlib import Path

# Import the spectrogram functions from node_video
from numpy.lib import stride_tricks


def fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning):
    """
    Perform Short-Time Fourier Transform with windowing and overlap.
    
    Args:
        sig: Input signal
        frameSize: Size of each frame (window)
        overlapFac: Overlap factor (0.5 = 50% overlap)
        window: Window function to apply
    
    Returns:
        STFT matrix (complex values)
    """
    win = window(frameSize)
    hopSize = int(frameSize - np.floor(overlapFac * frameSize))

    # zeros at beginning (thus center of 1st window should be for sample nr. 0)
    samples = np.append(np.zeros(int(np.floor(frameSize/2.0))), sig)
    # cols for windowing
    cols = np.ceil((len(samples) - frameSize) / float(hopSize)) + 1
    # zeros at end (thus samples can be fully covered by frames)
    samples = np.append(samples, np.zeros(frameSize))

    frames = stride_tricks.as_strided(
        samples,
        shape=(int(cols), frameSize),
        strides=(samples.strides[0]*hopSize, samples.strides[0])
    ).copy()
    frames *= win

    return np.fft.rfft(frames)


def make_logscale(spec, sr=44100, factor=20.):
    """
    Apply logarithmic scaling to frequency bins for better low-frequency resolution.
    
    Args:
        spec: Spectrogram array (time x frequency)
        sr: Sample rate
        factor: Scaling factor (higher = more emphasis on low frequencies)
    
    Returns:
        (newspec, freqs): Rescaled spectrogram and corresponding frequencies
    """
    timebins, freqbins = np.shape(spec)

    scale = np.linspace(0, 1, freqbins) ** factor
    scale *= (freqbins-1)/max(scale)
    scale = np.unique(np.round(scale))

    # create spectrogram with new freq bins
    newspec = np.complex128(np.zeros([timebins, len(scale)]))
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):], axis=1)
        else:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):int(scale[i+1])], axis=1)

    # list center freq of bins
    allfreqs = np.abs(np.fft.fftfreq(freqbins*2, 1./sr)[:freqbins+1])
    freqs = []
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            freqs += [np.mean(allfreqs[int(scale[i]):])]
        else:
            freqs += [np.mean(allfreqs[int(scale[i]):int(scale[i+1])])]

    return newspec, freqs


def plot_spectrogram(location, plotpath=None, binsize=2**10, colormap="jet"):
    """
    Generate and save a spectrogram from an audio file.
    
    Args:
        location: Path to the audio file (.wav)
        plotpath: Path where to save the spectrogram image (optional)
        binsize: Size of FFT bins (default: 1024)
        colormap: Matplotlib colormap to use (default: "jet")
    
    Returns:
        ims: The spectrogram image array
    """
    samplerate, samples = wav.read(location)
    s = fourier_transformation(samples, binsize)
    sshow, freq = make_logscale(s, factor=1.0, sr=samplerate)
    ims = 20.*np.log10(np.abs(sshow)/10e-6)  # amplitude to decibel

    timebins, freqbins = np.shape(ims)

    plt.figure(figsize=(15, 7.5))
    plt.imshow(np.transpose(ims), origin="lower", aspect="auto", cmap=colormap, interpolation="none")
    xlocs = np.float32(np.linspace(0, timebins-1, 5))
    plt.xticks(xlocs, ["%.02f" % l for l in ((xlocs*len(samples)/timebins)+(0.5*binsize))/samplerate])
    ylocs = np.int16(np.round(np.linspace(0, freqbins-1, 10)))
    plt.yticks(ylocs, ["%.02f" % freq[i] for i in ylocs])

    if plotpath:
        plt.savefig(plotpath, bbox_inches="tight")
    else:
        plt.show()
    plt.clf()
    plt.close()

    return ims


def extract_audio_from_video(video_path, output_audio_path=None):
    """
    Extract audio from a video file using ffmpeg.
    
    Args:
        video_path: Path to the video file
        output_audio_path: Path where to save the extracted audio (optional)
    
    Returns:
        Path to the extracted audio file
    """
    if output_audio_path is None:
        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        output_audio_path = os.path.join(temp_dir, 'temp_audio.wav')
    
    # Use ffmpeg to extract audio
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # PCM 16-bit
        '-ar', '44100',  # Sample rate
        '-ac', '2',  # Stereo
        '-y',  # Overwrite output file
        output_audio_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_audio_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to extract audio from {video_path}: {e.stderr.decode()}")


def video_to_spectrogram(video_path, output_image_path, binsize=2**10, colormap="jet"):
    """
    Convert a video file to a spectrogram image.
    
    Args:
        video_path: Path to the video file
        output_image_path: Path where to save the spectrogram image
        binsize: Size of FFT bins (default: 1024)
        colormap: Matplotlib colormap to use (default: "jet")
    
    Returns:
        The spectrogram image array
    """
    # Extract audio from video
    audio_path = extract_audio_from_video(video_path)
    
    try:
        # Generate spectrogram
        ims = plot_spectrogram(audio_path, plotpath=output_image_path, binsize=binsize, colormap=colormap)
        return ims
    finally:
        # Clean up temporary audio file
        if os.path.exists(audio_path) and 'temp_audio' in audio_path:
            os.remove(audio_path)


def batch_process_videos(csv_path, audio_dir, output_dir, binsize=2**10, colormap="jet"):
    """
    Batch process videos from a CSV file (similar to ESC-50 format).
    
    Args:
        csv_path: Path to the CSV file with metadata
        audio_dir: Directory containing audio/video files
        output_dir: Directory where to save spectrograms
        binsize: Size of FFT bins (default: 1024)
        colormap: Matplotlib colormap to use (default: "jet")
    
    Expected CSV format:
        - filename: Name of the audio/video file
        - category: Category/class of the file (optional)
    """
    # Load CSV
    df = pd.read_csv(csv_path)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create category subdirectories if category column exists
    if 'category' in df.columns:
        for cat in df['category'].unique():
            os.makedirs(os.path.join(output_dir, cat), exist_ok=True)
    
    # Process each file
    for i, row in df.iterrows():
        filename = row['filename']
        
        # Determine input path
        audio_path = os.path.join(audio_dir, filename)
        
        if not os.path.exists(audio_path):
            print(f"Warning: File not found: {audio_path}")
            continue
        
        # Determine output path
        if 'category' in df.columns:
            category = row['category']
            # Change extension to .jpg
            base_name = os.path.splitext(filename)[0] + '.jpg'
            save_path = os.path.join(output_dir, category, base_name)
        else:
            base_name = os.path.splitext(filename)[0] + '.jpg'
            save_path = os.path.join(output_dir, base_name)
        
        try:
            # Check if it's a video file (needs audio extraction) or audio file
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']:
                # Video file - extract audio first
                video_to_spectrogram(audio_path, save_path, binsize=binsize, colormap=colormap)
            else:
                # Audio file - process directly
                plot_spectrogram(audio_path, plotpath=save_path, binsize=binsize, colormap=colormap)
            
            print(f"Processed {i+1}/{len(df)}: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert video/audio files to spectrogram images'
    )
    
    # Mode selection
    parser.add_argument('--mode', choices=['single', 'batch'], default='single',
                        help='Processing mode: single file or batch')
    
    # Single file mode arguments
    parser.add_argument('--input', type=str,
                        help='Input video/audio file path (for single mode)')
    parser.add_argument('--output', type=str,
                        help='Output spectrogram image path (for single mode)')
    
    # Batch mode arguments
    parser.add_argument('--csv', type=str,
                        help='CSV file with metadata (for batch mode)')
    parser.add_argument('--audio-dir', type=str,
                        help='Directory containing audio/video files (for batch mode)')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for spectrograms (for batch mode)')
    
    # Common arguments
    parser.add_argument('--binsize', type=int, default=1024,
                        help='FFT bin size (default: 1024)')
    parser.add_argument('--colormap', type=str, default='jet',
                        help='Matplotlib colormap (default: jet)')
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        if not args.input or not args.output:
            parser.error("Single mode requires --input and --output arguments")
        
        # Process single file
        ext = os.path.splitext(args.input)[1].lower()
        if ext in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']:
            video_to_spectrogram(args.input, args.output, binsize=args.binsize, colormap=args.colormap)
        else:
            plot_spectrogram(args.input, plotpath=args.output, binsize=args.binsize, colormap=args.colormap)
        
        print(f"Spectrogram saved to: {args.output}")
    
    elif args.mode == 'batch':
        if not args.csv or not args.audio_dir or not args.output_dir:
            parser.error("Batch mode requires --csv, --audio-dir, and --output-dir arguments")
        
        # Batch process files
        batch_process_videos(args.csv, args.audio_dir, args.output_dir, 
                             binsize=args.binsize, colormap=args.colormap)
        
        print(f"All spectrograms saved to: {args.output_dir}")


if __name__ == '__main__':
    main()
