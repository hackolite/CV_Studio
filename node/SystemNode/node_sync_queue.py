#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Queue Synchronization Node

This node synchronizes data from multiple queues. Each "Add Slot" creates
an input entry and a corresponding output entry with a selectable input type
(Image, Audio, or JSON - only one type per slot).

The node does NOT display frames visually. It retrieves data from queues,
buffers it with a configurable retention time (default: 3 seconds), 
synchronizes based on timestamps, and passes the synchronized data to outputs.

The node displays the number of available elements for synchronization.
"""
import copy
import time

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node

# Default retention time in seconds
DEFAULT_RETENTION_TIME = 3.0


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
        
        # Initialize slot types tracking
        if node.tag_node_name not in node._slot_types:
            node._slot_types[node.tag_node_name] = {}  # {slot_idx: 'image'|'audio'|'json'}
        
        # Initialize sync state for this node
        if node.tag_node_name not in node._sync_state:
            node._sync_state[node.tag_node_name] = {
                'retention_time': DEFAULT_RETENTION_TIME,  # Default 3 seconds retention time
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
                    default_value=DEFAULT_RETENTION_TIME,
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
                # Display available elements count for synchronization
                dpg.add_text(
                    tag=node.tag_node_name + ':ElementsCount',
                    default_value='Available: 0',
                )

        return node


class Node(Node):
    _ver = '0.0.3'

    node_label = 'SyncQueue'
    node_tag = 'SyncQueue'

    _opencv_setting_dict = None
    _max_slot_number = 10
    _slot_id = {}  # Track number of slots per node instance
    _slot_types = {}  # Track input type per slot {node_tag: {slot_idx: 'image'|'audio'|'json'}}
    _sync_state = {}  # Track synchronization state per node instance

    def __init__(self):
        pass

    def _update_retention_time(self, sender, data, user_data):
        """Update the retention time for data buffering."""
        tag_node_name = user_data
        retention_time = dpg_get_value(sender)
        if tag_node_name in self._sync_state:
            self._sync_state[tag_node_name]['retention_time'] = retention_time

    def _update_slot_type(self, sender, data, user_data):
        """Update the input type for a slot."""
        tag_node_name, slot_idx = user_data
        selected_type = dpg_get_value(sender)
        
        # Map combo selection to internal type
        type_map = {
            'Image': 'image',
            'Audio': 'audio',
            'JSON': 'json'
        }
        
        if tag_node_name in self._slot_types:
            self._slot_types[tag_node_name][slot_idx] = type_map.get(selected_type, 'image')

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
        5. Updates the available elements count display
        
        No visual display is performed.
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Get current number of slots
        slot_num = self._slot_id.get(tag_node_name, 0)
        
        # Get sync state
        sync_state = self._sync_state.get(tag_node_name, {})
        retention_time = sync_state.get('retention_time', DEFAULT_RETENTION_TIME)
        
        # Initialize slot buffers if not exists
        if 'slot_buffers' not in sync_state:
            sync_state['slot_buffers'] = {}
            self._sync_state[tag_node_name] = sync_state
        
        slot_buffers = sync_state['slot_buffers']
        
        # Get slot types
        slot_types = self._slot_types.get(tag_node_name, {})
        
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
        total_available_elements = 0
        
        for slot_idx in range(1, slot_num + 1):
            # Get the slot's configured type (use 'or' to handle None values)
            slot_type = slot_types.get(slot_idx) or 'image'
            
            if slot_idx not in slot_buffers:
                slot_buffers[slot_idx] = {
                    'data': []  # Single buffer for the slot's configured type
                }
            
            if slot_idx in slot_connections:
                connections = slot_connections[slot_idx]
                
                # Determine which data dict to use based on slot type
                data_dict = None
                connection_type_key = None
                
                if slot_type == 'image':
                    data_dict = node_image_dict
                    connection_type_key = 'IMAGE'
                elif slot_type == 'json':
                    data_dict = node_result_dict
                    connection_type_key = 'JSON'
                elif slot_type == 'audio':
                    data_dict = node_audio_dict
                    connection_type_key = 'AUDIO'
                
                if data_dict is not None and connection_type_key in connections:
                    source_node = connections[connection_type_key]
                    
                    # Get queue info to access all buffered items with timestamps
                    queue_info = data_dict.get_queue_info(source_node)
                    
                    if queue_info.get('exists') and not queue_info.get('is_empty'):
                        # Access the queue manager directly to get all timestamped items
                        queue_manager = data_dict._queue_manager
                        queue = queue_manager.get_queue(source_node, slot_type)
                        all_items = queue.get_all()
                        
                        # Add new items to slot buffer
                        for timestamped_data in all_items:
                            # Check if this item is already in our buffer
                            already_exists = any(
                                item['timestamp'] == timestamped_data.timestamp
                                for item in slot_buffers[slot_idx]['data']
                            )
                            
                            if not already_exists:
                                slot_buffers[slot_idx]['data'].append({
                                    'data': copy.deepcopy(timestamped_data.data),
                                    'timestamp': timestamped_data.timestamp,
                                    'received_at': current_time
                                })
            
            # Count available elements in this slot's buffer
            total_available_elements += len(slot_buffers[slot_idx].get('data', []))
        
        # Clean up old data from buffers
        # Keep items for a reasonable window (retention_time + 1 second buffer)
        max_buffer_age = max(retention_time + 1.0, 2.0)
        for slot_idx in slot_buffers:
            slot_buffers[slot_idx]['data'] = [
                item for item in slot_buffers[slot_idx].get('data', [])
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
            slot_type = slot_types.get(slot_idx) or 'image'
            
            if slot_idx in slot_buffers:
                buffer_data = slot_buffers[slot_idx].get('data', [])
                
                if buffer_data:
                    # Get items that have been retained long enough
                    valid_items = [
                        item for item in buffer_data
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
                        if slot_type == 'audio' and isinstance(synced_data, dict):
                            # Audio data is already a dict (from video node), preserve/update timestamp
                            if 'timestamp' not in synced_data or synced_data['timestamp'] != synced_timestamp:
                                synced_data = synced_data.copy()
                                synced_data['timestamp'] = synced_timestamp
                        elif slot_type == 'audio':
                            # Audio data is raw numpy array, wrap with timestamp
                            synced_data = {
                                'data': synced_data,
                                'timestamp': synced_timestamp
                            }
                        
                        output_data[slot_type][slot_idx] = synced_data
                        synced_count += 1
        
        # Update output text values for each slot
        for slot_idx in range(1, slot_num + 1):
            slot_type = slot_types.get(slot_idx) or 'image'
            
            # Update output text based on slot type
            output_tag = f"{tag_node_name}:{self._get_type_constant(slot_type)}:Output{slot_idx:02d}Value"
            if dpg.does_item_exist(output_tag):
                if slot_idx in output_data[slot_type]:
                    buffer_count = len(slot_buffers.get(slot_idx, {}).get('data', []))
                    dpg_set_value(output_tag, f'Out{slot_idx}: {slot_type.capitalize()} ({buffer_count})')
                else:
                    dpg_set_value(output_tag, f'Out{slot_idx}: No data')
        
        # Update status text
        status_tag = tag_node_name + ':Status'
        if dpg.does_item_exist(status_tag):
            dpg_set_value(status_tag, f'Slots: {slot_num} | Synced: {synced_count}')
        
        # Update available elements count display
        elements_tag = tag_node_name + ':ElementsCount'
        if dpg.does_item_exist(elements_tag):
            dpg_set_value(elements_tag, f'Available: {total_available_elements}')
        
        # Return aggregated data for each slot
        result = {}
        for slot_idx in range(1, slot_num + 1):
            slot_type = slot_types.get(slot_idx) or 'image'
            result[f'slot_{slot_idx}'] = {
                'image': output_data['image'].get(slot_idx) if slot_type == 'image' else None,
                'json': output_data['json'].get(slot_idx) if slot_type == 'json' else None,
                'audio': output_data['audio'].get(slot_idx) if slot_type == 'audio' else None,
            }
        
        # Also return first slot for backward compatibility
        first_slot_type = slot_types.get(1) or 'image'
        result['image'] = output_data['image'].get(1) if first_slot_type == 'image' else None
        result['json'] = output_data['json'].get(1) if first_slot_type == 'json' else None
        result['audio'] = output_data['audio'].get(1) if first_slot_type == 'audio' else None
        
        return result

    def _get_type_constant(self, slot_type):
        """Map slot type string to node TYPE constant."""
        type_map = {
            'image': self.TYPE_IMAGE,
            'audio': self.TYPE_AUDIO,
            'json': self.TYPE_JSON
        }
        return type_map.get(slot_type, self.TYPE_IMAGE)

    def close(self, node_id):
        """Clean up node resources."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        if tag_node_name in self._slot_id:
            del self._slot_id[tag_node_name]
        if tag_node_name in self._slot_types:
            del self._slot_types[tag_node_name]
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
            setting_dict['retention_time'] = DEFAULT_RETENTION_TIME
        
        # Save slot types
        setting_dict['slot_types'] = self._slot_types.get(tag_node_name, {})

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
        retention_time = setting_dict.get('retention_time', DEFAULT_RETENTION_TIME)
        retention_tag = tag_node_name + ':RetentionTime'
        if dpg.does_item_exist(retention_tag):
            dpg_set_value(retention_tag, retention_time)
        
        # Update sync state
        if tag_node_name in self._sync_state:
            self._sync_state[tag_node_name]['retention_time'] = retention_time
        
        # Restore slot types
        saved_slot_types = setting_dict.get('slot_types', {})
        if tag_node_name not in self._slot_types:
            self._slot_types[tag_node_name] = {}
        
        # Recreate slots with their saved types
        for i in range(slot_number):
            slot_idx = i + 1
            slot_type = saved_slot_types.get(slot_idx, saved_slot_types.get(str(slot_idx), 'image'))
            self._add_slot(None, None, tag_node_name, initial_type=slot_type)

    def _add_slot(self, sender, data, user_data, initial_type='image'):
        """
        Add a new input/output slot pair with selectable input type.
        
        Each slot consists of:
        - A type selector combo (Image, Audio, JSON)
        - One input attribute for the selected type
        - One output attribute for the selected type
        
        Only one input type per slot (not all 3 types).
        """
        tag_node_name = user_data
        
        # Ensure tag_node_name is initialized in _slot_id
        if tag_node_name not in self._slot_id:
            self._slot_id[tag_node_name] = 0
        
        # Ensure tag_node_name is initialized in _slot_types
        if tag_node_name not in self._slot_types:
            self._slot_types[tag_node_name] = {}
        
        if self._max_slot_number > self._slot_id[tag_node_name]:
            self._slot_id[tag_node_name] += 1
            slot_idx = self._slot_id[tag_node_name]
            
            # Store the initial slot type (ensure it's never None)
            self._slot_types[tag_node_name][slot_idx] = initial_type or 'image'
            
            # Determine where to insert (before the Add Slot button)
            before_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input00'
            
            # Map initial type to combo display value
            type_display_map = {
                'image': 'Image',
                'audio': 'Audio',
                'json': 'JSON'
            }
            initial_display = type_display_map.get(initial_type, 'Image')
            
            # Get the type constant for input/output tags
            type_constant = self._get_type_constant(initial_type)
            
            # Create type selector combo
            type_selector_tag = f"{tag_node_name}:TypeSelector{slot_idx:02d}"
            with dpg.node_attribute(
                    tag=f"{tag_node_name}:TypeSelectorAttr{slot_idx:02d}",
                    attribute_type=dpg.mvNode_Attr_Static,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_combo(
                    tag=type_selector_tag,
                    items=['Image', 'Audio', 'JSON'],
                    default_value=initial_display,
                    width=100,
                    label=f'Slot{slot_idx}',
                    callback=self._update_slot_type,
                    user_data=(tag_node_name, slot_idx),
                )
            
            # Create input slot for the selected type
            input_tag = f"{tag_node_name}:{type_constant}:Input{slot_idx:02d}"
            input_value_tag = f"{input_tag}Value"
            with dpg.node_attribute(
                    tag=input_tag,
                    attribute_type=dpg.mvNode_Attr_Input,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=input_value_tag,
                    default_value=f'In{slot_idx}: {initial_display}',
                )
            
            # Create corresponding output slot
            output_tag = f"{tag_node_name}:{type_constant}:Output{slot_idx:02d}"
            output_value_tag = f"{output_tag}Value"
            with dpg.node_attribute(
                    tag=output_tag,
                    attribute_type=dpg.mvNode_Attr_Output,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=output_value_tag,
                    default_value=f'Out{slot_idx}: {initial_display} (0)',
                )
