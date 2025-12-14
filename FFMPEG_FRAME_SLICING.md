# FFmpeg Frame Slicing Implementation

## Overview

This document describes the implementation of ffmpeg-based frame extraction to replace OpenCV's `cv2.VideoCapture.read()` in the VideoNode.

**Date**: 2025-12-14  
**Status**: ✅ Complete  
**Issue**: "le slice des images plutot avec ffmpeg qu'avec opencv"  

---

## Problem Statement

The original implementation used OpenCV's `cv2.VideoCapture` to read video frames:
```python
video_capture = cv2.VideoCapture(video_path)
ret, frame = video_capture.read()
```

The request was to use ffmpeg for frame extraction instead of OpenCV.

---

## Solution

### New Architecture

The new implementation uses ffmpeg as a subprocess to stream raw video frames:

1. **Frame Extraction**: ffmpeg outputs raw RGB24 frames to stdout
2. **Metadata Extraction**: ffprobe provides video metadata (width, height, fps, frame_count)
3. **Color Conversion**: RGB frames are converted to BGR for OpenCV compatibility
4. **Process Management**: Proper lifecycle management of ffmpeg subprocess

### Key Components

#### 1. Video Info Extraction (`_get_video_info`)

```python
def _get_video_info(self, video_path):
    """Extract video metadata using ffprobe"""
    # Returns: {'width': int, 'height': int, 'fps': float, 'frame_count': int}
```

Uses ffprobe to extract:
- Video dimensions (width, height)
- Frame rate (parsed from r_frame_rate)
- Frame count (nb_frames)

#### 2. FFmpeg Reader Start (`_start_ffmpeg_reader`)

```python
def _start_ffmpeg_reader(self, video_path):
    """Start an ffmpeg process to read video frames"""
    # Returns: subprocess.Popen object
```

Starts ffmpeg with:
- `-f rawvideo`: Output raw video data
- `-pix_fmt rgb24`: RGB 24-bit pixel format
- `-fps_mode passthrough`: Preserve original frame rate
- Output to stdout (`-`)

#### 3. Frame Reading (`_read_frame_from_ffmpeg`)

```python
def _read_frame_from_ffmpeg(self, process, width, height):
    """Read a single frame from ffmpeg stdout pipe"""
    # Returns: (success: bool, frame: numpy.ndarray)
```

Process:
1. Calculate frame size: `width × height × 3` bytes (RGB24)
2. Read raw bytes from stdout
3. Convert to numpy array and reshape
4. Convert RGB to BGR using `cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)`

#### 4. Process Cleanup (`_stop_ffmpeg_reader`)

```python
def _stop_ffmpeg_reader(self, process):
    """Stop an ffmpeg reader process gracefully"""
```

Graceful shutdown:
1. Close stdout pipe
2. Send SIGTERM
3. Wait with 5-second timeout
4. Force kill if timeout expires

#### 5. Resource Cleanup (`_cleanup_video_resources`)

```python
def _cleanup_video_resources(self, node_id):
    """Clean up video resources for a node"""
```

Centralized cleanup to avoid code duplication:
- Stops ffmpeg process
- Removes entries from tracking dictionaries

---

## Implementation Changes

### Before (OpenCV)
```python
# Initialization
self._video_capture[str(node_id)] = cv2.VideoCapture(movie_path)

# Frame reading
ret, frame = video_capture.read()

# Seeking/looping
video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

# Cleanup
video_capture.release()
```

### After (FFmpeg)
```python
# Initialization
self._video_capture[str(node_id)] = self._start_ffmpeg_reader(movie_path)
self._video_info[str(node_id)] = self._get_video_info(movie_path)

# Frame reading
width = video_info['width']
height = video_info['height']
ret, frame = self._read_frame_from_ffmpeg(video_capture, width, height)

# Seeking/looping (restart process)
self._stop_ffmpeg_reader(video_capture)
video_capture = self._start_ffmpeg_reader(movie_path)

# Cleanup
self._cleanup_video_resources(str(node_id))
```

---

## Benefits

1. **Native FFmpeg Processing**: Video frames are extracted using ffmpeg's native decoding
2. **No OpenCV Dependency for Frame Reading**: OpenCV is only used for color conversion
3. **Consistent Metadata**: ffprobe provides reliable video information
4. **Better VFR Support**: Works alongside existing VFR detection and conversion
5. **Clean Architecture**: Centralized resource management and error handling

---

## Compatibility

### Maintained
- ✅ Audio synchronization logic (unchanged)
- ✅ Frame timing and playback speed control
- ✅ Video looping functionality
- ✅ Frame skipping (skip_rate)
- ✅ Queue management
- ✅ Metadata flow through pipeline
- ✅ Color format (BGR) expected by downstream nodes

### Changed
- Frame reading mechanism (OpenCV → FFmpeg)
- Video metadata extraction (prefers ffprobe over OpenCV)
- Loop implementation (restart process instead of seeking)

---

## Error Handling

The implementation includes robust error handling:

1. **ffprobe failures**: Falls back to OpenCV for metadata
2. **ffmpeg startup failures**: Returns None and logs error
3. **Frame read failures**: Returns (False, None) to signal EOF
4. **Process termination**: Handles timeout with forced kill
5. **Resource cleanup**: Safe cleanup even if process is already dead

---

## Testing

### Manual Testing
Created test video with ffmpeg and verified:
- ✅ 30 frames read successfully from test video
- ✅ Frame dimensions match expected (320x240)
- ✅ Frame data type correct (uint8)
- ✅ Graceful process shutdown

### Integration Testing
- ✅ Structure tests pass
- ✅ Syntax validation passes
- ✅ Security scan passes (0 vulnerabilities)
- ✅ Code review feedback addressed

---

## Performance Considerations

1. **Buffering**: Uses large buffer (10^8 bytes) for efficient reading
2. **Process Overhead**: Subprocess management adds minimal overhead
3. **Frame Format**: Raw RGB24 format is efficient for reading
4. **Color Conversion**: Single cv2.cvtColor call per frame

---

## Future Improvements

Potential enhancements (not required for current implementation):

1. Frame seeking support (would require multiple ffmpeg processes or complex pipe management)
2. Hardware acceleration support (add `-hwaccel` flags)
3. Frame rate control in ffmpeg (add `-r` flag)
4. Parallel frame extraction for better performance

---

## References

- Original Issue: "le slice des images plutot avec ffmpeg qu'avec opencv"
- Related: VFR_AUDIO_SYNC_FIX.md (VFR detection and conversion)
- Related: FPS_BASED_AUDIO_CHUNKING.md (audio synchronization)
