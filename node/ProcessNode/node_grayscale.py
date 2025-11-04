#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node_editor import node_resizer

from node.node_abc import DpgNodeABC

from node.basenode import Node

def image_process(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image

class FactoryNode:
    node_label = 'Grayscale'
    node_tag = 'Grayscale'
    

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
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']


        black_image = np.zeros((small_window_w, small_window_h, 3))
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
                    default_value='Input BGR image',
                )
                
                # Add size selector
                with dpg.group(horizontal=True):
                    dpg.add_text("Size:")
                    node.tag_node_size_selector = node.tag_node_name + ':SizeSelector'
                    dpg.add_combo(
                        items=node_resizer.SIZE_PRESET_NAMES,
                        default_value="Small",
                        tag=node.tag_node_size_selector,
                        width=100,
                        callback=lambda: node.resize_node(node_id),
                    )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

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


class Node(Node):
    _ver = '0.0.2'  # Bumped version for resize feature

    node_label = 'Grayscale'
    node_tag = 'Grayscale'

    _opencv_setting_dict = None
    _node_sizes = {}  # Store node sizes {node_id: (width, height)}

    def __init__(self):
        pass
    
    def resize_node(self, node_id):
        """Callback when node size is changed"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        size_selector_tag = tag_node_name + ':SizeSelector'
        
        # Get selected size
        size_name = dpg_get_value(size_selector_tag)
        width, height = node_resizer.get_size_from_preset(size_name)
        
        # Store the new size
        self._node_sizes[str(node_id)] = (width, height)
        
        # Update texture size
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        
        # Create new blank texture with new size
        black_image = np.zeros((width, height, 3))
        black_texture = self.convert_cv_to_dpg(black_image, width, height)
        
        # Delete old texture and create new one
        if dpg.does_item_exist(output_value01_tag):
            dpg.delete_item(output_value01_tag)
        
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                width,
                height,
                black_texture,
                tag=output_value01_tag,
                format=dpg.mvFormat_Float_rgb,
            )



    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        # Get size from stored sizes, or use defaults
        if str(node_id) in self._node_sizes:
            small_window_w, small_window_h = self._node_sizes[str(node_id)]
        else:
            small_window_w = self._opencv_setting_dict['process_width']
            small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']


        for connection_info in connection_list:
            pass

 
        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict=None)


        if frame is not None and use_pref_counter:
            start_time = time.monotonic()


        if frame is not None:
            frame = image_process(frame)


        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')


        if frame is not None:
            texture = self.convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image":frame, "json":None, "audio":None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        size_selector_tag = tag_node_name + ':SizeSelector'

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        
        # Save the selected size
        if dpg.does_item_exist(size_selector_tag):
            setting_dict['size_preset'] = dpg_get_value(size_selector_tag)
        
        # Save the actual size if stored
        if str(node_id) in self._node_sizes:
            setting_dict['node_size'] = self._node_sizes[str(node_id)]

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        size_selector_tag = tag_node_name + ':SizeSelector'
        
        # Restore size preset if saved
        if 'size_preset' in setting_dict and dpg.does_item_exist(size_selector_tag):
            dpg_set_value(size_selector_tag, setting_dict['size_preset'])
        
        # Restore node size if saved
        if 'node_size' in setting_dict:
            self._node_sizes[str(node_id)] = setting_dict['node_size']
            # Trigger resize to update the texture
            self.resize_node(node_id)
