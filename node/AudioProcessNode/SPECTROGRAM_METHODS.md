# Spectrogram Node - Methods Documentation

## Overview
The Spectrogram node provides four different methods for visualizing audio data, each with distinct characteristics and use cases.

## Available Methods

### 1. Mel Spectrogram (mel)
**Default method** - Frequency representation on a mel scale, which better matches human perception of pitch.

- **Best for:** Music analysis, speech processing, general audio visualization
- **Output:** Frequency bins arranged on a perceptual mel scale
- **Colormap:** INFERNO (red-yellow-white gradient)
- **Characteristics:**
  - Non-linear frequency spacing (more detail in lower frequencies)
  - Perceptually meaningful representation
  - Standard for music information retrieval tasks

### 2. STFT Spectrogram (stft)
**Linear frequency** - Short-Time Fourier Transform with linear frequency spacing.

- **Best for:** Technical audio analysis, precise frequency measurements
- **Output:** Linear frequency bins from 0 Hz to Nyquist frequency
- **Colormap:** VIRIDIS (purple-blue-green-yellow gradient)
- **Characteristics:**
  - Linear frequency spacing (equal Hz per bin)
  - More detail in higher frequencies
  - Better for identifying exact frequencies

### 3. Chromagram (chromagram)
**Pitch class representation** - Shows the intensity of the 12 pitch classes (C, C#, D, etc.).

- **Best for:** Music theory analysis, chord detection, key detection
- **Output:** 12 bins representing the chromatic scale
- **Colormap:** PLASMA (blue-purple-orange-yellow gradient)
- **Characteristics:**
  - Octave-invariant (all C notes combined regardless of octave)
  - Only 12 frequency bins (one per semitone)
  - Excellent for harmonic analysis

### 4. MFCC (mfcc)
**Mel-Frequency Cepstral Coefficients** - Compact representation of the spectral envelope.

- **Best for:** Speech recognition, speaker identification, audio classification
- **Output:** 20 cepstral coefficients
- **Colormap:** JET (blue-cyan-green-yellow-red gradient)
- **Characteristics:**
  - Very compact representation (only 20 bins)
  - Captures timbral characteristics
  - Standard for speech and audio ML applications

## Usage in Node

1. Add a Spectrogram node from the AudioProcess menu
2. Connect an audio input to the node
3. Select the desired method from the dropdown menu:
   - **mel** - Mel Spectrogram (default)
   - **stft** - Linear STFT Spectrogram
   - **chromagram** - Pitch Class Chromagram
   - **mfcc** - MFCC Coefficients
4. The visualization updates automatically when the method is changed

## Technical Details

### Common Parameters
All methods use the same underlying parameters:
- **n_fft:** 2048 - FFT window size
- **hop_length:** 512 - Samples between successive frames
- **sample_rate:** Inherited from audio input (default 22050 Hz)

### Output Dimensions
The output dimensions vary by method:
- **mel:** 128 frequency bins × time frames × 3 (RGB)
- **stft:** 1025 frequency bins × time frames × 3 (RGB)
- **chromagram:** 12 pitch classes × time frames × 3 (RGB)
- **mfcc:** 20 coefficients × time frames × 3 (RGB)

## Persistence
The selected method is saved when you export the graph to JSON and restored when you import it.

## Examples

### Music Analysis Pipeline
```
Audio Input → Spectrogram (chromagram) → Display
```
Use chromagram to visualize chord progressions and key changes.

### Speech Processing Pipeline
```
Audio Input → Spectrogram (mfcc) → ML Model
```
Use MFCC for speech recognition or speaker identification tasks.

### General Audio Visualization
```
Audio Input → Spectrogram (mel) → Video Overlay
```
Use mel spectrogram for aesthetically pleasing audio visualization.

### Frequency Analysis
```
Audio Input → Spectrogram (stft) → Display
```
Use STFT for precise frequency measurement and analysis.

## Implementation Notes

Each method is implemented as a separate function:
- `create_mel_spectrogram()`
- `create_stft_spectrogram()`
- `create_chromagram()`
- `create_mfcc()`

The main `create_spectrogram()` function dispatches to the appropriate method based on the `method` parameter.

## Color Maps

Each method uses a different OpenCV colormap optimized for that visualization type:
- **INFERNO:** High contrast, perceptually uniform (mel)
- **VIRIDIS:** Perceptually uniform, good for linear data (stft)
- **PLASMA:** Vibrant colors, good for pitch data (chromagram)
- **JET:** Full rainbow spectrum, traditional for scientific data (mfcc)

All outputs are flipped vertically so that low frequencies appear at the bottom and high frequencies at the top.
