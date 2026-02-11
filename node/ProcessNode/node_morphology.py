#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


def image_process(image, morph_type, kernel_size, iterations):
    """Apply morphological operations for shape refinement.
    
    Morphological operations are essential for cleaning up segmentation results,
    filling holes, and improving object connectivity in detection pipelines.
    
    Args:
        image: Input BGR image
        morph_type: Type of morphological operation (0-6)
        kernel_size: Size of the structuring element (odd number)
        iterations: Number of times to apply the operation
    
    Returns:
        Processed image
    """
    # Ensure kernel size is odd
    if kernel_size % 2 == 0:
        kernel_size += 1
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    
    # Morphological operation types
    morph_operations = {
        0: cv2.MORPH_ERODE,
        1: cv2.MORPH_DILATE,
        2: cv2.MORPH_OPEN,
        3: cv2.MORPH_CLOSE,
        4: cv2.MORPH_GRADIENT,
        5: cv2.MORPH_TOPHAT,
        6: cv2.MORPH_BLACKHAT,
    }
    
    operation = morph_operations.get(morph_type, cv2.MORPH_CLOSE)
    image = cv2.morphologyEx(image, operation, kernel, iterations=iterations)
    
    return image


class FactoryNode:
    node_label = 'Morphology'
    node_tag = 'Morphology'

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
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input03Value'
        node.tag_node_input_enable_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputEnable'
        node.tag_node_input_enable_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputEnableValue'
        node.tag_node_enable_checkbox_name = node.tag_node_name + ':EnableCheckbox'
        node.tag_node_enable_checkbox_value_name = node.tag_node_name + ':EnableCheckboxValue'
        node.tag_node_combo_name = node.tag_node_name + ':MorphTypeCombo'
        node.tag_node_combo_value_name = node.tag_node_name + ':MorphTypeComboValue'
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

            # Morphological operation type combo
            with dpg.node_attribute(
                    tag=node.tag_node_combo_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_combo_value_name,
                    label='Operation',
                    items=node._morph_types,
                    default_value=node._morph_types[3],  # Close by default
                    width=small_window_w - 80,
                )

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

            # Iterations slider
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input03_value_name,
                    label="Iterations",
                    width=small_window_w - 80,
                    default_value=1,
                    min_value=node._min_iterations,
                    max_value=node._max_iterations,
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

    node_label = 'Morphology'
    node_tag = 'Morphology'

    _morph_types = ['Erode', 'Dilate', 'Open', 'Close', 'Gradient', 'TopHat', 'BlackHat']
    _min_kernel_size = 1
    _max_kernel_size = 21
    _min_iterations = 1
    _max_iterations = 10

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
        combo_tag = tag_node_name + ':MorphTypeComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_INT + ':Input03Value'
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
                elif ':Input03Value' in destination_tag:
                    input_value = max(self._min_iterations, input_value)
                    input_value = min(self._max_iterations, input_value)
                
                dpg_set_value(destination_tag, input_value)

        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)

        morph_type_str = dpg_get_value(combo_tag)
        morph_type = self._morph_types.index(morph_type_str)
        kernel_size = int(dpg_get_value(input_value02_tag))
        iterations = int(dpg_get_value(input_value03_tag))

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # Only process if enabled, otherwise pass-through
        if frame is not None and enable_processing:
            frame = image_process(frame, morph_type, kernel_size, iterations)

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
        combo_tag = tag_node_name + ':MorphTypeComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_INT + ':Input03Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'

        pos = dpg.get_item_pos(tag_node_name)
        morph_type = dpg_get_value(combo_tag)
        kernel_size = dpg_get_value(input_value02_tag)
        iterations = dpg_get_value(input_value03_tag)
        enable_value = dpg_get_value(enable_checkbox_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[combo_tag] = morph_type
        setting_dict[input_value02_tag] = kernel_size
        setting_dict[input_value03_tag] = iterations
        setting_dict[enable_checkbox_tag] = enable_value

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        combo_tag = tag_node_name + ':MorphTypeComboValue'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_INT + ':Input03Value'
        enable_checkbox_tag = tag_node_name + ':EnableCheckboxValue'
        
        if combo_tag in setting_dict:
            morph_type = setting_dict[combo_tag]
            dpg_set_value(combo_tag, morph_type)
        
        if input_value02_tag in setting_dict:
            kernel_size = int(setting_dict[input_value02_tag])
            dpg_set_value(input_value02_tag, kernel_size)
        
        if input_value03_tag in setting_dict:
            iterations = int(setting_dict[input_value03_tag])
            dpg_set_value(input_value03_tag, iterations)
        
        if enable_checkbox_tag in setting_dict:
            enable_value = setting_dict[enable_checkbox_tag]
            dpg_set_value(enable_checkbox_tag, enable_value)
