# Object Detection Draw Bounding Boxes Feature

## Overview
The Object Detection node now includes a checkbox to control whether bounding boxes are drawn on the output image. This allows users to send images with or without visual annotations while maintaining the detection data in JSON format.

## Feature Details

### User Interface
A new checkbox labeled "Draw Bounding Boxes" has been added to the Object Detection node UI:
- **Location**: Below the "Reject" class dropdown
- **Default State**: Checked (enabled)
- **Label**: "Draw Bounding Boxes"

### Behavior

#### When Checkbox is CHECKED (Filled) ✓
- Object detection runs normally
- Bounding boxes are drawn on the output image
- Detection data (bboxes, scores, class_ids) is sent in JSON output
- Image output shows visual annotations with:
  - Colored bounding boxes
  - Class labels
  - Confidence scores

#### When Checkbox is UNCHECKED (Empty) ☐
- Object detection runs normally
- **NO** bounding boxes are drawn on the output image
- Detection data (bboxes, scores, class_ids) is still sent in JSON output
- Image output shows the original, unmodified frame

### Key Points
1. **JSON Output is Always Available**: Regardless of the checkbox state, detection results are always available in the JSON output for downstream nodes
2. **Visual Independence**: Downstream nodes like Tracking can receive clean images while still having access to detection data
3. **Backward Compatible**: Existing workflows will continue to work with the checkbox defaulting to enabled
4. **Settings Persistence**: The checkbox state is saved and loaded with the node settings

## Use Cases

### Use Case 1: Clean Pipeline for Video Recording
**Scenario**: You want to record video without visual annotations but still need detection data for analytics.

**Setup**:
1. Connect Object Detection → Tracking → Video Recorder
2. Uncheck "Draw Bounding Boxes" on Object Detection node
3. Tracking node receives detection JSON but clean video frames
4. Video Recorder saves clean video
5. Analytics can still access detection data

### Use Case 2: Debugging with Visual Feedback
**Scenario**: You want to see what the object detector found.

**Setup**:
1. Keep "Draw Bounding Boxes" checked (default)
2. Visual output shows all detections with bounding boxes
3. Easy to verify detection accuracy

### Use Case 3: Dual Output
**Scenario**: You need both annotated and clean versions.

**Setup**:
1. Use two Object Detection nodes with same input
2. First node: Checkbox checked → annotated output
3. Second node: Checkbox unchecked → clean output
4. Different downstream processing for each

## Tracking Node Behavior
The Tracking (Multi-Object Tracking) node is **unchanged** and continues to:
- Draw tracking bounding boxes on its output (as before)
- Show track IDs (TID) and class IDs (CID)
- Receive detection data from Object Detection via JSON

The tracking node draws its **own** bounding boxes based on tracking results, independent of the Object Detection node's checkbox setting.

## Implementation Details

### Technical Changes
1. **UI Addition**: Added checkbox with tag `DrawBBoxValue`
2. **Update Logic**: Modified `update()` method to check checkbox state before drawing
3. **Settings Methods**: Added checkbox state to `get_setting_dict()` and `set_setting_dict()`
4. **Default Value**: Defaults to `True` for backward compatibility

### Code Flow
```python
# Get checkbox state
draw_bbox = dpg_get_value(self.tag_node_draw_bbox_value_name)
if draw_bbox is None:
    draw_bbox = True  # Default

# Conditional drawing
if frame is not None:
    if draw_bbox:
        # Draw bounding boxes on copy
        debug_frame = copy.deepcopy(frame)
        debug_frame = self.draw_object_detection_info(...)
    else:
        # Send original frame
        debug_frame = frame
```

## Testing
Comprehensive tests verify:
1. Checkbox UI elements exist
2. Default value is True
3. Backward compatibility is maintained
4. Conditional drawing logic is correct
5. JSON output is independent of checkbox state

Run tests with:
```bash
python tests/test_object_detection_draw_bbox_checkbox.py
```

## Migration Guide
Existing workflows require **no changes**:
- The checkbox defaults to checked (enabled)
- All existing behavior is preserved
- Settings files are automatically upgraded with backward-compatible defaults

To use the new feature:
1. Open your workflow
2. Select the Object Detection node
3. Uncheck "Draw Bounding Boxes" to send clean images
4. Save your workflow to persist the setting

## Visual Summary

```
┌─────────────────────────────────────────────────────────────┐
│              OBJECT DETECTION NODE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input:  [Image] ────────►                                 │
│                                                             │
│  Model:  [YOLOX-Nano ▼]                                    │
│  Score:  [━━━●━━━━━━━━] 0.3                               │
│  Reject: [           ▼]                                    │
│  ☑ Draw Bounding Boxes  ← NEW FEATURE!                    │
│                                                             │
│  Output: [Image] ────────►  (with or without bbox)        │
│          [JSON]  ────────►  (always has detection data)   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

CHECKED (✓):                    UNCHECKED (☐):
┌──────────────────┐           ┌──────────────────┐
│  ┏━━━━━━━━┓      │           │                  │
│  ┃ Person ┃      │           │                  │
│  ┗━━━━━━━━┛      │           │                  │
│    0.95          │           │   [clean image]  │
│                  │           │                  │
└──────────────────┘           └──────────────────┘
  With bounding boxes            Without bounding boxes
  JSON: {bboxes: [...]}          JSON: {bboxes: [...]}
```

## Future Enhancements
Possible future improvements:
- Toggle button for quick enable/disable
- Keyboard shortcut for checkbox
- Different visualization styles (filled, transparent, etc.)
- Per-class drawing control

## Support
For issues or questions:
1. Check this documentation
2. Review test cases in `tests/test_object_detection_draw_bbox_checkbox.py`
3. Open an issue on GitHub
