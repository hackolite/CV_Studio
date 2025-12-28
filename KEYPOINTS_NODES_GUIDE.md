# Keypoints Data Processing and Trigger Nodes

## Overview

This implementation adds two new nodes to CV_Studio for processing and monitoring keypoints data from pose estimation models (like the Tennis pose estimation node):

1. **DataProcessing/Keypoints** - Receives and validates keypoints data from pose estimation nodes
2. **Trigger/KeypointDeviation** - Monitors keypoints over time and triggers when significant deviation is detected

## Nodes Description

### DataProcessing/Keypoints Node

**Location:** `VisionProcess` menu → `DataProcessing/Keypoints`

**Purpose:** Receives JSON data containing keypoints from pose estimation nodes, validates the structure, and passes it through to downstream nodes.

**Inputs:**
- JSON keypoints data from pose estimation nodes (like TennisKeyPoints)

**Outputs:**
- JSON keypoints data (pass-through with processing metadata)
- Elapsed time (when performance counter is enabled)

**Features:**
- Validates that input contains `results_list` field with keypoints
- Adds metadata: `processed=True` and `processing_node='DataProcessingKeypoints'`
- Compatible with all pose estimation models that output keypoints in `results_list` field

### Trigger/KeypointDeviation Node

**Location:** `Trigger` menu → `Trigger/KeypointDeviation`

**Purpose:** Monitors keypoints over a time window and triggers when the current position deviates significantly from the average.

**Inputs:**
- JSON keypoints data (from DataProcessing/Keypoints or directly from pose estimation)

**Parameters:**
- **Window (sec)**: Time window in seconds for calculating average position (default: 2.0, range: 0.5-10.0)
- **Threshold**: Distance threshold that triggers deviation detection (default: 100.0, range: 10.0-500.0)

**Outputs:**
- **Trigger**: Boolean indicating whether deviation threshold was exceeded
- **Distance**: Current calculated distance from average position
- **JSON**: Pass-through keypoints data with added `trigger_info` metadata
- Elapsed time (when performance counter is enabled)

**Algorithm:**
1. Maintains a sliding window buffer of keypoints over the specified time window
2. Calculates the mean keypoints position over the window
3. Computes Euclidean distance between current keypoints and mean
4. Triggers if distance > threshold

**Trigger Info Metadata:**
The output JSON includes a `trigger_info` dictionary with:
- `triggered`: boolean - whether the threshold was exceeded
- `distance`: float - calculated distance value
- `threshold`: float - current threshold setting
- `window_seconds`: float - time window used
- `buffer_size`: int - number of samples in buffer

## Usage Pipeline

### Basic Pipeline
```
PoseEstimation (Tennis) → DataProcessing/Keypoints → Trigger/KeypointDeviation
```

### Example Use Cases

1. **Sports Movement Detection**
   - Detect when a tennis player makes a significant movement (serve, swing, etc.)
   - Window: 1-2 seconds
   - Threshold: 100-200 pixels

2. **Pose Change Detection**
   - Identify when a person changes from one pose to another
   - Window: 0.5-1 seconds  
   - Threshold: 50-150 pixels

3. **Activity Monitoring**
   - Track if someone moves from a resting position
   - Window: 2-5 seconds
   - Threshold: 150-300 pixels

## Testing

Three test files are provided:

1. **tests/test_keypoints_nodes.py** - Unit tests for individual node functionality
2. **tests/test_keypoints_pipeline_integration.py** - Integration test of the full pipeline

Run tests:
```bash
python tests/test_keypoints_nodes.py
python tests/test_keypoints_pipeline_integration.py
```

All tests should pass with the message "All tests passed! ✓"

## Technical Details

### Keypoints Data Format

Expected input format from pose estimation:
```python
{
    'model_name': 'TennisKeyPoints',
    'score_th': 0.3,
    'results_list': np.ndarray([[x1, y1], [x2, y2], ...])  # Shape: (N, 2)
}
```

### Distance Calculation

The trigger node uses Euclidean distance on flattened keypoints:
```python
distance = sqrt(sum((current_keypoints - mean_keypoints)^2))
```

### Buffer Management

- Keypoints are stored with timestamps in a deque
- Old entries outside the time window are automatically removed
- Requires at least 2 samples before calculating distances
- Buffer size is reported in trigger_info

## Configuration Tips

### Adjusting Sensitivity

**For more sensitive detection (trigger more often):**
- Decrease threshold value
- Decrease window size (shorter averaging period)

**For less sensitive detection (trigger only on major changes):**
- Increase threshold value
- Increase window size (longer averaging period)

### Optimal Settings

Start with defaults and adjust based on your use case:
- **Fast movements**: Window=1.0s, Threshold=150
- **Slow movements**: Window=3.0s, Threshold=100
- **Fine movements**: Window=0.5s, Threshold=50

## Compatibility

- Works with any pose estimation model that outputs keypoints in a `results_list` field as a numpy array
- Compatible with:
  - TennisKeyPoints
  - TennisKeyPoints_2
  - MoveNet models
  - MediaPipe Pose/Hands (if they output in same format)

## Future Enhancements

Possible improvements:
- Add different distance metrics (Manhattan, Cosine)
- Support for tracking specific keypoints only
- Multiple threshold levels with different outputs
- Smoothing options for noisy keypoint data
- Velocity-based triggering
