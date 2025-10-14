# Spectrogram-Video Loop Synchronization Fix

## Problem Statement
"Je veux que le spectrogramme soit celui correspondant a la frame affichée dans le node video de façon a faire un défilement"

Translation: "I want the spectrogram to be the one corresponding to the frame displayed in the video node in order to make scrolling"

## Issue Description

When a video loops back to the beginning (when loop mode is enabled), the spectrogram was not properly synchronized with the displayed video frame. This caused the spectrogram scrolling indicator to continue advancing instead of resetting to the beginning of the audio.

### Root Cause

In the `update()` method of `VideoNode` (file: `node/InputNode/node_video.py`), when the video reached the end and loop mode was enabled:

1. The video position was reset to frame 0: `video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)` (line 469)
2. **BUT** the `_frame_count` was NOT reset to 0

This caused a desynchronization:
- The **video player** showed frame 0 (start of video)
- The **spectrogram** calculated position based on the old frame count (e.g., frame 9000 if the video just looped)
- Result: The yellow indicator line and scrolling window were out of sync with the actual displayed video frame

## Solution

Added a single line to reset the frame counter when the video loops:

```python
if loop_flag:
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
    self._frame_count[str(node_id)] = 0  # ← Added this line
    _, frame = video_capture.read()
```

### How It Works

Now when the video loops:
1. Video position is reset to 0 ✓
2. Frame count is reset to 0 ✓
3. A new frame is read from position 0 ✓
4. Later in the code, when calculating spectrogram position:
   - `current_frame = self._frame_count.get(str(node_id), 0)` returns 0
   - `current_time = 0 / fps = 0.0` seconds
   - `spectrogram_col = 0` (start of spectrogram)
   - The scrolling window shows columns [0-240] with indicator at the left edge ✓

## Technical Details

### File Modified
- `node/InputNode/node_video.py` (line 470)

### Change
```diff
                 if not ret:
                     if loop_flag:
                         video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
+                        self._frame_count[str(node_id)] = 0
                         _, frame = video_capture.read()
```

### Testing

Created new test file `tests/test_video_loop_frame_count.py` with two tests:

1. **test_frame_count_reset_on_loop()** - Verifies that frame count is reset when video loops
2. **test_frame_count_and_position_reset_together()** - Ensures both resets happen in the same code block

Both tests pass ✓

## Impact

### Before Fix
- ❌ Spectrogram continued scrolling when video looped
- ❌ Yellow indicator line was in wrong position after loop
- ❌ Spectrogram window showed incorrect time range after loop

### After Fix
- ✅ Spectrogram resets to start when video loops
- ✅ Yellow indicator line correctly shows position at start
- ✅ Spectrogram scrolling window shows correct time range (0-240 columns)
- ✅ Perfect synchronization between video frame and spectrogram display

## Backward Compatibility

- ✅ No breaking changes
- ✅ Only affects loop behavior
- ✅ Non-looping videos unaffected
- ✅ All existing functionality preserved

## Verification

The fix can be verified by:
1. Loading a video with audio in the Video node
2. Enabling spectrogram display
3. Enabling loop mode
4. Playing the video until it reaches the end and loops
5. Observing that the spectrogram resets to the beginning (yellow line at left edge, window shows columns 0-240)

Expected behavior: The spectrogram should show the same position as the video frame throughout playback, including when the video loops back to the start.
