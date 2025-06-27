#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
#from node_editor.util import convert_cv_to_dpg
#from node.draw_node.draw_util.draw_util import draw_info
from node.basenode import Node

def image_process(
        image,
        text,
        elapsed_time_text,
        color=(0, 255, 0),
        thickness=2,
):
    pos_index = 0
    pos_list = [
        (15, 30),
        (15, 60),
    ]

    if text != '':
        image = cv2.putText(
            image,
            text,
            pos_list[pos_index],
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            color,
            thickness=thickness,
        )
        pos_index += 1
    if elapsed_time_text != '':
        image = cv2.putText(
            image,
            'Elapsed time: ' + elapsed_time_text,
            pos_list[pos_index],
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            thickness=thickness,
        )
        pos_index += 1
    return image



class FactoryNode:
    node_label = 'PutText'
    node_tag = 'PutText'
    

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
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Input03Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'

        node.tag_color_edit_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ColorEditValue'


        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']


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
                with dpg.group(horizontal=True):
                    dpg.add_input_text(
                        tag=node.tag_node_input02_value_name,
                        label='',
                        width=small_window_w - 30,
                    )
                    dpg.add_color_edit(
                        (0, 255, 0),
                        tag=node.tag_color_edit_value_name,
                        no_inputs=True,
                        no_alpha=True,
                    )

            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input03_value_name,
                    default_value='elapsed time(ms)',
                )

        return node

class Node(Node):
    _ver = '0.0.1'

    node_label = 'PutText'
    node_tag = 'PutText'

    _opencv_setting_dict = None

    def __init__(self):
        pass


    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Input03Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'

        tag_color_edit_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ColorEditValue'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        draw_info_on_result = self._opencv_setting_dict['draw_info_on_result']


        node_name = ''
        connection_info_src = ''
        connect_elapsed_time_flag = False
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_TEXT:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = dpg_get_value(source_tag)
                dpg_set_value(destination_tag, input_value)
            if connection_type == self.TYPE_TIME_MS:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = (dpg_get_value(source_tag))
                dpg_set_value(destination_tag, input_value)

                connect_elapsed_time_flag = True
            if connection_type == self.TYPE_IMAGE:

                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                node_name = connection_info_src[1]
                connection_info_src = ':'.join(connection_info_src)


        frame = node_image_dict.get(connection_info_src, None)
        if draw_info_on_result and connection_info_src != '':
            node_result = node_result_dict[connection_info_src]
            print(node_name)
            frame = self.draw_info(node_name, node_result, frame)


        text = dpg_get_value(input_value02_tag)
        color = dpg_get_value(tag_color_edit_value_name)[:3]
        color = (
            int(round(color[2], 0)),
            int(round(color[1], 0)),
            int(round(color[0], 0)),
        )
        elapsed_time_text = ''
        if connect_elapsed_time_flag:
            elapsed_time_text = dpg_get_value(input_value03_tag)

        if frame is not None:
            frame = image_process(frame, text, elapsed_time_text, color)


        if frame is not None:
            texture = self.convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image" : frame, "json" : None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        tag_color_edit_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ColorEditValue'

        text = dpg_get_value(input_value02_tag)
        color = dpg_get_value(tag_color_edit_value_name)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = text
        setting_dict[tag_color_edit_value_name] = color

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        tag_color_edit_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ColorEditValue'

        text = setting_dict[input_value02_tag]
        color = setting_dict[tag_color_edit_value_name]

        dpg_set_value(input_value02_tag, text)
        dpg_set_value(tag_color_edit_value_name, color)
