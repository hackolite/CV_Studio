#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Coordinate Examples Node

This node provides a dropdown list with predefined coordinate examples
that can be used with the Map visualization node. No external server required.

Examples include:
- AISTRACKER: Sample boat positions (AIS-like data)
- World Cities: Major cities around the world
- European Ports: Maritime port coordinates
- None: No data output
"""

import json
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode


# Predefined coordinate examples compatible with Map node format
COORDINATE_EXAMPLES = {
    "None": [],
    "AISTRACKER": [
        {"latitude": 48.8566, "longitude": 2.3522, "name": "Vessel Paris", "mmsi": "123456789"},
        {"latitude": 51.5074, "longitude": -0.1278, "name": "Cargo London", "mmsi": "234567890"},
        {"latitude": 43.2965, "longitude": 5.3698, "name": "Tanker Marseille", "mmsi": "345678901"},
        {"latitude": 41.3851, "longitude": 2.1734, "name": "Ferry Barcelona", "mmsi": "456789012"},
        {"latitude": 40.4168, "longitude": -3.7038, "name": "Cruise Madrid", "mmsi": "567890123"},
    ],
    "World Cities": [
        {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
        {"latitude": 35.6762, "longitude": 139.6503, "name": "Tokyo"},
        {"latitude": -33.8688, "longitude": 151.2093, "name": "Sydney"},
        {"latitude": 37.7749, "longitude": -122.4194, "name": "San Francisco"},
        {"latitude": 52.5200, "longitude": 13.4050, "name": "Berlin"},
        {"latitude": 1.3521, "longitude": 103.8198, "name": "Singapore"},
    ],
    "European Ports": [
        {"latitude": 51.9244, "longitude": 4.4777, "name": "Rotterdam"},
        {"latitude": 53.5511, "longitude": 9.9937, "name": "Hamburg"},
        {"latitude": 51.2277, "longitude": 4.4074, "name": "Antwerp"},
        {"latitude": 49.4431, "longitude": 0.1073, "name": "Le Havre"},
        {"latitude": 36.1408, "longitude": -5.3536, "name": "Gibraltar"},
        {"latitude": 43.1242, "longitude": -5.9458, "name": "Gijon"},
    ],
    "Mediterranean Sea": [
        {"latitude": 36.7213, "longitude": -4.4214, "name": "Malaga"},
        {"latitude": 43.2965, "longitude": 5.3698, "name": "Marseille"},
        {"latitude": 43.7102, "longitude": 7.2620, "name": "Nice"},
        {"latitude": 41.1171, "longitude": 16.8719, "name": "Bari"},
        {"latitude": 35.8989, "longitude": 14.5146, "name": "Malta"},
        {"latitude": 37.9838, "longitude": 23.7275, "name": "Athens"},
    ],
}


def get_example_names():
    """Get list of available example names for the dropdown."""
    return list(COORDINATE_EXAMPLES.keys())


class FactoryNode:
    node_label = 'CoordinateExamples'
    node_tag = 'CoordinateExamples'
    
    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=[0, 0],
        opencv_setting_dict=None,
        callback=None,
    ):
        """Adds a Coordinate Examples node with a dropdown to select predefined coordinate datasets."""
        
        # Generate node instance
        node = Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        
        # Dropdown tag for example selection
        node.tag_node_dropdown_name = node.tag_node_name + ':Dropdown'
        node.tag_node_dropdown_value_name = node.tag_node_name + ':DropdownValue'
        
        # Status text tag
        node.tag_node_status_name = node.tag_node_name + ':Status'
        node.tag_node_status_value_name = node.tag_node_name + ':StatusValue'
        
        # Output tags (JSON type for coordinates)
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'
        
        node._opencv_setting_dict = opencv_setting_dict

        small_window_w = 200

        # Create yellow theme for JSON button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 128, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 64, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))

        # Create node in the GUI
        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Dropdown for selecting example dataset
            with dpg.node_attribute(
                tag=node.tag_node_dropdown_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_dropdown_value_name,
                    items=get_example_names(),
                    label="Example",
                    default_value="AISTRACKER",
                    width=small_window_w - 60,
                    callback=lambda s, a, u: Node.on_selection_change(s, a, u),
                    user_data=(node, node_id),
                )
            
            # Status text showing number of points
            with dpg.node_attribute(
                tag=node.tag_node_status_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_status_value_name,
                    default_value='5 points (AISTRACKER)',
                )
            
            # JSON output
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="JSON (Coordinates)",
                    tag=node.tag_node_output01_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                    
        return node


class Node(BaseNode):
    _ver = '1.0.0'

    node_label = 'CoordinateExamples'
    node_tag = 'CoordinateExamples'

    _opencv_setting_dict = None

    def __init__(self):
        pass
    
    @staticmethod
    def on_selection_change(sender, app_data, user_data):
        """Callback when dropdown selection changes."""
        node, node_id = user_data
        selected_example = app_data
        
        # Get the coordinates for the selected example
        coordinates = COORDINATE_EXAMPLES.get(selected_example, [])
        num_points = len(coordinates)
        
        # Update status text
        tag_node_name = str(node_id) + ':' + node.node_tag
        status_tag = tag_node_name + ':StatusValue'
        
        if num_points > 0:
            status_text = f'{num_points} points ({selected_example})'
        else:
            status_text = 'No data (None selected)'
        
        dpg_set_value(status_tag, status_text)

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """Coordinate Examples node outputs the selected example coordinates as JSON."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        dropdown_tag = tag_node_name + ':DropdownValue'
        
        # Get selected example name
        selected_example = dpg_get_value(dropdown_tag)
        if selected_example is None:
            selected_example = "None"
        
        # Get the coordinates for the selected example
        coordinates = COORDINATE_EXAMPLES.get(selected_example, [])
        
        # Return coordinates in format compatible with Map node
        # Map node expects [{"latitude": x, "longitude": y, ...}]
        # or {"boats": [...]} format
        if coordinates:
            # Output as a list of coordinate objects (compatible with Map node)
            json_output = coordinates
        else:
            # Return empty list when None selected
            json_output = []
        
        return {"image": None, "json": json_output, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        """Save the current dropdown selection."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        dropdown_tag = tag_node_name + ':DropdownValue'

        selected_example = dpg_get_value(dropdown_tag)
        if selected_example is None:
            selected_example = "AISTRACKER"
        
        pos = dpg.get_item_pos(tag_node_name)
        
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[dropdown_tag] = selected_example
        
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Restore the dropdown selection."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        dropdown_tag = tag_node_name + ':DropdownValue'
        status_tag = tag_node_name + ':StatusValue'

        selected_example = setting_dict.get(dropdown_tag, "AISTRACKER")
        dpg_set_value(dropdown_tag, selected_example)
        
        # Update status text
        coordinates = COORDINATE_EXAMPLES.get(selected_example, [])
        num_points = len(coordinates)
        if num_points > 0:
            status_text = f'{num_points} points ({selected_example})'
        else:
            status_text = 'No data (None selected)'
        dpg_set_value(status_tag, status_text)
