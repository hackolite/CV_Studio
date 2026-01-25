# Class Exclusion and ReID Labeling - Verification Report

## Executive Summary

✅ **VERIFIED**: The class exclusion and ReID labeling system is correctly implemented.

After thorough analysis and testing, I can confirm that:
1. **Excluded classes are properly removed from JSON output** in the object detection node
2. **Excluded classes do NOT reach tracking or ReID nodes**
3. **ReID labeling is the authoritative source** when ReID is in the pipeline

## Problem Statement (French → English)

**Original**: "vérifie que la classe est bien exclue dans l'output json dans le node object detection, la classe exclue ne doit pas etre utilisée dans les autres nodes, tracking, reId non plus. la labellisation réalisée dans Reid est celle qui doit etre absolument utilisée ensuite."

**Translation**: "Verify that the class is properly excluded in the json output in the object detection node, the excluded class must not be used in other nodes, tracking, ReID either. The labeling done in ReID is the one that must absolutely be used afterwards."

## System Architecture

### Pipeline Configurations

#### Configuration 1: ObjectDetection → MOT (without ReID)
```
[ObjectDetection] --JSON--> [MOT] --JSON--> [Display]
     |                        |
     |- bboxes               |- track_ids
     |- scores               |- bboxes
     |- class_ids (filtered) |- scores
     |- class_names (dict)   |- class_ids (from OD)
                             |- class_names (from OD)
```

#### Configuration 2: ObjectDetection → ReID → MOT (with ReID)
```
[ObjectDetection] --JSON--> [ReID] --JSON--> [MOT] --JSON--> [Display]
     |                        |                |
     |- bboxes               |- bboxes        |- track_ids
     |- scores               |- scores        |- bboxes
     |- class_ids (filtered) |- class_ids     |- scores
     |- class_names (dict)      (REPLACED)    |- class_ids (from ReID)
                             |- class_names    |- class_names (from ReID)
                                (REPLACED)
```

## Implementation Details

### 1. Object Detection Node (`node/DLNode/node_object_detection.py`)

**Class Exclusion Filter** (lines 441-494):

```python
# Parse excluded classes from dropdown (format: "1: player2")
rejected_classes_str = dpg_get_value(self.tag_node_rejected_classes_value_name)

# Parse rejected class IDs
rejected_classes = set()
for class_str in rejected_classes_str.split(','):
    if ':' in class_str:
        class_id_str = class_str.split(':')[0].strip()
        rejected_classes.add(int(class_id_str))

# Filter out rejected classes
if rejected_classes:
    keep_mask = np.array([class_id not in rejected_classes for class_id in class_ids])
    bboxes = bboxes[keep_mask]
    scores = scores[keep_mask]
    class_ids = class_ids[keep_mask]
```

**JSON Output** (lines 496-501):
```python
result['bboxes'] = bboxes.tolist()      # Filtered bboxes
result['scores'] = scores.tolist()      # Filtered scores
result['class_ids'] = class_ids.tolist() # Filtered class_ids
result['class_names'] = class_name_dict  # Full dict (lookup table)
```

**Key Points**:
- ✅ Excluded classes are removed from `bboxes`, `scores`, and `class_ids` arrays
- ✅ `class_names` dictionary still contains all classes (used only as lookup)
- ✅ Only filtered data is passed to downstream nodes

### 2. ReID Node (`node/TrackerNode/node_reid.py`)

**Input Processing** (lines 447-451):
```python
# Extract object detection data
bboxes = json_data.get('bboxes', [])
scores = json_data.get('scores', [])
class_ids = json_data.get('class_ids', [])      # Already filtered by OD
class_names = json_data.get('class_names', [])
```

**ReID Labeling** (lines 468-492):
```python
reid_class_ids = []   # Replace class_ids with ReID labels
reid_class_names = [] # Replace class_names with slot names

for bbox in bboxes:
    feature = self._extract_features(frame, bbox)
    slot_idx = self._assign_to_centroid(feature, tag_node_name)
    
    if slot_idx is not None:
        slot_name = self._slot_names[tag_node_name].get(slot_idx, f"player{slot_idx}")
        reid_class_ids.append(slot_idx - 1)  # 0-indexed
        reid_class_names.append(slot_name)

# Create output JSON with REPLACED class_ids
result = {
    'bboxes': bboxes,
    'scores': scores,
    'class_ids': reid_class_ids,     # REPLACED with slot indices
    'class_names': reid_class_names,  # REPLACED with slot names
}
```

