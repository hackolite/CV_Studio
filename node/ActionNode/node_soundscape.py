#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Soundscape node — receives Super JSON from Agent and extracts its action."""

import json
import os

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

_TOOL_TEMPLATE = {
    'tool_name': 'Soundscape',
    'description': 'Plays one or more ambient sound tracks from a library.',
    'parameters': {
        'enabled': 'boolean',
        'tracks': 'list[string]  # list of soundscape IDs from the library',
        'volume': 'float  # 0.0 to 1.0',
    },
}

_LIB_PATH = os.path.join(os.path.dirname(__file__), 'soundscape_library.json')


def _load_library():
    try:
        with open(_LIB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('soundscapes', [])
    except Exception:
        return []


class FactoryNode:
    node_label = 'Soundscape'
    node_tag = 'Soundscape'

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(BaseNode):
    _ver = '0.0.1'
    node_label = 'Soundscape'
    node_tag = 'Soundscape'

    def __init__(self):
        self._opencv_setting_dict = {}
        self._last_output = {}
        self._library = []

    def get_tool_template(self):
        lib_ids = [s['id'] for s in self._library]
        tmpl = dict(_TOOL_TEMPLATE)
        tmpl['available_track_ids'] = lib_ids
        return tmpl

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        self._opencv_setting_dict = opencv_setting_dict or {}
        w = self._opencv_setting_dict.get('process_width', 280)
        self._library = _load_library()

        tag = str(node_id) + ':' + self.node_tag
        self.tag_node_name = tag

        tag_in      = tag + ':' + self.TYPE_JSON + ':Input01'
        tag_in_val  = tag + ':' + self.TYPE_JSON + ':Input01Value'
        tag_out     = tag + ':' + self.TYPE_JSON + ':Output01'
        tag_out_val = tag + ':' + self.TYPE_JSON + ':Output01Value'

        self._tag_enabled   = tag + ':EnabledValue'
        self._tag_volume    = tag + ':VolumeValue'
        self._tag_active    = tag + ':ActiveTracksValue'
        self._tag_received  = tag + ':ReceivedValue'
        self._tag_out_val   = tag_out_val

        sound_items = [f"{s['id']} — {s['name']}" for s in self._library]

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            with dpg.node_attribute(tag=tag_in, attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text(tag=tag_in_val, default_value='Super JSON input')

            with dpg.node_attribute(tag=tag + ':ParamsAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_checkbox(tag=self._tag_enabled, label='Enabled', default_value=True)
                dpg.add_slider_float(tag=self._tag_volume, label='Volume',
                                     default_value=0.35, min_value=0.0, max_value=1.0, width=w)
                dpg.add_text(default_value='Active Tracks (from agent)')
                dpg.add_input_text(tag=self._tag_active, default_value='',
                                   width=w, readonly=True)

            with dpg.node_attribute(tag=tag + ':LibAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(default_value='Library')
                dpg.add_listbox(items=sound_items, num_items=5, width=w)

            with dpg.node_attribute(tag=tag + ':ReceivedAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(default_value='Received JSON')
                dpg.add_input_text(tag=self._tag_received, default_value='',
                                   multiline=True, width=w, height=80, readonly=True)

            with dpg.node_attribute(tag=tag_out, attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(tag=tag_out_val, default_value='JSON Output')

        return self

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        tag = self.tag_node_name
        tag_in = tag + ':' + self.TYPE_JSON + ':Input01'

        super_json = None
        for conn in connection_list:
            if conn[1] == tag_in:
                src_key = ':'.join(conn[0].split(':')[:2])
                data = node_result_dict.get(src_key)
                if isinstance(data, dict):
                    super_json = data
                break

        if super_json and isinstance(super_json.get('actions'), dict):
            action_data = super_json['actions'].get('Soundscape', {})
        else:
            action_data = {}

        if action_data:
            self._last_output = action_data
            tracks = action_data.get('tracks', [])
            try:
                dpg_set_value(self._tag_enabled, bool(action_data.get('enabled', True)))
                dpg_set_value(self._tag_volume, float(action_data.get('volume', 0.35)))
                dpg_set_value(self._tag_active, ', '.join(str(t) for t in tracks))
                dpg_set_value(self._tag_received, json.dumps(action_data, indent=2))
            except (SystemError, AttributeError):
                pass
        elif super_json is not None:
            self._last_output = {}
            try:
                dpg_set_value(self._tag_received, '{"enabled": false}')
            except (SystemError, AttributeError):
                pass

        return {'image': None, 'json': self._last_output, 'audio': None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag = self.tag_node_name
        pos = dpg.get_item_pos(tag)
        d = {'ver': self._ver, 'pos': pos}
        for k in [self._tag_enabled, self._tag_volume]:
            try:
                d[k] = dpg_get_value(k)
            except (SystemError, AttributeError):
                pass
        return d

    def set_setting_dict(self, node_id, setting_dict):
        for k in [self._tag_enabled, self._tag_volume]:
            if k in setting_dict:
                try:
                    dpg_set_value(k, setting_dict[k])
                except (SystemError, AttributeError):
                    pass
