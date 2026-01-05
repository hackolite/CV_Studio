# ReId Node - Player Re-Identification

## Overview

The ReId (Re-Identification) node is a tracking enhancement node that assigns consistent identities to detected objects (players, people, etc.) across video frames using K-means clustering on visual features.

## Location
- **Domain**: Tracking
- **File**: `node/TrackerNode/node_reid.py`
- **Style**: Blue pastel (Tracking domain color)

## Features

### 1. Slot Management
- **Add Slot**: Create new identity slots with default names (player1, player2, etc.)
- **Remove Slot**: Remove the most recent slot
- **Custom Naming**: Users can rename slots to any desired name (e.g., "Team A Captain", "Player #10")
- **Maximum Slots**: Supports up to 20 different identities

### 2. K-means Clustering
- **Training Phase**: Collects visual features from the first 100 frames
- **Feature Extraction**: Uses color histograms (16 bins per RGB channel = 48-dimensional feature vector)
- **Automatic Clustering**: Trains K-means with K = number of slots after 100 frames
- **Robust**: Handles edge cases like invalid bounding boxes and out-of-bounds detections

### 3. Re-Identification
- **Centroid Matching**: After training, assigns each detected object to the nearest centroid
- **Consistent Labeling**: Maintains stable identities across frames
- **JSON Output**: Provides `reid_labels` (numeric) and `reid_names` (custom names) in output JSON

### 4. Visualization
- **Bounding Boxes**: Draws colored boxes around detected objects
- **Name Labels**: Displays custom names and confidence scores
- **Color Coding**: Each identity gets a consistent color based on its name

## Inputs

### Input 1: IMAGE
- **Type**: IMAGE
- **Description**: Input video frame (typically from a camera or video source)
- **Format**: BGR color image (NumPy array)

### Input 2: JSON (Tracking Data)
- **Type**: JSON
- **Description**: Tracking data from a MOT (Multi-Object Tracking) node
- **Required Fields**:
  - `track_ids`: List of track IDs
  - `bboxes`: List of bounding boxes [x1, y1, x2, y2]
  - `scores`: List of detection confidence scores
  - `class_ids`: List of class IDs
  - `class_names`: List of class names

## Outputs

### Output 1: IMAGE
- **Type**: IMAGE
- **Description**: Annotated image with ReId labels and bounding boxes
- **Format**: BGR color image (NumPy array)

### Output 2: TIME_MS (optional)
- **Type**: TIME_MS
- **Description**: Processing time in milliseconds
- **Condition**: Only available if `use_pref_counter` is enabled

### Output 3: JSON
- **Type**: JSON
- **Description**: Extended tracking data with ReId labels
- **Additional Fields**:
  - `reid_labels`: List of numeric identity labels (1, 2, 3, ...)
  - `reid_names`: List of custom identity names ("player1", "player2", ...)
- **Inherited Fields**: All fields from input JSON are passed through

## Usage Example

### Basic Pipeline
```
Video/Camera → Object Detection → Multi-Object Tracking → ReId → Display/Record
```

### Configuration Steps
1. **Add ReId Node**: Drag and drop the ReId node from the Tracking category
2. **Connect Inputs**:
   - Connect video source to IMAGE input
   - Connect MOT node JSON output to JSON input
3. **Configure Slots**:
   - Add slots for the expected number of identities
   - Rename slots to meaningful names (optional)
4. **Training Phase**: Let the video run for 100 frames to train K-means
5. **Production Phase**: After training, the node will assign consistent identities

## Algorithm Details

### Feature Extraction
For each detected bounding box:
1. Extract the region of interest (ROI) from the frame
2. Compute color histograms for each channel (B, G, R)
3. Normalize histograms to sum to 1
4. Concatenate into a 48-dimensional feature vector

### K-means Training
After collecting features from 100 frames:
1. Set K = number of slots
2. Train K-means clustering on all collected features
3. Store cluster centroids for later matching

### Identity Assignment
For each new detection:
1. Extract feature vector
2. Calculate Euclidean distance to all centroids
3. Assign to the nearest centroid
4. Use slot name for that centroid

## Limitations and Considerations

1. **Training Requirement**: Needs 100 frames to train, during which identities are not assigned
2. **Visual Features**: Uses only color information; may struggle with similar-looking objects
3. **Static Slots**: Number of slots should be set before training; changing slots requires retraining
4. **Occlusion**: May re-assign identities after long occlusions or scene changes
5. **Lighting Changes**: Significant lighting changes may affect feature matching

## Configuration Settings

The node inherits settings from `opencv_setting_dict`:
- `process_width`: Width for display preview
- `process_height`: Height for display preview
- `use_pref_counter`: Enable/disable performance timing

## Testing

Run the test suite:
```bash
python -m pytest tests/test_reid_node.py -v
```

Test coverage includes:
- Node creation and initialization
- Feature extraction (valid, invalid, out-of-bounds bboxes)
- K-means training (sufficient/insufficient samples)
- Centroid assignment
- Color generation
- Slot name management

## Future Enhancements

Potential improvements:
- Deep learning features (ResNet, OSNet) for better accuracy
- Dynamic slot addition during runtime
- Appearance model updates over time
- Multi-camera re-identification
- Integration with tracking confidence scores

## Dependencies

- `numpy`: Numerical operations
- `opencv-python`: Image processing
- `scikit-learn`: K-means clustering
- `dearpygui`: UI components

## Version History

- **v0.0.1** (2026-01-05): Initial implementation
  - Basic K-means clustering
  - Slot management
  - Color histogram features
  - JSON input/output
