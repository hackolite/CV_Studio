# Spectrogram Boundary Cursors Implementation

## Overview
This implementation adds visual boundary cursors (start and end) to the spectrogram display, in addition to the existing middle cursor. These cursors clearly show the exact portion of the spectrogram that is being sent to the classification node for audio analysis.

## Problem Statement
Previously, the spectrogram display showed only a single yellow cursor indicating the current playback position. However, when the windowed spectrogram is sent to the classification node (yolo-cls), it wasn't visually clear what portion of the audio was being analyzed. This lack of precision made it difficult to understand which sounds were being classified.

## Solution
Added two green boundary cursors at the start (left) and end (right) edges of the spectrogram window, making it immediately clear:
1. **What audio window is being analyzed** - The area between the green cursors
2. **Where the current playback position is** - The yellow cursor in the middle
3. **The exact portion sent to classification** - The entire visible window including both green boundaries

## What Was Changed

### File: `node/InputNode/node_video.py`

**Lines Modified:** 743-805

### Key Changes:

1. **Moved cursor drawing after padding** (lines 749-770)
   - Padding is applied first to handle edge cases
   - Indicator position is adjusted when left padding is added
   - Ensures cursors are drawn on the final window that will be sent to classification

2. **Added boundary cursors** (lines 772-794)
   ```python
   # Draw boundary cursors (green) at start and end of the window
   # These show the full window (including padding) being sent to classification
   # Green in BGR is (0, 255, 0)
   start_cursor_col = 0
   end_cursor_col = spectrogram_window.shape[1] - 1
   
   # Draw start boundary cursor (left edge)
   cv2.line(spectrogram_window, (start_cursor_col, 0), ...)
   
   # Draw end boundary cursor (right edge)
   cv2.line(spectrogram_window, (end_cursor_col, 0), ...)
   ```

3. **Kept existing middle cursor** (lines 796-805)
   ```python
   # Draw yellow vertical line at current position within the window (middle cursor)
   if 0 <= indicator_col < spectrogram_window.shape[1]:
       cv2.line(spectrogram_window, (indicator_col, 0), ...)
   ```

## Visual Representation

```
Spectrogram Display:
┌─────────────────────────────────────┐
│ │                 │               │ │  ← Frequency axis (vertical)
│ │                 │               │ │
│ │                 │               │ │
│ G                 Y               G │
│ r                 e               r │
│ e                 l               e │
│ e                 l               e │
│ n                 o               n │
│                   w                 │
└─────────────────────────────────────┘
  ↑                 ↑               ↑
  Start            Current         End
  boundary         position        boundary
  cursor           cursor          cursor
  (Left edge)      (Playback)      (Right edge)

This entire window is sent to classification node
```

## Color Coding

- **Green (0, 255, 0)** - Boundary cursors (start and end)
  - Mark the edges of the window sent to classification
  - Always at positions 0 and width-1 of the display
  
- **Yellow (0, 255, 255)** - Current position cursor (middle)
  - Shows exact playback position
  - Moves from left to right as video plays
  - Position calculated based on video frame, FPS, and audio sample rate

## How It Works

### 1. Window Extraction
```python
window_width = small_window_w  # Display width (e.g., 240 pixels)
half_window = window_width // 2
start_col = max(0, spectrogram_col - half_window)
end_col = min(full_spectrogram.shape[1], start_col + window_width)
```
- Extracts a window centered on the current playback position
- Window width matches the display width for 1:1 pixel mapping

### 2. Padding (Edge Cases)
```python
if spectrogram_window.shape[1] < window_width:
    # Add black padding on left or right
    # Adjust indicator_col if padding on left
```
- At the start of audio: pads on the right
- At the end of audio: pads on the left and adjusts middle cursor position

### 3. Cursor Drawing
```python
# Always draw at edges of final window
start_cursor_col = 0
end_cursor_col = spectrogram_window.shape[1] - 1

# Draw all three cursors
cv2.line(...)  # Start (green)
cv2.line(...)  # End (green)
cv2.line(...)  # Middle (yellow) if within bounds
```

