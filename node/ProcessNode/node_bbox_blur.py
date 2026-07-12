#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BBoxBlur – applies Gaussian blur inside every bounding box from a connected
Object Detection JSON output.

Typical usage
-------------
ObjectDetection (IMAGE output) ──► BBoxBlur (IMAGE input)
ObjectDetection (JSON output)  ──► BBoxBlur (JSON input)

The node reads bounding-box coordinates from the JSON input
(keys ``bboxes``, ``scores``, ``score_th``) and blurs each region whose
confidence score meets the threshold.  The result is useful for anonymizing
faces detected by the BlazeFace model.

When no JSON input is connected the node passes the image through unmodified.
"""

import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node


def _blur_bboxes(image: np.ndarray, bboxes, scores, score_th: float, kernel_size: int) -> np.ndarray:
    """Return a copy of *image* with each qualifying bbox region blurred."""
    result = image.copy()
    h, w = image.shape[:2]
    # Ensure kernel size is odd and at least 1
    k = max(1, int(kernel_size))
    if k % 2 == 0:
        k += 1

    for bbox, score in zip(bboxes, scores):
        if score < score_th:
            continue
        x1 = max(0, int(bbox[0]))
        y1 = max(0, int(bbox[1]))
        x2 = min(w, int(bbox[2]))
        y2 = min(h, int(bbox[3]))
        if x2 <= x1 or y2 <= y1:
            continue
        region = result[y1:y2, x1:x2]
        result[y1:y2, x1:x2] = cv2.GaussianBlur(region, (k, k), 0)

    return result


class FactoryNode:
    node_label = 'BBox Blur'
    node_tag = 'BBoxBlur'

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=None,
        opencv_setting_dict=None,
        callback=None,
    ):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(Node):  # noqa: F811
    _ver = '0.0.1'

    node_label = 'BBox Blur'
    node_tag = 'BBoxBlur'

    _min_kernel = 1
    _max_kernel = 151

    _opencv_setting_dict = None

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=None,
        opencv_setting_dict=None,
        callback=None,
    ):
        if pos is None:
            pos = [0, 0]

        tag_node_name = str(node_id) + ':' + self.node_tag
        self.tag_node_name = tag_node_name

        # ---- Input tags ------------------------------------------------
        tag_input_image_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01'
        tag_input_image_value = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'

        tag_input_json_name = tag_node_name + ':' + self.TYPE_JSON + ':Input02'
        tag_input_json_value = tag_node_name + ':' + self.TYPE_JSON + ':Input02Value'

        # ---- Output tags -----------------------------------------------
        tag_output_image_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01'
        tag_output_image_value = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'

        tag_output_time_name = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02'
        tag_output_time_value = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        # ---- Control tags ----------------------------------------------
        tag_kernel = tag_node_name + ':KernelValue'
        tag_score_th = tag_node_name + ':ScoreThValue'

        self._opencv_setting_dict = opencv_setting_dict
        small_window_w = opencv_setting_dict['process_width']
        small_window_h = opencv_setting_dict['process_height']
        use_pref_counter = opencv_setting_dict['use_pref_counter']

        # Black placeholder texture
        black_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        black_texture = self.convert_cv_to_dpg(black_image, small_window_w, small_window_h)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=tag_output_image_value,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
            tag=tag_node_name,
            parent=parent,
            label=self.node_label,
            pos=pos,
        ):
            # IMAGE input
            with dpg.node_attribute(
                tag=tag_input_image_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=tag_input_image_value,
                    default_value='Input Image',
                )

            # JSON input (bounding boxes)
            with dpg.node_attribute(
                tag=tag_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=tag_input_json_value,
                    default_value='Detections (JSON)',
                )

            # IMAGE output
            with dpg.node_attribute(
                tag=tag_output_image_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(tag_output_image_value)

            # Kernel size slider
            with dpg.node_attribute(
                tag=tag_node_name + ':KernelAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=tag_kernel,
                    label='kernel',
                    width=small_window_w - 80,
                    default_value=51,
                    min_value=self._min_kernel,
                    max_value=self._max_kernel,
                )

            # Score threshold slider
            with dpg.node_attribute(
                tag=tag_node_name + ':ScoreAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=tag_score_th,
                    label='score',
                    width=small_window_w - 80,
                    default_value=0.3,
                    min_value=0.0,
                    max_value=1.0,
                )

            # Elapsed time output
            if use_pref_counter:
                with dpg.node_attribute(
                    tag=tag_output_time_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=tag_output_time_value,
                        default_value='elapsed time(ms)',
                    )

        return self

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_output_image_value = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        tag_output_time_value = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        tag_kernel = tag_node_name + ':KernelValue'
        tag_score_th = tag_node_name + ':ScoreThValue'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        kernel_size = dpg_get_value(tag_kernel) or 51
        score_th = dpg_get_value(tag_score_th)
        if score_th is None:
            score_th = 0.3

        # ---- Resolve connections ----------------------------------------
        src_image_key = ''
        src_json_key = ''
        for conn in connection_list:
            conn_type = conn[0].split(':')[2]
            src_key = ':'.join(conn[0].split(':')[:2])
            if conn_type == self.TYPE_IMAGE and not src_image_key:
                src_image_key = src_key
            elif conn_type == self.TYPE_JSON and not src_json_key:
                src_json_key = src_key

        # ---- Fetch data -------------------------------------------------
        frame = node_image_dict.get(src_image_key, None) if src_image_key else None
        json_data = node_result_dict.get(src_json_key, None) if src_json_key else None

        if frame is None:
            return {'image': None, 'json': None, 'audio': None}

        if use_pref_counter:
            start_time = time.monotonic()

        # ---- Apply blur inside bounding boxes ---------------------------
        output_frame = frame
        if json_data and isinstance(json_data, dict):
            bboxes = json_data.get('bboxes', [])
            scores = json_data.get('scores', [])
            if bboxes and scores:
                output_frame = _blur_bboxes(frame, bboxes, scores, score_th, kernel_size)

        if use_pref_counter:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            dpg_set_value(tag_output_time_value, str(elapsed_ms).zfill(4) + 'ms')

        # ---- Update UI texture ------------------------------------------
        texture = self.convert_cv_to_dpg(output_frame, small_window_w, small_window_h)
        dpg_set_value(tag_output_image_value, texture)

        return {'image': output_frame, 'json': None, 'audio': None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_kernel = tag_node_name + ':KernelValue'
        tag_score_th = tag_node_name + ':ScoreThValue'

        pos = dpg.get_item_pos(tag_node_name)

        return {
            'ver': self._ver,
            'pos': pos,
            tag_kernel: dpg_get_value(tag_kernel),
            tag_score_th: dpg_get_value(tag_score_th),
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_kernel = tag_node_name + ':KernelValue'
        tag_score_th = tag_node_name + ':ScoreThValue'

        if tag_kernel in setting_dict:
            dpg_set_value(tag_kernel, int(setting_dict[tag_kernel]))
        if tag_score_th in setting_dict:
            dpg_set_value(tag_score_th, float(setting_dict[tag_score_th]))
