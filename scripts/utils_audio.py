#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio utility functions for audio diagnostic agent.
Provides functions for extracting audio, computing spectrograms, and analyzing frequency bands.
"""

import subprocess
import json
import os
import numpy as np
import librosa
import soundfile as sf
import matplotlib.pyplot as plt
from typing import Tuple, Optional, Dict


def get_sample_rate(video_path: str) -> Optional[int]:
    """
    Get the original audio sample rate from a video file using ffprobe.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Sample rate in Hz, or None if extraction fails
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a:0',
            '-show_entries', 'stream=sample_rate',
            '-of', 'json',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if 'streams' in data and len(data['streams']) > 0:
            sample_rate = int(data['streams'][0].get('sample_rate', 0))
            return sample_rate if sample_rate > 0 else None
            
        return None
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error getting sample rate from {video_path}: {e}")
        return None


def extract_audio_wav(video_path: str, output_wav_path: str, sample_rate: Optional[int] = None) -> bool:
    """
    Extract audio from video to WAV format, preserving original sample rate if not specified.
    
    Args:
        video_path: Path to the video file
        output_wav_path: Path for the output WAV file
        sample_rate: Target sample rate (if None, uses original)
        
    Returns:
        True if extraction succeeded, False otherwise
    """
    try:
        cmd = ['ffmpeg', '-y', '-i', video_path]
        
        if sample_rate is not None:
            cmd.extend(['-ar', str(sample_rate)])
            
        cmd.extend([
            '-ac', '1',  # mono
            '-acodec', 'pcm_s16le',
            output_wav_path
        ])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_wav_path):
            return True
        else:
            print(f"ffmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error extracting audio from {video_path}: {e}")
        return False


def compute_mel_spectrogram(
    audio_path: str,
    sr: Optional[int] = None,
    n_fft: int = 2048,
    hop_length: int = 512,
    n_mels: int = 128,
    fmin: float = 0.0,
    fmax: Optional[float] = None
) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """
    Compute Mel spectrogram from audio file.
    
    Args:
        audio_path: Path to audio file (WAV format)
        sr: Target sample rate (if None, uses native rate)
        n_fft: FFT window size
        hop_length: Number of samples between successive frames
        n_mels: Number of Mel bands
        fmin: Minimum frequency
        fmax: Maximum frequency (if None, uses sr/2)
        
    Returns:
        Tuple of (mel_spectrogram in dB, actual sample rate used), or (None, None) on error
    """
    try:
        # Load audio
        y, actual_sr = librosa.load(audio_path, sr=sr, mono=True)
        
        if fmax is None:
            fmax = actual_sr / 2.0
            
        # Compute Mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=actual_sr,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
            fmin=fmin,
            fmax=fmax
        )
        
        # Convert to dB scale
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        return mel_spec_db, actual_sr
        
    except Exception as e:
        print(f"Error computing mel spectrogram from {audio_path}: {e}")
        return None, None


def measure_energy_in_band(
    mel_spec_db: np.ndarray,
    freq_min: float,
    freq_max: float,
    sr: int,
    n_mels: int,
    fmin: float = 0.0,
    fmax: Optional[float] = None
) -> float:
    """
    Measure average energy in a specific frequency band of the Mel spectrogram.
    
    Args:
        mel_spec_db: Mel spectrogram in dB
        freq_min: Lower bound of frequency band (Hz)
        freq_max: Upper bound of frequency band (Hz)
        sr: Sample rate used for the spectrogram
        n_mels: Number of Mel bands
        fmin: Minimum frequency of the spectrogram
        fmax: Maximum frequency of the spectrogram (if None, uses sr/2)
        
    Returns:
        Average energy in dB within the specified band
    """
    if fmax is None:
        fmax = sr / 2.0
        
    # Convert Hz to Mel scale
    mel_min = librosa.hz_to_mel(freq_min)
    mel_max = librosa.hz_to_mel(freq_max)
    mel_fmin = librosa.hz_to_mel(fmin)
    mel_fmax = librosa.hz_to_mel(fmax)
    
    # Find corresponding Mel bin indices
    mel_range = mel_fmax - mel_fmin
    bin_min = int(((mel_min - mel_fmin) / mel_range) * n_mels)
    bin_max = int(((mel_max - mel_fmin) / mel_range) * n_mels)
    
    # Clamp to valid range
    bin_min = max(0, min(bin_min, n_mels - 1))
    bin_max = max(0, min(bin_max, n_mels - 1))
    
    if bin_min >= bin_max:
        bin_max = bin_min + 1
        
    # Extract energy in the band
    band_energy = mel_spec_db[bin_min:bin_max, :]
    
    # Return mean energy
    return float(np.mean(band_energy))


def save_spectrogram_image(
    mel_spec_db: np.ndarray,
    output_path: str,
    sr: int,
    hop_length: int,
    title: str = "Mel Spectrogram"
) -> bool:
    """
    Save Mel spectrogram as PNG image.
    
    Args:
        mel_spec_db: Mel spectrogram in dB
        output_path: Path for output PNG file
        sr: Sample rate
        hop_length: Hop length used in spectrogram computation
        title: Title for the plot
        
    Returns:
        True if save succeeded, False otherwise
    """
    try:
        plt.figure(figsize=(10, 4))
        librosa.display.specshow(
            mel_spec_db,
            sr=sr,
            hop_length=hop_length,
            x_axis='time',
            y_axis='mel',
            cmap='viridis'
        )
        plt.colorbar(format='%+2.0f dB')
        plt.title(title)
        plt.tight_layout()
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        return True
        
    except Exception as e:
        print(f"Error saving spectrogram image to {output_path}: {e}")
        return False
