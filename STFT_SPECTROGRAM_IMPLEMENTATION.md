# STFT-based Spectrogram Implementation

## Overview

This implementation adds STFT-based (Short-Time Fourier Transform) spectrogram generation functions to CV Studio, inspired by the provided reference code. The spectrograms display correctly in the node system with proper frequency orientation and colormap application.

## Files Modified

### 1. `node/InputNode/spectrogram_utils.py`
Added STFT-based utility functions:

- **`fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning)`**
  - Implements STFT with windowing using numpy stride tricks
  - Parameters:
    - `sig`: Audio signal as numpy array
    - `frameSize`: Size of the FFT window (default 1024)
    - `overlapFac`: Overlap factor between frames (default 0.5 = 50%)
    - `window`: Window function (default Hanning window)
  - Returns: Complex-valued STFT result

- **`make_logscale(spec, sr=44100, factor=20.)`**
  - Converts spectrogram to logarithmic frequency scale
  - Parameters:
    - `spec`: Complex spectrogram array from FFT
    - `sr`: Sample rate (default 44100)
    - `factor`: Log scale factor (default 20.0)
  - Returns: (newspec, freqs) tuple with log-scale spectrogram and center frequencies

- **`plot_spectrogram(location, plotpath=None, binsize=2**10, colormap="jet")`**
  - Creates and saves a spectrogram from a WAV audio file
  - Parameters:
    - `location`: Path to WAV audio file
    - `plotpath`: Output image path (optional)
    - `binsize`: FFT window size (default 1024)
    - `colormap`: Matplotlib colormap name (default "jet")
  - Returns: dB spectrogram matrix

- **`create_spectrogram_from_audio(audio_data, sample_rate=22050, binsize=2**10, colormap="jet")`**
  - Creates RGB spectrogram image from audio data for node display
  - Uses the STFT approach with fourier_transformation and make_logscale
  - Returns: RGB image (H, W, 3) with dtype uint8

- **`REFERENCE_AMPLITUDE = 1e-6`**
  - Named constant for dB conversion (1 micropascal reference)

### 2. `node/AudioProcessNode/node_spectrogram.py`
Enhanced the Spectrogram node:

- Imported STFT-based functions from spectrogram_utils
- Added `create_stft_custom()` method that uses the new STFT approach
- Added 'stft_custom' to the method dropdown (now 5 methods: mel, stft, stft_custom, chromagram, mfcc)
- Maintains compatibility with existing methods

### 3. `tests/test_stft_spectrogram_node.py`
New comprehensive test file:

- Tests that Spectrogram node has the new stft_custom method
- Verifies STFT functions produce valid RGB spectrograms
- Tests fourier_transformation, make_logscale, and colormap application
- All assertions pass

## Usage

### In the Spectrogram Node UI:
1. Connect an audio source to the Spectrogram node
2. Select "stft_custom" from the Method dropdown
3. The node will display the STFT-based spectrogram

### Programmatically:
```python
from node.InputNode.spectrogram_utils import create_spectrogram_from_audio
import numpy as np

# Create test audio signal
sample_rate = 22050
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration))
audio_data = np.sin(2 * np.pi * 440 * t)  # 440 Hz tone

# Generate spectrogram
spec_image = create_spectrogram_from_audio(
    audio_data, 
    sample_rate=sample_rate, 
    binsize=1024, 
    colormap="jet"
)
# spec_image is now an RGB image (H, W, 3) ready for display
```

## Technical Details

### STFT Approach
The implementation uses:
1. **Windowing**: Hanning window by default for spectral smoothing
2. **Stride tricks**: Efficient frame extraction using numpy.lib.stride_tricks
3. **Overlap**: Configurable overlap factor (default 50%)
4. **Log scaling**: Converts linear frequency bins to logarithmic scale
5. **dB conversion**: Converts amplitude to decibels using reference amplitude

### Display Properties
- **Orientation**: Low frequencies at bottom, high frequencies at top (using flipud)
- **Axes**: Time on X-axis, Frequency on Y-axis
- **Colormap**: Multiple options (jet, viridis, inferno, plasma, magma)
- **Format**: RGB uint8 images compatible with CV Studio's display system

## Testing

All tests pass:
- ✅ 11/11 existing spectrogram colormap tests
- ✅ STFT function tests
- ✅ Visual verification with frequency sweeps and constant tones
- ✅ No security vulnerabilities (CodeQL)

## Verification

Visual tests confirm spectrograms display correctly:
- Frequency sweeps appear as diagonal patterns
- Constant tones appear as horizontal lines
- Proper frequency orientation (low to high, bottom to top)
- Colormaps apply correctly with good visual distinction

## Security

- No security vulnerabilities detected by CodeQL scanner
- Uses named constants for magic numbers (REFERENCE_AMPLITUDE)
- Proper error handling for missing dependencies (scipy)
- Input validation for audio data

## Summary

The STFT-based spectrogram implementation successfully adds the requested functionality using `fourier_transformation`, `make_logscale`, and supporting functions. Spectrograms display correctly in the node system with proper orientation, multiple colormap support, and accurate frequency/time representation.
