# ObjHeatmap Node Documentation

## Description
The **ObjHeatmap** node creates a temporal heatmap visualization based on object detection data. It accumulates detection locations over time with a configurable decay factor, creating a "heat trail" effect that shows where objects are frequently detected.

## Purpose
This node is useful for:
- Analyzing object movement patterns in video feeds
- Identifying high-activity zones
- Visualizing traffic patterns
- Understanding spatial distribution of detected objects over time

## Inputs
- **Input detection JSON** (TYPE_JSON): JSON data from object detection nodes containing:
  - `bboxes`: List of bounding boxes [x1, y1, x2, y2]
  - `scores`: Detection confidence scores
  - `class_ids`: (optional) Class IDs for each detection
  - `class_names`: (optional) Mapping of class IDs to names

## Outputs
- **Output Image** (TYPE_IMAGE): Heatmap visualization in JET colormap (blue=cold, red=hot)
- **Elapsed Time** (TYPE_TIME_MS): Processing time in milliseconds (if enabled)

## Parameters
- **Decay**: Temporal decay factor (0.5 to 0.99)
  - Higher values (0.95-0.99): Longer memory, slower fade
  - Lower values (0.5-0.8): Shorter memory, faster fade
  - Default: 0.95

## How It Works
1. Receives detection data from object detection nodes (e.g., ObjectDetection, YOLO)
2. For each detection:
   - Adds the detection score to the corresponding bounding box region
3. Applies temporal decay to previous heatmap values
4. Normalizes and applies Gaussian blur for smooth visualization
5. Applies JET colormap for final visualization

## Example Usage
```
VideoInput → ObjectDetection → ObjHeatmap → VideoOutput
```

## Implementation Details
- Uses exponential decay for temporal smoothing
- Gaussian blur (25x25 kernel) for smooth appearance
- JET colormap: blue (low activity) → green → yellow → red (high activity)
- Automatically clips coordinates to image bounds
- Handles empty detection lists gracefully

## Visual Examples
See `/tmp/obj_heatmap_*.png` for test-generated examples:
- `obj_heatmap_basic.png`: Static detections
- `obj_heatmap_motion.png`: Moving detections with trail effect
- `obj_heatmap_accumulation.png`: Accumulation over multiple frames

## Notes
- The heatmap accumulates continuously, so areas with frequent detections become "hotter"
- The decay parameter controls how quickly old detections fade away
- Works with any object detection node that outputs JSON in the expected format
