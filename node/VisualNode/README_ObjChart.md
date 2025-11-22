# ObjChart Node Documentation

## Overview
The **ObjChart** node is a visualization node that accumulates and displays object detection counts over time. It creates charts showing how many detections of each class occurred in different time periods, with support for multiple visualization types.

## Location
- **Category**: Visual
- **Menu Path**: Visual → ObjChart
- **File**: `node/VisualNode/node_obj_chart.py`

## Purpose
This node is designed to analyze object detection patterns over time by:
- Accumulating detection counts per class with 24-hour round-robin storage
- Grouping data by time buckets (minutes or hours)
- Visualizing trends with dynamic chart type selection (bar, line, or area)
- Supporting multiple class selection for comparison
- Maintaining efficient memory usage with automatic data cleanup

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
- **Description**: Chart visualization as an image
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

### Chart Type Dropdown (NEW)
- **Options**: "bar", "line", or "area"
- **Description**: Choose the visualization type
  - **bar**: Grouped bar chart (default) - best for comparing discrete values
  - **line**: Line chart with markers - best for showing trends over time
  - **area**: Stacked area chart - best for showing cumulative contributions

### Class Selection Slots
- **Initial Slot**: One class selector is created by default
- **Options**: "All", "0", "1", "2", ..., "9"
  - **All**: Shows combined count of all detected classes
  - **0-9**: Shows count for specific class ID
- **Add Class Slot Button**: Click to add additional class selectors
- **Multi-class Display**: Selected classes are shown as separate series with different colors

## Features

### 24-Hour Round-Robin Storage (NEW)
- Automatically stores detection data with a maximum retention of 24 hours
- Memory-efficient: old data is automatically cleaned up
- Data persists when switching between visualization types
- Suitable for long-running monitoring applications

### Time-based Accumulation
- Automatically groups detections into time buckets
- Displays last 30 time buckets in the chart
- Automatically prunes older data from memory after 24 hours

### Dynamic Visualization (NEW)
- Switch between chart types on the fly without losing data
- Bar chart: Grouped bars for side-by-side comparison
- Line chart: Continuous lines with markers for trend analysis
- Area chart: Stacked areas for cumulative view

### Dynamic Class Selection
- Start with one class selector
- Add as many class selectors as needed
- Each class appears as a separate series in the chart

### Chart Visualization
- Clear chart with grid lines
- Rotated time labels for readability
- Legend showing class names (when available)
- Automatic y-axis scaling based on data

## Usage Example

### Basic Setup
1. Add an **ObjectDetection** node to your graph
2. Add an **ObjChart** node
3. Connect ObjectDetection JSON output → ObjChart JSON input
4. Select time unit (minute or hour)
5. Select chart type (bar, line, or area)
6. Select which classes to track (default is "All")

### Multi-class Tracking
1. Click "Add Class Slot" to add more class selectors
2. Set each slot to a different class ID
3. The chart will show separate series for each selected class

### Switching Visualization Types
1. Change the "Chart Type" dropdown at any time
2. Data is preserved when switching between bar, line, and area charts
3. Choose the visualization that best suits your analysis needs

### Video Output
1. Connect ObjChart image output → VideoWriter or ImageConcat
2. The chart updates in real-time as detections accumulate
3. Create time-lapse visualizations of detection patterns

## Technical Details

### Code Structure
- **Base Class**: Inherits from `Chart` (imported from `node.basenode.Node`)
- **Factory Pattern**: Implements FactoryNode for node editor integration

### Data Structure
- **Storage**: `defaultdict(lambda: defaultdict(int))`
- **Keys**: Class ID (int or "All") → Time bucket (datetime) → Count (int)
- **Retention**: 24 hours (1440 minutes) with automatic cleanup
- **Display**: Last 30 time buckets shown in chart

### Time Bucket Calculation
- **Minute buckets**: `datetime.now().replace(second=0, microsecond=0)`
- **Hour buckets**: `datetime.now().replace(minute=0, second=0, microsecond=0)`

### Data Cleanup (NEW)
- **Method**: `cleanup_old_data()`
- **Frequency**: Called on every update cycle
- **Criteria**: Removes all data older than 24 hours
- **Memory efficiency**: Prevents unlimited memory growth in long-running applications

### Rendering
- Uses matplotlib with 'Agg' backend (no GUI required)
- Chart size: 8x4 inches at 100 DPI (800x400 pixels)
- Converts to BGR format for OpenCV compatibility
- Support for three chart types:
  - **Bar**: `ax.bar()` with grouped bars
  - **Line**: `ax.plot()` with markers
  - **Area**: `ax.stackplot()` with alpha blending

## Limitations

- Maximum of 30 time buckets displayed (configured via `max_buckets`)
- Data retention limited to 24 hours (configured via `max_data_age_hours`)
- Class selection limited to classes 0-9 in dropdown (can be expanded by modifying code)
- Time buckets are based on system time (not video timestamps)

## Future Enhancements

Potential improvements:
- Support for custom class ID ranges
- Configurable time bucket size
- Export data to CSV
- Cumulative vs. per-bucket count modes
- Custom color schemes
- Adjustable history length and display window
- Video timestamp synchronization

## Testing

Run tests with:
```bash
python -m pytest tests/test_obj_chart_node.py -v
```

Test coverage includes:
- Node import and inheritance verification
- Time bucket calculation
- Chart rendering (bar, line, area)
- Data accumulation
- 24-hour cleanup mechanism

Generate visual test outputs:
```bash
python tests/test_obj_chart_visual.py
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
