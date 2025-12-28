#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import copy
from collections import deque
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


class FactoryNode:
    node_label = 'Trigger/KeypointDeviation'
    node_tag = 'TriggerKeypointDeviation'

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
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        
        node.tag_node_output_bool_name = node.tag_node_name + ':' + node.TYPE_BOOLEAN + ':Output01'
        node.tag_node_output_bool_value_name = node.tag_node_name + ':' + node.TYPE_BOOLEAN + ':Output01Value'
        
        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Output02'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Output02Value'
        
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'
        
        node.tag_node_input_window_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02'
        node.tag_node_input_window_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02Value'
        
        node.tag_node_input_threshold_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input_threshold_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        
        node.tag_node_output_time_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output04'
        node.tag_node_output_time_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output04Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Input: Keypoints JSON
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Keypoints JSON Input',
                )

            # Parameter: Window size (seconds)
            with dpg.node_attribute(
                tag=node.tag_node_input_window_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input_window_value_name,
                    label="Window (sec)",
                    width=small_window_w - 80,
                    default_value=2.0,
                    min_value=0.5,
                    max_value=10.0,
                    callback=None,
                )

            # Parameter: Threshold distance
            with dpg.node_attribute(
                tag=node.tag_node_input_threshold_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input_threshold_value_name,
                    label="Threshold",
                    width=small_window_w - 80,
                    default_value=100.0,
                    min_value=10.0,
                    max_value=500.0,
                    callback=None,
                )

            # Output: Trigger boolean
            with dpg.node_attribute(
                tag=node.tag_node_output_bool_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_bool_value_name,
                    default_value='Trigger: False',
                )

            # Output: Distance value
            with dpg.node_attribute(
                tag=node.tag_node_output_float_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_float_value_name,
                    default_value='Distance: 0.0',
                )

            # Output: Pass-through JSON
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='Keypoints JSON Output',
                )

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

    node_label = 'Trigger/KeypointDeviation'
    node_tag = 'TriggerKeypointDeviation'

    _opencv_setting_dict = None
    _keypoints_history = {}  # Store history per node instance

    def __init__(self):
        self._keypoints_buffer = deque()  # Buffer with timestamps
        self._last_trigger_state = False

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_bool_tag = tag_node_name + ':' + self.TYPE_BOOLEAN + ':Output01Value'
        output_float_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Output02Value'
        output_time_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output04Value'
        input_window_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get parameters
        window_seconds = dpg_get_value(input_window_tag)
        threshold_distance = dpg_get_value(input_threshold_tag)

        # Find JSON connection
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)

        # Get JSON data
        json_data = node_result_dict.get(connection_info_src, None)

        if json_data is not None and use_pref_counter:
            start_time = time.monotonic()

        # Process keypoints and check for deviation
        trigger_state = False
        distance = 0.0
        output_json = None

        if json_data is not None and isinstance(json_data, dict):
            output_json = copy.deepcopy(json_data)
            
            # Extract keypoints from results_list
            if 'results_list' in json_data:
                results_list = json_data['results_list']
                current_time = time.time()
                
                # Convert keypoints to flat array
                if isinstance(results_list, np.ndarray):
                    keypoints_flat = results_list.flatten()
                    
                    # Add current keypoints to buffer with timestamp
                    self._keypoints_buffer.append((current_time, keypoints_flat))
                    
                    # Remove old entries outside the window
                    cutoff_time = current_time - window_seconds
                    while self._keypoints_buffer and self._keypoints_buffer[0][0] < cutoff_time:
                        self._keypoints_buffer.popleft()
                    
                    # Calculate average if we have enough history
                    if len(self._keypoints_buffer) >= 2:
                        # Calculate mean keypoints over the window
                        keypoints_arrays = [kp for _, kp in self._keypoints_buffer]
                        mean_keypoints = np.mean(keypoints_arrays, axis=0)
                        
                        # Calculate distance between current and mean
                        # Using Euclidean distance of the flattened keypoints
                        distance = np.sqrt(np.sum((keypoints_flat - mean_keypoints) ** 2))
                        
                        # Check if distance exceeds threshold
                        if distance > threshold_distance:
                            trigger_state = True
                    
                    # Add trigger information to output JSON
                    output_json['trigger_info'] = {
                        'triggered': trigger_state,
                        'distance': float(distance),
                        'threshold': float(threshold_distance),
                        'window_seconds': float(window_seconds),
                        'buffer_size': len(self._keypoints_buffer)
                    }

        # Update UI outputs
        dpg_set_value(output_bool_tag, f'Trigger: {trigger_state}')
        dpg_set_value(output_float_tag, f'Distance: {distance:.2f}')

        if json_data is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_time_tag, str(elapsed_time).zfill(4) + 'ms')

        self._last_trigger_state = trigger_state

        return {"image": None, "json": output_json, "audio": None}

    def close(self, node_id):
        # Clear buffer on close
        self._keypoints_buffer.clear()

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_window_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        
        window_seconds = dpg_get_value(input_window_tag)
        threshold_distance = dpg_get_value(input_threshold_tag)
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_window_tag] = window_seconds
        setting_dict[input_threshold_tag] = threshold_distance

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_window_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        
        if input_window_tag in setting_dict:
            dpg_set_value(input_window_tag, setting_dict[input_window_tag])
        if input_threshold_tag in setting_dict:
            dpg_set_value(input_threshold_tag, setting_dict[input_threshold_tag])
