#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import multiprocessing as mp

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
#from node_editor.util import convert_cv_to_dpg
from node.basenode import Node



class FactoryNode:
    node_label = 'RTSP'
    node_tag = 'RTSP'
    

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


        node = RtspNode()
        
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node.tag_node_button_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Button'
        node.tag_node_button_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ButtonValue'


        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        node.tag_node_queue_info_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":QueueInfo"
        )
        node.tag_node_queue_info_value_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":QueueInfoValue"
        )






        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['input_window_width']
        node.small_window_h = node._opencv_setting_dict['input_window_height']
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

        
        # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))          # Yellow background
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255)) # Yellow on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))   # Yellow on press



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
                dpg.add_input_text(
                    tag=node.tag_node_input01_value_name,
                    label='URL',
                    width=node.small_window_w - 30,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node.small_window_w,
                    callback=node._button,
                    user_data=node.tag_node_name,
                )



            # Outputs audio, json, float, elapsed time as disabled yellow buttons
            def add_yellow_disabled_button(label, tag):
                btn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node._small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                return btn


            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)

            # Queue size information label
            with dpg.node_attribute(
                tag=node.tag_node_queue_info_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_queue_info_value_name,
                    default_value="Queue: Image=0/0 Audio=0/0",
                )
        
        return node






def receive_image_process(rtsp_url, image_queue, request):
    rtsp_capture = cv2.VideoCapture(rtsp_url)

    while True:
        ret, frame = rtsp_capture.read()

        if ret:
            if image_queue.qsize() == 0:
                image_queue.put(frame)
            time.sleep(0.001)
        else:
            time.sleep(1)
            rtsp_capture.release()
            rtsp_capture = cv2.VideoCapture(rtsp_url)


        if request.value == 0:
            rtsp_capture.release()
            break


class RtspNode(Node):
    _ver = '0.0.1'

    node_label = 'Rtsp'
    node_tag = 'Rtsp'

    _opencv_setting_dict = None
    _start_label = 'Start'
    _stop_label = 'Stop'

    _rtsp_capture = {}

    _image_queue = {}
    _request = {}
    _process = {}

    def __init__(self):
        super().__init__()  # Call parent constructor
        self._min_val = 1
        self._max_val = 1000

        self._small_window_w = 240
        self._small_window_h = 135

        self._start_label = "Start"
        self._stop_label  = "Stop"
        
        self.node_tag = "Rtsp"
        self.node_label = "Rtsp"
        

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']


        use_mp = self._opencv_setting_dict['use_multiprocessing_rtsp']


        rtsp_url = dpg_get_value(input_value01_tag)


        rtsp_capture = None
        image_queue = None
        if rtsp_url != '':
            if use_mp:
                # multiprocessing
                if rtsp_url in self._image_queue:
                    image_queue = self._image_queue[rtsp_url]
            else:
                # multiprocessing
                if rtsp_url in self._rtsp_capture:
                    rtsp_capture = self._rtsp_capture[rtsp_url]


        if rtsp_url != '' and use_pref_counter:
            start_time = time.monotonic()


        frame = None
        if use_mp:
            # multiprocessing
            if image_queue is not None:
                num = image_queue.qsize()
                if num > 0:
                    frame = image_queue.get()
        else:
            # multiprocessing
            if rtsp_capture is not None:
                ret, frame = rtsp_capture.read()
                if not ret:
                    return {"image": None, "json": None, "audio": None}


        if rtsp_url != '' and use_pref_counter:
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

        # Update queue size information label
        self.update_queue_info_display(tag_node_name, node_image_dict, node_audio_dict)

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        # multiprocessing
        use_mp = self._opencv_setting_dict['use_multiprocessing_rtsp']
        if use_mp:
            # multiprocessing
            for rtsp_url in self._process.keys():
                self._request[rtsp_url].value = 0
                if self._process[rtsp_url].is_alive():
                    self._process[rtsp_url].terminate()

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'

        pos = dpg.get_item_pos(tag_node_name)
        rtsp_url = dpg_get_value(tag_node_input01_value_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_input01_value_name] = rtsp_url

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'

        rtsp_url = setting_dict[tag_node_input01_value_name]

        dpg_set_value(tag_node_input01_value_name, rtsp_url)

    def _button(self, sender, data, user_data):
        tag_node_name = user_data
        input_value01_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)

        # RTSP URL
        rtsp_url = dpg_get_value(input_value01_tag)

        # multiprocessing
        use_mp = self._opencv_setting_dict['use_multiprocessing_rtsp']

        if label == self._start_label:
            if rtsp_url != '':
                if use_mp:
                    # multiprocessing
                    if not (rtsp_url in self._process):
                        self._image_queue[rtsp_url] = mp.Queue(maxsize=1)
                        self._request[rtsp_url] = mp.Value('i', 1)
                        self._process[rtsp_url] = mp.Process(
                            target=receive_image_process,
                            args=(rtsp_url, self._image_queue[rtsp_url],
                                  self._request[rtsp_url]),
                        )
                        self._process[rtsp_url].start()
                else:
                    # multiprocessing
                    if not (rtsp_url in self._rtsp_capture):
                        rtsp_capture = cv2.VideoCapture(rtsp_url)
                        self._rtsp_capture[rtsp_url] = rtsp_capture

            dpg.set_item_label(tag_node_button_value_name, self._stop_label)
        elif label == self._stop_label:
            if rtsp_url != '':
                if use_mp:
                    # multiprocessing
                    if rtsp_url in self._request:
                        self._request[rtsp_url].value = 0
                        if self._process[rtsp_url].is_alive():
                            self._process[rtsp_url].terminate()
                        self._image_queue.pop(rtsp_url)
                        self._request.pop(rtsp_url)
                        self._process.pop(rtsp_url)
                else:
                    # multiprocessing
                    if rtsp_url in self._rtsp_capture:
                        self._rtsp_capture[rtsp_url].release()
                        self._rtsp_capture.pop(rtsp_url)

            dpg.set_item_label(tag_node_button_value_name, self._start_label)
