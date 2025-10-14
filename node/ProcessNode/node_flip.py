#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
#from node_editor.util import convert_cv_to_dpg
from node.basenode import Node

def image_process(image, hflip_flag, vflip_flag):
    flipcode = None
    if hflip_flag and vflip_flag:
        flipcode = 0
    elif hflip_flag:
        flipcode = 1
    elif vflip_flag:
        flipcode = -1

    if flipcode is not None:
        image = cv2.flip(image, flipcode)

    return image


class FactoryNode:
    node_label = 'Flip'
    node_tag = 'Flip'
    

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
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input03Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        
        # Audio tags
        node.tag_node_input_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':InputAudio'
        node.tag_node_input_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':InputAudioValue'
        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'


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

        # Audio texture registry
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output_audio_value_name,
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

            # Audio input
            with dpg.node_attribute(
                    tag=node.tag_node_input_audio_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_audio_value_name,
                    default_value='Input Audio Spectrogram',
                )

            # Audio output
            with dpg.node_attribute(
                    tag=node.tag_node_output_audio_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output_audio_value_name)



            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    label='Horizontal flip',
                    tag=node.tag_node_input02_value_name,
                    callback=None,
                    user_data=node.tag_node_name,
                    default_value=False,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    label='Vertical flip',
                    tag=node.tag_node_input03_value_name,
                    callback=None,
                    user_data=node.tag_node_name,
                    default_value=False,
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

    node_label = 'Flip'
    node_tag = 'Flip'

    _opencv_setting_dict = None

    def __init__(self):
        pass


    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict=None,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        tag_node_input03_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        output_audio_tag = tag_node_name + ':' + self.TYPE_AUDIO + ':OutputAudioValue'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Initialize node_audio_dict if not provided
        if node_audio_dict is None:
            node_audio_dict = {}


        connection_info_src = ''
        connection_info_audio = ''
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = connection_info_src.split(':')[:2]
            connection_info_src = ':'.join(connection_info_src)


        frame = node_image_dict.get(connection_info_src, None)
        audio_frame = node_audio_dict.get(connection_info_audio, None)


        hflip_flag = dpg_get_value(tag_node_input02_value_name)
        vflip_flag = dpg_get_value(tag_node_input03_value_name)


        if frame is not None and use_pref_counter:
            start_time = time.monotonic()


        # Process image
        if frame is not None:
            frame = image_process(frame, hflip_flag, vflip_flag)

        # Process audio (same algorithm as images)
        processed_audio = None
        if audio_frame is not None:
            processed_audio = image_process(audio_frame, frame, hflip_flag, vflip_flag)



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

        # Update audio texture
        if processed_audio is not None:
            texture = self.convert_cv_to_dpg(
                processed_audio,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_audio_tag, texture)

        return {"image":frame, "audio": processed_audio, "json":None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        tag_node_input03_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'

        pos = dpg.get_item_pos(tag_node_name)

        hflip_flag = dpg_get_value(tag_node_input02_value_name)
        vflip_flag = dpg_get_value(tag_node_input03_value_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_input02_value_name] = hflip_flag
        setting_dict[tag_node_input03_value_name] = vflip_flag

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        tag_node_input03_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'

        hflip_flag = setting_dict[tag_node_input02_value_name]
        vflip_flag = setting_dict[tag_node_input03_value_name]

        dpg_set_value(tag_node_input02_value_name, hflip_flag)
        dpg_set_value(tag_node_input03_value_name, vflip_flag)
