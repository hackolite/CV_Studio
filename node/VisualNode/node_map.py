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
import traceback
from datetime import datetime
from io import BytesIO

import numpy as np
import cv2
from PIL import Image
import dearpygui.dearpygui as dpg
import requests

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

# ─────────────────────────────────────────────────────────────────────────────
# Enhanced OSM Tile Management (inspired by DearPyGui OSM implementation)
# ─────────────────────────────────────────────────────────────────────────────

# OSM tile configuration
TILE_SIZE = 256
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_HEADERS = {"User-Agent": "CV_Studio/1.0"}
OSM_CACHE_DIR = os.path.join(tempfile.gettempdir(), '.osm_cache')
os.makedirs(OSM_CACHE_DIR, exist_ok=True)


def lat_lon_to_tile_float(lat, lon, zoom):
    """
    Convert lat/lon to fractional tile coordinates at a given zoom level.
    
    This provides sub-pixel accuracy for tile positioning, allowing precise
    alignment of GPS coordinates on the assembled map.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        zoom: OSM zoom level (1-19)
    
    Returns:
        Tuple of (tile_x, tile_y) as floats
    """
    n = 2 ** zoom
    fx = (lon + 180.0) / 360.0 * n
    fy = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return fx, fy


def lat_lon_to_pixel_on_map(lat, lon, origin_fx, origin_fy, zoom):
    """
    Convert lat/lon to pixel coordinates on an assembled tile map.
    
    This uses fractional tile coordinates to achieve sub-pixel accuracy,
    ensuring GPS points are positioned exactly where they should be.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        origin_fx: Fractional tile X coordinate of map's top-left corner
        origin_fy: Fractional tile Y coordinate of map's top-left corner
        zoom: OSM zoom level
    
    Returns:
        Tuple of (pixel_x, pixel_y) as floats
    """
    fx, fy = lat_lon_to_tile_float(lat, lon, zoom)
    px = (fx - origin_fx) * TILE_SIZE
    py = (fy - origin_fy) * TILE_SIZE
    return px, py


def get_osm_tile(z, x, y, use_cache=True):
    """
    Download an OSM tile from the server or retrieve from cache.
    
    This function implements a tile download logic that avoids downloading
    tiles every time by using a local cache.
    
    Args:
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        use_cache: Whether to use cached tiles (default: True)
    
    Returns:
        PIL Image object in RGBA format, or None if download fails
    """
    # Check cache first
    cache_path = os.path.join(OSM_CACHE_DIR, f"{z}_{x}_{y}.png")
    
    if use_cache and os.path.exists(cache_path):
        try:
            img = Image.open(cache_path).convert("RGBA")
            print(f"Map node: Tile {z}/{x}/{y} loaded from cache (no download needed)")
            return img
        except Exception as e:
            print(f"Map node: Cache read error for tile {z}/{x}/{y}: {e}")
            # Remove corrupted cache file
            try:
                os.remove(cache_path)
            except:
                pass
    
    # Download tile
    try:
        url = OSM_TILE_URL.format(z=z, x=x, y=y)
        print(f"Map node: Downloading tile {z}/{x}/{y} from OSM server...")
        response = requests.get(url, headers=OSM_HEADERS, timeout=8)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        
        # Save to cache
        if use_cache:
            try:
                img.save(cache_path)
                print(f"Map node: Tile {z}/{x}/{y} saved to cache for future use")
            except Exception as e:
                print(f"Map node: Cache write error for tile {z}/{x}/{y}: {e}")
        
        return img
    except Exception as e:
        print(f"Map node: Download error for tile {z}/{x}/{y}: {e}")
        # Return gray fallback tile
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (180, 180, 180, 255))


