#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import gc
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

    def add_node(self, parent, node_id, pos=[0, 0], opencv_setting_dict=None, callback=None):

        node = MjpegNode()

        node.tag_node_name = str(node_id) + ':' + node.node_tag

        node.tag_node_input01_value_name = node.tag_node_name + ':text:Input01Value'
        node.tag_node_output01_value_name = node.tag_node_name + ':image:Output01Value'
        node.tag_node_button_value_name = node.tag_node_name + ':text:ButtonValue'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':audio:OutputAudioValue'
        node.tag_node_output_json_value_name = node.tag_node_name + ':json:OutputJsonValue'

        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = opencv_setting_dict['input_window_width']
        node.small_window_h = opencv_setting_dict['input_window_height']

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

        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):

            with dpg.node_attribute():
                dpg.add_input_text(
                    tag=node.tag_node_input01_value_name,
                    label='URL',
                    width=node.small_window_w - 20,
                )

            with dpg.node_attribute():
                dpg.add_slider_int(
                    tag=node.tag_node_name + ':fps',
                    label='FPS',
                    default_value=10,
                    min_value=1,
                    max_value=30,
                    width=node.small_window_w - 20,
                )

            with dpg.node_attribute():
                dpg.add_image(node.tag_node_output01_value_name)

            with dpg.node_attribute():
                dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    callback=node._button,
                    user_data=node.tag_node_name,
                    width=node.small_window_w,
                )

        return node


class MjpegNode(Node):
    _ver = '0.0.1'
    _start_label = 'Start'
    _stop_label = 'Stop'

    def __init__(self):
        super().__init__()

        self._capture = {}
        self._last_frame = {}
        self._last_frame_time = {}
        self._is_streaming = {}

    def _open_capture(self, url):
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if cap is not None and cap.isOpened():
            return cap

        try:
            cap.release()
        except Exception:
            pass

        cap = cv2.VideoCapture(url)
        if cap is not None and cap.isOpened():
            return cap

        try:
            cap.release()
        except Exception:
            pass
        return None

    # -------------------------
    # START / STOP
    # -------------------------
    def _button(self, sender, app_data, user_data):

        node_id = user_data.split(':')[0]
        url_tag = user_data + ':text:Input01Value'
        button_tag = user_data + ':text:ButtonValue'

        label = dpg.get_item_label(button_tag)
        url = dpg_get_value(url_tag)

        if label == self._start_label:

            if url:
                cap = self._open_capture(url)
                if cap is not None:
                    self._capture[node_id] = cap
                    self._is_streaming[node_id] = True
                    dpg.set_item_label(button_tag, self._stop_label)
                    return
            self._is_streaming[node_id] = False
            dpg.set_item_label(button_tag, self._start_label)

        else:

            self._is_streaming[node_id] = False

            if node_id in self._capture:
                try:
                    self._capture[node_id].release()
                except:
                    pass
                del self._capture[node_id]

            dpg.set_item_label(button_tag, self._start_label)

    # -------------------------
    # UPDATE LOOP
    # -------------------------
    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):

        node_id = str(node_id)
        tag_node_name = node_id + ':' + self.node_tag

        if not self._is_streaming.get(node_id, False):
            return {'image': None, 'json': None, 'audio': None}

        cap = self._capture.get(node_id, None)
        if cap is None:
            return {'image': None, 'json': None, 'audio': None}

        # FPS control
        target_fps = dpg_get_value(tag_node_name + ':fps') or 10
        min_interval = 1.0 / target_fps

        now = time.monotonic()
        last_t = self._last_frame_time.get(node_id, 0)

        # cache frame
        if (now - last_t) < min_interval:
            frame = self._last_frame.get(node_id)
            return {'image': frame, 'json': None, 'audio': None}

        # -------------------------
        # READ FRAME SAFE
        # -------------------------
        ret, frame = False, None

        try:
            if cap.isOpened():
                ret, frame = cap.read()
        except Exception as e:
            print("[MJPEG] read error:", e)

        # -------------------------
        # RECONNECT
        # -------------------------
        if not ret or frame is None:

            url_tag = tag_node_name + ':text:Input01Value'
            url = dpg_get_value(url_tag)

            try:
                cap.release()
            except:
                pass

            gc.collect()
            time.sleep(0.3)

            new_cap = self._open_capture(url)
            if new_cap is not None:
                self._capture[node_id] = new_cap
            else:
                self._capture.pop(node_id, None)
                print("[MJPEG] reconnect failed")

            return {'image': self._last_frame.get(node_id), 'json': None, 'audio': None}

        # -------------------------
        # STORE FRAME
        # -------------------------
        self._last_frame[node_id] = frame
        self._last_frame_time[node_id] = now

        # convert for UI
        texture = self.convert_cv_to_dpg(
            frame,
            self.small_window_w,
            self.small_window_h
        )

        dpg_set_value(tag_node_name + ':image:Output01Value', texture)

        return {'image': frame, 'json': None, 'audio': None}

    # -------------------------
    # CLOSE
    # -------------------------
    def close(self, node_id):

        node_id = str(node_id)

        self._is_streaming.pop(node_id, None)

        cap = self._capture.pop(node_id, None)
        if cap:
            try:
                cap.release()
            except:
                pass

        self._last_frame.pop(node_id, None)
        self._last_frame_time.pop(node_id, None)
