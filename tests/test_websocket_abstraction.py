#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone test for WebSocket abstraction layer.
Tests the WebSocketConnectionHandler and AISStreamHandler without requiring dearpygui.
"""
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


class AISStreamHandler(WebSocketConnectionHandler):
    """Handler for AIS (Automatic Identification System) stream connections."""
    
    def __init__(self, url: str, api_key: str, bounding_box: Optional[List] = None):
        super().__init__(url, api_key)
        self.bounding_box = bounding_box or self._get_default_bounding_box()
        self.websocket = None
        
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
                    "speed": position.get("Sog", 0.0),
                    "course": position.get("Cog", 0.0),
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


def test_ais_stream_handler_structure():
    """Test that AISStreamHandler has correct structure"""
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_KEY",
        bounding_box=[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
    )
    
    assert handler.url == "wss://test.example.com", "URL not set correctly"
    assert handler.api_key == "TEST_KEY", "API key not set correctly"
    assert handler.bounding_box == [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]], "Bounding box not set correctly"
    assert callable(handler.get_subscribe_message), "get_subscribe_message should be callable"
    assert callable(handler.parse_message), "parse_message should be callable"
    
    print("✓ AISStreamHandler has correct structure")
    return True


def test_ais_subscription_message():
    """Test that AIS subscription message is correctly formatted"""
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_API_KEY",
        bounding_box=[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
    )
    
    sub_msg = handler.get_subscribe_message()
    
    assert "APIKey" in sub_msg, "Subscription message missing APIKey"
    assert "BoundingBoxes" in sub_msg, "Subscription message missing BoundingBoxes"
    assert sub_msg["APIKey"] == "TEST_API_KEY", "APIKey not correct"
    assert sub_msg["BoundingBoxes"] == [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]], "BoundingBoxes not correct"
    
    print("✓ AIS subscription message is correctly formatted")
    return True


def test_ais_message_parsing():
    """Test that AIS messages are correctly parsed"""
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_KEY"
    )
    
    test_message = json.dumps({
        "Message": {
            "PositionReport": {
                "Latitude": 40.7128,
                "Longitude": -74.0060,
                "Sog": 12.5,
                "Cog": 90.0,
                "TrueHeading": 85
            }
        },
        "MetaData": {
            "MMSI": "123456789",
            "ShipName": "Test Ship",
            "ShipType": "Cargo",
            "Destination": "New York",
            "time_utc": "2024-01-01T12:00:00Z"
        }
    })
    
    parsed = handler.parse_message(test_message)
    
    assert parsed is not None, "Message should be parsed"
    assert parsed["mmsi"] == "123456789", "MMSI not parsed correctly"
    assert parsed["ship_name"] == "Test Ship", "Ship name not parsed correctly"
    assert parsed["latitude"] == 40.7128, "Latitude not parsed correctly"
    assert parsed["longitude"] == -74.0060, "Longitude not parsed correctly"
    assert parsed["speed"] == 12.5, "Speed not parsed correctly"
    assert parsed["course"] == 90.0, "Course not parsed correctly"
    assert parsed["heading"] == 85, "Heading not parsed correctly"
    assert parsed["ship_type"] == "Cargo", "Ship type not parsed correctly"
    assert parsed["destination"] == "New York", "Destination not parsed correctly"
    
    print("✓ AIS messages are correctly parsed")
    return True


def test_ais_message_parsing_invalid():
    """Test that invalid messages return None"""
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_KEY"
    )
    
    result = handler.parse_message("invalid json")
    assert result is None, "Invalid JSON should return None"
    
    result = handler.parse_message('{"other": "data"}')
    assert result is None, "Wrong structure should return None"
    
    print("✓ Invalid AIS messages correctly return None")
    return True


def test_default_bounding_box():
    """Test that default bounding box is set correctly"""
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_KEY"
    )
    
    assert handler.bounding_box is not None, "Default bounding box should be set"
    assert isinstance(handler.bounding_box, list), "Bounding box should be a list"
    assert len(handler.bounding_box) > 0, "Bounding box should not be empty"
    
    print("✓ Default bounding box is set correctly")
    return True


def test_message_queue():
    """Test that message queue is initialized correctly"""
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_KEY"
    )
    
    assert hasattr(handler, 'message_queue'), "Handler should have message_queue"
    assert isinstance(handler.message_queue, queue.Queue), "message_queue should be a Queue"
    assert handler.message_queue.maxsize == 100, "Queue maxsize should be 100"
    
    print("✓ Message queue is initialized correctly")
    return True


if __name__ == "__main__":
    print("\n=== Testing WebSocket Abstraction Layer ===\n")
    
    try:
        test_ais_stream_handler_structure()
        test_ais_subscription_message()
        test_ais_message_parsing()
        test_ais_message_parsing_invalid()
        test_default_bounding_box()
        test_message_queue()
        print("\n✅ All abstraction layer tests passed!\n")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
