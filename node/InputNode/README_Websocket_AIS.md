# WebSocket Input Node with AIS Stream Support

## Overview

The WebSocket Input Node provides an abstraction layer for handling WebSocket connections with specific support for AIS (Automatic Identification System) streams for boat tracking.

## Features

- **Abstract WebSocket Connection Handler**: Extensible architecture for different WebSocket protocols
- **AIS Stream Integration**: Built-in support for AIS streaming services
- **Bounding Box Filtering**: Filter boat data by geographic region
- **Real-time JSON Output**: Stream boat information in JSON format
- **Queue-based Message Handling**: Efficient message processing with bounded queues

## Architecture

### Classes

#### `WebSocketConnectionHandler` (Abstract Base)
Abstract base class for handling WebSocket connections with different protocols.

**Methods:**
- `connect()`: Connect to the WebSocket server
- `get_subscribe_message()`: Get subscription message
- `parse_message(message)`: Parse incoming messages
- `handle_messages()`: Handle incoming message stream

#### `AISStreamHandler` (Concrete Implementation)
Handler for AIS stream connections with bounding box filtering.

**Constructor:**
```python
AISStreamHandler(
    url: str,              # WebSocket URL
    api_key: str,          # API key for authentication
    bounding_box: List     # Geographic bounding box
)
```

#### `WebsocketNode` (Node Implementation)
The main node class that integrates with CV Studio's node editor.

## Usage

### Basic Configuration

1. **WebSocket URL**: Enter the AIS stream URL
   ```
   wss://stream.aisstream.io/v0/stream
   ```

2. **API Key**: Enter your AIS stream API key
   ```
   YOUR_API_KEY_HERE
   ```
   Note: Get your free API key at https://aisstream.io/

3. **Bounding Box**: Define geographic region in JSON format
   ```json
   [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
   ```

### Bounding Box Examples

#### Mediterranean Sea Region
```json
[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
```

#### North Atlantic
```json
[[[-80, 20], [-10, 20], [-10, 60], [-80, 60], [-80, 20]]]
```

#### Global Coverage
```json
[[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]
```

#### Custom Region (New York Harbor)
```json
[[[-74.1, 40.6], [-73.9, 40.6], [-73.9, 40.8], [-74.1, 40.8], [-74.1, 40.6]]]
```

### Bounding Box Format

Bounding boxes are defined as polygons using longitude/latitude coordinates:
- Format: `[[[lon1, lat1], [lon2, lat2], ..., [lon1, lat1]]]`
- Coordinates: `[longitude, latitude]`
- Longitude range: -180 to 180
- Latitude range: -90 to 90
- The polygon must be closed (first and last points must be the same)

## Output Format

The node outputs JSON data with the following structure:

```json
{
  "boats": [
    {
      "mmsi": "123456789",
      "ship_name": "Example Ship",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "speed": 12.5,
      "course": 90.0,
      "heading": 85,
      "timestamp": "2024-01-01T12:00:00Z",
      "ship_type": "Cargo",
      "destination": "New York"
    }
  ],
  "count": 1,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Output Fields

| Field | Description |
|-------|-------------|
| `mmsi` | Maritime Mobile Service Identity (unique ship identifier) |
| `ship_name` | Name of the vessel |
| `latitude` | Current latitude position |
| `longitude` | Current longitude position |
| `speed` | Speed over ground (knots) |
| `course` | Course over ground (degrees) |
| `heading` | True heading (degrees) |
| `timestamp` | Time of position report (UTC) |
| `ship_type` | Type of vessel (e.g., Cargo, Tanker, Passenger) |
| `destination` | Reported destination |

## Installation

The WebSocket node requires the `websockets` package:

```bash
pip install websockets
```

Or add to your requirements.txt:
```
websockets>=11.0.0
```

## Example Code

### Standalone Usage

```python
import asyncio
import json
from node.InputNode.node_websocket import AISStreamHandler

async def main():
    # Create AIS stream handler
    handler = AISStreamHandler(
        url="wss://stream.aisstream.io/v0/stream",
        api_key="YOUR_API_KEY_HERE",
        bounding_box=[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
    )
    
    # Connect and receive messages
    await handler.connect()

# Run the async function
asyncio.run(main())
```

### Extending with Custom Handlers

You can create custom WebSocket handlers by extending `WebSocketConnectionHandler`:

```python
from node.InputNode.node_websocket import WebSocketConnectionHandler

class MyCustomHandler(WebSocketConnectionHandler):
    def __init__(self, url: str, api_key: str):
        super().__init__(url, api_key)
    
    def get_subscribe_message(self):
        return {"type": "subscribe", "api_key": self.api_key}
    
    def parse_message(self, message: str):
        # Custom parsing logic
        data = json.loads(message)
        return {"custom_field": data.get("field")}
    
    async def connect(self):
        # Custom connection logic
        import websockets
        async with websockets.connect(self.url) as ws:
            await ws.send(json.dumps(self.get_subscribe_message()))
            await self.handle_messages()
    
    async def handle_messages(self):
        # Custom message handling
        pass
```

## Troubleshooting

### "websockets package is not installed"
Install the websockets package:
```bash
pip install websockets
```

### No Data Received
- Check your API key is valid
- Verify the bounding box coordinates are correct
- Ensure there is boat traffic in your selected region
- Check your internet connection

### Connection Errors
- Verify the WebSocket URL is correct
- Check firewall settings
- Ensure the AIS stream service is operational

## References

- AIS Stream Documentation: https://aisstream.io/documentation
- WebSocket Protocol: https://datatracker.ietf.org/doc/html/rfc6455
- AIS Message Format: https://www.itu.int/rec/R-REC-M.1371/en

## License

This implementation is part of CV Studio and follows the same license (Apache 2.0).
