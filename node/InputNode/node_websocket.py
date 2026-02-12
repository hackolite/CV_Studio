#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import threading
import queue

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


# Abstract WebSocket Connection Handler
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


# AIS Stream Handler Implementation
class AISStreamHandler(WebSocketConnectionHandler):
    """Handler for AIS (Automatic Identification System) stream connections.
    
    This handler connects to AIS streaming services and filters boat data based on
    bounding box coordinates.
    
    Example usage:
        handler = AISStreamHandler(
            url="wss://stream.aisstream.io/v0/stream",
            api_key="YOUR_API_KEY_HERE",
            bounding_box=[[[-90, -180], [-90, 180], [90, 180], [90, -180], [-90, -180]]]
        )
    """
    
    def __init__(self, url: str, api_key: str, bounding_box: Optional[List] = None):
        super().__init__(url, api_key)
        self.bounding_box = bounding_box or self._get_default_bounding_box()
        self.websocket = None
        
    def _get_default_bounding_box(self) -> List:
        """Return a default bounding box covering the entire world.
        
        Bounding box format: [[longitude, latitude], ...]
        Example: Mediterranean Sea region
        """
        return [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
    
    def get_subscribe_message(self) -> Dict[str, Any]:
        """Get the AIS stream subscription message.
        
        Returns:
            Dictionary with APIKey and BoundingBoxes for subscription
            
        Example:
            {
                "APIKey": "YOUR_API_KEY_HERE",
                "BoundingBoxes": [[[-90, -180], [-90, 180], [90, 180], [90, -180], [-90, -180]]]
            }
        """
        return {
            "APIKey": self.api_key,
            "BoundingBoxes": self.bounding_box
        }
    
    def parse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse AIS stream message and extract boat information.
        
        Args:
            message: Raw JSON message from AIS stream
            
        Returns:
            Parsed boat data with relevant fields or None if parsing fails
        """
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
            # Import websockets only when needed
            import websockets
            
            async with websockets.connect(self.url) as websocket:
                self.websocket = websocket
                self.is_connected = True
                
                # Send subscription message
                subscribe_message = self.get_subscribe_message()
                await websocket.send(json.dumps(subscribe_message))
                
                # Handle incoming messages
                await self.handle_messages()
                
        except ImportError:
            print("Error: 'websockets' package is not installed. Please run: pip install websockets")
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
                    # Add to queue if not full
                    if not self.message_queue.full():
                        self.message_queue.put(boat_data)
                        
        except Exception as e:
            print(f"Error handling AIS messages: {e}")
            self.is_connected = False


class FactoryNode:
    node_label = 'Websocket'
    node_tag = 'Websocket'
    
    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Adds a WebSocket node with AIS stream support.
        
        This node supports connecting to WebSocket services like AIS streams.
        Example configuration:
        - URL: wss://stream.aisstream.io/v0/stream
        - API Key: YOUR_API_KEY_HERE
        - Bounding Box: [[[-90, -180], [-90, 180], [90, 180], [90, -180], [-90, -180]]]
        """
        
        # Generate tags for Node and its attributes
        node = WebsocketNode()
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        
        tag_input_url = f"{node.tag_node_name}:InputURL"
        tag_start_button = f"{node.tag_node_name}:StartButton"
        
        # URL input field
        node.tag_node_input_text_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input_text_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'
        
        # API_KEY input field
        node.tag_node_input_apikey_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':InputAPIKey'
        node.tag_node_input_apikey_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':InputAPIKeyValue'
        
        # Bounding box input field (JSON format)
        node.tag_node_input_bbox_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':InputBBox'
        node.tag_node_input_bbox_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':InputBBoxValue'
        
        # Use node.node_tag instead of self.node_tag
        tag_node_name = str(node_id) + ':' + node.node_tag
        tag_node_output01_name = tag_node_name + ':' + node.TYPE_INT + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + node.TYPE_INT + ':Output01Value'

        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        small_window_w = 280

        # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))          # Yellow background
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 128, 255)) # Light yellow on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 64, 255))   # Darker yellow on press
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))                # Black text for better readability
        
        # Outputs audio, json, float, elapsed time as disabled yellow buttons
        def add_yellow_disabled_button(label, tag):
            btn = dpg.add_button(
                label=label,
                tag=tag,
                enabled=False,
                width=small_window_w
            )
            dpg.bind_item_theme(btn, yellow_button_theme)
            return btn  

        # Create node in the GUI
        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):  
            # Input field for WebSocket URL
            with dpg.node_attribute(tag=node.tag_node_input_text_name, attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_text(
                    tag=node.tag_node_input_text_value_name, 
                    width=small_window_w, 
                    hint="wss://stream.aisstream.io/v0/stream",
                    default_value="wss://stream.aisstream.io/v0/stream"
                )
        
            # Input field for API_KEY
            with dpg.node_attribute(tag=node.tag_node_input_apikey_name, attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_text(
                    tag=node.tag_node_input_apikey_value_name, 
                    width=small_window_w, 
                    hint="YOUR_API_KEY_HERE", 
                    password=True
                )
        
            # Input field for bounding box (JSON format)
            with dpg.node_attribute(tag=node.tag_node_input_bbox_name, attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_text(
                    tag=node.tag_node_input_bbox_value_name, 
                    width=small_window_w, 
                    hint='[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]',
                    multiline=True,
                    height=60,
                    default_value='[[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]'
                )
        
            # Start button
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                btn = dpg.add_button(label="Start", tag=tag_start_button, callback=callback, user_data=tag_input_url, width=small_window_w)
                dpg.bind_item_theme(btn, yellow_button_theme)
                
            # Outputs
            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                    
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                add_yellow_disabled_button("JSON (Boats)", node.tag_node_output_json_value_name)
                    
        return node


class WebsocketNode(BaseNode):
    """WebSocket node for processing WebSocket connections with AIS boat tracking support.
    
    This node implements an abstraction layer for WebSocket connections with specific
    support for AIS (Automatic Identification System) streams that provide boat tracking data.
    
    Features:
    - Abstract WebSocket connection handling
    - AIS stream integration with bounding box filtering
    - JSON output with boat information
    - Real-time data streaming
    
    Example Configuration:
    - URL: wss://stream.aisstream.io/v0/stream
    - API Key: YOUR_API_KEY_HERE
    - Bounding Box: [[[-5, 36], [36, 36], [36, 46], [-5, 46], [-5, 36]]]
      (This example covers the Mediterranean Sea region)
    
    The node outputs JSON data containing boat information:
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
        ]
    }
    """
    _ver = '0.0.2'
    
    # Configuration constants
    MAX_BOATS_STORED = 100  # Maximum number of boat entries to keep in memory
    THREAD_SHUTDOWN_TIMEOUT = 2.0  # Timeout in seconds for thread shutdown

    def __init__(self):
        super().__init__()  # Call parent constructor
        self.node_label = 'Websocket'
        self.node_tag = 'Websocket'
        self.connection_handler = None
        self.connection_thread = None
        self.boats_data = []

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        """Update method called by the processing graph.
        
        Returns:
            Dictionary with image, json, and audio outputs
        """
        # Collect boat data from the queue
        if self.connection_handler and self.connection_handler.is_connected:
            while not self.connection_handler.message_queue.empty():
                try:
                    boat_data = self.connection_handler.message_queue.get_nowait()
                    self.boats_data.append(boat_data)
                    
                    # Keep only last MAX_BOATS_STORED boats to avoid memory issues
                    if len(self.boats_data) > self.MAX_BOATS_STORED:
                        self.boats_data = self.boats_data[-self.MAX_BOATS_STORED:]
                        
                except queue.Empty:
                    break
        
        # Return JSON output with boats list
        json_output = {
            "boats": self.boats_data,
            "count": len(self.boats_data),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return {"image": None, "json": json_output, "audio": None}


    def close(self, node_id):
        """Clean up when node is closed."""
        if self.connection_handler:
            self.connection_handler.is_connected = False
        if self.connection_thread and self.connection_thread.is_alive():
            # Wait for thread to finish with configured timeout
            self.connection_thread.join(timeout=self.THREAD_SHUTDOWN_TIMEOUT)


    def get_setting_dict(self, node_id):
        """Get node settings for saving."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value_tag = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'
        
        # Tags for the input fields
        url_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        apikey_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':InputAPIKeyValue'
        bbox_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':InputBBoxValue'

        output_value = round((dpg_get_value(output_value_tag)), 3)
        url_value_raw = dpg_get_value(url_value_tag)
        url_value = url_value_raw if url_value_raw else ""
        apikey_value_raw = dpg_get_value(apikey_value_tag)
        apikey_value = apikey_value_raw if apikey_value_raw else ""
        bbox_value_raw = dpg_get_value(bbox_value_tag)
        bbox_value = bbox_value_raw if bbox_value_raw else ""
        
        pos = dpg.get_item_pos(tag_node_name)
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[output_value_tag] = output_value
        setting_dict[url_value_tag] = url_value
        setting_dict[apikey_value_tag] = apikey_value
        setting_dict[bbox_value_tag] = bbox_value
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Restore node settings from saved data."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value_tag = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'
        
        # Tags for the input fields
        url_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        apikey_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':InputAPIKeyValue'
        bbox_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':InputBBoxValue'

        output_value = float(setting_dict[output_value_tag])
        dpg_set_value(output_value_tag, output_value)
        
        # Set the input field values if they exist in the setting dict
        if url_value_tag in setting_dict:
            dpg_set_value(url_value_tag, setting_dict[url_value_tag])
        if apikey_value_tag in setting_dict:
            dpg_set_value(apikey_value_tag, setting_dict[apikey_value_tag])
        if bbox_value_tag in setting_dict:
            dpg_set_value(bbox_value_tag, setting_dict[bbox_value_tag])


# Test code to verify that the node displays correctly
if __name__ == "__main__":
    dpg.create_context()
    
    with dpg.window(label="Test WebSocket Node", width=800, height=600):
        with dpg.node_editor(label="Node Editor"):
            factory = FactoryNode()
            factory.add_node(parent=dpg.last_item(), node_id=1, pos=[100, 100])
    
    dpg.create_viewport(title='Test WebSocket Node', width=900, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
