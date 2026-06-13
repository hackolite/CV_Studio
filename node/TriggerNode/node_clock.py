#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
from datetime import datetime

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


def _parse_hhmm(value):
    """Parse a HH:MM string and return (hour, minute), or None on error."""
    try:
        parts = value.strip().split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (ValueError, AttributeError):
        pass
    return None


def _in_interval(now_h, now_m, start_h, start_m, end_h, end_m):
    """
    Return True if (now_h, now_m) is within [start, end].
    Supports overnight intervals (e.g. 22:00 – 06:00).
    """
    now = now_h * 60 + now_m
    start = start_h * 60 + start_m
    end = end_h * 60 + end_m

    if start <= end:
        # Normal interval: e.g. 08:00 – 18:00
        return start <= now <= end
    else:
        # Overnight interval: e.g. 22:00 – 06:00
        return now >= start or now <= end


class FactoryNode:
    node_label = 'Clock'
    node_tag = 'Clock'

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

    node_label = 'Clock'
    node_tag = 'Clock'

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

        tag_debut_name = tag_node_name + ':debut'
        tag_debut_value_name = tag_node_name + ':debutValue'

        tag_fin_name = tag_node_name + ':fin'
        tag_fin_value_name = tag_node_name + ':finValue'

        tag_node_output01_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01Value'

        self._opencv_setting_dict = opencv_setting_dict
        small_window_w = self._opencv_setting_dict.get('process_width', 640)

        with dpg.node(
            tag=tag_node_name,
            parent=parent,
            label=self.node_label,
            pos=pos,
        ):
            # Debut (start time)
            with dpg.node_attribute(
                tag=tag_debut_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_debut_value_name,
                    label="debut (HH:MM)",
                    default_value="00:00",
                    width=80,
                    hint="HH:MM",
                )

            # Fin (end time)
            with dpg.node_attribute(
                tag=tag_fin_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_fin_value_name,
                    label="fin (HH:MM)",
                    default_value="23:59",
                    width=80,
                    hint="HH:MM",
                )

            # Output
            with dpg.node_attribute(
                tag=tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=tag_node_output01_value_name,
                    default_value='-- : --',
                )

        self.tag_node_name = tag_node_name
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
        tag_debut_value_name = tag_node_name + ':debutValue'
        tag_fin_value_name = tag_node_name + ':finValue'
        tag_output_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01Value'

        debut_str = dpg_get_value(tag_debut_value_name) or '00:00'
        fin_str = dpg_get_value(tag_fin_value_name) or '23:59'

        now = datetime.now()
        now_h, now_m = now.hour, now.minute

        start = _parse_hhmm(debut_str)
        end = _parse_hhmm(fin_str)

        active = False
        if start is not None and end is not None:
            active = _in_interval(now_h, now_m, start[0], start[1], end[0], end[1])

        status = 'ACTIF' if active else 'inactif'
        dpg_set_value(
            tag_output_value_name,
            f'{now_h:02d}:{now_m:02d}  [{status}]',
        )

        return {"image": None, "json": {"BOOL": active}, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_debut_value_name = tag_node_name + ':debutValue'
        tag_fin_value_name = tag_node_name + ':finValue'

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_debut_value_name] = dpg_get_value(tag_debut_value_name)
        setting_dict[tag_fin_value_name] = dpg_get_value(tag_fin_value_name)

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_debut_value_name = tag_node_name + ':debutValue'
        tag_fin_value_name = tag_node_name + ':finValue'

        debut = setting_dict.get(tag_debut_value_name, '00:00')
        fin = setting_dict.get(tag_fin_value_name, '23:59')

        dpg_set_value(tag_debut_value_name, debut)
        dpg_set_value(tag_fin_value_name, fin)
