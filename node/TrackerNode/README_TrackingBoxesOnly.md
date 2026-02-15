# Tracking Boxes Only Feature

## Problem

When the MOT (Multi-Object Tracking) node receives frames from an Object Detection node, those frames already have detection bounding boxes drawn on them. When the MOT node then draws tracking bounding boxes on top, both sets of boxes become visible, which can be confusing.

## Solution

A new checkbox "Tracking Boxes Only" has been added to the MOT node that allows users to display only the tracking bounding boxes without the object detection bounding boxes.

## Usage

### Option 1: Show Both Detection and Tracking Boxes (Default)

1. Connect your pipeline: `Video → Object Detection → MOT`
2. Keep the "Tracking Boxes Only" checkbox **unchecked** (default)
3. The MOT node will display both detection boxes (from the input frame) and tracking boxes (drawn by MOT)

### Option 2: Show Only Tracking Boxes

1. Connect your pipeline: `Video → Object Detection → MOT`
2. **Check** the "Tracking Boxes Only" checkbox in the MOT node
3. The MOT node will display only tracking boxes on a black background
4. Detection boxes will not be visible

## Visual Comparison

### Before (Checkbox Unchecked - Default)
```
Input Frame:     [Video with detection boxes drawn]
MOT Processing:  [Adds tracking boxes on top]
Result:          [Video with BOTH detection and tracking boxes visible]
```

### After (Checkbox Checked)
```
Input Frame:     [Video with detection boxes drawn] 
MOT Processing:  [Creates clean black frame, draws only tracking boxes]
Result:          [Black background with ONLY tracking boxes visible]
```

## Technical Details

### Implementation

When "Tracking Boxes Only" is enabled:
- MOT creates a clean black frame using `np.zeros_like(frame)`
- Tracking boxes are drawn on this clean frame
- Detection boxes are not visible since they were on the original frame

When "Tracking Boxes Only" is disabled (default):
- MOT uses the input frame as-is (may have detection boxes)
- Tracking boxes are drawn on top
- Both detection and tracking boxes may be visible

### Code Location

- File: `node/TrackerNode/node_mot.py`
- UI Element: Checkbox labeled "Tracking Boxes Only"
- Default: `False` (maintains backward compatibility)

## Use Cases

### When to Use "Tracking Boxes Only"

1. **Clear Tracking Visualization**: When you want to see only which objects are being tracked
2. **Debugging Tracking**: To verify tracking behavior without detection box clutter
3. **Tracking Performance Analysis**: To focus solely on tracking results
4. **Downstream Processing**: When you want to send only tracking data downstream

### When to Use Default (Both Boxes)

1. **Full Pipeline Visualization**: To see both detection and tracking in context
2. **Comparison**: To compare detection vs tracking bounding boxes
3. **Debugging**: To see if tracking boxes match detection boxes
4. **Standard Operation**: For normal use with visual context

## Backward Compatibility

✅ **Fully backward compatible**
- Default checkbox state is `False` (unchecked)
- Existing pipelines continue to work without changes
- No breaking changes to existing functionality

## Testing

Run the test suite:
```bash
python tests/test_tracking_only_boxes.py
```

Expected output:
```
✓ Clean frame creation: PASS
✓ Dimension matching: PASS
✓ Tracking boxes drawing: PASS
✓ Detection boxes removal: PASS
✓ Checkbox behavior: PASS
```

## Notes

- The black background when using "Tracking Boxes Only" mode is intentional
- It clearly indicates that only tracking data is being displayed
- To see tracking boxes with video content, connect the video source directly to MOT for the image input, and use Object Detection's JSON output for detection data

## Recommended Pipeline Architecture

For optimal results, use this architecture:

```
Video Source
  ├──> Object Detection (JSON Output only)
  │       └──> MOT (JSON Input for detections)
  └──> MOT (Image Input for clean frame)
```

This way:
- MOT receives clean video frames (no pre-drawn boxes)
- MOT receives detection data via JSON
- MOT can draw tracking boxes on clean frames
- Result: Clean visualization with only tracking boxes (even without the checkbox)
