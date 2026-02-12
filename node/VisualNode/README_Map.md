# Map Visualization Node

## Overview
The Map node provides interactive map visualization using OpenStreetMap and Leaflet. It extracts latitude/longitude coordinates from JSON data and displays them on an interactive map that opens in your web browser.

## Features
- **Multiple JSON Format Support**: Automatically extracts latitude/longitude from various JSON structures
- **Interactive Map**: Opens in browser with full zoom, pan, and marker interaction
- **Preview Display**: Shows a simple preview of point distribution in the node
- **Customizable View**: Adjust zoom level and view size with sliders
- **Marker Clustering**: Automatically clusters nearby markers for better performance with many points

## Inputs
- **JSON with lat/lon**: JSON data containing latitude and longitude information

## Outputs
- **Preview Image**: A simple visualization showing the distribution of points
- **Processing Time**: Time taken to process and generate the map

## Controls
- **Zoom Slider** (1-18): Set the initial zoom level for the map
  - Lower values: See more of the world (zoomed out)
  - Higher values: See less area in detail (zoomed in)
- **View Size Slider** (0.5-5.0): Adjust the bounding box size
  - Values < 1.0: Tighter view around points
  - Values > 1.0: Wider view with more context
- **Open Map in Browser Button**: Opens the generated interactive map in your default web browser

## Supported JSON Formats

### AIS Boat Data (from WebSocket node)
```json
{
  "boats": [
    {
      "mmsi": "123456789",
      "ship_name": "Example Ship",
      "latitude": 40.7128,
      "longitude": -74.0060
    }
  ]
}
```

### Simple List Format
```json
[
  {
    "latitude": 51.5074,
    "longitude": -0.1278,
    "name": "London"
  },
  {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "name": "Paris"
  }
]
```

### Alternative lat/lon Keys
```json
[
  {
    "lat": 35.6762,
    "lon": 139.6503,
    "name": "Tokyo"
  }
]
```

## Usage Example

### With WebSocket AIS Data
1. Add a **WebSocket** node (Input menu)
2. Configure it for AIS stream (see WebSocket node documentation)
3. Add a **Map** node (Visual menu)
4. Connect WebSocket JSON output to Map JSON input
5. Adjust zoom and view size as needed
6. Click "Open Map in Browser" to see the interactive map

### With Custom JSON Data
1. Create or load JSON data with latitude/longitude
2. Add a **Map** node
3. Connect your JSON source to the Map input
4. Configure visualization settings
5. Open the map in your browser

## Map Features

The generated HTML map includes:
- **OpenStreetMap** base layer
- **Interactive markers** for each point
- **Marker clustering** for better performance
- **Tooltips** showing point names on hover
- **Popups** with detailed information on click
- **Full zoom/pan controls**
- **Auto-fit bounds** to show all points

## Technical Details

### Dependencies
- `folium>=0.14.0`: Python library for generating Leaflet maps

### Data Extraction
The node automatically searches JSON structures for:
- `latitude`/`longitude` keys
- `lat`/`lon` keys
- Nested structures (e.g., AIS `boats` array)
- Lists of coordinate objects

### Output Files
Maps are saved as temporary HTML files in:
- **Linux/Mac**: `/tmp/cv_studio_map_YYYYMMDD_HHMMSS.html`
- **Windows**: `%TEMP%\cv_studio_map_YYYYMMDD_HHMMSS.html`

Files are kept in the temp directory and will be cleaned up by the operating system.

## Tips

### Optimal Zoom Levels
- **World view**: 1-3
- **Continent**: 3-5
- **Country**: 5-7
- **City**: 10-12
- **Neighborhood**: 13-15
- **Street**: 16-18

### Performance
- The map uses marker clustering for efficient display of many points
- Preview image generation is fast and lightweight
- Map generation time increases with the number of points (typically < 1 second for 1000 points)

### Customization
The view size slider allows you to control how much context is shown around your points:
- Set to 1.0 for a tight fit around all points
- Increase to see more surrounding area
- Decrease to focus more tightly on the points

## Troubleshooting

### "No lat/lon found" status
- Check that your JSON contains `latitude`/`longitude` or `lat`/`lon` keys
- Verify the JSON structure matches one of the supported formats
- Check the JSON is valid (use a JSON validator if needed)

### Map doesn't open
- Verify the "Open Map in Browser" button is clicked after data is received
- Check your default browser is set correctly
- Look for the map file in your system's temp directory

### Preview shows no points
- Ensure JSON data is being received (check connections)
- Verify latitude/longitude values are valid numbers
- Check that coordinates are in decimal degrees format

## Example Workflows

### Marine Traffic Monitoring
WebSocket (AIS) → Map
- Real-time visualization of ship positions
- Click markers to see ship details

### Location Analytics
CSV/Database → JSON Converter → Map
- Visualize customer locations
- Analyze geographic distribution

### GPS Tracking
MQTT/WebSocket → Map
- Track moving objects in real-time
- Historical path visualization

## Future Enhancements
Potential features for future versions:
- Path/trajectory visualization
- Heatmap overlay
- Custom marker icons
- Multiple map tile providers
- Export map as image
- Time-based animation
