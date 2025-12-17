# YouTube and Video Node Consistency

## Overview

This document describes the changes made to ensure the YouTube and Video input nodes function similarly and correctly.

## Problem Statement

The YouTube input node had inconsistencies in its implementation compared to the Video input node:
- Two update methods (`_update` and `update`) causing confusion
- No proper state management for Start/Stop functionality
- Inconsistent frame timing and interval handling
- Missing proper frame caching
- Unused import (pafy) that caused dependency issues

## Changes Made

### 1. Removed Deprecated `_update` Method

**Before:**
```python
def _update(self, node_id, connection_list, node_image_dict, node_result_dict):
    # Old implementation
    
def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
    # Another implementation
```

**After:**
```python
def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
    # Single, consistent implementation
```

### 2. Added State Management

Added proper state tracking to match Video node:
```python
def __init__(self):
    # ... existing code ...
    
    # State management
    self._is_playing = {}
    self._last_frame_time = {}
    self._last_frame = {}
```

### 3. Improved Button Callback

Enhanced the button callback to properly track playback state:
```python
def button(self, sender, data, user_data):
    # ... existing code ...
    node_id = tag_parts[0]
    
    if label == self._start_label:
        # ... start logic ...
        self._is_playing[node_id] = True
    elif label == self._stop_label:
        # ... stop logic ...
        self._is_playing[node_id] = False
```

### 4. Standardized Update Method

The update method now:
- Checks if playback is active before reading frames
- Uses frame interval from slider
- Properly caches frames
- Returns consistent structure: `{"image": frame, "json": None, "audio": None}`

### 5. Removed Unused Import

Removed the `pafy` import that was not actually used in the code.

## Testing

Created comprehensive test suite (`test_youtube_video_similarity.py`) that verifies:
- Both nodes have the same update method signature
- Both nodes have state management attributes
- Both nodes have close methods
- Both nodes have settings methods
- Both nodes return the same structure
- YouTube node no longer has deprecated `_update` method

All 15 tests pass:
- 6 URL validation tests
- 2 button tag parsing tests
- 7 similarity tests

## Node Comparison

### Similarities (Core Functionality)
Both nodes now share:
1. State management (`_is_playing`, `_last_frame_time`, `_last_frame`)
2. Proper `update()` method with same signature
3. Consistent return structure
4. Start/Stop button behavior
5. Frame interval control from slider
6. Resource cleanup via `close()` method
7. Settings persistence

### Differences (By Design)
The nodes differ in their specialized features:

| Feature | YouTube Node | Video Node |
|---------|--------------|------------|
| **Input Source** | YouTube URLs via yt-dlp | Local video files |
| **Selection UI** | Text input for URL | File dialog |
| **Loop** | ❌ | ✅ |
| **Target FPS** | ❌ | ✅ |
| **Playback Speed** | ❌ | ✅ |
| **Audio Support** | Placeholder only | Full support |
| **Queue Display** | ❌ | ✅ |
| **VFR to CFR** | ❌ | ✅ |

## Benefits

1. **Consistency**: Both nodes now follow the same architectural patterns
2. **Maintainability**: Single update method is easier to maintain
3. **Correctness**: Proper state management prevents race conditions
4. **User Experience**: Predictable Start/Stop behavior
5. **Testing**: Comprehensive test coverage ensures quality

## Future Enhancements

Potential improvements for the YouTube node:
- Add loop functionality for continuous playback
- Implement actual audio extraction from YouTube streams
- Add playback speed control
- Add queue size display
- Consider VFR to CFR conversion for YouTube streams

## Conclusion

The YouTube and Video nodes now have consistent behavior for their core functionality (streaming video frames with Start/Stop control), while maintaining their specialized features. This ensures a better user experience and easier maintenance going forward.
