#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions for spectrogram colormap application.

This module provides utilities for applying colormaps to 2D spectrogram arrays,
converting them to colored RGB images for better visualization and event detection.
"""

import os
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend to prevent display
import matplotlib.cm as cm
from matplotlib import pyplot as plt
from numpy.lib import stride_tricks
try:
    import scipy.io.wavfile as wav
except ImportError:
    wav = None


def apply_colormap_cv2(spectrogram_2d, colormap=cv2.COLORMAP_INFERNO):
    """
    Apply colormap to a 2D spectrogram using OpenCV (fast and efficient).
    
    Args:
        spectrogram_2d: np.ndarray with shape (H, W), dtype float or int
                       Represents amplitude/dB values of the spectrogram
        colormap: OpenCV colormap constant (e.g., cv2.COLORMAP_INFERNO, 
                 cv2.COLORMAP_VIRIDIS, cv2.COLORMAP_JET)
    
    Returns:
        np.ndarray: RGB image with shape (H, W, 3) and dtype uint8
    
    Raises:
        ValueError: If input is not 2D
    """
    if spectrogram_2d.ndim != 2:
        raise ValueError("spectrogram_2d must be 2D")
    
    # Normalize to 0..255
    norm = cv2.normalize(spectrogram_2d, None, 0, 255, cv2.NORM_MINMAX)
    img_u8 = np.clip(norm, 0, 255).astype(np.uint8)
    
    # Apply colormap (returns BGR)
    colored_bgr = cv2.applyColorMap(img_u8, colormap)
    
    # Convert BGR to RGB
    colored_rgb = cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)
    
    return colored_rgb


def apply_colormap_mpl(spectrogram_2d, cmap_name='viridis'):
    """
    Apply colormap to a 2D spectrogram using matplotlib (fallback method).
    
    Args:
        spectrogram_2d: np.ndarray with shape (H, W), dtype float or int
                       Represents amplitude/dB values of the spectrogram
        cmap_name: Matplotlib colormap name (e.g., 'viridis', 'inferno', 'jet')
    
    Returns:
        np.ndarray: RGB image with shape (H, W, 3) and dtype uint8
    
    Raises:
        ValueError: If input is not 2D
    """
    if spectrogram_2d.ndim != 2:
        raise ValueError("spectrogram_2d must be 2D")
    
    # Get the colormap (use new API if available, fallback to deprecated)
    import matplotlib
    if hasattr(matplotlib, 'colormaps'):
        cmap = matplotlib.colormaps.get_cmap(cmap_name)
    else:
        cmap = cm.get_cmap(cmap_name)
    
    # Normalize to 0..1 range, handling edge cases
    min_val = np.nanmin(spectrogram_2d)
    max_val = np.nanmax(spectrogram_2d)
    denom = max_val - min_val
    
    if denom == 0 or not np.isfinite(denom):
        # All values are the same or invalid
        normed = np.full_like(spectrogram_2d, 0.5, dtype=np.float64)
    else:
        normed = (spectrogram_2d - min_val) / denom
    
    # Replace any non-finite values with 0
    normed = np.nan_to_num(normed, nan=0.0, posinf=1.0, neginf=0.0)
    
    # Apply colormap (returns RGBA with values in 0..1)
    rgba = cmap(normed)
    
    # Convert to RGB (discard alpha) and scale to 0..255
    rgb = (rgba[..., :3] * 255).astype(np.uint8)
    
    return rgb


def apply_colormap_to_spectrogram(arr2d, method='cv2', cmap='INFERNO'):
    """
    Robust wrapper for applying colormaps to spectrograms.
    Detects the method and applies the appropriate colormap function.
    
    Args:
        arr2d: np.ndarray with shape (H, W), dtype float or int
               2D spectrogram array
        method: 'cv2' (default, uses OpenCV) or 'mpl' (uses matplotlib)
        cmap: Colormap name. For 'cv2' method: 'INFERNO', 'VIRIDIS', 'JET', 
              'MAGMA', 'PLASMA', etc. For 'mpl' method: lowercase matplotlib 
              colormap names like 'inferno', 'viridis', 'jet', etc.
    
    Returns:
        np.ndarray: RGB image with shape (H, W, 3) and dtype uint8
    
    Raises:
        ValueError: If input is not 2D or method is not recognized
    """
    if arr2d.ndim != 2:
        raise ValueError("Input array must be 2D")
    
    if method == 'cv2':
        # Map string to OpenCV colormap constant
        cmap_upper = cmap.upper()
        colormap_attr = f"COLORMAP_{cmap_upper}"
        
        if hasattr(cv2, colormap_attr):
            cv_colormap = getattr(cv2, colormap_attr)
        else:
            # Default to INFERNO if colormap not found (use logging instead of print)
            import warnings
            warnings.warn(f"Colormap '{cmap}' not found, using INFERNO as fallback", UserWarning)
            cv_colormap = cv2.COLORMAP_INFERNO
        
        return apply_colormap_cv2(arr2d, colormap=cv_colormap)
    
    elif method == 'mpl':
        # Use matplotlib with lowercase colormap name
        cmap_name = cmap.lower()
        return apply_colormap_mpl(arr2d, cmap_name=cmap_name)
    
    else:
        raise ValueError(f"Unknown method '{method}'. Use 'cv2' or 'mpl'.")


# OpenCV colormap constants for reference
AVAILABLE_OPENCV_COLORMAPS = [
    'AUTUMN', 'BONE', 'JET', 'WINTER', 'RAINBOW', 'OCEAN', 'SUMMER',
    'SPRING', 'COOL', 'HSV', 'PINK', 'HOT', 'PARULA', 'MAGMA', 'INFERNO',
    'PLASMA', 'VIRIDIS', 'CIVIDIS', 'TWILIGHT', 'TWILIGHT_SHIFTED', 'TURBO'
]

# Reference amplitude for dB conversion (matching ESC-50 training code)
# IMPORTANT: The user's training code uses 10e-6, which mathematically equals 1e-5
# We preserve 10e-6 notation to exactly match the training code for traceability
# Formula: 20.*np.log10(np.abs(sshow)/10e-6) from the ESC-50 training implementation
REFERENCE_AMPLITUDE = 10e-6  # Do not change to 1e-5, must match training code exactly


def fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning):
    """
    Transformée de Fourier avec fenêtrage (STFT with windowing).
    
    Args:
        sig: Audio signal as numpy array
        frameSize: Size of the FFT window
        overlapFac: Overlap factor between frames (default 0.5 = 50% overlap)
        window: Window function (default np.hanning)
    
    Returns:
        np.ndarray: Complex-valued STFT result with shape (num_frames, frameSize//2+1)
    """
    win = window(frameSize)
    hopSize = int(frameSize - np.floor(overlapFac * frameSize))

    # Zeros au début pour centrer la première fenêtre sur l'échantillon 0
    samples = np.append(np.zeros(int(np.floor(frameSize/2.0))), sig)
    # Colonnes pour le fenêtrage
    cols = np.ceil((len(samples) - frameSize) / float(hopSize)) + 1
    # Zeros à la fin pour couvrir complètement les échantillons
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
    Convertit le spectrogramme en échelle logarithmique.
    
    Args:
        spec: Complex spectrogram array from FFT
        sr: Sample rate (default 44100)
        factor: Log scale factor (default 20.0)
    
    Returns:
        tuple: (newspec, freqs) where:
            - newspec: Log-scale spectrogram as complex array
            - freqs: List of center frequencies for each bin
    """
    timebins, freqbins = np.shape(spec)

    scale = np.linspace(0, 1, freqbins) ** factor
    scale *= (freqbins-1)/max(scale)
    scale = np.unique(np.round(scale))

    # Créer le spectrogramme avec les nouvelles bins de fréquence
    newspec = np.zeros([timebins, len(scale)], dtype=np.complex128)
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):], axis=1)
        else:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):int(scale[i+1])], axis=1)

    # Lister les fréquences centrales des bins
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
    Crée et sauvegarde un spectrogramme à partir d'un fichier audio.
    
    Args:
        location: Chemin du fichier audio (.wav)
        plotpath: Chemin de sauvegarde de l'image (si None, utilise un fichier temporaire)
        binsize: Taille de la fenêtre FFT (par défaut 1024)
        colormap: Colormap matplotlib à utiliser
    
    Returns:
        ims: Matrice du spectrogramme en décibels
    """
    if wav is None:
        raise ImportError("scipy is required for plot_spectrogram. Install with: pip install scipy")
    
    # Lire le fichier audio
    samplerate, samples = wav.read(location)
    
    # Appliquer la transformée de Fourier
    s = fourier_transformation(samples, binsize)
    
    # Convertir en échelle logarithmique
    sshow, freq = make_logscale(s, factor=1.0, sr=samplerate)
    
    # Convertir l'amplitude en décibels
    ims = 20. * np.log10(np.abs(sshow) / REFERENCE_AMPLITUDE)

    timebins, freqbins = np.shape(ims)

    # Créer la figure
    plt.figure(figsize=(15, 7.5))
    plt.imshow(
        np.transpose(ims), 
        origin="lower", 
        aspect="auto", 
        cmap=colormap, 
        interpolation="none"
    )
    
    # Configurer les axes X (temps)
    xlocs = np.float32(np.linspace(0, timebins-1, 5))
    plt.xticks(
        xlocs, 
        ["%.02f" % l for l in ((xlocs*len(samples)/timebins)+(0.5*binsize))/samplerate]
    )
    
    # Configurer les axes Y (fréquence)
    ylocs = np.int16(np.round(np.linspace(0, freqbins-1, 10)))
    plt.yticks(ylocs, ["%.02f" % freq[i] for i in ylocs])

    # Always save to a file instead of displaying
    if plotpath is None:
        # Use a temporary file if no path is provided
        import tempfile
        fd, plotpath = tempfile.mkstemp(suffix='.png', prefix='spectrogram_')
        os.close(fd)  # Close file descriptor, we'll use the path
    
    plt.savefig(plotpath, bbox_inches="tight")
    plt.clf()

    return ims


def create_spectrogram_from_audio(audio_data, sample_rate=44100, binsize=2**10, colormap="jet"):
    """
    Create a spectrogram image from audio data using STFT.
    
    This function uses the fourier_transformation and make_logscale approach
    to create spectrograms compatible with the CV Studio node system.
    
    Args:
        audio_data: numpy array of audio samples
        sample_rate: sample rate of the audio (default 44100, ESC-50 native)
        binsize: FFT window size (default 1024)
        colormap: colormap name for visualization (default "jet")
    
    Returns:
        np.ndarray: RGB image of the spectrogram with shape (H, W, 3) and dtype uint8
    """
    if audio_data is None or len(audio_data) == 0:
        return None
    
    # Appliquer la transformée de Fourier
    s = fourier_transformation(audio_data, binsize)
    
    # Convertir en échelle logarithmique
    sshow, freq = make_logscale(s, factor=1.0, sr=sample_rate)
    
    # Convertir l'amplitude en décibels
    ims = 20. * np.log10(np.abs(sshow) / REFERENCE_AMPLITUDE)
    
    # Transpose to get correct orientation (frequencies on Y-axis)
    ims_transposed = np.transpose(ims)
    
    # Apply colormap using existing utility
    # Map common matplotlib colormap names to OpenCV
    colormap_mapping = {
        'jet': 'JET',
        'viridis': 'VIRIDIS',
        'inferno': 'INFERNO',
        'plasma': 'PLASMA',
        'magma': 'MAGMA',
        'hot': 'HOT',
    }
    
    cv_colormap = colormap_mapping.get(colormap.lower(), 'JET')
    
    try:
        # Use OpenCV colormap application
        colored_spec = apply_colormap_to_spectrogram(ims_transposed, method='cv2', cmap=cv_colormap)
    except Exception:
        # Fallback to matplotlib colormap
        colored_spec = apply_colormap_to_spectrogram(ims_transposed, method='mpl', cmap=colormap.lower())
    
    # Flip vertically so low frequencies are at the bottom
    colored_spec = np.flipud(colored_spec)
    
    return colored_spec
