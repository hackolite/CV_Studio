# Homography Node Guide

## Overview

The **Homography Node** is a data processing node that calculates and applies homography transformations to convert image coordinates to real-world coordinates. It's primarily designed for sports analytics (e.g., tennis court tracking) where detected keypoints from a camera view need to be mapped to actual court coordinates.

## Location

**Menu:** `DataProcess` → `Homography`

## Purpose

The Homography node:
1. Takes detected keypoints from pose estimation (court corners/lines detection)
2. Calculates a homography matrix that maps image coordinates to real-world coordinates
3. Transforms player positions (or any other points) from image space to real-world space
4. Outputs both the transformed coordinates and the homography matrix for downstream processing

## Node Type

**Category:** DataProcess (StatsNode)

## Inputs

### Input 1: Master Keypoints (JSON)
- **Purpose:** Keypoints detected from pose estimation used to calculate the homography matrix
- **Source:** Typically from a PoseEstimation node (e.g., TennisKeyPoints model)
- **Format:** JSON containing `results_list` with detected keypoint coordinates
- **Example:**
  ```json
  {
    "model_name": "TennisKeyPoints",
    "score_th": 0.3,
    "results_list": [[x1, y1], [x2, y2], ..., [x14, y14]]
  }
  ```

### Input 2: Points to Transform (JSON)
- **Purpose:** Points (e.g., player positions) to transform from image to real-world coordinates
- **Format:** JSON with keypoints or points array
- **Supported formats:**
  1. Structured keypoints:
     ```json
     {
       "keypoints": [
         {"x": 350, "y": 300},
         {"x": 450, "y": 200}
       ]
     }
     ```
  2. Direct points array:
     ```json
     {
       "points": [[350, 300], [450, 200]]
     }
     ```
  3. Raw array:
     ```json
     [[350, 300], [450, 200]]
     ```

## Outputs

### Output 1: Transformed Data (JSON)
Contains the following fields:

- **`homography_matrix`**: 3x3 transformation matrix (as a list)
- **`template`**: Tennis court template with real-world coordinates in meters
- **`detected_keypoints`**: Original detected keypoints from pose estimation
- **`input_points`**: Points that were provided for transformation
- **`transformed_points`**: Transformed coordinates in real-world units (meters)

**Example output:**
```json
{
  "homography_matrix": [[a, b, c], [d, e, f], [g, h, i]],
  "template": {
    "units": "meters",
    "origin": "bottom_left_corner_outside_doubles",
    "keypoints": [...]
  },
  "detected_keypoints": [[x1, y1], ..., [x14, y14]],
  "input_points": [[350, 300], [450, 200]],
  "transformed_points": [[4.52, 10.57], [6.45, 15.82]]
}
```

### Output 2: Elapsed Time (ms)
- Processing time in milliseconds (when performance counter is enabled)

## Tennis Court Template

The node uses a standard tennis court template with the following dimensions (in meters):

```
Origin: Bottom-left corner of doubles court (outside line)
Units: meters

Court dimensions:
- Doubles width: 10.97 m
- Total length: 23.77 m
- Singles width: 8.23 m (1.37 m from each side)
- Service line distance from baseline: 5.485 m
```

**14 Keypoints:**
1. doubles_bl (0.00, 0.00) - Bottom-left doubles corner
2. doubles_br (10.97, 0.00) - Bottom-right doubles corner
3. doubles_tr (10.97, 23.77) - Top-right doubles corner
4. doubles_tl (0.00, 23.77) - Top-left doubles corner
5. singles_bl (1.37, 0.00) - Bottom-left singles corner
6. singles_br (9.60, 0.00) - Bottom-right singles corner
7. singles_tr (9.60, 23.77) - Top-right singles corner
8. singles_tl (1.37, 23.77) - Top-left singles corner
9. service_bl (1.37, 5.485) - Bottom-left service line
10. service_br (9.60, 5.485) - Bottom-right service line
11. service_tl (1.37, 18.285) - Top-left service line
12. service_tr (9.60, 18.285) - Top-right service line
13. center_t_bottom (5.485, 5.485) - Bottom center T
14. center_t_top (5.485, 18.285) - Top center T

## Usage Pipeline

### Basic Pipeline
```
PoseEstimation (TennisKeyPoints) → Homography
                                         ↓
                    Player Tracker → Homography
```

### Complete Example
```
1. Video Input → PoseEstimation (TennisKeyPoints)
                        ↓
                    Homography (Input 1: Master Keypoints)
                        ↓
2. Video Input → ObjectDetection (Players) → Homography (Input 2: Player Positions)
                                                    ↓
                                          JSON Output with Real-World Coordinates
```

## How It Works

### 1. Homography Calculation
When the node receives master keypoints from pose estimation:
- Extracts the 14 detected keypoint coordinates (image space)
- Matches them with the 14 template coordinates (real-world space)
- Uses OpenCV's `cv2.findHomography()` with RANSAC to calculate the 3x3 transformation matrix
- Stores the matrix for transforming subsequent points

### 2. Point Transformation
When the node receives points to transform:
- Uses the previously calculated homography matrix
- Applies perspective transformation: `H * [x, y, 1]^T`
- Converts homogeneous coordinates back to 2D
- Returns coordinates in meters relative to the court origin

### 3. Output
- Always outputs the homography matrix and template
- Includes transformed points when both inputs are connected
- Maintains the original detected keypoints for reference

## Requirements

- **Minimum Points:** 4 corresponding points (the node uses 14 for better accuracy)
- **OpenCV Version:** Requires OpenCV with `cv2.findHomography()` support
- **Input Alignment:** Master keypoints must match the order in the template

