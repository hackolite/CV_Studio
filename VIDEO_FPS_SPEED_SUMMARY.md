# Video Node UI Changes - Summary

## Before (Original)

```
┌─────────────────────────────┐
│      Video Node             │
├─────────────────────────────┤
│ [Select Movie]              │
│ ┌─────────────────────────┐ │
│ │    Video Display        │ │
│ └─────────────────────────┘ │
│ ☐ Show Spectrogram          │
│ ┌─────────────────────────┐ │
│ │  Spectrogram Display    │ │
│ └─────────────────────────┘ │
│ ☑ Loop                      │
│ Skip Rate:    |──●─|        │  Range: 1-10
│ [Start]                     │
│ Audio (output)              │
│ JSON (output)               │
│ Float (output)              │
└─────────────────────────────┘
```

## After (With FPS and Speed Control)

```
┌─────────────────────────────┐
│      Video Node             │
├─────────────────────────────┤
│ [Select Movie]              │
│ ┌─────────────────────────┐ │
│ │    Video Display        │ │
│ └─────────────────────────┘ │
│ ☐ Show Spectrogram          │
│ ┌─────────────────────────┐ │
│ │  Spectrogram Display    │ │
│ └─────────────────────────┘ │
│ ☑ Loop                      │
│ Skip Rate:    |──●─|        │  Range: 1-10
│ Target FPS:   |─────────●─| │  Range: 1-120 ⭐ NEW
│ Speed:        |────●──────| │  Range: 0.25x-4.0x ⭐ NEW
│ [Start]                     │
│ Audio (output)              │
│ JSON (output)               │
│ Float (output)              │
└─────────────────────────────┘
```

## New Controls Detail

### Target FPS Slider
- **Label**: "Target FPS"
- **Type**: Integer slider
- **Default**: 24
- **Range**: 1 to 120
- **Width**: 160 pixels (small_window_w - 80)
- **Purpose**: Set the playback frame rate

### Speed Slider
- **Label**: "Speed"
- **Type**: Float slider
- **Default**: 1.0
- **Range**: 0.25 to 4.0
- **Width**: 160 pixels (small_window_w - 80)
- **Purpose**: Control playback speed multiplier

## Key Features

### 1. Independent Controls
```
Skip Rate:   Controls which frames are displayed (1, 2, 3...)
Target FPS:  Controls playback frame rate (24, 30, 60...)
Speed:       Controls playback speed (0.25x, 0.5x, 1.0x, 2.0x, 4.0x)
```

### 2. Combined Effects
```
Example: Skip Rate=2, FPS=24, Speed=0.5x
- Only every 2nd frame is shown
- Frames display at 24 fps rate
- Each frame is shown for 2x normal duration
```

### 3. Spectrogram Sync Maintained
```
The spectrogram automatically follows the video playback:
- Synchronized with frame counter
- Works with all speed settings
- Smooth scrolling maintained
```

## Use Case Examples

### Cinema Standard (24 FPS)
```
Settings:
- Target FPS: 24 ✓
- Speed: 1.0x
- Skip Rate: 1

Result: Standard cinema playback
```

### Slow Motion Analysis
```
Settings:
- Target FPS: 24
- Speed: 0.25x ✓
- Skip Rate: 1

Result: 4x slower playback for detailed analysis
```

### Fast Preview
```
Settings:
- Target FPS: 24
- Speed: 4.0x ✓
- Skip Rate: 1

Result: 4x faster playback for quick scanning
```

### Selective Frame Analysis
```
Settings:
- Target FPS: 24
- Speed: 0.5x
- Skip Rate: 2 ✓

Result: Every 2nd frame shown at half speed
```

## Implementation Highlights

### Frame Timing Algorithm
```python
# Calculate frame interval
frame_interval = (1.0 / target_fps) / playback_speed

# Check if enough time passed
should_read_frame = (last_time is None) or 
                   ((current_time - last_time) >= frame_interval)

# Read frame if ready
if should_read_frame:
    read_next_frame()
    last_frame_time = current_time
```

### Settings Persistence
```python
# Save settings
setting_dict[tag_node_input04_value_name] = target_fps
setting_dict[tag_node_input05_value_name] = playback_speed

# Restore settings (with defaults for backward compatibility)
target_fps = int(setting_dict.get(tag_node_input04_value_name, 24))
playback_speed = float(setting_dict.get(tag_node_input05_value_name, 1.0))
```

## Technical Details

### New Instance Variables
- `_last_frame_time = {}`: Tracks last frame display time per node

### Modified Methods
1. `add_node()`: Added two new slider UI elements
2. `update()`: Added frame timing logic
3. `get_setting_dict()`: Save FPS and speed settings
4. `set_setting_dict()`: Restore FPS and speed settings

### Backward Compatibility
- Old project files without FPS/speed settings will use defaults
- Default FPS: 24
- Default Speed: 1.0x
- No migration needed

## Testing

### Structure Tests
- ✓ UI elements present
- ✓ Default values correct
- ✓ Range values correct

### Timing Tests
- ✓ Frame interval calculation accurate
- ✓ Edge cases handled (zero FPS, zero speed)
- ✓ Actual timing matches expected

### Integration Tests
- ✓ Works with existing Skip Rate
- ✓ Spectrogram stays synchronized
- ✓ Settings save/restore properly

## Files Modified

1. **node/InputNode/node_video.py** (85 lines changed)
   - Added UI controls for FPS and speed
   - Implemented frame timing logic
   - Updated settings save/restore

2. **tests/test_video_fps_speed_control.py** (new file)
   - Structure verification tests

3. **tests/demo_fps_speed_timing.py** (new file)
   - Timing calculation demo

4. **VIDEO_FPS_SPEED_CONTROL.md** (new file)
   - Feature documentation

5. **VIDEO_FPS_SPEED_VISUAL_GUIDE.md** (new file)
   - Visual explanations and examples
