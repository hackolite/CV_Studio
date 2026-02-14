#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Map Visualization Node for CV Studio

This node provides interactive map visualization using:
- contextily: For downloading OpenStreetMap tiles
- matplotlib: For rendering maps with GPS points
- Pillow: For image processing
- Dear PyGui: For displaying maps in the node editor

Features:
- Downloads OpenStreetMap tiles with contextily
- Renders maps with GPS points (lat, lon)
- Converts rendered maps into textures
- Displays textures inside dpg.node_editor nodes
- Supports zoom and bounding box auto-scaling
- Implements local tile caching
- Updates textures dynamically when new GPS points are added
"""
import time
import json
import os
import tempfile
import hashlib
import math
from datetime import datetime

import numpy as np
import cv2
from PIL import Image
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode

# Import matplotlib for map rendering
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

# Import contextily for OpenStreetMap tile downloading
try:
    import contextily as ctx
    CONTEXTILY_AVAILABLE = True
except ImportError:
    print("Warning: contextily not installed. Map rendering will be limited.")
    CONTEXTILY_AVAILABLE = False

# Cache directory for map tiles and generated maps
# contextily has its own caching mechanism, but we create this for compatibility
CACHE_DIR = os.path.join(tempfile.gettempdir(), 'cv_studio_map_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# Map rendering constants
MIN_RANGE_METERS = 1000      # Minimum range for single points (1 km)
DEFAULT_RANGE_METERS = 10000  # Default range when min is needed (10 km)
MAP_PADDING_FACTOR = 0.15     # Padding around bounding box (15%)

# Simplified continental outlines for map context visualization
# These are rough approximations to give geographic context in the map view
# Format: {region_name: (longitude_coords, latitude_coords)}
SIMPLIFIED_CONTINENTS = {
    'europe': {
        'bounds': {'lon': (-15, 40), 'lat': (35, 70)},
        'outline': {
            'lon': [-10, 15, 30, 30, 15, 0, -10, -10],
            'lat': [35, 35, 40, 60, 70, 65, 50, 35]
        }
    },
    'north_america': {
        'bounds': {'lon': (-130, -60), 'lat': (25, 50)},
        'outline': {
            'lon': [-125, -125, -70, -70, -125],
            'lat': [25, 50, 50, 25, 25]
        }
    },
    'asia': {
        'bounds': {'lon': (60, 140), 'lat': (20, 50)},
        'outline': {
            'lon': [60, 140, 140, 100, 60, 60],
            'lat': [20, 20, 50, 50, 40, 20]
        }
    }
}


class FactoryNode:
    node_label = 'Map'
    node_tag = 'Map'
    

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

        node = Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        # Map controls
        node.tag_node_zoom_name = node.tag_node_name + ':Zoom'
        node.tag_node_zoom_value_name = node.tag_node_name + ':ZoomValue'
        node.tag_node_size_name = node.tag_node_name + ':MapSize'
        node.tag_node_size_value_name = node.tag_node_name + ':MapSizeValue'
        node.tag_node_cache_name = node.tag_node_name + ':UseCache'
        node.tag_node_cache_value_name = node.tag_node_name + ':UseCacheValue'
        node.tag_node_status_name = node.tag_node_name + ':Status'
        node.tag_node_status_value_name = node.tag_node_name + ':StatusValue'
        # Pan controls
        node.tag_node_pan_x_value_name = node.tag_node_name + ':PanXValue'
        node.tag_node_pan_y_value_name = node.tag_node_name + ':PanYValue'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create initial preview image
        black_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='JSON with lat/lon',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Zoom slider
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_zoom_value_name,
                    label="Zoom",
                    width=small_window_w - 80,
                    default_value=10,
                    min_value=1,
                    max_value=18,
                    clamped=True,
                )

            # Map size slider (for bounding box adjustment)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_size_value_name,
                    label="View Size",
                    width=small_window_w - 80,
                    default_value=1.0,
                    min_value=0.5,
                    max_value=5.0,
                    clamped=True,
                )

            # Pan X slider (horizontal translation: left/right)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_pan_x_value_name,
                    label="Pan X (Left/Right)",
                    width=small_window_w - 80,
                    default_value=0.0,
                    min_value=-1.0,
                    max_value=1.0,
                    clamped=True,
                )

            # Pan Y slider (vertical translation: up/down)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_pan_y_value_name,
                    label="Pan Y (Up/Down)",
                    width=small_window_w - 80,
                    default_value=0.0,
                    min_value=-1.0,
                    max_value=1.0,
                    clamped=True,
                )

            # Cache checkbox
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_cache_value_name,
                    label="Cache Maps",
                    default_value=True,
                )

            # Status text
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_status_value_name,
                    default_value='No data',
                )

        return node


class Node(DpgNodeABC):
    _ver = "0.0.1"
    node_label = 'Map'
    node_tag = 'Map'

    TYPE_BOOLEAN = "BOOLEAN"
    TYPE_TEXT = "TEXT"
    TYPE_IMAGE = "IMAGE"
    TYPE_FLOAT = "FLOAT"
    TYPE_INT = "INT"
    TYPE_TIME_MS = "TIME_MS"
    TYPE_JSON = "JSON"

    def __init__(self):
        self.last_map_path = None
        self.point_data = []
        self._opencv_setting_dict = None
        # contextily handles its own caching internally
        # We keep these for compatibility with tests
        self.cached_tiles = {}
        self.cache_center = None
        self.cache_radius = 2
        # Pan offset tracking (in meters, Web Mercator)
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0


    @staticmethod
    def lat_lon_to_web_mercator(lat, lon):
        """
        Convert latitude/longitude to Web Mercator coordinates (EPSG:3857).
        This is the projection system used by most web mapping services.
        """
        # Earth radius in meters
        R = 6378137.0
        
        # Convert to radians
        lon_rad = math.radians(lon)
        lat_rad = math.radians(lat)
        
        # Web Mercator formulas
        x = R * lon_rad
        y = R * math.log(math.tan(math.pi / 4 + lat_rad / 2))
        
        return x, y


    @staticmethod
    def web_mercator_to_lat_lon(x, y):
        """
        Convert Web Mercator coordinates (EPSG:3857) to latitude/longitude.
        """
        # Earth radius in meters
        R = 6378137.0
        
        # Inverse Web Mercator formulas
        lon = math.degrees(x / R)
        lat = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)
        
        return lat, lon


    def _calculate_extent(self, points, zoom_level=None, size_factor=1.0, pan_offset_x=0.0, pan_offset_y=0.0):
        """
        Calculate the bounding box extent in Web Mercator coordinates.
        
        Args:
            points: List of points with 'lat' and 'lon' keys
            zoom_level: Optional zoom level (not used, kept for compatibility)
            size_factor: Factor to scale the bounding box (default 1.0)
                        Values < 1.0 zoom in (smaller view area)
                        Values > 1.0 zoom out (larger view area)
            pan_offset_x: Horizontal pan offset as fraction of range (-1.0 to 1.0)
            pan_offset_y: Vertical pan offset as fraction of range (-1.0 to 1.0)
        
        Returns:
            Tuple of (west, south, east, north) in Web Mercator coordinates
        """
        if not points:
            # Default view: world centered at (0, 0)
            return (-20037508.34, -20037508.34, 20037508.34, 20037508.34)
        
        # Convert all points to Web Mercator
        mercator_coords = [self.lat_lon_to_web_mercator(p['lat'], p['lon']) for p in points]
        
        # Get bounding box
        xs = [coord[0] for coord in mercator_coords]
        ys = [coord[1] for coord in mercator_coords]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Calculate center point
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Get range
        x_range = max_x - min_x
        y_range = max_y - min_y
        
        # Ensure minimum range for single points or very close points
        if x_range < MIN_RANGE_METERS:  # Less than 1km
            x_range = DEFAULT_RANGE_METERS  # Use 10km as minimum range
        if y_range < MIN_RANGE_METERS:
            y_range = DEFAULT_RANGE_METERS
        
        # Add base padding (15%)
        x_range_padded = x_range * (1.0 + MAP_PADDING_FACTOR * 2)
        y_range_padded = y_range * (1.0 + MAP_PADDING_FACTOR * 2)
        
        # Apply size factor: scale the range around center
        # size_factor < 1.0 = zoom in (smaller range)
        # size_factor > 1.0 = zoom out (larger range)
        final_x_range = x_range_padded * size_factor
        final_y_range = y_range_padded * size_factor
        
        # Calculate extent from center
        west = center_x - final_x_range / 2
        east = center_x + final_x_range / 2
        south = center_y - final_y_range / 2
        north = center_y + final_y_range / 2
        
        # Apply pan offsets (as a fraction of the final range)
        pan_x_meters = pan_offset_x * final_x_range
        pan_y_meters = pan_offset_y * final_y_range
        
        west += pan_x_meters
        east += pan_x_meters
        south += pan_y_meters
        north += pan_y_meters
        
        return (west, south, east, north)


    @classmethod
    def create_for_testing(cls):
        """Factory method for creating node instances in tests"""
        node = object.__new__(cls)
        node._opencv_setting_dict = {}
        node.last_map_path = None
        node.point_data = []
        node.cached_tiles = {}
        node.cache_center = None
        node.cache_radius = 2
        node.pan_offset_x = 0.0
        node.pan_offset_y = 0.0
        return node


    def update(
        self,
        node_id: int,
        connection_list: list[list[str]],
        node_image_dict: dict[str, any],
        node_result_dict: dict[str, any],
        node_audio_dict: dict[str, any],
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Input01Value'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        tag_node_output02_value_name = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
        tag_node_cache_value_name = tag_node_name + ':UseCacheValue'
        tag_node_status_value_name = tag_node_name + ':StatusValue'
        tag_node_pan_x_value_name = tag_node_name + ':PanXValue'
        tag_node_pan_y_value_name = tag_node_name + ':PanYValue'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        if use_pref_counter:
            start_time = time.perf_counter()

        # Find connected source for JSON data
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)
                break
        
        # Get input JSON data from node_result_dict (correct approach)
        input_value = node_result_dict.get(connection_info_src, None)
        
        # Log received data for debugging
        if connection_info_src:
            if input_value is not None:
                print(f"Map node: Received data from {connection_info_src}")
                print(f"Map node: Data type: {type(input_value).__name__}")
                if isinstance(input_value, (list, dict)):
                    try:
                        import json as json_module
                        json_str = json_module.dumps(input_value, indent=2)
                        print(f"Map node: JSON data (first 500 chars):\n{json_str[:500]}")
                    except Exception as e:
                        print(f"Map node: Could not serialize data: {e}")
                elif isinstance(input_value, str):
                    print(f"Map node: String data (length {len(input_value)}): {input_value[:100]}")
            else:
                print(f"Map node: No data received from {connection_info_src}")
        
        # Initialize output image
        preview_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        
        if input_value is not None:
            # Reset the no-data flag since we have data now
            if hasattr(self, '_no_data_logged'):
                self._no_data_logged = False
                
            try:
                # Parse JSON data
                if isinstance(input_value, str):
                    # Handle empty or whitespace-only strings
                    if not input_value.strip():
                        print("Map node: Received empty JSON string")
                        dpg_set_value(tag_node_status_value_name, "Waiting for data...")
                        # Skip further processing for empty input
                    else:
                        print(f"Map node: Received JSON string (length: {len(input_value)})")
                        data = json.loads(input_value)
                        
                        # Log the structure of received data
                        if isinstance(data, dict):
                            print(f"Map node: JSON contains keys: {list(data.keys())}")
                            if 'boats' in data:
                                print(f"Map node: Found {len(data.get('boats', []))} boats in data")
                        elif isinstance(data, list):
                            print(f"Map node: JSON is a list with {len(data)} items")

                        # Extract points with latitude and longitude
                        points = self._extract_lat_lon_from_json(data)
                        
                        if points:
                            print(f"Map node: Extracted {len(points)} points with lat/lon")
                            self.point_data = points
                            
                            # Get zoom, size, cache, and pan parameters
                            zoom_level = dpg_get_value(tag_node_zoom_value_name)
                            size_factor = dpg_get_value(tag_node_size_value_name)
                            use_cache = dpg_get_value(tag_node_cache_value_name)
                            pan_x = dpg_get_value(tag_node_pan_x_value_name)
                            pan_y = dpg_get_value(tag_node_pan_y_value_name)
                            if use_cache is None:
                                use_cache = True  # Default to enabled
                            if pan_x is None:
                                pan_x = 0.0
                            if pan_y is None:
                                pan_y = 0.0
                            
                            # HTML map generation removed - only tile-based preview
                            status_text = f"✓ {len(points)} point(s) displayed"
                            
                            # Create map visualization image (main display)
                            preview_image = self._create_preview_image(
                                points, small_window_w, small_window_h, pan_x, pan_y
                            )
                            
                            # Update status
                            dpg_set_value(tag_node_status_value_name, status_text)
                        else:
                            status_msg = "No lat/lon in data"
                            print(f"Map node: {status_msg}")
                            dpg_set_value(tag_node_status_value_name, status_msg)
                else:
                    print(f"Map node: Received JSON object (type: {type(input_value).__name__})")
                    data = input_value

                    # Log the structure of received data
                    if isinstance(data, dict):
                        print(f"Map node: JSON contains keys: {list(data.keys())}")
                        if 'boats' in data:
                            print(f"Map node: Found {len(data.get('boats', []))} boats in data")
                    elif isinstance(data, list):
                        print(f"Map node: JSON is a list with {len(data)} items")

                    # Extract points with latitude and longitude
                    points = self._extract_lat_lon_from_json(data)
                    
                    if points:
                        print(f"Map node: Extracted {len(points)} points with lat/lon")
                        self.point_data = points
                        
                        # Get zoom, size, cache, and pan parameters
                        zoom_level = dpg_get_value(tag_node_zoom_value_name)
                        size_factor = dpg_get_value(tag_node_size_value_name)
                        use_cache = dpg_get_value(tag_node_cache_value_name)
                        pan_x = dpg_get_value(tag_node_pan_x_value_name)
                        pan_y = dpg_get_value(tag_node_pan_y_value_name)
                        if use_cache is None:
                            use_cache = True  # Default to enabled
                        if pan_x is None:
                            pan_x = 0.0
                        if pan_y is None:
                            pan_y = 0.0
                        
                        # HTML map generation removed - only tile-based preview
                        status_text = f"✓ {len(points)} point(s) displayed"
                        
                        # Create map visualization image (main display)
                        preview_image = self._create_preview_image(
                            points, small_window_w, small_window_h, pan_x, pan_y
                        )
                        
                        # Update status
                        dpg_set_value(tag_node_status_value_name, status_text)
                    else:
                        status_msg = "No lat/lon in data"
                        print(f"Map node: {status_msg}")
                        dpg_set_value(tag_node_status_value_name, status_msg)
                    
            except json.JSONDecodeError as e:
                error_msg = f"JSON parse error: {str(e)[:60]}"
                print(f"Map node: {error_msg}")
                dpg_set_value(tag_node_status_value_name, error_msg)
            except Exception as e:
                error_msg = f"Error: {str(e)[:40]}"
                print(f"Map node: Error processing data: {e}")
                dpg_set_value(tag_node_status_value_name, error_msg)
        else:
            # No input data
            if not hasattr(self, '_no_data_logged') or not self._no_data_logged:
                print("Map node: Waiting for input data...")
                self._no_data_logged = True

        # Convert preview to DPG texture and update
        preview_texture = self.convert_cv_to_dpg(
            preview_image,
            small_window_w,
            small_window_h,
        )
        dpg_set_value(tag_node_output01_value_name, preview_texture)

        if use_pref_counter:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            dpg_set_value(tag_node_output02_value_name, elapsed_time)

        return {"image": preview_image, "json": None, "audio": None}




    def _extract_lat_lon_from_json(self, data):
        """Extract latitude and longitude from JSON data"""
        points = []
        
        # Handle different JSON structures
        if isinstance(data, dict):
            # Check for AIS boat data structure
            if 'boats' in data:
                for boat in data['boats']:
                    if 'latitude' in boat and 'longitude' in boat:
                        points.append({
                            'lat': boat['latitude'],
                            'lon': boat['longitude'],
                            'name': boat.get('ship_name', 'Unknown'),
                            'info': boat.get('mmsi', '')
                        })
            # Check for direct lat/lon in dict
            elif 'latitude' in data and 'longitude' in data:
                points.append({
                    'lat': data['latitude'],
                    'lon': data['longitude'],
                    'name': data.get('name', 'Point'),
                    'info': ''
                })
            # Check for nested data
            else:
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        points.extend(self._extract_lat_lon_from_json(value))
        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if 'latitude' in item and 'longitude' in item:
                        points.append({
                            'lat': item['latitude'],
                            'lon': item['longitude'],
                            'name': item.get('name', 'Point'),
                            'info': item.get('mmsi', '')
                        })
                    elif 'lat' in item and 'lon' in item:
                        points.append({
                            'lat': item['lat'],
                            'lon': item['lon'],
                            'name': item.get('name', 'Point'),
                            'info': ''
                        })
        
        return points


    def _generate_cache_key(self, points, zoom_level, size_factor):
        """
        Generate a cache key based on map parameters.
        
        Args:
            points: List of coordinate points
            zoom_level: Map zoom level
            size_factor: View size factor
            
        Returns:
            Hash string to use as cache key
        """
        # Create a string representation of key parameters
        # Sort points to ensure consistent ordering
        sorted_points = sorted(points, key=lambda p: (p['lat'], p['lon']))
        
        # Build key from essential data
        key_data = {
            'points': [(p['lat'], p['lon']) for p in sorted_points[:100]],  # Limit to first 100 points
            'zoom': zoom_level,
            'size': round(size_factor, 2),
        }
        
        # Generate hash
        key_str = json.dumps(key_data, sort_keys=True)
        cache_key = hashlib.md5(key_str.encode()).hexdigest()
        
        return cache_key

    # HTML map generation disabled - functionality removed
    # def _generate_map(self, points, zoom_level, size_factor, use_cache=True):
    #     """Generate an HTML map with Leaflet using folium with optional caching"""
    #     # This method has been disabled to remove HTML rendering functionality


    def _create_preview_image(self, points, width, height, pan_x=0.0, pan_y=0.0):
        """
        Create a map visualization image using contextily for OSM tiles.
        
        This method:
        1. Uses contextily to download and cache OSM tiles
        2. Renders GPS points on the map using matplotlib
        3. Converts the result to a texture for Dear PyGui
        
        Args:
            points: List of points with 'lat' and 'lon' keys
            width: Width of output image in pixels
            height: Height of output image in pixels
            pan_x: Horizontal pan offset (-1.0 to 1.0)
            pan_y: Vertical pan offset (-1.0 to 1.0)
        
        Returns:
            numpy array in BGR format suitable for OpenCV/DPG
        """
        if not points:
            preview = np.zeros((height, width, 3), dtype=np.uint8)
            return preview
        
        # Try contextily rendering first
        if CONTEXTILY_AVAILABLE:
            try:
                return self._render_with_contextily(points, width, height, pan_x, pan_y)
            except Exception as e:
                print(f"Error rendering with contextily: {e}")
                print("Falling back to matplotlib-only rendering")
        
        # Fallback to matplotlib rendering without basemap
        return self._render_with_matplotlib(points, width, height)


    def _render_with_contextily(self, points, width, height, pan_x=0.0, pan_y=0.0):
        """
        Render map using contextily for OSM tiles and matplotlib for points.
        
        This is the primary rendering method that:
        1. Creates a matplotlib figure
        2. Plots GPS points in Web Mercator projection
        3. Adds OSM basemap tiles using contextily
        4. Converts to numpy array for DPG texture
        
        Args:
            points: List of points with 'lat' and 'lon' keys
            width: Width of output image in pixels
            height: Height of output image in pixels
            pan_x: Horizontal pan offset (-1.0 to 1.0)
            pan_y: Vertical pan offset (-1.0 to 1.0)
        
        Returns:
            numpy array in BGR format
        """
        # Convert points to Web Mercator coordinates
        mercator_points = []
        for point in points:
            x, y = self.lat_lon_to_web_mercator(point['lat'], point['lon'])
            mercator_points.append({
                'x': x,
                'y': y,
                'name': point.get('name', 'Point'),
                'lat': point['lat'],
                'lon': point['lon']
            })
        
        # Calculate extent (bounding box) with pan offsets
        xs = [p['x'] for p in mercator_points]
        ys = [p['y'] for p in mercator_points]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Add padding using the same logic as _calculate_extent
        x_range = max_x - min_x
        y_range = max_y - min_y
        
        # Ensure minimum range for single points or very close points
        if x_range < MIN_RANGE_METERS:
            x_range = DEFAULT_RANGE_METERS
        if y_range < MIN_RANGE_METERS:
            y_range = DEFAULT_RANGE_METERS
        
        min_x -= x_range * MAP_PADDING_FACTOR
        max_x += x_range * MAP_PADDING_FACTOR
        min_y -= y_range * MAP_PADDING_FACTOR
        max_y += y_range * MAP_PADDING_FACTOR
        
        # Apply pan offsets
        total_x_range = max_x - min_x
        total_y_range = max_y - min_y
        
        pan_x_meters = pan_x * total_x_range
        pan_y_meters = pan_y * total_y_range
        
        min_x += pan_x_meters
        max_x += pan_x_meters
        min_y += pan_y_meters
        max_y += pan_y_meters
        
        # Create figure
        dpi = 100
        fig_width = width / dpi
        fig_height = height / dpi
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        
        # Plot points in Web Mercator coordinates
        for point in mercator_points:
            ax.plot(point['x'], point['y'], 'o', 
                   color='red', markersize=10, 
                   markeredgecolor='darkred', markeredgewidth=2,
                   markerfacecolor='yellow', zorder=5)
            
            # Add labels for small number of points
            if len(mercator_points) <= 10:
                ax.annotate(point['name'],
                           (point['x'], point['y']),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, color='black', weight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', 
                                   facecolor='white', alpha=0.8, edgecolor='black'))
        
        # Set axis limits
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        
        # Add OSM basemap using contextily
        # Use zoom='auto' to let contextily determine optimal zoom level
        # crs='EPSG:3857' specifies Web Mercator projection
        try:
            ctx.add_basemap(ax, crs='EPSG:3857', source=ctx.providers.OpenStreetMap.Mapnik,
                          zoom='auto', attribution=None)
        except Exception as e:
            print(f"Warning: Could not add basemap: {e}")
            # Continue without basemap - points will still be visible
            ax.set_facecolor('#ADD8E6')  # Light blue background
        
        # Hide axes completely - we don't want to show x,y coordinates (Web Mercator values)
        # The map tiles provide the geographic context, not numeric coordinates
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f'Map View - {len(points)} point(s)', fontsize=10, pad=10)
        
        # Tight layout
        plt.tight_layout(pad=0.5)
        
        # Render to image
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        
        # Convert to numpy array
        image = np.asarray(canvas.buffer_rgba())[:, :, :3]
        
        # Convert RGB to BGR for OpenCV
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # Clean up
        plt.close(fig)
        
        return image


    def _render_with_matplotlib(self, points, width, height):
        """Fallback: Create a map visualization image with matplotlib (original implementation)"""
        if not points:
            preview = np.zeros((height, width, 3), dtype=np.uint8)
            return preview
        
        # Get bounds
        lats = [p['lat'] for p in points]
        lons = [p['lon'] for p in points]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Add padding to avoid points on edges
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        
        if lat_range == 0:
            lat_range = 0.1  # Small default range for single point
        if lon_range == 0:
            lon_range = 0.1
        
        padding = 0.15
        plot_min_lat = min_lat - lat_range * padding
        plot_max_lat = max_lat + lat_range * padding
        plot_min_lon = min_lon - lon_range * padding
        plot_max_lon = max_lon + lon_range * padding
        
        # Create figure with matplotlib
        dpi = 100
        fig_width = width / dpi
        fig_height = height / dpi
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        
        # Set background color (light blue for water)
        ax.set_facecolor('#ADD8E6')
        fig.patch.set_facecolor('#E0F2F7')
        
        # Draw grid lines (representing latitude/longitude grid)
        ax.grid(True, linestyle='--', linewidth=0.5, color='#888888', alpha=0.3)
        
        # Draw a simple coastline approximation (rectangular land masses)
        # This is a simplified representation - for actual coastlines, use cartopy or basemap
        self._draw_simplified_map_features(ax, plot_min_lon, plot_max_lon, plot_min_lat, plot_max_lat)
        
        # Plot points
        for point in points:
            ax.plot(point['lon'], point['lat'], 'ro', markersize=8, 
                   markeredgecolor='darkred', markeredgewidth=1.5, 
                   markerfacecolor='yellow', zorder=5)
            
            # Add label for points if not too many
            if len(points) <= 10:
                ax.annotate(point['name'], 
                           (point['lon'], point['lat']),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=7, color='black',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        # Set axis limits
        ax.set_xlim(plot_min_lon, plot_max_lon)
        ax.set_ylim(plot_min_lat, plot_max_lat)
        
        # Hide coordinate tick values for cleaner map display
        # The fallback map shows simplified geographic features instead of precise coordinates
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f'Map View - {len(points)} point(s)', fontsize=10, pad=10)
        
        # Set aspect ratio to maintain geographic proportions
        # Use cos(mean_lat) to approximate the aspect ratio
        # Clamp mean_lat to avoid division by zero at poles
        mean_lat = (min_lat + max_lat) / 2
        mean_lat = np.clip(mean_lat, -85, 85)  # Avoid extreme polar regions
        aspect_ratio = 1.0 / np.cos(np.radians(mean_lat))
        # Clamp aspect ratio to reasonable range
        aspect_ratio = np.clip(aspect_ratio, 0.1, 10.0)
        ax.set_aspect(aspect_ratio)
        
        # Tight layout to minimize margins
        plt.tight_layout(pad=0.5)
        
        # Render to image using FigureCanvasAgg
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        
        # Convert to numpy array
        image = np.asarray(canvas.buffer_rgba())[:, :, :3]
        
        # Convert RGB to BGR for OpenCV
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # Clean up
        plt.close(fig)
        
        return image
    
    def _draw_simplified_map_features(self, ax, min_lon, max_lon, min_lat, max_lat):
        """Draw simplified map features (land approximation)
        
        Uses predefined continental outlines to provide geographic context.
        These are rough approximations - for precise coastlines, use cartopy or basemap.
        """
        # Determine if we're looking at a specific region
        lon_center = (min_lon + max_lon) / 2
        lat_center = (min_lat + max_lat) / 2
        
        # Check each continent and draw if we're viewing that region
        for continent_name, continent_data in SIMPLIFIED_CONTINENTS.items():
            bounds = continent_data['bounds']
            lon_bounds = bounds['lon']
            lat_bounds = bounds['lat']
            
            # Check if view center falls within this continent's bounds
            if (lon_bounds[0] < lon_center < lon_bounds[1] and 
                lat_bounds[0] < lat_center < lat_bounds[1]):
                # Draw the continent outline
                outline = continent_data['outline']
                ax.fill(outline['lon'], outline['lat'], 
                       color='#90EE90', alpha=0.3, zorder=1,
                       label=f'{continent_name.title()} (approx)')
                break  # Only draw one continent to avoid clutter
        
        # For other regions or zoomed views, just show water background
        # The grid and colors will still give a map-like appearance


    def close(self, node_id: int):
        pass


    def add_node(
        self,
        parent,
        node_id,
        pos,
        width,
        height,
        opencv_setting_dict,
    ):
        """Required abstract method - not used in this implementation"""
        pass


    def get_setting_dict(self, node_id):
        """Get node settings for saving"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
        tag_node_cache_value_name = tag_node_name + ':UseCacheValue'
        tag_node_pan_x_value_name = tag_node_name + ':PanXValue'
        tag_node_pan_y_value_name = tag_node_name + ':PanYValue'
        
        return {
            'zoom': dpg_get_value(tag_node_zoom_value_name),
            'size': dpg_get_value(tag_node_size_value_name),
            'cache': dpg_get_value(tag_node_cache_value_name),
            'pan_x': dpg_get_value(tag_node_pan_x_value_name),
            'pan_y': dpg_get_value(tag_node_pan_y_value_name),
        }


    def set_setting_dict(self, node_id, setting_dict):
        """Set node settings when loading"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
        tag_node_cache_value_name = tag_node_name + ':UseCacheValue'
        tag_node_pan_x_value_name = tag_node_name + ':PanXValue'
        tag_node_pan_y_value_name = tag_node_name + ':PanYValue'
        
        if 'zoom' in setting_dict:
            dpg_set_value(tag_node_zoom_value_name, setting_dict['zoom'])
        if 'size' in setting_dict:
            dpg_set_value(tag_node_size_value_name, setting_dict['size'])
        if 'cache' in setting_dict:
            dpg_set_value(tag_node_cache_value_name, setting_dict['cache'])
        if 'pan_x' in setting_dict:
            dpg_set_value(tag_node_pan_x_value_name, setting_dict['pan_x'])
        if 'pan_y' in setting_dict:
            dpg_set_value(tag_node_pan_y_value_name, setting_dict['pan_y'])


    def convert_cv_to_dpg(self, image, width, height):
        """Convert OpenCV image to DearPyGUI texture format"""
        resize_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        data = np.flip(resize_image, 2)
        data = data.ravel()
        data = np.asarray(data, dtype=np.float32)
        texture_data = np.true_divide(data, 255.0)
        return texture_data
