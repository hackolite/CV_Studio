#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script demonstrating the WebSocket AIS Stream handler.

This example shows how to:
1. Import and use the AIS stream handler from CV Studio
2. Connect to the AIS stream service
3. Receive and parse boat data
4. Process boat information in real-time

Requirements:
    pip install websockets

Usage:
    python example_ais_stream.py YOUR_API_KEY
    
Get your free API key at: https://aisstream.io/
"""

import asyncio
import json
import sys
import os

# Add parent directory to path to import from CV Studio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the AIS stream handler from CV Studio
from node.InputNode.node_websocket import AISStreamHandler


async def main():
    """Main function to run the AIS stream example."""
    
    # Check if API key is provided
    if len(sys.argv) < 2:
        print("Usage: python example_ais_stream.py YOUR_API_KEY")
        print("\nGet your free API key at: https://aisstream.io/")
        print("\nExample bounding boxes:")
        print("  Mediterranean Sea: [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]")
        print("  North Atlantic: [[[-80, 20], [-10, 20], [-10, 60], [-80, 60], [-80, 20]]]")
        print("  Global: [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    # Optional: Custom bounding box from command line
    bounding_box = None
    if len(sys.argv) > 2:
        try:
            bounding_box = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print("Warning: Invalid bounding box JSON, using default")
    
    # Create AIS stream handler using CV Studio's implementation
    handler = AISStreamHandler(
        url="wss://stream.aisstream.io/v0/stream",
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
