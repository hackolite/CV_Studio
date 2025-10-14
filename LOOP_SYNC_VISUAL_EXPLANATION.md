# Spectrogram-Video Loop Synchronization - Visual Explanation

## The Problem (Before Fix)

### Video Playback Timeline:
```
Video plays normally:
Frame:  [0]→[1]→[2]→...→[8998]→[8999]→[9000]→END
                                              ↓ LOOP
                                          Reset to [0]

After loop, video shows:
Frame:  [0]→[1]→[2]→...
```

### Frame Count and Spectrogram Position:
```
BEFORE LOOP:
_frame_count: 9000
video position: 9000
spectrogram column: 12919 (end)

AFTER LOOP (BEFORE FIX):
_frame_count: 9001 ← ❌ NOT RESET! Still incrementing!
video position: 0   ← ✓ Reset correctly
spectrogram column: 12920 ← ❌ WRONG! Should be 0

Result: VIDEO shows frame 0, but SPECTROGRAM shows end position
```

### Visual Representation (Before Fix):
```
Loop happens:
┌────────────────────────────────────────┐
│ VIDEO NODE                             │
│ ┌────────────────┐                     │
│ │   Frame 0      │ ← Shows first frame │
│ │   [IMAGE]      │                     │
│ └────────────────┘                     │
│ ┌────────────────┐                     │
│ │ Spectrogram    │                     │
│ │ ████████████|  │ ← ❌ Shows END!     │
│ │ (window at     │    (column 12680-   │
│ │  end of audio) │     12920)          │
│ └────────────────┘                     │
└────────────────────────────────────────┘
                    DESYNCHRONIZED ❌
```

---

## The Solution (After Fix)

### Code Change:
```python
if loop_flag:
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
    self._frame_count[str(node_id)] = 0  # ← ADDED THIS LINE
    _, frame = video_capture.read()
```

### Frame Count and Spectrogram Position:
```
BEFORE LOOP:
_frame_count: 9000
video position: 9000
spectrogram column: 12919 (end)

AFTER LOOP (AFTER FIX):
_frame_count: 0    ← ✓ Reset to 0!
video position: 0  ← ✓ Reset to 0!
spectrogram column: 0 ← ✓ CORRECT! At start!

Result: Both VIDEO and SPECTROGRAM show beginning
```

### Visual Representation (After Fix):
```
Loop happens:
┌────────────────────────────────────────┐
│ VIDEO NODE                             │
│ ┌────────────────┐                     │
│ │   Frame 0      │ ← Shows first frame │
│ │   [IMAGE]      │                     │
│ └────────────────┘                     │
│ ┌────────────────┐                     │
│ │ Spectrogram    │                     │
│ │ |██████████    │ ← ✓ Shows START!   │
│ │ (window at     │    (column 0-240)   │
│ │  start of      │                     │
│ │  audio)        │                     │
│ └────────────────┘                     │
└────────────────────────────────────────┘
                    SYNCHRONIZED ✓
```

---

## Frame-by-Frame Example

### 5-minute video at 30 FPS (9000 total frames)

#### Normal Playback (No loop):
```
Frame 0:
  _frame_count: 0
  current_time: 0.0s
  spectrogram_col: 0
  window: [0-240]
  indicator: column 0 (left edge)

Frame 900:
  _frame_count: 900
  current_time: 30.0s
  spectrogram_col: 1292
  window: [1172-1412]
  indicator: column 120 (centered)

Frame 8999:
  _frame_count: 8999
  current_time: 299.97s
  spectrogram_col: 12918
  window: [12678-12918]
  indicator: column 240 (right edge)
```

#### Loop Behavior:

**BEFORE FIX:**
```
Frame 9000 (end):
  _frame_count: 9000
  Video reaches end, loops to frame 0

Frame 9001 (after loop):
  _frame_count: 9001 ← ❌ WRONG
  video shows: Frame 0
  current_time: 9001/30 = 300.03s
  spectrogram_col: 12920 ← ❌ OUT OF BOUNDS
  Result: Spectrogram shows invalid position
```

**AFTER FIX:**
```
Frame 9000 (end):
  _frame_count: 9000
  Video reaches end, loops to frame 0
  _frame_count RESET to 0 ← ✓ FIXED

Frame 1 (after loop):
  _frame_count: 1 ← ✓ CORRECT
  video shows: Frame 1
  current_time: 1/30 = 0.033s
  spectrogram_col: 1
  window: [0-240]
  indicator: column 1
  Result: ✓ Perfect sync!
```

---

## Calculation Example

For a video with:
- **FPS**: 30
- **Sample Rate (sr)**: 22050 Hz
- **Hop Length**: 512 samples

### Formula:
```
current_frame = _frame_count
current_time = current_frame / fps
current_sample = current_time * sr
spectrogram_col = current_sample / hop_length
```

### Before Fix (at loop):
```
_frame_count = 9001 (NOT reset)
current_time = 9001 / 30 = 300.03 seconds
current_sample = 300.03 * 22050 = 6615661.5
spectrogram_col = 6615661.5 / 512 ≈ 12921

But spectrogram only has 12919 columns!
Result: ❌ OUT OF BOUNDS or wrong position
```

### After Fix (at loop):
```
_frame_count = 0 (RESET)
current_time = 0 / 30 = 0.0 seconds
current_sample = 0.0 * 22050 = 0
spectrogram_col = 0 / 512 = 0

Result: ✓ Correct position at start!
```

---

## Summary

| Aspect | Before Fix | After Fix |
|--------|-----------|-----------|
| Video position at loop | ✓ Reset to 0 | ✓ Reset to 0 |
| Frame count at loop | ❌ NOT reset | ✓ Reset to 0 |
| Spectrogram position | ❌ End of audio | ✓ Start of audio |
| Sync with video | ❌ Broken | ✓ Perfect |
| Yellow indicator | ❌ Wrong position | ✓ Correct position |
| Scrolling window | ❌ Shows end | ✓ Shows start |

## Code Impact

**Lines changed**: 1  
**Files modified**: 1 (`node/InputNode/node_video.py`)  
**Risk**: Very low (minimal change, well-tested)  
**Impact**: High (fixes desynchronization issue)
