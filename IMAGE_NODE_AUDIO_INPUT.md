# Image Node Audio Input Support

## Overview

The Image node now accepts audio spectrograms as inputs and treats them as regular images. This enables seamless processing of audio spectrograms through the same image processing pipeline without any special handling.

## Key Changes

### Image Node (`node/InputNode/node_image.py`)

1. **Audio Input Pin Added**
   - New audio input attribute accepts audio spectrogram connections
   - Displayed as "Input Audio Spectrogram" text input pin

2. **Processing Logic**
   - When an audio spectrogram is connected to the audio input, it is treated as a regular image
   - Audio spectrograms have priority over file-based images when connected
   - If no audio is connected, the node works exactly as before (loads images from files)

3. **Return Format Updated**
   - Changed from tuple `(frame, None)` to dict `{"image": frame, "audio": None, "json": None}`
   - This matches the format used by other nodes (e.g., video node) for consistency

## Workflow Example

```
Video Node → Audio Spectrogram Output
                    ↓
             Image Node (Audio Input)
                    ↓
             Resize/Blur/etc. (Image Input)
```

The audio spectrogram flows through the Image node and is then processed by standard image processing nodes without any special handling.

## Benefits

### User Experience
- **Seamless Integration**: Audio spectrograms can be processed like regular images
- **No Special Logic**: All existing image processing nodes work with spectrograms automatically
- **Flexible Workflows**: Can mix and match audio and image inputs

### Technical
- **Backward Compatible**: Existing projects work without modification
- **Consistent Interface**: Same pattern as other input nodes
- **Minimal Changes**: Only the Image node needed modification

## Usage

1. Connect a video node's audio output to the Image node's audio input
2. The Image node will display the audio spectrogram
3. Connect the Image node's output to any image processing node
4. The spectrogram is processed like a regular image

## Implementation Details

### Audio Input Priority
When both a file and an audio connection are available:
- **Audio connected**: Uses the audio spectrogram as the image
- **No audio**: Falls back to the selected image file

### Connection Handling
```python
# Check for audio input connection
audio_frame = None
for connection_info in connection_list:
    connection_type = connection_info.split(':')[2]
    if connection_type == self.TYPE_AUDIO:
        # Extract audio from node_audio_dict
        connection_info_audio = connection_info.split(':')[:2]
        connection_info_audio = ':'.join(connection_info_audio)
        audio_frame = node_audio_dict.get(connection_info_audio, None)
        break

# Use audio if available, otherwise use file
if audio_frame is not None:
    frame = audio_frame
else:
    # Load from file as usual
    ...
```

## Files Modified

- `node/InputNode/node_image.py`: Added audio input pin and processing logic
- `tests/test_image_node_audio_input.py`: Tests for audio input functionality
- `tests/test_image_node_integration.py`: Integration tests

## Compatibility

- **Fully backward compatible**: Existing image nodes work without changes
- **No breaking changes**: All existing functionality preserved
- **Works with existing nodes**: All ProcessNode and DLNode files already support audio

## Testing

Run the tests to verify functionality:
```bash
python tests/test_image_node_audio_input.py
python tests/test_image_node_integration.py
```

Both tests should pass, confirming:
- Audio input structure is correct
- Connection logic works properly
- Backward compatibility is maintained
- Return format is compatible with main.py
