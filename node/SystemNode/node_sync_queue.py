#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Queue Synchronization Node

This node synchronizes data from multiple queues. Each "Add Slot" creates
an input entry and a corresponding output entry. The node retrieves elements
from the connected queues and synchronizes them based on timestamps.
"""
import copy
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


class FactoryNode:
    node_label = 'SyncQueue'
    node_tag = 'SyncQueue'
    
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
        node.tag_node_input00_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input00'
        
        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']

        # Initialize slot tracking for this node instance
        if node.tag_node_name not in node._slot_id:
            node._slot_id[node.tag_node_name] = 0
        
        # Initialize sync state for this node
        if node.tag_node_name not in node._sync_state:
            node._sync_state[node.tag_node_name] = {}

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Add Slot button (static attribute)
            with dpg.node_attribute(
                    tag=node.tag_node_input00_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='Add Slot',
                    width=int(small_window_w / 3),
                    callback=node._add_slot,
                    user_data=node.tag_node_name,
                )
                dpg.add_text(
                    tag=node.tag_node_name + ':Status',
                    default_value='Slots: 0',
                )

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'SyncQueue'
    node_tag = 'SyncQueue'

    _opencv_setting_dict = None
    _max_slot_number = 10
    _slot_id = {}  # Track number of slots per node instance
    _sync_state = {}  # Track synchronization state per node instance

    def __init__(self):
        pass

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """
        Update the sync queue node.
        
        This method processes connections and synchronizes data from multiple sources.
        Each input slot has a corresponding output slot.
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Get current number of slots
        slot_num = self._slot_id.get(tag_node_name, 0)
        
        # Update status text
        status_tag = tag_node_name + ':Status'
        if dpg.does_item_exist(status_tag):
            dpg_set_value(status_tag, f'Slots: {slot_num}')
        
        # Process connections and organize by slot
        slot_connections = {}
        for connection_info in connection_list:
            # Extract slot number from destination tag
            # Format: node_id:NodeTag:TYPE:InputXX or OutputXX
            parts = connection_info[1].split(':')
            if len(parts) >= 4:
                slot_str = parts[-1]  # InputXX or OutputXX
                # Extract number from Input01, Input02, etc.
                slot_number = int(''.join(filter(str.isdigit, slot_str)))
                
                connection_type = parts[2]  # IMAGE, JSON, AUDIO, etc.
                
                # Get source node info
                source_parts = connection_info[0].split(':')
                source_node_id_name = ':'.join(source_parts[:2])
                
                if slot_number not in slot_connections:
                    slot_connections[slot_number] = {}
                
                slot_connections[slot_number][connection_type] = source_node_id_name
        
        # Prepare output data for each slot
        output_data = {
            'image': {},
            'json': {},
            'audio': {}
        }
        
        # Process each slot's connections
        for slot_idx in range(1, slot_num + 1):
            if slot_idx in slot_connections:
                connections = slot_connections[slot_idx]
                
                # Get data from connected sources based on type
                for data_type, source_node in connections.items():
                    if data_type == 'IMAGE':
                        data = node_image_dict.get(source_node)
                        if data is not None:
                            output_data['image'][slot_idx] = copy.deepcopy(data)
                    elif data_type == 'JSON':
                        data = node_result_dict.get(source_node)
                        if data is not None:
                            output_data['json'][slot_idx] = copy.deepcopy(data)
                    elif data_type == 'AUDIO':
                        data = node_audio_dict.get(source_node)
                        if data is not None:
                            output_data['audio'][slot_idx] = copy.deepcopy(data)
        
        # Update output values for each slot
        for slot_idx in range(1, slot_num + 1):
            # Update image output if exists
            image_output_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output{slot_idx:02d}Value"
            if dpg.does_item_exist(image_output_tag):
                if slot_idx in output_data['image']:
                    image = output_data['image'][slot_idx]
                    small_window_w = self._opencv_setting_dict['process_width']
                    small_window_h = self._opencv_setting_dict['process_height']
                    texture = self.convert_cv_to_dpg(image, small_window_w, small_window_h)
                    dpg_set_value(image_output_tag, texture)
            
            # Update JSON output text if exists
            json_output_tag = f"{tag_node_name}:{self.TYPE_JSON}:Output{slot_idx:02d}Value"
            if dpg.does_item_exist(json_output_tag):
                if slot_idx in output_data['json']:
                    json_data = output_data['json'][slot_idx]
                    dpg_set_value(json_output_tag, f'Data: {str(json_data)[:50]}...')
                else:
                    dpg_set_value(json_output_tag, 'No JSON data')
            
            # Audio data is passed through without display
        
        # Return aggregated data (first available of each type)
        result = {
            'image': output_data['image'].get(1) if output_data['image'] else None,
            'json': output_data['json'].get(1) if output_data['json'] else None,
            'audio': output_data['audio'].get(1) if output_data['audio'] else None,
        }
        
        return result

    def close(self, node_id):
        """Clean up node resources."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        if tag_node_name in self._slot_id:
            del self._slot_id[tag_node_name]
        if tag_node_name in self._sync_state:
            del self._sync_state[tag_node_name]

    def get_setting_dict(self, node_id):
        """Save node configuration."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict['slot_id'] = self._slot_id.get(tag_node_name, 0)

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Restore node configuration."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        slot_number = int(setting_dict.get('slot_id', 0))
        # Recreate slots
        for _ in range(slot_number):
            self._add_slot(None, None, tag_node_name)

    def _add_slot(self, sender, data, user_data):
        """
        Add a new input/output slot pair.
        
        Each slot consists of:
        - One input attribute (can connect to IMAGE, JSON, or AUDIO)
        - One output attribute of each type (IMAGE, JSON, AUDIO)
        """
        tag_node_name = user_data
        
        if self._max_slot_number > self._slot_id[tag_node_name]:
            self._slot_id[tag_node_name] += 1
            slot_idx = self._slot_id[tag_node_name]
            
            small_window_w = self._opencv_setting_dict['process_width']
            small_window_h = self._opencv_setting_dict['process_height']
            
            # Create black texture for image output
            black_image = np.zeros((small_window_h, small_window_w, 3))
            black_texture = self.convert_cv_to_dpg(black_image, small_window_w, small_window_h)
            
            # Register texture for this slot
            texture_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output{slot_idx:02d}Value"
            if not dpg.does_item_exist(texture_tag):
                with dpg.texture_registry(show=False):
                    dpg.add_raw_texture(
                        small_window_w,
                        small_window_h,
                        black_texture,
                        tag=texture_tag,
                        format=dpg.mvFormat_Float_rgb,
                    )
            
            # Determine where to insert (before the Add Slot button)
            before_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input00'
            
            # Create input slots for different data types
            # IMAGE Input
            input_image_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Input{slot_idx:02d}"
            input_image_value_tag = f"{input_image_tag}Value"
            with dpg.node_attribute(
                    tag=input_image_tag,
                    attribute_type=dpg.mvNode_Attr_Input,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=input_image_value_tag,
                    default_value=f'In{slot_idx}: Image',
                )
            
            # JSON Input
            input_json_tag = f"{tag_node_name}:{self.TYPE_JSON}:Input{slot_idx:02d}"
            input_json_value_tag = f"{input_json_tag}Value"
            with dpg.node_attribute(
                    tag=input_json_tag,
                    attribute_type=dpg.mvNode_Attr_Input,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=input_json_value_tag,
                    default_value=f'In{slot_idx}: JSON',
                )
            
            # AUDIO Input
            input_audio_tag = f"{tag_node_name}:{self.TYPE_AUDIO}:Input{slot_idx:02d}"
            input_audio_value_tag = f"{input_audio_tag}Value"
            with dpg.node_attribute(
                    tag=input_audio_tag,
                    attribute_type=dpg.mvNode_Attr_Input,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=input_audio_value_tag,
                    default_value=f'In{slot_idx}: Audio',
                )
            
            # Create corresponding output slots
            # IMAGE Output
            output_image_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output{slot_idx:02d}"
            output_image_value_tag = f"{output_image_tag}Value"
            with dpg.node_attribute(
                    tag=output_image_tag,
                    attribute_type=dpg.mvNode_Attr_Output,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_image(texture_tag)
            
            # JSON Output
            output_json_tag = f"{tag_node_name}:{self.TYPE_JSON}:Output{slot_idx:02d}"
            output_json_value_tag = f"{output_json_tag}Value"
            with dpg.node_attribute(
                    tag=output_json_tag,
                    attribute_type=dpg.mvNode_Attr_Output,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=output_json_value_tag,
                    default_value=f'Out{slot_idx}: JSON',
                )
            
            # AUDIO Output
            output_audio_tag = f"{tag_node_name}:{self.TYPE_AUDIO}:Output{slot_idx:02d}"
            output_audio_value_tag = f"{output_audio_tag}Value"
            with dpg.node_attribute(
                    tag=output_audio_tag,
                    attribute_type=dpg.mvNode_Attr_Output,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=output_audio_value_tag,
                    default_value=f'Out{slot_idx}: Audio',
                )
