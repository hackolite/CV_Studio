# Spectrogram Cursor and Classification Colors

This document describes the features added to CV Studio for enhanced visual feedback during video playback with spectrogram analysis and classification.

## Features

### 1. Scrolling Spectrogram with Fixed Cursor (node_video.py)

A yellow vertical cursor is displayed on the spectrogram to show the current playback position. The cursor moves during the first portion of playback, then stays fixed while the spectrogram scrolls to the left.

#### How It Works

- **Initial Cursor Movement**: During the first third of the spectrogram, the cursor moves from left to right (0 to width/3)
- **Fixed Cursor with Scrolling**: After the first third, the cursor stays fixed at 1/3 of the width and the spectrogram scrolls to the left
- **Accurate Synchronization**: The cursor position and scrolling are calculated based on:
  - Current video frame number
  - Video FPS (frames per second)
  - Audio chunk duration and step duration
  - Spectrogram chunk being displayed

#### Implementation Details

The cursor and scrolling are managed by the `_add_playback_cursor_to_spectrogram()` method:

```python
def _add_playback_cursor_to_spectrogram(self, spectrogram_bgr, node_id, frame_number):
    """
    Add a yellow vertical cursor to the spectrogram showing current playback position.
    On the first frame, the cursor moves. After that, the cursor stays fixed at 1/3 of the width
    and the spectrogram scrolls to the left.
    """
```

**Cursor and Scrolling Characteristics:**
- **Color**: Yellow (BGR: 0, 255, 255)
- **Thickness**: 3 pixels for better visibility
- **Fixed Position**: 1/3 of the spectrogram width (after initial movement)
- **Scrolling**: Spectrogram content shifts left while cursor remains stationary
- **Position Calculation**:
  1. Calculate current time from frame number: `current_time = frame_number / fps`
  2. Determine which audio chunk is displayed: `chunk_index = int(current_time / step_duration)`
  3. Calculate position within that chunk: `time_within_chunk = current_time - chunk_start_time`
  4. For first 1/3: cursor moves proportionally
  5. After 1/3: cursor fixed, spectrogram scrolls left

**Visual Example:**
```
Initial Phase (first 1/3):
┌────────────────────────────────┐
│  Frequency                     │
│    ▓▓▓▓|▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓    │ <- Cursor moves right
│    ▓▓▓▓|▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓    │
└────────────────────────────────┘

After 1/3 (scrolling phase):
┌────────────────────────────────┐
│  Frequency                     │
│    ▓▓▓▓▓▓▓▓|▓▓▓▓▓▓▓▓▓▓        │ <- Cursor stays at 1/3
│    ▓▓▓▓▓▓▓▓|▓▓▓▓▓▓▓▓▓▓        │    Spectrogram scrolls ←
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

## Usage

### Enabling the Scrolling Spectrogram

1. Add a **Video** node to your graph
2. Load a video file with audio
3. Enable the "Show Spectrogram" checkbox
4. Play the video
5. The yellow cursor will move initially, then stay fixed while the spectrogram scrolls

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

- **Scrolling Spectrogram**: Minimal performance impact (simple array operations and line drawing)
- **Classification Colors**: No performance impact (only changes text color, not computation)
- **Concat Display**: Negligible impact (same rendering, just different position and scale)

### Compatibility

- All features are **backward compatible**
- No changes required to existing graphs or configurations
- Works with all existing input sources and models

### Thread Safety

All features operate on the main update thread and are thread-safe within the CV Studio architecture.

## Code References

### Modified Files

1. **`/node/InputNode/node_video.py`**
   - Modified: `_add_playback_cursor_to_spectrogram()` method to implement scrolling behavior
   - Modified: `update()` method to call cursor rendering

2. **`/node/DLNode/node_classification.py`**
   - Modified: `draw_classification_info()` method with extended 5-color ranking system

3. **`/node/VideoNode/node_image_concat.py`**
   - Added: `draw_classification_info()` method override for larger, bottom-left display

### Testing

A comprehensive test file validates all features:
- **`/tests/test_cursor_and_colors.py`**: Validates cursor, scrolling, and color features

Run the test with:
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

### Example 1: Audio Classification with Scrolling Spectrogram

1. Load a video with audio content
2. Connect Video node → Classification (Yolo-cls) node
3. Enable spectrogram display
4. Observe:
   - Yellow cursor initially moving, then staying fixed at 1/3 width
   - Spectrogram scrolling to the left during playback
   - Classification results in rank-based colors (red, yellow, blue, violet, magenta)
   - Real-time synchronization between audio and visual feedback

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

**Q: The cursor doesn't stay fixed**
- A: Make sure you're past the first 1/3 of the chunk duration
- A: Verify the video has proper FPS metadata

**Q: Spectrogram doesn't scroll**
- A: This is normal during the first 1/3 of playback
- A: Ensure the video is playing (not paused)

**Q: Classification colors don't appear correctly**
- A: Verify you have at least 5 classification results for all colors
- A: Update to the latest version

**Q: Text in concat node is too large/small**
- A: This is currently fixed at font_scale=1.0; customization coming in future updates

**Q: Text position is cut off at bottom**
- A: Image resolution may be too small; the positioning accounts for text height

## License

These features are part of CV Studio and are licensed under the Apache License 2.0.
