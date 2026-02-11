#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


def image_process(image, h, h_color, template_window_size, search_window_size):
    """Apply Non-Local Means (NLM) denoising for advanced noise reduction.
    
    NLM denoising is highly effective for removing noise while preserving fine details
    and textures, making it superior to bilateral filtering for low-light scenarios
    and heavy noise conditions.
    
    Args:
        image: Input BGR image
        h: Filter strength for luminance (higher = more smoothing, 10 recommended)
        h_color: Filter strength for color (higher = more smoothing, 10 recommended)
        template_window_size: Size of template patch (should be odd, typically 7)
        search_window_size: Size of search area (should be odd, typically 21)
    
    Returns:
        Denoised image
    """
    image = cv2.fastNlMeansDenoisingColored(
        image,
        None,
        h,
        h_color,
        template_window_size,
        search_window_size
    )
    return image


class FactoryNode:
    node_label = 'NLM Denoise'
    node_tag = 'NLMDenoise'

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
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02Value'
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input04Value'
        node.tag_node_input05_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input05'
        node.tag_node_input05_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input05Value'
        node.tag_node_input_enable_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputEnable'
        node.tag_node_input_enable_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputEnableValue'
        node.tag_node_enable_checkbox_name = node.tag_node_name + ':EnableCheckbox'
        node.tag_node_enable_checkbox_value_name = node.tag_node_name + ':EnableCheckboxValue'
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

            # h (luminance) slider
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input02_value_name,
                    label="h (Luminance)",
                    width=small_window_w - 80,
                    default_value=10.0,
                    min_value=node._min_h,
                    max_value=node._max_h,
                    callback=None,
                )

            # h_color slider
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label="h (Color)",
                    width=small_window_w - 80,
                    default_value=10.0,
                    min_value=node._min_h,
                    max_value=node._max_h,
                    callback=None,
                )

            # Template window size slider
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input04_value_name,
                    label="Template Size",
                    width=small_window_w - 80,
                    default_value=7,
                    min_value=node._min_template_size,
                    max_value=node._max_template_size,
                    callback=None,
                )

            # Search window size slider
            with dpg.node_attribute(
                    tag=node.tag_node_input05_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input05_value_name,
                    label="Search Size",
                    width=small_window_w - 80,
                    default_value=21,
                    min_value=node._min_search_size,
                    max_value=node._max_search_size,
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

    node_label = 'NLM Denoise'
    node_tag = 'NLMDenoise'

    _min_h = 0.0
    _max_h = 30.0
    _min_template_size = 3
    _max_template_size = 11
    _min_search_size = 7
    _max_search_size = 35

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
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_INT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_INT + ':Input05Value'
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
            
            if connection_type == self.TYPE_FLOAT:
                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = round(float(dpg_get_value(source_tag)), 3)
                input_value = max(self._min_h, input_value)
                input_value = min(self._max_h, input_value)
                dpg_set_value(destination_tag, input_value)

            if connection_type == self.TYPE_INT:
                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = int(dpg_get_value(source_tag))
                
                # Apply appropriate limits based on destination
                if ':Input04Value' in destination_tag:
                    input_value = max(self._min_template_size, input_value)
                    input_value = min(self._max_template_size, input_value)
                elif ':Input05Value' in destination_tag:
                    input_value = max(self._min_search_size, input_value)
                    input_value = min(self._max_search_size, input_value)
                
                dpg_set_value(destination_tag, input_value)

        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)

        h = float(dpg_get_value(input_value02_tag))
        h_color = float(dpg_get_value(input_value03_tag))
        template_size = int(dpg_get_value(input_value04_tag))
        search_size = int(dpg_get_value(input_value05_tag))

        # Ensure sizes are odd
        if template_size % 2 == 0:
            template_size += 1
        if search_size % 2 == 0:
            search_size += 1

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # Only process if enabled, otherwise pass-through
        if frame is not None and enable_processing:
            frame = image_process(frame, h, h_color, template_size, search_size)

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
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_INT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_INT + ':Input05Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'

        pos = dpg.get_item_pos(tag_node_name)
        h = dpg_get_value(input_value02_tag)
        h_color = dpg_get_value(input_value03_tag)
        template_size = dpg_get_value(input_value04_tag)
        search_size = dpg_get_value(input_value05_tag)
        enable_value = dpg_get_value(enable_checkbox_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = h
        setting_dict[input_value03_tag] = h_color
        setting_dict[input_value04_tag] = template_size
        setting_dict[input_value05_tag] = search_size
        setting_dict[enable_checkbox_tag] = enable_value

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_INT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_INT + ':Input05Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'
        
        if input_value02_tag in setting_dict:
            h = float(setting_dict[input_value02_tag])
            dpg_set_value(input_value02_tag, h)
        
        if input_value03_tag in setting_dict:
            h_color = float(setting_dict[input_value03_tag])
            dpg_set_value(input_value03_tag, h_color)
        
        if input_value04_tag in setting_dict:
            template_size = int(setting_dict[input_value04_tag])
            dpg_set_value(input_value04_tag, template_size)
        
        if input_value05_tag in setting_dict:
            search_size = int(setting_dict[input_value05_tag])
            dpg_set_value(input_value05_tag, search_size)
        
        if enable_checkbox_tag in setting_dict:
            enable_value = setting_dict[enable_checkbox_tag]
            dpg_set_value(enable_checkbox_tag, enable_value)
