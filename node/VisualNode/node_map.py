#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import json
import os
import tempfile
import webbrowser
import hashlib
from datetime import datetime

import cv2
import numpy as np
import dearpygui.dearpygui as dpg
import requests
from PIL import Image
import io
import math

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode

# Import matplotlib for map rendering
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg


# Cache directory for map tiles and generated maps
CACHE_DIR = os.path.join(tempfile.gettempdir(), 'cv_studio_map_cache')
OSM_TILE_CACHE_DIR = os.path.join(CACHE_DIR, 'osm_tiles')
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OSM_TILE_CACHE_DIR, exist_ok=True)

# OSM tile server URL pattern
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

# User-Agent header for OSM tile requests (required by OSM tile usage policy)
OSM_USER_AGENT = "CV_Studio/1.0"

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
        node.tag_node_open_button_name = node.tag_node_name + ':OpenMap'
        node.tag_node_status_name = node.tag_node_name + ':Status'
        node.tag_node_status_value_name = node.tag_node_name + ':StatusValue'

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

            # Open map button (optional - for interactive HTML view)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=node.tag_node_open_button_name,
                    label="Open Interactive HTML",
                    callback=lambda s, a, u: Node.open_map_callback(s, a, u),
                    user_data=node,
                    width=small_window_w - 20,
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
        self.cached_tiles = {}  # Store cached tiles in memory
        self.cache_center = None  # (lat, lon, zoom) of cached region
        self.cache_radius = 2  # Number of tiles to cache in each direction


    @staticmethod
    def lat_lon_to_tile(lat, lon, zoom):
        """Convert latitude/longitude to tile coordinates at given zoom level"""
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x_tile = int((lon + 180.0) / 360.0 * n)
        y_tile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x_tile, y_tile


    @staticmethod
    def tile_to_lat_lon(x_tile, y_tile, zoom):
        """Convert tile coordinates to latitude/longitude"""
        n = 2.0 ** zoom
        lon = x_tile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y_tile / n)))
        lat = math.degrees(lat_rad)
        return lat, lon


    def _get_tile_cache_path(self, x, y, zoom):
        """Get the file path for a cached tile"""
        return os.path.join(OSM_TILE_CACHE_DIR, f"{zoom}_{x}_{y}.png")


    def _download_tile(self, x, y, zoom):
        """Download a single OSM tile and cache it"""
        cache_path = self._get_tile_cache_path(x, y, zoom)
        
        # Check if already cached on disk
        if os.path.exists(cache_path):
            try:
                with Image.open(cache_path) as img:
                    return np.array(img)
            except Exception as e:
                print(f"Error loading cached tile {x},{y},{zoom}: {e}")
                # If cache is corrupted, delete and re-download
                os.remove(cache_path)
        
        # Download tile from OSM
        try:
            url = OSM_TILE_URL.format(z=zoom, x=x, y=y)
            headers = {'User-Agent': OSM_USER_AGENT}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            # Load and return as numpy array
            img = Image.open(io.BytesIO(response.content))
            return np.array(img)
            
        except Exception as e:
            print(f"Error downloading tile {x},{y},{zoom}: {e}")
            # Return a blank tile on error
            return np.zeros((256, 256, 3), dtype=np.uint8)


    def _cache_osm_tiles_around_point(self, lat, lon, zoom, radius=2):
        """
        Cache OSM tiles around a given point.
        
        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            zoom: Zoom level
            radius: Number of tiles to cache in each direction from center
        """
        center_x, center_y = self.lat_lon_to_tile(lat, lon, zoom)
        
        print(f"Caching OSM tiles around ({lat:.4f}, {lon:.4f}) at zoom {zoom}")
        print(f"Center tile: ({center_x}, {center_y}), radius: {radius}")
        
        # Cache tiles in a square around the center
        cached_count = 0
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                x = center_x + dx
                y = center_y + dy
                
                # Skip invalid tiles
                if x < 0 or y < 0 or x >= 2**zoom or y >= 2**zoom:
                    continue
                
                tile_data = self._download_tile(x, y, zoom)
                if tile_data is not None:
                    self.cached_tiles[(x, y, zoom)] = tile_data
                    cached_count += 1
        
        print(f"Cached {cached_count} tiles")
        self.cache_center = (lat, lon, zoom)
        self.cache_radius = radius
        
        return cached_count


    @classmethod
    def create_for_testing(cls):
        """Factory method for creating node instances in tests"""
        node = object.__new__(cls)
        node._opencv_setting_dict = {}
        node.last_map_path = None
        node.point_data = []
        return node
        

    @staticmethod
    def open_map_callback(sender, app_data, user_data):
        """Open the generated map in the default browser"""
        node = user_data
        if node.last_map_path and os.path.exists(node.last_map_path):
            webbrowser.open('file://' + os.path.abspath(node.last_map_path))
        else:
            # Update status to inform user
            if hasattr(node, 'tag_node_status_value_name'):
                dpg_set_value(node.tag_node_status_value_name, "No map generated yet")
            print("No map generated yet")


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

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        if use_pref_counter:
            start_time = time.perf_counter()

        # Get input JSON data
        input_value = dpg_get_value(tag_node_input01_value_name)
        
        # Initialize output image
        preview_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        
        if input_value is not None:
            # Reset the no-data flag since we have data now
            if hasattr(self, '_no_data_logged'):
                self._no_data_logged = False
                
            try:
                # Parse JSON data
                if isinstance(input_value, str):
                    print(f"Map node: Received JSON string (length: {len(input_value)})")
                    data = json.loads(input_value)
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
                    
                    # Get zoom, size, and cache parameters
                    zoom_level = dpg_get_value(tag_node_zoom_value_name)
                    size_factor = dpg_get_value(tag_node_size_value_name)
                    use_cache = dpg_get_value(tag_node_cache_value_name)
                    if use_cache is None:
                        use_cache = True  # Default to enabled
                    
                    # Generate HTML map (for optional interactive view in browser)
                    map_path = self._generate_map(points, zoom_level, size_factor, use_cache)
                    
                    if map_path:
                        self.last_map_path = map_path
                        status_text = f"✓ {len(points)} point(s) displayed"
                        print(f"Map node: Interactive HTML map ready at {map_path}")
                    else:
                        # Map generation failed (likely folium not installed) - that's ok
                        status_text = f"✓ {len(points)} point(s) displayed"
                        print("Map node: Displaying map (HTML not generated - folium needed for interactive view)")
                    
                    # Create map visualization image (main display)
                    preview_image = self._create_preview_image(
                        points, small_window_w, small_window_h
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

        return preview_image




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


    def _generate_map(self, points, zoom_level, size_factor, use_cache=True):
        """Generate an HTML map with Leaflet using folium with optional caching"""
        try:
            import folium
            from folium.plugins import MarkerCluster
        except ImportError:
            print("folium not installed, map generation skipped. Install with: pip install folium")
            return None

        if not points:
            return None

        # Generate cache key based on points, zoom, and size
        if use_cache:
            cache_key = self._generate_cache_key(points, zoom_level, size_factor)
            cached_path = os.path.join(CACHE_DIR, f"map_{cache_key}.html")
            
            # Check if cached map exists
            if os.path.exists(cached_path):
                print(f"Map node: Using cached map from {cached_path}")
                return cached_path

        # Calculate center and bounds
        lats = [p['lat'] for p in points]
        lons = [p['lon'] for p in points]
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Calculate bounds with size factor
        lat_range = (max(lats) - min(lats)) * size_factor
        lon_range = (max(lons) - min(lons)) * size_factor
        
        # Create map with tile caching
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_level,
            tiles='OpenStreetMap',
            attr='OpenStreetMap'
        )
        
        # Add marker cluster for better performance with many points
        marker_cluster = MarkerCluster().add_to(m)
        
        # Add markers for each point
        for point in points:
            folium.Marker(
                location=[point['lat'], point['lon']],
                popup=f"{point['name']}<br>{point['info']}",
                tooltip=point['name']
            ).add_to(marker_cluster)
        
        # Fit bounds to show all points
        if len(points) > 1:
            sw = [min(lats) - lat_range * 0.1, min(lons) - lon_range * 0.1]
            ne = [max(lats) + lat_range * 0.1, max(lons) + lon_range * 0.1]
            m.fit_bounds([sw, ne])
        
        # Save to appropriate location (cache or temp)
        if use_cache:
            map_path = cached_path
            print(f"Map node: Caching map to {map_path}")
        else:
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            map_path = os.path.join(temp_dir, f"cv_studio_map_{timestamp}.html")
            print(f"Map node: Saving map to temp {map_path}")
        
        m.save(map_path)
        
        return map_path


    def _create_preview_image(self, points, width, height):
        """Create a map visualization image using cached OSM tiles if available"""
        if not points:
            preview = np.zeros((height, width, 3), dtype=np.uint8)
            return preview
        
        # Get bounds
        lats = [p['lat'] for p in points]
        lons = [p['lon'] for p in points]
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Determine appropriate zoom level based on span
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        lat_span = max_lat - min_lat
        lon_span = max_lon - min_lon
        
        # Calculate zoom level (higher zoom = more detailed)
        # Use the larger span to determine zoom
        max_span = max(lat_span, lon_span)
        if max_span < 0.01:
            zoom_level = 15
        elif max_span < 0.05:
            zoom_level = 13
        elif max_span < 0.2:
            zoom_level = 11
        elif max_span < 1.0:
            zoom_level = 9
        elif max_span < 5.0:
            zoom_level = 7
        else:
            zoom_level = 5
        
        # Try to render using OSM tiles
        try:
            osm_image = self._render_with_osm_tiles(
                center_lat, center_lon, zoom_level, points, width, height
            )
            if osm_image is not None:
                return osm_image
        except Exception as e:
            print(f"Error rendering with OSM tiles: {e}")
        
        # Fallback to matplotlib rendering
        return self._render_with_matplotlib(points, width, height)


    def _render_with_osm_tiles(self, center_lat, center_lon, zoom, points, width, height):
        """
        Render map preview using cached OSM tiles.
        
        Returns:
            numpy array with rendered map, or None if tiles not available
        """
        # Cache tiles around center point if not already cached or zoom changed
        if (self.cache_center is None or 
            self.cache_center[2] != zoom or
            abs(self.cache_center[0] - center_lat) > 0.1 or
            abs(self.cache_center[1] - center_lon) > 0.1):
            self._cache_osm_tiles_around_point(center_lat, center_lon, zoom, radius=3)
        
        # Get center tile coordinates
        center_x, center_y = self.lat_lon_to_tile(center_lat, center_lon, zoom)
        
        # Calculate how many tiles we need to fill the preview
        tile_size = 256
        tiles_x = math.ceil(width / tile_size) + 2
        tiles_y = math.ceil(height / tile_size) + 2
        
        # Create canvas for compositing tiles
        canvas_width = tiles_x * tile_size
        canvas_height = tiles_y * tile_size
        canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
        
        # Composite tiles onto canvas
        start_tile_x = center_x - tiles_x // 2
        start_tile_y = center_y - tiles_y // 2
        
        for i in range(tiles_x):
            for j in range(tiles_y):
                tile_x = start_tile_x + i
                tile_y = start_tile_y + j
                
                # Get tile from cache
                if (tile_x, tile_y, zoom) in self.cached_tiles:
                    tile = self.cached_tiles[(tile_x, tile_y, zoom)]
                else:
                    # Try to download if not in cache
                    tile = self._download_tile(tile_x, tile_y, zoom)
                    if tile is not None:
                        self.cached_tiles[(tile_x, tile_y, zoom)] = tile
                
                if tile is not None:
                    # Convert RGB to BGR for OpenCV
                    if tile.shape[2] == 4:  # RGBA
                        tile = cv2.cvtColor(tile, cv2.COLOR_RGBA2BGR)
                    elif tile.shape[2] == 3:  # RGB
                        tile = cv2.cvtColor(tile, cv2.COLOR_RGB2BGR)
                    
                    # Place tile on canvas
                    y_start = j * tile_size
                    y_end = y_start + tile_size
                    x_start = i * tile_size
                    x_end = x_start + tile_size
                    canvas[y_start:y_end, x_start:x_end] = tile
        
        # Calculate pixel offset for center point within the center tile
        # Get the fractional part of tile coordinates
        center_x_frac = (center_lon + 180.0) / 360.0 * (2.0 ** zoom)
        center_y_frac = (1.0 - math.asinh(math.tan(math.radians(center_lat))) / math.pi) / 2.0 * (2.0 ** zoom)
        
        pixel_offset_x = int((center_x_frac - center_x) * tile_size)
        pixel_offset_y = int((center_y_frac - center_y) * tile_size)
        
        # Calculate crop region to center the view
        canvas_center_x = (tiles_x * tile_size) // 2 + pixel_offset_x
        canvas_center_y = (tiles_y * tile_size) // 2 + pixel_offset_y
        
        crop_x1 = max(0, canvas_center_x - width // 2)
        crop_y1 = max(0, canvas_center_y - height // 2)
        crop_x2 = min(canvas_width, crop_x1 + width)
        crop_y2 = min(canvas_height, crop_y1 + height)
        
        # Crop to desired size
        preview = canvas[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Resize if necessary to exact dimensions
        if preview.shape[0] != height or preview.shape[1] != width:
            preview = cv2.resize(preview, (width, height))
        
        # Draw markers for each point
        for point in points:
            # Convert lat/lon to pixel coordinates on the preview
            point_x_tile, point_y_tile = self.lat_lon_to_tile(point['lat'], point['lon'], zoom)
            
            # Calculate pixel position relative to canvas center
            pixel_x = canvas_center_x + (point_x_tile - center_x) * tile_size
            pixel_y = canvas_center_y + (point_y_tile - center_y) * tile_size
            
            # Adjust for fractional tile position
            point_x_frac = (point['lon'] + 180.0) / 360.0 * (2.0 ** zoom)
            point_y_frac = (1.0 - math.asinh(math.tan(math.radians(point['lat']))) / math.pi) / 2.0 * (2.0 ** zoom)
            
            pixel_x = canvas_center_x + int((point_x_frac - center_x_frac) * tile_size)
            pixel_y = canvas_center_y + int((point_y_frac - center_y_frac) * tile_size)
            
            # Convert to preview coordinates
            preview_x = pixel_x - crop_x1
            preview_y = pixel_y - crop_y1
            
            # Draw marker if within bounds
            if 0 <= preview_x < width and 0 <= preview_y < height:
                # Draw red circle with yellow center
                cv2.circle(preview, (preview_x, preview_y), 12, (0, 0, 255), -1)
                cv2.circle(preview, (preview_x, preview_y), 8, (0, 255, 255), -1)
                cv2.circle(preview, (preview_x, preview_y), 12, (0, 0, 128), 2)
                
                # Add label if not too many points
                if len(points) <= 10:
                    label = point['name']
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.4
                    thickness = 1
                    
                    # Get text size for background
                    (text_width, text_height), baseline = cv2.getTextSize(
                        label, font, font_scale, thickness
                    )
                    
                    # Draw background rectangle
                    text_x = preview_x + 15
                    text_y = preview_y + 5
                    cv2.rectangle(
                        preview,
                        (text_x - 2, text_y - text_height - 2),
                        (text_x + text_width + 2, text_y + baseline + 2),
                        (255, 255, 255),
                        -1
                    )
                    
                    # Draw text
                    cv2.putText(
                        preview, label, (text_x, text_y),
                        font, font_scale, (0, 0, 0), thickness
                    )
        
        return preview


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
        
        # Labels
        ax.set_xlabel('Longitude', fontsize=8)
        ax.set_ylabel('Latitude', fontsize=8)
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
        
        return {
            'zoom': dpg_get_value(tag_node_zoom_value_name),
            'size': dpg_get_value(tag_node_size_value_name),
            'cache': dpg_get_value(tag_node_cache_value_name),
        }


    def set_setting_dict(self, node_id, setting_dict):
        """Set node settings when loading"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
        tag_node_cache_value_name = tag_node_name + ':UseCacheValue'
        
        if 'zoom' in setting_dict:
            dpg_set_value(tag_node_zoom_value_name, setting_dict['zoom'])
        if 'size' in setting_dict:
            dpg_set_value(tag_node_size_value_name, setting_dict['size'])
        if 'cache' in setting_dict:
            dpg_set_value(tag_node_cache_value_name, setting_dict['cache'])


    def convert_cv_to_dpg(self, image, width, height):
        """Convert OpenCV image to DearPyGUI texture format"""
        resize_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        data = np.flip(resize_image, 2)
        data = data.ravel()
        data = np.asarray(data, dtype=np.float32)
        texture_data = np.true_divide(data, 255.0)
        return texture_data
