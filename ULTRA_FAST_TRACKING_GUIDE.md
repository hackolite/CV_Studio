# Ultra-Fast Tracking Methods for Tennis and Sports

## Overview
This document describes the two new ultra-fast tracking methods added to CV_Studio, specifically optimized for tennis and fast-moving sports scenarios: **OC-SORT** and **BoT-SORT**.

## New Tracking Methods

### 1. OC-SORT (Observation-Centric SORT)

**Key Features:**
- **Observation-centric momentum**: Handles occlusions better by using historical observations
- **Virtual trajectory**: Predicts object positions during temporary occlusions
- **Fast processing**: Optimized for real-time tracking with minimal computational overhead
- **Ideal for tennis**: Handles fast-moving balls and players with quick direction changes

**Technical Details:**
- Based on the paper: "Observation-Centric SORT: Rethinking SORT for Robust Multi-Object Tracking" (2022)
- Uses Kalman filtering with observation history for better prediction
- Delta_t parameter (default: 3) controls how many past observations are used for momentum calculation
- Higher max_age (default: 30) keeps tracks alive longer during occlusions

**Usage in CV_Studio:**
Select "OC-SORT" from the tracking method dropdown in the MultiObjectTracking node.

**Parameters:**
- `max_age`: Maximum frames to keep a track alive without detection (default: 30)
- `min_hits`: Minimum detections before confirming a track (default: 3)
- `iou_threshold`: IoU threshold for matching (default: 0.3)
- `delta_t`: Time steps for observation-centric momentum (default: 3)

**Advantages for Tennis:**
- Handles rapid direction changes (serves, volleys)
- Maintains tracking during brief occlusions (net crossing, player overlap)
- Low latency for real-time tracking
- Robust to fast ball speeds

### 2. BoT-SORT (Robust Associations Multi-Pedestrian Tracking)

**Key Features:**
- **GIoU matching**: Uses Generalized IoU for better association of non-overlapping boxes
- **Two-stage association**: Separates high-confidence and low-confidence detections
- **Velocity smoothing**: Uses smoothed velocity for stable predictions
- **Confidence tracking**: Maintains track confidence scores over time

**Technical Details:**
- Based on the paper: "BoT-SORT: Robust Associations Multi-Pedestrian Tracking" (2022)
- Implements two-stage cascade matching for better accuracy
- Uses GIoU instead of IoU for improved non-overlapping box matching
- Confidence decay during occlusion helps manage track quality

**Usage in CV_Studio:**
Select "BoT-SORT" from the tracking method dropdown in the MultiObjectTracking node.

**Parameters:**
- `max_age`: Maximum frames to keep a track alive without detection (default: 30)
- `min_hits`: Minimum detections before confirming a track (default: 3)
- `iou_threshold`: IoU threshold for matching (default: 0.3)
- `use_giou`: Use GIoU instead of IoU (default: True)

**Advantages for Tennis:**
- Better handles players at different court positions (non-overlapping)
- Two-stage matching improves accuracy for both ball and player tracking
- Smoothed velocity predictions reduce jitter
- Confidence-based filtering reduces false positives

## Performance Comparison

| Feature | OC-SORT | BoT-SORT | SORT | ByteTrack |
|---------|---------|----------|------|-----------|
| Speed | ⚡⚡⚡ Very Fast | ⚡⚡⚡ Very Fast | ⚡⚡⚡ Very Fast | ⚡⚡ Fast |
| Occlusion Handling | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Good | ⭐⭐⭐ Excellent |
| Non-overlapping Objects | ⭐⭐ Good | ⭐⭐⭐ Excellent | ⭐⭐ Good | ⭐⭐ Good |
| Fast Motion | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Good | ⭐⭐ Good |
| Tennis Ball Tracking | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Good | ⭐⭐ Good |
| Player Tracking | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Good | ⭐⭐⭐ Excellent |

## When to Use Each Tracker

### Use OC-SORT when:
- Tracking fast-moving objects (tennis balls, shuttlecocks)
- Objects frequently change direction
- Brief occlusions are common
- You need minimal latency
- Memory of past observations is important

### Use BoT-SORT when:
- Tracking multiple players/objects at varying distances
- Objects don't overlap much
- You want confidence-based track management
- Need robust association with non-overlapping boxes
- Tracking both small (ball) and large (players) objects

## Implementation Details

Both trackers are implemented as multi-class wrappers, meaning they can track different object classes simultaneously (e.g., ball, player 1, player 2).

**File Structure:**
```
node/TrackerNode/mot/
├── ocsort/
│   ├── __init__.py
│   ├── ocsort_tracker.py      # Core OC-SORT algorithm
│   └── mc_ocsort.py            # Multi-class wrapper
└── botsort/
    ├── __init__.py
    ├── botsort_tracker.py      # Core BoT-SORT algorithm
    └── mc_botsort.py            # Multi-class wrapper
```

## Integration

The trackers are automatically available in the MultiObjectTracking node after implementation. No additional dependencies are required beyond the existing `filterpy` package.

To use:
1. Add a MultiObjectTracking node to your workflow
2. Connect it to an ObjectDetection node
3. Select "OC-SORT" or "BoT-SORT" from the dropdown
4. Process your video

## References

1. **OC-SORT**: Cao, J., et al. (2022). "Observation-Centric SORT: Rethinking SORT for Robust Multi-Object Tracking." arXiv:2203.14360
2. **BoT-SORT**: Aharon, N., et al. (2022). "BoT-SORT: Robust Associations Multi-Pedestrian Tracking." arXiv:2206.14651

## License

Both implementations are released under the MIT license, consistent with the original papers and CV_Studio's licensing.
