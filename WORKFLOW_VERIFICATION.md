# Audio/Video Workflow Verification

## Overview

This document describes the verification and improvements made to the audio/video workflow to ensure proper synchronization and configuration flow through the pipeline.

## Problem Statement (Original - French)

"Vérifie le workflow, input video, imageConcat audio + image, le fps a utiliser est celui slider input/node_video, le taille de chunk de audio est celui de input/node video, vérifie qu'il n'y a pas d'overlap, le flux audio doit pouvoir etre concaténé de manière a avoir la meme taille que la video d'entrée. c'est lui qui doit faire foi pour la construction de la video en sortie. vérifie la construction du flux video en sortie de imageconcat pour qu'il soit ok"

### Translation

Verify the workflow, input video, imageConcat audio + image:
- The FPS to use is the one from the input/node_video slider
- The audio chunk size is the one from input/node_video
- Verify there's no overlap
- The audio stream must be concatenatable to have the same size as the input video
- It (the audio) must be authoritative for the construction of the output video
- Verify the construction of the video output stream from imageconcat is correct

## Workflow Components

### 1. Video Node (Input)
**File**: `node/InputNode/node_video.py`

**Configuration (UI Sliders)**:
- `Target FPS` (line 208-216): FPS for playback and output (default: 24)
- `Chunk Size` (line 232-244): Audio chunk duration in seconds (default: 2.0)
- `Queue Chunks` (line 246-258): Number of chunks to keep in queue (default: 4)

**Processing**:
- Extracts video metadata (FPS, frame count) - line 398-404
- Extracts and chunks audio - line 406-475
- Uses `chunk_duration = step_duration` (no overlap) - line 446, 934
- Calculates queue sizes using `target_fps` - line 493

**Output** (line 820-834):
```python
{
    'image': frame,           # Video frame
    'audio': audio_chunk,     # Audio chunk with timestamp
    'json': None,             # JSON data (if any)
    'timestamp': float,       # Frame timestamp
    'metadata': {             # NEW: Configuration metadata
        'target_fps': 24,     # From slider (authoritative)
        'chunk_duration': 2.0,
        'step_duration': 2.0,
        'video_fps': 30.0,    # Actual video FPS
        'sample_rate': 44100
    }
}
```

### 2. ImageConcat Node
**File**: `node/VideoNode/node_image_concat.py`

**Processing**:
- Receives data from multiple input slots (images, audio, JSON)
- Concatenates IMAGE slots into single frame - line 528-537
- Collects metadata from source nodes - line 540-553
- Passes through AUDIO slots with timestamps - line 555-586
- Passes through JSON data

**Output** (line 598-602):
```python
{
    'image': concatenated_frame,  # Concatenated video frame
    'audio': audio_chunks,         # Dict of audio chunks by slot
    'json': json_chunks,           # Dict of JSON data by slot
    'metadata': source_metadata    # Passed through from Video node
}
```

### 3. VideoWriter Node
**File**: `node/VideoNode/node_video_writer.py`

**Processing**:
- Receives frame, audio, and metadata from ImageConcat
- Stores source metadata - line 365-375
- Uses `target_fps` from source metadata (not global setting) - line 1053-1058
- Uses `chunk_duration` from source for worker mode - line 1081-1087
- Collects audio samples during recording - line 450-490
- Adapts video duration to match audio when recording stops - line 621-720

**Key Features**:
- **Metadata Storage**: `_source_metadata_dict` stores FPS and chunk settings from Video node
- **Audio Authoritative**: Video duration adapted to match audio duration
- **FPS Priority**: Uses `target_fps` from Video node slider, not global setting

## Key Verification Points

### ✅ 1. FPS from Slider is Used

**Location**: `node_video.py` line 913, 936
```python
target_fps = int(target_fps_value) if target_fps_value is not None else 24
self._preprocess_video(..., target_fps=target_fps)
```

