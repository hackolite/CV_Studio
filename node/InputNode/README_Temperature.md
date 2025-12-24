# Temperature Input Node

## Description

The Temperature Input Node fetches real-time weather data from the Open-Meteo API (https://api.open-meteo.com/) for a specified location and outputs the data in JSON format.

## Features

- Fetches current weather data including temperature, wind speed, and weather code
- Configurable latitude and longitude inputs
- Yellow-themed button for fetching data
- JSON output compatible with the rest of the CV Studio system
- Error handling for invalid coordinates or API failures

## Usage

1. **Add the Node**: Select "Temperature" from the "Input" menu
2. **Configure Location**: 
   - Enter the latitude (default: 48.8566 for Paris)
   - Enter the longitude (default: 2.3522 for Paris)
3. **Fetch Data**: Click the "Fetch Temperature" button
4. **Connect Output**: Connect the JSON output to other nodes that accept JSON data

## API Details

The node uses the Open-Meteo API:
```
https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true
```

### Example Output

```json
{
  "latitude": 48.8566,
  "longitude": 2.3522,
  "generationtime_ms": 0.123,
  "utc_offset_seconds": 0,
  "timezone": "GMT",
  "timezone_abbreviation": "GMT",
  "elevation": 42.0,
  "current_weather": {
    "temperature": 15.2,
    "windspeed": 10.5,
    "winddirection": 180,
    "weathercode": 0,
    "is_day": 1,
    "time": "2025-12-24T11:00"
  }
}
```

## Coordinates Examples

- **Paris**: 48.8566, 2.3522
- **New York**: 40.7128, -74.0060
- **Tokyo**: 35.6762, 139.6503
- **London**: 51.5074, -0.1278
- **Sydney**: -33.8688, 151.2093

## Error Handling

The node handles the following error cases:
- Invalid coordinate format (non-numeric values)
- API connection failures
- Network timeouts (10 second timeout)
- Unexpected errors

Errors are returned in the JSON output with an "error" field containing the error message.

## Node Version

- Version: 1.0.0
- Author: CV Studio
- API: Open-Meteo (https://open-meteo.com/)
- License: Free for non-commercial use (Open-Meteo API)

## Dependencies

- `requests` library (for HTTP requests)

## Notes

- The Open-Meteo API is free and doesn't require an API key
- Data is fetched only when the "Fetch Temperature" button is clicked
- The last fetched data is retained until new data is fetched
- The node outputs `None` for image and audio data types
