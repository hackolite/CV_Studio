# Video FPS and Speed Control - README Snippet

## 🎥 Video Node: FPS and Speed Control

The Video Node now includes powerful playback control features that allow you to play videos at a specific frame rate and control playback speed.

### New Features

#### 🎬 Target FPS Control
Set the exact frame rate for video playback, independent of the source video's original FPS.

- **Default**: 24 fps (cinema standard)
- **Range**: 1-120 fps
- **Use case**: Force consistent playback rate across different videos

#### ⚡ Playback Speed Control
Slow down or speed up video playback for analysis or preview.

- **Default**: 1.0x (normal speed)
- **Range**: 0.25x - 4.0x
- **Use cases**:
  - 0.25x-0.5x: Slow motion for detailed analysis
  - 1.0x: Normal playback
  - 2.0x-4.0x: Fast preview mode

### Quick Examples

```
Cinema Standard:     FPS: 24,  Speed: 1.0x  → Standard 24 fps playback
Slow Motion:         FPS: 24,  Speed: 0.25x → 4x slower for analysis
Fast Preview:        FPS: 24,  Speed: 4.0x  → 4x faster for scanning
High FPS Smooth:     FPS: 60,  Speed: 1.0x  → Smooth 60 fps playback
```

### Key Features

✅ **Non-blocking** - Precise frame timing without blocking the update loop
✅ **Synchronized** - Spectrogram automatically follows video playback
✅ **Persistent** - Settings saved between sessions
✅ **Compatible** - Works with existing features (Loop, Skip Rate)
✅ **Backward Compatible** - Old projects automatically use defaults

### Documentation

Complete documentation available:

- **Quick Start**: [VIDEO_FPS_SPEED_QUICK_REF.md](VIDEO_FPS_SPEED_QUICK_REF.md)
- **Visual Guide**: [VIDEO_FPS_SPEED_VISUAL_GUIDE.md](VIDEO_FPS_SPEED_VISUAL_GUIDE.md)
- **Full Documentation**: [VIDEO_FPS_SPEED_INDEX.md](VIDEO_FPS_SPEED_INDEX.md)

### UI Location

The new controls appear in the Video Node between the "Skip Rate" slider and the "Start" button:

```
Video Node
├── Select Movie
├── Video Display
├── Show Spectrogram
├── Spectrogram Display
├── Loop
├── Skip Rate
├── Target FPS     ← NEW
├── Speed          ← NEW
└── Start
```

### Technical Implementation

Frame timing is calculated as:
```python
frame_interval = (1.0 / target_fps) / playback_speed
```

The system only reads a new frame when enough time has passed, ensuring accurate playback timing while maintaining system efficiency.

---

**Version**: 0.0.1  
**Added**: 2025-10-14  
**PR**: [Add Video FPS and Speed Control](link-to-pr)
