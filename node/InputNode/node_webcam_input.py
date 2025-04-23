#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import numpy as np
import dearpygui.dearpygui as dpg


from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
#from node_editor.util import self.convert_cv_to_dpg




class FactoryNode:
    node_label = 'WebCam'
    node_tag = 'WebCam'
    

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
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input01Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'


        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['input_window_width']
        node.small_window_h = node._opencv_setting_dict['input_window_height']
        device_no_list = node._opencv_setting_dict['device_no_list']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        black_image = np.zeros((node.small_window_w, node.small_window_h, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            node.small_window_w,
            node.small_window_h,
        )


        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                node.small_window_w,
                node.small_window_h,
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
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    device_no_list,
                    width=node.small_window_w - 100,
                    label="Device No",
                    tag=node.tag_node_input01_value_name,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

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

    node_label = 'WebCam'
    node_tag = 'WebCam'

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
        input_value01_tag = tag_node_name + ':' + self.TYPE_INT + ':Input01Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        device_no_list = self._opencv_setting_dict['device_no_list']
        camera_capture_list = self._opencv_setting_dict['camera_capture_list']
        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']


        camera_no = dpg_get_value(input_value01_tag)


        camera_capture = None
        if camera_no != '':
            camera_no = int(camera_no)
            camera_index = device_no_list.index(camera_no)
            camera_capture = camera_capture_list[camera_index]


        if camera_no != '' and use_pref_counter:
            start_time = time.perf_counter()


        frame = None
        if camera_capture is not None:
            ret, frame = camera_capture.read()
            if not ret:
                return


        if camera_no != '' and use_pref_counter:
            elapsed_time = time.perf_counter() - start_time
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

        return frame, None

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
