# Pull Request: Fix Spectrogram Frame-by-Frame Scrolling

## Issue
**"Les spectrogrammes ne défilent pas images par images"**  
(The spectrograms don't scroll frame by frame)

## Problem
The spectrogram display was showing the **entire audio spectrogram compressed** to fit in a 240x135 pixel window, resulting in:
- **53:1 compression ratio** - illegible spectrogram
- **Static display** - no visible scrolling
- **Hidden indicator** - yellow line barely visible or off-screen

## Solution
Implemented a **sliding window approach** that:
- Extracts a 240-column window from the full spectrogram
- Centers the window on the current playback position
- Scrolls the window smoothly as the video plays
- Displays at **1:1 pixel resolution** (no compression)
- Keeps the yellow indicator **always visible and centered**

## Changes Made

### Core Implementation
**File:** `node/InputNode/node_video.py` (lines 500-577)

#### Key Changes:
1. **Sliding Window Extraction**
   - Extract 240 columns centered at current playback position
   - 1:1 pixel mapping for full frequency detail

2. **Position Tracking**
   - Calculate indicator position relative to window
   - Ensure indicator stays visible

3. **Edge Handling**
   - Pad with black pixels at video start/end
   - Adjust window boundaries intelligently

4. **Fallback Support**
   - Show full spectrogram if metadata unavailable
   - Maintains backward compatibility

### Testing
**New Test Files:**
- `tests/test_spectrogram_scrolling.py` - 7 comprehensive tests
- `tests/demo_spectrogram_scrolling.py` - Visual demonstration

**Test Coverage:**
- ✅ Sliding window extraction logic
- ✅ Window centering on playback position
- ✅ Indicator positioning within window
- ✅ Boundary condition handling
- ✅ Edge case padding
- ✅ Yellow line preservation
- ✅ Python syntax validation

### Documentation
**Added Files:**
- `SPECTROGRAM_SCROLLING_FIX.md` - Technical documentation
- `FIX_SUMMARY.md` - Complete summary
- `VISUAL_EXPLANATION.md` - Visual diagrams and examples

## Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| **Compression** | 53:1 | 1:1 (none) |
| **Visibility** | Illegible | Full detail |
| **Scrolling** | Static | Smooth, frame-by-frame |
| **Indicator** | Off-screen | Always centered |
| **Performance** | Good | Same (no degradation) |

## Visual Example

```
Before:
[Full 12,919-column spectrogram compressed to 240 pixels]
- Can't read frequencies
- Yellow line invisible

After (at t=30s):
Window shows columns [1171-1411] at full resolution
         [███████|████████]
                 ▲
          Yellow indicator (centered)
```

## Technical Details

### Algorithm
```python
# Calculate current position
spectrogram_col = int(current_sample / hop_length)

# Extract sliding window
window_width = 240
start = max(0, spectrogram_col - 120)
end = min(total_cols, start + 240)
window = full_spectrogram[:, start:end]

# Draw indicator in window
indicator_pos = spectrogram_col - start
draw_line(window, indicator_pos)
```

### Performance
- **Window extraction:** O(1) - numpy array slicing
- **Memory:** Minimal - only 240 columns copied per frame
- **Frame rate:** No impact - same as before

## Testing Results

```
✓ All 7 new tests pass
✓ All existing tests still pass
✓ Syntax validation passed
✓ Demo script runs successfully
✓ Backward compatibility maintained
```

## Backward Compatibility

✅ **Maintains all existing functionality:**
- Spectrogram generation unchanged
- Synchronization logic preserved
- Metadata usage consistent
- Fallback for missing metadata
- All existing tests pass

## User Benefits

1. **✅ Readable Spectrograms** - See actual frequency detail
2. **✅ Smooth Scrolling** - Frame-by-frame updates
3. **✅ Always Visible** - Indicator stays centered in view
4. **✅ Professional UX** - Matches audio analysis tools
5. **✅ Real-time Feedback** - Visual sync with playback

## Files Changed

```
M  node/InputNode/node_video.py              (77 lines modified)
A  tests/test_spectrogram_scrolling.py       (145 lines)
A  tests/demo_spectrogram_scrolling.py       (116 lines)
A  SPECTROGRAM_SCROLLING_FIX.md              (186 lines)
A  FIX_SUMMARY.md                            (154 lines)
A  VISUAL_EXPLANATION.md                     (150 lines)
```

## Review Checklist

- ✅ **Minimal changes** - Only modified necessary code
- ✅ **Well tested** - 7 new tests + all existing tests pass
- ✅ **Documented** - 3 comprehensive documentation files
- ✅ **Backward compatible** - No breaking changes
- ✅ **Performance neutral** - No degradation
- ✅ **User-focused** - Significantly improves UX

## Next Steps

This PR is ready for review and merging. The implementation:
- Solves the reported issue completely
- Adds no performance overhead
- Maintains full backward compatibility
- Is well-tested and documented
- Follows existing code patterns

---

**Ready for Review** ✓