## Use Cases

### 1. Sports Analytics (Tennis)
- **Application:** Track player positions in real-world court coordinates
- **Pipeline:** Court detection → Player tracking → Homography transformation
- **Output:** Player positions in meters for heatmaps, distance calculations, speed analysis

### 2. Court Coverage Analysis
- **Application:** Analyze player movement patterns
- **Pipeline:** TennisKeyPoints → Homography → Position tracking over time
- **Output:** Coverage statistics, movement efficiency metrics

### 3. Ball Trajectory Analysis
- **Application:** Map ball positions to court coordinates
- **Pipeline:** Ball detection → Homography → Trajectory analysis
- **Output:** Landing positions, bounce locations in real coordinates

### 4. Multi-Camera Calibration
- **Application:** Unify coordinates from multiple camera views
- **Pipeline:** Per-camera court detection → Homography → Unified coordinate system
- **Output:** Consistent player positions across camera angles

## Technical Details

### Homography Matrix
- 3x3 matrix that maps image points to real-world points
- Calculated using RANSAC for robustness against outliers
- Uses all 14 keypoints for overdetermined system (better accuracy)

### Transformation Formula
```
[x', y', w']^T = H * [x, y, 1]^T
x_transformed = x' / w'
y_transformed = y' / w'
```

Where:
- (x, y): Image coordinates
- (x', y'): Real-world coordinates after normalization
- H: 3x3 homography matrix
- w': Homogeneous coordinate for normalization

### Error Handling
- Returns `None` for homography_matrix if calculation fails
- Returns `None` for transformed_points if transformation fails
- Requires at least 4 corresponding points
- Validates input data structure before processing

## Configuration

The node has no user-configurable parameters. All settings are automatic:
- Template coordinates are fixed (standard tennis court dimensions)
- Homography calculation uses RANSAC with threshold of 5.0 pixels
- Transformation is automatic when both inputs are connected

## Testing

A comprehensive test suite is provided in `tests/test_homography_node.py`:

```bash
python tests/test_homography_node.py
```

**Tests include:**
- Node import and initialization
- Tennis court template validation
- Homography matrix calculation
- Point transformation accuracy
- Complete node update cycle

## Limitations

1. **Fixed Template:** Currently designed for tennis courts only
2. **Point Count:** Master keypoints must provide exactly 14 points
3. **2D Only:** Does not handle 3D transformations or camera calibration
4. **No Validation:** Does not validate if detected keypoints form a valid court shape

## Future Enhancements

Possible improvements:
- Support for other sports (basketball, soccer, etc.)
- Configurable templates via JSON input
- Inverse transformation (real-world to image coordinates)
- Quality metrics for homography (reprojection error)
- Support for partial keypoint detection (< 14 points)
- Automatic court dimension estimation
- Multi-template support with template selection

## Troubleshooting

### No Output
- **Issue:** Output JSON is `None`
- **Solution:** Ensure Input 1 (Master Keypoints) is connected to a PoseEstimation node

### Invalid Homography Matrix
- **Issue:** `homography_matrix` is `None` in output
- **Solution:** 
  - Verify pose estimation is detecting all 14 keypoints
  - Check that keypoints form a valid court shape
  - Ensure sufficient camera angle (not too oblique)

### Wrong Transformed Coordinates
- **Issue:** Transformed points don't match expected positions
- **Solution:**
  - Verify keypoint detection accuracy in pose estimation
  - Check that the court template matches your court type
  - Ensure consistent keypoint ordering

## Example Code

### Creating Mock Data for Testing

```python
import numpy as np

# Mock detected keypoints (image coordinates)
detected_keypoints = np.array([
    [100, 500], [700, 500], [700, 50], [100, 50],
    [200, 500], [600, 500], [600, 50], [200, 50],
    [200, 400], [600, 400], [200, 150], [600, 150],
    [400, 400], [400, 150],
], dtype=np.float32)

master_json = {
    'model_name': 'TennisKeyPoints',
    'score_th': 0.3,
    'results_list': detected_keypoints
}

# Mock player positions (image coordinates)
player_positions = {
    'keypoints': [
        {'x': 350, 'y': 300},  # Player 1
        {'x': 450, 'y': 200},  # Player 2
    ]
}
```

## Compatibility

- **Works with:** Any pose estimation model that outputs keypoints in `results_list` field
- **Designed for:** TennisKeyPoints and TennisKeyPoints_2 models
- **Compatible with:** All JSON-based data processing nodes
- **Output format:** Standard JSON for use with triggers, routers, overlays, etc.

## Performance

- **Typical processing time:** < 1ms per frame
- **Homography calculation:** One-time per frame (cached for point transformations)
- **Memory usage:** Minimal (stores only 3x3 matrix and template)
- **Scalability:** Can transform unlimited points with same homography matrix

## Related Nodes

- **PoseEstimation:** Provides master keypoints for homography calculation
- **ObjectDetection:** Can provide player/ball positions for transformation
- **CourtKeypointData:** Processes keypoints before homography
- **Position Prediction:** Can use transformed coordinates for trajectory prediction
- **Overlay nodes:** Can visualize transformed coordinates on video

## See Also

- [Keypoints Nodes Guide](KEYPOINTS_NODES_GUIDE.md)
- [Tennis Pose Estimation](node/DLNode/pose_estimation/tennis_keypoints/)
- [OpenCV Homography Documentation](https://docs.opencv.org/master/d9/d0c/group__calib3d.html#ga4abc2ece9fab9398f2e560d53c8c9780)
