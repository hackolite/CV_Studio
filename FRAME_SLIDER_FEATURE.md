# Frame Slider Feature for Spectrogram Visualization

## Overview

This feature adds a **Frame Width slider** to the Video node that allows users to control the width of the spectrogram window that is sent to the classification node (specifically yolo-cls). This provides more precise control over the audio segment analyzed during classification.

## What's New

### Video Node Enhancements

1. **New Frame Width Slider (Input06)**
   - Label: "Frame Width"
   - Range: 60 to 240 pixels
   - Default: 240 pixels (full window width)
   - Location: Below the Speed slider in the Video node

2. **Dynamic Spectrogram Windowing**
   - The spectrogram window width now adjusts based on the slider value
   - Smaller values = narrower audio segments for analysis
   - Larger values = wider audio segments for analysis

### Classification Node Enhancements

1. **Frame Width Processing for Yolo-cls**
   - When using Yolo-cls model, the spectrogram is automatically resized to match the frame width slider value
   - Other classification models (ResNet50, MobileNetV3, etc.) are not affected

2. **Backward Compatibility**
   - All existing nodes continue to work without modification
   - The feature gracefully handles both new metadata format and old format

## Technical Details

### Data Flow

```
Video Node
  ├─ User adjusts Frame Width slider (60-240 pixels)
  ├─ Spectrogram window is extracted based on slider value
  ├─ Audio data is passed as tuple: (spectrogram, frame_width)
  └─ Returned via node_audio_dict

Classification Node
  ├─ Receives audio data via get_input_frame()
  ├─ Extracts frame and metadata from tuple
  ├─ For Yolo-cls: resizes spectrogram to frame_width
  └─ For other models: uses frame as-is
```

### Code Changes

#### 1. Video Node (`node/InputNode/node_video.py`)

**Added:**
- `tag_node_input06_name` and `tag_node_input06_value_name` tags
- Frame Width slider UI element
- Slider value persisted in `get_setting_dict()` and `set_setting_dict()`

**Modified:**
- `update()` method now uses `frame_width` from slider for spectrogram windowing
- Audio data returned as tuple: `(spectrogram_bgr, frame_width)`

#### 2. Base Node (`node/basenode.py`)

**Modified:**
- `get_input_frame()` now returns `(frame, metadata)` tuple
- Handles both old format (single value) and new format (tuple)
- Extracts frame_width from tuple and creates metadata dictionary

#### 3. Classification Node (`node/DLNode/node_classification.py`)

**Modified:**
- `update()` method unpacks `(frame, audio_metadata)` from `get_input_frame()`
- Extracts `frame_width` from metadata
- For Yolo-cls model: resizes spectrogram to match `frame_width`
- For other models: uses frame without modification

#### 4. Other Nodes

**Updated to handle new signature:**
- All DL nodes (semantic segmentation, face detection, monocular depth, object detection)
- All Process nodes (blur, canny, contrast, crop, etc.)
- Changes: `frame = ...` → `frame, _ = ...` to discard metadata

## Usage Example

### Step-by-Step Workflow

1. **Load Video with Audio**
   - Add Video node to canvas
   - Select a video file with audio track
   - Enable "Show Spectrogram" checkbox

2. **Adjust Frame Width**
   - Use the "Frame Width" slider to control analysis window
   - Smaller values (e.g., 60-120) = more focused analysis
   - Larger values (e.g., 180-240) = broader context

3. **Connect to Classification**
   - Connect Video node's spectrogram output (AUDIO) to Classification node input
   - Select "Yolo-cls" model in Classification node
   - The spectrogram will be automatically resized based on Frame Width slider

4. **Observe Results**
   - Classification analyzes only the window specified by Frame Width
   - Results are more precise for narrower windows
   - Results have more context for wider windows

### Visual Feedback

The spectrogram visualization shows:
- **Green cursors** at left and right edges (window boundaries)
- **Yellow cursor** in the middle (current playback position)
- The width between green cursors matches the Frame Width slider value

