#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node

def crop_from_center(image, width, center_x, center_y):
    """Crop image using square width and center position
    
    Args:
        image: Input image
        width: Width of the crop square (normalized, 0.0 to 1.0)
        center_x: X position of center (normalized, 0.0 to 1.0)
        center_y: Y position of center (normalized, 0.0 to 1.0)
    
    Returns:
        Cropped image (square)
    """
    image_height, image_width = image.shape[0], image.shape[1]
    
    # Ensure width is valid
    if width <= 0:
        width = 0.01
    if width > 1.0:
        width = 1.0
    
    # Use the smaller dimension to ensure square crop fits
    min_dimension = min(image_width, image_height)
    
    # Calculate square size in pixels
    square_size = int(width * min_dimension)
    if square_size < 1:
        square_size = 1
    
    # Calculate center position in pixels
    center_x_px = int(center_x * image_width)
    center_y_px = int(center_y * image_height)
    
    # Calculate half size
    half_size = square_size // 2
    
    # Calculate crop boundaries
    min_x_px = center_x_px - half_size
    max_x_px = min_x_px + square_size
    min_y_px = center_y_px - half_size
    max_y_px = min_y_px + square_size
    
    # Clamp to image boundaries
    if min_x_px < 0:
        min_x_px = 0
        max_x_px = square_size
    if max_x_px > image_width:
        max_x_px = image_width
        min_x_px = image_width - square_size
    if min_y_px < 0:
        min_y_px = 0
        max_y_px = square_size
    if max_y_px > image_height:
        max_y_px = image_height
        min_y_px = image_height - square_size
    
    # Ensure we don't go negative
    min_x_px = max(0, min_x_px)
    min_y_px = max(0, min_y_px)
    
    # Crop image
    cropped = image[min_y_px:max_y_px, min_x_px:max_x_px]
    
    return cropped


class FactoryNode:
    node_label = 'Zoom'
    node_tag = 'Zoom'
    

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
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']


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
                    default_value='Input BGR image',
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
                dpg.add_slider_float(
                    tag=node.tag_node_input02_value_name,
                    label="width",
                    width=small_window_w - 80,
                    default_value=0.5,
                    min_value=node._width_min_val,
                    max_value=node._width_max_val,
                    callback=None,
                )
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label="center x",
                    width=small_window_w - 80,
                    default_value=0.5,
                    min_value=node._center_min_val,
                    max_value=node._center_max_val,
                    callback=None,
                )
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input04_value_name,
                    label="center y",
                    width=small_window_w - 80,
                    default_value=0.5,
                    min_value=node._center_min_val,
                    max_value=node._center_max_val,
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

    node_label = 'Zoom'
    node_tag = 'Zoom'

    _width_min_val = 0.01
    _width_max_val = 1.00
    _center_min_val = 0.0
    _center_max_val = 1.0

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
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']


        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            connection_tag = connection_info[1].split(':')[3]
            if connection_type == self.TYPE_FLOAT:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = round(float(dpg_get_value(source_tag)), 3)
                if connection_tag == 'Input02':
                    input_value = max([self._width_min_val, input_value])
                    input_value = min([self._width_max_val, input_value])
                if connection_tag == 'Input03' or connection_tag == 'Input04':
                    input_value = max([self._center_min_val, input_value])
                    input_value = min([self._center_max_val, input_value])
                dpg_set_value(destination_tag, input_value)

        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)


        width = float(dpg_get_value(input_value02_tag))
        center_x = float(dpg_get_value(input_value03_tag))
        center_y = float(dpg_get_value(input_value04_tag))
       

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        if frame is not None:
            frame = crop_from_center(frame, width, center_x, center_y)


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
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'


        width = float(dpg_get_value(input_value02_tag))
        center_x = float(dpg_get_value(input_value03_tag))
        center_y = float(dpg_get_value(input_value04_tag))

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = width
        setting_dict[input_value03_tag] = center_x
        setting_dict[input_value04_tag] = center_y

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'

        width = float(setting_dict[input_value02_tag])
        center_x = float(setting_dict[input_value03_tag])
        center_y = float(setting_dict[input_value04_tag])

        dpg_set_value(input_value02_tag, width)
        dpg_set_value(input_value03_tag, center_x)
        dpg_set_value(input_value04_tag, center_y)
