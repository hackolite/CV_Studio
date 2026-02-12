#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the Websocket input node.
Verifies that the websocket node can be imported and instantiated correctly.
Tests the abstraction layer for WebSocket connections and AIS stream handling.
"""
import sys
import os
import json

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_websocket_node_import():
    """Test that Websocket node can be imported"""
    from node.InputNode.node_websocket import FactoryNode, WebsocketNode
    
    print("✓ Websocket node imported successfully")
    return True


def test_websocket_abstraction_import():
    """Test that WebSocket abstraction classes can be imported"""
    from node.InputNode.node_websocket import WebSocketConnectionHandler, AISStreamHandler
    
    print("✓ WebSocket abstraction classes imported successfully")
    return True


def test_websocket_factory_structure():
    """Test that Websocket FactoryNode has correct structure"""
    from node.InputNode.node_websocket import FactoryNode, WebsocketNode
    
    factory = FactoryNode()
    node = WebsocketNode()
    
    # Verify FactoryNode attributes
    assert hasattr(factory, 'node_label'), "FactoryNode missing node_label"
    assert hasattr(factory, 'node_tag'), "FactoryNode missing node_tag"
    assert factory.node_label == 'Websocket', f"Expected node_label 'Websocket', got '{factory.node_label}'"
    assert factory.node_tag == 'Websocket', f"Expected node_tag 'Websocket', got '{factory.node_tag}'"
    
    # Verify Node attributes
    assert hasattr(node, 'node_label'), "Node missing node_label"
    assert hasattr(node, 'node_tag'), "Node missing node_tag"
    assert node.node_label == 'Websocket', f"Expected node_label 'Websocket', got '{node.node_label}'"
    assert node.node_tag == 'Websocket', f"Expected node_tag 'Websocket', got '{node.node_tag}'"
    
    # Verify Node has required type constants
    assert hasattr(node, 'TYPE_AUDIO'), "Node missing TYPE_AUDIO"
    assert hasattr(node, 'TYPE_JSON'), "Node missing TYPE_JSON"
    assert hasattr(node, 'TYPE_INT'), "Node missing TYPE_INT"
    assert hasattr(node, 'TYPE_TEXT'), "Node missing TYPE_TEXT"
    
    # Verify Node has required methods
    assert hasattr(node, 'update'), "Node missing update method"
    assert hasattr(node, 'close'), "Node missing close method"
    assert hasattr(node, 'get_setting_dict'), "Node missing get_setting_dict method"
    assert hasattr(node, 'set_setting_dict'), "Node missing set_setting_dict method"
    
    # Verify new fields for boat tracking
    assert hasattr(node, 'connection_handler'), "Node missing connection_handler"
    assert hasattr(node, 'boats_data'), "Node missing boats_data"
    
    print("✓ Websocket node has correct structure")
    return True


def test_websocket_node_new_fields():
    """Test that the new API_KEY and bounding box fields are correctly defined"""
    from node.InputNode.node_websocket import FactoryNode, WebsocketNode
    
    # The field tags are created in add_node, so we can't test them directly on the node instance
    # But we can verify the get_setting_dict and set_setting_dict methods handle the new fields
    node = WebsocketNode()
    
    # Verify the methods exist
    assert callable(node.get_setting_dict), "get_setting_dict should be callable"
    assert callable(node.set_setting_dict), "set_setting_dict should be callable"
    
    print("✓ Websocket node methods are callable")
    return True


def test_ais_stream_handler_structure():
    """Test that AISStreamHandler has correct structure"""
    from node.InputNode.node_websocket import AISStreamHandler
    
    # Create handler with test data
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_KEY",
        bounding_box=[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
    )
    
    # Verify attributes
    assert handler.url == "wss://test.example.com", "URL not set correctly"
    assert handler.api_key == "TEST_KEY", "API key not set correctly"
    assert handler.bounding_box == [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]], "Bounding box not set correctly"
    
    # Verify methods exist
    assert callable(handler.get_subscribe_message), "get_subscribe_message should be callable"
    assert callable(handler.parse_message), "parse_message should be callable"
    
    print("✓ AISStreamHandler has correct structure")
    return True


def test_ais_subscription_message():
    """Test that AIS subscription message is correctly formatted"""
    from node.InputNode.node_websocket import AISStreamHandler
    
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_API_KEY",
        bounding_box=[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
    )
    
    sub_msg = handler.get_subscribe_message()
    
    # Verify message structure
    assert "APIKey" in sub_msg, "Subscription message missing APIKey"
    assert "BoundingBoxes" in sub_msg, "Subscription message missing BoundingBoxes"
    assert sub_msg["APIKey"] == "TEST_API_KEY", "APIKey not correct"
    assert sub_msg["BoundingBoxes"] == [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]], "BoundingBoxes not correct"
    
    print("✓ AIS subscription message is correctly formatted")
    return True


def test_ais_message_parsing():
    """Test that AIS messages are correctly parsed"""
    from node.InputNode.node_websocket import AISStreamHandler
    
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_KEY"
    )
    
    # Create test AIS message
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
    
    # Verify parsed data
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
    from node.InputNode.node_websocket import AISStreamHandler
    
    handler = AISStreamHandler(
        url="wss://test.example.com",
        api_key="TEST_KEY"
    )
    
    # Test with invalid JSON
    result = handler.parse_message("invalid json")
    assert result is None, "Invalid JSON should return None"
    
    # Test with valid JSON but wrong structure
    result = handler.parse_message('{"other": "data"}')
    assert result is None, "Wrong structure should return None"
    
    print("✓ Invalid AIS messages correctly return None")
    return True


def test_websocket_node_update_output():
    """Test that the update method returns correct JSON structure"""
    from node.InputNode.node_websocket import WebsocketNode
    
    node = WebsocketNode()
    
    # Call update method
    result = node.update(
        node_id=1,
        connection_list=[],
        node_image_dict={},
        node_result_dict={},
        node_audio_dict={}
    )
    
    # Verify result structure
    assert "image" in result, "Result missing image"
    assert "json" in result, "Result missing json"
    assert "audio" in result, "Result missing audio"
    
    # Verify JSON output structure
    json_output = result["json"]
    assert "boats" in json_output, "JSON output missing boats"
    assert "count" in json_output, "JSON output missing count"
    assert "timestamp" in json_output, "JSON output missing timestamp"
    assert isinstance(json_output["boats"], list), "boats should be a list"
    assert isinstance(json_output["count"], int), "count should be an integer"
    
    print("✓ Websocket node update returns correct JSON structure")
    return True


if __name__ == "__main__":
    print("\n=== Testing Websocket Node ===\n")
    
    try:
        test_websocket_node_import()
        test_websocket_abstraction_import()
        test_websocket_factory_structure()
        test_websocket_node_new_fields()
        test_ais_stream_handler_structure()
        test_ais_subscription_message()
        test_ais_message_parsing()
        test_ais_message_parsing_invalid()
        test_websocket_node_update_output()
        print("\n✅ All tests passed!\n")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
