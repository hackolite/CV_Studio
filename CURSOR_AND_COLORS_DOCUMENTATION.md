# Spectrogram Cursor and Classification Colors

This document describes the features added to CV Studio for enhanced visual feedback during video playback with spectrogram analysis and classification.

## Features

### 1. Scrolling Spectrogram with Three-Phase Cursor (node_video.py)

A yellow vertical cursor is displayed on the spectrogram to show the current playback position. The cursor uses a three-phase behavior to provide clear visual feedback throughout the entire video playback.

#### How It Works

The cursor behavior has been updated to use **overall video progress** instead of chunk-based progress, ensuring the cursor always reaches the end of the spectrogram when the video completes.

**Three Phases:**

- **Phase 1 - Initial Movement (First 1/3 of video)**: Cursor moves from left (0) to 1/3 of width
  - Based on overall video progress: `video_progress = current_frame / total_frames`
  - When video is 0-33% complete, cursor smoothly moves from 0 to width/3
  
- **Phase 2 - Middle Scrolling (Middle 1/3 of video)**: Cursor behavior within chunks
  - When video is 33-67% complete, uses chunk-based scrolling
  - Cursor can move within chunks and spectrogram scrolls to show progression
  
- **Phase 3 - Final Movement (Last 1/3 of video)**: Cursor moves from 1/3 to the end
  - **NEW**: When video is 67-100% complete, cursor moves from width/3 to right edge
  - At 100% completion, cursor reaches ~99% of width (near right edge)
  - Makes it visually clear when the video playback is complete ✅

**Accurate Synchronization**: The cursor position is calculated based on:
  - Current video frame number and total frame count
  - Video FPS (frames per second)
  - Audio chunk duration and step duration
  - Spectrogram chunk being displayed

#### Implementation Details

The cursor and scrolling are managed by the `_add_playback_cursor_to_spectrogram()` method:

```python
def _add_playback_cursor_to_spectrogram(self, spectrogram_bgr, node_id, frame_number):
    """
    Add a yellow vertical cursor to the spectrogram showing current playback position.
    The cursor behavior has three phases:
    1. Initial phase (first 1/3 of video): cursor moves from left (0) to 1/3 of width
    2. Middle phase (middle 1/3 of video): cursor stays fixed at 1/3, spectrogram scrolls left
    3. Final phase (last 1/3 of video): cursor moves from 1/3 to the end (right edge)
    """
```

**Cursor Characteristics:**
- **Color**: Yellow (BGR: 0, 255, 255)
- **Thickness**: 3 pixels for better visibility
- **Fixed Position**: 1/3 of the spectrogram width (during middle phase)
- **Scrolling**: Spectrogram content shifts left while cursor remains stationary (middle phase)
- **Position Calculation**:
  1. Calculate overall video progress: `video_progress = (frame_number / fps) / total_duration`
  2. Phase 1 (0-33%): cursor moves from 0 to width/3
  3. Phase 2 (33-67%): chunk-based scrolling behavior
  4. Phase 3 (67-100%): cursor moves from width/3 to width (end)

**Visual Example:**
```
Phase 1 - Initial Movement (0-33% of video):
┌────────────────────────────────┐
│  Frequency                     │
│    ▓▓▓▓|▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓    │ <- Cursor moves right (0 to 1/3)
│    ▓▓▓▓|▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓    │
└────────────────────────────────┘

Phase 2 - Middle Scrolling (33-67% of video):
┌────────────────────────────────┐
│  Frequency                     │
│    ▓▓▓▓▓▓▓▓|▓▓▓▓▓▓▓▓▓▓        │ <- Cursor stays at 1/3
│    ▓▓▓▓▓▓▓▓|▓▓▓▓▓▓▓▓▓▓        │    Spectrogram scrolls ←
└────────────────────────────────┘

Phase 3 - Final Movement (67-100% of video):
┌────────────────────────────────┐
│  Frequency                     │
│    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓| │ <- Cursor moves to end ✅
│    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓| │    (1/3 to 100%)
└────────────────────────────────┘
```

### 2. Color-Coded Classification Rankings (node_classification.py)

Classification results now display with different colors based on their ranking position (1st through 5th place and beyond).

#### Color Scheme

| Position | Score Rank | Color | BGR Value |
|----------|------------|-------|-----------|
| 1 | Highest | **Red** | (0, 0, 255) |
| 2 | Second | **Yellow** | (0, 255, 255) |
| 3 | Third | **Blue** | (255, 0, 0) |
| 4 | Fourth | **Violet** | (255, 0, 128) |
| 5 | Fifth | **Magenta** | (255, 0, 255) |
| 6+ | Lower | Green | (0, 255, 0) |

#### How It Works

The `draw_classification_info()` method has been enhanced in the Classification Node to apply rank-based colors:

```python
def draw_classification_info(self, image, class_ids, class_scores, class_names):
    """
    Override base class method to add color differentiation based on ranking.
    Position 1 (index 0, highest score): Red
    Position 2 (index 1): Yellow
    Position 3 (index 2): Blue
    Position 4 (index 3): Violet
    Position 5 (index 4): Magenta
    """
```

