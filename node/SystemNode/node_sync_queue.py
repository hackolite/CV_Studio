#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Queue Synchronization Node

This node synchronizes data from multiple queues. Each "Add Slot" creates
an input entry and a corresponding output entry. The node retrieves elements
from the connected queues and synchronizes them based on timestamps.

The node does NOT display frames visually. It retrieves data from queues,
buffers it with a configurable retention time, synchronizes based on timestamps,
and passes the synchronized data to outputs.
"""
import copy
import time

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

        # Initialize slot tracking for this node instance
        if node.tag_node_name not in node._slot_id:
            node._slot_id[node.tag_node_name] = 0
        
        # Initialize sync state for this node
        if node.tag_node_name not in node._sync_state:
            node._sync_state[node.tag_node_name] = {
                'retention_time': 0.0,  # Retention time in seconds before sync
                'slot_buffers': {},  # Buffers for each slot
            }

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Add Slot button and settings (static attribute)
            with dpg.node_attribute(
                    tag=node.tag_node_input00_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("Retention Time (s):")
                dpg.add_input_float(
                    tag=node.tag_node_name + ':RetentionTime',
                    default_value=0.0,
                    min_value=0.0,
                    max_value=10.0,
                    width=150,
                    step=0.1,
                    callback=node._update_retention_time,
                    user_data=node.tag_node_name,
                )
                dpg.add_button(
                    label='Add Slot',
                    width=150,
                    callback=node._add_slot,
                    user_data=node.tag_node_name,
                )
                dpg.add_text(
                    tag=node.tag_node_name + ':Status',
                    default_value='Slots: 0 | Synced: 0',
                )

        return node


class Node(Node):
    _ver = '0.0.2'

    node_label = 'SyncQueue'
    node_tag = 'SyncQueue'

    _opencv_setting_dict = None
    _max_slot_number = 10
    _slot_id = {}  # Track number of slots per node instance
    _sync_state = {}  # Track synchronization state per node instance

    def __init__(self):
        pass

    def _update_retention_time(self, sender, data, user_data):
        """Update the retention time for data buffering."""
        tag_node_name = user_data
        retention_time = dpg_get_value(sender)
        if tag_node_name in self._sync_state:
            self._sync_state[tag_node_name]['retention_time'] = retention_time

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
        
        This method:
        1. Retrieves data from queues connected to input slots
        2. Buffers data with timestamps (respecting retention time)
        3. Synchronizes data across slots based on timestamps
        4. Outputs synchronized data to respective output slots
        
        No visual display is performed.
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Get current number of slots
        slot_num = self._slot_id.get(tag_node_name, 0)
        
        # Get sync state
        sync_state = self._sync_state.get(tag_node_name, {})
        retention_time = sync_state.get('retention_time', 0.0)
        
        # Initialize slot buffers if not exists
        if 'slot_buffers' not in sync_state:
            sync_state['slot_buffers'] = {}
            self._sync_state[tag_node_name] = sync_state
        
        slot_buffers = sync_state['slot_buffers']
        
        # Process connections and organize by slot
        slot_connections = {}
        for connection_info in connection_list:
            # Extract slot number from destination tag
            # Format: node_id:NodeTag:TYPE:InputXX or OutputXX
            parts = connection_info[1].split(':')
            if len(parts) >= 4:
                slot_str = parts[-1]  # InputXX or OutputXX
                # Extract number from Input01, Input02, etc.
                digits = ''.join(filter(str.isdigit, slot_str))
                if not digits:
                    continue  # Skip if no digits found
                try:
                    slot_number = int(digits)
                except ValueError:
                    continue  # Skip malformed slot numbers
                
                connection_type = parts[2]  # IMAGE, JSON, AUDIO, etc.
                
                # Get source node info
                source_parts = connection_info[0].split(':')
                source_node_id_name = ':'.join(source_parts[:2])
                
                if slot_number not in slot_connections:
                    slot_connections[slot_number] = {}
                
                slot_connections[slot_number][connection_type] = source_node_id_name
        
        # Retrieve data from queues for each slot
        current_time = time.time()
        
        for slot_idx in range(1, slot_num + 1):
            if slot_idx not in slot_buffers:
                slot_buffers[slot_idx] = {
                    'image': [],
                    'json': [],
                    'audio': []
                }
            
            if slot_idx in slot_connections:
                connections = slot_connections[slot_idx]
                
                # Get data from connected sources and their queues
                for data_type, source_node in connections.items():
                    data_dict = None
                    buffer_key = None
                    
                    if data_type == 'IMAGE':
                        data_dict = node_image_dict
                        buffer_key = 'image'
                    elif data_type == 'JSON':
                        data_dict = node_result_dict
                        buffer_key = 'json'
                    elif data_type == 'AUDIO':
                        data_dict = node_audio_dict
                        buffer_key = 'audio'
                    
                    if data_dict is not None and buffer_key is not None:
                        # Get queue info to access all buffered items with timestamps
                        queue_info = data_dict.get_queue_info(source_node)
                        
                        if queue_info.get('exists') and not queue_info.get('is_empty'):
                            # Access the queue manager directly to get all timestamped items
                            queue_manager = data_dict._queue_manager
                            queue = queue_manager.get_queue(source_node, buffer_key)
                            all_items = queue.get_all()
                            
                            # Add new items to slot buffer
                            for timestamped_data in all_items:
                                # Check if this item is already in our buffer
                                already_exists = any(
                                    item['timestamp'] == timestamped_data.timestamp
                                    for item in slot_buffers[slot_idx][buffer_key]
                                )
                                
                                if not already_exists:
                                    slot_buffers[slot_idx][buffer_key].append({
                                        'data': copy.deepcopy(timestamped_data.data),
                                        'timestamp': timestamped_data.timestamp,
                                        'received_at': current_time
                                    })
        
        # Clean up old data from buffers
        # Keep items for a reasonable window (retention_time + 1 second buffer)
        max_buffer_age = max(retention_time + 1.0, 2.0)
        for slot_idx in slot_buffers:
            for data_type in ['image', 'json', 'audio']:
                slot_buffers[slot_idx][data_type] = [
                    item for item in slot_buffers[slot_idx][data_type]
                    if (current_time - item['received_at']) <= max_buffer_age
                ]
        
        # Synchronize data based on timestamps
        synced_count = 0
        output_data = {
            'image': {},
            'json': {},
            'audio': {}
        }
        
        # For each slot, find data that has been retained long enough
        for slot_idx in range(1, slot_num + 1):
            if slot_idx in slot_buffers:
                for data_type in ['image', 'json', 'audio']:
                    if slot_buffers[slot_idx][data_type]:
                        # Get items that have been retained long enough
                        valid_items = [
                            item for item in slot_buffers[slot_idx][data_type]
                            if (current_time - item['received_at']) >= retention_time
                        ]
                        
                        if valid_items:
                            # Sort by timestamp and get most recent
                            valid_items.sort(key=lambda x: x['timestamp'], reverse=True)
                            synced_item = valid_items[0]
                            synced_data = synced_item['data']
                            synced_timestamp = synced_item['timestamp']
                            
                            # Preserve timestamp in output data for downstream synchronization
                            # Wrap audio data with timestamp information for VideoWriter
                            if data_type == 'audio' and isinstance(synced_data, dict):
                                # Audio data is already a dict (from video node), preserve/update timestamp
                                if 'timestamp' not in synced_data or synced_data['timestamp'] != synced_timestamp:
                                    synced_data = synced_data.copy()
                                    synced_data['timestamp'] = synced_timestamp
                            elif data_type == 'audio':
                                # Audio data is raw numpy array, wrap with timestamp
                                synced_data = {
                                    'data': synced_data,
                                    'timestamp': synced_timestamp
                                }
                            
                            output_data[data_type][slot_idx] = synced_data
                            synced_count += 1
        
        # Update output text values for each slot (no visual display)
        for slot_idx in range(1, slot_num + 1):
            # Update image output text if exists (no visual display)
            image_output_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output{slot_idx:02d}Value"
            if dpg.does_item_exist(image_output_tag):
                if slot_idx in output_data['image']:
                    dpg_set_value(image_output_tag, f'Image data synced')
                else:
                    dpg_set_value(image_output_tag, f'No image data')
            
            # Update JSON output text if exists
            json_output_tag = f"{tag_node_name}:{self.TYPE_JSON}:Output{slot_idx:02d}Value"
            if dpg.does_item_exist(json_output_tag):
                if slot_idx in output_data['json']:
                    json_data = output_data['json'][slot_idx]
                    dpg_set_value(json_output_tag, f'JSON: {str(json_data)[:30]}...')
                else:
                    dpg_set_value(json_output_tag, 'No JSON data')
            
            # Update audio output text if exists
            audio_output_tag = f"{tag_node_name}:{self.TYPE_AUDIO}:Output{slot_idx:02d}Value"
            if dpg.does_item_exist(audio_output_tag):
                if slot_idx in output_data['audio']:
                    dpg_set_value(audio_output_tag, f'Audio data synced')
                else:
                    dpg_set_value(audio_output_tag, 'No audio data')
        
        # Update status text
        status_tag = tag_node_name + ':Status'
        if dpg.does_item_exist(status_tag):
            dpg_set_value(status_tag, f'Slots: {slot_num} | Synced: {synced_count}')
        
        # Return aggregated data for each slot
        result = {}
        for slot_idx in range(1, slot_num + 1):
            result[f'slot_{slot_idx}'] = {
                'image': output_data['image'].get(slot_idx),
                'json': output_data['json'].get(slot_idx),
                'audio': output_data['audio'].get(slot_idx),
            }
        
        # Also return first slot for backward compatibility
        result['image'] = output_data['image'].get(1)
        result['json'] = output_data['json'].get(1)
        result['audio'] = output_data['audio'].get(1)
        
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
        
        # Save retention time
        retention_tag = tag_node_name + ':RetentionTime'
        if dpg.does_item_exist(retention_tag):
            setting_dict['retention_time'] = dpg_get_value(retention_tag)
        else:
            setting_dict['retention_time'] = 0.0

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Restore node configuration."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Safely get slot_id with validation
        slot_id_value = setting_dict.get('slot_id', 0)
        try:
            slot_number = int(slot_id_value)
        except (ValueError, TypeError):
            slot_number = 0  # Default to 0 if conversion fails
        
        # Restore retention time
        retention_time = setting_dict.get('retention_time', 0.0)
        retention_tag = tag_node_name + ':RetentionTime'
        if dpg.does_item_exist(retention_tag):
            dpg_set_value(retention_tag, retention_time)
        
        # Update sync state
        if tag_node_name in self._sync_state:
            self._sync_state[tag_node_name]['retention_time'] = retention_time
        
        # Recreate slots
        for _ in range(slot_number):
            self._add_slot(None, None, tag_node_name)

    def _add_slot(self, sender, data, user_data):
        """
        Add a new input/output slot pair.
        
        Each slot consists of:
        - One input attribute (can connect to IMAGE, JSON, or AUDIO)
        - One output attribute of each type (IMAGE, JSON, AUDIO) with text display only
        
        No visual frame display is performed.
        """
        tag_node_name = user_data
        
        # Ensure tag_node_name is initialized in _slot_id
        if tag_node_name not in self._slot_id:
            self._slot_id[tag_node_name] = 0
        
        if self._max_slot_number > self._slot_id[tag_node_name]:
            self._slot_id[tag_node_name] += 1
            slot_idx = self._slot_id[tag_node_name]
            
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
            
            # Create corresponding output slots (TEXT ONLY - NO VISUAL DISPLAY)
            # IMAGE Output (text only)
            output_image_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output{slot_idx:02d}"
            output_image_value_tag = f"{output_image_tag}Value"
            with dpg.node_attribute(
                    tag=output_image_tag,
                    attribute_type=dpg.mvNode_Attr_Output,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=output_image_value_tag,
                    default_value=f'Out{slot_idx}: Image',
                )
            
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
