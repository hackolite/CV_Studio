# Video-Audio Synchronization: Quick Reference

## Process Overview

The CV Studio Video Node synchronizes video playback with audio spectrogram visualization through the following process:

### 1. Split Audio and Video
- **Input:** Video file (e.g., `.mp4`, `.avi`)
- **Process:** Extract audio stream using `ffmpeg` or `librosa`
- **Output:** 
  - Video frames (accessible via OpenCV)
  - Audio samples at 22,050 Hz

### 2. Generate Spectrogram
- **Input:** Audio samples
- **Process:** Compute mel-spectrogram using librosa
- **Parameters:**
  - `n_fft = 2048` (FFT window size)
  - `hop_length = 512` (samples between columns)
  - `n_mels = 128` (frequency bands)
- **Output:** 2D array (128 rows × N columns)

### 3. Play Video Frame-by-Frame
- **Process:** Read video frames sequentially with OpenCV
- **Tracking:** `frame_count` increments for each frame
- **Output:** Current frame number

### 4. Synchronize Frame with Audio
- **Formula:**
  ```python
  time = frame_count / fps
  audio_sample = time * sample_rate
  spectrogram_column = audio_sample / hop_length
  ```
- **Example:** Frame 900 at 30 FPS → 30s → sample 661,500 → column 1,292

### 5. Display Scrolling Window
- **Window size:** 240 columns (1:1 pixel mapping)
- **Position:** Centered at current spectrogram column
- **Indicator:** Yellow vertical line at center
- **Effect:** Smooth scrolling as video plays

## Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `sample_rate` (sr) | 22,050 Hz | Audio sampling frequency |
| `hop_length` | 512 samples | Samples per spectrogram column |
| `n_mels` | 128 bands | Number of frequency bands |
| `fps` | 30 (typical) | Video frames per second |
| `window_width` | 240 columns | Displayed spectrogram width |

## Synchronization Formula

```python
# Convert video frame to spectrogram column
current_frame = self._frame_count.get(str(node_id), 0)
current_time = current_frame / fps
current_sample = int(current_time * sr)
spectrogram_col = int(current_sample / hop_length)
```

## File Location

All implementation is in: `node/InputNode/node_video.py`

- **Audio extraction:** `_prepare_spectrogram()` method (lines 286-402)
- **Frame reading:** `update()` method (lines 464-483)
- **Synchronization:** `update()` method (lines 512-527)
- **Window display:** `update()` method (lines 529-578)

## Performance

- **One-time costs (at load):**
  - Audio extraction: ~1-2 seconds
  - Spectrogram generation: ~1-3 seconds
  
- **Per-frame costs (during playback):**
  - Window extraction: < 1 ms
  - Line drawing: < 1 ms
  - Total: < 5 ms per frame

## Example Timeline

For a 60-second video at 30 FPS:

| Time | Video Frame | Audio Sample | Spectrogram Column |
|------|-------------|--------------|-------------------|
| 0s   | 0           | 0            | 0                 |
| 1s   | 30          | 22,050       | 43                |
| 10s  | 300         | 220,500      | 430               |
| 30s  | 900         | 661,500      | 1,292             |
| 60s  | 1,800       | 1,323,000    | 2,584             |

## Visual Layout

```
┌─────────────────────────┐
│  Video Node             │
├─────────────────────────┤
│  [Select Movie]         │
├─────────────────────────┤
│  ┌───────────────────┐  │
│  │   Video Frame     │  │  ← Current frame
│  └───────────────────┘  │
├─────────────────────────┤
│  ☑ Show Spectrogram     │
│  ┌───────────────────┐  │
│  │   ████|████████   │  │  ← Scrolling window
│  │   ████|████████   │  │     with yellow line
│  │   ████|████████   │  │
│  └───────────────────┘  │
├─────────────────────────┤
│  ☑ Loop                 │
│  Skip Rate: 1           │
│  [Start]                │
└─────────────────────────┘
```

## Key Benefits

✅ **Perfect synchronization** - Mathematical precision  
✅ **Frame-by-frame accuracy** - Every frame has exact audio match  
✅ **Readable display** - No compression, 1:1 pixel mapping  
✅ **Smooth scrolling** - Window slides continuously  
✅ **Loop support** - Resets properly when video loops  
✅ **Efficient** - Heavy computation done once at load time

## Related Documentation

For detailed explanations, see:
- [VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md) - Complete technical guide (English)
- [SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md](SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md) - Complete guide in French
- [VISUAL_SYNC_DIAGRAMS.md](VISUAL_SYNC_DIAGRAMS.md) - Detailed visual diagrams

## Troubleshooting

**Problem:** Spectrogram doesn't match video  
**Solution:** Ensure `hop_length=512` is used consistently

**Problem:** Line indicator doesn't move  
**Solution:** Check that `frame_count` is incrementing

**Problem:** Window doesn't scroll  
**Solution:** Verify window extraction logic uses correct boundaries

**Problem:** Video loops but spectrogram doesn't reset  
**Solution:** Ensure both `frame_count` and video position reset to 0 (fixed in line 470)
