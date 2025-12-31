#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


def image_process(image, beta):
    image = cv2.convertScaleAbs(image, alpha=1.0, beta=beta)
    return image


class FactoryNode:
    node_label = "Brightness"
    node_tag = "Brightness"

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
        node.tag_node_name = str(node_id) + ":" + node.node_tag
        node.tag_node_input01_name = (
            node.tag_node_name + ":" + node.TYPE_IMAGE + ":Input01"
        )
        node.tag_node_input01_value_name = (
            node.tag_node_name + ":" + node.TYPE_IMAGE + ":Input01Value"
        )
        node.tag_node_input02_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input02"
        )
        node.tag_node_input02_value_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input02Value"
        )
        node.tag_node_input_enable_name = (
            node.tag_node_name + ":" + node.TYPE_JSON + ":InputEnable"
        )
        node.tag_node_input_enable_value_name = (
            node.tag_node_name + ":" + node.TYPE_JSON + ":InputEnableValue"
        )
        node.tag_node_enable_checkbox_name = (
            node.tag_node_name + ":EnableCheckbox"
        )
        node.tag_node_enable_checkbox_value_name = (
            node.tag_node_name + ":EnableCheckboxValue"
        )
        node.tag_node_output01_name = (
            node.tag_node_name + ":" + node.TYPE_IMAGE + ":Output01"
        )
        node.tag_node_output01_value_name = (
            node.tag_node_name + ":" + node.TYPE_IMAGE + ":Output01Value"
        )
        node.tag_node_output02_name = (
            node.tag_node_name + ":" + node.TYPE_TIME_MS + ":Output02"
        )
        node.tag_node_output02_value_name = (
            node.tag_node_name + ":" + node.TYPE_TIME_MS + ":Output02Value"
        )

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict["process_width"]
        small_window_h = node._opencv_setting_dict["process_height"]
        use_pref_counter = node._opencv_setting_dict["use_pref_counter"]

        black_image = np.zeros((small_window_w, small_window_h, 3), dtype=np.uint8)
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
                    default_value="Input BGR image",
                )

            # Boolean enable/disable input
            with dpg.node_attribute(
                tag=node.tag_node_input_enable_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_enable_value_name,
                    default_value="Enable (JSON BOOL)",
                )

            # Enable checkbox (default True)
            with dpg.node_attribute(
                tag=node.tag_node_enable_checkbox_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_enable_checkbox_value_name,
                    label="Enable processing",
                    default_value=True,
                )

            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            with dpg.node_attribute(
                tag=node.tag_node_input02_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input02_value_name,
                    label="beta",
                    width=small_window_w - 80,
                    default_value=0,
                    min_value=node._min_val,
                    max_value=node._max_val,
                    callback=None,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output02_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value="elapsed time(ms)",
                    )

        return node


class Node(Node):
    _ver = "0.0.1"

    node_label = "Brightness"
    node_tag = "Brightness"

    _min_val = 0
    _max_val = 255

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
        frame = None
        tag_node_name = str(node_id) + ":" + self.node_tag
        input_value02_tag = tag_node_name + ":" + self.TYPE_INT + ":Input02Value"
        enable_checkbox_tag = tag_node_name + ":EnableCheckboxValue"
        output_value01_tag = tag_node_name + ":" + self.TYPE_IMAGE + ":Output01Value"
        output_value02_tag = tag_node_name + ":" + self.TYPE_TIME_MS + ":Output02Value"

        small_window_w = self._opencv_setting_dict["process_width"]
        small_window_h = self._opencv_setting_dict["process_height"]
        use_pref_counter = self._opencv_setting_dict["use_pref_counter"]

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

        for connection_info in connection_list:
            connection_type = connection_info[0].split(":")[2]

            if connection_type == self.TYPE_INT:
                source_tag = connection_info[0] + "Value"
                destination_tag = connection_info[1] + "Value"

                input_value = int(dpg_get_value(source_tag))
                input_value = max([self._min_val, input_value])
                input_value = min([self._max_val, input_value])
                dpg_set_value(destination_tag, input_value)

            elif connection_type == self.TYPE_AUDIO:
                frame = self.get_input_frame(
                    connection_list, node_image_dict, node_audio_dict
                )

            else:
                # Skip JSON connections (already handled above)
                if connection_type.upper() != self.TYPE_JSON.upper():
                    frame = self.get_input_frame(
                        connection_list, node_image_dict, node_audio_dict
                    )

        beta = int(dpg_get_value(input_value02_tag))

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # Only process if enabled, otherwise pass-through
        if frame is not None and enable_processing:
            frame = image_process(frame, beta)

        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + "ms")

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
        tag_node_name = str(node_id) + ":" + self.node_tag
        input_value02_tag = tag_node_name + ":" + self.TYPE_INT + ":Input02Value"
        enable_checkbox_tag = tag_node_name + ":EnableCheckboxValue"

        kernel_size = dpg_get_value(input_value02_tag)
        enable_value = dpg_get_value(enable_checkbox_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict["ver"] = self._ver
        setting_dict["pos"] = pos
        setting_dict[input_value02_tag] = kernel_size
        setting_dict[enable_checkbox_tag] = enable_value

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ":" + self.node_tag
        input_value02_tag = tag_node_name + ":" + self.TYPE_INT + ":Input02Value"
        enable_checkbox_tag = tag_node_name + ":EnableCheckboxValue"

        kernel_size = int(setting_dict[input_value02_tag])
        dpg_set_value(input_value02_tag, kernel_size)
        
        if enable_checkbox_tag in setting_dict:
            enable_value = setting_dict[enable_checkbox_tag]
            dpg_set_value(enable_checkbox_tag, enable_value)