## Benefits

### 1. Precision Control
- Users can fine-tune the audio segment size for classification
- Useful for isolating specific sounds or events

### 2. Performance Optimization
- Smaller windows = faster processing (less data to analyze)
- Larger windows = more context for classification

### 3. Flexibility
- Different audio types may benefit from different window sizes
- Users can experiment to find optimal settings

### 4. Visual Clarity
- The spectrogram display updates to show the exact window being analyzed
- Clear visual feedback helps users understand what's being processed

## Backward Compatibility

### Guaranteed Compatibility

1. **Existing Projects**
   - Projects created before this feature continue to work
   - Default frame width is full window (240 pixels)
   - No changes needed to existing node graphs

2. **Other Classification Models**
   - ResNet50, MobileNetV3, EfficientNet continue to work as before
   - Only Yolo-cls uses the frame width information
   - No performance impact on other models

3. **Non-Audio Inputs**
   - Image inputs work exactly as before
   - Metadata is only created for audio (spectrogram) inputs
   - All Process nodes ignore metadata

## Testing

### Test Coverage

1. **Feature Tests** (`tests/test_frame_slider_feature.py`)
   - Validates UI elements exist
   - Checks settings persistence
   - Verifies metadata passing
   - Ensures Yolo-cls integration

2. **Integration Tests** (`tests/test_frame_slider_integration.py`)
   - Tests metadata tuple handling
   - Validates backward compatibility
   - Checks frame width extraction
   - Verifies conditional logic

3. **Existing Tests**
   - All existing tests continue to pass
   - No breaking changes to existing functionality

## Troubleshooting

### Frame Width Not Affecting Classification

**Problem:** Changing Frame Width slider doesn't affect results

**Solutions:**
- Ensure you're using Yolo-cls model (not ResNet50 or others)
- Check that Video node is connected to Classification node via AUDIO output
- Verify "Show Spectrogram" is enabled in Video node

### Spectrogram Looks Different

**Problem:** Spectrogram appearance changed after update

**Solution:** This is expected. The window width now matches the slider value. Adjust the Frame Width slider to 240 for full width.

## Future Enhancements

Potential improvements for future versions:

1. **Per-Model Settings**
   - Allow different frame widths for different classification models
   - Save preferences per model type

2. **Auto-Optimization**
   - Automatically suggest optimal frame width based on audio characteristics
   - Adaptive windowing based on detected events

3. **Real-Time Adjustment**
   - Allow frame width adjustment during playback
   - Live preview of classification results at different widths

## API Reference

### Video Node

**New Attribute:**
```python
tag_node_input06_value_name  # Frame Width slider value (60-240)
```

**Audio Data Format:**
```python
# Old format (still supported)
audio_data = spectrogram_bgr

# New format (with metadata)
audio_data = (spectrogram_bgr, frame_width)
```

### Base Node

**Modified Method:**
```python
def get_input_frame(self, connection_list, node_image_dict, node_audio_dict=None):
    """
    Returns: (frame, metadata) tuple
    - frame: Image or spectrogram data
    - metadata: None for images, dict with 'frame_width' for audio
    """
```

### Classification Node

**Frame Width Access:**
```python
frame, audio_metadata = self.get_input_frame(...)
frame_width = None
if audio_metadata is not None and 'frame_width' in audio_metadata:
    frame_width = audio_metadata['frame_width']
```

## Summary

The Frame Slider feature provides users with precise control over spectrogram window size for audio classification tasks. It's specifically designed to work with Yolo-cls for audio classification while maintaining full backward compatibility with all existing nodes and workflows.

**Key Points:**
- ✅ New Frame Width slider (60-240 pixels) in Video node
- ✅ Dynamic spectrogram windowing based on slider value
- ✅ Automatic integration with Yolo-cls classification
- ✅ Full backward compatibility with existing projects
- ✅ Visual feedback via boundary cursors
- ✅ Comprehensive test coverage
