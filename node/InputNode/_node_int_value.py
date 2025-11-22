#!/usr/bin/env python
# -*- coding: utf-8 -*-
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode


class FactoryNode:
    node_label = 'IntValue'
    node_tag = 'IntValue'
    
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
        """Adds an Int Value node that outputs an integer value."""
        
        # Generate node instance
        node = Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        
        # Output tags
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_INT + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Output01Value'
        
        node._opencv_setting_dict = opencv_setting_dict

        # Create node in the GUI
        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Int value slider as output
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_output01_value_name,
                    label="",
                    width=150,
                    default_value=0,
                    min_value=-100,
                    max_value=100,
                    callback=None,
                )
                    
        return node


class Node(BaseNode):
    _ver = '1.0.0'

    node_label = 'IntValue'
    node_tag = 'IntValue'

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
        """Int Value node just passes through the value set by the slider."""
        # No processing needed - the slider value is directly accessible
        # through the output tag when other nodes connect to it
        return {"image": None, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        """Save the current int value."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value_tag = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'

        output_value = int(dpg_get_value(output_value_tag))
        pos = dpg.get_item_pos(tag_node_name)
        
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[output_value_tag] = output_value
        
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Restore the int value."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value_tag = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'

        output_value = int(setting_dict[output_value_tag])
        dpg_set_value(output_value_tag, output_value)
