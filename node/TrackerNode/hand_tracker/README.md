# Hand Tracking Node

## Overview

The Hand Tracking node is a specialized tracker for hand pose estimation. It tracks multiple hands across video frames and maintains their unique identities over time.

## Features

- **Multi-hand tracking**: Track multiple hands simultaneously
- **Persistent IDs**: Each hand maintains a unique ID across frames
- **Palm-based tracking**: Uses palm center coordinates for robust tracking
- **Automatic cleanup**: Removes hands that disappear for extended periods
- **Compatible with MediaPipe Hands**: Designed to work with MediaPipe Hands pose estimation

## How It Works

The Hand Tracking node uses a simple yet effective tracking algorithm:

1. **Detection Association**: Associates detected hands in the current frame with tracked hands from previous frames based on palm center proximity
2. **ID Assignment**: New hands are assigned unique IDs
3. **ID Persistence**: Hands are tracked across frames, maintaining their IDs even during brief occlusions
4. **Automatic Removal**: Hands that disappear for more than 30 frames are automatically removed from tracking

## Usage

### Basic Pipeline

1. Add an **Input** node (WebCam, Video, or Image)
2. Add a **Pose Estimation** node
   - Select a MediaPipe Hands model (Complexity0 or Complexity1)
3. Add the **Hand Tracking** node
4. Connect:
   - Input → Pose Estimation (image input)
   - Pose Estimation → Hand Tracking (both image and JSON outputs)
5. Add a **Result Image** node and connect Hand Tracking output to visualize results

### Pipeline Example

```
WebCam → Pose Estimation (MediaPipe Hands) → Hand Tracking → Result Image
                ↓                                      ↑
                └──────────────(JSON)─────────────────┘
```

## Node Inputs

- **Input Image**: The video frame (same as pose estimation input)
- **Hand Pose Data (JSON)**: Results from MediaPipe Hands pose estimation node

## Node Outputs

- **Output Image**: Visualization with tracked hands, colored by ID
- **Tracking Results (JSON)**: Contains:
  - `hand_ids`: List of unique hand IDs
  - `tracked_hands`: List of hand data with persistent IDs
  - `model_name`: The pose estimation model used

## Visualization

The Hand Tracking node provides rich visualization:

- **Colored keypoints**: Each tracked hand is drawn in a unique color
- **Skeleton lines**: Finger and palm connections shown
- **ID labels**: Each hand is labeled with its unique ID and handedness (Left/Right)
- **Color palette**: Up to 6 distinct colors for different hands

## Parameters

The tracker has built-in parameters optimized for hand tracking:

- **max_distance**: 100 pixels - Maximum distance to associate hands between frames
- **max_frames_disappeared**: 30 frames - How long to keep tracking a disappeared hand

## Technical Details

### Tracking Algorithm

The tracker uses a greedy matching algorithm:

1. Calculate distances between tracked hand palm centers and detected palm centers
2. Match hands using closest pairs (greedy assignment)
3. Matches with distance > max_distance are rejected
4. Unmatched detections create new tracks
5. Unmatched tracks are marked as disappeared

### Data Flow

```
Input: MediaPipe Hands Results
  ↓
Extract palm centers
  ↓
Match with existing tracks (distance-based)
  ↓
Update matched tracks
  ↓
Create new tracks for unmatched detections
  ↓
Remove old disappeared tracks
  ↓
Output: Tracked hands with persistent IDs
```

## Limitations

- Requires MediaPipe Hands for hand detection (won't work with other pose estimation models)
- Tracking quality depends on the quality of hand detection
- May swap IDs if hands cross or overlap significantly
- Limited to tracking hands based on palm position only

## Future Improvements

Potential enhancements for future versions:

- [ ] Support for other hand pose estimation models
- [ ] More sophisticated matching using full hand pose similarity
- [ ] Configurable tracking parameters via UI
- [ ] Hand gesture recognition integration
- [ ] Trajectory smoothing using Kalman filters

## Example Use Cases

1. **Hand gesture control**: Track hand movements for gesture-based interfaces
2. **Sign language recognition**: Track multiple hands for sign language interpretation
3. **Interactive applications**: Control UI elements with hand movements
4. **Performance analysis**: Analyze hand movements in sports or music performance
5. **Medical applications**: Track hand tremor or range of motion

## Integration with Other Nodes

The Hand Tracking node works seamlessly with:

- **Draw Information**: Add bounding boxes and labels
- **Video Writer**: Record tracked hand movements
- **PutText**: Add custom annotations
- **Image Concat**: Compare with and without tracking

## Version

- **Version**: 0.0.1
- **Node Tag**: HandTracking
- **Node Label**: Hand Tracking

## Author

Part of the CV Studio Tracker Node collection.
