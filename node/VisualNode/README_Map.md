# Map Node

## Overview

The Map node is a visualization node that displays geographical data on an interactive map. It takes JSON input containing latitude and longitude coordinates and renders them on a map interface.

## Features

- **JSON Input**: Accepts various JSON structures containing geographical coordinates
- **Auto-fit View**: Automatically adjusts the view to show all points with padding
- **Zoom Control**: Slider to zoom in/out (0.5x to 10x)
- **Pan Controls**: Horizontal and vertical sliders to move the view
- **Multiple Format Support**: Handles AIS data, simple lat/lon objects, and lists

## Inputs

### JSON (lat/lon)
Accepts JSON data in various formats:

1. **AIS Boat Data Format**:
```json
{
  "boats": [
    {
      "mmsi": "123456789",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "ship_name": "Example Ship"
    }
  ],
  "count": 1
}
```

2. **Simple Object Format**:
```json
{
  "latitude": 48.8566,
  "longitude": 2.3522
}
```

3. **Short Format**:
```json
{
  "lat": 51.5074,
  "lon": -0.1278
}
```

4. **List Format**:
```json
[
  {"latitude": 40.7128, "longitude": -74.0060},
  {"latitude": 34.0522, "longitude": -118.2437}
]
```

## Controls

### Zoom Slider
- **Range**: 0.5 to 10.0
- **Default**: 1.0 (original view)
- **Effect**: 
  - Values < 1.0: Zoom out (see more area)
  - Values > 1.0: Zoom in (see less area, more detail)

### Pan X (Left/Right) Slider
- **Range**: -1.0 to 1.0
- **Default**: 0.0 (centered)
- **Effect**:
  - Negative values: Pan left (west)
  - Positive values: Pan right (east)

### Pan Y (Up/Down) Slider
- **Range**: -1.0 to 1.0
- **Default**: 0.0 (centered)
- **Effect**:
  - Negative values: Pan down (south)
  - Positive values: Pan up (north)

## Outputs

### Map Image
RGB image showing the map with plotted coordinates as red dots.

### Processing Time (optional)
Elapsed time in milliseconds for rendering the map.

## Usage Example

### With WebSocket AIS Node

1. Add a **WebSocket** node (from Input menu)
2. Configure WebSocket for AIS stream:
   - URL: `wss://stream.aisstream.io/v0/stream`
   - API Key: Your AIS Stream API key
   - Bounding Box: Geographic area of interest
3. Add a **Map** node (from Visual menu)
4. Connect WebSocket's JSON output to Map's JSON input
5. Adjust zoom and pan sliders to navigate the map
6. Red dots will appear showing boat positions

### With Custom JSON Data

1. Add a data source node that outputs JSON with lat/lon
2. Add a **Map** node (from Visual menu)
3. Connect JSON output to Map input
4. View geographical data visualized on the map

## Technical Details

### Coordinate Extraction

The node intelligently extracts coordinates from various JSON structures:
- Searches for `latitude`/`longitude` fields
- Searches for `lat`/`lon` or `lat`/`lng` fields
- Handles AIS `boats` array structure
- Recursively searches nested structures
- Processes lists of coordinate objects

### Auto-fit Behavior

On first data reception:
1. Calculates bounding box of all points
2. Adds 10% padding on all sides
3. Centers the view to show all points

The initial bounds are preserved as you zoom/pan, ensuring you can always return to the original view by resetting sliders to default values.

### Map Rendering

- Uses matplotlib for rendering
- Light blue background represents water
- Red dots with dark red borders represent coordinates
- Grid lines help with orientation
- Shows current bounds and point count in title

## Tips

1. **Reset View**: Set all sliders to default (Zoom=1.0, Pan X=0.0, Pan Y=0.0) to return to the auto-fit view
2. **Fine Navigation**: Use small zoom values with pan for precise navigation
3. **Wide Area View**: Set zoom to 0.5 to see a larger area
4. **Performance**: The node efficiently handles hundreds of points
5. **Real-time Updates**: Works seamlessly with streaming data sources like WebSocket

## Limitations

1. Does not display actual OpenStreetMap tiles (uses simplified background)
2. Points are displayed as dots without labels
3. No interactive click/hover information
4. Fixed color scheme (red points on blue background)

## Future Enhancements

Potential improvements for future versions:
- Actual OSM tile integration via folium
- Customizable point colors and sizes
- Point labels and tooltips
- Export map as PNG file
- Multiple point layers
- Heat map mode
- Trail/path visualization for moving objects

## Examples

### Mediterranean Boat Tracking
```
WebSocket Node → Map Node
URL: wss://stream.aisstream.io/v0/stream
BoundingBox: [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
```

### Global Ship Monitoring
```
WebSocket Node → Map Node
URL: wss://stream.aisstream.io/v0/stream
BoundingBox: [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]
Zoom: 0.5 (to see the whole world)
```

## Troubleshooting

### No points visible
- Check that JSON input contains valid lat/lon data
- Verify coordinate format matches supported structures
- Try resetting zoom and pan to defaults

### Points outside view
- Reset zoom to 1.0 and pan sliders to 0.0
- Adjust pan sliders to navigate to points
- Increase zoom-out (zoom < 1.0) to see wider area

### Performance issues
- Reduce number of points if possible
- Consider filtering data before the Map node
- Ensure adequate GPU/CPU resources

## Related Nodes

- **WebSocket**: Stream real-time geographical data
- **JSON Filter**: Pre-process JSON before mapping
- **ObjChart**: Visualize object detection statistics
- **Heatmap**: Create density visualizations

## Version History

- **v0.0.1** (2026-02-12): Initial release
  - Basic map visualization
  - Zoom and pan controls
  - Multi-format JSON support
  - Auto-fit view
