#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import pafy
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
#from node_editor.util import convert_cv_to_dpg

import threading
from threading import Lock

from node.basenode import Node



class YoutubeCapture(object):
    _frame = None
    _ret = None

    _lock = Lock()

    _video_capture = None
    _wait_interval = 5  # ms
    _prev_read_time = 0

    def __init__(self, rtsp_link):
        self._video_capture = cv2.VideoCapture(rtsp_link)

        thread = threading.Thread(
            target=self._youtube_read_thread,
            args=(self._video_capture, ),
            name="youtube_read_thread",
        )

        thread.daemon = True
        thread.start()

    def _youtube_read_thread(self, video_capture):
        while True:
            with self._lock:
                current_time = time.monotonic()
                interval_time = current_time - self._prev_read_time
                interval_time = int(interval_time * 1000)
                if interval_time > self._wait_interval:
                    self._ret, self._frame = video_capture.read()
                    self._prev_read_time = current_time

    def read(self):
        if (self._ret is not None) and (self._frame is not None):
            return self._ret, self._frame.copy()
        else:
            return self._ret, None

    def release(self):
        if self._video_capture is not None:
            self._video_capture.release()

    def set_interval(self, interval_time):
        self._wait_interval = interval_time



import numpy as np
import dearpygui.dearpygui as dpg

class Node:
    TYPE_TEXT = "Text"
    TYPE_INT = "Int"
    TYPE_IMAGE = "Image"
    TYPE_TIME_MS = "TimeMs"
    TYPE_AUDIO = "Audio"
    TYPE_JSON = "Json"
    TYPE_FLOAT = "Float"
    
    def __init__(self):
        self._min_val = 1
        self._max_val = 1000
        self._start_label = "Start"
        self.node_tag = "WebRTC"
        self.node_label = "WebRTC"
        
    def convert_cv_to_dpg(self, cv_img, w, h):
        return (np.zeros(w * h * 3, dtype=np.float32)).tobytes()
    
    def _button(self, sender, app_data, user_data):
        print(f"Button clicked for {user_data}")

class FactoryNode:
    node_label = 'WebRTC'
    node_tag = 'WebRTC'

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
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'

        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02Value'

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

        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloat'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloatValue'

        node.tag_node_output_type_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':OutputType'
        node.tag_node_output_type_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':OutputTypeValue'

        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['input_window_width']
        node.small_window_h = node._opencv_setting_dict['input_window_height']
        use_pref_counter = node._opencv_setting_dict.get('use_pref_counter', False)

        black_image = np.zeros((node.small_window_w, node.small_window_h, 3), dtype=np.uint8)
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
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255)) # Light yellow on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))   # Darker yellow on press

		
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
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input02_value_name,
                    label="Interval(ms)",
                    width=node.small_window_w - 110,
                    default_value=33,
                    min_value=node._min_val,
                    max_value=node._max_val,
                    callback=None,
                )

            # Add dropdown for output type selection
            with dpg.node_attribute(
                    tag=node.tag_node_output_type_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_output_type_value_name,
                    items=["Image", "Float", "Audio", "JSON"],
                    label="Output Type",
                    default_value="Image",
                    width=node.small_window_w - 80,
                )

            # Bouton Start avec thème jaune
            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn_start = dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node.small_window_w,
                    callback=node._button,
                    user_data=node.tag_node_name,
                )
                dpg.bind_item_theme(btn_start, yellow_button_theme)

            # Outputs audio, json, float, elapsed time as disabled yellow buttons
            def add_yellow_disabled_button(label, tag):
                btn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node.small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                return btn

            #with dpg.node_attribute(tag=node.tag_node_output02_name, attribute_type=dpg.mvNode_Attr_Output):
            #    add_yellow_disabled_button("Elapsed time (ms)", node.tag_node_output02_value_name)

            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)

            with dpg.node_attribute(tag=node.tag_node_output_float_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("Float", node.tag_node_output_float_value_name)

        return node



class Node(Node):
    _ver = '0.0.1'

    node_label = 'WebRTC'
    node_tag = 'WebRTC'

    _opencv_setting_dict = None
    _start_label = 'Start'
    _stop_label = 'Stop'
    _loading_label = 'Loading...'

    _min_val = 1
    _max_val = 200

    _youtube_capture = {}
    _prev_read_time = {}

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
        input_value01_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']


        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_INT:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = int(dpg_get_value(source_tag))
                input_value = max([self._min_val, input_value])
                input_value = min([self._max_val, input_value])
                dpg_set_value(destination_tag, input_value)

        # YouTube URL
        youtube_url = dpg_get_value(input_value01_tag)
        # Interval time
        wait_interval = dpg_get_value(input_value02_tag)

        # VideoCapture()
        youtube_capture = None
        if youtube_url != '':
            if youtube_url in self._youtube_capture:
                youtube_capture = self._youtube_capture[youtube_url]


        if youtube_url != '' and use_pref_counter:
            start_time = time.monotonic()


        frame = None
        if youtube_capture is not None:
            ret = False

            if youtube_url not in self._prev_read_time:
                ret, frame = youtube_capture.read()
            else:
                youtube_capture.set_interval(wait_interval)
                ret, frame = youtube_capture.read()

            if not ret:
                return None, None

            self._prev_read_time[youtube_url] = start_time


        if youtube_url != '' and use_pref_counter:
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

        return frame, None

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        tag_node_output_type_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':OutputTypeValue'

        pos = dpg.get_item_pos(tag_node_name)
        youtube_url = dpg_get_value(tag_node_input01_value_name)
        interval_time = dpg_get_value(tag_node_input02_value_name)
        output_type = dpg_get_value(tag_node_output_type_value_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_input01_value_name] = youtube_url
        setting_dict[tag_node_input02_value_name] = interval_time
        setting_dict[tag_node_output_type_value_name] = output_type

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        tag_node_output_type_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':OutputTypeValue'

        youtube_url = setting_dict[tag_node_input01_value_name]
        interval_time = setting_dict[tag_node_input02_value_name]
        output_type = setting_dict.get(tag_node_output_type_value_name, "Image")

        dpg_set_value(tag_node_input01_value_name, youtube_url)
        dpg_set_value(tag_node_input02_value_name, interval_time)
        dpg_set_value(tag_node_output_type_value_name, output_type)

    def _button(self, sender, data, user_data):
        tag_node_name = user_data
        input_value01_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)


        youtube_url = dpg_get_value(input_value01_tag)

        if label == self._start_label:
            if youtube_url != '':
                if not (youtube_url in self._youtube_capture):
                    dpg.set_item_label(tag_node_button_value_name,
                                       self._loading_label)

                    pafy_video = pafy.new(youtube_url)
                    pafy_best_video = pafy_video.getbest(preftype="mp4")
                    youtube_capture = YoutubeCapture(pafy_best_video.url)
                    self._youtube_capture[youtube_url] = youtube_capture

                    dpg.set_item_label(tag_node_button_value_name,
                                       self._stop_label)
        elif label == self._stop_label:
            if youtube_url != '':
                if youtube_url in self._youtube_capture:
                    self._youtube_capture[youtube_url].release()
                    del self._youtube_capture[youtube_url]

            dpg.set_item_label(tag_node_button_value_name, self._start_label)
