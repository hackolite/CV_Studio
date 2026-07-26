#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Trajectory node: receives tracking data from a MultiObjectTracking node and
draws the trajectory (history of centre-point positions) of each tracked ID.
A COCO-class filter lets the user restrict drawing to one class of interest.
"""
import copy
import time
from collections import deque

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── COCO-80 class names (index 0 = "person", …, 79 = "toothbrush") ──────────
COCO_CLASSES = [
    'All classes',        # sentinel: no filter
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train',
    'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag',
    'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
    'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
    'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon',
    'bowl', 'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot',
    'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant',
    'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
    'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush',
]

# COCO class_id is 0-indexed (person=0).  Build a lookup: name -> id.
# (index 0 in COCO_CLASSES is 'All classes', which is not a real COCO id)
_COCO_NAME_TO_ID = {name: idx - 1 for idx, name in enumerate(COCO_CLASSES) if idx > 0}

_DEFAULT_MAX_LEN = 60       # history length (frames)
_COLOR_CYCLE_MODULO = 100   # cycle track-ID colours over this many slots


class FactoryNode:
    node_label = 'Trajectory'
    node_tag = 'Trajectory'

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

        # ── input ports ──────────────────────────────────────────────────────
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'

        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'

        # ── static controls ──────────────────────────────────────────────────
        node.tag_node_class_filter_name = node.tag_node_name + ':ClassFilter'
        node.tag_node_class_filter_value_name = node.tag_node_name + ':ClassFilterValue'

        node.tag_node_max_len_name = node.tag_node_name + ':' + node.TYPE_INT + ':MaxLen'
        node.tag_node_max_len_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':MaxLenValue'

        node.tag_node_thickness_name = node.tag_node_name + ':Thickness'
        node.tag_node_thickness_value_name = node.tag_node_name + ':ThicknessValue'

        # ── output ports ─────────────────────────────────────────────────────
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'

        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node.tag_node_output03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        black_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        black_texture = node.convert_cv_to_dpg(black_image, small_window_w, small_window_h)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Yellow theme for JSON output button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Image input
            with dpg.node_attribute(
                tag=node.tag_node_input01_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Image',
                )

            # JSON input (tracker data)
            with dpg.node_attribute(
                tag=node.tag_node_input02_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='JSON Tracker',
                )

            # Image output
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(default_value='Image')
                dpg.add_image(node.tag_node_output01_value_name)

            # COCO class filter combo
            with dpg.node_attribute(
                tag=node.tag_node_class_filter_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    COCO_CLASSES,
                    default_value=COCO_CLASSES[0],
                    label='Class filter',
                    width=small_window_w,
                    tag=node.tag_node_class_filter_value_name,
                )

            # Max history length slider
            with dpg.node_attribute(
                tag=node.tag_node_max_len_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_max_len_value_name,
                    label='History (frames)',
                    width=small_window_w - 80,
                    default_value=_DEFAULT_MAX_LEN,
                    min_value=5,
                    max_value=500,
                )

            # Line thickness slider
            with dpg.node_attribute(
                tag=node.tag_node_thickness_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_thickness_value_name,
                    label='Line thickness',
                    width=small_window_w - 80,
                    default_value=2,
                    min_value=1,
                    max_value=10,
                )

            # Elapsed time output
            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output02_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

            # JSON output (pass-through)
            with dpg.node_attribute(
                tag=node.tag_node_output03_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(default_value='JSON')
                btn = dpg.add_button(
                    label='Trajectory Data',
                    tag=node.tag_node_output03_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'Trajectory'
    node_tag = 'Trajectory'

    _opencv_setting_dict = None

    # Per-node trajectory history: {node_id: {track_id: deque([(cx, cy), …])}}
    _trajectories = {}

    def __init__(self):
        pass

    # ── helpers ───────────────────────────────────────────────────────────────

    def _class_matches(self, class_id, class_names, selected_class):
        """Return True if the detection belongs to the selected COCO class."""
        if selected_class == 'All classes':
            return True
        target_id = _COCO_NAME_TO_ID.get(selected_class, -1)
        if target_id < 0:
            return True
        # Primary check: numeric class_id
        if int(class_id) == target_id:
            return True
        # Secondary check: compare class name string (handles non-standard id offsets)
        name = self.get_class_name(int(class_id), class_names).lower()
        return name == selected_class.lower()

    def _draw_trajectories(self, image, node_id_str, thickness):
        """Draw all stored trajectory polylines onto *image* (modifies in-place)."""
        traj_dict = self._trajectories.get(node_id_str, {})
        for tid, points in traj_dict.items():
            pts = list(points)
            if len(pts) < 2:
                continue
            color = self.get_color(tid % _COLOR_CYCLE_MODULO)
            for i in range(1, len(pts)):
                cv2.line(image, pts[i - 1], pts[i], color, thickness=thickness)
        return image

    # ── update ────────────────────────────────────────────────────────────────

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_image_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_time_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        class_filter_tag = tag_node_name + ':ClassFilterValue'
        max_len_tag = tag_node_name + ':' + self.TYPE_INT + ':MaxLenValue'
        thickness_tag = tag_node_name + ':ThicknessValue'

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']
        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']

        # ── read UI parameters ───────────────────────────────────────────────
        selected_class = dpg_get_value(class_filter_tag) or 'All classes'
        max_len = dpg_get_value(max_len_tag)
        max_len = int(max_len) if max_len is not None else _DEFAULT_MAX_LEN
        thickness = dpg_get_value(thickness_tag)
        thickness = int(thickness) if thickness is not None else 2

        # ── resolve connections ──────────────────────────────────────────────
        image_src = ''
        json_src = ''
        for connection_info in connection_list:
            conn_type = connection_info[0].split(':')[2]
            if conn_type == self.TYPE_IMAGE:
                image_src = ':'.join(connection_info[0].split(':')[:2])
            elif conn_type in (self.TYPE_JSON, 'JSON'):
                json_src = ':'.join(connection_info[0].split(':')[:2])

        frame = node_image_dict.get(image_src, None) if image_src else None
        json_data = node_result_dict.get(json_src, None) if json_src else None

        if use_pref_counter and frame is not None:
            start_time = time.monotonic()

        node_id_str = str(node_id)
        if node_id_str not in self._trajectories:
            self._trajectories[node_id_str] = {}

        traj_dict = self._trajectories[node_id_str]

        # ── update trajectory histories ──────────────────────────────────────
        if json_data and isinstance(json_data, dict):
            track_ids = json_data.get('track_ids', [])
            bboxes = json_data.get('bboxes', [])
            class_ids = json_data.get('class_ids', [])
            class_names = json_data.get('class_names', [])

            for tid, bbox, cid in zip(track_ids, bboxes, class_ids):
                if not self._class_matches(cid, class_names, selected_class):
                    continue
                x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                if tid not in traj_dict:
                    traj_dict[tid] = deque(maxlen=max_len)
                else:
                    # Resize history if max_len changed
                    if traj_dict[tid].maxlen != max_len:
                        traj_dict[tid] = deque(traj_dict[tid], maxlen=max_len)
                traj_dict[tid].append((cx, cy))

        output_frame = None
        if frame is not None:
            debug_frame = copy.deepcopy(frame)
            debug_frame = self._draw_trajectories(debug_frame, node_id_str, thickness)
            output_frame = debug_frame
            texture = self.convert_cv_to_dpg(debug_frame, small_window_w, small_window_h)
            dpg_set_value(output_image_tag, texture)

        if use_pref_counter and frame is not None:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            try:
                dpg_set_value(output_time_tag, str(elapsed_ms).zfill(4) + 'ms')
            except Exception:
                pass

        return {'image': output_frame, 'json': json_data or {}, 'audio': None}

    def close(self, node_id):
        self._trajectories.pop(str(node_id), None)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        class_filter_tag = tag_node_name + ':ClassFilterValue'
        max_len_tag = tag_node_name + ':' + self.TYPE_INT + ':MaxLenValue'
        thickness_tag = tag_node_name + ':ThicknessValue'
        try:
            pos = dpg.get_item_pos(tag_node_name)
        except Exception:
            pos = [0, 0]
        setting_dict = {
            'ver': self._ver,
            'pos': pos,
            'class_filter': dpg_get_value(class_filter_tag) or 'All classes',
            'max_len': dpg_get_value(max_len_tag) or _DEFAULT_MAX_LEN,
            'thickness': dpg_get_value(thickness_tag) or 2,
        }
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        class_filter_tag = tag_node_name + ':ClassFilterValue'
        max_len_tag = tag_node_name + ':' + self.TYPE_INT + ':MaxLenValue'
        thickness_tag = tag_node_name + ':ThicknessValue'
        try:
            dpg_set_value(class_filter_tag, setting_dict.get('class_filter', 'All classes'))
            dpg_set_value(max_len_tag, int(setting_dict.get('max_len', _DEFAULT_MAX_LEN)))
            dpg_set_value(thickness_tag, int(setting_dict.get('thickness', 2)))
        except Exception:
            pass
