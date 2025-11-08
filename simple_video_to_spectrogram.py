#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple Video Chunk to Spectrogram Converter

This script demonstrates using the fourier_transformation and make_logscale 
functions to convert video chunks (audio) into spectrogram images, following
the example provided in the problem statement.

Example usage similar to the ESC-50 dataset processing.
"""

import os
import pandas as pd
import scipy.io.wavfile as wav
import numpy as np
import matplotlib.pyplot as plt
from numpy.lib import stride_tricks


def fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning):
    """
    Perform Short-Time Fourier Transform with windowing and overlap.
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
    Apply logarithmic scaling to frequency bins.
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
    This function follows the exact structure from the problem statement.
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

    return ims


def process_video_chunks_to_spectrograms(csv_path, audio_root, spectrogram_root):
    """
    Process video chunks (audio files) into spectrogram images.
    
    This follows the exact pattern from the problem statement for ESC-50 processing.
    
    Args:
        csv_path: Path to CSV file with columns 'filename' and 'category'
        audio_root: Root directory containing audio files
        spectrogram_root: Root directory where spectrograms will be saved
    """
    # Charger le CSV
    esc50_df = pd.read_csv(csv_path)

    # Créer les dossiers
    os.makedirs(spectrogram_root, exist_ok=True)

    for cat in esc50_df['category'].unique():
        os.makedirs(os.path.join(spectrogram_root, cat), exist_ok=True)

    # Générer tous les spectrogrammes
    for i, row in esc50_df.iterrows():
        filename = row['filename']
        category = row['category']
        audio_path = os.path.join(audio_root, filename)
        save_path = os.path.join(spectrogram_root, category, filename.replace('.wav', '.jpg'))

        try:
            plot_spectrogram(audio_path, plotpath=save_path)
            print(f"Processed {i+1}/{len(esc50_df)}: {filename}")
        except Exception as e:
            print(f"Erreur avec {filename}: {e}")


if __name__ == '__main__':
    # Example usage - adjust paths as needed
    
    # Example 1: Process ESC-50 dataset (if you have it)
    # process_video_chunks_to_spectrograms(
    #     csv_path='/path/to/ESC-50-master/meta/esc50.csv',
    #     audio_root='/path/to/ESC-50-master/audio',
    #     spectrogram_root='/path/to/ESC-50-master/spectrogram'
    # )
    
    # Example 2: Process a single audio file
    # plot_spectrogram(
    #     location='/path/to/audio.wav',
    #     plotpath='/path/to/output/spectrogram.jpg'
    # )
    
    print("Video chunk to spectrogram converter ready.")
    print("Uncomment the example usage above or import this module to use the functions.")
