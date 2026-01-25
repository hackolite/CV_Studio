# Tennis Court Display Synchronization - Implementation Summary

## Problem Statement

The tennis court sometimes displays things that are not shown in the tracking node display, or vice versa. The displays should be synchronized. Le Tennis court doit appliquer un nms. Laisse MOT comme tel. c'est le tennis court qui doit filtrer le tracking pour éviter les detections/tracking en double.

**Translation:** The Tennis court must apply NMS (Non-Maximum Suppression). Leave MOT as is. It's the tennis court that must filter the tracking to avoid duplicate detections/tracking.

## Root Cause Analysis

The issue was caused by duplicate detections in the data pipeline:

1. **Multiple detections per player**: Object detection may report the same person in multiple overlapping bounding boxes
2. **No filtering in tennis court**: The tennis court node was displaying ALL detections received from Homography without any deduplication
3. **Desynchronization**: MOT might filter some duplicates internally, but tennis court was showing everything, leading to mismatched displays

## Solution Implemented

### NMS (Non-Maximum Suppression) in Tennis Court Node

Added NMS filtering to `node/VisualNode/node_tennis_court.py` to remove duplicate detections before displaying on the tennis court visualization.

### Key Changes

#### 1. NMS Algorithm Implementation (`_nms` method)
```python
def _nms(self, bboxes, scores, iou_threshold):
    """
    Apply Non-Maximum Suppression to filter overlapping bounding boxes.
    - Uses IoU (Intersection over Union) to detect overlaps
    - Keeps detection with highest score in each overlapping cluster
    - Default threshold: 0.5 (50% overlap)
    """
```

**How it works:**
- Sorts detections by confidence score (highest first)
- For each detection, removes all overlapping detections (IoU > 0.5)
- Keeps only the best detection from each cluster

#### 2. Integration with Tracking Data (`_apply_nms_to_tracking` method)
```python
def _apply_nms_to_tracking(self, transformed_points, bboxes, scores, class_ids, labels):
    """
    Apply NMS to filter duplicate tracking detections.
    - Filters bboxes, transformed_points, labels, class_ids together
    - Ensures all arrays stay synchronized after filtering
    """
```

**Data flow:**
```
Homography Output:
  - transformed_points: [[4.5, 10.0], [4.6, 10.1], [7.0, 15.0], [2.5, 8.0]]
  - bboxes: [[500,300,600,600], [510,310,610,610], [700,300,800,600], [300,400,400,700]]
  - labels: ['Player A', 'Player A', 'Player B', 'Player C']
  
After NMS (IoU=0.5):
  - transformed_points: [[4.5, 10.0], [7.0, 15.0], [2.5, 8.0]]  ← Duplicate removed
  - bboxes: [[500,300,600,600], [700,300,800,600], [300,400,400,700]]
  - labels: ['Player A', 'Player B', 'Player C']
```

#### 3. Integration in Update Method
Modified the `update()` method to apply NMS before updating player positions:

```python
# Apply NMS to filter duplicate detections
if transformed_points is not None and bboxes and len(bboxes) > 0:
    transformed_points, labels, class_ids = self._apply_nms_to_tracking(
        transformed_points, bboxes, scores, class_ids, labels
    )

# Now update positions with filtered data
if transformed_points is not None and labels is not None:
    self._update_player_positions(transformed_points, labels)
```

### Configuration

Added configurable NMS threshold:
```python
# NMS (Non-Maximum Suppression) threshold for filtering duplicate detections
NMS_IOU_THRESHOLD = 0.5  # 50% overlap threshold
```

Can be adjusted if needed:
- Lower value (e.g., 0.3) = more aggressive filtering (fewer detections kept)
- Higher value (e.g., 0.7) = less aggressive filtering (more detections kept)

## Test Coverage

### Unit Tests (`test_tennis_court_nms.py`)
1. ✅ `test_nms_basic` - Verifies basic NMS with overlapping boxes
2. ✅ `test_nms_no_overlap` - Ensures non-overlapping boxes are preserved
3. ✅ `test_nms_empty_input` - Handles empty input gracefully
4. ✅ `test_apply_nms_to_tracking` - Tests filtering with labels and tracking data
5. ✅ `test_apply_nms_no_scores` - Works even without confidence scores
6. ✅ `test_nms_integration_with_update` - Integration with node update method

### Integration Tests (`test_nms_pipeline_integration.py`)
1. ✅ `test_nms_filters_duplicates_in_pipeline` - End-to-end duplicate filtering
2. ✅ `test_nms_preserves_non_overlapping_detections` - Preserves valid detections
3. ✅ `test_nms_synchronizes_mot_and_tennis_displays` - Verifies synchronization

### Existing Tests
- ✅ All existing tennis court tests continue to pass
- ✅ No regressions introduced

## Technical Improvements

### Modern IoU Calculation
- Uses continuous coordinates (no +1 offset)
- Compatible with modern object detection systems
- Consistent with other components

### Robust Validation
- Validates all array lengths before processing
- Handles missing scores gracefully
- Checks labels array length properly

### Clean Integration
- MOT node unchanged (as requested)
- Homography node unchanged
- Only tennis court node modified
- Minimal, surgical changes

## Results

### Before NMS
- Tennis court could show 4+ detections for 2 players
- Duplicates visible as overlapping markers
- Desynchronized with MOT display

### After NMS
- Tennis court shows exactly N unique players (matching MOT)
- No duplicate markers on court
- Displays synchronized between MOT and Tennis Court

## Example Scenario

**Input from MOT/Homography:**
- Player A detected twice (overlapping bboxes at IoU=0.75)
  - Detection 1: bbox=[500,300,600,600], score=0.95, position=[4.5, 10.0]
  - Detection 2: bbox=[510,310,610,610], score=0.85, position=[4.6, 10.1]
- Player B detected once
  - Detection 3: bbox=[700,300,800,600], score=0.90, position=[7.0, 15.0]

**After NMS (threshold=0.5):**
- Player A: 1 detection (kept Detection 1 with higher score)
  - bbox=[500,300,600,600], score=0.95, position=[4.5, 10.0]
- Player B: 1 detection (unchanged)
  - bbox=[700,300,800,600], score=0.90, position=[7.0, 15.0]

**Result:** Tennis court displays 2 markers (one per player) instead of 3

## Security Analysis

- ✅ CodeQL security scan: 0 alerts
- ✅ No new dependencies added
- ✅ No security vulnerabilities introduced

## Files Changed

1. `node/VisualNode/node_tennis_court.py` - Added NMS implementation
2. `tests/test_tennis_court_nms.py` - Added unit tests (new file)
3. `tests/test_nms_pipeline_integration.py` - Added integration tests (new file)

## Migration Notes

- No breaking changes
- No configuration required
- Works with existing pipelines
- Backward compatible

## Conclusion

The implementation successfully:
- ✅ Filters duplicate detections in tennis court display
- ✅ Synchronizes tennis court with MOT display
- ✅ Preserves MOT node unchanged (as requested)
- ✅ Passes all tests (unit + integration + existing)
- ✅ No security issues
- ✅ Uses minimal, surgical changes
