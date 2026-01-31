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
- **Input Image** (TYPE_IMAGE, optional): Background image to overlay the heatmap on. When connected, the heatmap is blended with the input image (40% input, 60% heatmap). This input also displays the connected image for preview.
- **Input detection JSON** (TYPE_JSON): JSON data from object detection nodes containing:
  - `bboxes`: List of bounding boxes [x1, y1, x2, y2]
  - `scores`: Detection confidence scores
  - `class_ids`: (optional) Class IDs for each detection
  - `class_names`: (optional) Mapping of class IDs to names

## Outputs
- **Output Image** (TYPE_IMAGE): Heatmap visualization in JET colormap (blue=cold, red=hot)
- **Elapsed Time** (TYPE_TIME_MS): Processing time in milliseconds (if enabled)

## Parameters
- **Class**: Filter heatmap by object class
  - "All": Show all detected objects
  - "0"-"9": Show only objects of the selected class
  - Default: "All"
- **Decay**: Temporal decay factor (0.5 to 0.99)
  - Higher values (0.95-0.99): Longer memory, slower fade
  - Lower values (0.5-0.8): Shorter memory, faster fade
  - Default: 0.95

## How It Works
1. Optionally receives background image from video/camera input nodes (displays the input image)
2. Receives detection data from object detection nodes (e.g., ObjectDetection, YOLO)
3. For each detection:
   - Filters by selected class (if not "All")
   - Adds the detection score to the corresponding bounding box region
4. Applies temporal decay to previous heatmap values
5. Normalizes and applies Gaussian blur for smooth visualization
6. Applies JET colormap for final visualization
7. If input image is connected, blends the heatmap with the input image for context

## Example Usage
```
# Basic heatmap without background
VideoInput → ObjectDetection → ObjHeatmap → VideoOutput

# Heatmap with video background overlay
VideoInput → (split) → ObjectDetection → ObjHeatmap → VideoOutput
           ↓                              ↑
           └──────────────────────────────┘
```

## Implementation Details
- Input image is displayed in the node for preview when connected
- When input image is provided, the heatmap is blended with it (40% original, 60% heatmap)
- Uses exponential decay for temporal smoothing
- Gaussian blur (25x25 kernel) for smooth appearance
- JET colormap: blue (low activity) → green → yellow → red (high activity)
- Automatically clips coordinates to image bounds
- Handles empty detection lists gracefully
- Supports grayscale and color images (automatically converts to BGR)

## Visual Examples
See `/tmp/obj_heatmap_*.png` for test-generated examples:
- `obj_heatmap_basic.png`: Static detections
- `obj_heatmap_motion.png`: Moving detections with trail effect
- `obj_heatmap_accumulation.png`: Accumulation over multiple frames

## Notes
- The heatmap accumulates continuously, so areas with frequent detections become "hotter"
- The decay parameter controls how quickly old detections fade away
- Works with any object detection node that outputs JSON in the expected format
