# K-means Court Keypoint Deviation Implementation

## Overview

This document describes the K-means clustering implementation for the `CourtKeypointDeviation` trigger node in CV_Studio.

## Problem Statement

The goal was to implement a K-means clustering algorithm that:
1. Clusters keypoints into 2 groups: "court" (in-play) and "out-of-play"
2. Identifies the court cluster as the one with least variation
3. Triggers when new keypoints belong to the out-of-play cluster
4. Allows user configuration of sample count for training (100, 200, or 300)
5. Returns JSON with standard `BOOL` field format

## Implementation Details

### Algorithm Overview

The implementation uses a two-phase approach:

#### Phase 1: Training
1. Collects keypoints from incoming JSON data
2. Flattens each keypoint array (shape [N, 2]) to 1D for K-means
3. Buffers samples until configured count is reached (100, 200, or 300)
4. Trains sklearn KMeans model with 2 clusters
5. Calculates variance for each cluster (sum of variances per dimension)
6. Identifies court cluster as the one with least variance
7. Stores trained model and court cluster ID

#### Phase 2: Classification
1. Predicts cluster for new incoming keypoints
2. Calculates distance to court cluster center
3. Triggers if:
   - Primary: Predicted cluster != court cluster (not in court)
   - Secondary: Distance to court center > threshold
4. Outputs JSON with `BOOL` field and classification info

### UI Components

**Inputs:**
- Keypoints JSON (from pose estimation nodes)

**Parameters:**
- **Threshold** (slider): Distance threshold for secondary trigger condition (10-500, default 100)
- **Sample Count** (dropdown): Number of samples for training (100, 200, 300, default 200)

**Outputs:**
- **Trigger (BOOL)**: Boolean output following standard format
- **Distance**: Distance to court cluster center
- **JSON**: Pass-through with added `BOOL` and `kmeans_info` fields

### JSON Output Format

During training:
```json
{
  "BOOL": false,
  "kmeans_info": {
    "training_complete": false,
    "samples_collected": 50,
    "samples_needed": 100
  }
}
```

After training (training complete):
```json
{
  "BOOL": false,
  "kmeans_info": {
    "training_complete": true,
    "samples_collected": 100,
    "court_cluster_id": 0,
    "variance_cluster_0": 616.11,
    "variance_cluster_1": 8406.49
  }
}
```

During classification:
```json
{
  "BOOL": true,
  "kmeans_info": {
    "training_complete": true,
    "predicted_cluster": 1,
    "court_cluster_id": 0,
    "is_court": false,
    "distance_to_court": 245.67,
    "threshold": 100.0
  }
}
```

### Technical Considerations

1. **Variance Calculation**: Uses sum of variances across all dimensions for accurate cluster comparison
2. **Flattened Keypoints**: Each keypoint array is flattened to 1D for K-means compatibility
3. **Random State**: Fixed at 42 for reproducible results
4. **K-means Initialization**: Uses 10 initializations (n_init=10) for robust clustering

## Usage Example

### Basic Pipeline
```
PoseEstimation (Tennis) → CourtKeypointDeviation → VideoRecorder
```

### Configuration Steps
1. Add CourtKeypointDeviation node to workflow
2. Connect keypoints JSON output from pose estimation
3. Select sample count (e.g., 200 for balanced training)
4. Adjust threshold if needed for sensitivity
5. Let system collect samples (shows progress in JSON output)
6. After training, triggers automatically when keypoints leave court cluster

### Use Cases

1. **Tennis Out Detection**:
   - Detects when ball/player keypoints move outside court boundaries
   - Sample count: 200 (good balance)
   - Threshold: 100-150

2. **Sports Activity Zones**:
   - Identifies when players enter restricted zones
   - Sample count: 300 (more stable clusters)
   - Threshold: 150-200

3. **Movement Pattern Detection**:
   - Detects unusual movement patterns
   - Sample count: 100 (faster training)
   - Threshold: 50-100

## Testing

Two comprehensive test suites verify the implementation:

1. **test_keypoints_nodes.py**: Basic structure and attribute tests
2. **test_kmeans_keypoint_deviation.py**: Full K-means functionality tests
   - Training phase verification
   - Classification accuracy
   - JSON BOOL format compliance

Run tests:
```bash
python tests/test_keypoints_nodes.py
python tests/test_kmeans_keypoint_deviation.py
```

## Dependencies

- **scikit-learn**: K-means clustering implementation
- **numpy**: Array operations and distance calculations
- **dearpygui**: UI components

Added to `requirements.txt`:
```
scikit-learn
```

## Performance

- **Training**: O(n * k * i * d) where:
  - n = number of samples
  - k = number of clusters (2)
  - i = number of iterations
  - d = number of dimensions (flattened keypoint size)
  
- **Classification**: O(k * d) - very fast once trained

Memory usage scales with buffer size (max 300 samples).

## Security

✅ CodeQL Analysis: 0 alerts
✅ Dependency Check: No vulnerabilities in scikit-learn
✅ Input Validation: All inputs validated before use
✅ No resource leaks or unsafe operations

## Future Enhancements

Possible improvements:
1. Incremental learning to reduce memory usage
2. Support for more than 2 clusters
3. Different distance metrics (Manhattan, Cosine)
4. Confidence scores for predictions
5. Visualization of clusters
6. Auto-tuning of threshold based on cluster separation
