# Video Node - Quick Reference Card

## 🎬 FPS & Speed Control Features

### New Controls Added

| Control | Type | Range | Default | Purpose |
|---------|------|-------|---------|---------|
| **Target FPS** | Integer | 1-120 | 24 | Set playback frame rate |
| **Speed** | Float | 0.25x-4.0x | 1.0x | Control playback speed |

### Quick Examples

#### 🎥 Standard Cinema (24 FPS)
```
Target FPS: 24
Speed: 1.0x
→ Standard 24 fps cinema playback
```

#### 🐌 Slow Motion (Quarter Speed)
```
Target FPS: 24
Speed: 0.25x
→ 4x slower for detailed analysis
```

#### 🐌 Slow Motion (Half Speed)
```
Target FPS: 24
Speed: 0.5x
→ 2x slower for comfortable viewing
```

#### ⚡ Fast Forward (2x)
```
Target FPS: 24
Speed: 2.0x
→ 2x faster for quick preview
```

#### ⚡ Fast Forward (4x)
```
Target FPS: 24
Speed: 4.0x
→ 4x faster for rapid scanning
```

#### 🎞️ High Frame Rate Smooth
```
Target FPS: 60
Speed: 1.0x
→ Smooth 60 fps playback
```

#### 🎞️ High FPS Slow Motion
```
Target FPS: 60
Speed: 0.5x
→ Buttery smooth half-speed
```

### Keyboard Shortcuts (Suggested)

While the UI uses sliders, you could imagine these shortcuts:

- **Speed**:
  - `1` = 0.25x
  - `2` = 0.5x
  - `3` = 1.0x (normal)
  - `4` = 2.0x
  - `5` = 4.0x

- **FPS**:
  - `F1` = 24 fps
  - `F2` = 30 fps
  - `F3` = 60 fps

### Frame Timing Formula

```
Frame Interval = (1 / Target FPS) / Speed

Examples:
- 24 FPS @ 1.0x  = 0.042s per frame (42ms)
- 24 FPS @ 0.5x  = 0.083s per frame (83ms)
- 24 FPS @ 2.0x  = 0.021s per frame (21ms)
- 60 FPS @ 1.0x  = 0.017s per frame (17ms)
```

### Common Combinations

#### Analysis Mode
```
Skip Rate: 1 (show all frames)
Target FPS: 24
Speed: 0.25x (quarter speed)
→ Perfect for frame-by-frame analysis
```

#### Preview Mode
```
Skip Rate: 1
Target FPS: 30
Speed: 4.0x (quad speed)
→ Quickly scan through content
```

#### Cinematic Mode
```
Skip Rate: 1
Target FPS: 24
Speed: 1.0x
→ Standard cinema experience
```

#### Selective Analysis
```
Skip Rate: 5 (every 5th frame)
Target FPS: 24
Speed: 0.5x (half speed)
→ Key frames at half speed
```

### Tips & Tricks

1. **Fine Control**: Use Target FPS for coarse adjustment, Speed for fine-tuning

2. **Smooth Slow Motion**: Use higher FPS (60) with slower speed (0.5x) for smooth slow-mo

3. **Quick Scan**: Combine higher speed (4.0x) with skip rate (2-3) for ultra-fast preview

4. **Spectrogram Sync**: The spectrogram automatically follows your playback speed

5. **No Performance Impact**: Only displays frames when needed - efficient processing

### Compatibility

✅ Works with:
- Video looping
- Skip rate feature
- Spectrogram display
- All video formats
- Saved settings

✅ Backward compatible:
- Old projects auto-use defaults (24 fps, 1.0x)

### Troubleshooting

**Video playing too fast?**
- Decrease Speed slider (towards 0.25x)

**Video playing too slow?**
- Increase Speed slider (towards 4.0x)

**Want different frame rate?**
- Adjust Target FPS slider

**Choppy playback?**
- Lower FPS or increase speed
- Check system performance

**Spectrogram out of sync?**
- Should auto-sync with frame count
- Restart video if needed

### Technical Notes

- Frame timing uses `time.time()` for accuracy
- First frame always displays immediately
- Settings persist between sessions
- Zero FPS/speed handled gracefully
- No external dependencies added

---

**Version**: 0.0.1
**Updated**: 2025-10-14
**Feature**: FPS and Speed Control for Video Node