**Key Points**:
- ✅ ReID receives only non-excluded classes from ObjectDetection
- ✅ ReID completely replaces `class_ids` with slot-based labels (0, 1, 2...)
- ✅ ReID completely replaces `class_names` with custom slot names
- ✅ Original class IDs are not preserved after ReID

### 3. MOT Tracking Node (`node/TrackerNode/node_mot.py`)

**Input Reception** (lines 349-368):
```python
# Get detection data from JSON input (Input04) if connected
if json_detection_connection_src:
    node_result = node_result_dict.get(json_detection_connection_src, {})
elif connection_info_src:
    node_result = node_result_dict.get(connection_info_src, {})

od_bboxes = node_result.get('bboxes', [])
od_scores = node_result.get('scores', [])
od_class_ids = node_result.get('class_ids', [])     # From OD or ReID
od_class_names = node_result.get('class_names', []) # From OD or ReID
```

**Output** (lines 387-392):
```python
result['track_ids'] = track_ids
result['bboxes'] = t_bboxes
result['scores'] = t_scores
result['class_ids'] = t_class_ids       # Pass through from input
result['class_names'] = od_class_names  # Pass through from input
```

**Key Points**:
- ✅ MOT receives filtered data (either from OD or ReID)
- ✅ MOT passes through `class_ids` and `class_names` from its input
- ✅ If ReID is in pipeline, MOT uses ReID labels (not original OD class IDs)

### 4. Visualization (`node/basenode.py`)

**Drawing Function** (lines 926-984):
```python
def draw_multi_object_tracking_info(self, image, track_ids, bboxes, scores, class_ids, class_names, track_id_dict):
    for id, bbox, score, class_id in zip(track_ids, bboxes, scores, class_ids):
        # Get class name
        class_name = self.get_class_name(class_id, class_names)
        text = "CID:%s(%s)" % (str(int(class_id)), class_name)
```

**get_class_name Method** (lines 263-278):
```python
def get_class_name(self, class_id, class_names):
    class_id_int = int(class_id)
    if isinstance(class_names, dict):
        return class_names.get(class_id_int, f"class_{class_id_int}")
    elif isinstance(class_names, list) and 0 <= class_id_int < len(class_names):
        return class_names[class_id_int]
    # ... fallback
```

**Key Points**:
- ✅ Supports both dictionary (from OD) and list (from ReID) formats
- ✅ Only displays classes that are in the `class_ids` array
- ✅ Excluded classes never appear because they're not in `class_ids`

## Test Results

### Test 1: Class Exclusion End-to-End
**File**: `tests/test_class_exclusion_tracking_integration.py`

**Status**: ✅ PASSED

**Verified**:
- ObjectDetection excludes player2 (class_id=1) from JSON output
- MOT receives only [0, 2] (player1, ball)
- Track IDs remain consistent across multiple frames

### Test 2: ReID Pipeline Integration
**File**: `tests/test_reid_pipeline_integration.py`

**Status**: ✅ PASSED

**Verified**:
- ReID receives ObjectDetection data
- ReID replaces class_ids with slot indices
- MOT can process ReID output

### Test 3: Class Exclusion + ReID + MOT
**File**: `tests/test_class_exclusion_reid_mot_integration.py`

**Status**: ✅ PASSED

**Verified**:
- Excluded classes removed from ObjectDetection JSON
- ReID receives only non-excluded classes
- ReID replaces original class_ids with slot-based labels
- MOT uses ReID labels (not original class IDs)
- Excluded classes never reach any downstream node

### Test 4: Class Exclusion Without ReID
**File**: `tests/test_class_exclusion_without_reid.py`

**Status**: ✅ PASSED

**Verified**:
- ObjectDetection filters class_ids array correctly
- class_names dict contains all classes (lookup only)
- MOT receives only non-excluded class_ids
- Visualization shows only non-excluded objects

## Data Flow Validation

### Scenario: Tennis Match with Player Exclusion

**Setup**:
- 3 objects detected: player1 (class_id=0), player2 (class_id=1), ball (class_id=2)
- User excludes player2 (class_id=1)

