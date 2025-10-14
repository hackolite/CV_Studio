# Video FPS and Speed Control - Visual Explanation

## Feature Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Video Node Controls                    │
├─────────────────────────────────────────────────────────────┤
│  [Select Movie]              ← Choose video file            │
│  ┌───────────────────────┐                                  │
│  │   Video Display       │  ← Video frames                  │
│  └───────────────────────┘                                  │
│  ☑ Show Spectrogram          ← Enable/disable spectrogram   │
│  ┌───────────────────────┐                                  │
│  │ Spectrogram Display   │  ← Audio visualization           │
│  └───────────────────────┘                                  │
│  ☑ Loop                      ← Loop video                   │
│  Skip Rate:   |─────●─|      ← Skip frames (1-10)           │
│  Target FPS:  |─────────●──| ← NEW! Target FPS (1-120)      │
│  Speed:       |──────●─────| ← NEW! Speed (0.25x-4.0x)      │
│  [Start]                     ← Start/stop playback          │
└─────────────────────────────────────────────────────────────┘
```

## How Frame Timing Works

### Normal Playback (24 FPS, 1.0x speed)

```
Frame interval = (1/24) / 1.0 = 0.042 seconds

Timeline:
0.000s  0.042s  0.084s  0.126s  0.168s
  │       │       │       │       │
  ▼       ▼       ▼       ▼       ▼
Frame 1 Frame 2 Frame 3 Frame 4 Frame 5

Each frame displays for 42ms
```

### Slow Motion (24 FPS, 0.5x speed)

```
Frame interval = (1/24) / 0.5 = 0.083 seconds

Timeline:
0.000s  0.083s  0.166s  0.249s  0.332s
  │       │       │       │       │
  ▼       ▼       ▼       ▼       ▼
Frame 1 Frame 2 Frame 3 Frame 4 Frame 5

Each frame displays for 83ms (2x slower)
```

### Fast Forward (24 FPS, 2.0x speed)

```
Frame interval = (1/24) / 2.0 = 0.021 seconds

Timeline:
0.000s  0.021s  0.042s  0.063s  0.084s
  │       │       │       │       │
  ▼       ▼       ▼       ▼       ▼
Frame 1 Frame 2 Frame 3 Frame 4 Frame 5

Each frame displays for 21ms (2x faster)
```

## Frame Reading Decision Flow

```
┌─────────────────────────────────────────────┐
│         Video Node Update Cycle             │
└─────────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Get current time     │
        └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Calculate required   │
        │  frame interval:      │
        │  (1/FPS) / Speed      │
        └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Has enough time      │
        │  passed?              │
        └───────────────────────┘
               │           │
          Yes  │           │ No
               ▼           │
    ┌──────────────────┐  │
    │  Read next frame │  │
    │  from video      │  │
    └──────────────────┘  │
               │           │
               ▼           │
    ┌──────────────────┐  │
    │  Update display  │  │
    └──────────────────┘  │
               │           │
               ▼           │
    ┌──────────────────┐  │
    │  Record frame    │  │
    │  display time    │  │
    └──────────────────┘  │
               │           │
               └───────────┘
                    │
                    ▼
            Return to next cycle
```

## Example Scenarios

### Scenario 1: Cinema Standard (24 FPS)

```
Settings:
- Target FPS: 24
- Speed: 1.0x

Result: Video plays at standard cinema frame rate
Perfect for cinematic content analysis
```

### Scenario 2: Slow Motion Detail Analysis (24 FPS, 0.25x)

```
Settings:
- Target FPS: 24
- Speed: 0.25x

Result: Video plays 4x slower than normal
Each frame visible for 167ms instead of 42ms
Perfect for analyzing fast movements
```

### Scenario 3: Quick Preview (24 FPS, 4.0x)

```
Settings:
- Target FPS: 24
- Speed: 4.0x

Result: Video plays 4x faster than normal
Each frame visible for 10.4ms instead of 42ms
Perfect for quickly scanning through content
```

### Scenario 4: High Frame Rate + Slow Motion (60 FPS, 0.5x)

```
Settings:
- Target FPS: 60
- Speed: 0.5x

Result: Smooth playback at half speed
Each frame visible for 33ms
Great for smooth slow-motion analysis
```

## Integration with Existing Features

### Skip Rate + Speed Control

```
Skip Rate = 2 (show every 2nd frame)
Speed = 0.5x (half speed)

Source frames:  1  2  3  4  5  6  7  8
Skip Rate:      1  X  3  X  5  X  7  X
Displayed:      1     3     5     7

Each displayed frame shown for 2x normal time
```

### Spectrogram Synchronization

```
The spectrogram remains synchronized because:
1. Frame counter increments for every frame read
2. Spectrogram position = frame_count / fps * sr / hop_length
3. Speed control doesn't affect frame counting
4. Only affects display timing

Frame 1 ──────┐
              ├─→ Spectrogram position calculated
Frame 2 ──────┤
              ├─→ Updates regardless of speed
Frame 3 ──────┘
```

## Benefits

1. **Flexible Playback**: Match any target frame rate
2. **Analysis Tools**: Slow down for detailed examination
3. **Preview Mode**: Speed up for quick scanning
4. **Maintained Sync**: Spectrogram stays aligned
5. **Easy Control**: Simple sliders for adjustment
6. **Smooth Playback**: Time-based frame display

## Technical Notes

- Frame interval calculated as: `(1.0 / target_fps) / playback_speed`
- Zero FPS or speed handled gracefully (defaults to 0 interval)
- First frame always displayed (no previous time to compare)
- Settings saved and restored between sessions
- Backward compatible with existing projects (uses defaults)