def assemble_osm_map(center_lat, center_lon, zoom, tiles_x=3, tiles_y=3, progress_callback=None):
    """
    Assemble an OSM map centered exactly on the given coordinates.
    
    This function downloads the necessary tiles and assembles them with
    sub-pixel accuracy to ensure the center point is positioned exactly
    at the center of the resulting image.
    
    Implements tile download logic with caching to avoid downloading tiles every time.
    
    Args:
        center_lat: Latitude of center point
        center_lon: Longitude of center point
        zoom: OSM zoom level (1-19)
        tiles_x: Number of tiles horizontally (default: 3)
        tiles_y: Number of tiles vertically (default: 3)
        progress_callback: Optional callback function(current, total, from_cache) for progress updates
    
    Returns:
        Tuple of (pil_image, origin_fx, origin_fy, cache_stats) where:
        - pil_image: Assembled map as PIL Image
        - origin_fx: Fractional tile X of top-left corner
        - origin_fy: Fractional tile Y of top-left corner
        - cache_stats: Dict with 'cached', 'downloaded', 'total' tile counts
    """
    # Calculate fractional tile position of center
    fx, fy = lat_lon_to_tile_float(center_lat, center_lon, zoom)
    
    # Calculate origin (top-left corner of grid)
    origin_fx = fx - tiles_x / 2.0
    origin_fy = fy - tiles_y / 2.0
    
    # Integer tile coordinates for downloading
    tile_x0 = int(math.floor(origin_fx))
    tile_y0 = int(math.floor(origin_fy))
    
    # Offset within the first tile (sub-pixel positioning)
    off_x = int((origin_fx - tile_x0) * TILE_SIZE)
    off_y = int((origin_fy - tile_y0) * TILE_SIZE)
    
    # Create larger canvas to accommodate offset
    map_w = TILE_SIZE * tiles_x
    map_h = TILE_SIZE * tiles_y
    canvas = Image.new("RGBA", (map_w + TILE_SIZE, map_h + TILE_SIZE))
    
    # Track cache statistics
    tiles_from_cache = 0
    tiles_downloaded = 0
    
    # Download and paste tiles
    total_tiles = (tiles_y + 1) * (tiles_x + 1)
    current_tile = 0
    tiles_downloaded_so_far = 0  # Progress counter for downloads
    
    print(f"Map node: Assembling map with {total_tiles} tiles at zoom {zoom}...")
    
    # First, check how many tiles need downloading
    tiles_need_download = 0
    for row in range(tiles_y + 1):
        for col in range(tiles_x + 1):
            z, x, y = zoom, tile_x0 + col, tile_y0 + row
            cache_path = os.path.join(OSM_CACHE_DIR, f"{z}_{x}_{y}.png")
            if not os.path.exists(cache_path):
                tiles_need_download += 1
    
    # If all tiles are cached, notify callback to hide progress bar
    if tiles_need_download == 0 and progress_callback:
        progress_callback(0, 0, True)  # Signal all cached
    
    for row in range(tiles_y + 1):
        for col in range(tiles_x + 1):
            z, x, y = zoom, tile_x0 + col, tile_y0 + row
            cache_path = os.path.join(OSM_CACHE_DIR, f"{z}_{x}_{y}.png")
            
            # Check if tile was already cached before calling get_osm_tile
            was_cached = os.path.exists(cache_path)
            
            tile = get_osm_tile(z, x, y)
            if tile:
                canvas.paste(tile, (col * TILE_SIZE, row * TILE_SIZE))
                
                # Update statistics
                if was_cached:
                    tiles_from_cache += 1
                else:
                    tiles_downloaded += 1
                    tiles_downloaded_so_far += 1
                    # Only update progress for downloaded tiles to avoid blinking
                    if progress_callback:
                        progress_callback(tiles_downloaded_so_far, tiles_need_download, False)
            
            current_tile += 1
    
    # Log cache statistics
    print(f"Map node: Tile cache summary - {tiles_from_cache} from cache, "
          f"{tiles_downloaded} downloaded, {total_tiles} total")
    
    # Crop to final size with sub-pixel offset
    final_img = canvas.crop((off_x, off_y, off_x + map_w, off_y + map_h))
    
    # Return cache statistics along with the image
    cache_stats = {
        'cached': tiles_from_cache,
        'downloaded': tiles_downloaded,
        'total': total_tiles
    }
    
    return final_img, origin_fx, origin_fy, cache_stats


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
        # Pan controls
        node.tag_node_pan_x_value_name = node.tag_node_name + ':PanXValue'
        node.tag_node_pan_y_value_name = node.tag_node_name + ':PanYValue'
        # Download progress bar
        node.tag_node_progress_name = node.tag_node_name + ':Progress'

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
                    label="",
                    width=small_window_w,
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
                    label="",
                    width=small_window_w,
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
                    label="",
                    width=small_window_w,
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
                    label="",
                    width=small_window_w,
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

            # Download progress bar
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_progress_bar(
                    label="Download Progress",
                    tag=node.tag_node_progress_name,
                    default_value=0.0,
                    overlay="",
                    width=small_window_w,
                    show=False,  # Initially hidden, will show only when downloading
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
        tag_node_pan_x_value_name = tag_node_name + ':PanXValue'
        tag_node_pan_y_value_name = tag_node_name + ':PanYValue'
        tag_node_progress_name = tag_node_name + ':Progress'

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
                            
                            # Log current parameter values
                            print(f"Map node: Parameters - zoom={zoom_level}, size={size_factor}, pan_x={pan_x}, pan_y={pan_y}, cache={use_cache}")
                            
                            # Create map visualization image (main display)
                            preview_image, cache_stats = self._create_preview_image(
                                points, small_window_w, small_window_h, zoom_level, size_factor, pan_x, pan_y, tag_node_progress_name
                            )
                        else:
                            print("Map node: No lat/lon in data")
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
                        
                        # Log current parameter values
                        print(f"Map node: Parameters - zoom={zoom_level}, size={size_factor}, pan_x={pan_x}, pan_y={pan_y}, cache={use_cache}")
                        
                        # Create map visualization image (main display)
                        preview_image, cache_stats = self._create_preview_image(
                            points, small_window_w, small_window_h, zoom_level, size_factor, pan_x, pan_y, tag_node_progress_name
                        )
                    else:
                        print("Map node: No lat/lon in data")
                    
            except json.JSONDecodeError as e:
                error_msg = f"JSON parse error: {str(e)[:60]}"
                print(f"Map node: {error_msg}")
            except Exception as e:
                error_msg = f"Error: {str(e)[:40]}"
                print(f"Map node: Error processing data: {e}")
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


    def _create_preview_image(self, points, width, height, zoom_level=10, size_factor=1.0, pan_x=0.0, pan_y=0.0, progress_tag=None):
        """
        Create a map visualization image using enhanced OSM tile rendering.
        
        This method:
        1. Tries direct OSM tile assembly with sub-pixel accuracy (preferred)
        2. Falls back to contextily rendering if direct method fails
        3. Falls back to matplotlib-only rendering if both fail
        
        Args:
            points: List of points with 'lat' and 'lon' keys
            width: Width of output image in pixels
            height: Height of output image in pixels
            zoom_level: OSM tile zoom level (1-18)
            size_factor: View size factor (0.5-5.0)
            pan_x: Horizontal pan offset (-1.0 to 1.0)
            pan_y: Vertical pan offset (-1.0 to 1.0)
            progress_tag: Optional DearPyGUI tag for progress bar updates
        
        Returns:
            Tuple of (numpy array in BGR format, cache_stats dict) or (numpy array, None) for fallbacks
        """
        if not points:
            preview = np.zeros((height, width, 3), dtype=np.uint8)
            return preview, None
        
        print(f"Map node: Creating preview with zoom={zoom_level}, size={size_factor}")
        
        # Try direct OSM tile rendering first (enhanced method)
        try:
            return self._render_with_direct_osm_tiles(points, width, height, zoom_level, size_factor, pan_x, pan_y, progress_tag)
        except Exception as e:
            print(f"Map node: Direct OSM rendering failed: {e}")
            traceback.print_exc()
            print("Map node: Falling back to contextily rendering")
        
        # Try contextily rendering as fallback
        if CONTEXTILY_AVAILABLE:
            try:
                return self._render_with_contextily(points, width, height, zoom_level, size_factor, pan_x, pan_y), None
            except Exception as e:
                print(f"Map node: Error rendering with contextily: {e}")
                traceback.print_exc()
                print("Map node: Falling back to matplotlib-only rendering")
        
        # Final fallback to matplotlib rendering without basemap
        return self._render_with_matplotlib(points, width, height), None


    def _render_with_direct_osm_tiles(self, points, width, height, zoom_level=10, size_factor=1.0, pan_x=0.0, pan_y=0.0, progress_tag=None):
        """
        Enhanced OSM rendering using direct tile download and assembly.
        
        This method provides sub-pixel accurate positioning of GPS points by:
        1. Calculating the map center from all points
        2. Assembling OSM tiles with fractional tile positioning
        3. Converting GPS coordinates to exact pixel positions
        4. Drawing markers with visual enhancements (halos, shadows)
        
        Args:
            points: List of points with 'lat' and 'lon' keys
            width: Width of output image in pixels
            height: Height of output image in pixels
            zoom_level: OSM tile zoom level (1-18)
            size_factor: View size factor (0.5-5.0, not used in this method)
            pan_x: Horizontal pan offset (-1.0 to 1.0)
            pan_y: Vertical pan offset (-1.0 to 1.0)
            progress_tag: Optional DearPyGUI tag for progress bar updates
        
        Returns:
            Tuple of (numpy array in BGR format, cache_stats dict)
        """
        if not points:
            # Return empty blue background
            img = np.zeros((height, width, 3), dtype=np.uint8)
            img[:] = (224, 216, 173)  # Light blue-gray
            return img, None
        
        try:
            # Calculate center point from all GPS coordinates
            lats = [p['lat'] for p in points]
            lons = [p['lon'] for p in points]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            
            # Apply pan offsets to center
            # For pan, we shift the center by a fraction of the visible area
            # Approximate: 0.01 degrees per 0.1 pan unit at zoom 12
            lat_range = max(lats) - min(lats) if len(set(lats)) > 1 else 0.01
            lon_range = max(lons) - min(lons) if len(set(lons)) > 1 else 0.01
            
            # Apply pan (negative because map moves opposite to pan direction)
            center_lat -= pan_y * lat_range * 0.5
            center_lon += pan_x * lon_range * 0.5
            
            # Calculate number of tiles needed
            tiles_x = max(3, (width + TILE_SIZE - 1) // TILE_SIZE)
            tiles_y = max(3, (height + TILE_SIZE - 1) // TILE_SIZE)
            
            print(f"Map node (direct OSM): Assembling {tiles_x}x{tiles_y} tiles at zoom {zoom_level}")
            print(f"Map node (direct OSM): Center: ({center_lat:.6f}, {center_lon:.6f})")
            
            # Define progress callback function
            def update_progress(current, total, from_cache):
                if progress_tag and dpg.does_item_exist(progress_tag):
                    # If from_cache is True, it means all tiles are cached - hide progress bar
                    if from_cache:
                        dpg.hide_item(progress_tag)
                    # Only show progress bar if there are tiles to download
                    elif total > 0:
                        progress = current / total
                        dpg.set_value(progress_tag, progress)
                        overlay_text = f"Downloading: {current}/{total} tiles"
                        dpg.configure_item(progress_tag, overlay=overlay_text)
                        # Make progress bar visible
                        dpg.show_item(progress_tag)
            
            # Assemble map with sub-pixel accuracy and progress tracking
            pil_map, origin_fx, origin_fy, cache_stats = assemble_osm_map(
                center_lat, center_lon, zoom_level, tiles_x, tiles_y, update_progress
            )
            
            # Convert PIL image to numpy array
            map_array = np.array(pil_map)
            
            # Convert RGBA to BGR for OpenCV
            if map_array.shape[2] == 4:
                map_array = cv2.cvtColor(map_array, cv2.COLOR_RGBA2BGR)
            else:
                map_array = cv2.cvtColor(map_array, cv2.COLOR_RGB2BGR)
            
            # Draw GPS points with enhanced markers
            for point in points:
                # Calculate exact pixel position
                px, py = lat_lon_to_pixel_on_map(
                    point['lat'], point['lon'], 
                    origin_fx, origin_fy, zoom_level
                )
                
                px, py = int(px), int(py)
                
                # Skip points outside the visible area
                if px < 0 or px >= map_array.shape[1] or py < 0 or py >= map_array.shape[0]:
                    continue
                
                # Draw halo (outer glow) with semi-transparent blending
                overlay = map_array.copy()
                cv2.circle(overlay, (px, py), 14, (180, 120, 80), -1, cv2.LINE_AA)
                cv2.addWeighted(overlay, 0.3, map_array, 0.7, 0, map_array)
                
                # Draw outer ring
                cv2.circle(map_array, (px, py), 14, (0, 80, 255), 2, cv2.LINE_AA)
                
                # Draw main dot
                cv2.circle(map_array, (px, py), 6, (0, 30, 220), -1, cv2.LINE_AA)
                cv2.circle(map_array, (px, py), 6, (0, 50, 255), 2, cv2.LINE_AA)
            
            # Resize to target dimensions if needed
            if map_array.shape[1] != width or map_array.shape[0] != height:
                map_array = cv2.resize(map_array, (width, height), interpolation=cv2.INTER_AREA)
            
            # Reset progress bar after rendering completes and hide it
            if progress_tag and dpg.does_item_exist(progress_tag):
                dpg.set_value(progress_tag, 0.0)
                dpg.configure_item(progress_tag, overlay="")
                dpg.hide_item(progress_tag)
            
            print(f"Map node (direct OSM): Rendered {len(points)} points successfully")
            return map_array, cache_stats
            
        except Exception as e:
            print(f"Map node (direct OSM): Error rendering with direct tiles: {e}")
            traceback.print_exc()
            # Fall back to contextily method
            return self._render_with_contextily(points, width, height, zoom_level, size_factor, pan_x, pan_y), None


    def _render_with_contextily(self, points, width, height, zoom_level=10, size_factor=1.0, pan_x=0.0, pan_y=0.0):
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
            zoom_level: OSM tile zoom level (1-18)
            size_factor: View size factor (0.5-5.0)
            pan_x: Horizontal pan offset (-1.0 to 1.0)
            pan_y: Vertical pan offset (-1.0 to 1.0)
        
        Returns:
            numpy array in BGR format
        """
        print(f"Map node: _render_with_contextily called with zoom={zoom_level}, size={size_factor}, pan=({pan_x}, {pan_y})")
        
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
        
        print(f"Map node: Converted {len(mercator_points)} points to Web Mercator")
        
        # Calculate extent (bounding box) with size_factor and pan offsets
        xs = [p['x'] for p in mercator_points]
        ys = [p['y'] for p in mercator_points]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        print(f"Map node: Initial bounds - X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
        
        # Add padding using the same logic as _calculate_extent
        x_range = max_x - min_x
        y_range = max_y - min_y
        
        # Ensure minimum range for single points or very close points
        if x_range < MIN_RANGE_METERS:
            x_range = DEFAULT_RANGE_METERS
            print(f"Map node: X range too small, using default: {DEFAULT_RANGE_METERS}m")
        if y_range < MIN_RANGE_METERS:
            y_range = DEFAULT_RANGE_METERS
            print(f"Map node: Y range too small, using default: {DEFAULT_RANGE_METERS}m")
        
        # Apply size factor (direct multiplication: smaller factor = smaller range = zoom in)
        # size_factor < 1.0 = zoom in (smaller range)
        # size_factor = 1.0 = normal view
        # size_factor > 1.0 = zoom out (larger range)
        x_range = x_range * size_factor
        y_range = y_range * size_factor
        print(f"Map node: Range after size_factor ({size_factor}): X={x_range:.2f}m, Y={y_range:.2f}m")
        
        min_x -= x_range * MAP_PADDING_FACTOR
        max_x += x_range * MAP_PADDING_FACTOR
        min_y -= y_range * MAP_PADDING_FACTOR
        max_y += y_range * MAP_PADDING_FACTOR
        
        print(f"Map node: After padding ({MAP_PADDING_FACTOR}): X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
        
        # Apply pan offsets
        total_x_range = max_x - min_x
        total_y_range = max_y - min_y
        
        pan_x_meters = pan_x * total_x_range
        pan_y_meters = pan_y * total_y_range
        
        min_x += pan_x_meters
        max_x += pan_x_meters
        min_y += pan_y_meters
        max_y += pan_y_meters
        
        print(f"Map node: After pan ({pan_x}, {pan_y}): X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
        
        # Create figure
        dpi = 150
        fig_width = width / dpi
        fig_height = height / dpi
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        print(f"Map node: Created figure {fig_width}x{fig_height} inches at {dpi} DPI")
        
        # Plot points in Web Mercator coordinates
        for point in mercator_points:
            ax.plot(point['x'], point['y'], 'o', 
                   color='red', markersize=10, 
                   markeredgecolor='darkred', markeredgewidth=2,
                   markerfacecolor='yellow', zorder=5)
        
        # Set axis limits
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        
        # Set background colors BEFORE attempting to load tiles
        # This ensures a proper background is visible whether tiles load or not
        ax.set_facecolor('#ADD8E6')  # Light blue background for axes
        fig.patch.set_facecolor('#E0F2F7')  # Light blue background for figure
        
        # Add OSM basemap using contextily
        # Use the zoom_level parameter from the slider
        basemap_loaded = False
        try:
            print(f"Map node: Attempting to load OSM tiles with zoom={zoom_level}")
            print(f"Map node: Using provider: {ctx.providers.OpenStreetMap.Mapnik}")
            print(f"Map node: CRS: EPSG:3857 (Web Mercator)")
            
            ctx.add_basemap(ax, crs='EPSG:3857', source=ctx.providers.OpenStreetMap.Mapnik,
                          zoom=zoom_level, attribution=None)
            basemap_loaded = True
            print("✓ Map node: OpenStreetMap tiles loaded successfully")
        except Exception as e:
            print(f"⚠ Map node: Could not load OpenStreetMap tiles")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error message: {e}")
            traceback.print_exc()
            print("  Using fallback: light blue background without tiles")
            # Background already set above - points will still be visible
        
        # Hide axes completely - we don't want to show x,y coordinates (Web Mercator values)
        # The map tiles provide the geographic context, not numeric coordinates
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Set title with status indicator
        title_text = f'Map View - {len(points)} point(s)'
        if not basemap_loaded:
            title_text += ' (no tiles)'
        ax.set_title(title_text, fontsize=10, pad=10)
        
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
        dpi = 150
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
