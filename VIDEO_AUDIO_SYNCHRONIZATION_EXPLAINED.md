# Video-Audio Synchronization: Complete Process Explanation

## Overview

This document explains in detail how the CV Studio Video Node processes a video file by:
1. **Splitting** audio and video streams
2. **Cutting** video into individual frames
3. **Matching** audio spectrogram frames with corresponding video frames
4. **Playing** the synchronized content in the node

---

## Step 1: Splitting Audio and Video

### What Happens
When a user selects a video file, the system separates the audio stream from the video stream.

### Implementation
**Location:** `node/InputNode/node_video.py`, method `_prepare_spectrogram()`, lines 286-322

```python
# Step 1A: Try to extract audio directly from video
y, sr = librosa.load(movie_path, sr=22050)

# Step 1B: If direct extraction fails, use ffmpeg
subprocess.run([
    'ffmpeg', '-i', movie_path,    # Input: video file
    '-vn',                          # Remove video stream
    '-acodec', 'pcm_s16le',        # Audio codec
    '-ar', '22050',                # Sample rate: 22050 Hz
    '-ac', '1',                    # Mono audio (1 channel)
    '-y', tmp_audio_path           # Output: temporary audio file
])
```

### Result
- **Audio stream:** Extracted as digital samples at 22,050 Hz (22,050 samples per second)
- **Video stream:** Remains in original file, accessed separately via OpenCV

---

## Step 2: Video Frame Extraction

### What Happens
The video is processed frame-by-frame during playback.

### Implementation
**Location:** `node/InputNode/node_video.py`, method `update()`, lines 464-483

```python
# Open video file with OpenCV
video_capture = cv2.VideoCapture(movie_path)

# Extract video properties
fps = video_capture.get(cv2.CAP_PROP_FPS)  # e.g., 30 frames per second

# Read frames one by one during playback
while True:
    ret, frame = video_capture.read()  # Read next frame
    if not ret:
        # End of video reached
        if loop_flag:
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to frame 0
            self._frame_count[str(node_id)] = 0             # Reset frame counter
        break
    
    self._frame_count[str(node_id)] += 1  # Track current frame number
    
    if (self._frame_count[str(node_id)] % skip_rate) == 0:
        break  # Display this frame
```

### Result
- **Video frames:** Each frame is a 2D array of pixels (height × width × 3 colors)
- **Frame tracking:** `_frame_count` keeps track of which frame is currently displayed
- **Frame rate:** System knows how many frames per second (e.g., 30 FPS)

---

## Step 3: Audio Spectrogram Generation

### What Happens
The extracted audio is transformed into a visual spectrogram that shows frequencies over time.

### Implementation
**Location:** `node/InputNode/node_video.py`, method `_prepare_spectrogram()`, lines 324-366

```python
# Step 3A: Compute mel-spectrogram from audio
S = librosa.feature.melspectrogram(
    y=y,                    # Audio signal
    sr=sr,                  # Sample rate (22050 Hz)
    n_fft=2048,            # FFT window size
    hop_length=512,        # Samples between columns (CRITICAL for sync!)
    n_mels=128,            # Number of frequency bands
    power=2.0              # Power spectrogram
)

# Step 3B: Convert to decibel scale for better visualization
S_db = librosa.power_to_db(S, ref=np.max)

# Step 3C: Normalize to 0-1 range
S_normalized = (S_db - S_db.min()) / (S_db.max() - S_db.min() + 1e-6)

# Step 3D: Apply color mapping (magma colormap)
cmap = matplotlib.cm.get_cmap('magma')
S_colored = cmap(S_normalized)

# Step 3E: Convert to 8-bit RGB image
S_rgb = (S_colored[:, :, :3] * 255).astype(np.uint8)

# Step 3F: Flip vertically (low frequencies at bottom)
S_rgb = np.flipud(S_rgb)

# Step 3G: Convert to BGR for OpenCV compatibility
S_bgr = cv2.cvtColor(S_rgb, cv2.COLOR_RGB2BGR)
```

### Spectrogram Structure
- **Rows (Y-axis):** Frequency bands (128 mel-bands, low frequencies at bottom)
- **Columns (X-axis):** Time progression
- **Each column:** Represents 512 audio samples = 512/22050 ≈ 0.023 seconds

### Result
- **Spectrogram array:** 2D image (128 rows × N columns) stored in `_spectrogram_array[node_id]`
- **Metadata stored:** Audio sample rate, hop length, video FPS

---

## Step 4: Frame-by-Frame Synchronization

### The Matching Formula

This is the **CRITICAL STEP** where audio and video are synchronized.

**Location:** `node/InputNode/node_video.py`, method `update()`, lines 512-527

