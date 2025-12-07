# VideoWriter Audio+Video Merge Implementation

## Overview

This implementation adds support for merging audio and video in the VideoWriter node for MP4, AVI, and MKV formats. The VideoWriter node can now properly receive audio data from the ImageConcat node (or any other node that outputs audio) and merge it with video frames using ffmpeg.

## Problem Statement

The original request (in French) was:
> "Vérifier qu'après concat utilisant audio + video, le node suivant qui est videowriter est capable de fusionner audio et image pour mp4, AVI ou mkv."

Translation:
> "Verify that after concatenation using audio + video, the next node which is VideoWriter is capable of merging audio and image for MP4, AVI or MKV."

## Architecture

### Data Flow

```
┌──────────────┐
│  Video Node  │
│ (with audio) │
└──────┬───────┘
       │
       │ IMAGE + AUDIO
       │
       ▼
┌──────────────┐
│ ImageConcat  │  ← Can concatenate multiple audio+video streams
│    Node      │
└──────┬───────┘
       │
       │ IMAGE + AUDIO (merged)
       │
       ▼
┌──────────────┐
│ VideoWriter  │  ← Now merges audio and video using ffmpeg
│    Node      │
└──────────────┘
```

### Implementation Details

#### 1. Audio Sample Collection

During recording, the VideoWriter node collects audio samples from the input:

- **Single audio chunk** (from Video node):
  ```python
  {'data': numpy_array, 'sample_rate': 22050}
  ```

- **Multi-slot audio** (from ImageConcat node):
  ```python
  {
    0: {'data': numpy_array, 'sample_rate': 22050},
    1: {'data': numpy_array, 'sample_rate': 22050},
    ...
  }
  ```

Audio samples are stored in `_audio_samples_dict[tag_node_name]` during recording.

#### 2. Temporary Video File

When recording starts, the VideoWriter creates a temporary video file (e.g., `video_temp.mp4`) instead of the final file. This allows us to:
1. Write video frames using OpenCV's VideoWriter
2. Merge the temporary video with audio using ffmpeg when recording stops
3. Create the final output file with both audio and video

#### 3. FFmpeg Merge Process

When recording stops, if audio samples were collected:

1. **Concatenate audio samples** into a single numpy array
2. **Write audio to temporary WAV file** using soundfile
3. **Merge video and audio** using ffmpeg-python:
   ```python
   ffmpeg.output(
       video_input,
       audio_input,
       output_path,
       vcodec='copy',      # Copy video codec (no re-encoding)
       acodec='aac',       # Use AAC for audio (widely compatible)
       shortest=None       # Use shortest stream duration
   )
   ```
4. **Clean up temporary files**

#### 4. Format Support

All three requested formats are supported:

- **MP4**: Uses `mp4v` codec for video, AAC for audio
- **AVI**: Uses `MJPG` codec for video, AAC for audio
- **MKV**: Uses `FFV1` lossless codec for video, AAC for audio

## Code Changes

### Modified Files

1. **`node/VideoNode/node_video_writer.py`**
   - Added `soundfile` import for audio file I/O
   - Added `_audio_samples_dict` to store audio samples during recording
   - Added `_recording_metadata_dict` to store recording metadata
   - Modified `update()` to collect audio samples
   - Added `_merge_audio_video_ffmpeg()` method to merge audio and video
   - Modified `_recording_button()` to:
     - Create temporary video files
     - Initialize audio collection
     - Merge audio and video when stopping

### New Files

1. **`tests/test_videowriter_audio_merge.py`**
   - Tests ffmpeg availability
   - Tests audio/video merge functionality
   - Tests audio sample collection (single chunk)
   - Tests audio sample collection (multi-slot)
   - Tests recording metadata initialization
   - Tests all supported formats (MP4, AVI, MKV)

## Dependencies

The implementation requires:
- `ffmpeg-python`: Python bindings for ffmpeg
- `soundfile`: For writing audio to WAV files
- `ffmpeg`: The actual ffmpeg binary (system dependency)

All dependencies are already listed in `requirements.txt`.

## Usage

1. **Create a workflow**:
   - Add a Video node (or other video source with audio)
   - Optionally add an ImageConcat node to combine multiple streams
   - Connect to VideoWriter node

2. **Configure VideoWriter**:
   - Select format (MP4, AVI, or MKV) from the dropdown
   - Click "Start" to begin recording

3. **Recording**:
   - Video frames and audio samples are collected
   - Audio is automatically synchronized with video

4. **Stop recording**:
   - Click "Stop"
   - Audio and video are merged using ffmpeg
   - Final file is saved with both audio and video

## Testing

Run the tests:
```bash
cd /home/runner/work/CV_Studio/CV_Studio
python -m pytest tests/test_videowriter_audio_merge.py -v
```

All tests pass, validating:
- ✅ FFmpeg availability
- ✅ Audio/video merge functionality
- ✅ Audio sample collection from single source
- ✅ Audio sample collection from multiple sources (concat)
- ✅ Recording metadata initialization
- ✅ Support for MP4, AVI, and MKV formats

## Backwards Compatibility

The implementation is fully backwards compatible:
- If no audio data is provided, VideoWriter works as before (video only)
- If ffmpeg is not available, a warning is printed but video recording still works
- Existing workflows are not affected

## Future Enhancements

Potential improvements for the future:
1. Support for separate audio tracks (currently multi-slot audio is merged)
2. Audio codec selection (currently defaults to AAC)
3. Audio quality/bitrate settings
4. Progress indicator during ffmpeg merge
5. Support for different audio formats (currently uses WAV as intermediate)
