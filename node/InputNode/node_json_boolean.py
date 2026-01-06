#!/usr/bin/env python
# -*- coding: utf-8 -*-
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode


class FactoryNode:
    node_label = 'JsonBoolean'
    node_tag = 'JsonBoolean'
    
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
        """Adds a JSON Boolean node that outputs a boolean value wrapped in JSON."""
        
        # Generate node instance
        node = Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        
        # Output tags (JSON type)
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'
        
        # Internal checkbox tag
        node.tag_node_checkbox_name = node.tag_node_name + ':Checkbox'
        
        node._opencv_setting_dict = opencv_setting_dict

        # Create yellow theme for JSON button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # Create node in the GUI
        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Checkbox input
            with dpg.node_attribute(
                tag=node.tag_node_name + ':Input',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_checkbox_name,
                    label="Enabled",
                    default_value=True,
                    callback=None,
                )
            
            # JSON output button
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(default_value='JSON (boolean)')
                btn = dpg.add_button(
                    label="Boolean Output",
                    tag=node.tag_node_output01_value_name,
                    width=150,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                    
        return node


class Node(BaseNode):
    _ver = '1.0.0'

    node_label = 'JsonBoolean'
    node_tag = 'JsonBoolean'

    _opencv_setting_dict = None

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
        """JSON Boolean node outputs the checkbox value as JSON."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        checkbox_tag = tag_node_name + ':Checkbox'
        
        # Get checkbox value
        checkbox_value = dpg_get_value(checkbox_tag)
        if checkbox_value is None:
            checkbox_value = True  # Default to True
        
        # Wrap in JSON format with 'enabled' key
        json_output = {
            'enabled': bool(checkbox_value)
        }
        
        return {"image": None, "json": json_output, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        """Save the current boolean value."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        checkbox_tag = tag_node_name + ':Checkbox'

        checkbox_value = dpg_get_value(checkbox_tag)
        if checkbox_value is None:
            checkbox_value = True
        
        pos = dpg.get_item_pos(tag_node_name)
        
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[checkbox_tag] = bool(checkbox_value)
        
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Restore the boolean value."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        checkbox_tag = tag_node_name + ':Checkbox'

        checkbox_value = setting_dict.get(checkbox_tag, True)
        dpg_set_value(checkbox_tag, bool(checkbox_value))
