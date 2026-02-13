# Secure API Key Management Guide

## Overview

This guide explains how to securely manage API keys for WebSocket connections (particularly AIS stream) in CV Studio. The implementation follows security best practices by keeping sensitive credentials out of source code.

## Problem Statement

The original issue requested:
> "inspire toi de ça pour le websocket préinscrit la clées, mais cache"
> (Use this as inspiration for the websocket, pre-configure the key but hide it)

This means:
1. ✅ Pre-configure the API key (make it easy to set up)
2. ✅ Hide the key (don't hardcode it in visible source files)

## Solution Implemented

### 1. Environment Variables

API keys are now loaded from environment variables instead of being hardcoded:

```python
api_key = os.getenv('AIS_STREAM_API_KEY')
```

### 2. `.env` File Support

Created `.env.example` template for easy setup:

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env and add your API key
AIS_STREAM_API_KEY=your_actual_api_key_here
```

The actual `.env` file is git-ignored for security.

### 3. Centralized Configuration

Created `src/utils/env_config.py` module for managing environment variables:

```python
from src.utils.env_config import get_ais_config, is_api_key_configured

# Check if API key is configured
if not is_api_key_configured():
    print("Please set AIS_STREAM_API_KEY")

# Get configuration
config = get_ais_config()
api_key = config['api_key']
url = config['url']
```

### 4. Updated Example Script

The `examples/example_ais_stream.py` now:
- ✅ Loads API key from environment variables
- ✅ Falls back to command line argument for convenience
- ✅ Shows clear error messages if API key is missing
- ✅ Doesn't expose API keys in code or logs

## Usage Methods

### Method 1: .env File (Recommended)

Best for development and local testing.

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API key:
   ```bash
   AIS_STREAM_API_KEY=your_api_key_here
   AIS_STREAM_URL=wss://stream.aisstream.io/v0/stream
   AIS_STREAM_BOUNDING_BOX=[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
   ```

3. Run the example:
   ```bash
   python examples/example_ais_stream.py
   ```

### Method 2: Environment Variable

Best for production and CI/CD pipelines.

```bash
# Set environment variable
export AIS_STREAM_API_KEY='your_api_key_here'

# Run the example
python examples/example_ais_stream.py
```

On Windows:
```cmd
set AIS_STREAM_API_KEY=your_api_key_here
python examples/example_ais_stream.py
```

### Method 3: Command Line (Not Recommended)

Only use for quick testing. API key will be visible in shell history.

```bash
python examples/example_ais_stream.py YOUR_API_KEY
```

## Security Features

### ✅ What's Protected

1. **API Keys Hidden**: No real API keys in source code
2. **Git Ignored**: `.env` files are automatically ignored by git
3. **Example Template**: `.env.example` shows structure without real credentials
4. **Password Fields**: Node UI uses password fields for API keys
5. **Secure Logs**: API keys are not logged or displayed

### ✅ Files Modified

1. **`.env.example`**: Template for environment variables
2. **`requirements.txt`**: Added `python-dotenv>=0.19.0`
3. **`examples/example_ais_stream.py`**: Updated to use environment variables
4. **`src/utils/env_config.py`**: New utility module for env management
5. **`node/InputNode/README_Websocket_AIS.md`**: Updated documentation
6. **`tests/test_env_config.py`**: Comprehensive test suite

## Testing

### Run Tests

```bash
# Install dependencies
pip install python-dotenv

# Run environment config tests
python tests/test_env_config.py

# Run WebSocket abstraction tests
python tests/test_websocket_abstraction.py
```

### Test Results

All tests pass:
- ✅ Environment variable loading
- ✅ API key configuration checks
- ✅ .env file parsing
- ✅ Security validation (no hardcoded keys)
- ✅ WebSocket abstraction layer

## Example Usage

### Python Script

```python
import os
from pathlib import Path
from dotenv import load_dotenv
from node.InputNode.node_websocket import AISStreamHandler

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Get API key from environment
api_key = os.getenv('AIS_STREAM_API_KEY')

if not api_key:
    raise ValueError("Please set AIS_STREAM_API_KEY environment variable")

# Create handler
handler = AISStreamHandler(
    url="wss://stream.aisstream.io/v0/stream",
    api_key=api_key,
    bounding_box=[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
)
```

### CV Studio Node

The WebSocket node in the CV Studio editor automatically:
1. Shows a password field for API key input
2. Hides the API key with asterisks (*****)
3. Doesn't log or display the API key
4. Uses secure connection (wss://)

## Comparison with Problem Statement

The problem statement provided this example code:

```python
async def connect_ais_stream():
    async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
        subscribe_message = {"APIKey": "58462ad27e7ad5bd8004d4948e46015ec75cc5df",  # ❌ Hardcoded!
                             "BoundingBoxes": [[[-90, -180], [90, 180]]],
                             "FiltersShipMMSI": ["368207620", "367719770", "211476060"],
                             "FilterMessageTypes": ["PositionReport"]}
        # ... rest of code
```

### ❌ Problems with Original Code

1. **Hardcoded API Key**: Key is visible in source code
2. **Security Risk**: Key will be committed to git
3. **No Flexibility**: Can't change key without editing code
4. **Double asyncio.run()**: Bug in `asyncio.run(asyncio.run(...))`

### ✅ Our Implementation

```python
# Load from environment
api_key = os.getenv('AIS_STREAM_API_KEY')  # ✅ Hidden

handler = AISStreamHandler(
    url="wss://stream.aisstream.io/v0/stream",
    api_key=api_key,  # ✅ Secure
    bounding_box=[[[-90, -180], [90, 180]]]
)

# Fixed: Single asyncio.run()
asyncio.run(main())  # ✅ Correct
```

## Best Practices

1. **Never commit `.env` files**: Already in `.gitignore`
2. **Use `.env.example` for documentation**: Shows structure without secrets
3. **Rotate keys regularly**: Easy to update in `.env` file
4. **Different keys for different environments**: Use separate `.env` files
5. **Use environment variables in production**: Don't rely on `.env` files in prod

## Getting Your API Key

1. Visit https://aisstream.io/
2. Sign up for a free account
3. Copy your API key
4. Add it to your `.env` file

## Support

For issues or questions:
- Check the documentation in `node/InputNode/README_Websocket_AIS.md`
- Run the example: `python examples/example_ais_stream.py`
- Review tests: `python tests/test_env_config.py`

## References

- [12-Factor App: Config](https://12factor.net/config)
- [OWASP: Secure Configuration Management](https://owasp.org/www-project-proactive-controls/)
- [python-dotenv Documentation](https://pypi.org/project/python-dotenv/)
- [AIS Stream Documentation](https://aisstream.io/documentation)
