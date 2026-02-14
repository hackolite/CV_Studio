# Map Node Pan and Zoom Controls

## Overview

The Map visualization node now includes comprehensive pan (translation) and zoom controls for OpenStreetMap rendering. This allows users to interactively explore map views by:
- Zooming in and out
- Panning left, right, up, and down

## Controls

### Zoom Control
- **UI Element**: Slider labeled "Zoom" (1-18)
- **Alternative**: "View Size" slider (0.5-5.0)
  - Values < 1.0: Zoom in (closer view)
  - Values > 1.0: Zoom out (wider view)
- **Default**: 10 (Zoom) or 1.0 (View Size)

### Pan Controls

#### Pan X (Horizontal Translation)
- **UI Element**: Slider labeled "Pan X (Left/Right)"
- **Range**: -1.0 to 1.0
- **Behavior**:
  - Negative values (-1.0 to 0): Pan left (view shifts west, showing more east)
  - Positive values (0 to 1.0): Pan right (view shifts east, showing more west)
- **Default**: 0.0 (centered)

#### Pan Y (Vertical Translation)
- **UI Element**: Slider labeled "Pan Y (Up/Down)"
- **Range**: -1.0 to 1.0
- **Behavior**:
  - Negative values (-1.0 to 0): Pan down (view shifts south, showing more north)
  - Positive values (0 to 1.0): Pan up (view shifts north, showing more south)
- **Default**: 0.0 (centered)

## Usage Example

### Two Boats at Port
The example in `examples/demo_two_boats_with_pan_zoom.py` demonstrates:
1. Two boats at Port of Marseille, France
2. Zoom in/out functionality
3. Pan in all 4 directions
4. OpenStreetMap tile integration

```python
from node.VisualNode.node_map import Node as MapNode

# Create node
node = MapNode.create_for_testing()

# Define boats at port
boats_data = {
    "boats": [
        {
            "ship_name": "Mediterranean Star",
            "latitude": 43.2965,
            "longitude": 5.3698,
        },
        {
            "ship_name": "Provence Express",
            "latitude": 43.3015,
            "longitude": 5.3745,
        }
    ]
}

# Extract points
points = node._extract_lat_lon_from_json(boats_data)

# Normal view
extent = node._calculate_extent(points, size_factor=1.0, pan_offset_x=0.0, pan_offset_y=0.0)

# Zoom in
extent = node._calculate_extent(points, size_factor=0.5, pan_offset_x=0.0, pan_offset_y=0.0)

# Pan right and up
extent = node._calculate_extent(points, size_factor=1.0, pan_offset_x=0.5, pan_offset_y=0.5)

# Create map preview
preview = node._create_preview_image(points, 640, 480, pan_x=0.0, pan_y=0.0)
```

## Implementation Details

### Pan Offset Calculation
Pan offsets are applied as a fraction of the visible range:
```python
pan_x_meters = pan_offset_x * final_x_range
pan_y_meters = pan_offset_y * final_y_range

west += pan_x_meters
east += pan_x_meters
south += pan_y_meters
north += pan_y_meters
```

### Zoom (Size Factor) Calculation
Size factor scales the view range around the center point:
```python
# Calculate center
center_x = (min_x + max_x) / 2
center_y = (min_y + max_y) / 2

# Apply size factor
final_x_range = base_x_range * size_factor
final_y_range = base_y_range * size_factor

# Calculate extent from center
west = center_x - final_x_range / 2
east = center_x + final_x_range / 2
```

## Testing

### Automated Tests
Run the comprehensive test suite:
```bash
python tests/test_map_pan_and_zoom.py
```

Tests include:
- Two boats at port visualization
- Zoom in/out functionality
- Pan left/right (X-axis)
- Pan up/down (Y-axis)
- OpenStreetMap rendering
- Combined zoom and pan operations

### Interactive Demo
Run the interactive demo:
```bash
python examples/demo_two_boats_with_pan_zoom.py
```

## Requirements Satisfied

✅ **2 bateaux** (2 boats): Example with two boats at port
✅ **au port** (at port): Port of Marseille location
✅ **avec zoom** (with zoom): Zoom slider and size factor control
✅ **dézoom** (zoom out): Size factor > 1.0 or higher zoom level
✅ **translation gauche** (pan left): Pan X slider, negative values
✅ **translation droite** (pan right): Pan X slider, positive values
✅ **translation haut** (pan up): Pan Y slider, positive values
✅ **translation bas** (pan down): Pan Y slider, negative values
✅ **gestion openstreetmap** (OpenStreetMap management): Contextily integration with tile caching

## Technical Notes

### Coordinate System
- Uses Web Mercator projection (EPSG:3857)
- Coordinates are in meters from the origin
- Suitable for OpenStreetMap tile rendering

### OpenStreetMap Integration
- Uses `contextily` library for OSM tile downloading
- Automatic tile caching for performance
- Falls back to matplotlib rendering if tiles unavailable

### Performance
- Pan and zoom calculations are efficient (no tile re-download needed)
- Tiles are cached automatically by contextily
- Preview images are generated on-demand

## API Reference

### Node Methods

#### `_calculate_extent(points, zoom_level=None, size_factor=1.0, pan_offset_x=0.0, pan_offset_y=0.0)`
Calculate the bounding box extent with zoom and pan.

**Parameters:**
- `points`: List of points with 'lat' and 'lon' keys
- `zoom_level`: Optional zoom level (deprecated, use size_factor)
- `size_factor`: Zoom factor (0.5-5.0, default 1.0)
- `pan_offset_x`: Horizontal pan (-1.0 to 1.0, default 0.0)
- `pan_offset_y`: Vertical pan (-1.0 to 1.0, default 0.0)

**Returns:**
- Tuple of (west, south, east, north) in Web Mercator coordinates

#### `_create_preview_image(points, width, height, pan_x=0.0, pan_y=0.0)`
Create a map visualization image with OSM tiles.

**Parameters:**
- `points`: List of points with 'lat' and 'lon' keys
- `width`: Image width in pixels
- `height`: Image height in pixels
- `pan_x`: Horizontal pan offset (-1.0 to 1.0, default 0.0)
- `pan_y`: Vertical pan offset (-1.0 to 1.0, default 0.0)

**Returns:**
- numpy array in BGR format (suitable for OpenCV/DearPyGUI)

## See Also
- `node/VisualNode/node_map.py`: Main implementation
- `tests/test_map_node.py`: Original map node tests
- `tests/test_map_pan_and_zoom.py`: Pan and zoom tests
- `examples/demo_map_visualization.py`: General map examples
