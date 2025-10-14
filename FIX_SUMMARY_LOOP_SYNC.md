# Fix Summary: Spectrogram-Video Frame Synchronization on Loop

## Problem Statement (French)
"Je veux que le spectrogramme soit celui correspondant a la frame affichée dans le node video de façon a faire un défilement"

**Translation**: "I want the spectrogram to be the one corresponding to the frame displayed in the video node in order to make scrolling"

## Issue
When a video with spectrogram display was set to loop mode, the spectrogram was not synchronized with the displayed video frame after the loop. The spectrogram continued scrolling instead of resetting to the beginning.

## Root Cause
When the video reached the end and looped back to frame 0:
- Video position was reset: ✓
- Frame counter `_frame_count` was NOT reset: ✗

This caused the spectrogram position calculation to use an incorrect frame number, resulting in desynchronization.

## Solution
Added **one line** to reset the frame counter when the video loops:

```python
if loop_flag:
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
    self._frame_count[str(node_id)] = 0  # ← Added this line
    _, frame = video_capture.read()
```

### File Modified
- `node/InputNode/node_video.py` (line 470)

### Impact
- **Lines changed**: 1
- **Risk**: Minimal (surgical change)
- **Effect**: Fixes spectrogram synchronization on video loop

## Testing
Created comprehensive test suite:
- `tests/test_video_loop_frame_count.py` - Validates frame count reset behavior
- All existing tests continue to pass

## Documentation
1. **SPECTROGRAM_VIDEO_LOOP_FIX.md** - Detailed technical explanation
2. **LOOP_SYNC_VISUAL_EXPLANATION.md** - Visual diagrams and examples

## Result
✅ Spectrogram now properly synchronizes with video frames  
✅ When video loops, spectrogram resets to start  
✅ Yellow indicator line shows correct position  
✅ Scrolling window displays correct time range  
✅ Perfect frame-by-frame correspondence maintained

## Verification
To verify the fix:
1. Load a video with audio
2. Enable spectrogram display
3. Enable loop mode
4. Play until video loops
5. Observe: Spectrogram resets to beginning, staying in sync with video

## Example Behavior

### Before Fix
```
Video loops → Shows frame 0
Spectrogram → Still at end position (column ~12919)
Result: ❌ DESYNCHRONIZED
```

### After Fix
```
Video loops → Shows frame 0
Spectrogram → Resets to start (column 0)
Result: ✓ SYNCHRONIZED
```

## Backward Compatibility
- ✅ No breaking changes
- ✅ Only affects loop behavior
- ✅ Non-looping playback unchanged
- ✅ All existing features preserved

---

**Status**: ✅ Complete and tested  
**Commit**: defebd2  
**Branch**: copilot/sync-spectrogram-with-video-frame