```python
# Step 4A: Get current video frame number
current_frame = self._frame_count.get(str(node_id), 0)  # e.g., frame 900

# Step 4B: Convert frame number to time in seconds
fps = 30.0  # frames per second
current_time = current_frame / fps  # 900 / 30 = 30.0 seconds

# Step 4C: Convert time to audio sample position
sr = 22050  # audio sample rate (samples per second)
current_sample = int(current_time * sr)  # 30.0 * 22050 = 661,500 samples

# Step 4D: Convert audio sample to spectrogram column
hop_length = 512  # samples per column
spectrogram_col = int(current_sample / hop_length)  # 661,500 / 512 = 1,292

# Step 4E: This means:
# - Video is showing frame 900 (at 30 seconds)
# - Audio spectrogram column 1,292 corresponds to that exact moment
```

### Why This Works

The synchronization is mathematically precise:

```
Video Frame → Time → Audio Sample → Spectrogram Column
    900     → 30.0s →   661,500    →      1,292

Every video frame maps to exactly one spectrogram column!
```

### Key Parameters (Must Match!)
- **hop_length = 512:** Same value used to generate spectrogram
- **sr = 22050:** Same sample rate used to extract audio
- **fps:** Actual frame rate from video file

---

## Step 5: Scrolling Window Display

### What Happens
Instead of showing the entire spectrogram (which would be compressed and unreadable), the system shows a **sliding window** centered on the current position.

### Implementation
**Location:** `node/InputNode/node_video.py`, method `update()`, lines 529-567

```python
# Step 5A: Define window size (matches display width)
window_width = 240  # pixels
half_window = 120   # pixels

# Step 5B: Calculate window boundaries
start_col = max(0, spectrogram_col - half_window)
end_col = min(full_spectrogram.shape[1], start_col + window_width)

# Step 5C: Extract the window slice
spectrogram_window = full_spectrogram[:, start_col:end_col].copy()

# Step 5D: Calculate indicator position within window
indicator_col = spectrogram_col - start_col

# Step 5E: Draw yellow line at current position
if 0 <= indicator_col < spectrogram_window.shape[1]:
    cv2.line(spectrogram_window, 
            (indicator_col, 0), 
            (indicator_col, spectrogram_window.shape[0] - 1), 
            (0, 255, 255),  # Yellow in BGR
            2)              # 2 pixels wide

# Step 5F: Handle edge cases (start/end of video)
if spectrogram_window.shape[1] < window_width:
    # Pad with black pixels to maintain consistent width
    pad_width = window_width - spectrogram_window.shape[1]
    if start_col == 0:
        # At start: pad right
        padding = np.zeros((spectrogram_window.shape[0], pad_width, 3), dtype=np.uint8)
        spectrogram_window = np.hstack([spectrogram_window, padding])
    else:
        # At end: pad left
        padding = np.zeros((spectrogram_window.shape[0], pad_width, 3), dtype=np.uint8)
        spectrogram_window = np.hstack([padding, spectrogram_window])
```

### Visual Representation

```
Full Spectrogram (e.g., 12,919 columns for 5-minute video):
[████████████████████████████████████████████████████████████████████████]
                         ↑
                    Current position
                    (column 1,292)

Displayed Window (240 columns):
              [█████████████|█████████████]
                            ↑
                      Yellow indicator
                   (centered in window)

As video plays → window slides right → creates scrolling effect
```

### Scrolling Example

```
Frame 0:     Window shows columns [0-240]       | Indicator at column 0 (left edge)
Frame 300:   Window shows columns [150-390]     | Indicator at column 120 (centered)
Frame 900:   Window shows columns [1172-1412]   | Indicator at column 120 (centered)
Frame 5000:  Window shows columns [6386-6626]   | Indicator at column 120 (centered)
```

---

## Step 6: Playing in the Node

### What Happens
The synchronized video frame and spectrogram window are displayed together in the DearPyGUI node interface.

### Implementation
**Location:** `node/InputNode/node_video.py`, method `update()`, lines 493-499 and 572-578

```python
# Step 6A: Convert video frame to display texture
if frame is not None:
    texture = self.convert_cv_to_dpg(
        frame,              # Video frame (numpy array)
        small_window_w,     # 240 pixels
        small_window_h,     # 135 pixels
    )
    dpg_set_value(tag_node_output_image, texture)  # Update video display

# Step 6B: Convert spectrogram window to display texture
texture = self.convert_cv_to_dpg(
    spectrogram_window,  # Spectrogram window with yellow line
    small_window_w,      # 240 pixels
    small_window_h       # 135 pixels
)
dpg_set_value(tag_node_spectrogram_value, texture)  # Update spectrogram display
```

### User Interface Layout

```
┌─────────────────────────────────┐
│       Video Node                │
├─────────────────────────────────┤
│  [Select Movie]                 │
├─────────────────────────────────┤
│  ┌───────────────────────────┐  │  ← Video frame display
│  │                           │  │    (240×135 pixels)
│  │     Video Frame           │  │
│  │                           │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  ☑ Show Spectrogram             │
│  ┌───────────────────────────┐  │  ← Spectrogram display
│  │     ███|███████            │  │    (240×135 pixels)
│  │     ███|███████            │  │    Yellow line shows
│  │     ███|███████            │  │    current position
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  ☑ Loop                         │
│  Skip Rate: [===|=========] 1   │
│  [Start]                        │
└─────────────────────────────────┘
```