#### Visual Example

```
Classification Results Display:
┌────────────────────────────────┐
│  12:dog(0.95)    <- Red (1st)  │
│  8:cat(0.87)     <- Yellow (2nd)│
│  15:bird(0.73)   <- Blue (3rd) │
│  22:fish(0.42)   <- Violet (4th)│
│  9:horse(0.31)   <- Magenta (5th)│
│  5:mouse(0.18)   <- Green (6th+)│
└────────────────────────────────┘
```

#### Supported Models

This color scheme works with all classification models:
- MobileNetV3 Small
- MobileNetV3 Large
- EfficientNet B0
- ResNet50
- **Yolo-cls** (audio classification)

### 3. Enhanced Classification Display in Concat Node (node_image_concat.py)

When classification results are displayed in the Image Concat node, they appear with enhanced formatting for better visibility.

#### Display Characteristics

- **Size**: Larger text (font scale 1.0 vs 0.6, thickness 3 vs 2)
- **Position**: Bottom left corner instead of top left
- **Colors**: Same rank-based color scheme as classification node
- **Line Spacing**: Increased spacing (35px vs 20px) for better readability

#### Implementation

```python
def draw_classification_info(self, image, class_ids, class_scores, class_names):
    """
    Override base class method to display classification results
    bigger and at the bottom left of the image.
    """
    # Larger font size and thicker text
    font_scale = 1.0  # Increased from 0.6
    thickness = 3     # Increased from 2
    line_spacing = 35  # Increased from 20
    
    # Calculate starting position from bottom
    # Position at bottom left with margin
```

**Visual Example in Concat View:**
```
┌─────────────────────────────────────┐
│                                     │
│        Video/Image Display          │
│                                     │
│                                     │
│  12:dog(0.95)    <- Red (larger)   │
│  8:cat(0.87)     <- Yellow (larger)│
│  15:bird(0.73)   <- Blue (larger)  │
└─────────────────────────────────────┘
     ↑ Bottom left positioning
```

### 4. Audio Storage Feature (node_video.py)

When a video is loaded and preprocessed, the audio track is automatically extracted and saved as a separate file for reuse.

#### How It Works

During video preprocessing in the `_preprocess_video()` method:

1. **Audio Extraction**: Audio is extracted from the video using librosa
2. **MP3 Conversion**: The extracted audio is converted to MP3 format using ffmpeg
3. **File Storage**: The MP3 file is saved in the same directory as the video with suffix `_audio.mp3`
4. **Fallback**: If MP3 conversion fails, a WAV file is saved instead

#### Saved File Format

**Primary format: MP3**
- Filename: `{video_name}_audio.mp3`
- Codec: libmp3lame (high quality)
- Quality: qscale 2 (high quality setting)
- Location: Same folder as the source video

**Fallback format: WAV**
- Filename: `{video_name}_audio.wav`
- Used when ffmpeg MP3 encoding is unavailable
- Preserves original sample rate and audio data

#### Benefits

- **Reusability**: Audio file can be used by other applications without re-extraction
- **Performance**: Avoids repeated audio extraction from video
- **Convenience**: Stored alongside video for easy access
- **Quality**: High-quality MP3 encoding preserves audio fidelity

#### Example

When loading a video file:
```
Video: /path/to/videos/my_video.mp4
Audio saved as: /path/to/videos/my_video_audio.mp3
```

Console output during preprocessing:
```
🎵 Extracting audio...
✅ Audio extracted (SR: 22050 Hz, Duration: 30.5s)
💾 Audio saved as MP3: /path/to/videos/my_video_audio.mp3
```

## Usage

### Enabling the Three-Phase Cursor Spectrogram

1. Add a **Video** node to your graph
2. Load a video file with audio
3. Enable the "Show Spectrogram" checkbox
4. Play the video
5. Observe the cursor behavior:
   - **Phase 1 (0-33%)**: Cursor moves from left to 1/3 position
   - **Phase 2 (33-67%)**: Cursor fixed at 1/3, spectrogram scrolls
   - **Phase 3 (67-100%)**: Cursor moves from 1/3 to end, clearly showing completion ✅

### Accessing Saved Audio Files

1. Load a video file in the Video node
2. The audio is automatically extracted and saved during preprocessing
3. Check the same folder as your video file
4. Look for `{video_name}_audio.mp3` or `{video_name}_audio.wav`
5. The audio file can be used in other applications or nodes

### Viewing Color-Coded Classifications

1. Add a **Classification** node to your graph
2. Connect it to an input source (image, video, webcam)
3. Select a classification model
4. The results will automatically display with rank-based colors

### Enhanced Display in Concat Node

1. Add an **Image Concat** node to your graph
2. Connect classification results to one of its inputs
3. Classification results will appear larger and at the bottom left of each image slot

## Technical Notes

### Performance

