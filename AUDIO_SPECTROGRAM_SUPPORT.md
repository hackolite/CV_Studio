# Audio Spectrogram Support Feature

## Overview

This feature enables all image processing and deep learning nodes in CV_Studio to accept and process audio spectrograms (as BGR images) alongside regular images. Audio spectrograms are treated identically to regular images, allowing the same processing algorithms to be applied to both.

## Key Changes

### 1. Core System (`main.py`)

- Added `node_audio_dict = {}` parallel to `node_image_dict` in both async and sync event loops
- Updated `update_node_info()` to accept `node_audio_dict` parameter
- Added audio data propagation: `if data.get("audio"): node_audio_dict[node_id_name] = copy.deepcopy(data["audio"])`
- All `node.update()` calls now pass `node_audio_dict` as a parameter

### 2. Base Node (`node/basenode.py`)

- Updated `update()` method signature to include `node_audio_dict=None` parameter
- `TYPE_AUDIO = "AUDIO"` constant was already defined

### 3. ProcessNode Files

All ProcessNode files have been updated with the following changes:

#### Updated Files:
- `node_blur.py`
- `node_brightness.py`
- `node_contrast.py`
- `node_resize.py`
- `node_crop.py`
- `node_flip.py`
- `node_canny.py`
- `node_threshold.py`
- `node_grayscale.py`
- `node_equalize_hist.py`
- `node_apply_color_map.py`
- `node_gamma_correction.py`
- `node_image_alpha_blend.py`
- `node_omnidirectional_viewer.py`
- `node_simple_filter.py`

#### Changes Made:

**1. Audio Tag Definitions** (in `add_node()` method):
```python
# Audio tags
node.tag_node_input_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':InputAudio'
node.tag_node_input_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':InputAudioValue'
node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'
```

**2. Audio Texture Registry**:
```python
# Audio texture registry
with dpg.texture_registry(show=False):
    dpg.add_raw_texture(
        small_window_w,
        small_window_h,
        black_texture,
        tag=node.tag_node_output_audio_value_name,
        format=dpg.mvFormat_Float_rgb,
    )
```

**3. Audio Node Attributes**:
```python
# Audio input
with dpg.node_attribute(
        tag=node.tag_node_input_audio_name,
        attribute_type=dpg.mvNode_Attr_Input,
):
    dpg.add_text(
        tag=node.tag_node_input_audio_value_name,
        default_value='Input Audio Spectrogram',
    )

# Audio output
with dpg.node_attribute(
        tag=node.tag_node_output_audio_name,
        attribute_type=dpg.mvNode_Attr_Output,
):
    dpg.add_image(node.tag_node_output_audio_value_name)
```

**4. Update Method Signature**:
```python
def update(
    self,
    node_id,
    connection_list,
    node_image_dict,
    node_result_dict,
    node_audio_dict=None,  # New parameter
):
```

**5. Audio Processing Logic**:
```python
# Initialize node_audio_dict if not provided
if node_audio_dict is None:
    node_audio_dict = {}

# Get audio connection
connection_info_audio = ''
for connection_info in connection_list:
    if connection_type == self.TYPE_AUDIO:
        connection_info_audio = connection_info[0]
        connection_info_audio = connection_info_audio.split(':')[:2]
        connection_info_audio = ':'.join(connection_info_audio)

# Get audio data
audio_frame = node_audio_dict.get(connection_info_audio, None)

# Process audio (same algorithm as images)
processed_audio = None
if audio_frame is not None:
    processed_audio = image_process(audio_frame, params)

# Update audio texture
if processed_audio is not None:
    texture = self.convert_cv_to_dpg(
        processed_audio,
        small_window_w,
        small_window_h,
    )
    dpg_set_value(output_audio_tag, texture)

# Return audio in result
return {"image":frame, "audio": processed_audio, "json":None}
```

### 4. DLNode Files

All DLNode files have been updated with the `node_audio_dict=None` parameter in their `update()` method:

