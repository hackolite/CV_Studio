#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import copy
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FactoryNode:
    node_label = 'DistanceTracker'
    node_tag = 'DistanceTracker'

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
        
        # Input 1: JSON from Homography node with transformed points
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        
        # Input 2: JSON boolean to enable/disable tracking
        node.tag_node_input_enable_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input_enable_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        
        # Output 1: JSON with distance information
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'
        
        # Output 2: Elapsed time
        node.tag_node_output_time_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output_time_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create yellow theme for JSON buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # JSON Input from Homography
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='JSON',
                )

            # JSON boolean Input for enable/disable
            with dpg.node_attribute(
                tag=node.tag_node_input_enable_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_enable_value_name,
                    default_value='JSON (boolean)',
                )

            # JSON Output
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(default_value='JSON')
                btn = dpg.add_button(
                    label="Distance Data",
                    tag=node.tag_node_output_json_value_name,
                    width=200,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)

            # Time Output
            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output_time_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output_time_value_name,
                        default_value='Elapsed time(ms)',
                    )

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'DistanceTracker'
    node_tag = 'DistanceTracker'

    _opencv_setting_dict = None
    
    # Store previous positions for each player/object (by label)
    _previous_positions = {}
    
    # Store cumulative distances for each player/object (by label)
    _cumulative_distances = {}
    
    # Track previous tracking_enabled state per node
    _previous_tracking_state = {}

    def __init__(self):
        pass

    def _calculate_euclidean_distance(self, point1, point2):
        """
        Calculate Euclidean distance between two points in meters.
        
        Args:
            point1: [x, y] coordinates in meters
            point2: [x, y] coordinates in meters
            
        Returns:
            distance in meters
        """
        if point1 is None or point2 is None:
            return 0.0
        
        dx = point2[0] - point1[0]
        dy = point2[1] - point1[1]
        return np.sqrt(dx**2 + dy**2)

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_time_value_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Find JSON input connections
        json_connection_info_src = ''
        enable_connection_info_src = ''
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            connection_target = connection_info[1]
            
            if connection_type == self.TYPE_JSON or connection_type.upper() == 'JSON':
                # Check which input this connects to
                if ':Input01' in connection_target:
                    # Homography JSON input
                    json_connection_info_src = connection_info[0]
                    json_connection_info_src = json_connection_info_src.split(':')[:2]
                    json_connection_info_src = ':'.join(json_connection_info_src)
                elif ':Input02' in connection_target:
                    # Enable/disable boolean input
                    enable_connection_info_src = connection_info[0]
                    enable_connection_info_src = enable_connection_info_src.split(':')[:2]
                    enable_connection_info_src = ':'.join(enable_connection_info_src)

        # Get JSON data from Homography node
        json_data = node_result_dict.get(json_connection_info_src, None) if json_connection_info_src else None
        
        # Get enable/disable boolean (default: True)
        tracking_enabled = True
        if enable_connection_info_src:
            enable_data = node_result_dict.get(enable_connection_info_src, None)
            if enable_data is not None:
                # Extract boolean value from JSON
                if isinstance(enable_data, dict):
                    tracking_enabled = enable_data.get('enabled', True)
                elif isinstance(enable_data, bool):
                    tracking_enabled = enable_data

        if use_pref_counter and json_data is not None:
            start_time = time.monotonic()

        # Create output JSON
        output_json = None
        
        # Check if tracking state changed from disabled to enabled (stop->start transition)
        node_id_str = str(node_id)
        previous_state = self._previous_tracking_state.get(node_id_str, True)
        if not previous_state and tracking_enabled:
            # Transition from stop to start: reset distance tracking state
            logger.info(f"Distance tracking re-enabled for node {node_id}, resetting state")
            if node_id_str in self._previous_positions:
                self._previous_positions[node_id_str] = {}
            if node_id_str in self._cumulative_distances:
                self._cumulative_distances[node_id_str] = {}
        
        # Update tracking state for next iteration
        self._previous_tracking_state[node_id_str] = tracking_enabled
        
        # Only calculate distances if enabled
        if json_data is not None and tracking_enabled:
            # Extract transformed points and labels
            transformed_points = json_data.get('transformed_points', None)
            class_ids = json_data.get('class_ids', [])
            class_names = json_data.get('class_names', [])
            
            # Initialize node-specific storage if not exists
            if node_id_str not in self._previous_positions:
                self._previous_positions[node_id_str] = {}
            if node_id_str not in self._cumulative_distances:
                self._cumulative_distances[node_id_str] = {}
            
            # Calculate distances for each detected object
            distances_by_label = {}
            cumulative_by_label = {}
            
            if transformed_points is not None and len(transformed_points) > 0:
                for i, current_point in enumerate(transformed_points):
                    # Get label for this point
                    label = None
                    if i < len(class_ids):
                        class_id = class_ids[i]
                        if isinstance(class_names, dict):
                            label = class_names.get(class_id, None)
                        elif isinstance(class_names, list) and class_id < len(class_names):
                            label = class_names[class_id]
                    
                    # Skip objects without valid ReId labels
                    if label is None:
                        continue
                    
                    # Get previous position for this label
                    prev_position = self._previous_positions[node_id_str].get(label, None)
                    
                    # Calculate distance traveled since last frame
                    if prev_position is not None:
                        distance = self._calculate_euclidean_distance(prev_position, current_point)
                        
                        # Update cumulative distance
                        if label not in self._cumulative_distances[node_id_str]:
                            self._cumulative_distances[node_id_str][label] = 0.0
                        self._cumulative_distances[node_id_str][label] += distance
                    else:
                        distance = 0.0
                    
                    # Store current position as previous for next frame
                    self._previous_positions[node_id_str][label] = current_point
                    
                    # Store distances
                    distances_by_label[label] = {
                        'frame_distance': float(distance),
                        'cumulative_distance': float(self._cumulative_distances[node_id_str].get(label, 0.0)),
                        'position': [float(current_point[0]), float(current_point[1])]
                    }
            
            # Prepare output JSON
            output_json = {
                'distances_by_label': distances_by_label,
                'total_players': len(distances_by_label),
                'tracking_enabled': True
            }
            
            # Pass through homography data for downstream nodes
            output_json.update(json_data)
            
            # Display distances using logger
            logger.info("="*70)
            logger.info("[DistanceTracker] Player Distances:")
            logger.info("="*70)
            for label, data in distances_by_label.items():
                logger.info(f"  {label}:")
                logger.info(f"    Position: ({data['position'][0]:.2f}m, {data['position'][1]:.2f}m)")
                logger.info(f"    Frame distance: {data['frame_distance']:.3f}m")
                logger.info(f"    Total distance: {data['cumulative_distance']:.2f}m")
            logger.info("="*70)
        
        elif json_data is not None and not tracking_enabled:
            # Tracking disabled, pass through data without calculating distances
            output_json = copy.deepcopy(json_data)
            output_json['tracking_enabled'] = False

        if use_pref_counter and json_data is not None:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            try:
                dpg_set_value(output_time_value_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception:
                pass  # DPG not initialized (e.g., in tests)

        return {"image": None, "json": output_json, "audio": None}
    
    def close(self, node_id):
        """Clean up stored positions and distances when node is closed."""
        node_id_str = str(node_id)
        if node_id_str in self._previous_positions:
            del self._previous_positions[node_id_str]
        if node_id_str in self._cumulative_distances:
            del self._cumulative_distances[node_id_str]

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        try:
            pos = dpg.get_item_pos(tag_node_name)
        except Exception:
            pos = [0, 0]  # Default position if DPG not initialized

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
