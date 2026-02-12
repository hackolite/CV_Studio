#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Map Node - Visualize geographical data on OpenStreetMap
Takes JSON input with latitude/longitude coordinates and displays them on a map
"""
import time
import json
from typing import List, Tuple, Optional, Dict, Any

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode

# Import matplotlib for map rendering
import matplotlib
matplotlib.use('Agg')  # Force non-GUI backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg


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
        
        # Input: JSON data
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        
        # Output: Map visualization
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        
        # Output: Processing time
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        
        # Zoom slider control
        node.tag_node_zoom_name = node.tag_node_name + ':Zoom'
        node.tag_node_zoom_value_name = node.tag_node_name + ':ZoomValue'
        
        # Pan X (horizontal) slider
        node.tag_node_pan_x_name = node.tag_node_name + ':PanX'
        node.tag_node_pan_x_value_name = node.tag_node_name + ':PanXValue'
        
        # Pan Y (vertical) slider
        node.tag_node_pan_y_name = node.tag_node_name + ':PanY'
        node.tag_node_pan_y_value_name = node.tag_node_name + ':PanYValue'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create black texture for initial display
        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        # Register texture
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Create node UI
        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Input JSON
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='JSON (lat/lon)',
                )

            # Output map image
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Zoom slider
            with dpg.node_attribute(
                    tag=node.tag_node_zoom_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_zoom_value_name,
                    label="Zoom",
                    width=small_window_w - 80,
                    default_value=1.0,
                    min_value=0.5,
                    max_value=10.0,
                    callback=None,
                )

            # Pan X slider (left/right)
            with dpg.node_attribute(
                    tag=node.tag_node_pan_x_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_pan_x_value_name,
                    label="Pan X (Left/Right)",
                    width=small_window_w - 80,
                    default_value=0.0,
                    min_value=-1.0,
                    max_value=1.0,
                    callback=None,
                )

            # Pan Y slider (up/down)
            with dpg.node_attribute(
                    tag=node.tag_node_pan_y_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_pan_y_value_name,
                    label="Pan Y (Up/Down)",
                    width=small_window_w - 80,
                    default_value=0.0,
                    min_value=-1.0,
                    max_value=1.0,
                    callback=None,
                )

            # Processing time output
            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

        return node


class Node(BaseNode):
    _ver = '0.0.1'

    node_label = 'Map'
    node_tag = 'Map'

    def __init__(self, opencv_setting_dict=None):
        super().__init__()

        if opencv_setting_dict is None:
            opencv_setting_dict = {
                'process_height': 480,
                'process_width': 640
            }

        self._opencv_setting_dict = opencv_setting_dict
        
        # Store initial bounds for auto-fit
        self.initial_bounds = None
        self.auto_fit = True

    def extract_coordinates(self, json_data: Any) -> List[Tuple[float, float]]:
        """
        Extract latitude and longitude coordinates from JSON data.
        Supports various JSON structures including AIS data.
        
        Args:
            json_data: JSON data (dict, list, or string)
            
        Returns:
            List of (latitude, longitude) tuples
        """
        coordinates = []
        
        # Parse JSON string if needed
        if isinstance(json_data, str):
            try:
                json_data = json.loads(json_data)
            except json.JSONDecodeError:
                return coordinates
        
        # Handle different JSON structures
        if isinstance(json_data, dict):
            # Check for AIS boat data structure
            if 'boats' in json_data:
                for boat in json_data.get('boats', []):
                    lat = boat.get('latitude')
                    lon = boat.get('longitude')
                    if lat is not None and lon is not None:
                        coordinates.append((float(lat), float(lon)))
            
            # Check for direct lat/lon in dict
            elif 'latitude' in json_data and 'longitude' in json_data:
                lat = json_data.get('latitude')
                lon = json_data.get('longitude')
                if lat is not None and lon is not None:
                    coordinates.append((float(lat), float(lon)))
            
            # Check for lat/lon or lat/lng variants
            elif 'lat' in json_data and 'lon' in json_data:
                lat = json_data.get('lat')
                lon = json_data.get('lon')
                if lat is not None and lon is not None:
                    coordinates.append((float(lat), float(lon)))
            
            elif 'lat' in json_data and 'lng' in json_data:
                lat = json_data.get('lat')
                lon = json_data.get('lng')
                if lat is not None and lon is not None:
                    coordinates.append((float(lat), float(lon)))
            
            # Recursively search in nested structures
            else:
                for value in json_data.values():
                    coordinates.extend(self.extract_coordinates(value))
        
        elif isinstance(json_data, list):
            # Process each item in list
            for item in json_data:
                coordinates.extend(self.extract_coordinates(item))
        
        return coordinates

    def calculate_bounds(
        self, 
        coordinates: List[Tuple[float, float]]
    ) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box for coordinates.
        
        Args:
            coordinates: List of (latitude, longitude) tuples
            
        Returns:
            (min_lat, max_lat, min_lon, max_lon)
        """
        if not coordinates:
            # Default bounds (world view)
            return (-90, 90, -180, 180)
        
        lats = [coord[0] for coord in coordinates]
        lons = [coord[1] for coord in coordinates]
        
        min_lat = min(lats)
        max_lat = max(lats)
        min_lon = min(lons)
        max_lon = max(lons)
        
        # Add padding (10% on each side)
        lat_padding = (max_lat - min_lat) * 0.1 if max_lat != min_lat else 1.0
        lon_padding = (max_lon - min_lon) * 0.1 if max_lon != min_lon else 1.0
        
        min_lat -= lat_padding
        max_lat += lat_padding
        min_lon -= lon_padding
        max_lon += lon_padding
        
        # Clamp to valid lat/lon ranges
        min_lat = max(-90, min_lat)
        max_lat = min(90, max_lat)
        min_lon = max(-180, min_lon)
        max_lon = min(180, max_lon)
        
        return (min_lat, max_lat, min_lon, max_lon)

    def render_map(
        self,
        coordinates: List[Tuple[float, float]],
        bounds: Tuple[float, float, float, float],
        width: int,
        height: int,
        zoom: float = 1.0,
        pan_x: float = 0.0,
        pan_y: float = 0.0,
    ) -> np.ndarray:
        """
        Render map with coordinates using matplotlib.
        
        Args:
            coordinates: List of (latitude, longitude) tuples
            bounds: (min_lat, max_lat, min_lon, max_lon)
            width: Output width in pixels
            height: Output height in pixels
            zoom: Zoom level (0.5 = zoom out, 2.0 = zoom in)
            pan_x: Horizontal pan (-1.0 to 1.0, left to right)
            pan_y: Vertical pan (-1.0 to 1.0, down to up)
            
        Returns:
            RGB image as numpy array
        """
        min_lat, max_lat, min_lon, max_lon = bounds
        
        # Apply zoom (inverse - higher zoom means smaller view)
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        lat_range = (max_lat - min_lat) / zoom
        lon_range = (max_lon - min_lon) / zoom
        
        # Calculate panned bounds
        pan_lat_offset = (max_lat - min_lat) * pan_y * 0.5
        pan_lon_offset = (max_lon - min_lon) * pan_x * 0.5
        
        view_min_lat = center_lat - lat_range / 2 + pan_lat_offset
        view_max_lat = center_lat + lat_range / 2 + pan_lat_offset
        view_min_lon = center_lon - lon_range / 2 + pan_lon_offset
        view_max_lon = center_lon + lon_range / 2 + pan_lon_offset
        
        # Create figure with exact pixel size
        dpi = 100
        fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax = fig.add_subplot(111)
        
        # Set background color (light blue for water)
        ax.set_facecolor('#aadaff')
        
        # Draw a simple grid to represent map tiles
        # This is a simplified representation without actual OSM tiles
        grid_color = '#cccccc'
        ax.grid(True, color=grid_color, linestyle='-', linewidth=0.5, alpha=0.5)
        
        # Plot coordinates as red dots
        if coordinates:
            lats = [coord[0] for coord in coordinates]
            lons = [coord[1] for coord in coordinates]
            ax.scatter(lons, lats, c='red', s=50, alpha=0.7, 
                      edgecolors='darkred', linewidths=1.5, zorder=5)
        
        # Set axis limits
        ax.set_xlim(view_min_lon, view_max_lon)
        ax.set_ylim(view_min_lat, view_max_lat)
        
        # Labels
        ax.set_xlabel('Longitude', fontsize=10)
        ax.set_ylabel('Latitude', fontsize=10)
        ax.set_title(f'Map View ({len(coordinates)} points)', fontsize=12, fontweight='bold')
        
        # Add coordinate info text
        if coordinates:
            info_text = (f"Bounds: [{view_min_lat:.2f}, {view_max_lat:.2f}] x "
                        f"[{view_min_lon:.2f}, {view_max_lon:.2f}]")
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                   fontsize=8, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Tight layout
        plt.tight_layout()
        
        # Render to numpy array
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        
        # Get RGB buffer
        buf = canvas.buffer_rgba()
        image = np.asarray(buf)
        
        # Convert RGBA to RGB
        image = image[:, :, :3]
        
        # Close figure to free memory
        plt.close(fig)
        
        return image

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Input/output tags
        input_value01_tag = tag_node_name + ':' + self.TYPE_JSON + ':Input01Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        
        # Control tags
        zoom_value_tag = tag_node_name + ':ZoomValue'
        pan_x_value_tag = tag_node_name + ':PanXValue'
        pan_y_value_tag = tag_node_name + ':PanYValue'
        
        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Start timing
        if use_pref_counter:
            start = time.perf_counter()

        # Get input JSON data
        json_data = node_result_dict.get(input_value01_tag, None)
        
        # Get control values
        zoom = dpg_get_value(zoom_value_tag)
        pan_x = dpg_get_value(pan_x_value_tag)
        pan_y = dpg_get_value(pan_y_value_tag)
        
        # Extract coordinates from JSON
        coordinates = []
        if json_data is not None:
            coordinates = self.extract_coordinates(json_data)
        
        # Calculate bounds
        if self.auto_fit and coordinates:
            # First time or when new data arrives, auto-fit to show all points
            self.initial_bounds = self.calculate_bounds(coordinates)
            self.auto_fit = False
        elif not self.initial_bounds:
            # No data yet, use default bounds
            self.initial_bounds = self.calculate_bounds([])
        
        # Render map
        map_image = self.render_map(
            coordinates=coordinates,
            bounds=self.initial_bounds,
            width=small_window_w,
            height=small_window_h,
            zoom=zoom,
            pan_x=pan_x,
            pan_y=pan_y,
        )
        
        # Convert to DPG texture format
        texture = self.convert_cv_to_dpg(
            map_image,
            small_window_w,
            small_window_h,
        )
        
        # Update texture
        dpg_set_value(output_value01_tag, texture)
        
        # Update timing
        if use_pref_counter:
            elapsed_time = (time.perf_counter() - start) * 1000
            dpg_set_value(output_value02_tag, f"{elapsed_time:.2f}ms")
        
        # Store in output dict
        node_image_dict[output_value01_tag] = map_image

    def close(self, node_id):
        """Cleanup when node is closed"""
        pass

    def get_setting_dict(self, node_id):
        """Get node settings for serialization"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        zoom_value_tag = tag_node_name + ':ZoomValue'
        pan_x_value_tag = tag_node_name + ':PanXValue'
        pan_y_value_tag = tag_node_name + ':PanYValue'
        
        return {
            'zoom': dpg_get_value(zoom_value_tag),
            'pan_x': dpg_get_value(pan_x_value_tag),
            'pan_y': dpg_get_value(pan_y_value_tag),
        }