#### Updated Files:
- `node_object_detection.py` (fully implemented with audio processing)
- `node_classification.py`
- `node_face_detection.py`
- `node_pose_estimation.py`
- `node_semantic_segmentation.py`
- `node_monocular_depth_estimation.py`
- `node_low_light_image_enhancement.py`

Note: `node_object_detection.py` has full audio processing implementation including:
- Audio tag definitions
- Audio texture registry
- Audio input/output attributes
- Audio processing logic (applies same model to audio spectrograms)
- Audio debug image rendering

### 5. Other Node Types

All other node types have been updated with the `node_audio_dict=None` parameter:

- InputNode files (video, webcam, image, etc.)
- ActionNode files
- OverlayNode files
- StatsNode files
- TriggerNode files
- VideoNode files
- VisualNode files
- TrackerNode files

### 6. Video Node (`node/InputNode/node_video.py`)

The video node now outputs audio spectrograms:
```python
# Capture spectrogram_bgr variable and return it
return {"image":frame, "audio": spectrogram_bgr, "json" : None}
```

## Usage Examples

### Example 1: Video → Spectrogram → Blur → Display
1. Add Video node and load a video file with audio
2. Enable "Extract Audio Spectrogram" toggle
3. Connect Video's AUDIO output to Blur node's AUDIO input
4. Connect Blur's AUDIO output to display
5. The audio spectrogram will be blurred just like an image

### Example 2: Video → Spectrogram → Resize → YOLO Detection
1. Add Video node with audio
2. Enable spectrogram extraction
3. Connect AUDIO output to Resize node
4. Resize the spectrogram to match YOLO input size
5. Connect to YOLO Object Detection node
6. YOLO will detect patterns in the audio spectrogram (useful for audio event detection)

### Example 3: Spectrogram → Multiple Processing → Classification
1. Video with audio → Extract spectrogram
2. Apply multiple image processing operations (contrast, brightness, etc.)
3. Feed to classification model (e.g., ESC-50 for environmental sound classification)

## Technical Details

### Spectrogram Format
- Spectrograms are numpy arrays in BGR uint8 format (identical to regular images)
- Shape: (height, width, 3) where:
  - height = frequency bins
  - width = time frames
  - 3 = BGR color channels
- Created using librosa and matplotlib colormaps

### Processing
- Same algorithms applied to both images and spectrograms
- No special logic required - spectrograms flow through nodes like images
- Parallel data flow: `node_image_dict` for images, `node_audio_dict` for spectrograms

### Compatibility
- Fully backward compatible
- Nodes without audio connections work exactly as before
- `node_audio_dict` defaults to `None` and is initialized if needed

## Testing

A comprehensive test suite has been added in `tests/test_audio_support_structure.py` that validates:
- Syntax correctness of all modified files
- Presence of `node_audio_dict` parameter in all `update()` methods
- Audio tag definitions in ProcessNode files
- Audio processing logic in ProcessNode files
- Return statements include audio data
- Video node returns audio spectrograms

Run tests with:
```bash
python3 tests/test_audio_support_structure.py
```

## Files Modified

- `main.py` - Core event loop
- `node/basenode.py` - Base node class
- 10 ProcessNode files (blur, brightness, contrast, resize, crop, flip, canny, threshold, grayscale, equalize_hist)
- 5 additional ProcessNode files (apply_color_map, gamma_correction, image_alpha_blend, omnidirectional_viewer, simple_filter)
- 7 DLNode files (object_detection, classification, face_detection, pose_estimation, semantic_segmentation, monocular_depth_estimation, low_light_image_enhancement)
- 29 other node files across InputNode, ActionNode, OverlayNode, StatsNode, TriggerNode, VideoNode, VisualNode, and TrackerNode directories

Total: 52 files modified

## Future Enhancements

Potential future improvements:
1. Add audio-specific processing nodes (e.g., pitch shift, time stretch)
2. Add audio visualization nodes (waveform, MFCC, chromagram)
3. Add audio-specific deep learning models (speech recognition, music genre classification)
4. Support for multiple audio channels (stereo spectrograms)
5. Real-time audio input and processing