**Without ReID (ObjectDetection → MOT)**:
```
ObjectDetection:
  class_ids: [0, 2]  ← player2 excluded
  class_names: {0: 'player1', 1: 'player2', 2: 'ball'}  ← full dict

MOT:
  class_ids: [0, 2]  ← received from OD
  class_names: {0: 'player1', 1: 'player2', 2: 'ball'}  ← passed through

Display:
  Track 100: Class 0 (player1)  ← looks up class_names[0]
  Track 101: Class 2 (ball)     ← looks up class_names[2]
```

**With ReID (ObjectDetection → ReID → MOT)**:
```
ObjectDetection:
  class_ids: [0, 2]  ← player2 excluded
  class_names: {0: 'player1', 1: 'player2', 2: 'ball'}

ReID:
  class_ids: [0, 1]  ← REPLACED with slot indices
  class_names: ['player1', 'ball']  ← REPLACED with slot names

MOT:
  class_ids: [0, 1]  ← received from ReID
  class_names: ['player1', 'ball']  ← received from ReID

Display:
  Track 100: Class 0 (player1)  ← uses ReID slot names
  Track 101: Class 1 (ball)     ← uses ReID slot names
```

## Answers to Problem Statement

### ✅ Question 1: "vérifie que la classe est bien exclue dans l'output json dans le node object detection"
**Answer**: YES, verified.

The class exclusion filter in `node_object_detection.py` (lines 441-494) correctly:
1. Parses the rejected classes from the dropdown
2. Filters `bboxes`, `scores`, and `class_ids` arrays
3. Outputs JSON with only non-excluded classes

**Evidence**:
- Line 486-488: `keep_mask` filters all arrays
- Line 497-499: Only filtered data goes into result JSON
- Tests confirm excluded classes never appear in `class_ids` array

### ✅ Question 2: "la classe exclue ne doit pas etre utilisée dans les autres nodes, tracking, reId non plus"
**Answer**: YES, verified.

Excluded classes do NOT reach downstream nodes:
1. **ReID Node**: Receives only filtered `class_ids` from ObjectDetection
2. **MOT Node**: Receives only filtered data (either from OD or ReID)
3. **Visualization**: Displays only classes present in `class_ids` array

**Evidence**:
- ReID input (line 450): `class_ids = json_data.get('class_ids', [])` receives filtered data
- MOT input (line 365): `od_class_ids = node_result.get('class_ids', [])` receives filtered data
- Tests confirm excluded classes never appear in any downstream node

### ✅ Question 3: "la labellisation réalisée dans Reid est celle qui doit etre absolument utilisée ensuite"
**Answer**: YES, verified.

When ReID is in the pipeline, its labeling becomes the authoritative source:
1. ReID **completely replaces** `class_ids` with slot indices (0, 1, 2...)
2. ReID **completely replaces** `class_names` with custom slot names
3. MOT receives and uses ReID labels (not original ObjectDetection class IDs)

**Evidence**:
- ReID output (lines 487-492): Creates new result with REPLACED class_ids/class_names
- MOT input (lines 365-366): Receives whatever its input provides (ReID labels if connected)
- Tests confirm MOT uses ReID slot indices when ReID is in pipeline

## Conclusion

The CV_Studio class exclusion and ReID labeling system is **correctly implemented** and **working as designed**.

### Summary of Findings:
✅ Excluded classes are properly filtered from JSON output in ObjectDetection  
✅ Excluded classes do not reach ReID or MOT nodes  
✅ ReID labeling completely replaces original class_ids when used  
✅ MOT tracking uses ReID labels as the authoritative source  
✅ Visualization displays only non-excluded, properly labeled objects  

### No Code Changes Required:
The existing implementation already satisfies all requirements from the problem statement. The comprehensive tests added validate the correct behavior.

### Test Coverage:
- ✅ Class exclusion without ReID (OD → MOT)
- ✅ Class exclusion with ReID (OD → ReID → MOT)
- ✅ Multi-frame consistency
- ✅ ReID labeling authority

All tests pass successfully, confirming the system works correctly.

---

**Verification Date**: 2026-01-25  
**Status**: ✅ VERIFIED - System Working Correctly  
**Tests Added**: 4 comprehensive integration tests  
**Tests Passed**: 4/4 (100%)
