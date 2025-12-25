#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
from collections import deque

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


class FactoryNode:
    node_label = 'SimpleRouter'
    node_tag = 'SimpleRouter'
    
    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=None,
        opencv_setting_dict=None,
        callback=None,
    ):
        """Creates and adds a SimpleRouter node to the processing graph."""
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(BaseNode):
    _ver = '0.0.1'

    node_label = 'SimpleRouter'
    node_tag = 'SimpleRouter'

    _opencv_setting_dict = None
    
    # Blinking effect constants (same as trigger nodes)
    WHITE_COLOR = (255, 255, 255, 255)  # Bright white for blinking
    TEXT_COLOR_BLACK = (0, 0, 0, 255)  # Black text for readability
    BLINK_CYCLE_DURATION = 1.0  # Duration of one white/original cycle in seconds
    WHITE_PHASE_DURATION = 0.5  # Duration of white phase within each cycle

    def __init__(self):
        # Track activation timestamps
        self.activation_timestamps = deque()
        # Blinking state tracking
        self.blink_start_time = None
        self.blink_active = False
        self.previous_trigger_state = False
        self.original_theme = None
        self.white_theme = None
        # Track number of slots
        self.num_slots = 2  # Default starting with 2 slots
        self.max_slots = 10  # Maximum number of slots allowed

    def add_node(
        self,
        parent,
        node_id,
        pos=None,
        opencv_setting_dict=None,
        callback=None,
    ):
        if pos is None:
            pos = [0, 0]
        
        # Tag names
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Output
        tag_node_output01_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01Value'
        
        # Window duration control
        tag_node_window_duration_name = tag_node_name + ':WindowDuration'
        tag_node_window_duration_value_name = tag_node_name + ':WindowDurationValue'
        
        # Slot management button
        tag_node_add_slot_button = tag_node_name + ':AddSlotButton'
        tag_node_remove_slot_button = tag_node_name + ':RemoveSlotButton'

        # OpenCV settings
        self._opencv_setting_dict = opencv_setting_dict
        small_window_w = self._opencv_setting_dict.get('process_width', 640)

        # Create node in the GUI
        with dpg.node(
                tag=tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):
            # Window duration in seconds
            with dpg.node_attribute(
                    tag=tag_node_window_duration_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_float(
                    tag=tag_node_window_duration_value_name,
                    label="Window (seconds)",
                    default_value=5.0,
                    min_value=0.1,
                    min_clamped=True,
                    width=small_window_w - 150,
                    format="%.1f",
                )
            
            # Slot management buttons
            with dpg.node_attribute(
                    tag=tag_node_name + ':SlotManagement',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        tag=tag_node_add_slot_button,
                        label="Add Slot",
                        callback=self._callback_add_slot,
                        user_data=(node_id, parent),
                        width=100,
                    )
                    dpg.add_button(
                        tag=tag_node_remove_slot_button,
                        label="Remove Slot",
                        callback=self._callback_remove_slot,
                        user_data=(node_id, parent),
                        width=100,
                    )

            # Create initial slots
            for i in range(self.num_slots):
                self._create_slot(tag_node_name, parent, i, small_window_w)

            # JSON Output
            with dpg.node_attribute(
                    tag=tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=tag_node_output01_value_name,
                    default_value='Output trigger JSON',
                )

        self.tag_node_name = tag_node_name
        
        # Create white theme for blinking
        self._create_white_theme()
        
        return self
    
    def _create_slot(self, tag_node_name, parent, slot_index, small_window_w):
        """Create a single slot with input and checkbox"""
        tag_node_input_name = tag_node_name + ':' + self.TYPE_JSON + f':Input{slot_index:02d}'
        tag_node_input_value_name = tag_node_input_name + 'Value'
        tag_node_checkbox_name = tag_node_name + f':Checkbox{slot_index:02d}'
        tag_node_checkbox_value_name = tag_node_checkbox_name + 'Value'
        
        # Check if attribute already exists to avoid duplicates
        if dpg.does_item_exist(tag_node_input_name):
            return
            
        # Input slot
        with dpg.node_attribute(
                tag=tag_node_input_name,
                attribute_type=dpg.mvNode_Attr_Input,
                parent=tag_node_name,
        ):
            dpg.add_text(
                tag=tag_node_input_value_name,
                default_value=f'Input Slot {slot_index + 1}',
            )
        
        # Checkbox for expected state
        with dpg.node_attribute(
                tag=tag_node_checkbox_name,
                attribute_type=dpg.mvNode_Attr_Static,
                parent=tag_node_name,
        ):
            dpg.add_checkbox(
                tag=tag_node_checkbox_value_name,
                label=f"Slot {slot_index + 1} expects True",
                default_value=True,
            )
    
    def _callback_add_slot(self, sender, app_data, user_data):
        """Add a new slot to the node"""
        node_id, parent = user_data
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        if self.num_slots < self.max_slots:
            small_window_w = self._opencv_setting_dict.get('process_width', 640)
            self._create_slot(tag_node_name, parent, self.num_slots, small_window_w)
            self.num_slots += 1
    
    def _callback_remove_slot(self, sender, app_data, user_data):
        """Remove the last slot from the node"""
        node_id, parent = user_data
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        if self.num_slots > 1:  # Keep at least one slot
            slot_index = self.num_slots - 1
            tag_node_input_name = tag_node_name + ':' + self.TYPE_JSON + f':Input{slot_index:02d}'
            tag_node_checkbox_name = tag_node_name + f':Checkbox{slot_index:02d}'
            
            # Delete the slot and checkbox attributes
            try:
                if dpg.does_item_exist(tag_node_input_name):
                    dpg.delete_item(tag_node_input_name)
                if dpg.does_item_exist(tag_node_checkbox_name):
                    dpg.delete_item(tag_node_checkbox_name)
                self.num_slots -= 1
            except (SystemError, AttributeError):
                # GUI item may not be accessible during node deletion or UI updates
                pass
    
    def _create_white_theme(self):
        """Create a white theme for blinking effect"""
        with dpg.theme() as white_theme:
            with dpg.theme_component(dpg.mvNode):
                dpg.add_theme_color(
                    dpg.mvNodeCol_TitleBar, self.WHITE_COLOR, category=dpg.mvThemeCat_Nodes
                )
                dpg.add_theme_color(
                    dpg.mvNodeCol_TitleBarHovered, self.WHITE_COLOR, category=dpg.mvThemeCat_Nodes
                )
                dpg.add_theme_color(
                    dpg.mvNodeCol_TitleBarSelected, self.WHITE_COLOR, category=dpg.mvThemeCat_Nodes
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Text, self.TEXT_COLOR_BLACK, category=dpg.mvThemeCat_Core
                )
        
        self.white_theme = white_theme
    
    def _handle_blink_effect(self, node_id, trigger_active, current_time):
        """
        Handle the blinking effect when trigger is active.
        Blinks white/original continuously while trigger is active.
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Detect trigger activation (transition from False to True)
        if trigger_active and not self.previous_trigger_state:
            # Start blinking
            self.blink_start_time = current_time
            self.blink_active = True
            # Store original theme if not already stored
            if self.original_theme is None:
                try:
                    self.original_theme = dpg.get_item_theme(tag_node_name)
                except (SystemError, AttributeError):
                    # If we can't get the theme, we'll just use None
                    pass
        
        # Detect trigger deactivation (transition from True to False)
        if not trigger_active and self.previous_trigger_state:
            # Stop blinking and restore original theme
            try:
                if self.original_theme is not None:
                    dpg.bind_item_theme(tag_node_name, self.original_theme)
            except (SystemError, AttributeError):
                pass
            self.blink_active = False
            self.blink_start_time = None
        
        # Update previous state for next iteration
        self.previous_trigger_state = trigger_active
        
        # Handle active blinking - blink continuously while trigger is active
        if self.blink_active and self.blink_start_time is not None and trigger_active:
            elapsed = current_time - self.blink_start_time
            
            # Blink pattern: alternate between white and original color
            # Each cycle lasts BLINK_CYCLE_DURATION seconds
            cycle_time = elapsed % self.BLINK_CYCLE_DURATION
            
            try:
                if cycle_time < self.WHITE_PHASE_DURATION:
                    # Show white
                    dpg.bind_item_theme(tag_node_name, self.white_theme)
                else:
                    # Show original color
                    if self.original_theme is not None:
                        dpg.bind_item_theme(tag_node_name, self.original_theme)
            except (SystemError, AttributeError):
                # GUI item may not be accessible during node deletion or UI updates, skip theme change
                pass

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_window_duration_value_name = tag_node_name + ':WindowDurationValue'

        # Get window duration configuration
        try:
            window_duration = float(dpg_get_value(tag_node_window_duration_value_name))
        except (ValueError, TypeError):
            window_duration = 5.0

        current_time = time.time()
        
        # Check all slots to see if the combination is met
        combination_met = True
        
        for slot_index in range(self.num_slots):
            tag_node_input_name = tag_node_name + ':' + self.TYPE_JSON + f':Input{slot_index:02d}'
            tag_node_checkbox_value_name = tag_node_name + f':Checkbox{slot_index:02d}Value'
            
            # Get expected state from checkbox
            try:
                expected_state = dpg_get_value(tag_node_checkbox_value_name)
            except (SystemError, AttributeError):
                expected_state = True  # Default to True
            
            # Find connected source for this slot
            slot_value = None
            for connection_info in connection_list:
                if connection_info[1] == tag_node_input_name:
                    connection_info_src = connection_info[0]
                    connection_info_src = connection_info_src.split(':')[:2]
                    connection_info_src = ':'.join(connection_info_src)
                    
                    # Get JSON data from connected node
                    node_result = node_result_dict.get(connection_info_src, {})
                    if node_result and isinstance(node_result, dict):
                        slot_value = node_result.get('BOOL', None)
                    break
            
            # If slot is not connected or value doesn't match expected, combination is not met
            if slot_value is None or slot_value != expected_state:
                combination_met = False
                break
        
        # If combination is met, add timestamp to activation history
        if combination_met:
            self.activation_timestamps.append(current_time)
        
        # Clean up old timestamps outside the sliding window
        cutoff_time = current_time - window_duration
        while self.activation_timestamps and self.activation_timestamps[0] < cutoff_time:
            self.activation_timestamps.popleft()
        
        # Trigger is active if there's at least one activation in the window
        trigger_active = len(self.activation_timestamps) > 0
        
        # Create output JSON
        output_json = {"BOOL": trigger_active}
        
        # Update output text
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01Value'
        try:
            trigger_text = 'Active' if trigger_active else 'Inactive'
            activations_count = len(self.activation_timestamps)
            output_text = f'Activations: {activations_count} (Status: {trigger_text})'
            dpg_set_value(tag_node_output01_value_name, output_text)
        except (SystemError, AttributeError):
            # GUI item may not be accessible during update cycle or when node is being destroyed
            pass
        
        # Handle blinking effect when trigger is active
        self._handle_blink_effect(node_id, trigger_active, current_time)
        
        return {"image": None, "json": output_json, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_window_duration_value_name = tag_node_name + ':WindowDurationValue'

        window_duration = dpg_get_value(tag_node_window_duration_value_name)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_window_duration_value_name] = window_duration
        setting_dict['num_slots'] = self.num_slots
        
        # Save checkbox states for all slots
        for slot_index in range(self.num_slots):
            tag_node_checkbox_value_name = tag_node_name + f':Checkbox{slot_index:02d}Value'
            try:
                checkbox_state = dpg_get_value(tag_node_checkbox_value_name)
                setting_dict[tag_node_checkbox_value_name] = checkbox_state
            except (SystemError, AttributeError):
                pass

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_window_duration_value_name = tag_node_name + ':WindowDurationValue'

        window_duration = setting_dict.get(tag_node_window_duration_value_name, 5.0)
        dpg_set_value(tag_node_window_duration_value_name, window_duration)
        
        # Restore number of slots if saved
        saved_num_slots = setting_dict.get('num_slots', self.num_slots)
        self.num_slots = saved_num_slots
        
        # Restore checkbox states for all slots
        for slot_index in range(self.num_slots):
            tag_node_checkbox_value_name = tag_node_name + f':Checkbox{slot_index:02d}Value'
            checkbox_state = setting_dict.get(tag_node_checkbox_value_name, True)
            try:
                dpg_set_value(tag_node_checkbox_value_name, checkbox_state)
            except (SystemError, AttributeError):
                pass
