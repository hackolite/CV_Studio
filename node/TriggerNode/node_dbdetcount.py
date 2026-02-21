#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DbDetCount – Delta-Based Detection Count trigger node.

Computes a rolling average (mean) of detection counts over a configurable
time window (in seconds).  Fires the trigger when the absolute difference
between the most-recent count and the rolling mean exceeds a user-defined
delta threshold.

  trigger = |current_count - rolling_mean| > delta
"""
import time
from collections import deque

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


class FactoryNode:
    node_label = 'DbDetCount'
    node_tag = 'DbDetCount'

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


class Node(BaseNode):
    _ver = '0.0.1'

    node_label = 'DbDetCount'
    node_tag = 'DbDetCount'

    _opencv_setting_dict = None

    def __init__(self):
        # Each entry is (timestamp, count) for one frame
        self._samples = deque()
        self._last_trigger = False

    # ------------------------------------------------------------------
    # GUI construction
    # ------------------------------------------------------------------

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
        tag_input01_name = tag_node_name + ':' + self.TYPE_JSON + ':Input01'
        tag_input01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Input01Value'
        tag_output01_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01'
        tag_output01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01Value'

        tag_window_name = tag_node_name + ':Window'
        tag_window_value_name = tag_node_name + ':WindowValue'
        tag_delta_name = tag_node_name + ':Delta'
        tag_delta_value_name = tag_node_name + ':DeltaValue'

        self._opencv_setting_dict = opencv_setting_dict
        small_window_w = self._opencv_setting_dict.get('process_width', 640)

        with dpg.node(
            tag=tag_node_name,
            parent=parent,
            label=self.node_label,
            pos=pos,
        ):
            # JSON input
            with dpg.node_attribute(
                tag=tag_input01_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=tag_input01_value_name,
                    default_value='Input detection JSON',
                )

            # Rolling-window duration in seconds
            with dpg.node_attribute(
                tag=tag_window_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_float(
                    tag=tag_window_value_name,
                    label='AverageMean (s)',
                    default_value=5.0,
                    min_value=0.1,
                    min_clamped=True,
                    width=small_window_w - 150,
                    format='%.1f',
                )

            # Delta threshold
            with dpg.node_attribute(
                tag=tag_delta_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_float(
                    tag=tag_delta_value_name,
                    label='Delta',
                    default_value=2.0,
                    min_value=0.0,
                    min_clamped=True,
                    width=small_window_w - 150,
                    format='%.2f',
                )

            # JSON output
            with dpg.node_attribute(
                tag=tag_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=tag_output01_value_name,
                    default_value='Output trigger JSON',
                )

        self.tag_node_name = tag_node_name
        return self

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_window_value = tag_node_name + ':WindowValue'
        tag_delta_value = tag_node_name + ':DeltaValue'
        tag_output_value = tag_node_name + ':' + self.TYPE_JSON + ':Output01Value'

        # Resolve upstream JSON source
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                parts = connection_info[0].split(':')[:2]
                connection_info_src = ':'.join(parts)
                break

        node_result = node_result_dict.get(connection_info_src, {})

        # Read parameters
        try:
            window_duration = float(dpg_get_value(tag_window_value))
            delta = float(dpg_get_value(tag_delta_value))
        except (ValueError, TypeError):
            window_duration = 5.0
            delta = 2.0

        current_time = time.time()

        # Count detections in this frame
        current_count = 0
        if node_result and isinstance(node_result, dict):
            class_ids = node_result.get('class_ids', [])
            if class_ids:
                current_count = len(class_ids)

        # Add the current sample
        self._samples.append((current_time, current_count))

        # Evict samples outside the rolling window
        cutoff = current_time - window_duration
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

        # Compute rolling mean (exclude the very last sample so that we
        # compare the current value against the *historical* mean)
        history = list(self._samples)[:-1]
        if history:
            rolling_mean = sum(c for _, c in history) / len(history)
        else:
            rolling_mean = float(current_count)

        # Fire trigger when deviation exceeds delta
        diff = abs(current_count - rolling_mean)
        trigger_active = diff > delta

        self._last_trigger = trigger_active

        # Build output JSON
        output_json = {
            'BOOL': trigger_active,
            'count': current_count,
            'mean': rolling_mean,
            'diff': diff,
            'delta': delta,
        }

        # Update display text
        state_str = 'Active' if trigger_active else 'Inactive'
        try:
            dpg_set_value(
                tag_output_value,
                f'Count:{current_count} Mean:{rolling_mean:.1f} '
                f'Diff:{diff:.1f} (Trigger:{state_str})',
            )
        except (SystemError, AttributeError):
            pass

        return {'image': None, 'json': output_json, 'audio': None}

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def close(self, node_id):
        self._samples.clear()

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_window_value = tag_node_name + ':WindowValue'
        tag_delta_value = tag_node_name + ':DeltaValue'

        pos = dpg.get_item_pos(tag_node_name)
        setting_dict = {
            'ver': self._ver,
            'pos': pos,
            tag_window_value: dpg_get_value(tag_window_value),
            tag_delta_value: dpg_get_value(tag_delta_value),
        }
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_window_value = tag_node_name + ':WindowValue'
        tag_delta_value = tag_node_name + ':DeltaValue'

        if tag_window_value in setting_dict:
            dpg_set_value(tag_window_value, float(setting_dict[tag_window_value]))
        if tag_delta_value in setting_dict:
            dpg_set_value(tag_delta_value, float(setting_dict[tag_delta_value]))
