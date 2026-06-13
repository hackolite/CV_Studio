#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import threading

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


class FactoryNode:
    node_label = 'MJPEG'
    node_tag = 'MJPEG'

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
        node = MjpegNode()

        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'

        node.tag_node_input_fps_name = node.tag_node_name + ':' + node.TYPE_INT + ':InputFps'
        node.tag_node_input_fps_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':InputFpsValue'

        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'

        node.tag_node_button_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Button'
        node.tag_node_button_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ButtonValue'

        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['input_window_width']
        node.small_window_h = node._opencv_setting_dict['input_window_height']
        node._small_window_w = node.small_window_w
        node._small_window_h = node.small_window_h

        black_image = np.zeros((node.small_window_h, node.small_window_w, 3))
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

        # Yellow theme for active/output buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))

        node.yellow_button_theme = yellow_button_theme

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # URL input
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=node.tag_node_input01_value_name,
                    label='URL',
                    width=node.small_window_w - 30,
                )

            # FPS slider
            with dpg.node_attribute(
                    tag=node.tag_node_input_fps_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input_fps_value_name,
                    label='FPS',
                    default_value=10,
                    min_value=1,
                    max_value=30,
                    width=node.small_window_w - 60,
                )

            # Image output
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Start/Stop button
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

            def add_yellow_disabled_button(label, tag):
                btn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node._small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                return btn

            with dpg.node_attribute(
                    tag=node.tag_node_output_audio_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                add_yellow_disabled_button('Audio', node.tag_node_output_audio_value_name)

            with dpg.node_attribute(
                    tag=node.tag_node_output_json_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                add_yellow_disabled_button('JSON', node.tag_node_output_json_value_name)

        return node


class MjpegNode(Node):
    _ver = '0.0.1'

    node_label = 'MJPEG'
    node_tag = 'MJPEG'

    _opencv_setting_dict = None
    _start_label = 'Start'
    _stop_label = 'Stop'

    def __init__(self):
        super().__init__()

        self._small_window_w = 240
        self._small_window_h = 135
        self.small_window_w = 240
        self.small_window_h = 135

        self._start_label = 'Start'
        self._stop_label = 'Stop'
        self.node_tag = 'MJPEG'
        self.node_label = 'MJPEG'

        self.yellow_button_theme = None

        # Per-instance streaming state (keyed by node_id string)
        self._capture = {}          # url -> cv2.VideoCapture
        self._last_frame = {}       # node_id -> last captured frame
        self._last_frame_time = {}  # node_id -> monotonic timestamp of last grab
        self._is_streaming = {}     # node_id -> bool
        self._frame_count = {}      # node_id -> int

    def _button(self, sender, data, user_data):
        tag_node_name = user_data
        input_url_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_button = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'
        node_id = tag_node_name.split(':')[0]

        label = dpg.get_item_label(tag_button)
        mjpeg_url = dpg_get_value(input_url_tag)

        if label == self._start_label:
            if mjpeg_url:
                cap = cv2.VideoCapture(mjpeg_url)
                self._capture[node_id] = cap
                self._last_frame[node_id] = None
                self._last_frame_time[node_id] = 0.0
                self._frame_count[node_id] = 0
                self._is_streaming[node_id] = True
            dpg.set_item_label(tag_button, self._stop_label)
        elif label == self._stop_label:
            self._is_streaming[node_id] = False
            if node_id in self._capture:
                try:
                    self._capture[node_id].release()
                except Exception:
                    pass
                del self._capture[node_id]
            self._last_frame.pop(node_id, None)
            self._last_frame_time.pop(node_id, None)
            self._frame_count.pop(node_id, None)
            dpg.set_item_label(tag_button, self._start_label)

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        input_fps_tag = tag_node_name + ':' + self.TYPE_INT + ':InputFpsValue'

        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']

        node_id_str = str(node_id)

        if not self._is_streaming.get(node_id_str, False):
            return {'image': None, 'json': None, 'audio': None}

        cap = self._capture.get(node_id_str)
        if cap is None:
            return {'image': None, 'json': None, 'audio': None}

        # FPS throttling: only grab a new frame when enough time has elapsed
        target_fps = dpg_get_value(input_fps_tag)
        try:
            target_fps = int(target_fps)
        except (TypeError, ValueError):
            target_fps = 10
        target_fps = max(1, min(30, target_fps))
        min_interval = 1.0 / target_fps

        now = time.monotonic()
        last_t = self._last_frame_time.get(node_id_str, 0.0)
        if (now - last_t) < min_interval:
            # Return cached frame without reading a new one
            frame = self._last_frame.get(node_id_str)
            return {'image': frame, 'json': None, 'audio': None}

        # Grab next frame from the MJPEG stream
        try:
            ret, frame = cap.read()
        except Exception:
            ret, frame = False, None

        if not ret or frame is None:
            # Try to reconnect
            url_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
            mjpeg_url = dpg_get_value(url_tag)
            try:
                cap.release()
            except Exception:
                pass
            try:
                new_cap = cv2.VideoCapture(mjpeg_url)
                self._capture[node_id_str] = new_cap
            except Exception:
                pass
            return {'image': self._last_frame.get(node_id_str), 'json': None, 'audio': None}

        self._last_frame[node_id_str] = frame
        self._last_frame_time[node_id_str] = now
        self._frame_count[node_id_str] = self._frame_count.get(node_id_str, 0) + 1

        texture = self.convert_cv_to_dpg(frame, small_window_w, small_window_h)
        dpg_set_value(output_value01_tag, texture)

        return {'image': frame, 'json': None, 'audio': None}

    def close(self, node_id):
        node_id_str = str(node_id)
        self._is_streaming.pop(node_id_str, None)
        cap = self._capture.pop(node_id_str, None)
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        self._last_frame.pop(node_id_str, None)
        self._last_frame_time.pop(node_id_str, None)
        self._frame_count.pop(node_id_str, None)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_url = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_fps = tag_node_name + ':' + self.TYPE_INT + ':InputFpsValue'

        pos = dpg.get_item_pos(tag_node_name)
        mjpeg_url = dpg_get_value(tag_url)
        fps = dpg_get_value(tag_fps)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_url] = mjpeg_url
        setting_dict[tag_fps] = fps

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_url = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_fps = tag_node_name + ':' + self.TYPE_INT + ':InputFpsValue'

        if tag_url in setting_dict:
            dpg_set_value(tag_url, setting_dict[tag_url])
        if tag_fps in setting_dict:
            dpg_set_value(tag_fps, setting_dict[tag_fps])
