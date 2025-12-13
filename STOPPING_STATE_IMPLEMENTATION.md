# Video Writer Stopping State Implementation

## Overview
This document describes the implementation of the stopping state mechanism for the VideoWriter node to properly synchronize audio and video when recording stops.

## Problem Statement
The original French requirement translated to:
> "When I stop recording, we must stop populating the audio queue, count the number of audio elements, calculate duration_of_audio * fps * number_of_audio_elements, which gives the number of frames to wait. When we reach the correct number of concat images, we can stop the image queues. Then start creating the audio track, then create the video from images alone respecting the fps, and mix the two if AVI or mpeg4."

## Root Cause
The legacy mode VideoWriter had a synchronization issue:
1. When user pressed Stop, it immediately stopped both audio and video collection
2. If video frames stopped arriving before audio finished, this caused desynchronization
3. The video file would be shorter than the audio duration

## Solution Design

### Architecture
The solution implements a "stopping state" mechanism that:
1. Immediately stops audio collection when user presses Stop
2. Calculates required video frames based on collected audio duration
3. Continues collecting video frames until requirement is met
4. Then finalizes the recording

### Key Components

#### 1. Stopping State Dictionary
```python
_stopping_state_dict = {}  # {node: {'stopping': bool, 'required_frames': int, 'audio_chunks': int}}
```
Tracks which nodes are in stopping state and their target frame count.

#### 2. Frame Calculation Formula
```python
required_frames = int(audio_duration * fps)
```
Where:
- `audio_duration = total_audio_samples / sample_rate`
- `fps` = frames per second from recording metadata
- This ensures video has enough frames to cover the audio duration

#### 3. Modified Stop Flow

**Before (Immediate Stop):**
```
User clicks Stop → Release VideoWriter → Merge audio/video
```

**After (Gradual Stop with Synchronization):**
```
User clicks Stop 
  → Count audio samples collected
  → Calculate required frames
  → If need more frames:
      → Enter stopping state
      → Continue collecting frames (but no more audio)
      → When target reached → Release VideoWriter → Merge
  → If already have enough:
      → Release VideoWriter immediately → Merge
```

### Implementation Details

#### Modified Methods

1. **`_recording_button()` - Stop Logic**
   - Calculates total audio samples across all slots
   - Computes audio duration and required video frames
   - Enters stopping state if more frames needed
   - Returns early to prevent premature finalization

2. **`update()` - Frame Collection**
   - Checks if in stopping state
   - Stops collecting audio: `if audio_data is not None and tag_node_name in self._audio_samples_dict and not is_stopping:`
   - Continues collecting frames and checks if target reached
   - Triggers finalization when target is met

3. **Cleanup Methods**
   - Added `_stopping_state_dict.pop()` to cleanup sections
   - Ensures state is cleared in both normal and error paths

### Safety Features

1. **Division by Zero Protection**
   ```python
   if sample_rate <= 0:
       logger.warning(f"[VideoWriter] Invalid sample rate {sample_rate}, using default 22050 Hz")
       sample_rate = 22050
   ```

2. **FPS Validation**
   ```python
   if fps <= 0:
       logger.warning(f"[VideoWriter] Invalid fps {fps}, using default 30")
       fps = 30
   ```

3. **Fallback to Immediate Stop**
   - If already have enough frames, stops immediately
   - Prevents unnecessary waiting

## Testing

### Test Coverage
Created `test_videowriter_stopping_state.py` with 7 test cases:

1. **test_stopping_state_dict_exists** - Verifies the class variable exists
2. **test_stopping_state_calculation** - Tests frame calculation logic
3. **test_audio_not_collected_in_stopping_state** - Verifies audio stops
4. **test_stopping_state_cleanup** - Checks cleanup implementation
5. **test_frame_count_comparison** - Tests comparison logic
6. **test_audio_duration_calculation** - Validates duration math
7. **test_required_frames_calculation** - Tests frame calculation

All tests pass ✅

### Integration Tests
Existing workflow tests continue to pass:
- `test_workflow_integration_simple.py` - All 6 tests pass ✅

## Scope and Limitations

### In Scope
- **Legacy Mode** (direct cv2.VideoWriter usage)
  - This is where the synchronization issue occurred
  - Full stopping state mechanism implemented

### Out of Scope
- **Background Worker Mode**
  - Already handles audio/video synchronization correctly
  - Queues both frame and audio together
  - No changes needed

## Examples

### Example 1: Recording with 3 seconds of audio at 30 fps
```
1. User starts recording
2. Collects 3 seconds of audio (66,150 samples at 22050 Hz)
3. Collects 50 frames of video
4. User clicks Stop

Calculation:
- Audio duration: 66150 / 22050 = 3.0 seconds
- Required frames: 3.0 * 30 = 90 frames
- Current frames: 50
- Need: 40 more frames

Action:
- Stop collecting audio
- Continue collecting 40 more frames
- When frame 90 arrives → Finalize and merge
```

### Example 2: Already have enough frames
```
1. User starts recording
2. Collects 3 seconds of audio
3. Collects 100 frames of video
4. User clicks Stop

Calculation:
- Required frames: 90
- Current frames: 100
- Already have enough ✓

Action:
- Stop immediately and merge
```

## Benefits

1. **Proper A/V Sync** - Video always has enough frames for audio duration
2. **No Dropped Audio** - All collected audio is preserved
3. **Clean State Management** - Stopping state properly tracked and cleaned up
4. **Safety First** - Validation and defaults prevent crashes
5. **Backward Compatible** - Only affects legacy mode, worker mode unchanged

## Future Enhancements

Potential improvements for future consideration:
1. Add UI feedback showing "Collecting frames..." during stopping state
2. Allow user to cancel the stopping state
3. Add timeout to prevent infinite waiting
4. Support for variable frame rate videos

## References

- **Modified File:** `node/VideoNode/node_video_writer.py`
- **Test File:** `tests/test_videowriter_stopping_state.py`
- **Related Tests:** `tests/test_workflow_integration_simple.py`
