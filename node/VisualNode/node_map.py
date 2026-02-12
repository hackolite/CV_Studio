#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import json
import os
import tempfile
import webbrowser
from datetime import datetime

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


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

            # Status text
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_status_value_name,
                    default_value='No data',
                )

            # Open map button
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=node.tag_node_open_button_name,
                    label="Open Map in Browser",
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
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Input01Value'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        tag_node_output02_value_name = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
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
                    
                    # Get zoom and size parameters
                    zoom_level = dpg_get_value(tag_node_zoom_value_name)
                    size_factor = dpg_get_value(tag_node_size_value_name)
                    
                    # Generate map
                    map_path = self._generate_map(points, zoom_level, size_factor)
                    
                    if map_path:
                        self.last_map_path = map_path
                        status_text = f"✓ {len(points)} points mapped"
                        print(f"Map node: Map generated at {map_path}")
                    else:
                        # Map generation failed (likely folium not installed)
                        status_text = f"Points: {len(points)} (folium needed)"
                        print("Map node: Map generation failed (folium not installed)")
                    
                    # Create preview image
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


    def _generate_map(self, points, zoom_level, size_factor):
        """Generate an HTML map with Leaflet using folium"""
        try:
            import folium
            from folium.plugins import MarkerCluster
        except ImportError:
            print("folium not installed, map generation skipped. Install with: pip install folium")
            return None

        if not points:
            return None

        # Calculate center and bounds
        lats = [p['lat'] for p in points]
        lons = [p['lon'] for p in points]
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Calculate bounds with size factor
        lat_range = (max(lats) - min(lats)) * size_factor
        lon_range = (max(lons) - min(lons)) * size_factor
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_level,
            tiles='OpenStreetMap'
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
        
        # Save to temp file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        map_path = os.path.join(temp_dir, f"cv_studio_map_{timestamp}.html")
        m.save(map_path)
        
        return map_path


    def _create_preview_image(self, points, width, height):
        """Create a simple preview image showing point distribution"""
        preview = np.zeros((height, width, 3), dtype=np.uint8)
        
        if not points:
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
            lat_range = 1
        if lon_range == 0:
            lon_range = 1
        
        padding = 0.1
        min_lat -= lat_range * padding
        max_lat += lat_range * padding
        min_lon -= lon_range * padding
        max_lon += lon_range * padding
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        
        # Draw background (ocean blue)
        preview[:] = (120, 60, 20)  # BGR
        
        # Draw grid
        for i in range(5):
            y = int(height * i / 4)
            cv2.line(preview, (0, y), (width, y), (80, 40, 10), 1)
            x = int(width * i / 4)
            cv2.line(preview, (x, 0), (x, height), (80, 40, 10), 1)
        
        # Draw points
        for point in points:
            # Normalize coordinates
            x = int((point['lon'] - min_lon) / lon_range * (width - 20) + 10)
            y = int((1 - (point['lat'] - min_lat) / lat_range) * (height - 20) + 10)
            
            # Draw point
            cv2.circle(preview, (x, y), 3, (0, 255, 255), -1)  # Yellow
            cv2.circle(preview, (x, y), 4, (0, 0, 255), 1)  # Red border
        
        # Add text overlay
        text = f"{len(points)} points"
        cv2.putText(preview, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        return preview


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
        
        return {
            'zoom': dpg_get_value(tag_node_zoom_value_name),
            'size': dpg_get_value(tag_node_size_value_name),
        }


    def set_setting_dict(self, node_id, setting_dict):
        """Set node settings when loading"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
        
        if 'zoom' in setting_dict:
            dpg_set_value(tag_node_zoom_value_name, setting_dict['zoom'])
        if 'size' in setting_dict:
            dpg_set_value(tag_node_size_value_name, setting_dict['size'])


    def convert_cv_to_dpg(self, image, width, height):
        """Convert OpenCV image to DearPyGUI texture format"""
        resize_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        data = np.flip(resize_image, 2)
        data = data.ravel()
        data = np.asarray(data, dtype=np.float32)
        texture_data = np.true_divide(data, 255.0)
        return texture_data
