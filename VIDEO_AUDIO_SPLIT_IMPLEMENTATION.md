# Video Node Audio/Video Split Implementation

## Overview

The Video node has been updated to properly split video and audio data into separate output streams:
- **IMAGE output (Output01)**: Video frames pass frame-by-frame as TYPE_IMAGE
- **AUDIO output (Output03)**: Audio chunks pass as TYPE_AUDIO

## Changes Made

### 1. New Method: `_get_audio_chunk_for_frame()`

This method retrieves the appropriate audio chunk for the current video frame:

```python
def _get_audio_chunk_for_frame(self, node_id, frame_number):
    """
    Get the audio chunk data for a specific frame number.
    
    Args:
        node_id: Node identifier
        frame_number: Current frame number
        
    Returns:
        Dictionary with 'data' (numpy array) and 'sample_rate' (int), or None if not available
    """
```

**Output Format:**
```python
{
    'data': numpy.ndarray,      # Audio samples for this chunk
    'sample_rate': int          # Sample rate (e.g., 22050 Hz)
}
```

### 2. Modified `update()` Method

The update method now returns audio chunk data instead of the spectrogram image:

**Before:**
```python
return {"image": frame, "json": None, "audio": spectrogram_bgr}
```

**After:**
```python
# Get audio chunk data for this frame to pass to other audio nodes
audio_chunk_data = None
current_frame_num = self._frame_count.get(str(node_id), 0)
if str(node_id) in self._audio_chunks:
    audio_chunk_data = self._get_audio_chunk_for_frame(str(node_id), current_frame_num)

# Return frame via IMAGE output and audio chunk data via AUDIO output
return {"image": frame, "json": None, "audio": audio_chunk_data}
```

## Usage

### Connecting Video Node to Other Nodes

1. **For Video Processing:**
   - Connect Video node's **IMAGE output (Output01)** to any image processing node
   - Frames will flow frame-by-frame through the connection
   - Example: `Video → Object Detection → Display`

2. **For Audio Processing:**
   - Connect Video node's **AUDIO output (Output03)** to any audio processing node (TYPE_AUDIO)
   - Audio chunks will flow synchronized with video frames
   - Example: `Video → Spectrogram → Display`

3. **For Combined Processing:**
   - Connect both outputs to different processing chains
   - Example:
     ```
     Video (IMAGE) → Object Detection → Overlay
     Video (AUDIO) → Spectrogram → Display
     ```

### Audio Chunk Timing

- Audio chunks are synchronized with video frames
- The chunk index is calculated based on:
  - Current frame number
  - Video FPS (frames per second)
  - Audio step duration (default: 1 second)
- Formula: `chunk_index = int((frame_number / fps) / step_duration)`

## Compatibility

### Nodes that Accept Audio Chunks

Any node with TYPE_AUDIO input that expects the format:
```python
{
    'data': numpy.ndarray,
    'sample_rate': int
}
```

**Examples:**
- Spectrogram node (`node/AudioProcessNode/node_spectrogram.py`)
- Any custom audio processing nodes

### Backward Compatibility

- The internal spectrogram visualization remains unchanged
- The "Show Spectrogram" checkbox still works for internal display
- Existing video playback functionality is not affected

## Technical Details

### Pre-processing

When a video is loaded, the `_preprocess_video()` method:
1. Extracts all video frames
2. Extracts and chunks audio (default: 5-second chunks with 1-second steps)
3. Pre-computes spectrograms for visualization
4. Stores metadata for frame-to-chunk mapping

### Data Storage

- `_video_frames[node_id]`: List of all extracted video frames
- `_audio_chunks[node_id]`: List of audio chunk numpy arrays
- `_spectrogram_chunks[node_id]`: List of pre-computed spectrogram images
- `_chunk_metadata[node_id]`: Metadata including FPS, sample rate, durations

### Memory Considerations

- All frames and chunks are pre-loaded into memory
- For long videos, this may require significant RAM
- Future optimization: Load chunks on-demand

## Testing

Run the integration tests:
```bash
python -m pytest tests/test_video_audio_integration.py -v
```

Expected output:
```
✓ Audio chunk format verification passed
✓ Spectrogram node compatibility verified
✓ Video node output types verified
```

## Example Workflow

1. Load a video file using the "Select Movie" button
2. Video is automatically pre-processed:
   - Frames extracted
   - Audio chunked
   - Spectrograms pre-computed
3. Connect outputs:
   - IMAGE output → Image processing nodes
   - AUDIO output → Audio processing nodes
4. Both streams flow independently but synchronized

## Future Enhancements

- [ ] On-demand chunk loading for memory efficiency
- [ ] Configurable chunk duration and step size via UI
- [ ] Support for real-time video streams
- [ ] Audio resampling options
- [ ] Multiple audio track support
