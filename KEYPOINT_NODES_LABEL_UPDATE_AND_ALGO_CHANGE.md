# Summary of Changes - Keypoint Nodes Label Update and Algorithm Revision

## Issues Resolved

This PR resolves the requirements stated in the issue:

1. **Renamed `Court/KeypointDeviation` → `CourtKeypointDeviation`** (removed slash, made it one word)
2. **Renamed `Court/KeypointData` → `CourtKeypointData`** (removed slash, made it one word)
3. **Revised the deviation detection algorithm** to use master frame with widest parallelogram

## Code Changes

### 1. Node Label Updates

**File: `node/TriggerNode/node_trigger_keypoint_deviation.py`**
- Changed `node_label = 'Court/KeypointDeviation'` 
- To `node_label = 'CourtKeypointDeviation'`
- Applied to both `FactoryNode` and `Node` classes

**File: `node/StatsNode/node_dataprocessing_keypoints.py`**
- Changed `node_label = 'Court/KeypointData'`
- To `node_label = 'CourtKeypointData'`
- Applied to both `FactoryNode` and `Node` classes

**Updated Tests**
- `tests/test_keypoints_nodes.py`: Updated assertions to match new labels
- `tests/test_keypoints_pipeline_integration.py`: Fixed import path and updated print statements

### 2. Algorithm Revision

**Previous Algorithm (Cumulative Average Based):**
- Maintained a cumulative sum of all keypoints seen
- Calculated mean from cumulative data
- Compared each new frame to the running average
- Used Euclidean distance for deviation measurement

**New Algorithm (Master Frame Based):**
The new algorithm implements a more sophisticated approach:

1. **Master Frame Selection:**
   - Calculates bounding box area for each frame's keypoints
   - Area = (max_x - min_x) × (max_y - min_y)
   - Tracks the frame with the largest area as the "master"
   - Updates master whenever a wider parallelogram is detected

2. **Deviation Calculation:**
   - For non-master frames, calculates sum of absolute differences (Manhattan distance)
   - Delta = Σ|current_keypoints - master_keypoints|
   - This represents the total positional deviation from the master frame

3. **Trigger Logic:**
   - Trigger activates when delta exceeds the threshold slider value
   - Threshold is user-adjustable via the UI slider
   - Distance is reset to 0 when a new master is selected

**Implementation Details:**

```python
class Node(Node):
    def __init__(self):
        self._master_keypoints = None  # Master frame with widest parallelogram
        self._master_area = 0.0  # Area of the master parallelogram
        self._last_trigger_state = False

    def update(...):
        # Calculate bounding box area
        x_coords = keypoints[:, 0]
        y_coords = keypoints[:, 1]
        width = np.max(x_coords) - np.min(x_coords)
        height = np.max(y_coords) - np.min(y_coords)
        current_area = width * height
        
        # Update master if this frame has a wider parallelogram
        if self._master_keypoints is None or current_area > self._master_area:
            self._master_keypoints = keypoints.copy()
            self._master_area = current_area
            distance = 0.0
        else:
            # Calculate delta: sum of absolute differences with master
            deltas = np.abs(keypoints - self._master_keypoints)
            distance = np.sum(deltas)
            
            # Check if distance exceeds threshold
            if distance > threshold_distance:
                trigger_state = True
```

**Output JSON Structure:**

The trigger node now provides richer information:

```json
{
  "trigger_info": {
    "triggered": false,
    "distance": 123.45,
    "threshold": 100.0,
    "master_area": 50000.0,
    "current_area": 48000.0,
    "is_master": false
  }
}
```

## Technical Rationale

### Why Master Frame Approach?

1. **Stability**: The master frame represents the most "open" or "expanded" court keypoint configuration
2. **Reference Point**: Provides a consistent baseline for comparison rather than a constantly changing average
3. **Semantic Meaning**: Larger bounding area typically indicates better pose detection or more visible court lines
4. **Practical Application**: In tennis court analysis, the widest view typically represents the optimal detection state

### Why Manhattan Distance?

- **Computational Efficiency**: Sum of absolute differences is faster than Euclidean distance
- **Interpretability**: Each unit directly corresponds to pixel displacement
- **Sensitivity**: Better captures individual keypoint deviations without being dominated by outliers

## Backward Compatibility

**Preserved:**
- `node_tag` values remain unchanged (`TriggerKeypointDeviation`, `DataProcessingKeypoints`)
- Existing JSON workflow files will continue to work
- Same input/output structure

**Changed:**
- Node labels in UI (visual only)
- Internal algorithm logic
- Output JSON includes new fields (`master_area`, `current_area`, `is_master`)
- Removed old fields (`count`)

## Security Summary

**CodeQL Scan**: 0 alerts
- No vulnerabilities introduced
- Proper array bounds checking
- Safe NumPy operations
- No resource leaks

## Impact

### Before
- Average-based deviation detection
- Running cumulative calculation
- Node labels: `Court/KeypointDeviation`, `Court/KeypointData`

### After
- Master frame-based deviation detection
- Widest parallelogram selection logic
- Node labels: `CourtKeypointDeviation`, `CourtKeypointData`
- Richer diagnostic information in output JSON

## Usage Example

```python
# The trigger node automatically:
# 1. Monitors incoming keypoint JSON
# 2. Identifies the frame with largest bounding area as master
# 3. Calculates deviation from master for subsequent frames
# 4. Triggers when deviation exceeds slider threshold

# User only needs to:
# - Connect keypoint source to trigger node
# - Adjust threshold slider to desired sensitivity
```
