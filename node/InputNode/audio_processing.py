#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Audio processing utilities for CV_Studio.

This module provides utilities for:
- Chunking audio files with sliding windows
- Creating spectrograms from audio chunks
- Generating annotated videos from spectrograms
"""

import os
import numpy as np
import soundfile as sf
import librosa
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt
from numpy.lib import stride_tricks
import cv2
from PIL import Image, ImageDraw, ImageFont


def chunk_audio_wav_or_mp3(input_audio, output_folder, chunk_duration=5.0, step_duration=0.25):
    """
    Chunk audio file (WAV or MP3) into overlapping segments.
    
    Args:
        input_audio: Path to input audio file (.wav or .mp3)
        output_folder: Directory to save audio chunks
        chunk_duration: Duration of each chunk in seconds (default 5.0)
        step_duration: Step duration between chunks in seconds (default 0.25)
        
    Returns:
        Number of chunks created
        
    Example:
        >>> chunk_audio_wav_or_mp3('input.mp3', 'chunks/', chunk_duration=5.0, step_duration=0.25)
        Created 100 chunks
    """
    os.makedirs(output_folder, exist_ok=True)

    print(f"📥 Loading: {input_audio}")
    try:
        # Load audio with librosa - supports .wav, .mp3, etc.
        data, rate = librosa.load(input_audio, sr=None, mono=True)
    except Exception as e:
        print(f"❌ Error loading audio: {e}")
        return 0

    total_duration = len(data) / rate
    chunk_samples = int(chunk_duration * rate)
    step_samples = int(step_duration * rate)

    start = 0
    count = 1

    print(f"🔍 Sample rate: {rate} Hz")
    print(f"⏱️  Total duration: {total_duration:.2f}s")
    print("🚀 Chunking in progress...")

    while (start + chunk_samples) <= len(data):
        end = start + chunk_samples
        chunk = data[start:end]
        output_path = os.path.join(output_folder, f"chunk_{count}.wav")
        sf.write(output_path, chunk, rate)
        print(f"✅ chunk_{count}.wav: {start / rate:.2f}s → {end / rate:.2f}s")
        count += 1
        start += step_samples

    print(f"\n🎉 {count - 1} chunks saved to {output_folder}")
    return count - 1


def fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning):
    """
    Perform Short-Time Fourier Transform with windowing and overlap.
    
    Args:
        sig: Input signal
        frameSize: Size of each frame (window)
        overlapFac: Overlap factor (0.5 = 50% overlap)
        window: Window function to apply (default: np.hanning)
    
    Returns:
        STFT matrix (complex values)
    """
    win = window(frameSize)
    hopSize = int(frameSize - np.floor(overlapFac * frameSize))

    # Pad at beginning (center of 1st window at sample 0)
    samples = np.append(np.zeros(int(np.floor(frameSize/2.0))), sig)
    # Calculate number of columns
    cols = np.ceil((len(samples) - frameSize) / float(hopSize)) + 1
    # Pad at end (so samples can be fully covered by frames)
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
        sr: Sample rate (default 44100)
        factor: Scaling factor (higher = more emphasis on low frequencies)
    
    Returns:
        tuple: (newspec, freqs) - Rescaled spectrogram and corresponding frequencies
    """
    timebins, freqbins = np.shape(spec)

    scale = np.linspace(0, 1, freqbins) ** factor
    scale *= (freqbins-1)/max(scale)
    scale = np.unique(np.round(scale))

    # Create spectrogram with new freq bins
    newspec = np.complex128(np.zeros([timebins, len(scale)]))
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):], axis=1)
        else:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):int(scale[i+1])], axis=1)

    # List center freq of bins
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
    Generate and save a spectrogram image from an audio file.
    
    Args:
        location: Path to audio file (.wav)
        plotpath: Path to save spectrogram image (if None, display only)
        binsize: FFT bin size (default 1024)
        colormap: Matplotlib colormap name (default "jet")
        
    Returns:
        Spectrogram intensity matrix (in decibels)
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


def process_chunks_to_spectrograms(chunks_folder, spectro_output_folder, category="default"):
    """
    Convert all audio chunks in a folder to spectrogram images.
    
    Args:
        chunks_folder: Folder containing audio chunk files (.wav)
        spectro_output_folder: Output folder for spectrogram images
        category: Category name for organization (optional)
        
    Returns:
        Number of spectrograms created
    """
    os.makedirs(spectro_output_folder, exist_ok=True)

    count = 0
    for filename in sorted(os.listdir(chunks_folder)):
        if filename.endswith(".wav"):
            audio_path = os.path.join(chunks_folder, filename)
            base_name = os.path.splitext(filename)[0]
            save_path = os.path.join(spectro_output_folder, f"{base_name}.png")

            print(f"Creating spectrogram for {filename}...")
            try:
                plot_spectrogram(audio_path, plotpath=save_path)
                count += 1
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    print(f"\n🎉 Created {count} spectrograms in {spectro_output_folder}")
    return count


def get_linux_font(size=24):
    """
    Load a TrueType font for Linux systems.
    
    Args:
        size: Font size in points
        
    Returns:
        ImageFont object
    """
    linux_font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]

    for font_path in linux_font_paths:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except Exception:
            continue

    # Fallback to default font
    return ImageFont.load_default()


