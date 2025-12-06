# Equalizer Node Documentation

## Overview

The **Equalizer** node is a standard 5-band audio equalizer that allows you to adjust different frequency ranges of an audio signal. It is located in the **AudioProcess** menu of CV_Studio.

## Features

- **5-band frequency control**: Bass, Mid-Bass, Mid, Mid-Treble, and Treble
- **Real-time processing**: Apply equalization to live audio streams
- **Wide gain range**: -20dB to +20dB per band
- **Automatic normalization**: Prevents clipping when boosting multiple bands
- **Performance monitoring**: Optional elapsed time display

## Frequency Bands

The Equalizer divides the audio spectrum into five frequency bands:

| Band | Frequency Range | Typical Use |
|------|----------------|-------------|
| **Bass** | 20-250 Hz | Deep bass, kick drums, bass guitars |
| **Mid-Bass** | 250-500 Hz | Upper bass, lower vocals |
| **Mid** | 500-2000 Hz | Main vocals, guitars, most instruments |
| **Mid-Treble** | 2000-6000 Hz | Clarity, presence, cymbals |
| **Treble** | 6000-20000 Hz | High frequencies, air, sparkle |

## Usage

### Basic Setup

1. Add the **Equalizer** node from the **AudioProcess** menu
2. Connect an audio source (e.g., Microphone, Video) to the audio input
3. Connect the audio output to another node (e.g., Spectrogram, Audio Output)
4. Adjust the frequency band sliders to shape the sound

### Parameters

Each frequency band has a slider control that adjusts the gain in decibels (dB):

- **Range**: -20 dB (cut) to +20 dB (boost)
- **Default**: 0 dB (no change)
- **Positive values**: Boost the frequency band
- **Negative values**: Cut/reduce the frequency band

### Examples

#### Enhance Voice Clarity
- Bass: -3 dB (reduce rumble)
- Mid-Bass: 0 dB
- Mid: +3 dB (enhance voice)
- Mid-Treble: +2 dB (add presence)
- Treble: -2 dB (reduce sibilance)

#### Deep Bass Boost
- Bass: +10 dB
- Mid-Bass: +5 dB
- Mid: 0 dB
- Mid-Treble: 0 dB
- Treble: 0 dB

#### Podcast/Radio Voice
- Bass: -5 dB
- Mid-Bass: +2 dB
- Mid: +3 dB
- Mid-Treble: +2 dB
- Treble: -3 dB

## Technical Details

### Implementation

The Equalizer uses **Butterworth bandpass filters** (4th order) from scipy.signal to separate the audio into frequency bands:

- **Bass**: Low-pass filter at 250 Hz
- **Mid bands**: Bandpass filters for the specified ranges
- **Treble**: High-pass filter at 6000 Hz

Each band is filtered independently, scaled by the gain value (converted from dB to linear), and then recombined. The output is normalized to prevent clipping.

### Audio Format

- **Input**: Dictionary with `{'data': numpy_array, 'sample_rate': int}`
- **Output**: Dictionary with `{'data': numpy_array, 'sample_rate': int}`
- **Data type**: float32 numpy array (mono audio)
- **Sample rate**: Preserved from input (typically 22050 or 44100 Hz)

### Performance

Processing time depends on:
- Audio buffer length
- Sample rate
- Number of bands with non-zero gain

Typical processing time for 1 second of audio at 22050 Hz: < 50ms

## Saving and Loading

The Equalizer node saves all gain settings when you export the node graph:

```json
{
  "ver": "0.0.1",
  "pos": [x, y],
  "bass_gain": 0.0,
  "mid_bass_gain": 0.0,
  "mid_gain": 0.0,
  "mid_treble_gain": 0.0,
  "treble_gain": 0.0
}
```

## Troubleshooting

### No audio output
- Check that the audio input is connected
- Verify the input node is producing audio
- Check that sample rate is valid (> 0)

### Distorted output
- Reduce gain values (especially if boosting multiple bands)
- The node automatically normalizes, but extreme settings may introduce artifacts

### Performance issues
- Consider reducing the audio buffer size
- Process shorter audio chunks
- Use fewer bands (set unused bands to 0 dB)

## Related Nodes

- **Spectrogram**: Visualize the frequency content before/after equalization
- **Microphone**: Real-time audio input source
- **Video**: Extract and process audio from video files

## Version History

- **0.0.1**: Initial release with 5-band equalizer
