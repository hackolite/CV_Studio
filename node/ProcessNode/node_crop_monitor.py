#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node

def crop_and_get_info(image, min_x, max_x, min_y, max_y):
    """Crop image and calculate monitoring information"""
    if max_x < min_x:
        max_x = min_x + 0.01
    if max_y < min_y:
        max_y = min_y + 0.01

    image_height, image_width = image.shape[0], image.shape[1]
    
    # Convert normalized coordinates to pixel coordinates
    min_x_ = int(min_x * image_width)
    max_x_ = int(max_x * image_width)
    min_y_ = int(min_y * image_height)
    max_y_ = int(max_y * image_height)
    
    # Crop image
    cropped = image[min_y_:max_y_, min_x_:max_x_]
    
    # Calculate monitoring info
    width_pixels = max_x_ - min_x_
    height_pixels = max_y_ - min_y_
    center_x = min_x_ + width_pixels // 2
    center_y = min_y_ + height_pixels // 2
    
    return cropped, width_pixels, height_pixels, center_x, center_y


class FactoryNode:
    node_label = 'Crop Monitor'
    node_tag = 'CropMonitor'
    

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
        node.tag_node_input05_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input05'
        node.tag_node_input05_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input05Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        # Monitoring text outputs
        node.tag_node_info_width_name = node.tag_node_name + ':InfoWidth'
        node.tag_node_info_height_name = node.tag_node_name + ':InfoHeight'
        node.tag_node_info_center_name = node.tag_node_name + ':InfoCenter'

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
                    label="min x",
                    width=small_window_w - 80,
                    default_value=0,
                    min_value=node._min_min_val,
                    max_value=node._min_max_val,
                    callback=None,
                )
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label="max x",
                    width=small_window_w - 80,
                    default_value=1.0,
                    min_value=node._max_min_val,
                    max_value=node._max_max_val,
                    callback=None,
                )
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input04_value_name,
                    label="min y",
                    width=small_window_w - 80,
                    default_value=0,
                    min_value=node._min_min_val,
                    max_value=node._min_max_val,
                    callback=None,
                )
            with dpg.node_attribute(
                    tag=node.tag_node_input05_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input05_value_name,
                    label="max y",
                    width=small_window_w - 80,
                    default_value=1.0,
                    min_value=node._max_min_val,
                    max_value=node._max_max_val,
                    callback=None,
                )

            # Monitoring information display
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_info_width_name,
                    default_value='Width: 0 px',
                )
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_info_height_name,
                    default_value='Height: 0 px',
                )
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_info_center_name,
                    default_value='Center: (0, 0)',
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

    node_label = 'Crop Monitor'
    node_tag = 'CropMonitor'

    _min_min_val = 0.0
    _min_max_val = 0.99
    _max_min_val = 0.01
    _max_max_val = 1.00

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
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        
        info_width_tag = tag_node_name + ':InfoWidth'
        info_height_tag = tag_node_name + ':InfoHeight'
        info_center_tag = tag_node_name + ':InfoCenter'

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
                if connection_tag == 'Input02' or connection_tag == 'Input04':
                    input_value = max([self._min_min_val, input_value])
                    input_value = min([self._min_max_val, input_value])
                if connection_tag == 'Input03' or connection_tag == 'Input05':
                    input_value = max([self._max_min_val, input_value])
                    input_value = min([self._max_max_val, input_value])
                dpg_set_value(destination_tag, input_value)

        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)


        min_x = float(dpg_get_value(input_value02_tag))
        max_x = float(dpg_get_value(input_value03_tag))
        min_y = float(dpg_get_value(input_value04_tag))
        max_y = float(dpg_get_value(input_value05_tag))
       

        if min_x > max_x:
            min_x, max_x = max_x - 0.01, min_x + 0.01
            dpg_set_value(input_value02_tag, min_x)
            dpg_set_value(input_value03_tag, max_x)
        if min_y > max_y:
            min_y, max_y = max_y - 0.01, min_y + 0.01
            dpg_set_value(input_value04_tag, min_y)
            dpg_set_value(input_value05_tag, max_y)


        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        if frame is not None:
            frame, width_px, height_px, center_x, center_y = crop_and_get_info(
                frame, min_x, max_x, min_y, max_y
            )
            
            # Update monitoring information
            dpg_set_value(info_width_tag, f'Width: {width_px} px')
            dpg_set_value(info_height_tag, f'Height: {height_px} px')
            dpg_set_value(info_center_tag, f'Center: ({center_x}, {center_y})')


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
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'


        min_x = float(dpg_get_value(input_value02_tag))
        max_x = float(dpg_get_value(input_value03_tag))
        min_y = float(dpg_get_value(input_value04_tag))
        max_y = float(dpg_get_value(input_value05_tag))

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = min_x
        setting_dict[input_value03_tag] = max_x
        setting_dict[input_value04_tag] = min_y
        setting_dict[input_value05_tag] = max_y

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'

        min_x = float(setting_dict[input_value02_tag])
        max_x = float(setting_dict[input_value03_tag])
        min_y = float(setting_dict[input_value04_tag])
        max_y = float(setting_dict[input_value05_tag])

        dpg_set_value(input_value02_tag, min_x)
        dpg_set_value(input_value03_tag, max_x)
        dpg_set_value(input_value04_tag, min_y)
        dpg_set_value(input_value05_tag, max_y)
