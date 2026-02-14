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
- GPS Movement Simulation: Simulates moving objects with random paths
- None: No data output
"""

import json
import random
import math
import time
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode


# GPS Movement Simulation name constant
GPS_SIMULATION_NAME = "GPS Movement Simulation"


# Predefined coordinate examples compatible with Map node format
COORDINATE_EXAMPLES = {
    "None": [],
    "AISTRACKER": [
        {"latitude": 49.4431, "longitude": 0.1073, "name": "Vessel Le Havre", "mmsi": "123456789"},
        {"latitude": 51.4545, "longitude": 0.0553, "name": "Cargo Thames", "mmsi": "234567890"},
        {"latitude": 43.2965, "longitude": 5.3698, "name": "Tanker Marseille", "mmsi": "345678901"},
        {"latitude": 41.3851, "longitude": 2.1734, "name": "Ferry Barcelona", "mmsi": "456789012"},
        {"latitude": 39.4699, "longitude": -0.3763, "name": "Cruise Valencia", "mmsi": "567890123"},
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
        {"latitude": 43.5453, "longitude": -5.6615, "name": "Gijón"},
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


class GPSMovementSimulator:
    """
    Simulates GPS movement for various objects.
    Generates random paths simulating realistic movement patterns.
    """
    
    def __init__(self, num_objects=5, center_lat=48.8566, center_lon=2.3522):
        """
        Initialize the GPS movement simulator.
        
        Args:
            num_objects: Number of moving objects to simulate
            center_lat: Center latitude for the simulation area
            center_lon: Center longitude for the simulation area
        """
        self.num_objects = num_objects
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.objects = []
        self.start_time = time.time()
        self._initialize_objects()
    
    def _initialize_objects(self):
        """Initialize objects with random starting positions and velocities."""
        random.seed(42)  # Use a seed for reproducible "random" movements
        
        for i in range(self.num_objects):
            # Random starting position within ~10km radius
            radius_km = random.uniform(0.5, 10)
            angle = random.uniform(0, 2 * math.pi)
            
            # Convert km to degrees (approximate)
            lat_offset = (radius_km / 111.0) * math.cos(angle)
            lon_offset = (radius_km / (111.0 * math.cos(math.radians(self.center_lat)))) * math.sin(angle)
            
            obj = {
                'id': i,
                'name': f'Vehicle-{i+1:03d}',
                'lat': self.center_lat + lat_offset,
                'lon': self.center_lon + lon_offset,
                'speed_kmh': random.uniform(20, 80),  # km/h
                'direction': random.uniform(0, 2 * math.pi),  # radians
                'pattern': random.choice(['linear', 'circular', 'random_walk']),
            }
            self.objects.append(obj)
    
    def update_positions(self, time_elapsed=None):
        """
        Update positions of all objects based on elapsed time.
        
        Args:
            time_elapsed: Time in seconds since start. If None, uses actual elapsed time.
        """
        if time_elapsed is None:
            time_elapsed = time.time() - self.start_time
        
        for obj in self.objects:
            # Update position based on pattern
            if obj['pattern'] == 'linear':
                self._update_linear(obj, time_elapsed)
            elif obj['pattern'] == 'circular':
                self._update_circular(obj, time_elapsed)
            else:  # random_walk
                self._update_random_walk(obj, time_elapsed)
    
    def _update_linear(self, obj, time_elapsed):
        """Update position with linear movement."""
        # Distance traveled in km
        distance_km = (obj['speed_kmh'] / 3600.0) * (time_elapsed % 3600)
        
        # Convert to degrees
        lat_change = (distance_km / 111.0) * math.cos(obj['direction'])
        lon_change = (distance_km / (111.0 * math.cos(math.radians(obj['lat'])))) * math.sin(obj['direction'])
        
        # Update position (modulo to keep in reasonable bounds)
        base_lat = self.center_lat
        base_lon = self.center_lon
        obj['lat'] = base_lat + ((obj['lat'] - base_lat + lat_change) % 0.2) - 0.1
        obj['lon'] = base_lon + ((obj['lon'] - base_lon + lon_change) % 0.2) - 0.1
    
    def _update_circular(self, obj, time_elapsed):
        """Update position with circular movement."""
        # Angular velocity (radians per second)
        angular_velocity = obj['speed_kmh'] / (20.0 * 111.0)  # Assumes ~20km radius
        
        angle = angular_velocity * time_elapsed + obj['direction']
        radius_deg = 0.1  # ~11km radius
        
        obj['lat'] = self.center_lat + radius_deg * math.cos(angle)
        obj['lon'] = self.center_lon + radius_deg * math.sin(angle)
    
    def _update_random_walk(self, obj, time_elapsed):
        """Update position with random walk pattern."""
        # Change direction slightly at each update
        obj['direction'] += random.uniform(-0.3, 0.3)
        
        # Small movement step
        step_size = 0.001  # ~111 meters
        obj['lat'] += step_size * math.cos(obj['direction'])
        obj['lon'] += step_size * math.sin(obj['direction'])
        
        # Keep within bounds
        max_dist = 0.15
        dist_from_center = math.sqrt(
            (obj['lat'] - self.center_lat)**2 + 
            (obj['lon'] - self.center_lon)**2
        )
        if dist_from_center > max_dist:
            # Turn back toward center
            obj['direction'] = math.atan2(
                self.center_lon - obj['lon'],
                self.center_lat - obj['lat']
            )
    
    def get_coordinates(self):
        """
        Get current coordinates of all objects.
        
        Returns:
            List of coordinate dictionaries compatible with Map node
        """
        coordinates = []
        for obj in self.objects:
            coordinates.append({
                'latitude': obj['lat'],
                'longitude': obj['lon'],
                'name': obj['name'],
                'info': f"{obj['pattern']} - {obj['speed_kmh']:.1f} km/h"
            })
        return coordinates

def get_example_names():
    """Get list of available example names for the dropdown."""
    # Static examples first, then add GPS simulation
    static_names = list(COORDINATE_EXAMPLES.keys())
    return static_names + [GPS_SIMULATION_NAME]


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
    _ver = '1.0.2'

    node_label = 'CoordinateExamples'
    node_tag = 'CoordinateExamples'

    _opencv_setting_dict = None

    def __init__(self):
        self.gps_simulator = None  # Will be initialized when GPS simulation is selected
        self.last_update_time = None  # Track last GPS update time
        self.update_interval = 1.0  # Update GPS positions every 1 second
        self.last_coordinates = []  # Cache last generated coordinates
    
    @staticmethod
    def on_selection_change(sender, app_data, user_data):
        """Callback when dropdown selection changes."""
        node, node_id = user_data
        selected_example = app_data
        
        # Reset GPS simulator when switching away from GPS simulation
        if selected_example != GPS_SIMULATION_NAME and hasattr(node, 'gps_simulator'):
            node.gps_simulator = None
            node.last_update_time = None
            node.last_coordinates = []
        
        # Get the coordinates for the selected example
        if selected_example == GPS_SIMULATION_NAME:
            # For GPS simulation, show dynamic message
            num_points = 5  # Default number
            status_text = f'Simulating {num_points} moving objects (updates every 1s)'
        else:
            coordinates = COORDINATE_EXAMPLES.get(selected_example, [])
            num_points = len(coordinates)
            
            if num_points > 0:
                status_text = f'{num_points} points ({selected_example})'
            else:
                status_text = 'No data (None selected)'
        
        # Update status text
        tag_node_name = str(node_id) + ':' + node.node_tag
        status_tag = tag_node_name + ':StatusValue'
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
        
        # Handle GPS Movement Simulation
        if selected_example == GPS_SIMULATION_NAME:
            # Initialize simulator if not already done
            if self.gps_simulator is None:
                # Default: Paris, France as center
                self.gps_simulator = GPSMovementSimulator(
                    num_objects=5,
                    center_lat=48.8566,
                    center_lon=2.3522
                )
                self.last_update_time = time.time()
                # Get initial coordinates immediately so first call has data
                self.last_coordinates = self.gps_simulator.get_coordinates()
            
            # Check if enough time has elapsed for an update (1 second interval)
            current_time = time.time()
            time_elapsed = current_time - self.last_update_time
            
            if time_elapsed >= self.update_interval:
                # Update positions for current time
                self.gps_simulator.update_positions()
                
                # Get current coordinates
                self.last_coordinates = self.gps_simulator.get_coordinates()
                
                # Update the last update time
                self.last_update_time = current_time
            
            # Return the last generated coordinates (updated every second)
            json_output = self.last_coordinates
        else:
            # Get static coordinates for the selected example
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
        
        # Log generated JSON for debugging
        print(f"CoordinateExamples node: Sending {len(json_output) if isinstance(json_output, list) else 0} coordinates")
        if json_output and isinstance(json_output, list) and len(json_output) > 0:
            try:
                import json as json_module
                json_str = json_module.dumps(json_output[0], indent=2)
                print(f"CoordinateExamples node: First coordinate:\n{json_str}")
            except Exception as e:
                print(f"CoordinateExamples node: Could not serialize first coordinate: {e}")
        
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
        if selected_example == GPS_SIMULATION_NAME:
            status_text = 'Simulating 5 moving objects (updates every 1s)'
        else:
            coordinates = COORDINATE_EXAMPLES.get(selected_example, [])
            num_points = len(coordinates)
            if num_points > 0:
                status_text = f'{num_points} points ({selected_example})'
            else:
                status_text = 'No data (None selected)'
        dpg_set_value(status_tag, status_text)
