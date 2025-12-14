# VFR to CFR Video Conversion

## Overview

CV Studio now automatically detects and converts Variable Frame Rate (VFR) videos to Constant Frame Rate (CFR) before processing. This ensures perfect audio-video synchronization and prevents timing issues during playback.

## What is VFR vs CFR?

### Variable Frame Rate (VFR)
- Frame rate changes dynamically during the video
- Common in screen recordings, game captures, and some mobile videos
- Can cause synchronization issues with audio
- Example: Video might be 30fps during static scenes but drop to 15fps during motion

### Constant Frame Rate (CFR)
- Fixed frame rate throughout the entire video
- Standard for broadcast and streaming
- Ensures predictable timing for audio-video sync
- Example: Exactly 24, 30, or 60 frames per second throughout

## Why Convert VFR to CFR?

1. **Audio-Video Synchronization**: VFR videos can cause audio to drift out of sync because the frame timing is variable
2. **Predictable Processing**: CFR ensures consistent frame intervals for audio chunking
3. **Compatibility**: Some processing pipelines expect constant frame rates
4. **Quality**: Prevents timing artifacts and glitches during playback

## How It Works

### Automatic Detection

When you load a video in the Video node, CV Studio automatically:

1. **Analyzes the video** using ffprobe to detect VFR
2. **Compares** the reported frame rate (r_frame_rate) with the average frame rate (avg_frame_rate)
3. **Detects VFR** if these rates differ by more than 0.1 fps

### Automatic Conversion

If VFR is detected:

1. **Creates a temporary CFR video** using ffmpeg with high quality settings
2. **Uses the target FPS** from the Video node slider for consistent output
3. **Preserves audio** by copying the audio stream without re-encoding
4. **Uses the converted video** for all processing and playback
5. **Cleans up** the temporary file when the video is changed or node is closed

### Technical Details

The conversion uses ffmpeg with the following settings:

```bash
ffmpeg -i input_vfr.mp4 \
  -vsync cfr \              # Force constant frame rate
  -r 24 \                   # Target frame rate (from slider)
  -c:v libx264 \            # H.264 video codec
  -preset fast \            # Encoding speed preset
  -crf 18 \                 # Quality (18 = visually lossless)
  -c:a copy \               # Copy audio without re-encoding
  output_cfr.mp4
```

**Key Parameters:**
- `-vsync cfr`: Forces constant frame rate by duplicating or dropping frames as needed
- `-r`: Sets the exact output frame rate
- `-crf 18`: High quality (lower = better, 18 is visually lossless)
- `-preset fast`: Balances encoding speed with compression
- `-c:a copy`: Preserves original audio quality

## User Experience

### What You'll See

1. **Loading Video**: When you select a video file
2. **Detection**: Log message indicates if VFR is detected
3. **Conversion**: If VFR, a conversion process runs (may take time for large videos)
4. **Processing**: Once converted, audio preprocessing continues normally
5. **Playback**: Video plays with perfect audio-video synchronization

### Console Messages

```
[Video] Pre-processing video: /path/to/video.mp4
[Video] VFR detected: r_frame_rate=30.00, avg_frame_rate=23.45
[Video] VFR detected, converting to CFR...
[Video] Converting VFR to CFR: /path/to/video.mp4 -> /tmp/video_cfr.mp4
[Video] VFR to CFR conversion successful: /tmp/video_cfr.mp4
[Video] Using CFR video: /tmp/video_cfr.mp4
[Video] Metadata: FPS=24.0, Frames=720
```

Or for CFR videos:

```
[Video] Pre-processing video: /path/to/video.mp4
[Video] CFR detected: frame_rate=24.00
[Video] CFR video detected, no conversion needed
[Video] Metadata: FPS=24.0, Frames=720
```

## Performance Considerations

### Conversion Time

- **Small videos** (< 1 minute): A few seconds
- **Medium videos** (1-10 minutes): 10-60 seconds
- **Large videos** (> 10 minutes): 1+ minutes

The conversion time depends on:
- Video resolution
- Video duration
- CPU performance
- Encoding settings

### Disk Space

Temporary CFR videos are stored in the same directory as the original video:
- Similar file size to the original (due to high quality settings)
- Automatically cleaned up when:
  - You load a different video
  - You close the node
  - The application exits

## Configuration

### Target FPS

The conversion uses the **Target FPS** slider value from the Video node:
- Default: 24 fps
- Range: 1-120 fps
- Recommendation: Match the original video's average frame rate for best quality

### Quality Settings

Currently fixed to ensure high quality:
- CRF 18 (visually lossless)
- H.264 codec
- Fast preset

