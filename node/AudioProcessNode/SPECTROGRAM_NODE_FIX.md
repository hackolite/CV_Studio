# Spectrogram Node - Documentation

## Overview

The Spectrogram node converts audio input into a visual spectrogram representation. This node is now fully functional and can be used in the CV_Studio application.

## Problem Fixed

**Issue**: The Spectrogram node was listed in the AudioProcess menu but could not be instantiated because the node implementation was missing.

**Solution**: Created a complete node implementation (`node_spectrogram_node.py`) with:
- FactoryNode class for node creation and UI setup
- SpectrogramNode class for audio processing and visualization
- Full integration with the CV_Studio node editor

## Features

### Input
- **Audio**: Accepts audio data from any audio-producing node (e.g., Video node)
  - Expected format: Dictionary with `samples` (numpy array) and `sample_rate` (int)

### Output
- **Image**: Spectrogram visualization as a BGR image
- **Processing Time**: Time taken to generate the spectrogram (if performance counter is enabled)

### Parameters

1. **FFT Size** (Dropdown)
   - Options: 512, 1024, 2048, 4096
   - Default: 1024
   - Description: The size of the Fast Fourier Transform window. Larger values provide better frequency resolution but lower time resolution.

2. **Colormap** (Dropdown)
   - Options: jet, viridis, plasma, inferno, magma, hot, cool
   - Default: jet
   - Description: The color scheme used to visualize the spectrogram. Different colormaps can highlight different features of the audio.

## How to Use

1. **Add the Node**
   - Open CV_Studio
   - Navigate to: AudioProcess → Spectrogram
   - The node will appear in the editor

2. **Connect Audio Input**
   - Connect an audio output from another node (e.g., Video node's audio output)
   - The Spectrogram node accepts AUDIO type connections

3. **Configure Parameters**
   - Select desired FFT Size (default 1024 works well for most cases)
   - Choose a colormap (jet is classic, viridis is perceptually uniform)

4. **View Output**
   - The spectrogram visualization will appear in the node's output
   - Connect the IMAGE output to other nodes for further processing or visualization

## Technical Details

### Audio Processing Pipeline

1. **Audio Input**: Receives audio data with samples and sample rate
2. **Preprocessing**: Converts audio to mono and int16 format if needed
3. **Fourier Transform**: Applies FFT with the specified window size
4. **Logarithmic Scaling**: Converts frequency scale to logarithmic (factor=1.0)
5. **Decibel Conversion**: Converts amplitude to decibels (20*log10)
6. **Visualization**: Renders the spectrogram using matplotlib with the selected colormap
7. **Format Conversion**: Converts the matplotlib figure to a BGR image for OpenCV

### Integration with Existing Code

The node uses the following existing utility functions from `node_spectrogram.py`:
- `fourier_transformation()`: Performs the STFT with windowing
- `make_logscale()`: Converts to logarithmic frequency scale
- `REFERENCE_AMPLITUDE`: Standard reference for dB conversion (10e-6)

### Matplotlib Compatibility

The implementation uses `buffer_rgba()` method which is compatible with modern matplotlib versions (3.x+). This ensures the node works correctly with current dependencies.

## Testing

Comprehensive tests have been added to verify functionality:

### Basic Tests (`test_spectrogram_node_basic.py`)
- Node module import
- FactoryNode attributes
- SpectrogramNode instantiation

### Integration Tests (`test_spectrogram_node_integration.py`)
- Basic spectrogram generation with synthetic audio
- Different FFT sizes (512, 1024, 2048, 4096)
- Different colormaps (jet, viridis, plasma, inferno, magma, hot, cool)
- Edge cases (empty audio, None input)

All tests pass successfully.

## Example Use Cases

1. **Audio Visualization**
   - Connect Video → Spectrogram to visualize audio content
   - Use for audio analysis or debugging

2. **Audio-to-Image Processing**
   - Generate spectrograms for machine learning models
   - Connect Spectrogram → Classification for audio classification

3. **Real-time Audio Monitoring**
   - Visualize live audio streams
   - Monitor frequency content in real-time applications

## Troubleshooting

### Node doesn't appear in menu
- Make sure CV_Studio is restarted after the fix
- Check that `node_spectrogram_node.py` exists in `node/AudioProcessNode/`

### No output image
- Verify audio input is connected
- Check that audio data format is correct (dict with 'samples' and 'sample_rate')
- Ensure audio samples are not empty

### Performance issues
- Reduce FFT size for faster processing (try 512 or 1024)
- Larger FFT sizes (2048, 4096) provide better quality but slower processing

## Future Enhancements

Possible improvements for future development:
- Add frequency range filters (fmin, fmax)
- Support for different window functions (Hanning, Hamming, Blackman)
- Real-time scrolling spectrogram view
- Adjustable time window duration
- Export spectrogram as image file

## References

- ESC-50 Dataset: Used as reference for spectrogram parameters
- Librosa: Audio processing library
- Matplotlib: Visualization library
- OpenCV: Image processing
