# Microphone Node - Enhanced Features

## Summary of Enhancements

This document describes the enhancements made to the Microphone node to address the requirements for improved functionality, control, and monitoring.

## New Features

### 1. FPS Limit Slider
**Parameter**: FPS Limit  
**Type**: Slider (Float)  
**Range**: 1.0 - 60.0 FPS  
**Default**: 30.0 FPS  

Controls the maximum update rate of the microphone node. This helps prevent system overload when processing audio in real-time.

**Usage:**
- Set to **30 FPS** (default) for balanced performance
- Set to **60 FPS** for maximum responsiveness 
- Set to **10-15 FPS** for lower CPU usage or when high frequency updates aren't needed

**Benefits:**
- Prevents excessive CPU usage
- Allows fine-tuning performance vs responsiveness
- Helps maintain smooth operation when multiple nodes are active

### 2. Output Mode Selection
**Parameter**: Output Mode  
**Type**: Dropdown  
**Options**: 
- **Full Signal** (default): Outputs complete audio waveform data
- **dB Intensity**: Outputs sound intensity in decibels

**Full Signal Mode:**
- Returns the complete audio samples as a numpy array
- Suitable for downstream audio processing (spectrograms, analysis, etc.)
- Data format: float32 array with values between -1.0 and 1.0

**dB Intensity Mode:**
- Calculates RMS (Root Mean Square) of the audio chunk
- Converts to decibel scale: dB = 20 * log10(RMS)
- Returns a single value representing sound intensity
- Useful for volume monitoring, level meters, or simple audio activity detection
- Range: typically -60 dB (quiet) to 0 dB (full scale)

**Use Cases:**
- **Full Signal**: Spectrogram visualization, audio effects, recording, classification
- **dB Intensity**: Volume meters, noise level monitoring, voice activity detection

### 3. Channels Selection
**Parameter**: Channels  
**Type**: Dropdown  
**Options**:
- **Mono** (default): Single channel audio
- **Stereo**: Two channel audio (left/right)

**Mono Mode:**
- Captures audio from a single channel
- Uses less memory and processing power
- Suitable for most voice and analysis applications
- Output is a 1D array

**Stereo Mode:**
- Captures audio from two channels
- Preserves spatial audio information
- Suitable for music recording or spatial audio analysis
- Output is a 2D array (samples x 2)

### 4. Timestamp for Each Chunk
**Feature**: Automatic timestamping  
**Type**: Unix timestamp (float)  
**Precision**: Microseconds  

Every audio chunk now includes a precise timestamp indicating when the chunk was captured.

**Output Format:**
```python
{
    'data': numpy.ndarray,      # Audio samples
    'sample_rate': int,         # Sample rate in Hz
    'timestamp': float,         # Unix timestamp
    'channels': int,            # 1 for mono, 2 for stereo
    'output_mode': str          # 'Full Signal' or 'dB Intensity'
}
```

**JSON Output:**
```python
{
    'timestamp': float,         # Unix timestamp
    'sample_rate': int,         # Sample rate in Hz
    'channels': int,            # Number of channels
    'chunk_duration': float,    # Chunk duration in seconds
    'output_mode': str,         # Output mode
    'samples': int,             # Number of samples
    'db_value': float           # Only present in dB Intensity mode
}
```

**Benefits:**
- Enables precise synchronization with video streams
- Allows temporal analysis of audio data
- Facilitates correlation between multiple data sources
- Essential for timestamp-based queue systems

## Existing Features (Unchanged)

### Start/Stop Button
- Toggle recording on/off
- Button changes label between "Start" and "Stop"
- Stops audio stream when not recording

### Device Selection
- Dropdown list of all available input devices
- Automatically detects microphones on system

### Sample Rate Selection
- Standard rates: 8000, 16000, 22050, 44100, 48000 Hz
- Default: 44100 Hz (CD quality)

### Chunk Duration
- Slider: 0.1 - 5.0 seconds
- Default: 1.0 second
- Controls the size of each audio buffer

