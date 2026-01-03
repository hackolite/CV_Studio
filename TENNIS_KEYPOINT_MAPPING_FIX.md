# Tennis Keypoint Mapping Verification

## Problem Statement

The TennisKeyPoints pose estimation model outputs 14 keypoints in a specific order representing tennis court lines and corners. Previously, the Homography node used a different keypoint ordering and naming convention, which caused incorrect mapping between detected keypoints and real-world court coordinates.

## Model Output Format

The TennisKeyPoints pose estimation model outputs keypoints in the following order:

```
Index | Keypoint Name                           | Description
------+-----------------------------------------+------------------------------------
    0 | far_baseline_left_single_corner         | Top-left singles corner (far from camera)
    1 | far_baseline_right_single_corner        | Top-right singles corner (far from camera)
    2 | near_baseline_left_double_corner        | Bottom-left doubles corner (near camera)
    3 | near_baseline_right_double_corner       | Bottom-right doubles corner (near camera)
    4 | far_baseline_left_service_projection    | Top-left service line intersection
    5 | near_baseline_left_single_corner        | Bottom-left singles corner (near camera)
    6 | far_baseline_right_service_projection   | Top-right service line intersection
    7 | near_baseline_right_single_corner       | Bottom-right singles corner (near camera)
    8 | service_box_left_top_corner             | Near-left service line (bottom service box)
    9 | service_box_right_top_corner            | Near-right service line (bottom service box)
   10 | left_singles_sideline_midpoint          | Left singles sideline at net position
   11 | right_singles_sideline_midpoint         | Right singles sideline at net position
   12 | center_service_line_top_T               | Center T at far service line
   13 | center_service_line_bottom_T            | Center T at near service line
```

## Tennis Court Coordinates

The template uses the following coordinate system:
- **Origin**: Bottom-left corner of doubles court (0, 0)
- **Units**: Meters
- **X-axis**: Court width (0 to 10.97m for doubles width)
- **Y-axis**: Court length (0 to 23.77m from near to far baseline)

Standard tennis court dimensions:
- Doubles court width: 10.97 m
- Full court length: 23.77 m
- Singles court width: 8.23 m (1.37 m from each doubles sideline)
- Service line distance from baseline: 5.485 m
- Net position: 11.885 m from each baseline (center of court)

## Real-World Coordinates Mapping

```
Index | Keypoint Name                           | X (m)  | Y (m)   | Position on Court
------+-----------------------------------------+--------+---------+------------------------
    0 | far_baseline_left_single_corner         |   1.37 |   23.77 | Top-left singles
    1 | far_baseline_right_single_corner        |   9.60 |   23.77 | Top-right singles
    2 | near_baseline_left_double_corner        |   0.00 |    0.00 | Bottom-left doubles
    3 | near_baseline_right_double_corner       |  10.97 |    0.00 | Bottom-right doubles
    4 | far_baseline_left_service_projection    |   1.37 |   18.29 | Top-left service
    5 | near_baseline_left_single_corner        |   1.37 |    0.00 | Bottom-left singles
    6 | far_baseline_right_service_projection   |   9.60 |   18.29 | Top-right service
    7 | near_baseline_right_single_corner       |   9.60 |    0.00 | Bottom-right singles
    8 | service_box_left_top_corner             |   1.37 |    5.49 | Near-left service
    9 | service_box_right_top_corner            |   9.60 |    5.49 | Near-right service
   10 | left_singles_sideline_midpoint          |   1.37 |   11.89 | Left net position
   11 | right_singles_sideline_midpoint         |   9.60 |   11.89 | Right net position
   12 | center_service_line_top_T               |   5.49 |   18.29 | Far center T
   13 | center_service_line_bottom_T            |   5.49 |    5.49 | Near center T
```

## Visual Court Layout

```
                    FAR BASELINE (Top, Y=23.77m)
    ┌────────────────────────────────────────────────────────┐
    │  0                      12                      1     │ ← Far singles baseline
    │  ├───────────────────────┼───────────────────────┤     │
    │  4                                              6     │ ← Far service line (Y=18.285m)
    │                                                        │
    │  10                                            11     │ ← Net (Y=11.885m)
    │                                                        │
    │  8                      13                      9     │ ← Near service line (Y=5.485m)
    │  ├───────────────────────┼───────────────────────┤     │
    │  5                                              7     │ ← Near singles baseline
    ├══2══════════════════════════════════════════════3═════┤ ← Near doubles baseline (Y=0)
    
    Left (X=0)            Center (X=5.485)          Right (X=10.97)
```

## Changes Made

### 1. Homography Node Template (`node/StatsNode/node_homography.py`)

**Before**: Template used generic abbreviations (doubles_bl, singles_tr, etc.) in an arbitrary order.

**After**: Template now uses descriptive names matching the TennisKeyPoints model output, in the exact order the model returns them (indices 0-13).

Key changes:
- Reordered keypoints to match model output
- Renamed keypoints to match model naming convention
- Added comments with index numbers for clarity
- Updated coordinates to match official tennis court dimensions

### 2. TennisCourt Visualization Node (`node/VisualNode/node_tennis_court.py`)

**Before**: Drawing functions referenced old keypoint names (doubles_bl, singles_tr, etc.).

**After**: Drawing functions updated to use new keypoint names from the updated template.

Key changes:
- Updated all keypoint name references
- Modified drawing logic to work with new structure
- Maintained all visualization features (court lines, net, keypoints)

### 3. Test Files

Updated test files to use the new keypoint naming convention:
- `tests/test_homography_node.py` - Updated template validation
- `tests/test_tennis_court_node.py` - Updated mock template data
- `tests/test_keypoint_mapping_structure.py` - NEW: Structure validation test
- `tests/test_tennis_keypoints_mapping.py` - NEW: Full integration test

## Benefits

1. **Correct Homography Calculation**: The homography matrix now correctly maps detected keypoints to real-world coordinates.

2. **Accurate Visualization**: The TennisCourt node draws the court correctly with proper keypoint placement.

3. **Maintainability**: Descriptive keypoint names make the code self-documenting.

4. **Compatibility**: The mapping matches the TennisKeyPoints model output specification.

## Verification

Run the structure verification test:
```bash
python tests/test_keypoint_mapping_structure.py
```

Expected output:
```
✓ Testing template structure in node_homography.py
  ✓ All 14 keypoint names found in template
  Found 14 keypoints in template
  ✓ All keypoints in correct order

✓ Testing visualization node uses new keypoint names
  Found 10/10 new keypoint names
  ✓ Visualization node updated to use new keypoint names
```

## Usage Example

```python
# The PoseEstimation node outputs keypoints in the correct order
pose_output = {
    'model_name': 'TennisKeyPoints',
    'results_list': detected_keypoints  # numpy array of shape (14, 2)
}

# The Homography node automatically matches these with the template
# No manual reordering needed!
homography_output = homography_node.update(
    node_id=3,
    connection_list=[
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01']
    ],
    node_image_dict={},
    node_result_dict={'1:PoseEstimation': pose_output},
    node_audio_dict={}
)

# The TennisCourt node visualizes using the correct keypoint positions
court_visualization = tennis_court_node.update(
    node_id=4,
    connection_list=[
        ['3:Homography:JSON:Output01', '4:TennisCourt:JSON:Input01']
    ],
    node_image_dict={},
    node_result_dict={'3:Homography': homography_output['json']},
    node_audio_dict={}
)
```

## References

- Official tennis court dimensions: ITF Rules of Tennis
- TennisKeyPoints model: Custom pose estimation model for tennis court detection
- Homography transformation: OpenCV cv2.findHomography()
