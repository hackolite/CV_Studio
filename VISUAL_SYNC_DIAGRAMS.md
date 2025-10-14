# Video-Audio Synchronization: Visual Diagram Guide

This document provides clear visual diagrams to understand the complete video-audio synchronization process.

---

## Process Overview Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        VIDEO FILE (input.mp4)                        │
│                                                                      │
│  Contains: Video Stream (30 FPS) + Audio Stream (22050 Hz)          │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌────────────────────┐          ┌────────────────────┐
        │   VIDEO STREAM     │          │   AUDIO STREAM     │
        │                    │          │                    │
        │  Frames: 1,2,3...  │          │  Samples: PCM data │
        │  FPS: 30           │          │  Rate: 22050 Hz    │
        └────────────────────┘          └────────────────────┘
                    │                               │
                    │                               ▼
                    │                   ┌────────────────────┐
                    │                   │   SPECTROGRAM      │
                    │                   │   GENERATION       │
                    │                   │                    │
                    │                   │  hop_length = 512  │
                    │                   │  n_mels = 128      │
                    │                   └────────────────────┘
                    │                               │
                    │                               ▼
                    │                   ┌────────────────────┐
                    │                   │  SPECTROGRAM ARRAY │
                    │                   │                    │
                    │                   │  128 rows          │
                    │                   │  × N columns       │
                    │                   └────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   SYNCHRONIZATION     │
                        │   (frame → column)    │
                        │                       │
                        │  frame_count → time   │
                        │  time → sample        │
                        │  sample → column      │
                        └───────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  WINDOW EXTRACTION    │
                        │                       │
                        │  Extract 240 columns  │
                        │  centered at position │
                        │  Draw yellow line     │
                        └───────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   DISPLAY IN NODE     │
                        │                       │
                        │  [Video Frame]        │
                        │  [Spectrogram Window] │
                        └───────────────────────┘
```

---

## Step 1: Audio-Video Split

```
┌─────────────────────────────────────────────────────────┐
│                     input.mp4                           │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │  Frame 1   │  │  Frame 2   │  │  Frame 3   │  ...  │
│  └────────────┘  └────────────┘  └────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Audio: ████████████████████████████████████████ │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        │
                        │ ffmpeg split
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────┐            ┌──────────────────────┐
│ VIDEO ONLY   │            │   AUDIO ONLY         │
│              │            │                      │
│ Frame 1      │            │ Sample 0: 0.123      │
│ Frame 2      │            │ Sample 1: 0.456      │
│ Frame 3      │            │ Sample 2: 0.789      │
│ ...          │            │ ...                  │
│              │            │ Sample 22049: 0.111  │
│ (30/second)  │            │ (22050/second)       │
└──────────────┘            └──────────────────────┘
```

---

## Step 2: Video Frame Extraction

```
Video Processing Loop:

┌──────────────────────────────────────────────────────────┐
│  while playing:                                          │
│                                                          │
│    ┌──────────────────────────────┐                     │
│    │ Read next frame              │                     │
│    │ frame_count = frame_count + 1│                     │
│    └──────────────────────────────┘                     │
│                 │                                        │
│                 ▼                                        │
│    ┌──────────────────────────────┐                     │
│    │ Frame 0   [Image Data]       │                     │
│    │ Frame 1   [Image Data]       │                     │
│    │ Frame 2   [Image Data]       │  ← Current frame    │
│    │ Frame 3   [Image Data]       │                     │
│    │ ...                          │                     │
│    └──────────────────────────────┘                     │
│                 │                                        │
│                 ▼                                        │
│    ┌──────────────────────────────┐                     │
│    │ Display frame                │                     │
│    └──────────────────────────────┘                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Step 3: Spectrogram Generation

```
Audio Signal → FFT Windows → Mel Spectrogram

┌─────────────────────────────────────────────────────────────┐
│ Audio samples (22050 Hz):                                   │
│ [0.1, 0.2, -0.1, 0.3, 0.4, ...]                            │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ librosa.feature.melspectrogram()
                        │ hop_length = 512 samples
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Spectrogram Matrix                          │
│                                                              │
│  Frequency ↑                                                │
│  (128 mels)│  Column 0  Column 1  Column 2  ...  Column N   │
│            │  ┌──────┐  ┌──────┐  ┌──────┐      ┌──────┐   │
│  High      │  │ 0.01 │  │ 0.02 │  │ 0.03 │      │ 0.05 │   │
│            │  ├──────┤  ├──────┤  ├──────┤      ├──────┤   │
│  Mid       │  │ 0.50 │  │ 0.60 │  │ 0.45 │      │ 0.70 │   │
│            │  ├──────┤  ├──────┤  ├──────┤      ├──────┤   │
│  Low       │  │ 0.80 │  │ 0.75 │  │ 0.85 │      │ 0.90 │   │
│            │  └──────┘  └──────┘  └──────┘      └──────┘   │
│            └────────────────────────────────────────────→   │
│                           Time                               │
│                                                              │
│  Each column = 512 audio samples = 0.023 seconds            │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ Apply color mapping
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           Colored Spectrogram (magma colormap)              │
│                                                              │
│  ████  ████  ████  ████  ████  ████                         │
│  ████  ████  ████  ████  ████  ████                         │
│  ████  ████  ████  ████  ████  ████                         │
│                                                              │
│  Purple = Low energy    Yellow = High energy                │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 4: Frame-to-Spectrogram Synchronization

```
Mathematical Mapping:

