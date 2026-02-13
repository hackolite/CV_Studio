#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script demonstrating the WebSocket AIS Stream handler with secure API key management.

This example shows how to:
1. Import and use the AIS stream handler from CV Studio
2. Load API key securely from environment variables
3. Connect to the AIS stream service
4. Receive and parse boat data
5. Process boat information in real-time

Requirements:
    pip install websockets python-dotenv

Usage:
    # Method 1: Using .env file (recommended for development)
    1. Copy .env.example to .env
    2. Add your API key to .env file: AIS_STREAM_API_KEY=your_key_here
    3. Run: python example_ais_stream.py
    
    # Method 2: Using environment variable
    export AIS_STREAM_API_KEY='your_key_here'
    python example_ais_stream.py
    
    # Method 3: Using command line argument (not recommended for production)
    python example_ais_stream.py YOUR_API_KEY
    
Get your free API key at: https://aisstream.io/
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    # Try to load .env from project root
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    print("Warning: python-dotenv not installed. Install it with: pip install python-dotenv")

# Add parent directory to path to import from CV Studio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the AIS stream handler from CV Studio
from node.InputNode.node_websocket import AISStreamHandler


async def main():
    """Main function to run the AIS stream example."""
    
    # Try to get API key from environment variable first
    api_key = os.getenv('AIS_STREAM_API_KEY')
    
    # If not in environment, check command line argument
    if not api_key and len(sys.argv) >= 2:
        api_key = sys.argv[1]
    
    # If still no API key, show usage instructions
    if not api_key:
        print("Error: No API key provided!")
        print("\nYou can provide the API key in two ways:")
        print("1. Set environment variable: export AIS_STREAM_API_KEY='your_key_here'")
        print("2. Create a .env file with: AIS_STREAM_API_KEY=your_key_here")
        print("3. Pass as command line argument: python example_ais_stream.py YOUR_API_KEY")
        print("\nGet your free API key at: https://aisstream.io/")
        print("\nExample bounding boxes:")
        print("  Mediterranean Sea: [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]")
        print("  North Atlantic: [[[-80, 20], [-10, 20], [-10, 60], [-80, 60], [-80, 20]]]")
        print("  Global: [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]")
        sys.exit(1)
    
    # Optional: Get bounding box from environment variable or command line
    bounding_box = None
    
    # Try environment variable first
    bbox_env = os.getenv('AIS_STREAM_BOUNDING_BOX')
    if bbox_env:
        try:
            bounding_box = json.loads(bbox_env)
        except json.JSONDecodeError:
            print("Warning: Invalid bounding box in environment variable, using default")
    
    # Command line argument overrides environment variable
    # If API key came from command line (sys.argv[1]), bounding box is at sys.argv[2]
    # If API key came from environment, bounding box is at sys.argv[1]
    api_key_from_cmdline = len(sys.argv) >= 2 and sys.argv[1] == api_key
    bbox_index = 2 if api_key_from_cmdline else 1
    
    if len(sys.argv) > bbox_index:
        try:
            bounding_box = json.loads(sys.argv[bbox_index])
        except json.JSONDecodeError:
            print("Warning: Invalid bounding box JSON in command line, using default")
    
    # Get WebSocket URL from environment variable or use default
    url = os.getenv('AIS_STREAM_URL', 'wss://stream.aisstream.io/v0/stream')
    
    # Create AIS stream handler using CV Studio's implementation
    handler = AISStreamHandler(
        url=url,
        api_key=api_key,
        bounding_box=bounding_box
    )
    
    print(f"Connecting to {handler.url}...")
    print(f"Monitoring region: {handler.bounding_box}")
    print("\nWaiting for boat data...\n")
    
    boat_count = 0
    
    # Connect and receive messages
    try:
        import websockets
        
        async with websockets.connect(handler.url) as websocket:
            handler.websocket = websocket
            handler.is_connected = True
            print("✓ Connected successfully!")
            
            # Send subscription message
            subscribe_message = handler.get_subscribe_message()
            await websocket.send(json.dumps(subscribe_message))
            print("✓ Subscription message sent\n")
            
            # Handle incoming messages
            async for message in websocket:
                boat_data = handler.parse_message(message)
                if boat_data:
                    boat_count += 1
                    
                    # Print boat information
                    print(f"Boat #{boat_count}")
                    print(f"  MMSI: {boat_data['mmsi']}")
                    print(f"  Name: {boat_data['ship_name']}")
                    print(f"  Position: ({boat_data['latitude']:.4f}, {boat_data['longitude']:.4f})")
                    print(f"  Speed: {boat_data['speed']:.1f} knots")
                    print(f"  Course: {boat_data['course']:.1f}°")
                    print(f"  Type: {boat_data['ship_type']}")
                    print(f"  Destination: {boat_data['destination']}")
                    print(f"  Timestamp: {boat_data['timestamp']}")
                    print("-" * 60)
                    
    except ImportError:
        print("Error: 'websockets' package is not installed.")
        print("Please run: pip install websockets")
    except KeyboardInterrupt:
        print("\n\nStopping...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("AIS Stream WebSocket Example")
    print("=" * 60)
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
