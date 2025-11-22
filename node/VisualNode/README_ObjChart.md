# ObjChart Node Documentation

## Overview
The **ObjChart** node is a visualization node that accumulates and displays object detection counts over time. It creates a bar chart showing how many detections of each class occurred in different time periods.

## Location
- **Category**: Visual
- **Menu Path**: Visual → ObjChart
- **File**: `node/VisualNode/node_obj_chart.py`

## Purpose
This node is designed to analyze object detection patterns over time by:
- Accumulating detection counts per class
- Grouping data by time buckets (minutes or hours)
- Visualizing trends in a bar chart format
- Supporting multiple class selection for comparison

## Inputs

### 1. Input Image (Optional)
- **Type**: IMAGE
- **Description**: Optional image input (not used in current implementation, reserved for future features)

### 2. Input Detection JSON (Required)
- **Type**: JSON
- **Description**: Object detection results from ObjectDetection nodes
- **Expected Format**:
  ```json
  {
    "bboxes": [[x1, y1, x2, y2], ...],
    "scores": [0.95, 0.87, ...],
    "class_ids": [0, 1, 2, ...],
    "class_names": {"0": "person", "1": "car", ...},
    "score_th": 0.3
  }
  ```

## Outputs

### 1. Output Image
- **Type**: IMAGE
- **Description**: Bar chart visualization as an image
- **Format**: BGR color image compatible with other nodes
- **Can connect to**: VideoWriter, ImageConcat, or any image processing node

### 2. Elapsed Time (Optional)
- **Type**: TIME_MS
- **Description**: Processing time in milliseconds (only visible if use_pref_counter is enabled)

## Configuration Options

### Time Unit Dropdown
- **Options**: "minute" or "hour"
- **Description**: Choose the time bucket granularity for accumulation
  - **minute**: Groups detections by minute (format: HH:MM)
  - **hour**: Groups detections by hour (format: HH:00)

### Class Selection Slots
- **Initial Slot**: One class selector is created by default
- **Options**: "All", "0", "1", "2", ..., "9"
  - **All**: Shows combined count of all detected classes
  - **0-9**: Shows count for specific class ID
- **Add Class Slot Button**: Click to add additional class selectors
- **Multi-class Display**: Selected classes are shown as separate bars with different colors

## Features

### Time-based Accumulation
- Automatically groups detections into time buckets
- Maintains history of last 30 time buckets
- Older data is automatically pruned from display

### Dynamic Class Selection
- Start with one class selector
- Add as many class selectors as needed
- Each class appears as a separate bar series in the chart

### Chart Visualization
- Clear bar chart with grid lines
- Rotated time labels for readability
- Legend showing class names (when available)
- Automatic y-axis scaling based on data

## Usage Example

### Basic Setup
1. Add an **ObjectDetection** node to your graph
2. Add an **ObjChart** node
3. Connect ObjectDetection JSON output → ObjChart JSON input
4. Select time unit (minute or hour)
5. Select which classes to track (default is "All")

### Multi-class Tracking
1. Click "Add Class Slot" to add more class selectors
2. Set each slot to a different class ID
3. The chart will show bars for each selected class side-by-side

### Video Output
1. Connect ObjChart image output → VideoWriter or ImageConcat
2. The chart updates in real-time as detections accumulate
3. Create time-lapse visualizations of detection patterns

## Technical Details

### Data Structure
- **Storage**: `defaultdict(lambda: defaultdict(int))`
- **Keys**: Class ID (int or "All") → Time bucket (datetime) → Count (int)
- **Memory**: Automatically limited to last 30 time buckets

### Time Bucket Calculation
- **Minute buckets**: `datetime.now().replace(second=0, microsecond=0)`
- **Hour buckets**: `datetime.now().replace(minute=0, second=0, microsecond=0)`

### Rendering
- Uses matplotlib with 'Agg' backend (no GUI required)
- Chart size: 8x4 inches at 100 DPI (800x400 pixels)
- Converts to BGR format for OpenCV compatibility

## Limitations

- Maximum of 30 time buckets displayed (older data is dropped)
- Class selection limited to classes 0-9 in dropdown (more can be added by modifying the code)
- Time buckets are based on system time (not video timestamps)

## Future Enhancements

Potential improvements:
- Support for custom class ID ranges
- Configurable time bucket size
- Export data to CSV
- Cumulative vs. per-bucket count modes
- Custom color schemes
- Adjustable history length

## Testing

Run tests with:
```bash
python -m pytest tests/test_obj_chart_node.py -v
```

Generate sample visualizations:
```bash
python tests/test_obj_chart_visual.py
```

## Integration

The ObjChart node is automatically discovered by the node editor through:
1. File location in `node/VisualNode/`
2. Registration in `node_editor/style.py` under `VIZ` list
3. `FactoryNode` class implementation for dynamic loading

## Example Workflow

```
WebCam → ObjectDetection → ObjChart → ImageConcat → VideoWriter
                              ↓
                         (Time-based chart
                          showing detection
                          patterns)
```

This creates a video with object detection visualization and a chart showing detection trends over time.
