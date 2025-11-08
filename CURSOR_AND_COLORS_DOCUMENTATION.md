# Spectrogram Cursor and Classification Colors

This document describes the new features added to CV Studio for enhanced visual feedback during video playback with spectrogram analysis and classification.

## Features

### 1. Yellow Cursor on Spectrogram (node_video.py)

A yellow vertical cursor has been added to the spectrogram display to show the current playback position of the video relative to the audio spectrogram.

#### How It Works

- **Real-time Position Tracking**: The cursor moves in real-time as the video plays
- **Accurate Synchronization**: The cursor position is calculated based on:
  - Current video frame number
  - Video FPS (frames per second)
  - Audio chunk duration and step duration
  - Spectrogram chunk being displayed

#### Implementation Details

The cursor is drawn using the `_add_playback_cursor_to_spectrogram()` method:

```python
def _add_playback_cursor_to_spectrogram(self, spectrogram_bgr, node_id, frame_number):
    """
    Add a yellow vertical cursor to the spectrogram showing current playback position.
    """
```

**Cursor Characteristics:**
- **Color**: Yellow (BGR: 0, 255, 255)
- **Thickness**: 3 pixels for better visibility
- **Position Calculation**:
  1. Calculate current time from frame number: `current_time = frame_number / fps`
  2. Determine which audio chunk is displayed: `chunk_index = int(current_time / step_duration)`
  3. Calculate position within that chunk: `time_within_chunk = current_time - chunk_start_time`
  4. Convert to pixel position: `cursor_x = int((time_within_chunk / chunk_duration) * width)`

**Visual Example:**
```
Spectrogram Display with Cursor
┌────────────────────────────────┐
│  Frequency                     │
│    ▓▓▓▓▓▓▓▓|▓▓▓▓▓▓▓▓          │ <- Yellow cursor (|)
│    ▓▓▓▓▓▓▓▓|▓▓▓▓▓▓▓▓          │    indicates current
│    ▓▓▓▓▓▓▓▓|▓▓▓▓▓▓▓▓          │    playback position
└────────────────────────────────┘
      Time →
```

### 2. Color-Coded Classification Rankings (node_classification.py)

Classification results now display with different colors based on their ranking position (1st, 2nd, 3rd place).

#### Color Scheme

| Position | Score Rank | Color | BGR Value |
|----------|------------|-------|-----------|
| 1 | Highest | **Red** | (0, 0, 255) |
| 2 | Second | **Green** | (0, 255, 0) |
| 3 | Third | **Blue** | (255, 0, 0) |
| 4+ | Lower | Green | (0, 255, 0) |

#### How It Works

The `draw_classification_info()` method has been overridden in the Classification Node to apply rank-based colors:

```python
def draw_classification_info(self, image, class_ids, class_scores, class_names):
    """
    Override base class method to add color differentiation based on ranking.
    Position 1 (highest score): Red
    Position 2: Green
    Position 3: Blue
    """
```

#### Visual Example

```
Classification Results Display:
┌────────────────────────────────┐
│  12:dog(0.95)    <- Red (1st)  │
│  8:cat(0.87)     <- Green (2nd)│
│  15:bird(0.73)   <- Blue (3rd) │
│  22:fish(0.42)   <- Green      │
└────────────────────────────────┘
```

#### Supported Models

This color scheme works with all classification models:
- MobileNetV3 Small
- MobileNetV3 Large
- EfficientNet B0
- ResNet50
- **Yolo-cls** (audio classification)

## Usage

### Enabling the Spectrogram Cursor

1. Add a **Video** node to your graph
2. Load a video file with audio
3. Enable the "Show Spectrogram" checkbox
4. Play the video
5. The yellow cursor will automatically appear on the spectrogram, moving in sync with the video

### Viewing Color-Coded Classifications

1. Add a **Classification** node to your graph
2. Connect it to an input source (image, video, webcam)
3. Select a classification model
4. The results will automatically display with:
   - **Red** for the highest confidence prediction
   - **Green** for the second-highest
   - **Blue** for the third-highest

## Technical Notes

### Performance

- **Spectrogram Cursor**: Minimal performance impact (simple line drawing operation)
- **Classification Colors**: No performance impact (only changes text color, not computation)

### Compatibility

- Both features are **backward compatible**
- No changes required to existing graphs or configurations
- Works with all existing input sources and models

### Thread Safety

Both features operate on the main update thread and are thread-safe within the CV Studio architecture.

## Code References

### Modified Files

1. **`/node/InputNode/node_video.py`**
   - Added: `_add_playback_cursor_to_spectrogram()` method
   - Modified: `update()` method to call cursor rendering

2. **`/node/DLNode/node_classification.py`**
   - Added: `draw_classification_info()` method override with rank-based colors

### Testing

A comprehensive test file has been added:
- **`/tests/test_cursor_and_colors.py`**: Validates both features

Run the test with:
```bash
python tests/test_cursor_and_colors.py
```

## Future Enhancements

Potential improvements for future versions:

1. **Configurable Cursor Color**: Allow users to choose cursor color
2. **Cursor Style Options**: Different cursor styles (line, arrow, highlight)
3. **Custom Color Schemes**: User-defined colors for classification rankings
4. **Confidence Thresholds**: Color changes based on confidence levels
5. **Multi-cursor Support**: Show past/future positions for context

## Examples

### Example 1: Audio Classification with Spectrogram

1. Load a video with audio content
2. Connect Video node → Classification (Yolo-cls) node
3. Enable spectrogram display
4. Observe:
   - Yellow cursor tracking video playback
   - Classification results in rank-based colors
   - Real-time synchronization between audio and visual feedback

### Example 2: Image Classification Comparison

1. Load multiple images
2. Connect Image node → Classification node
3. Compare results visually:
   - Red text = most confident prediction
   - Green text = alternative prediction
   - Blue text = third option

## Troubleshooting

**Q: The cursor doesn't appear**
- A: Ensure the spectrogram is enabled via the "Show Spectrogram" checkbox
- A: Verify the video has audio content

**Q: Classification colors are all the same**
- A: This is normal for older versions; update to the latest version

**Q: Cursor position seems off**
- A: This can happen if video FPS is incorrectly detected; try with a different video

## License

These features are part of CV Studio and are licensed under the Apache License 2.0.
