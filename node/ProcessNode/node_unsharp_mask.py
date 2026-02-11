#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


def image_process(image, kernel_size, amount, threshold):
    """Apply unsharp masking for edge enhancement and local contrast improvement.
    
    Unsharp masking is highly effective for enhancing object boundaries and details,
    particularly in low-contrast or slightly blurred images. This improves object
    detection performance in diverse lighting conditions.
    
    Args:
        image: Input BGR image
        kernel_size: Size of Gaussian blur kernel (larger = more blurring)
        amount: Strength of sharpening (0.0-2.0, typically 1.0-1.5)
        threshold: Minimum brightness change to sharpen (reduces noise amplification)
    
    Returns:
        Sharpened image
    """
    # Ensure kernel size is odd
    if kernel_size % 2 == 0:
        kernel_size += 1
    
    # Create blurred version of the image
    blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    
    # Calculate the unsharp mask
    # Formula: sharpened = original + amount * (original - blurred)
    sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    
    # Apply threshold to reduce noise amplification
    if threshold > 0:
        low_contrast_mask = np.abs(image - blurred) < threshold
        sharpened = np.where(low_contrast_mask, image, sharpened)
    
    return sharpened


class FactoryNode:
    node_label = 'Unsharp Mask'
    node_tag = 'UnsharpMask'

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
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input04Value'
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

            # Kernel Size slider
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input02_value_name,
                    label="Kernel Size",
                    width=small_window_w - 80,
                    default_value=5,
                    min_value=node._min_kernel_size,
                    max_value=node._max_kernel_size,
                    callback=None,
                )

            # Amount slider
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label="Amount",
                    width=small_window_w - 80,
                    default_value=1.0,
                    min_value=node._min_amount,
                    max_value=node._max_amount,
                    callback=None,
                )

            # Threshold slider
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input04_value_name,
                    label="Threshold",
                    width=small_window_w - 80,
                    default_value=0,
                    min_value=node._min_threshold,
                    max_value=node._max_threshold,
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

    node_label = 'Unsharp Mask'
    node_tag = 'UnsharpMask'

    _min_kernel_size = 1
    _max_kernel_size = 25
    _min_amount = 0.0
    _max_amount = 2.0
    _min_threshold = 0
    _max_threshold = 50

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
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_INT + ':Input04Value'
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
                
                # Apply appropriate limits based on destination
                if ':Input02Value' in destination_tag:
                    input_value = max(self._min_kernel_size, input_value)
                    input_value = min(self._max_kernel_size, input_value)
                elif ':Input04Value' in destination_tag:
                    input_value = max(self._min_threshold, input_value)
                    input_value = min(self._max_threshold, input_value)
                
                dpg_set_value(destination_tag, input_value)

            if connection_type == self.TYPE_FLOAT:
                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = round(float(dpg_get_value(source_tag)), 3)
                input_value = max(self._min_amount, input_value)
                input_value = min(self._max_amount, input_value)
                dpg_set_value(destination_tag, input_value)

        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)

        kernel_size = int(dpg_get_value(input_value02_tag))
        amount = float(dpg_get_value(input_value03_tag))
        threshold = int(dpg_get_value(input_value04_tag))

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # Only process if enabled, otherwise pass-through
        if frame is not None and enable_processing:
            frame = image_process(frame, kernel_size, amount, threshold)

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
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_INT + ':Input04Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'

        pos = dpg.get_item_pos(tag_node_name)
        kernel_size = dpg_get_value(input_value02_tag)
        amount = dpg_get_value(input_value03_tag)
        threshold = dpg_get_value(input_value04_tag)
        enable_value = dpg_get_value(enable_checkbox_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = kernel_size
        setting_dict[input_value03_tag] = amount
        setting_dict[input_value04_tag] = threshold
        setting_dict[enable_checkbox_tag] = enable_value

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_INT + ':Input04Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'
        
        if input_value02_tag in setting_dict:
            kernel_size = int(setting_dict[input_value02_tag])
            dpg_set_value(input_value02_tag, kernel_size)
        
        if input_value03_tag in setting_dict:
            amount = float(setting_dict[input_value03_tag])
            dpg_set_value(input_value03_tag, amount)
        
        if input_value04_tag in setting_dict:
            threshold = int(setting_dict[input_value04_tag])
            dpg_set_value(input_value04_tag, threshold)
        
        if enable_checkbox_tag in setting_dict:
            enable_value = setting_dict[enable_checkbox_tag]
            dpg_set_value(enable_checkbox_tag, enable_value)
