#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


def image_process(image, kernel_type, strength):
    """Apply kernel-based sharpening for edge enhancement.
    
    Kernel-based sharpening uses convolution with predefined kernels to enhance
    edges and details in images. Different kernels provide different sharpening
    characteristics, from subtle to aggressive edge enhancement.
    
    Args:
        image: Input BGR image
        kernel_type: Type of sharpening kernel (0-3)
        strength: Sharpening strength multiplier (0.0-2.0)
    
    Returns:
        Sharpened image
    """
    # Define sharpening kernels
    kernels = {
        0: np.array([[-1, -1, -1],
                     [-1,  9, -1],
                     [-1, -1, -1]]),  # Standard sharpening
        
        1: np.array([[0, -1,  0],
                     [-1, 5, -1],
                     [0, -1,  0]]),  # Mild sharpening
        
        2: np.array([[-1, -1, -1, -1, -1],
                     [-1,  2,  2,  2, -1],
                     [-1,  2,  8,  2, -1],
                     [-1,  2,  2,  2, -1],
                     [-1, -1, -1, -1, -1]]) / 8.0,  # 5x5 strong sharpening
        
        3: np.array([[1,  4,    6,  4, 1],
                     [4, 16,  24, 16, 4],
                     [6, 24, -476, 24, 6],
                     [4, 16,  24, 16, 4],
                     [1,  4,    6,  4, 1]]) / -256.0,  # Laplacian sharpening
    }
    
    kernel = kernels[kernel_type]
    
    # Apply strength multiplier to kernel
    if kernel_type <= 1:
        # For simple kernels, blend with identity
        identity = np.array([[0, 0, 0],
                            [0, 1, 0],
                            [0, 0, 0]])
        kernel = identity + strength * (kernel - identity)
    else:
        # For complex kernels, multiply strength
        kernel = kernel * strength
    
    # Apply the kernel
    sharpened = cv2.filter2D(image, -1, kernel)
    
    # Clip values to valid range
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
    
    return sharpened


class FactoryNode:
    node_label = 'Kernel Sharpen'
    node_tag = 'KernelSharpen'

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
        node.tag_node_input_enable_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputEnable'
        node.tag_node_input_enable_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputEnableValue'
        node.tag_node_enable_checkbox_name = node.tag_node_name + ':EnableCheckbox'
        node.tag_node_enable_checkbox_value_name = node.tag_node_name + ':EnableCheckboxValue'
        node.tag_node_combo_name = node.tag_node_name + ':KernelCombo'
        node.tag_node_combo_value_name = node.tag_node_name + ':KernelComboValue'
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

            # Kernel type combo
            with dpg.node_attribute(
                    tag=node.tag_node_combo_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_combo_value_name,
                    label='Kernel Type',
                    items=node._kernel_types,
                    default_value=node._kernel_types[0],
                    width=small_window_w - 80,
                )

            # Strength slider
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input02_value_name,
                    label="Strength",
                    width=small_window_w - 80,
                    default_value=1.0,
                    min_value=node._min_strength,
                    max_value=node._max_strength,
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

    node_label = 'Kernel Sharpen'
    node_tag = 'KernelSharpen'

    _kernel_types = ['Standard', 'Mild', 'Strong 5x5', 'Laplacian']
    _min_strength = 0.0
    _max_strength = 2.0

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
        combo_tag = tag_node_name + ':KernelComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
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
                input_value = max(self._min_strength, input_value)
                input_value = min(self._max_strength, input_value)
                dpg_set_value(destination_tag, input_value)

        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)

        kernel_type_str = dpg_get_value(combo_tag)
        kernel_type = self._kernel_types.index(kernel_type_str)
        strength = float(dpg_get_value(input_value02_tag))

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # Only process if enabled, otherwise pass-through
        if frame is not None and enable_processing:
            frame = image_process(frame, kernel_type, strength)

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
        combo_tag = tag_node_name + ':KernelComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'

        pos = dpg.get_item_pos(tag_node_name)
        kernel_type = dpg_get_value(combo_tag)
        strength = dpg_get_value(input_value02_tag)
        enable_value = dpg_get_value(enable_checkbox_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[combo_tag] = kernel_type
        setting_dict[input_value02_tag] = strength
        setting_dict[enable_checkbox_tag] = enable_value

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        combo_tag = tag_node_name + ':KernelComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'
        
        if combo_tag in setting_dict:
            kernel_type = setting_dict[combo_tag]
            dpg_set_value(combo_tag, kernel_type)
        
        if input_value02_tag in setting_dict:
            strength = float(setting_dict[input_value02_tag])
            dpg_set_value(input_value02_tag, strength)
        
        if enable_checkbox_tag in setting_dict:
            enable_value = setting_dict[enable_checkbox_tag]
            dpg_set_value(enable_checkbox_tag, enable_value)
