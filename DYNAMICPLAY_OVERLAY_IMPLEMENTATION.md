# DynamicPlay Overlay Architecture Implementation

## Overview

This document describes the enhancement of the DynamicPlay node to implement a master stream + overlay architecture as requested in the problem statement.

## Problem Statement (Translated from French)

> "Okay, but for dynamic play, we need to first create a master stream on which we run the hand pose estimation model, and where we put the button. If the index is in the button, the button activates such or such stream, and the stream is embedded in the screen, and with the thumb and index we can move the image, make it smaller or larger according to thumb-index distance"

## Implementation

### Architecture Change

**Before:**
- Multiple input streams that could be selected
- Selected stream displayed full-screen
- Zoom functionality on selected stream

**After:**
- **Master Stream** (Input01): Always-visible background that runs hand pose estimation
- **Overlay Streams** (Input02-09): Up to 8 streams activatable as picture-in-picture
- Overlay can be moved and resized using hand gestures

### Key Features Implemented

#### 1. Master Stream with Hand Detection
- Input01 serves as the permanent background
- Hand pose estimation (MediaPipe Hands) runs continuously on master stream
- Button grid overlaid on master stream for overlay activation

#### 2. Picture-in-Picture Overlays
- Overlays appear as embedded windows on the master stream
- Only one overlay can be active at a time
- Cyan border highlights the active overlay
- Default size: 320x240 pixels

#### 3. Gesture Controls

**Activation:**
- Point thumb at numbered button (1-8)
- Overlay activates when thumb is inside button bounds
- Point at same button again to deactivate

**Dragging:**
- Pinch thumb and index finger together (< 40 pixels apart)
- Move hand while maintaining pinch
- Overlay position follows pinch midpoint
- Offset calculated from initial pinch to maintain grab position

**Resizing:**
- While pinching, vary thumb-index distance
- Distance 50px → Minimum size (100px)
- Distance 200px → Maximum size (800px)
- Linear interpolation between min and max
- Aspect ratio maintained automatically

### Code Changes

#### Modified Files
1. **node/VideoNode/node_dynamic_play.py** (major refactoring)
   - New class variables for overlay state
   - New method `_draw_overlay()` for picture-in-picture rendering
   - New method `_is_pinching()` for pinch gesture detection
   - Updated `update()` method for master+overlay architecture
   - Updated `close()` method for new state cleanup

2. **node/VideoNode/README_DynamicPlay.md** (documentation update)
   - New architecture description
   - Updated usage examples
   - Updated gesture control instructions

3. **node/VideoNode/README_DynamicPlay_FR.md** (French documentation update)
   - Complete French translation of new features
   - Updated examples and workflow

4. **tests/test_dynamic_play_node.py** (test updates)
   - Updated button creation test for overlay architecture
   - New overlay drawing test
   - New pinch gesture detection test
   - All 10 tests passing

### Technical Details

#### State Management
Per-node state dictionaries:
- `_active_overlay_index`: Currently active overlay (None if no overlay)
- `_overlay_position`: (x, y) position of overlay top-left corner
- `_overlay_size`: (width, height) of overlay in pixels
- `_is_dragging`: Boolean indicating if user is currently dragging
- `_drag_offset`: (dx, dy) offset from pinch point to overlay corner

#### Constants
```python
_MIN_OVERLAY_SIZE = 100        # Minimum overlay dimension
_MAX_OVERLAY_SIZE = 800        # Maximum overlay dimension
_BASE_PINCH_DISTANCE = 100     # Reference distance for calculations
_DEFAULT_OVERLAY_WIDTH = 320   # Initial overlay width
_DEFAULT_OVERLAY_HEIGHT = 240  # Initial overlay height
```

#### Gesture Detection

**Pointing Detection:**
```python
def _is_pointing(self, keypoints):
    # Index finger tip (8) above MCP (5)
    # Returns (is_pointing, tip_position)
```

**Pinch Detection:**
```python
def _is_pinching(self, keypoints):
    # Thumb tip (4) and index tip (8) < 40 pixels apart
    # Returns (is_pinching, midpoint_position)
```

