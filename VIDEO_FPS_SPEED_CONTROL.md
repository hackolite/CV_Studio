# Video Node FPS and Speed Control Feature

## Overview

This document describes the new FPS (frames per second) and playback speed control features added to the Video Node.

## New Features

### 1. Target FPS Control (24 FPS default)

A new slider allows you to set the target playback frame rate, with a default of 24 FPS.

- **Label**: "Target FPS"
- **Default**: 24 fps
- **Range**: 1-120 fps
- **Purpose**: Control at what frame rate the video is played back, independent of the source video's original FPS

### 2. Playback Speed Control

A new slider allows you to slow down or speed up the video playback.

- **Label**: "Speed"
- **Default**: 1.0x (normal speed)
- **Range**: 0.25x - 4.0x
- **Purpose**: Control playback speed as a multiplier
  - 0.25x = 4 times slower
  - 0.5x = 2 times slower
  - 1.0x = normal speed
  - 2.0x = 2 times faster
  - 4.0x = 4 times faster

## How It Works

### Frame Timing

The system calculates the time interval between frames based on:

```
frame_interval = (1.0 / target_fps) / playback_speed
```

**Examples**:
- 24 FPS at 1.0x speed: 1/24 / 1.0 = 0.042 seconds per frame
- 24 FPS at 2.0x speed: 1/24 / 2.0 = 0.021 seconds per frame (faster)
- 24 FPS at 0.5x speed: 1/24 / 0.5 = 0.083 seconds per frame (slower)

### Frame Reading Control

The node now checks if enough time has passed before reading the next frame:

1. Track the time when the last frame was displayed
2. Calculate the required interval based on target FPS and speed
3. Only read and display a new frame when enough time has passed

This ensures smooth playback at the specified frame rate and speed.

## UI Layout

The Video Node now includes the following controls (in order):

1. **Select Movie** - Button to choose video file
2. **Video Display** - Video frame output
3. **Show Spectrogram** - Checkbox to enable/disable spectrogram
4. **Spectrogram Display** - Audio spectrogram visualization
5. **Loop** - Checkbox to enable/disable video looping
6. **Skip Rate** - Slider to skip frames (1-10)
7. **Target FPS** - NEW: Slider to set playback frame rate (1-120)
8. **Speed** - NEW: Slider to control playback speed (0.25x-4.0x)
9. **Start/Stop** - Button to start/stop playback

## Use Cases

### 1. Force 24 FPS Playback

Set "Target FPS" to 24 to play any video at 24 fps, regardless of its original frame rate.

### 2. Slow Motion Analysis

- Set "Target FPS" to 24 (or desired rate)
- Set "Speed" to 0.25x or 0.5x to slow down playback for detailed analysis

### 3. Fast Preview

- Set "Speed" to 2.0x or 4.0x to quickly preview long videos

### 4. Frame-by-Frame Control

Combine with "Skip Rate" to have fine-grained control over which frames are displayed.

## Implementation Details

### New Instance Variables

- `_last_frame_time`: Dictionary tracking the last frame display time for each node

### Modified Methods

1. **add_node()**: Added UI elements for FPS and speed sliders
2. **update()**: Added frame timing logic to control playback speed
3. **get_setting_dict()**: Save FPS and speed settings
4. **set_setting_dict()**: Restore FPS and speed settings

### Backward Compatibility

The implementation includes default values when loading old settings:
- If `target_fps` is not in saved settings, defaults to 24
- If `playback_speed` is not in saved settings, defaults to 1.0

This ensures existing projects continue to work without modification.

## Testing

Tests are available in `tests/test_video_fps_speed_control.py` to verify:
- Presence of new UI elements
- Correct default values
- Frame timing logic implementation
- Settings save/restore functionality

## Notes

- The frame timing works independently of the "Skip Rate" feature
- Both features can be used together for maximum control
- Spectrogram synchronization remains intact with the new timing controls
- The actual playback smoothness depends on the system's ability to render frames at the requested rate
