#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script demonstrating the WebSocket AIS Stream handler.

This example shows how to:
1. Create an AIS stream handler
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
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import queue


class WebSocketConnectionHandler:
    """Abstract base class for handling WebSocket connections with different protocols."""
    
    def __init__(self, url: str, api_key: str = ""):
        self.url = url
        self.api_key = api_key
        self.is_connected = False
        self.message_queue = queue.Queue(maxsize=100)
        
    async def connect(self):
        """Connect to the WebSocket server. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement connect()")
    
    def get_subscribe_message(self) -> Dict[str, Any]:
        """Get the subscription message for the WebSocket. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement get_subscribe_message()")
    
    def parse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse incoming WebSocket message. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement parse_message()")
    
    async def handle_messages(self):
        """Handle incoming messages from WebSocket."""
        raise NotImplementedError("Subclasses must implement handle_messages()")


class AISStreamHandler(WebSocketConnectionHandler):
    """Handler for AIS (Automatic Identification System) stream connections."""
    
    def __init__(self, url: str, api_key: str, bounding_box: Optional[List] = None):
        super().__init__(url, api_key)
        self.bounding_box = bounding_box or self._get_default_bounding_box()
        self.websocket = None
        self.boat_count = 0
        
    def _get_default_bounding_box(self) -> List:
        """Return a default bounding box covering the Mediterranean Sea region."""
        return [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
    
    def get_subscribe_message(self) -> Dict[str, Any]:
        """Get the AIS stream subscription message."""
        return {
            "APIKey": self.api_key,
            "BoundingBoxes": self.bounding_box
        }
    
    def parse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse AIS stream message and extract boat information."""
        try:
            data = json.loads(message)
            
            # Extract relevant boat information
            if "Message" in data and "PositionReport" in data["Message"]:
                position = data["Message"]["PositionReport"]
                metadata = data.get("MetaData", {})
                
                boat_info = {
                    "mmsi": metadata.get("MMSI", "Unknown"),
                    "ship_name": metadata.get("ShipName", "Unknown"),
                    "latitude": position.get("Latitude", 0.0),
                    "longitude": position.get("Longitude", 0.0),
                    "speed": position.get("Sog", 0.0),  # Speed over ground
                    "course": position.get("Cog", 0.0),  # Course over ground
                    "heading": position.get("TrueHeading", 0),
                    "timestamp": metadata.get("time_utc", datetime.now(timezone.utc).isoformat()),
                    "ship_type": metadata.get("ShipType", "Unknown"),
                    "destination": metadata.get("Destination", "Unknown")
                }
                
                return boat_info
            
            return None
            
        except json.JSONDecodeError:
            return None
        except Exception as e:
            print(f"Error parsing AIS message: {e}")
            return None
    
    async def connect(self):
        """Connect to AIS stream WebSocket server."""
        try:
            import websockets
            
            print(f"Connecting to {self.url}...")
            async with websockets.connect(self.url) as websocket:
                self.websocket = websocket
                self.is_connected = True
                print("✓ Connected successfully!")
                
                # Send subscription message
                subscribe_message = self.get_subscribe_message()
                await websocket.send(json.dumps(subscribe_message))
                print("✓ Subscription message sent")
                print(f"  Monitoring region: {self.bounding_box}")
                print("\nWaiting for boat data...\n")
                
                # Handle incoming messages
                await self.handle_messages()
                
        except ImportError:
            print("Error: 'websockets' package is not installed.")
            print("Please run: pip install websockets")
            self.is_connected = False
        except Exception as e:
            print(f"Error connecting to AIS stream: {e}")
            self.is_connected = False
    
    async def handle_messages(self):
        """Handle incoming AIS messages."""
        if not self.websocket:
            return
            
        try:
            async for message in self.websocket:
                boat_data = self.parse_message(message)
                if boat_data:
                    self.boat_count += 1
                    
                    # Print boat information
                    print(f"Boat #{self.boat_count}")
                    print(f"  MMSI: {boat_data['mmsi']}")
                    print(f"  Name: {boat_data['ship_name']}")
                    print(f"  Position: ({boat_data['latitude']:.4f}, {boat_data['longitude']:.4f})")
                    print(f"  Speed: {boat_data['speed']:.1f} knots")
                    print(f"  Course: {boat_data['course']:.1f}°")
                    print(f"  Type: {boat_data['ship_type']}")
                    print(f"  Destination: {boat_data['destination']}")
                    print(f"  Timestamp: {boat_data['timestamp']}")
                    print("-" * 60)
                    
        except KeyboardInterrupt:
            print("\n\nStopping...")
        except Exception as e:
            print(f"Error handling AIS messages: {e}")
            self.is_connected = False


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
    
    # Create AIS stream handler
    handler = AISStreamHandler(
        url="wss://stream.aisstream.io/v0/stream",
        api_key=api_key,
        bounding_box=bounding_box
    )
    
    # Connect and receive messages
    try:
        await handler.connect()
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    print("=" * 60)
    print("AIS Stream WebSocket Example")
    print("=" * 60)
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
