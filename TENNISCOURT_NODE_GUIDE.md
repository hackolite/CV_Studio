# TennisCourt Visual Node Guide

## Overview

The **TennisCourt Visual Node** is a visualization node that draws a tennis court diagram with transformed points from homography calculations. It accepts homography data (including the tennis court template and transformed points) and creates a visual representation of the court with the points plotted on it.

**Improvements inspired by Tennis-Tracker** (https://github.com/abhroroy365/Tennis-Tracker):
- ✅ Red keypoint circles at court corners for better visual reference
- ✅ Blue net line at center of court (horizontal divider)
- ✅ White player/object markers for high contrast visibility
- ✅ Enhanced visualization style similar to professional tennis tracking systems

## Location

**Menu:** `Visual` → `TennisCourt`

## Purpose

The TennisCourt node:
1. Takes homography output data from the Homography node
2. Draws a tennis court diagram based on the court template
3. Plots transformed points (e.g., player positions) on the court visualization
4. Outputs both the visualization image and passes through the JSON data with visualization metadata

## Node Type

**Category:** Visual (VisualNode)

## Inputs

### Input 1: Homography JSON
- **Purpose:** Accepts homography output data containing the court template and transformed points
- **Source:** Typically from a Homography node
- **Format:** JSON containing:
  - `template`: Tennis court template with keypoints in meters
  - `transformed_points`: Points transformed to real-world coordinates
  - `homography_matrix`: The transformation matrix (optional for visualization)
  - `input_points`: Original points in image space (optional)

**Example input:**
```json
{
  "homography_matrix": [[...], [...], [...]],
  "template": {
    "units": "meters",
    "origin": "bottom_left_corner_outside_doubles",
    "keypoints": [
      {"id": 1, "name": "doubles_bl", "x": 0.00, "y": 0.00},
      ...
    ]
  },
  "transformed_points": [
    [4.5, 10.5],
    [6.2, 15.3]
  ],
  "input_points": [[350, 300], [420, 200]]
}
```

## Outputs

### Output 1: Visualization Image
- **Purpose:** Tennis court diagram with transformed points plotted
- **Format:** Image (OpenCV format)
- **Description:** Shows:
  - Green court background
  - White court lines (doubles, singles, service boxes, center line)
  - **Blue net line at center of court** (inspired by Tennis-Tracker)
  - **Red keypoint circles** at all 14 court corner positions (inspired by Tennis-Tracker)
  - **White circles** marking transformed player/object positions
  - Point indices labeled next to each transformed point

### Output 2: Enhanced JSON
- **Purpose:** Passes through the input JSON data with added visualization metadata
- **Format:** JSON with additional `visualization` field
- **Content:** Original homography data plus:
  - `scale`: Pixels per meter used for visualization
  - `offset_x`, `offset_y`: Court position offsets in the image
  - `image_width`, `image_height`: Visualization dimensions

**Example output:**
```json
{
  "homography_matrix": [[...], [...], [...]],
  "template": {...},
  "transformed_points": [[4.5, 10.5], [6.2, 15.3]],
  "input_points": [[350, 300], [420, 200]],
  "visualization": {
    "scale": 29.17,
    "offset_x": 140,
    "offset_y": 53,
    "image_width": 600,
    "image_height": 800
  }
}
```

### Output 3: Elapsed Time (ms)
- Processing time in milliseconds (when performance counter is enabled)

## Visualization Details

### Tennis Court Drawing

The court is drawn with standard tennis court dimensions:
- **Doubles court:** 10.97m × 23.77m
- **Singles court:** 8.23m × 23.77m
- **Service boxes:** From baseline to 5.485m
- **Center line:** Divides service boxes
- **Net line:** Blue horizontal line at center (11.88m from each baseline)

**Visual elements:**
- Green background for court surface
- White lines for court boundaries and markings
- **Blue net line** at center of court (inspired by Tennis-Tracker)
- **Red keypoint circles** (5px radius) at all 14 court positions (inspired by Tennis-Tracker)
- Automatic scaling to fit the visualization window
- Centered court positioning with margins

### Point Visualization

Transformed points are drawn as:
- **White filled circles** (5px radius) for high contrast visibility
- **Numerical labels** showing point index in white
- Points positioned according to their real-world coordinates (in meters)
- Excellent visibility against the green court background

## Usage Pipeline

### Basic Pipeline
```
PoseEstimation → Homography → TennisCourt
                                    ↓
                              Visualization
```

### Complete Example
```
1. Video Input → PoseEstimation (TennisKeyPoints)
                        ↓
2. Detected Keypoints → Homography (calculates transformation)
                            ↓
3. Player Detection → Homography (transforms player positions)
                          ↓
4. Homography Output → TennisCourt (visualizes court + players)
                            ↓
                      Court diagram with player positions
```

## How It Works

### 1. Input Processing
- Receives homography JSON data
- Extracts tennis court template
- Retrieves transformed points in real-world coordinates

### 2. Coordinate Calculation
- Calculates optimal scale to fit court in visualization window
- Determines court position offsets for centering
- Maintains aspect ratio of tennis court

### 3. Court Drawing
- Draws green background for court surface
- Renders doubles boundary rectangle
- Renders singles boundary rectangle
- Draws service line boundaries
- Draws center line and center T markings

### 4. Points Drawing
- Converts each transformed point from meters to pixel coordinates
- Draws colored circle at each position
- Adds index label for identification

### 5. Output Generation
- Creates visualization image
- Enhances input JSON with visualization metadata
- Returns both image and JSON outputs

## Configuration

The node has no user-configurable parameters. All settings are automatic:
- **Scale:** Calculated to fit court in window (typically 20-40 px/meter)
- **Offsets:** Calculated to center court in window
- **Colors:** Fixed (green court, white lines, red points)
- **Point size:** Fixed (8px radius circles)

## Use Cases

### 1. Player Position Analysis
- **Application:** Visualize where players are positioned on the court
- **Pipeline:** Court detection → Player tracking → Homography → TennisCourt
- **Output:** Court diagram showing real-time player positions

### 2. Heatmap Preparation
- **Application:** Prepare coordinate data for movement heatmaps
- **Pipeline:** Tracking → Homography → TennisCourt → Data export
- **Output:** Visual reference with coordinate overlay

### 3. Tactical Analysis
- **Application:** Study court coverage and positioning strategies
- **Pipeline:** Video replay → Position extraction → Visualization
- **Output:** Court diagrams showing player movement patterns

### 4. Training Feedback
- **Application:** Show athletes their court positioning in real-world coordinates
- **Pipeline:** Live video → Real-time transformation → Court display
- **Output:** Immediate visual feedback on court positioning

## Technical Details

### Coordinate System
- **Origin:** Bottom-left corner of doubles court
- **Units:** Meters
- **X-axis:** Court width (0 to 10.97m)
- **Y-axis:** Court length (0 to 23.77m)

### Scaling Algorithm
```python
scale_x = (window_width - margins) / court_width_meters
scale_y = (window_height - margins) / court_length_meters
scale = min(scale_x, scale_y)  # Preserve aspect ratio
```

### Drawing Order
1. Green court background
2. White court lines (from outer to inner)
3. Service lines and center markings
4. Transformed points with labels

## Requirements

- **Input:** Valid homography JSON from Homography node
- **Template:** Tennis court template with 14 keypoints
- **Transformed Points:** List of [x, y] coordinates in meters

## Testing

Comprehensive tests are provided:

```bash
# Unit tests for drawing functions
python tests/test_tennis_court_node.py

# Integration test with Homography node
python tests/test_tennis_court_integration.py
```

**Tests include:**
- Node import and structure validation
- Tennis court drawing on blank image
- Transformed points visualization
- Complete pipeline from Homography to TennisCourt
- Output validation (image and JSON structure)

## Limitations

1. **Fixed Court Type:** Currently supports tennis courts only
2. **2D Visualization:** No 3D perspective or camera angle adjustment
3. **Fixed Colors:** Court and point colors are hardcoded
4. **Point Style:** Single visualization style for all points
5. **Label Format:** Simple numeric indices only

## Future Enhancements

Possible improvements:
- Configurable court colors and line thickness
- Support for different sports courts (basketball, volleyball, etc.)
- Point color mapping based on metadata (team, player ID, etc.)
- Trail visualization for player movement over time
- Zone highlighting (service boxes, backcourt, etc.)
- Customizable point styles and labels
- Animation support for temporal data
- 3D perspective visualization option

## Troubleshooting

### No Visualization Output
- **Issue:** Output image is None or blank
- **Solution:** Ensure Homography node is connected and providing valid template data

### Court Not Visible
- **Issue:** Court is outside the visualization window
- **Solution:** The node automatically scales and centers; check if template data is valid

### Points Not Showing
- **Issue:** Transformed points not visible on court
- **Solution:** 
  - Verify Homography node is transforming points correctly
  - Check that transformed_points array is not empty
  - Ensure point coordinates are within court bounds (0-11m × 0-24m)

### Wrong Court Dimensions
- **Issue:** Court proportions look incorrect
- **Solution:** The court uses official tennis dimensions; if input template is modified, it may not scale correctly

## Performance

- **Typical processing time:** < 5ms per frame
- **Memory usage:** Minimal (single image buffer + template data)
- **Scalability:** Can visualize unlimited points (though readability decreases)
- **Real-time capable:** Yes, suitable for live video processing

## Related Nodes

- **Homography:** Provides the homography data and transformed points
- **CourtKeypointData:** Pre-processes keypoints before homography
- **PoseEstimation:** Detects tennis court keypoints for homography calculation
- **ObjectDetection:** Can provide player positions for transformation
- **VideoWriter:** Can record the visualization for later analysis
- **ImageConcat:** Can combine court visualization with original video

## Example Workflow

```
1. Load video of tennis match
2. Run TennisKeyPoints pose estimation to detect court
3. Feed court keypoints to Homography node (Input 1)
4. Run YOLOv8 to detect players
5. Feed player bounding boxes to Homography node (Input 2)
6. Connect Homography output to TennisCourt node
7. View real-time court visualization with player positions
8. Optional: Save visualization with VideoWriter
```

## See Also

- [Homography Node Guide](HOMOGRAPHY_NODE_GUIDE.md)
- [Keypoints Nodes Guide](KEYPOINTS_NODES_GUIDE.md)
- [Visual Nodes Overview](node/VisualNode/README.md)
- [Tennis Court Detection Models](node/DLNode/pose_estimation/tennis_keypoints/)