def annotate_image_with_classification(input_image_path, output_image_path, predictions):
    """
    Annotate an image with classification predictions.
    
    Args:
        input_image_path: Path to input image
        output_image_path: Path to save annotated image
        predictions: List of (label, score) tuples for top predictions
        
    Example:
        >>> predictions = [("Dog", 0.95), ("Cat", 0.03), ("Bird", 0.01)]
        >>> annotate_image_with_classification("input.png", "output.png", predictions)
    """
    image = Image.open(input_image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Font sizes decrease for each rank
    font_sizes = [56, 42, 32]
    colors = ['#00FF00', '#FFFF00', '#FF8800']  # Green, Yellow, Orange

    def draw_text_with_outline(draw, position, text, font, fill='white', outline='black', outline_width=3):
        x, y = position
        # Draw black outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline)
        # Draw main text
        draw.text(position, text, font=font, fill=fill)

    # Position at top center
    image_width = image.width
    y_position = 20

    # Draw each prediction with specific size and color
    for i, (label, score) in enumerate(predictions[:3]):
        font_size = font_sizes[i] if i < len(font_sizes) else font_sizes[-1]
        font = get_linux_font(font_size)
        color = colors[i] if i < len(colors) else colors[-1]

        # Text without percentage
        text = label

        # Calculate centered position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x_position = (image_width - text_width) // 2

        # Draw centered text
        draw_text_with_outline(draw, (x_position, y_position), text, font,
                             fill=color, outline='black', outline_width=3)

        # Move to next line
        y_position += text_height + 10

    image.save(output_image_path)
    print(f"✅ Annotated image saved: {output_image_path}")


def create_video_from_spectrograms(input_folder, output_video_path, fps=4):
    """
    Create a video from a sequence of spectrogram images.
    
    Args:
        input_folder: Folder containing chunk_XXX.png images
        output_video_path: Path for output video file
        fps: Frames per second for the video (default 4)
        
    Returns:
        Path to created video
        
    Example:
        >>> create_video_from_spectrograms('spectrograms/', 'output.mp4', fps=4)
        'output.mp4'
    """
    import re

    # Find all chunk files
    chunk_files = []
    chunk_pattern = re.compile(r'chunk_(\d+)\.png')

    for filename in os.listdir(input_folder):
        match = chunk_pattern.match(filename)
        if match:
            index = int(match.group(1))
            chunk_files.append((index, filename))

    # Sort by index
    chunk_files.sort(key=lambda x: x[0])

    if not chunk_files:
        print("❌ No chunk_XXX.png files found!")
        return None

    print(f"📊 {len(chunk_files)} chunks found")
    print(f"📊 Index range: {chunk_files[0][0]} to {chunk_files[-1][0]}")

    # Get dimensions from first image
    first_image_path = os.path.join(input_folder, chunk_files[0][1])
    first_image = cv2.imread(first_image_path)
    if first_image is None:
        print(f"❌ Cannot read image: {first_image_path}")
        return None

    height, width, channels = first_image.shape
    print(f"📐 Image dimensions: {width}x{height}")

    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    if not video_writer.isOpened():
        print("❌ Cannot open video writer!")
        return None

    # Each chunk displayed for 0.25 seconds
    frames_per_chunk = max(1, int(fps * 0.25))
    print(f"🎬 Creating video with {fps} fps...")
    print(f"📊 {frames_per_chunk} frame(s) per chunk")

    total_frames = 0
    for index, filename in chunk_files:
        image_path = os.path.join(input_folder, filename)
        image = cv2.imread(image_path)
        
        if image is None:
            print(f"⚠️  Cannot read {filename}, skipping")
            continue

        # Resize if needed
        if image.shape[:2] != (height, width):
            image = cv2.resize(image, (width, height))

        # Add chunk multiple times based on framerate
        for _ in range(frames_per_chunk):
            video_writer.write(image)
            total_frames += 1

    video_writer.release()

    final_duration = total_frames / fps
    print(f"✅ Video created: {output_video_path}")
    print(f"📊 {total_frames} total frames")
    print(f"⏱️  Duration: {final_duration:.2f} seconds")

    return output_video_path


def create_video_with_audio_sync(input_folder, output_video_path, audio_file=None, fps=4):
    """
    Create video from spectrograms with optional audio synchronization.
    
    Args:
        input_folder: Folder containing spectrogram images
        output_video_path: Path for output video file
        audio_file: Optional path to audio file to sync with video
        fps: Frames per second (default 4)
        
    Returns:
        Path to created video (with or without audio)
    """
    video_path = create_video_from_spectrograms(input_folder, output_video_path, fps)

    if video_path and audio_file and os.path.exists(audio_file):
        try:
            import subprocess
            output_with_audio = output_video_path.replace('.mp4', '_with_audio.mp4')

            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_file,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',
                output_with_audio
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"🎵 Video with audio created: {output_with_audio}")
                return output_with_audio
            else:
                print(f"⚠️  ffmpeg error: {result.stderr}")
                return video_path

        except Exception as e:
            print(f"⚠️  Cannot add audio: {e}")
            return video_path

    return video_path