Video Frame Number → Time → Audio Sample → Spectrogram Column

┌────────────┐
│  Frame 900 │
└────────────┘
      │
      │ ÷ FPS (30)
      ▼
┌────────────┐
│ 30.0 sec   │
└────────────┘
      │
      │ × Sample Rate (22050)
      ▼
┌────────────┐
│ 661,500    │  ← Audio sample position
│ samples    │
└────────────┘
      │
      │ ÷ hop_length (512)
      ▼
┌────────────┐
│ Column     │
│  1,292     │  ← Spectrogram column
└────────────┘


Example Timeline Alignment:

Frame:      0      30     60     90    120    ...    900    ...   1800
            │      │      │      │      │            │            │
Time (s):   0.0    1.0    2.0    3.0    4.0   ...   30.0   ...   60.0
            │      │      │      │      │            │            │
Sample:     0    22050  44100  66150  88200  ...  661500  ...  1323000
            │      │      │      │      │            │            │
Column:     0      43     86    129    172    ...   1292   ...   2584

Every video frame has an exact corresponding spectrogram column!
```

---

## Step 5: Scrolling Window Display

```
Full Spectrogram (Example: 2584 columns for 60-second video at 30 FPS):

[████████████████████████████████████████████████████████████████████]
 0                                                               2584

Current Position (frame 900 → column 1292):

[████████████████████████████████▲████████████████████████████████████]
 0                           1292                                 2584
                              ↑
                         Current position


Displayed Window (240 columns, centered):

                    start_col=1172        end_col=1412
                         │                    │
[████████████████████████│████████████████████│████████████████████████]
                         │      ▲             │
                         │      │             │
                         └──────┼─────────────┘
                                │
                         ┌──────┴──────┐
                         │             │
            ┌────────────▼─────────────▼────────────┐
            │  Displayed Window (240 columns)       │
            │                                        │
            │  ██████████████|███████████████        │
            │  ██████████████|███████████████        │
            │  ██████████████|███████████████        │
            │               ↑                        │
            │          Yellow line                   │
            │        (at column 120                  │
            │         within window)                 │
            └────────────────────────────────────────┘

As playback advances:

Frame 0:   [|████████████] Window at start, line at left edge
Frame 100: ──[████|████████] Window moved right, line centered
Frame 900: ────────────────[████|████████] Window keeps moving
Frame 1800:─────────────────────────────[████|] Window at end
```

---

## Step 6: Display in Node

```
DearPyGUI Node Layout:

┌──────────────────────────────────────────────────┐
│  Video Node                                      │
├──────────────────────────────────────────────────┤
│                                                  │
│  [Select Movie]  ← Button to choose video file  │
│                                                  │
├──────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────┐ │
│  │                                            │ │
│  │          Video Frame Display               │ │
│  │          (240 × 135 pixels)                │ │
│  │                                            │ │
│  │  [Current frame image shown here]          │ │
│  │                                            │ │
│  └────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│                                                  │
│  ☑ Show Spectrogram  ← Toggle checkbox          │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  High freq: ▓▓▓▓▓▓|▓▓▓▓▓▓▓                 │ │
│  │  Mid freq:  ▓▓▓▓▓▓|▓▓▓▓▓▓▓                 │ │
│  │  Low freq:  ▓▓▓▓▓▓|▓▓▓▓▓▓▓                 │ │
│  │                   ↑                         │ │
│  │             Yellow indicator                │ │
│  │         (current position)                  │ │
│  │          (240 × 135 pixels)                 │ │
│  └────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│                                                  │
│  ☑ Loop  ← Enable/disable looping               │
│                                                  │
│  Skip Rate: [========|===========] 1             │
│             ← Playback speed control             │
│                                                  │
│  [Start]  ← Play/Stop button                    │
│                                                  │
└──────────────────────────────────────────────────┘


Synchronization during playback:

Every frame update:
  1. Read video frame N
  2. Calculate: column = (N / fps) × sr / hop_length
  3. Extract window: columns [column-120 : column+120]
  4. Draw yellow line at center of window
  5. Update both displays simultaneously

