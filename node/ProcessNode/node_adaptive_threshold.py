#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


def image_process(image, method, threshold_type, block_size, c_value):
    """Apply adaptive thresholding for varying lighting conditions.
    
    Adaptive thresholding is crucial for object detection in images with uneven
    lighting, shadows, or varying illumination. It calculates threshold values
    locally for each pixel region, making it superior to fixed thresholding.
    
    Args:
        image: Input BGR image
        method: Adaptive method (0=Mean, 1=Gaussian)
        threshold_type: Threshold type (0=Binary, 1=Binary Inverted)
        block_size: Size of pixel neighborhood (must be odd)
        c_value: Constant subtracted from weighted mean
    
    Returns:
        Thresholded image
    """
    # Ensure block size is odd
    if block_size % 2 == 0:
        block_size += 1
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Adaptive method mapping
    methods = {
        0: cv2.ADAPTIVE_THRESH_MEAN_C,
        1: cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    }
    
    # Threshold type mapping
    threshold_types = {
        0: cv2.THRESH_BINARY,
        1: cv2.THRESH_BINARY_INV,
    }
    
    # Apply adaptive threshold
    result = cv2.adaptiveThreshold(
        gray,
        255,
        methods[method],
        threshold_types[threshold_type],
        block_size,
        c_value
    )
    
    # Convert back to BGR for display
    result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
    
    return result


class FactoryNode:
    node_label = 'Adaptive Threshold'
    node_tag = 'AdaptiveThreshold'

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
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02Value'
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        node.tag_node_input_enable_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputEnable'
        node.tag_node_input_enable_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputEnableValue'
        node.tag_node_enable_checkbox_name = node.tag_node_name + ':EnableCheckbox'
        node.tag_node_enable_checkbox_value_name = node.tag_node_name + ':EnableCheckboxValue'
        node.tag_node_combo_method_name = node.tag_node_name + ':MethodCombo'
        node.tag_node_combo_method_value_name = node.tag_node_name + ':MethodComboValue'
        node.tag_node_combo_type_name = node.tag_node_name + ':TypeCombo'
        node.tag_node_combo_type_value_name = node.tag_node_name + ':TypeComboValue'
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

            # Boolean enable/disable input
            with dpg.node_attribute(
                    tag=node.tag_node_input_enable_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_enable_value_name,
                    default_value='Enable (JSON BOOL)',
                )

            # Enable checkbox (default True)
            with dpg.node_attribute(
                    tag=node.tag_node_enable_checkbox_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_enable_checkbox_value_name,
                    label='Enable processing',
                    default_value=True,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Method combo
            with dpg.node_attribute(
                    tag=node.tag_node_combo_method_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_combo_method_value_name,
                    label='Method',
                    items=node._methods,
                    default_value=node._methods[1],  # Gaussian by default
                    width=small_window_w - 80,
                )

            # Threshold type combo
            with dpg.node_attribute(
                    tag=node.tag_node_combo_type_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_combo_type_value_name,
                    label='Type',
                    items=node._threshold_types,
                    default_value=node._threshold_types[0],
                    width=small_window_w - 80,
                )

            # Block size slider
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input02_value_name,
                    label="Block Size",
                    width=small_window_w - 80,
                    default_value=11,
                    min_value=node._min_block_size,
                    max_value=node._max_block_size,
                    callback=None,
                )

            # C value slider
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label="C Value",
                    width=small_window_w - 80,
                    default_value=2.0,
                    min_value=node._min_c,
                    max_value=node._max_c,
                    callback=None,
                )

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
    _ver = '0.0.1'

    node_label = 'Adaptive Threshold'
    node_tag = 'AdaptiveThreshold'

    _methods = ['Mean', 'Gaussian']
    _threshold_types = ['Binary', 'Binary Inverted']
    _min_block_size = 3
    _max_block_size = 99
    _min_c = -20.0
    _max_c = 20.0

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
        tag_node_name = str(node_id) + ':' + self.node_tag
        combo_method_tag = tag_node_name + ':MethodComboValue'
        combo_type_tag = tag_node_name + ':TypeComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Check if processing is enabled via checkbox (default) or JSON input
        enable_processing = dpg_get_value(enable_checkbox_tag)
        
        # Check for JSON boolean input (overrides checkbox if connected)
        enable_from_json = None
        for connection_info in connection_list:
            connection_type = connection_info[0].split(":")[2]
            if connection_type.upper() == self.TYPE_JSON.upper():
                # Check if this is the enable input
                if ":InputEnable" in connection_info[1]:
                    connection_info_src = connection_info[0]
                    connection_info_src = connection_info_src.split(':')[:2]
                    connection_info_src = ':'.join(connection_info_src)
                    
                    json_data = node_result_dict.get(connection_info_src, None)
                    if json_data is not None and isinstance(json_data, dict):
                        enable_from_json = json_data.get('BOOL', None)
                    break
        
        # JSON input overrides checkbox if connected
        if enable_from_json is not None:
            enable_processing = enable_from_json

        # Handle connections
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            
            if connection_type == self.TYPE_INT:
                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = int(dpg_get_value(source_tag))
                input_value = max(self._min_block_size, input_value)
                input_value = min(self._max_block_size, input_value)
                dpg_set_value(destination_tag, input_value)

            if connection_type == self.TYPE_FLOAT:
                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = round(float(dpg_get_value(source_tag)), 3)
                input_value = max(self._min_c, input_value)
                input_value = min(self._max_c, input_value)
                dpg_set_value(destination_tag, input_value)

        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)

        method_str = dpg_get_value(combo_method_tag)
        method = self._methods.index(method_str)
        
        threshold_type_str = dpg_get_value(combo_type_tag)
        threshold_type = self._threshold_types.index(threshold_type_str)
        
        block_size = int(dpg_get_value(input_value02_tag))
        c_value = float(dpg_get_value(input_value03_tag))

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # Only process if enabled, otherwise pass-through
        if frame is not None and enable_processing:
            frame = image_process(frame, method, threshold_type, block_size, c_value)

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

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        combo_method_tag = tag_node_name + ':MethodComboValue'
        combo_type_tag = tag_node_name + ':TypeComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'

        pos = dpg.get_item_pos(tag_node_name)
        method = dpg_get_value(combo_method_tag)
        threshold_type = dpg_get_value(combo_type_tag)
        block_size = dpg_get_value(input_value02_tag)
        c_value = dpg_get_value(input_value03_tag)
        enable_value = dpg_get_value(enable_checkbox_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[combo_method_tag] = method
        setting_dict[combo_type_tag] = threshold_type
        setting_dict[input_value02_tag] = block_size
        setting_dict[input_value03_tag] = c_value
        setting_dict[enable_checkbox_tag] = enable_value

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        combo_method_tag = tag_node_name + ':MethodComboValue'
        combo_type_tag = tag_node_name + ':TypeComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'
        
        if combo_method_tag in setting_dict:
            method = setting_dict[combo_method_tag]
            dpg_set_value(combo_method_tag, method)
        
        if combo_type_tag in setting_dict:
            threshold_type = setting_dict[combo_type_tag]
            dpg_set_value(combo_type_tag, threshold_type)
        
        if input_value02_tag in setting_dict:
            block_size = int(setting_dict[input_value02_tag])
            dpg_set_value(input_value02_tag, block_size)
        
        if input_value03_tag in setting_dict:
            c_value = float(setting_dict[input_value03_tag])
            dpg_set_value(input_value03_tag, c_value)
        
        if enable_checkbox_tag in setting_dict:
            enable_value = setting_dict[enable_checkbox_tag]
            dpg_set_value(enable_checkbox_tag, enable_value)