### Audio Activity Indicator
- Visual feedback showing when audio is being captured
- Gray when inactive, green when active

## Performance Considerations

### FPS Limiting
The FPS limit prevents the node from updating too frequently, which:
- Reduces CPU usage
- Prevents UI lag in the node editor
- Maintains stable performance with multiple nodes
- Allows the system to process audio at a controlled rate

### Memory Usage
- **Full Signal mode**: Memory usage depends on chunk duration and sample rate
  - Formula: `samples = sample_rate * chunk_duration * channels`
  - Example: 44100 Hz * 1.0s * 1 channel = 44,100 float32 values (~176 KB per chunk)
- **dB Intensity mode**: Minimal memory usage (single float value)

### CPU Usage
- **Mono**: Lower CPU and memory usage
- **Stereo**: ~2x CPU and memory compared to mono
- **FPS Limit**: Directly controls update frequency and overall CPU load

## Testing

All enhancements have been thoroughly tested:

### Unit Tests
- ✅ New attributes initialization
- ✅ Input tag structure
- ✅ Decibel calculation accuracy
- ✅ Timestamp format validation
- ✅ Output structure verification
- ✅ FPS limiting logic

### Integration Tests
- ✅ Backward compatibility with existing tests
- ✅ Node import and instantiation
- ✅ Factory structure validation
- ✅ Update method signature

## Examples

### Example 1: Real-time Audio Monitoring with dB Intensity
```
Setup:
1. Microphone Node (Output Mode: dB Intensity)
2. Connect to value display or graph node
3. Monitor sound levels in real-time

Configuration:
- Sample Rate: 44100 Hz
- Chunk Duration: 0.1s (fast response)
- FPS Limit: 30 (smooth updates)
- Output Mode: dB Intensity
- Channels: Mono
```

### Example 2: High-Quality Audio Recording
```
Setup:
1. Microphone Node (Output Mode: Full Signal)
2. Connect to audio processing chain
3. Save to file or process in real-time

Configuration:
- Sample Rate: 48000 Hz
- Chunk Duration: 1.0s
- FPS Limit: 30
- Output Mode: Full Signal
- Channels: Stereo
```

### Example 3: Low-Latency Voice Activity Detection
```
Setup:
1. Microphone Node
2. Switch between Full Signal and dB Intensity modes
3. Use timestamp for precise event timing

Configuration:
- Sample Rate: 16000 Hz (sufficient for voice)
- Chunk Duration: 0.1s (100ms latency)
- FPS Limit: 60 (high responsiveness)
- Output Mode: dB Intensity
- Channels: Mono
```

## Technical Implementation

### FPS Limiting Algorithm
```python
current_time = time.time()
min_interval = 1.0 / fps_limit
time_since_last = current_time - self._last_update_time

if time_since_last < min_interval:
    # Skip this update
    return None
    
self._last_update_time = current_time
# Process audio...
```

### dB Calculation
```python
rms = np.sqrt(np.mean(audio_data**2))
if rms > 0:
    db_value = 20 * np.log10(rms)
else:
    db_value = -inf
```

### Timestamp Generation
```python
chunk_timestamp = time.time()
# Unix timestamp with microsecond precision
```

## Compatibility

- ✅ Backward compatible with existing nodes
- ✅ Works with existing audio processing pipeline
- ✅ Compatible with timestamp preservation system
- ✅ Integrates with queue-backed dictionary system

## Version Information

**Enhanced Version**: 0.0.2  
**Date**: December 26, 2025  
**Changes**:
- Added FPS limit slider (1-60 FPS)
- Added output mode selection (Full Signal / dB Intensity)
- Added channels selection (Mono / Stereo)
- Added timestamp to audio output
- Added comprehensive JSON metadata output
- Enhanced audio output structure with additional fields

## See Also

- [Microphone Node README](node/InputNode/README_Microphone.md)
- [Timestamp Preservation Documentation](TIMESTAMP_PRESERVATION.md)
- [Node Editor Documentation](node_editor/README.md)