- **Three-Phase Cursor**: Minimal performance impact (simple array operations and line drawing)
- **Audio Storage**: One-time cost during video preprocessing, no runtime impact
- **Classification Colors**: No performance impact (only changes text color, not computation)
- **Concat Display**: Negligible impact (same rendering, just different position and scale)

### Compatibility

- All features are **backward compatible**
- No changes required to existing graphs or configurations
- Works with all existing input sources and models
- Audio files are created automatically without affecting existing functionality

### Thread Safety

All features operate on the main update thread and are thread-safe within the CV Studio architecture.

## Code References

### Modified Files

1. **`/node/InputNode/node_video.py`**
   - Modified: `_add_playback_cursor_to_spectrogram()` method to implement three-phase cursor behavior
     - Added video progress calculation based on total frames
     - Added Phase 3 logic for final 1/3 of video (cursor moves to end)
   - Modified: `_preprocess_video()` method to add audio storage
     - Saves extracted audio as MP3 (primary) or WAV (fallback)
     - Files saved in same directory as source video
   - Modified: `update()` method to call cursor rendering

2. **`/node/DLNode/node_classification.py`**
   - Modified: `draw_classification_info()` method with extended 5-color ranking system

3. **`/node/VideoNode/node_image_concat.py`**
   - Added: `draw_classification_info()` method override for larger, bottom-left display

### Testing

Test scripts validate the features:
- **Custom test script**: Validates three-phase cursor behavior and end-of-video progression
- **`/tests/test_cursor_and_colors.py`**: Validates cursor, scrolling, and color features

Run tests with:
```bash
python tests/test_cursor_and_colors.py
```

## Future Enhancements

Potential improvements for future versions:

1. **Configurable Cursor Options**: 
   - Adjustable cursor color
   - Configurable fixed position (currently 1/3)
   - Different cursor styles (line, arrow, highlight)

2. **Custom Color Schemes**: 
   - User-defined colors for classification rankings
   - Theme support (dark mode, light mode)
   - Colorblind-friendly palettes

3. **Advanced Scrolling**:
   - Configurable scroll speed
   - Smooth scrolling animation
   - Multiple scroll modes (fixed cursor, centered cursor, etc.)

4. **Display Options**:
   - Configurable text size and position
   - Transparency/opacity controls
   - Font selection

## Examples

### Example 1: Audio Classification with Three-Phase Cursor

1. Load a video with audio content
2. Connect Video node → Classification (Yolo-cls) node
3. Enable spectrogram display
4. Observe the three-phase cursor behavior:
   - **Phase 1 (0-33%)**: Yellow cursor moves from left to 1/3 position
   - **Phase 2 (33-67%)**: Cursor fixed at 1/3, spectrogram scrolls left
   - **Phase 3 (67-100%)**: Cursor moves from 1/3 to right edge, showing clear completion ✅
   - Classification results in rank-based colors (red, yellow, blue, violet, magenta)
   - Real-time synchronization between audio and visual feedback
5. Check the video folder for the saved audio file (`{video_name}_audio.mp3`)

### Example 2: Multi-View Classification Comparison

1. Load multiple images or video frames
2. Connect to Classification nodes with different models
3. Use Image Concat node to display results side-by-side
4. Observe:
   - Larger classification text at bottom left of each view
   - Easy comparison of classification results across models
   - Color-coded rankings for quick visual scanning

### Example 3: Real-Time Audio Analysis

1. Use Video node with audio-rich content
2. Connect to Yolo-cls for audio classification
3. Enable spectrogram display
4. Add Image Concat to show both video and spectrogram
5. Observe synchronized audio-visual analysis with enhanced display

## Troubleshooting

**Q: The cursor doesn't reach the end of the spectrogram**
- A: This is now fixed! The cursor will reach ~99% at video completion (Phase 3)
- A: Verify the video has proper FPS metadata and frame count

**Q: The cursor stays fixed in the middle**
- A: This is expected during Phase 2 (middle 33-67% of video)
- A: The cursor will start moving again in Phase 3 (last 33% of video)

**Q: Spectrogram doesn't scroll**
- A: This is normal during Phase 1 (first 33%) and Phase 3 (last 33%)
- A: Scrolling only occurs during Phase 2 (middle 33-67% of video)
- A: Ensure the video is playing (not paused)

**Q: Audio file not created**
- A: Check console output for preprocessing errors
- A: Ensure ffmpeg is installed for MP3 conversion
- A: Check write permissions in the video directory
- A: A WAV file should be created if MP3 conversion fails

**Q: Audio file location**
- A: Audio is saved in the same folder as the source video
- A: Look for `{video_name}_audio.mp3` or `{video_name}_audio.wav`

**Q: Classification colors don't appear correctly**
- A: Verify you have at least 5 classification results for all colors
- A: Update to the latest version

**Q: Text in concat node is too large/small**
- A: This is currently fixed at font_scale=1.0; customization coming in future updates

**Q: Text position is cut off at bottom**
- A: Image resolution may be too small; the positioning accounts for text height

## License

These features are part of CV Studio and are licensed under the Apache License 2.0.