Result: Perfect sync between video and audio visualization!
```

---

## Complete Data Flow Timeline

```
TIME POINT: Frame 900 (30 seconds into video)

┌─────────────────┐
│  User Action    │  User clicks "Start" button
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  Frame Reader   │  OpenCV reads frame 900
│  frame_count=900│
└─────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Sync Calculator            │
│                             │
│  frame:   900               │
│  time:    30.0s             │
│  sample:  661,500           │
│  column:  1,292             │
└─────────────────────────────┘
        │
        ├────────────────┬────────────────┐
        │                │                │
        ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│Video Display│  │Window Extract│  │Line Drawing │
│             │  │             │  │             │
│Show frame   │  │Extract cols │  │Draw line at │
│900          │  │1172-1412    │  │column 120   │
└─────────────┘  └─────────────┘  └─────────────┘
        │                │                │
        └────────────────┴────────────────┘
                       │
                       ▼
               ┌─────────────┐
               │  DPG Update │
               │             │
               │  Update both│
               │  textures   │
               └─────────────┘
                       │
                       ▼
               ┌─────────────┐
               │  User Sees  │
               │             │
               │  Video frame│
               │  + Spectro  │
               │  in sync!   │
               └─────────────┘
```

---

## Performance Optimization

```
┌────────────────────────────────────────────────────────┐
│                    Initialization                      │
│                   (Done ONCE)                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────┐    ┌─────────────────┐             │
│  │ Load Video   │───▶│ Extract Audio   │             │
│  └──────────────┘    └─────────────────┘             │
│                               │                        │
│                               ▼                        │
│                      ┌─────────────────┐              │
│                      │Generate Spectro │              │
│                      │  (Full, once)   │              │
│                      └─────────────────┘              │
│                               │                        │
│                               ▼                        │
│                      ┌─────────────────┐              │
│                      │ Store in memory │              │
│                      │ (128 × N array) │              │
│                      └─────────────────┘              │
│                                                        │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                      Playback                          │
│              (Done EVERY FRAME - fast!)                │
├────────────────────────────────────────────────────────┤
│                                                        │
│  For each frame:                                       │
│                                                        │
│  1. Read frame from video       (fast - OpenCV)       │
│  2. Calculate column number     (fast - math)         │
│  3. Extract 240 columns         (fast - array slice)  │
│  4. Draw 1 line                 (fast - cv2.line)     │
│  5. Convert to texture          (fast - existing)     │
│  6. Update display              (fast - DPG)          │
│                                                        │
│  Total per frame: < 5ms for typical video             │
│                                                        │
└────────────────────────────────────────────────────────┘

Why this is efficient:
  ✓ Heavy computation (FFT) done once at load
  ✓ No re-reading of audio during playback
  ✓ Simple array operations per frame
  ✓ No file I/O during playback
  ✓ Minimal memory usage (reuse same arrays)
```

---

## Key Formulas Reference

```
┌──────────────────────────────────────────────────────┐
│          Critical Synchronization Formulas           │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. Frame to Time:                                   │
│     time = frame_number / fps                        │
│                                                      │
│  2. Time to Audio Sample:                            │
│     sample = time × sample_rate                      │
│                                                      │
│  3. Audio Sample to Spectrogram Column:              │
│     column = sample / hop_length                     │
│                                                      │
│  4. Combined (Frame to Column):                      │
│     column = (frame / fps) × sr / hop_length         │
│                                                      │
│  5. Window Boundaries:                               │
│     start = max(0, column - 120)                     │
│     end = min(total_columns, start + 240)            │
│                                                      │
│  6. Indicator Position in Window:                    │
│     indicator = column - start                       │
│                                                      │
├──────────────────────────────────────────────────────┤
│  Standard Values:                                    │
│    fps = 30 (frames per second)                      │
│    sr = 22050 (audio samples per second)             │
│    hop_length = 512 (samples per spectrogram column) │
│    window_width = 240 (columns displayed)            │
└──────────────────────────────────────────────────────┘
```

---

## Summary Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                 Complete Synchronization System                  │
└──────────────────────────────────────────────────────────────────┘

INPUT: video.mp4
  │
  ├─► Video Stream ──────────┐
  │   (30 FPS)               │
  │                          │
  └─► Audio Stream ──┐       │
      (22050 Hz)     │       │
                     │       │
                     ▼       │
              Spectrogram    │
              (128 × N)      │
                     │       │
                     │       │
                     └───┬───┘
                         │
                         ▼
                  Synchronization
                   frame → column
                         │
                         ▼
                  Window Extract
                   (240 columns)
                         │
                         ▼
                   Draw Indicator
                    (yellow line)
                         │
                         ▼
                    Display Node
                         │
                         ▼
OUTPUT: Synchronized video + audio visualization

KEY: Every video frame perfectly matches one audio position!
```