**Verification**: `test_workflow_verification.py::test_fps_from_slider_used`
- Queue size calculation: `192 frames = 4 chunks * 2.0s * 24 fps` ✅
- Different from using video FPS: `240 frames = 4 * 2.0 * 30` ❌

### ✅ 2. Chunk Size from Slider is Used

**Location**: `node_video.py` line 920, 933
```python
chunk_size = float(chunk_size_value) if chunk_size_value is not None else 2.0
self._preprocess_video(..., chunk_duration=chunk_size)
```

**Verification**: `test_workflow_verification.py::test_chunk_size_from_slider_used`
- Chunk samples: `88200 = 2.0s * 44100 Hz` ✅

### ✅ 3. No Audio Overlap

**Location**: `node_video.py` line 934
```python
self._preprocess_video(..., step_duration=chunk_size)
```

**Verification**: `test_workflow_verification.py::test_no_audio_overlap`
- `step_duration = chunk_duration` ensures no gap or overlap ✅
- Chunks cover: `0.0s → 2.0s → 4.0s → 6.0s → 8.0s → 10.0s` ✅

### ✅ 4. Audio Concatenation Matches Video Size

**Location**: `node_video.py` line 443-475
```python
# Chunk audio with sliding window
while (start + chunk_samples) <= len(y):
    audio_chunks.append(chunk)
    start += step_samples

# Handle remaining audio with padding
remaining_samples = len(y) - start
if remaining_samples > 0:
    padded_chunk = np.pad(remaining_chunk, (0, padding_needed), ...)
    audio_chunks.append(padded_chunk)
```

**Verification**: `test_workflow_verification.py::test_audio_concatenation_matches_video_size`
- 10s video → 5 audio chunks of 2.0s = 10.0s total ✅
- Coverage ratio: 100% ✅

### ✅ 5. Audio is Authoritative for Video Construction

**Location**: `node_video_writer.py` line 621-720
```python
def _adapt_video_to_audio_duration(self, video_path, audio_samples, sample_rate, fps, ...):
    audio_duration = total_audio_samples / sample_rate
    required_frames = int(audio_duration * fps)
    frames_to_add = required_frames - video_frame_count
    
    # Duplicate last frame to match audio duration
    for _ in range(frames_to_add):
        out.write(last_frame)
```

**Verification**: `test_workflow_verification.py::test_audio_authoritative_for_video_construction`
- Video: 4.67s (140 frames at 30 fps)
- Audio: 5.00s
- Adaptation: Add 10 frames → 5.00s ✅

### ✅ 6. ImageConcat Video Output Stream is Correct

**Location**: `node_image_concat.py` line 528-602
```python
# Concatenate images
frame, display_frame = create_concat_image(frame_dict, image_slot_count)

# Collect audio and metadata
for slot_idx, slot_info in slot_data_dict.items():
    source_metadata = source_result.get('metadata', {})
    audio_chunks[slot_idx] = audio_chunk
    
# Return all data including metadata
return {
    'image': frame,
    'audio': audio_chunks,
    'json': json_chunks,
    'metadata': source_metadata
}
```

**Verification**: `test_workflow_verification.py::test_imageconcat_video_output_stream`
- IMAGE slots concatenated correctly ✅
- AUDIO slots passed through with timestamps ✅
- Metadata preserved ✅