**Distance Calculation:**
```python
def _calculate_pinch_distance(self, keypoints):
    # Euclidean distance between thumb (4) and index (8)
    # Used for resize calculation
```

### Visual Indicators

1. **Button Grid:**
   - Numbered 1-8 for overlay slots
   - Green border: Active overlay
   - White border: Available overlays
   - Red border: Button being pointed at

2. **Overlay Border:**
   - 3-pixel cyan border around active overlay
   - Makes overlay clearly visible on master stream

3. **On-Screen Text:**
   - "Overlay: N | Size: WxH" when overlay is active
   - "Point at button to activate overlay" when no overlay

4. **Hand Landmarks:**
   - Yellow circles: Thumb and index tips
   - Green circles: Other hand keypoints

### Grid Layout

Button grid adapts to number of overlay streams:

| Overlays | Grid Layout |
|----------|-------------|
| 1        | 1×1         |
| 2        | 2×1         |
| 3-4      | 2×2         |
| 5-6      | 3×2         |
| 7-8      | 3×3         |

### Example Workflow

```
[WebCam]    → Input01 (Master Stream)
[Video1]    → Input02 (Overlay 1)
[Video2]    → Input03 (Overlay 2)    → [DynamicPlay] → [Output]
[Video3]    → Input04 (Overlay 3)
```

**User Experience:**
1. Webcam always visible as background
2. Hand detection runs on webcam stream
3. Point at button "1" → Video1 appears as overlay
4. Pinch and drag → Move overlay around screen
5. Vary pinch distance → Resize overlay
6. Point at button "1" again → Deactivate overlay

### Testing

All 10 tests passing:
- ✅ Node registration
- ✅ File existence
- ✅ Import functionality
- ✅ Factory node attributes
- ✅ Node class attributes
- ✅ Node initialization
- ✅ Button grid creation
- ✅ Pinch distance calculation
- ✅ Pinch gesture detection
- ✅ Overlay drawing

### Code Quality

**Code Review:**
- ✅ All feedback addressed
- ✅ No magic numbers (constants defined)
- ✅ No duplicate code
- ✅ Clear comments and documentation

**Security:**
- ✅ CodeQL scan: 0 vulnerabilities
- ✅ No unsafe operations
- ✅ Proper bounds checking for overlay position/size

### Performance Considerations

1. **Hand Detection:** Runs only on master stream (not on overlays)
2. **Overlay Rendering:** Single resize operation per frame
3. **Memory:** Minimal overhead (state dictionaries only)
4. **Latency:** Real-time gesture response

### Limitations

1. Only one overlay active at a time
2. Maximum 8 overlay streams (9 total with master)
3. Single hand tracking
4. Overlay size limited to 100-800 pixels
5. Requires MediaPipe installation

### Future Enhancements

Potential improvements:
- Multiple simultaneous overlays
- Custom gesture mappings
- Overlay transparency/opacity control
- Overlay rotation
- Zoom within overlay
- Two-hand gestures
- Touch-style gestures on overlay

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| node/VideoNode/node_dynamic_play.py | ~200 modified | Core implementation |
| node/VideoNode/README_DynamicPlay.md | ~80 modified | English docs |
| node/VideoNode/README_DynamicPlay_FR.md | ~80 modified | French docs |
| tests/test_dynamic_play_node.py | ~40 modified | Updated tests |

## Version History

- **v0.0.1** (Original): Stream switching with zoom
- **v0.1.0** (This implementation): Master stream + overlay architecture

## Conclusion

The DynamicPlay node has been successfully enhanced to support the requested master stream + overlay architecture. The implementation provides:

✅ Continuous hand detection on master stream  
✅ Picture-in-picture overlay activation with pointing gesture  
✅ Overlay dragging with pinch gesture  
✅ Overlay resizing based on thumb-index distance  
✅ Comprehensive testing and documentation  
✅ Zero security vulnerabilities  

The node is ready for use and provides an intuitive hands-free interface for managing multiple video streams.
