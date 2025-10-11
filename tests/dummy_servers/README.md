# Dummy Servers for Testing

This directory contains dummy servers for testing API, WebSocket, and WebRTC input nodes in CV_Studio.

## Overview

The dummy servers simulate real data sources that can serve:
- **Images**: Random generated images (640x480 PNG)
- **Floats**: Random float values (0.0 - 100.0)

## Servers

### 1. API Server (`api_server.py`)

HTTP server with REST endpoints.

**Endpoints:**
- `GET /image` - Returns a random PNG image
- `GET /float` - Returns a JSON object with a random float value
- `GET /status` - Returns server status

**Usage:**
```bash
# Start with default settings (localhost:8080)
python api_server.py

# Custom host and port
python api_server.py --host 0.0.0.0 --port 9000
```

**Example requests:**
```bash
# Get float value
curl http://localhost:8080/float

# Get image
curl http://localhost:8080/image --output test.png

# Get status
curl http://localhost:8080/status
```

### 2. WebSocket Server (`websocket_server.py`)

WebSocket server that streams data continuously.

**Data Types:**
- `image` - Streams random images as base64-encoded PNG
- `float` - Streams random float values

**Usage:**
```bash
# Stream images (default)
python websocket_server.py --type image --port 8765

# Stream floats
python websocket_server.py --type float --port 8766

# Custom interval (seconds between messages)
python websocket_server.py --type image --interval 0.5
```

**Message Format:**
```json
// Image message
{
  "type": "image",
  "data": "base64_encoded_png_data...",
  "format": "png",
  "width": 640,
  "height": 480,
  "timestamp": 1234567890.123
}

// Float message
{
  "type": "float",
  "value": 42.42,
  "timestamp": 1234567890.123
}
```

### 3. WebRTC Server (`webrtc_server.py`)

WebRTC server for peer-to-peer streaming.

**Data Types:**
- `image` - Streams video with random frames
- `float` - Sends float data via data channel

**Usage:**
```bash
# Stream images via WebRTC
python webrtc_server.py --type image --port 8081

# Stream floats via data channel
python webrtc_server.py --type float --port 8081
```

**Note:** Requires additional libraries: `pip install aiohttp aiortc`

## Running All Servers

Use the `run_servers.py` script to launch multiple servers at once:

```bash
# Start all servers with default configuration
python run_servers.py

# Start all servers and run tests
python run_servers.py --test

# Start only API server
python run_servers.py --api-only

# Start only WebSocket servers
python run_servers.py --websocket-only

# Start only WebRTC server
python run_servers.py --webrtc-only

# Custom ports
python run_servers.py --api-port 9000 --ws-image-port 9001 --ws-float-port 9002
```

**Default Configuration:**
- API Server: `http://localhost:8080`
- WebSocket (images): `ws://localhost:8765`
- WebSocket (floats): `ws://localhost:8766`
- WebRTC: `http://localhost:8081`

## Testing

### Quick Test

Run a quick test to verify servers are working:

```bash
python test_servers.py --quick
```

### Full Test Suite

Run the complete integration test suite:

```bash
python test_servers.py
```

This will:
1. Start all necessary servers
2. Run integration tests on each server
3. Verify data formats and responses
4. Stop all servers after testing

### Manual Testing

You can also test servers manually:

**API Server:**
```bash
# Terminal 1: Start server
python api_server.py

# Terminal 2: Test endpoints
curl http://localhost:8080/status
curl http://localhost:8080/float
curl http://localhost:8080/image --output test.png
```

**WebSocket Server:**
```bash
# Terminal 1: Start server
python websocket_server.py --type image

# Terminal 2: Connect with client (requires websockets library)
python -c "
import asyncio
import websockets

async def test():
    async with websockets.connect('ws://localhost:8765') as ws:
        for i in range(3):
            msg = await ws.recv()
            print(f'Received: {len(msg)} bytes')

asyncio.run(test())
"
```

## Requirements

### Basic Requirements (API Server)
- Python 3.7+
- numpy
- Pillow

### WebSocket Server
- websockets (`pip install websockets`)

### WebRTC Server
- aiohttp (`pip install aiohttp`)
- aiortc (`pip install aiortc`)

### Install All Dependencies
```bash
pip install numpy Pillow websockets aiohttp aiortc
```

## Integration with CV_Studio

These servers can be used to test the input nodes in CV_Studio:

1. **API Node**: Point to `http://localhost:8080/image` or `http://localhost:8080/float`
2. **WebSocket Node**: Connect to `ws://localhost:8765` or `ws://localhost:8766`
3. **WebRTC Node**: Connect to `http://localhost:8081`

## Architecture

```
tests/dummy_servers/
├── __init__.py              # Package init
├── api_server.py            # HTTP REST API server
├── websocket_server.py      # WebSocket streaming server
├── webrtc_server.py         # WebRTC peer connection server
├── run_servers.py           # Launch all servers
├── test_servers.py          # Integration tests
└── README.md                # This file
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :8080

# Kill process
kill -9 <PID>
```

### Import Errors
Make sure all dependencies are installed:
```bash
pip install -r ../../requirements.txt
pip install websockets aiohttp aiortc
```

### Connection Refused
Wait a few seconds after starting servers before connecting. Servers need time to initialize.

## Examples

### Example 1: Test API with curl
```bash
# Start server
python api_server.py &

# Test all endpoints
curl http://localhost:8080/status | jq
curl http://localhost:8080/float | jq
curl http://localhost:8080/image --output /tmp/test.png
```

### Example 2: Stream WebSocket Data
```python
import asyncio
import websockets
import json

async def stream_data():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        for i in range(10):
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Frame {i}: {data['type']}")

asyncio.run(stream_data())
```

### Example 3: Launch Everything
```bash
# Start all servers and test
python run_servers.py --test

# In another terminal, use CV_Studio nodes to connect
```

## Development

To add new server types or modify existing ones:

1. Edit the respective server file (`api_server.py`, `websocket_server.py`, `webrtc_server.py`)
2. Update `run_servers.py` to include new configuration
3. Add tests in `test_servers.py`
4. Update this README

## License

Same as CV_Studio project.
