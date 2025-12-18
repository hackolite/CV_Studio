# VideoWriter Node - Format Options

## Overview

The VideoWriter node allows you to export your processing pipeline's output to video files. It supports multiple video formats with different encoding characteristics.

## Format Options

### 1. MP4 (Standard)
- **Extension:** `.mp4`
- **Codec:** MPEG-4 Part 2 (`mp4v`)
- **Encoding Type:** Interframe (temporal compression)
- **Characteristics:**
  - Uses P-frames and B-frames for compression
  - Smaller file sizes due to temporal compression
  - **NOT frame-by-frame** - frames depend on other frames
  - Best for: Final distribution, streaming, general use

### 2. MP4 (I-Frame) ✨ NEW
- **Extension:** `.mp4`
- **Codec:** H.264 (`libx264`) with intraframe-only encoding
- **Encoding Type:** Intraframe only (all I-frames)
- **Characteristics:**
  - **Every frame is independent** (no P or B frames)
  - True frame-by-frame encoding
  - Better compression than MJPEG with modern codec features
  - Larger file sizes than standard MP4
  - Perfect for: Frame-accurate editing, frame-by-frame analysis, professional post-production
- **Technical Details:**
  - Uses `keyint=1` to force all I-frames
  - Uses `scenecut=0` to disable scene detection
  - Re-encodes during audio merge for proper settings

### 3. AVI
- **Extension:** `.avi`
- **Codec:** Motion JPEG (`MJPG`)
- **Encoding Type:** Intraframe only
- **Characteristics:**
  - Each frame is a separate JPEG image
  - True frame-by-frame encoding
  - Large file sizes
  - Universal compatibility
  - Best for: Legacy systems, simple frame-by-frame editing

### 4. MKV
- **Extension:** `.mkv`
- **Codec:** FFV1 (lossless)
- **Encoding Type:** Intraframe only
- **Characteristics:**
  - Lossless video encoding
  - True frame-by-frame encoding
  - Supports metadata tracks (audio and JSON data)
  - Best for: Archival, preservation, metadata-rich recordings

## Frame-by-Frame Encoding

**Question:** Can I do frame-by-frame with the MP4 option of VideoWriter?

**Answer:** Yes! Use the **MP4 (I-Frame)** format for true frame-by-frame encoding with MP4 containers.

### What is Frame-by-Frame Encoding?

Frame-by-frame (intraframe) encoding means that each frame is encoded independently without referencing other frames. This allows:

- **Perfect frame accuracy** for editing and analysis
- **Instant seeking** to any frame
- **No temporal artifacts** from inter-frame compression
- **Reliable frame extraction** and manipulation

### Format Comparison for Frame-by-Frame

| Format | Frame-by-Frame | Codec | File Size | Quality | Use Case |
|--------|----------------|-------|-----------|---------|----------|
| **MP4** | ❌ No | MPEG-4 Part 2 | Small | Good | Distribution |
| **MP4 (I-Frame)** | ✅ Yes | H.264 Intra | Medium | Excellent | Professional editing |
| **AVI** | ✅ Yes | Motion JPEG | Large | Good | Legacy compatibility |
| **MKV** | ✅ Yes | FFV1 | Large | Lossless | Archival |

## Usage

1. **Select Format:**
   - In the VideoWriter node, use the **Format** dropdown
   - Choose your desired format from the list

2. **Start Recording:**
   - Click the **Start** button
   - The node will begin recording frames from the input

3. **Stop Recording:**
   - Click the **Stop** button
   - The video will be encoded and saved to the configured directory

## Output Location

Videos are saved to the directory specified in `setting.json`:
- **Configuration:** `video_writer_directory`
- **File naming:** `YYYYMMDD_HHMMSS.<ext>`

## Audio Support

All formats support audio merging:
- Audio is captured from connected nodes
- Audio quality: 192k AAC bitrate (high quality)
- Audio-video synchronization is automatic
- Audio has priority - video duration adapts to match audio length

## Technical Details

### Background Worker Mode

When FFmpeg is available, the VideoWriter uses a background worker for better performance:
- Non-blocking encoding (UI remains responsive)
- Progress tracking with ETA
- Pause/Resume/Cancel controls
- Efficient queue management

### Legacy Mode

Without FFmpeg, the VideoWriter uses direct OpenCV encoding:
- Synchronous frame writing
- Simpler implementation
- Automatic audio merge at the end

## Tips

- **For editing:** Use MP4 (I-Frame), AVI, or MKV
- **For distribution:** Use standard MP4
- **For archival:** Use MKV with FFV1
- **For compatibility:** Use AVI with MJPEG

## Requirements

- **FFmpeg-python:** Required for audio merging and MP4 (I-Frame) encoding
- **Soundfile:** Required for audio processing
- **OpenCV:** Required for basic video encoding

Install with:
```bash
pip install ffmpeg-python soundfile opencv-python
```

## See Also

- [Video Node Dynamic Play](README_DynamicPlay.md)
- [Main README](../../README.md)