---

## Complete Data Flow Summary

### Initialization (when video is loaded)

```
1. User selects video file
   ↓
2. Audio extraction
   - ffmpeg splits audio stream
   - Audio: 22050 samples/second
   ↓
3. Spectrogram generation
   - mel-spectrogram with hop_length=512
   - Result: 2D array (128 × N_columns)
   ↓
4. Store metadata
   - Audio: sample_rate, hop_length
   - Video: fps
```

### Playback (every frame update)

```
1. Read next video frame
   - frame_count increments
   - Frame stored as numpy array
   ↓
2. Calculate synchronization
   - frame → time → sample → column
   - Example: frame 900 → 30s → 661500 → col 1292
   ↓
3. Extract spectrogram window
   - 240 columns centered at current position
   - Draw yellow line at center
   ↓
4. Display both
   - Video frame in top display
   - Spectrogram window in bottom display
   ↓
5. Repeat for next frame
```

---

## Key Synchronization Points

### 1. **Temporal Resolution**
- **Video:** 1 frame = 1/30 second = 0.033 seconds (at 30 FPS)
- **Audio:** 1 spectrogram column = 512/22050 = 0.023 seconds
- **Result:** Audio resolution is higher than video (more detail)

### 2. **Consistency**
The hop_length=512 is **CRITICAL**:
- Used during spectrogram generation
- Used during playback synchronization
- Changing it would break sync!

### 3. **Precision**
Frame-to-column mapping is mathematically exact:
```python
# Forward: frame → column
column = int((frame / fps) * sr / hop_length)

# Backward: column → frame (approximately)
frame = int((column * hop_length / sr) * fps)
```

---

## Practical Example

### Video: 30 FPS, 1 minute duration

```
Video frames:    1800 frames (30 fps × 60 seconds)
Audio samples:   1,323,000 samples (22050 Hz × 60 seconds)
Spectrogram:     2584 columns (1,323,000 / 512)

Frame 0:     0.000s → sample 0       → column 0
Frame 30:    1.000s → sample 22,050  → column 43
Frame 900:   30.00s → sample 661,500 → column 1,292
Frame 1800:  60.00s → sample 1,323,000 → column 2,584
```

### Window Display

At frame 900 (30 seconds):
- Spectrogram column: 1,292
- Window shows: columns 1,172 to 1,412 (240 columns)
- Yellow line at: column 120 within window (center)
- Actual position: column 1,292 in full spectrogram

---

## Benefits of This Approach

### ✓ **Perfect Synchronization**
Mathematical formula ensures audio and video stay in sync

### ✓ **Frame-by-Frame Accuracy**
Every video frame matches exactly one audio moment

### ✓ **Readable Spectrogram**
1:1 pixel mapping (no compression) makes frequencies visible

### ✓ **Smooth Scrolling**
Window slides smoothly as video plays

### ✓ **Loop Support**
When video loops, both frame_count and position reset to 0

### ✓ **Efficient**
- Audio extraction: once at load time
- Spectrogram generation: once at load time
- Playback: only window extraction and line drawing (fast)

---

## Technical Details

### Frequency Bands (Mel Scale)
The spectrogram uses 128 mel-frequency bands:
- **Bottom rows:** Low frequencies (bass, 0-500 Hz)
- **Middle rows:** Mid frequencies (vocals, 500-4000 Hz)
- **Top rows:** High frequencies (treble, 4000-11025 Hz)

### Color Mapping
- **Magma colormap:** Dark purple (quiet) → Bright yellow (loud)
- **Yellow indicator line:** High contrast, easy to see
- **BGR format:** OpenCV/DearPyGUI compatibility

### Performance Optimizations
1. **Pre-computation:** Spectrogram generated once, reused
2. **Window extraction:** Only 240 columns processed per frame
3. **Metadata caching:** FPS, sample rate stored for quick access
4. **Efficient drawing:** Single line operation with cv2.line()

---

## Files Modified

1. **`node/InputNode/node_video.py`**
   - `_prepare_spectrogram()`: Audio extraction and spectrogram generation
   - `update()`: Frame-by-frame synchronization and display

2. **Storage Structures**
   - `_spectrogram_array[node_id]`: Full spectrogram (128 × N_columns)
   - `_spectrogram_meta[node_id]`: {y, sr, hop_length, fps}
   - `_frame_count[node_id]`: Current video frame number
   - `_video_capture[node_id]`: OpenCV VideoCapture object

---

## Conclusion

The video-audio synchronization system works by:
1. **Splitting** audio and video into separate streams
2. **Processing** video frame-by-frame with frame counting
3. **Generating** a time-frequency spectrogram from audio
4. **Matching** each video frame to a spectrogram column using precise math
5. **Displaying** a synchronized, scrolling window with visual indicator

The result is a **perfectly synchronized, readable, and smooth** audio-visual display that helps users understand what audio frequencies are present at each moment in the video.
