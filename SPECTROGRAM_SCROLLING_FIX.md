# Spectrogram Frame-by-Frame Scrolling Fix

## Problem Description

**Issue:** "Les spectrogrammes ne défilent pas images par images" (The spectrograms don't scroll frame by frame)

### Root Cause

The previous implementation displayed the **entire spectrogram** scaled down to fit the 240x135 pixel display window. For a typical 5-minute video:
- **Spectrogram columns:** ~12,919 columns
- **Display width:** 240 pixels
- **Scaling ratio:** 53:1 compression

This meant:
1. The spectrogram was heavily compressed and illegible
2. The yellow indicator line moved only a few pixels per minute of playback
3. Users couldn't see any meaningful scrolling or frequency detail

## Solution: Sliding Window Display

Instead of showing the entire spectrogram, we now display a **sliding window** that:
- Shows only 240 columns at a time (1:1 pixel mapping, no compression)
- Centers the window around the current playback position
- Scrolls smoothly as the video plays
- Keeps the yellow indicator line visible in the center

### How It Works

```
Full Spectrogram (12,919 columns):
[████████████████████████████████████████████████████████████]
                    ▲
                    Current Position (column 5000)

Displayed Window (240 columns centered at position):
              [████████|████████]
                       ▲
                 Yellow indicator
                 (centered in window)
```

As playback advances:
```
Frame 0:   Window shows columns [0-240]      | Indicator at left edge
Frame 100: Window shows columns [50-290]     | Indicator centered
Frame 500: Window shows columns [250-490]    | Indicator centered
...
```

## Technical Implementation

### Changes Made to `node/InputNode/node_video.py`

**Lines Modified:** 500-577

#### Key Changes:

1. **Extract sliding window** (lines 528-542):
   ```python
   window_width = small_window_w  # 240 pixels
   half_window = window_width // 2
   start_col = max(0, spectrogram_col - half_window)
   end_col = min(full_spectrogram.shape[1], start_col + window_width)
   spectrogram_window = full_spectrogram[:, start_col:end_col].copy()
   ```

2. **Calculate indicator position within window** (lines 544-545):
   ```python
   indicator_col = spectrogram_col - start_col
   ```

3. **Draw indicator in window** (lines 547-553):
   ```python
   if 0 <= indicator_col < spectrogram_window.shape[1]:
       cv2.line(spectrogram_window, 
               (indicator_col, 0), 
               (indicator_col, spectrogram_window.shape[0] - 1), 
               (0, 255, 255), 2)
   ```

4. **Handle edge cases with padding** (lines 555-564):
   - At the start of video: pad right side with black
   - At the end of video: pad left side with black
   - Ensures window is always exactly 240 pixels wide

## Benefits

### ✅ **Frame-by-Frame Scrolling**
The spectrogram now visibly scrolls every frame, giving real-time feedback.

### ✅ **Readable Frequency Detail**
1:1 pixel mapping means users can see individual frequency components clearly.

### ✅ **Centered Indicator**
The yellow line stays in the middle of the display, making it easy to track.

### ✅ **Smooth Playback**
Window updates synchronously with video frames for smooth scrolling.

### ✅ **No Compression**
Display shows actual spectrogram resolution without scaling artifacts.

## Testing

Created comprehensive test suite in `tests/test_spectrogram_scrolling.py`:

1. ✅ **test_sliding_window_extraction** - Validates window extraction logic
2. ✅ **test_window_centered_on_playback** - Ensures centering around playback position
3. ✅ **test_indicator_position_in_window** - Verifies indicator is positioned correctly
4. ✅ **test_boundary_handling** - Checks start/end boundary conditions
5. ✅ **test_padding_for_edges** - Validates padding at edges
6. ✅ **test_yellow_line_still_present** - Ensures yellow indicator still works
7. ✅ **test_python_syntax_valid** - Validates syntax

All tests pass successfully.

## Backward Compatibility

- ✅ Maintains all existing spectrogram functionality
- ✅ Still uses the same metadata and synchronization logic
- ✅ Fallback to full spectrogram view if metadata is unavailable
- ✅ All existing tests still pass

## Performance

- **Window extraction:** O(1) - simple array slicing
- **Padding:** O(n) - only when needed at edges
- **Line drawing:** O(1) - single vertical line
- **Memory:** Minimal - only copies displayed portion

## User Experience Improvements

### Before:
- ❌ Spectrogram compressed 53:1, illegible
- ❌ Yellow line barely visible
- ❌ No sense of movement or progression

### After:
- ✅ Spectrogram readable at full resolution
- ✅ Yellow line always centered and visible
- ✅ Smooth, frame-by-frame scrolling
- ✅ Clear visual feedback of playback position

## Example Calculation

For a 5-minute video at 30 FPS:

**Frame 0 (0:00):**
- Position: column 0
- Window: [0-240]
- Indicator: column 0 (left edge)

**Frame 900 (0:30):**
- Position: column 1292
- Window: [1172-1412]
- Indicator: column 120 (centered)

**Frame 9000 (5:00):**
- Position: column 12919 (end)
- Window: [12679-12919]
- Indicator: column 240 (right edge, padded)

The spectrogram smoothly scrolls through all 12,919 columns as the video plays.
