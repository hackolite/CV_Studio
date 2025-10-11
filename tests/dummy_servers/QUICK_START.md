# Quick Start Guide

## Installation

```bash
# Navigate to the dummy servers directory
cd tests/dummy_servers

# Install required dependencies
pip install numpy Pillow websockets
```

## Option 1: Run the Demo (Recommended for First Time)

```bash
python demo.py
```

This will:
- Start API server and WebSocket servers
- Test all endpoints automatically
- Display received data and statistics
- Save example images to `/tmp/`
- Stop all servers when done

## Option 2: Interactive Menu

```bash
./launch.sh
```

Choose from menu:
1. Start all servers
2. Start API server only
3. Start WebSocket servers only
4. Run demo
5. Run tests

## Option 3: Start Individual Servers

### API Server
```bash
python api_server.py --port 8080
```

Test it:
```bash
curl http://localhost:8080/status
curl http://localhost:8080/float
curl http://localhost:8080/image -o test.png
```

### WebSocket Server (Images)
```bash
python websocket_server.py --type image --port 8765
```

### WebSocket Server (Floats)
```bash
python websocket_server.py --type float --port 8766
```

## Option 4: Start All Servers at Once

```bash
python run_servers.py
```

With testing:
```bash
python run_servers.py --test
```

## Testing

### Quick Unit Tests (No Server Startup)
```bash
python test_unit.py
```

### Integration Tests
```bash
python test_servers.py --quick
```

### Full Test Suite
```bash
python test_servers.py
```

## Usage with CV_Studio Nodes

1. **API Node Configuration:**
   - URL for images: `http://localhost:8080/image`
   - URL for floats: `http://localhost:8080/float`

2. **WebSocket Node Configuration:**
   - URL for image stream: `ws://localhost:8765`
   - URL for float stream: `ws://localhost:8766`

3. **WebRTC Node Configuration:**
   - Signaling URL: `http://localhost:8081`

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8080
lsof -i :8080

# Kill the process
kill -9 <PID>
```

### Import Errors
```bash
# Install all dependencies
pip install -r requirements.txt
```

### Connection Refused
Wait a few seconds after starting servers before connecting. Servers need time to initialize.

## Examples

### Example 1: Test API Server
```bash
# Terminal 1: Start server
python api_server.py

# Terminal 2: Test endpoints
curl http://localhost:8080/status | python -m json.tool
curl http://localhost:8080/float | python -m json.tool
curl http://localhost:8080/image --output test.png
```

### Example 2: Test WebSocket Server
```python
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8765') as ws:
        for i in range(5):
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"Received: {data['type']}")

asyncio.run(test())
```

### Example 3: Run Everything
```bash
# One command to rule them all
python run_servers.py --test
```

## Next Steps

1. Start the servers
2. Open CV_Studio
3. Add an API or WebSocket input node
4. Configure it to connect to the dummy server
5. Connect the node to your processing pipeline
6. Enjoy testing with live data!

---

For more details, see [README.md](README.md) or [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md).
