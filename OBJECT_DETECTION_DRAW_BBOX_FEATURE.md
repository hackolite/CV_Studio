# Object Detection Draw Bounding Boxes Feature

## Overview
The Object Detection node includes a checkbox to control whether bounding boxes are drawn on the **output image** sent to downstream nodes. The **displayed image** in the UI always shows bounding boxes for visual feedback, while the output image respects the checkbox setting. This allows users to see detections while sending clean images for tracking or annotated images for video recording.

## Feature Details

### User Interface
A checkbox labeled "Draw Bounding Boxes" is included in the Object Detection node UI:
- **Location**: Below the "Reject" class dropdown
- **Default State**: Checked (enabled)
- **Label**: "Draw Bounding Boxes"

### Behavior

#### Display Image (UI Preview)
- **ALWAYS** shows bounding boxes regardless of checkbox state
- Provides visual feedback to see what the detector found
- Helps with debugging and verification
- Shows:
  - Colored bounding boxes
  - Class labels
  - Confidence scores

#### Output Image (Sent to Downstream Nodes)

**When Checkbox is CHECKED (Filled) ✓**
- Object detection runs normally
- Bounding boxes **ARE** drawn on the output image
- Detection data (bboxes, scores, class_ids) is sent in JSON output
- Use case: Video recording with annotations

**When Checkbox is UNCHECKED (Empty) ☐**
- Object detection runs normally
- Bounding boxes **ARE NOT** drawn on the output image
- Detection data (bboxes, scores, class_ids) is still sent in JSON output
- Output image is the original, unmodified frame
- Use case: Clean frames for tracking

### Key Points
1. **Display Always Shows Bounding Boxes**: The UI display always shows detections for user feedback, regardless of checkbox state
2. **Output Respects Checkbox**: The image sent to downstream nodes respects the checkbox setting
3. **JSON Output is Always Available**: Detection results are always available in the JSON output for downstream nodes
4. **Visual Independence**: Downstream nodes like Tracking can receive clean images while still having access to detection data
5. **Backward Compatible**: Existing workflows continue to work with the checkbox defaulting to enabled
6. **Settings Persistence**: The checkbox state is saved and loaded with the node settings

## Use Cases

### Use Case 1: Clean Pipeline for Video Recording
**Scenario**: You want to record video without visual annotations but still need detection data for analytics.

**Setup**:
1. Connect Object Detection → Tracking → Video Recorder
2. Uncheck "Draw Bounding Boxes" on Object Detection node
3. You still see bounding boxes in the UI for verification
4. Tracking node receives detection JSON and clean video frames
5. Video Recorder saves clean video
6. Analytics can still access detection data

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

# Separate displayed image from output image
display_frame = None  # For UI (always has bboxes)
output_frame = None   # For downstream nodes (respects checkbox)

if frame is not None:
    # Display image: ALWAYS draw bounding boxes (for user feedback)
    display_frame = copy.deepcopy(frame)
    display_frame = self.draw_object_detection_info(...)
    
    # Output image: Respect checkbox setting
    if draw_bbox:
        # When checked: send frame WITH bounding boxes (for video recording)
        output_frame = copy.deepcopy(frame)
        output_frame = self.draw_object_detection_info(...)
    else:
        # When unchecked: send clean frame (for tracking)
        output_frame = frame
    
    # Update UI with display frame (always has bboxes)
    texture = self.convert_cv_to_dpg(display_frame, ...)
    dpg_set_value(tag_node_output_image, texture)

# Send output frame to downstream nodes
data["image"] = output_frame
```

## Testing
Comprehensive tests verify:
1. Checkbox UI elements exist
2. Default value is True
3. Backward compatibility is maintained
4. Display frame and output frame are separated correctly
5. Display always shows bounding boxes
6. Output respects checkbox setting
7. JSON output is independent of checkbox state

Run tests with:
```bash
python tests/test_object_detection_draw_bbox_checkbox.py
python tests/test_bbox_display_vs_output.py
```

## Migration Guide
Existing workflows require **no changes**:
- The checkbox defaults to checked (enabled)
- All existing behavior is preserved
- Settings files are automatically upgraded with backward-compatible defaults

To use the new feature:
1. Open your workflow
2. Select the Object Detection node
3. Uncheck "Draw Bounding Boxes" to send clean images downstream
4. Note: You'll still see bounding boxes in the UI preview
5. Save your workflow to persist the setting

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
│  ☑ Draw Bounding Boxes  ← Controls OUTPUT only            │
│                                                             │
│  Display:[Image] ────────  ALWAYS shows bounding boxes     │
│  Output: [Image] ────────► (with or without bbox)         │
│          [JSON]  ────────► (always has detection data)    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

BEHAVIOR COMPARISON:

┌────────────────────────────────────────────────────────────────┐
│ CHECKBOX CHECKED (✓) - For Video Recording                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ UI Display (what you see):     Output (what's sent):          │
│ ┌──────────────────┐           ┌──────────────────┐           │
│ │  ┏━━━━━━━━┓      │           │  ┏━━━━━━━━┓      │           │
│ │  ┃ Person ┃      │           │  ┃ Person ┃      │           │
│ │  ┃ 0.95   ┃      │           │  ┃ 0.95   ┃      │           │
│ │  ┗━━━━━━━━┛      │           │  ┗━━━━━━━━┛      │           │
│ └──────────────────┘           └──────────────────┘           │
│   With bounding boxes            With bounding boxes           │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ CHECKBOX UNCHECKED (☐) - For Tracking                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ UI Display (what you see):     Output (what's sent):          │
│ ┌──────────────────┐           ┌──────────────────┐           │
│ │  ┏━━━━━━━━┓      │           │                  │           │
│ │  ┃ Person ┃      │           │                  │           │
│ │  ┃ 0.95   ┃      │           │   [clean image]  │           │
│ │  ┗━━━━━━━━┛      │           │                  │           │
│ └──────────────────┘           └──────────────────┘           │
│   STILL shows bboxes!            Clean (no bboxes)            │
│   (for verification)             (for tracking)               │
│                                                                │
└────────────────────────────────────────────────────────────────┘

JSON: {bboxes: [...], scores: [...], class_ids: [...]}  ← Always available
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
