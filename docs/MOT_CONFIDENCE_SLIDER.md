# MOT Node Confidence Slider Feature

## Overview

A new **confidence threshold slider** has been added to the Multi-Object Tracking (MOT) node in CV_Studio. This slider allows users to filter detections based on their confidence score before passing them to the tracker.

## UI Changes

The MOT node now includes a new slider control positioned between the tracker model selector and the performance counter:

```
┌─────────────────────────────────────────────────┐
│          Multi-Object Tracking (MOT) Node      │
├─────────────────────────────────────────────────┤
│  ◀ Image                                        │
│  ◀ JSON Start/Stop (boolean)                   │
│  ◀ JSON Detections                             │
├─────────────────────────────────────────────────┤
│  [Preview Image]                                │
├─────────────────────────────────────────────────┤
│  Tracker Model:  [▼ Dropdown        ]          │
│  **NEW** confidence: [━━━━━━━━━━━○] 0.0        │
│  elapsed time(ms)  ▶                            │
│  JSON  [Tracking Data]  ▶                       │
└─────────────────────────────────────────────────┘
```

### Slider Properties
- **Label**: "confidence"
- **Default Value**: 0.0 (no filtering)
- **Min Value**: 0.0
- **Max Value**: 1.0
- **Type**: Float slider

## Functionality

### How It Works

1. **Before Tracking**: The confidence threshold is applied to incoming detections before they are passed to the tracker algorithm.

2. **Filtering Logic**: 
   - If threshold = 0.0: No filtering is applied (all detections pass through)
   - If threshold > 0.0: Only detections with `score >= threshold` are kept

3. **After Filtering**: The filtered detections are passed to the selected tracker (ByteTrack, SORT, etc.)

### Code Implementation

The filtering is performed in the `update()` method of the MOT node:

```python
# Get confidence threshold from slider
confidence_threshold = dpg_get_value(confidence_threshold_tag)

# Filter detections based on confidence threshold
if confidence_threshold > 0.0:
    filtered_bboxes = []
    filtered_scores = []
    filtered_class_ids = []
    
    for bbox, score, class_id in zip(od_bboxes, od_scores, od_class_ids):
        if score >= confidence_threshold:
            filtered_bboxes.append(bbox)
            filtered_scores.append(score)
            filtered_class_ids.append(class_id)
    
    od_bboxes = filtered_bboxes
    od_scores = filtered_scores
    od_class_ids = filtered_class_ids
```

## Use Cases

### 1. Reducing False Positives
When object detection produces many low-confidence detections, setting a higher threshold (e.g., 0.5 or 0.6) can reduce false positives in tracking.

### 2. Improving Tracker Performance
Filtering out low-confidence detections can improve tracker performance by reducing the number of objects to track and avoiding confusion from uncertain detections.

### 3. Quality Control
For applications requiring high-quality tracking, set a higher threshold (e.g., 0.7 or 0.8) to only track objects the detector is very confident about.

## Example Usage

### Scenario: Tennis Court Tracking

**Input Detections** (from object detection):
- Player 1: bbox=[100, 100, 200, 200], score=0.95, class_id=0
- Player 2: bbox=[300, 100, 400, 200], score=0.82, class_id=0
- Ball: bbox=[250, 150, 260, 160], score=0.55, class_id=1
- False detection: bbox=[50, 50, 80, 80], score=0.25, class_id=0

**With Confidence Threshold = 0.0** (default):
- All 4 detections are tracked
- May result in tracking the false detection

**With Confidence Threshold = 0.5**:
- Player 1 (0.95) ✓ Tracked
- Player 2 (0.82) ✓ Tracked
- Ball (0.55) ✓ Tracked
- False detection (0.25) ✗ Filtered out

**With Confidence Threshold = 0.8**:
- Player 1 (0.95) ✓ Tracked
- Player 2 (0.82) ✓ Tracked
- Ball (0.55) ✗ Filtered out
- False detection (0.25) ✗ Filtered out

## Settings Persistence

The confidence threshold value is saved when you save your node configuration and restored when you load it:

- **Save**: The slider value is stored in `get_setting_dict()`
- **Load**: The slider value is restored in `set_setting_dict()`

## Compatibility

- **Backward Compatible**: Existing configurations without the confidence threshold setting will default to 0.0 (no filtering)
- **Works with All Trackers**: The filtering is applied before any tracker is called, so it works with all tracking algorithms (ByteTrack, SORT, OC-SORT, etc.)
- **Input Sources**: Works with detections from:
  - Object Detection nodes
  - ReId nodes
  - Any node that outputs detection JSON

## Technical Details

### Modified Files
- `node/TrackerNode/node_mot.py`: Added confidence slider UI and filtering logic

### Changes Made
1. Added slider UI component in `add_node()` method
2. Added filtering logic in `update()` method
3. Updated `get_setting_dict()` to save threshold value
4. Updated `set_setting_dict()` to restore threshold value

### Testing
- Unit tests for filtering logic: `tests/test_mot_confidence_slider.py`
- Demo script: `tests/demo_mot_confidence_slider.py`

## FAQ

**Q: What happens if I set the threshold too high?**
A: If the threshold is set higher than all detection scores, no objects will be tracked. The tracker will receive an empty list of detections.

**Q: Does this affect the object detection confidence slider?**
A: No, they are independent. The object detection slider filters detections before they leave the detection node. The MOT confidence slider filters them again before tracking. You can use both together for fine-grained control.

**Q: Should I always use a confidence threshold?**
A: Not necessarily. If your object detector is already well-tuned and produces good results, you can keep the threshold at 0.0. Use it when you notice false positives in tracking or want to improve performance.

**Q: Can I use different thresholds for different trackers?**
A: Yes, each MOT node instance maintains its own threshold value. If you have multiple MOT nodes, each can have a different threshold.