## Metadata Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Video Node (Input)                                           │
│                                                              │
│ UI Sliders:                                                  │
│  • Target FPS: 24                                            │
│  • Chunk Size: 2.0s                                          │
│  • Queue Chunks: 4                                           │
│                                                              │
│ Output metadata:                                             │
│  {                                                           │
│    'target_fps': 24,        ← From slider (authoritative)   │
│    'chunk_duration': 2.0,   ← From slider                    │
│    'step_duration': 2.0,    ← Equals chunk (no overlap)     │
│    'video_fps': 30.0,       ← Actual video FPS              │
│    'sample_rate': 44100     ← Audio sample rate             │
│  }                                                           │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   │ frame + audio + metadata
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ ImageConcat Node                                             │
│                                                              │
│ • Concatenates IMAGE slots                                  │
│ • Passes through AUDIO slots                                │
│ • Collects metadata from source nodes                       │
│ • Passes metadata downstream                                │
│                                                              │
│ Output: concat_frame + audio + json + metadata              │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   │ concat_frame + audio + metadata
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ VideoWriter Node                                             │
│                                                              │
│ Stores source metadata:                                      │
│  _source_metadata_dict[node] = metadata                     │
│                                                              │
│ When recording starts:                                       │
│  • Uses target_fps from metadata (24), not global (30)      │
│  • Uses chunk_duration from metadata (2.0s)                 │
│                                                              │
│ When recording stops:                                        │
│  • Concatenates audio samples                               │
│  • Adapts video duration to match audio (authoritative)     │
│  • Uses target_fps for frame calculations                   │
│                                                              │
│ Output: video file with synchronized audio                   │
└─────────────────────────────────────────────────────────────┘
```

## Test Coverage

### Test Files Created

1. **test_workflow_verification.py**
   - `test_fps_from_slider_used()` - Verifies FPS from slider is used
   - `test_chunk_size_from_slider_used()` - Verifies chunk size from slider
   - `test_no_audio_overlap()` - Verifies no overlap in chunks
   - `test_audio_concatenation_matches_video_size()` - Verifies audio/video size
   - `test_audio_authoritative_for_video_construction()` - Verifies audio drives video
   - `test_imageconcat_video_output_stream()` - Verifies ImageConcat output
   - `test_complete_workflow_integration()` - End-to-end test

2. **test_metadata_flow.py**
   - `test_video_node_returns_metadata()` - Metadata structure
   - `test_imageconcat_passes_metadata()` - Passthrough verification
   - `test_videowriter_uses_source_metadata()` - FPS selection logic
   - `test_complete_metadata_flow()` - End-to-end metadata flow
   - `test_fps_authoritative_for_output()` - FPS priority verification

3. **test_workflow_integration_simple.py**
   - `test_step_duration_equals_chunk_duration()` - No overlap
   - `test_audio_authoritative_calculation()` - Audio calculations
   - `test_queue_sizing_uses_target_fps()` - Queue sizing
   - `test_metadata_passthrough()` - Metadata flow
   - `test_output_video_fps_matches_target()` - Output FPS verification
   - `test_audio_video_size_matching()` - Size matching

### All Tests Pass ✅

```bash
$ python3 tests/test_workflow_verification.py
✅ ALL WORKFLOW VERIFICATION TESTS PASSED

$ python3 tests/test_metadata_flow.py
✅ ALL METADATA FLOW TESTS PASSED

$ python3 tests/test_workflow_integration_simple.py
✅ ALL INTEGRATION TESTS PASSED
```

## Code Quality

### Changes Summary

- **Lines Modified**: ~50
- **Lines Added**: ~35 (metadata flow)
- **Tests Added**: 20+ new tests
- **Breaking Changes**: None (backward compatible)

### Backward Compatibility

✅ All changes are backward compatible:
- If no metadata is present, falls back to global settings
- Existing recordings continue to work
- No changes to external APIs

### Performance Impact

✅ Minimal performance impact:
- Metadata copying is lightweight (dict copy)
- No additional file I/O
- No changes to video/audio processing

## Conclusion

All requirements from the problem statement have been verified and implemented:

1. ✅ **FPS from slider**: VideoWriter uses target_fps from Video node, not global setting
2. ✅ **Chunk size from slider**: Audio chunks use chunk_duration from Video node
3. ✅ **No overlap**: step_duration = chunk_duration ensures no gaps or overlaps
4. ✅ **Audio matches video size**: Concatenated audio covers full video duration
5. ✅ **Audio is authoritative**: Video duration adapted to match audio
6. ✅ **ImageConcat output correct**: Video stream properly constructed and metadata passed through

The workflow now correctly flows configuration from the Video node slider settings through ImageConcat to VideoWriter, ensuring consistent FPS and chunk settings throughout the pipeline.