Future versions may add configurable quality settings in the node editor settings.

## Troubleshooting

### Conversion Fails

If VFR to CFR conversion fails:
1. The original VFR video will be used
2. A warning message will appear in the console
3. Audio-video sync may be imperfect
4. Check that ffmpeg is installed and accessible

**Common causes:**
- ffmpeg not installed or not in PATH
- Corrupted video file
- Insufficient disk space
- Unsupported video codec

### Audio Out of Sync

If audio is still out of sync:
1. Check if the video is truly VFR (console messages)
2. Verify the Target FPS matches the video
3. Try different FPS values
4. Check the original video quality

### Slow Performance

If conversion is too slow:
1. Use lower resolution videos
2. Reduce the Target FPS
3. Convert videos externally before importing
4. Use CFR videos from the start

## Requirements

### Software Dependencies

- **ffmpeg**: Required for VFR detection and conversion
  - Version 4.0 or later recommended
  - Must be in system PATH
  
- **ffprobe**: Usually comes with ffmpeg
  - Used for VFR detection

### Installation

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Add to system PATH

## API Reference

### VideoNode Methods

#### `_detect_vfr(video_path)`
Detects if a video has variable frame rate.

**Parameters:**
- `video_path` (str): Path to the video file

**Returns:**
- `bool`: True if VFR detected, False if CFR or detection fails

**Example:**
```python
node = VideoNode()
is_vfr = node._detect_vfr("/path/to/video.mp4")
if is_vfr:
    print("VFR video detected")
```

#### `_convert_vfr_to_cfr(video_path, target_fps=None)`
Converts a VFR video to CFR.

**Parameters:**
- `video_path` (str): Path to the VFR video file
- `target_fps` (int, optional): Target FPS for CFR conversion. If None, uses the average FPS.

**Returns:**
- `str`: Path to the converted CFR video, or original path if conversion fails

**Example:**
```python
node = VideoNode()
cfr_path = node._convert_vfr_to_cfr("/path/to/vfr_video.mp4", target_fps=24)
print(f"CFR video: {cfr_path}")
```

### Storage

Converted videos are tracked in:
```python
node._converted_videos[node_id] = cfr_video_path
```

And automatically cleaned up via:
```python
node._cleanup_audio_chunks(node_id)
```

## Testing

### Unit Tests

Run the VFR conversion test suite:

```bash
python -m pytest tests/test_vfr_conversion.py -v
```

**Test Coverage:**
- VFR detection with various video types
- CFR conversion with different FPS settings
- Cleanup of temporary files
- Integration with preprocessing flow
- Error handling for missing files

### Manual Testing

1. **Create a test VFR video:**
```bash
# Screen record on a mobile device or use OBS with VFR setting
# Or use ffmpeg to create a test VFR video:
ffmpeg -f lavfi -i testsrc=duration=10:size=640x480:rate=30 \
  -vf "setpts=N/(FRAME_RATE*TB)" \
  -vsync vfr test_vfr.mp4
```

2. **Load in CV Studio:**
   - Open CV Studio
   - Add a Video node
   - Select the VFR video
   - Check console for VFR detection and conversion messages

3. **Verify Synchronization:**
   - Add an Audio Spectrogram node
   - Connect Video → Audio output to Spectrogram
   - Play the video and verify audio matches visual content

## Future Enhancements

Potential improvements for future versions:

1. **Configurable Quality**: Add settings for CRF, preset, and codec
2. **Parallel Conversion**: Convert in background while loading UI
3. **Progress Indicator**: Show conversion progress in the GUI
4. **Cache Management**: Reuse converted videos across sessions
5. **Format Selection**: Support for different output formats (MP4, AVI, MKV)
6. **Batch Processing**: Convert multiple VFR videos at once
7. **Smart Detection**: Use frame timing analysis for better VFR detection

## References

- [FFmpeg VFR to CFR Conversion Guide](https://trac.ffmpeg.org/wiki/ChangingFrameRate)
- [Understanding Video Frame Rates](https://www.adobe.com/creativecloud/video/discover/frame-rate.html)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [CV Studio Audio-Video Sync Documentation](VIDEO_AUDIO_SYNC_INDEX.md)

## Support

If you encounter issues with VFR to CFR conversion:

1. Check the console logs for error messages
2. Verify ffmpeg is installed: `ffmpeg -version`
3. Test with a different video file
4. Report issues on [GitHub Issues](https://github.com/hackolite/CV_Studio/issues)

---

**Last Updated:** 2025-12-14  
**Version:** 1.0.0  
**Author:** CV Studio Development Team