## Benefits

### ✓ **Visual Clarity**
Users can immediately see the exact audio window being analyzed, improving understanding of classification results.

### ✓ **Precise Analysis**
The classification node receives only the windowed portion of the spectrogram, allowing for more precise audio classification of specific sounds rather than the entire audio track.

### ✓ **Better User Feedback**
Three distinct cursors provide comprehensive visual feedback:
- Boundaries show the analysis window
- Middle cursor shows current playback position
- Different colors (green vs yellow) make them easily distinguishable

### ✓ **Consistent with Requirements**
Addresses the French problem statement requesting:
- "un curseur au milieu" (middle cursor) ✓
- "deux autres curseurs sur les côtés" (two side cursors) ✓
- "représente le début et la fin du frame" (represent start and end of frame) ✓
- "pour que le son soit analysé avec plus de précision" (for more precise sound analysis) ✓

## Technical Notes

### Window Width
- Default: 240 pixels (matches `small_window_w`)
- Each pixel column represents `hop_length` audio samples (512 samples)
- Total window duration: `(240 * 512) / 22050 Hz ≈ 5.6 seconds` of audio

### Cursor Thickness
- All cursors use 2-pixel thickness for visibility
- Drawn using OpenCV's `cv2.line()` function

### Performance
- No additional computational overhead (just 2 extra line drawing operations)
- Cursors are drawn on the windowed copy, not the original spectrogram
- Efficient even for real-time playback

### Compatibility
- Works with existing video node infrastructure
- Compatible with all classification models (yolo-cls, ResNet50, etc.)
- No changes to classification node required
- Backward compatible with nodes that don't use spectrogram

## Data Flow

```
Video Node:
├── Load video + extract audio
├── Compute full spectrogram
├── For each frame:
│   ├── Calculate current position in spectrogram
│   ├── Extract window around current position
│   ├── Apply padding if needed
│   ├── Draw boundary cursors (green) at edges
│   ├── Draw middle cursor (yellow) at current position
│   ├── Display in UI
│   └── Send window to classification via 'audio' output
│
└── Classification Node receives windowed spectrogram
    └── Analyzes only the windowed portion for precise results
```

## Testing

Comprehensive tests validate:
1. ✓ Boundary cursors are implemented
2. ✓ Cursor positions are correct (0, width-1, and indicator_col)
3. ✓ Visual distinction (green vs yellow)
4. ✓ Windowed portion is sent to classification
5. ✓ Original spectrogram sync tests still pass
6. ✓ Python syntax is valid

## Example Scenarios

### Scenario 1: Normal Playback (middle of audio)
```
Current frame: 450
Time: 15 seconds (at 30 FPS)
Spectrogram column: ~645
Window: columns 525-765 (240 pixels wide)

Display:
[Green cursor][...spectrogram data...|..Yellow cursor..|...spectrogram data...][Green cursor]
 col 0                                      col 120                          col 239
```

### Scenario 2: Start of Audio
```
Current frame: 30
Time: 1 second
Spectrogram column: 43
Window: columns 0-240 (with padding on right if needed)

Display:
[Green cursor][..Yellow..|...spectrogram data...|......black padding......][Green cursor]
 col 0           col 43                                                     col 239
```

### Scenario 3: End of Audio
```
Current frame: 2670
Time: 89 seconds
Spectrogram column: 3840 (near end)
Window: columns 3720-end, padded on left to 240 pixels

Display:
[Green cursor][...black padding...|...spectrogram data...|.Yellow..][Green cursor]
 col 0                                                      col ~180  col 239
```

## User Experience Impact

When users:
1. Load a video with audio
2. Enable "Show Spectrogram" toggle
3. Play the video

They now see:
- **Two green vertical lines** at the left and right edges
- **One yellow vertical line** at the current playback position
- Clear visual indication of the audio window being analyzed
- Better understanding of which sounds are being classified at each moment

This makes audio classification results more interpretable and helps users understand the temporal precision of the analysis.
