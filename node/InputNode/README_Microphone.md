# Microphone Node

## Description

The Microphone node captures real-time audio input from your system's microphone and outputs it as audio data that can be processed by other nodes in the CV Studio pipeline.

## Features

- **Real-time Audio Capture**: Record live audio from any available microphone
- **Configurable Sample Rate**: Choose from standard sample rates (8kHz to 48kHz)
- **Adjustable Chunk Size**: Configure audio chunk duration from 0.1s to 5.0s
- **Multiple Device Support**: Select from all available audio input devices
- **Start/Stop Control**: Easy toggle button to control recording
- **Audio Activity Indicator**: Visual indicator that blinks when audio levels increase

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| Audio | AUDIO | Audio data as numpy array with sample rate |
| JSON | JSON | Metadata about the audio capture (reserved for future use) |

## Audio Activity Indicator

The Microphone node includes a visual indicator that shows when audio is being captured:

- **"Audio: ○"** (gray): Not recording or very quiet audio
- **"Audio: ●"** (bright green): Blinking when audio level increases
- **"Audio: ○"** (darker green): Alternates with bright green for blinking effect

The indicator blinks green whenever the audio level (RMS) increases from the previous chunk, helping you:
- Verify that the microphone is actively capturing sound
- See real-time feedback when speaking or making sounds
- Confirm audio input is working without needing numerical values
- Know when the decibel level is rising

The blinking occurs when:
1. Audio level increases compared to the previous chunk
2. Audio level is above the minimum threshold (0.01) to ignore background noise

## Configuration

### Device Selection
Select the microphone device from the dropdown list. Available devices are automatically detected when the node is created.

### Sample Rate
Choose the audio sample rate:
- **8000 Hz**: Phone quality, minimal bandwidth
- **16000 Hz**: Wideband speech quality
- **22050 Hz**: Half of CD quality, good for most applications
- **44100 Hz**: CD quality (default), recommended for music
- **48000 Hz**: Professional audio quality

### Chunk Duration
Set the duration of each audio chunk in seconds (0.1s to 5.0s). This determines how much audio is captured and passed to downstream nodes in each update cycle.

- **Shorter chunks (0.1-0.5s)**: Lower latency, faster response, more frequent updates
- **Longer chunks (1.0-5.0s)**: Better for spectral analysis, more data per update

## Usage Examples

### Example 1: Real-time Spectrogram Visualization

1. Add a **Microphone** node (Input → Microphone)
2. Add a **Spectrogram** node (AudioProcess → Spectrogram)
3. Add a **Result Image** node (Visual → Result Image)
4. Connect: Microphone → Spectrogram → Result Image
5. Click "Start" on the Microphone node
6. Select your preferred spectrogram method (mel, stft, chromagram, mfcc)
7. See real-time visualization of your audio input

### Example 2: Audio Analysis Pipeline

1. Add a **Microphone** node
2. Add multiple **Spectrogram** nodes with different methods
3. Add an **Image Concat** node to view all spectrograms side-by-side
4. Connect the Microphone to all Spectrogram nodes
5. Connect all Spectrograms to Image Concat
6. Add a **Result Image (Large)** node for better visualization

## Requirements

### System Requirements

The Microphone node requires:
- **sounddevice**: Python package for audio I/O
- **PortAudio**: System library for cross-platform audio support

### Installation

#### Linux (Ubuntu/Debian)
```bash
# Install PortAudio library
sudo apt-get install portaudio19-dev python3-pyaudio

# Install Python package
pip install sounddevice
```

#### macOS
```bash
# Install PortAudio via Homebrew
brew install portaudio

# Install Python package
pip install sounddevice
```

#### Windows
```bash
# Install Python package (PortAudio is bundled)
pip install sounddevice
```

### Fallback Behavior

If sounddevice or PortAudio is not available:
- The Microphone node will still appear in the menu
- A message will indicate "sounddevice not available"
- The node will be non-functional until the dependencies are installed
- No errors will be raised in the application

## Audio Output Format

The Microphone node outputs audio data in the following format:

```python
{
    'data': numpy.ndarray,      # Audio samples as float32 array
    'sample_rate': int          # Sample rate in Hz
}
```

This format is compatible with all AudioProcess nodes including:
- Spectrogram
- Audio classification (future)
- Audio effects (future)

## Troubleshooting

### No Microphone Detected

**Problem**: Dropdown shows "No microphone detected"

**Solutions**:
- Check that a microphone is physically connected
- Verify microphone permissions in your OS settings
- Restart the application
- Check that other applications can access the microphone

### sounddevice Not Available

**Problem**: Dropdown shows "sounddevice not available"

**Solutions**:
- Install PortAudio system library (see Installation section)
- Install sounddevice: `pip install sounddevice`
- Restart the application

### Audio Quality Issues

**Problem**: Audio sounds distorted or has artifacts

**Solutions**:
- Increase chunk duration to 1.0s or higher
- Try a different sample rate
- Check microphone levels in system settings
- Move microphone away from noise sources

### High Latency

**Problem**: Noticeable delay between input and output

**Solutions**:
- Reduce chunk duration to 0.1-0.5s
- Use a lower sample rate (16000 or 22050 Hz)
- Close other audio applications
- Check system audio buffer settings

## Performance Considerations

- **CPU Usage**: Real-time audio capture is lightweight, but downstream processing (like spectrograms) may be CPU-intensive
- **Memory Usage**: Minimal, as audio chunks are processed and discarded
- **Latency**: Approximately equal to chunk duration plus processing time
- **Best Practices**:
  - Use 1.0s chunks for spectral analysis
  - Use 0.1-0.3s chunks for low-latency applications
  - Match sample rate to your analysis needs (higher is not always better)

## Technical Notes

### Audio Format
- **Channels**: Mono (1 channel)
- **Data Type**: float32 (-1.0 to 1.0)
- **Normalization**: Automatic by sounddevice

### Synchronization
- Each call to `update()` records a new audio chunk
- Recording is synchronous (blocks until chunk is complete)
- Compatible with the timestamped queue system

### Thread Safety
- The node is designed to work in CV Studio's async update loop
- Recording is performed synchronously to ensure data integrity

## Version History

- **0.0.2** (Current)
  - Replaced RMS and Peak volume meters with single blinking indicator
  - Indicator blinks green when audio level increases
  - Simplified visual feedback for audio activity
  
- **0.0.1** (Initial Release)
  - Basic microphone capture functionality
  - Configurable sample rate and chunk duration
  - Multi-device support
  - Graceful fallback when sounddevice unavailable

## License

This node is part of CV Studio and follows the same license (Apache 2.0).

## See Also

- [Spectrogram Node](../AudioProcessNode/SPECTROGRAM_METHODS.md) - Process audio into visual spectrograms
- [Video Node](README_DynamicPlay.md) - For video with synchronized audio
- [CV Studio Main README](../../README.md) - Full application documentation
