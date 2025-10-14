# Before and After: Audio Spectrogram Processing

## Problem (Before)

Audio spectrograms could only connect to AUDIO input pins:

```
┌──────────────────┐
│   Video Node     │
├──────────────────┤
│ [Video Output]   │●─→ To image nodes ✓
│ [Audio Output]   │●─→ To audio nodes only ✗
└──────────────────┘    (Limited processing)

┌──────────────────┐
│   Image Node     │
├──────────────────┤
│ [Select Image]   │
│ [Image Output]   │●─→ To processing nodes
└──────────────────┘
    ↑
    Cannot accept audio spectrograms ✗
```

**Issue**: Audio spectrograms couldn't be fed into image processing pipelines.

## Solution (After)

Audio spectrograms can now connect to the Image node and flow through any image processing pipeline:

```
┌──────────────────┐
│   Video Node     │
├──────────────────┤
│ [Video Output]   │●─→ To image nodes ✓
│                  │
│ [Audio Output]   │●─┐
└──────────────────┘  │
                      │ ✓ Now connectable!
                      │
                      ↓
┌──────────────────┐  │
│   Image Node     │←─┘
├──────────────────┤
│ [Select Image]   │
│ [Audio Input]    │← NEW! Accepts spectrograms
│ [Image Output]   │●─→ To any image processing node
└──────────────────┘
       ↓
┌──────────────────┐
│  Resize/Blur/etc │
├──────────────────┤
│ [Image Input]    │← Treats spectrogram as image
│ [Image Output]   │●─→ Further processing
└──────────────────┘
       ↓
┌──────────────────┐
│  YOLO/CNN/etc    │
├──────────────────┤
│ [Image Input]    │← AI models process audio!
│ [Results]        │
└──────────────────┘
```

## Key Changes to Image Node

### 1. Added Audio Input Pin

```python
# Before: No audio input
with dpg.node_attribute(
    tag=node.tag_node_input01_name,
    attribute_type=dpg.mvNode_Attr_Static,
):
    dpg.add_button(label='Select Image', ...)

# After: Audio input added
with dpg.node_attribute(
    tag=node.tag_node_input01_name,
    attribute_type=dpg.mvNode_Attr_Static,
):
    dpg.add_button(label='Select Image', ...)

# NEW: Audio input
with dpg.node_attribute(
    tag=node.tag_node_input_audio_name,
    attribute_type=dpg.mvNode_Attr_Input,  # ← Input pin
):
    dpg.add_text(default_value='Input Audio Spectrogram')
```

### 2. Updated Processing Logic

```python
# Before: Only file-based images
image_path = self._image_filepath.get(str(node_id), None)
frame = cv2.imread(image_path)

# After: Audio takes priority if connected
audio_frame = None
for connection_info in connection_list:
    if connection_type == self.TYPE_AUDIO:
        audio_frame = node_audio_dict.get(connection_info_audio, None)

if audio_frame is not None:
    frame = audio_frame  # ← Use spectrogram
else:
    frame = cv2.imread(image_path)  # ← Fallback to file
```

### 3. Fixed Return Format

```python
# Before: Tuple (incompatible with main.py expectations)
return frame, None

# After: Dict (matches video node and main.py)
return {"image": frame, "audio": None, "json": None}
```

## Workflow Examples

### Example 1: Audio → Blur → Display

```
Video Node [Audio Output] 
    → Image Node [Audio Input → Image Output]
    → Blur Node [Image Input → Image Output]
    → Display
```

### Example 2: Audio → Resize → Object Detection

```
Video Node [Audio Output]
    → Image Node [Audio Input → Image Output]
    → Resize Node [Image Input → Image Output]
    → YOLO Node [Image Input → Detections]
```

### Example 3: Audio → Multiple Processing

```
Video Node [Audio Output]
    → Image Node [Audio Input → Image Output]
    ├─→ Blur → Display
    ├─→ Edge Detection → Display
    └─→ Classification → Results
```

## Technical Details

### Data Format

Audio spectrograms are already in the same format as images:
- **Type**: numpy.ndarray
- **Shape**: (height, width, 3)
- **Dtype**: uint8
- **Color**: BGR (same as OpenCV images)

This is why NO CHANGES are needed in processing nodes!

### Connection Flow

1. **Video Node** creates spectrogram: `spectrogram_bgr` (numpy array)
2. **main.py** stores in `node_audio_dict[node_id] = spectrogram_bgr`
3. **Image Node** receives connection: `audio_frame = node_audio_dict.get(connection_info_audio)`
4. **Image Node** outputs as image: `return {"image": audio_frame, ...}`
5. **main.py** stores in `node_image_dict[node_id] = audio_frame`
6. **Processing Nodes** receive: `frame = node_image_dict.get(connection_info_src)`
7. **Processing Nodes** process: `cv2.resize(frame, ...)` works identically!

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Audio → Image** | ✗ Not possible | ✓ Seamless |
| **Processing** | Limited to audio nodes | ✓ All image nodes work |
| **Workflows** | Separate audio/image | ✓ Unified pipeline |
| **Changes Required** | N/A | ✓ Only 1 file modified |
| **Backward Compat** | N/A | ✓ 100% compatible |
| **Test Coverage** | N/A | ✓ Comprehensive tests |

## Conclusion

This simple enhancement enables powerful new workflows:
- **Audio Visualization**: Process spectrograms with image filters
- **Audio Analysis**: Apply computer vision models to audio data
- **Creative Effects**: Use image processing on audio representations
- **Unified Pipeline**: Mix audio and video processing seamlessly

All with **minimal code changes** and **full backward compatibility**! 🎉
