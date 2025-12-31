#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import re
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


def image_process(image1, image2, alpha_val, beta_val, gamma_val):
    image1_height, image1_width = image1.shape[:2]
    image2 = cv2.resize(image2, (image1_width, image1_height))
    image = cv2.addWeighted(image1, alpha_val, image2, beta_val, gamma_val)
    return image

def create_image_dict(
    slot_num,
    connection_info_src_dict,
    node_image_dict,
    node_result_dict,
    image_node_name,
    resize_width,
    resize_height,
    draw_info_on_result,
):
    frame_exist_flag = False


    black_image = np.zeros((resize_height, resize_width, 3)).astype(np.uint8)

    frame_dict = {}
    for index in range(slot_num - 1, -1, -1):
        node_id_name = connection_info_src_dict.get(index, None)
        frame = copy.deepcopy(node_image_dict.get(node_id_name, None))
        if frame is not None:
            if draw_info_on_result:
                node_result = node_result_dict[node_id_name]
                image_node_name = node_id_name.split(':')[1]
                frame = draw_info(image_node_name, node_result, frame)
            resize_frame = cv2.resize(frame, (resize_width, resize_height))
            frame_dict[slot_num - index - 1] = copy.deepcopy(resize_frame)

            frame_exist_flag = True
        else:
            frame_dict[slot_num - index - 1] = copy.deepcopy(black_image)

    display_num_list = [1, 2, 4, 4, 6, 6, 9, 9, 9]
    for index in range(display_num_list[slot_num - 1]):
        if frame_dict.get(index, None) is None:
            frame_dict[index] = copy.deepcopy(black_image)

    if not frame_exist_flag:
        frame_dict = None

    return frame_dict


class FactoryNode:
    node_label = 'ImageAlphaBlend'
    node_tag = 'ImageAlphaBlend'
    

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
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input02Value'
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04Value'
        node.tag_node_input05_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input05'
        node.tag_node_input05_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input05Value'
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


        if node.tag_node_name not in node._slot_id:
            node._slot_id[node.tag_node_name] = 1


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
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Input BGR image',
                )

            

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            

            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label="alpha val",
                    width=small_window_w - 80,
                    default_value=node._alpha_default,
                    min_value=node._alpha_min,
                    max_value=node._alpha_max,
                    callback=None,
                )
            

            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input04_value_name,
                    label="beta val",
                    width=small_window_w - 80,
                    default_value=node._beta_default,
                    min_value=node._beta_min,
                    max_value=node._beta_max,
                    callback=None,
                )
            

            with dpg.node_attribute(
                    tag=node.tag_node_input05_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input05_value_name,
                    label="gamma val",
                    width=small_window_w - 80,
                    default_value=node._gamma_default,
                    min_value=node._gamma_min,
                    max_value=node._gamma_max,
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

    node_label = 'Image Alpha Blend'
    node_tag = 'ImageAlphaBlend'
    _max_slot_number = 2
    _slot_id = {}
    _alpha_min = 0.0
    _alpha_max = 1.0
    _alpha_default = 1.0
    _beta_min = 0.0
    _beta_max = 1.0
    _beta_default = 0.3
    _gamma_min = 0
    _gamma_max = 255 
    _gamma_default = 0

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
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_INT + ':Input05Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']
        draw_info_on_result = self._opencv_setting_dict['draw_info_on_result']


        frame = None
        frame1 = None
        frame2 = None
        node_name_dict = {}
        connection_info_src = ''
        connection_info_src_dict = {}
        for connection_info in connection_list:


            slot_number = re.sub(r'\D', '', connection_info[1].split(':')[-1])
            if slot_number == '':
                continue
            slot_number = int(slot_number) - 1
            connection_type = connection_info[0].split(':')[2]
            connection_tag = connection_info[1].split(':')[3]
            

            if connection_type == self.TYPE_FLOAT:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = round(float(dpg_get_value(source_tag)),3)
                if connection_tag == 'Input03':
                    input_value = max([self._alpha_min, input_value])
                    input_value = min([self._alpha_max, input_value])
                if connection_tag == 'Input04':
                    input_value = max([self._beta_min, input_value])
                    input_value = min([self._beta_max, input_value])
                dpg_set_value(destination_tag, input_value)
            

            if connection_type == self.TYPE_INT:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = int(dpg_get_value(source_tag))
                if connection_tag == 'Input05':
                    input_value = max([self._gamma_min, input_value])
                    input_value = min([self._gamma_max, input_value])
                dpg_set_value(destination_tag, input_value)
            

            if connection_type == self.TYPE_IMAGE:

                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                node_name = connection_info_src[1]
                connection_info_src = ':'.join(connection_info_src)
                node_name_dict[slot_number] = node_name
                connection_info_src_dict[slot_number] = connection_info_src



        if len(connection_info_src_dict) == 1:
            connected_first_slot_no = (next(iter(connection_info_src_dict)))
            frame1 = node_image_dict.get(connection_info_src_dict[connected_first_slot_no])
            frame = frame1
        if len(connection_info_src_dict) == 2:
            frame1 = node_image_dict.get(connection_info_src_dict[0])  
            frame2 = node_image_dict.get(connection_info_src_dict[1])
            frame = frame1


        alpha_val = float(dpg_get_value(input_value03_tag))
        beta_val = float(dpg_get_value(input_value04_tag))
        gamma_val = int(dpg_get_value(input_value05_tag))


        if frame is not None and use_pref_counter:
            start_time = time.monotonic()
        
        if len(connection_info_src_dict) == 2:
            if frame1 is not None and frame2 is not None:
                frame = image_process(frame1, frame2, alpha_val, beta_val, gamma_val)


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
        input_value03_tag = tag_node_name + ':' + self.TYPE_INT + ':Input03Value'

        kernel_size = dpg_get_value(input_value03_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value03_tag] = kernel_size

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value03_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'

        kernel_size = int(setting_dict[input_value03_tag])

        dpg_set_value(input_value03_tag, kernel_size)
