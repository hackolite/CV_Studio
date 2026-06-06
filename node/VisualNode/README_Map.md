# Map Visualization Node

## Overview
The Map node provides interactive map visualization using OpenStreetMap tiles. It uses **contextily** for efficient tile downloading and caching, **matplotlib** for rendering, and displays GPS coordinates on an interactive map within the Dear PyGui node editor.

## Key Technologies
- **contextily**: Downloads and caches OpenStreetMap tiles
- **matplotlib**: Renders maps with GPS points
- **Pillow**: Image processing
- **Dear PyGui**: Interactive node-based interface

## Features
- **Multiple JSON Format Support**: Automatically extracts latitude/longitude from various JSON structures
- **Contextily-based Rendering**: Efficient OSM tile downloading with built-in caching
- **Real-time Visualization**: Shows GPS points directly in the node editor
- **Dynamic Updates**: Texture updates automatically when new GPS points are added
- **Zoom and Auto-scaling**: Automatically adjusts bounding box to fit all points
- **Local Tile Caching**: contextily handles tile caching for performance
- **Fallback Rendering**: Uses matplotlib-only rendering when tiles unavailable

## Inputs
- **JSON with lat/lon**: JSON data containing latitude and longitude information

## Outputs
- **Map Texture**: Real-time visualization of GPS points on OpenStreetMap tiles displayed in the node
- **Processing Time**: Time taken to process and generate the map

## Controls
- **Zoom Slider** (1-20): Set the zoom level for the map (clamped per provider's max_zoom)
  - Lower values: See more of the world (zoomed out)
  - Higher values: See less area in detail (zoomed in)
- **Tile Provider (Style)**: Choose the basemap style:
  - `OSM Standard` — classic OpenStreetMap (default)
  - `CartoDB Positron` — clean light style, great for dataviz
  - `CartoDB Dark Matter` — clean dark style
  - `Esri World Imagery` — satellite imagery (very high visual detail)
  - `OpenTopoMap` — topographic relief with contour lines
- **HiDPI tiles (@2x)**: When the provider supports it (e.g. CartoDB), fetch
  512 px tiles for ~4× the detail at the same coverage. No effect on
  providers that have no @2x variant.
- **Labels overlay**: Composite the provider's transparent labels-only layer
  on top of the basemap (e.g. street names over Esri satellite, à la Google
  Hybrid). Silently ignored on providers without a labels layer.
- **View Size Slider** (0.5-5.0): Adjust the bounding box size
  - Values < 1.0: Tighter view around points
  - Values > 1.0: Wider view with more context
- **Cache Maps Checkbox**: Enable/disable on-disk tile caching. The cache is
  namespaced per provider and density, so switching styles never serves the
  wrong PNGs.

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

### With GPS Movement Simulation
1. Add a **CoordinateExamples** node (Input menu)
2. Select "GPS Movement Simulation" from the dropdown
3. Add a **Map** node (Visual menu)
4. Connect CoordinateExamples JSON output to Map JSON input
5. Enable "Cache Maps" for faster repeated visualization
6. The map will automatically display GPS points with real-time updates
7. Points are rendered on OpenStreetMap tiles using contextily

### With WebSocket AIS Data
1. Add a **WebSocket** node (Input menu)
2. Configure it for AIS stream (see WebSocket node documentation)
3. Add a **Map** node (Visual menu)
4. Connect WebSocket JSON output to Map JSON input
5. The map texture updates automatically with new positions

### With Custom JSON Data
1. Create or load JSON data with latitude/longitude
2. Add a **Map** node
3. Connect your JSON source to the Map input
4. View the rendered map with GPS points in the node

## Map Features

The generated map visualization includes:
- **OpenStreetMap** base layer (via contextily)
- **GPS point markers** rendered on the map
- **Point labels** showing names (for ≤10 points)
- **Auto-fit bounds** to show all points
- **Dynamic texture updates** as new points arrive
- **Efficient tile caching** via contextily

## Tile Caching

The Map node uses contextily's built-in caching system for optimal performance:

### How Caching Works
- **Automatic Caching**: contextily automatically caches downloaded tiles
- **Cache Location**: System-dependent (typically `~/.cache/contextily/`)
- **Cache Hit**: Tiles are reused from cache when available
- **Network Fallback**: Downloads tiles as needed when not cached

### Performance Benefits
- ✅ Faster map rendering for repeated views
- ✅ Reduced network bandwidth usage
- ✅ Offline viewing of previously cached areas
- ✅ Automatic cache management

## Technical Details

### Dependencies
- `contextily>=1.3.0`: OpenStreetMap tile downloading and caching
- `matplotlib>=3.8`: Map rendering with GPS points
- `Pillow>=9.0.0`: Image processing
- `opencv-contrib-python>=4.8`: Image format conversion

### Rendering Pipeline
1. **Extract Coordinates**: Parse JSON to get lat/lon points
2. **Convert to Web Mercator**: Transform coordinates to EPSG:3857 projection
3. **Calculate Extent**: Determine bounding box with auto-scaling
4. **Render with contextily**: Download OSM tiles and plot GPS points
5. **Convert to Texture**: Convert matplotlib figure to DPG texture format
6. **Update Display**: Show texture in node editor

### Coordinate System
- **Input**: WGS84 lat/lon (degrees)
- **Internal**: Web Mercator EPSG:3857 (meters)
- **Output**: BGR image for OpenCV/DPG

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

### Map shows fallback rendering
- This is normal when network access is unavailable
- The node falls back to matplotlib-only rendering
- GPS points will still be visible with a simple background

### Preview shows no points
- Ensure JSON data is being received (check connections)
- Verify latitude/longitude values are valid numbers
- Check that coordinates are in decimal degrees format

### Performance issues
- contextily caching improves performance over time
- First load may be slower as tiles are downloaded
- Subsequent loads use cached tiles and are faster

## Example Workflows

### Marine Traffic Monitoring
WebSocket (AIS) → Map
- Real-time visualization of ship positions in node editor
- Automatic texture updates as ships move

### Location Analytics
CSV/Database → JSON Converter → Map
- Visualize customer locations
- Analyze geographic distribution

### GPS Tracking
MQTT/WebSocket → Map
- Track moving objects in real-time
- Dynamic texture updates for live tracking

## Implementation Details

### Contextily Integration
The node uses contextily for:
- **Tile Downloading**: Automatic OSM tile fetching
- **Tile Caching**: Built-in cache management
- **Basemap Rendering**: Efficient map tile composition

### Matplotlib Rendering
Matplotlib is used for:
- **Point Plotting**: GPS point visualization
- **Coordinate Transformation**: Web Mercator projection
- **Figure Composition**: Combining tiles and points
- **Export**: Converting to numpy array for DPG

### Dear PyGui Display
The rendered map is:
- **Converted to BGR**: OpenCV format for compatibility
- **Encoded as Texture**: DPG raw texture format
- **Updated Dynamically**: Texture refreshes with new data
- **Displayed in Node**: Shows in node editor canvas

## Future Enhancements
Potential features for future versions:
- Path/trajectory visualization
- Heatmap overlay
- Custom marker styles
- Multiple tile providers
- Interactive zoom controls
- Time-based animation
