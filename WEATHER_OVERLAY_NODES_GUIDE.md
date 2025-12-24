# Weather and Overlay Nodes - User Guide

## Overview
This document describes the Weather node (formerly Temperature) and the new Overlay node added to CV Studio.

## Weather Node

### Description
The Weather node fetches real-time weather data from the Open-Meteo API based on geographical coordinates.

### Changes from Temperature Node
- **Name**: Changed from "Temperature" to "Weather"
- **Functionality**: Remains the same - fetches weather data from Open-Meteo API
- **Output**: Provides JSON data with current weather information

### Inputs
- **Latitude** (Text): Geographical latitude (e.g., 48.8566 for Paris)
- **Longitude** (Text): Geographical longitude (e.g., 2.3522 for Paris)

### Outputs
- **JSON**: Weather data including:
  - `current_weather.temperature`: Temperature in Celsius
  - `current_weather.windspeed`: Wind speed in km/h
  - `current_weather.winddirection`: Wind direction in degrees
  - `current_weather.weathercode`: Weather condition code
  - `current_weather.is_day`: Day/night indicator
  - `current_weather.time`: Timestamp

### Usage
1. Add the Weather node from the Input menu
2. Enter the latitude and longitude coordinates
3. Click "Fetch Weather" button to retrieve data
4. Connect the JSON output to other nodes (like Overlay)

## Overlay Node (NEW)

### Description
The Overlay node displays JSON key-value pairs on top of an image in a stylish, configurable manner. Perfect for displaying weather data, statistics, or any structured information on video/image streams.

### Inputs
- **Master Image** (IMAGE): The base image on which to overlay the data
- **Overlay Data** (JSON): JSON object containing key-value pairs to display

### Outputs
- **Output Image** (IMAGE): The master image with overlay applied

### Configuration Options
- **Font Scale** (0.3 - 2.0): Size of the text
- **Text Color**: RGB color for the text
- **Background Color**: RGBA color for the semi-transparent panel
- **Position**: Where to place the overlay
  - Top Left
  - Top Right
  - Bottom Left
  - Bottom Right
  - Center

### Features
- **Automatic Flattening**: Nested JSON structures are automatically flattened for display
  - Example: `{"location": {"city": "Paris"}}` becomes `location_city: Paris`
- **Smart Formatting**: Float values are displayed with 2 decimal places
- **Semi-Transparent Panel**: Background panel with configurable transparency
- **Border**: Subtle border around the panel for better visibility
- **Responsive**: Automatically adjusts panel size based on content

### Usage Example: Weather Display

#### Basic Setup
1. Add a Video/Webcam node to get image stream
2. Add the Weather node
3. Configure Weather node with coordinates
4. Click "Fetch Weather"
5. Add the Overlay node
6. Connect:
   - Video/Webcam IMAGE output → Overlay IMAGE input
   - Weather JSON output → Overlay JSON input
7. Configure Overlay styling as desired
8. Connect Overlay output to display/video writer

#### Result
You'll see real-time weather information beautifully displayed on your video stream!

### Advanced Usage

#### Custom Data Display
The Overlay node works with any JSON data, not just weather:

```json
{
  "fps": 30.5,
  "resolution": "1920x1080",
  "objects_detected": 5,
  "processing_time": "16.7ms"
}
```

#### Multiple Overlays
Create multiple Overlay nodes with different positions to display different data sets:
- Top Right: Weather data
- Bottom Left: Processing statistics
- Top Left: System information

## Styling Tips

### High Contrast (Night Vision)
- Text Color: Bright green (100, 255, 100)
- Background: Dark green (10, 30, 10)
- Position: Bottom Left

### Clean Professional
- Text Color: White (255, 255, 255)
- Background: Black with 70% transparency (0, 0, 0, 180)
- Position: Top Right

### Alert Style
- Text Color: Yellow (255, 255, 100)
- Background: Dark grey (50, 50, 50)
- Font Scale: 1.0
- Position: Center

## Technical Details

### Color Format
- Text Color: RGB (0-255 for each channel)
- Background Color: RGBA (0-255 for RGB, 0-255 for alpha/transparency)
- Colors are automatically converted to BGR format for OpenCV

### Performance
- Minimal performance impact
- Efficient text rendering using OpenCV
- Caches converted colors for performance

### Limitations
- Maximum panel size is constrained by image dimensions
- Very long text may be truncated if it exceeds image bounds
- JSON data should be reasonably sized for readability

## Troubleshooting

### Overlay not visible
- Check that both IMAGE and JSON inputs are connected
- Verify JSON data is not empty/None
- Adjust text color for better contrast with image content
- Try different positions

### Text too small/large
- Adjust Font Scale slider (0.3 to 2.0)
- Default is 0.7, suitable for most use cases

### Background not transparent
- Verify Background Color alpha channel is < 255
- 180-200 provides good balance of readability and transparency

### Weather data not updating
- Click "Fetch Weather" button again
- Verify internet connectivity
- Check latitude/longitude values are valid

## Examples

See the test files for working examples:
- `tests/test_weather_overlay_nodes.py`: Unit tests
- `tests/demo_overlay_visual.py`: Visual demonstration with multiple styles

Generated demo images show:
- Different positioning options
- Various color schemes
- Nested JSON handling
- Before/after comparison
