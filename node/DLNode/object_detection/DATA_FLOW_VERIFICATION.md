# Object Detection to Tracking - Data Flow Verification

## Overview

This document verifies that class exclusion in the Object Detection node properly filters data before it reaches downstream nodes like Multi-Object Tracking (MOT).

## Data Flow

### 1. Object Detection Node (`node_object_detection.py`)

The Object Detection node processes frames and applies class exclusion:

```
Frame Input
    ↓
Run Detection Model (line 434-435)
    ↓
Apply Per-Class NMS (line 438-439)
    ↓
Apply Class Rejection Filter (line 442-484)
    │
    ├─ Parse rejected classes from UI dropdown (line 444-467)
    ├─ Create keep_mask for non-rejected classes (line 475)
    └─ Filter bboxes, scores, class_ids (line 476-478)
    ↓
Populate Result Dictionary (line 486-499)
    │
    ├─ result['bboxes'] = filtered bboxes
    ├─ result['scores'] = filtered scores
    ├─ result['class_ids'] = filtered class_ids
    └─ result['class_names'] = class name dictionary
    ↓
Draw Detection Overlay (line 509-518)
    │ (uses same filtered bboxes, scores, class_ids)
    ↓
Return Data (line 525-527)
    └─ data["json"] = result (containing filtered detections)
```

### 2. Main Loop (`main.py`)

The main loop stores the returned JSON in `node_result_dict`:

```python
node_result_dict[node_id_name] = copy.deepcopy(data["json"])
```

**Key Point**: `copy.deepcopy()` ensures no aliasing issues.

### 3. Multi-Object Tracking Node (`node_mot.py`)

The MOT node retrieves detection data from `node_result_dict`:

```
Read node_result_dict (line 351-359)
    ↓
Validate Detection Format (line 362)
    ↓
Extract Detection Data (line 363-366)
    │
    ├─ od_bboxes = node_result['bboxes']
    ├─ od_scores = node_result['scores']
    ├─ od_class_ids = node_result['class_ids']
    └─ od_class_names = node_result['class_names']
    ↓
Run Tracker (line 369-375)
    └─ Uses filtered detection data
    ↓
Assign Track IDs (line 377-383)
    ↓
Return Tracking Result (line 385-390)
```

## Class Exclusion Verification

### Scenario: Exclude player2 (class 1) in Tennis Tracking

**Input to Object Detection:**
- Detections: `[player1, player2, ball]`
- Class IDs: `[0, 1, 2]`
- Rejected Classes: `"1: player2"`

**After Class Rejection Filter:**
- Detections: `[player1, ball]`
- Class IDs: `[0, 2]`

**JSON Output from Object Detection:**
```json
{
  "bboxes": [[x1, y1, x2, y2], [x3, y3, x4, y4]],
  "class_ids": [0, 2],
  "scores": [0.95, 0.75],
  "class_names": {0: "player1", 1: "player2", 2: "ball"}
}
```

**Input to MOT:**
- The MOT node receives the **same filtered JSON**
- It only sees: `[player1, ball]` with class IDs `[0, 2]`
- player2 (class 1) is **completely absent** from the tracking input

**Result:**
- ✅ player2 is never tracked
- ✅ No "player switches" can occur because player2 never enters the tracking system

## Logging

The following debug logs can be used to verify data flow:

### Object Detection Node
```
DEBUG: Class rejection filter input: '1: player2'
DEBUG: Before class rejection: 3 detections, class_ids=[0, 1, 2]
DEBUG: Rejected classes: {1}
DEBUG: After class rejection: 2 detections, class_ids=[0, 2]
INFO: Class rejection filter: Excluded {1}, kept 2 detections
DEBUG: JSON output: 2 detections, class_ids=[0, 2]
```

### MOT Node
```
DEBUG: MOT received detections: 2 objects, class_ids=[0, 2]
```

## Potential Issues and Mitigations

### Issue 1: Dropdown Not Selected
**Symptom**: All classes pass through (no exclusion)
**Detection**: Log shows `Class rejection filter input: ''`
**Mitigation**: Code handles empty string (line 445)

### Issue 2: Invalid Class ID Format
**Symptom**: Class exclusion doesn't work
**Detection**: ValueError when parsing class IDs
**Mitigation**: Try-except catches invalid IDs (line 465)

### Issue 3: All Classes Rejected
**Symptom**: Empty detections passed to MOT
**Detection**: Log shows `JSON output: 0 detections`
**Mitigation**: MOT handles empty input gracefully

### Issue 4: Player Switches Due to Inconsistent Exclusion
**Symptom**: Player appears/disappears causing track ID changes
**Root Cause**: User changing exclusion settings during runtime
**Mitigation**: Document that exclusion should be set before starting tracking

## Verification Checklist

- [x] Class rejection filter modifies local variables (bboxes, scores, class_ids)
- [x] Filtered variables are used for JSON output (result dictionary)
- [x] Filtered variables are used for visual display (drawing)
- [x] JSON is deep-copied to avoid aliasing issues
- [x] MOT receives the same filtered data from node_result_dict
- [x] Logging added to track data flow at each stage
- [x] Empty detection case handled correctly
- [x] Invalid class ID parsing handled with try-except

## Conclusion

**The class exclusion implementation is CORRECT**. The filtered JSON from the Object Detection node is properly passed to the MOT node and used for tracking.

If "player switches" still occur, possible causes are:
1. **User changing exclusion settings during runtime** - Causes inconsistent filtering
2. **Tracker algorithm limitations** - Some trackers may swap IDs under occlusion
3. **Detection quality issues** - Low confidence or missed detections
4. **Class ID confusion** - Wrong class being excluded (verify class IDs in dropdown)

**Recommendation**: Enable DEBUG logging to verify the exact data flow in your specific scenario.
