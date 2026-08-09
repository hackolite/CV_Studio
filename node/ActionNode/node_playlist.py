#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Playlist node — receives Super JSON from Agent and extracts its action."""

import json
import os

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

_TOOL_TEMPLATE = {
    'tool_name': 'Playlist',
    'description': 'Plays a music playlist (world music library or user-uploaded).',
    'parameters': {
        'enabled': 'boolean',
        'playlist_name': 'string',
    },
}

_LIB_PATH = os.path.join(os.path.dirname(__file__), 'playlist_library.json')


def _load_library():
    try:
        with open(_LIB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('playlists', [])
    except Exception:
        return []


class FactoryNode:
    node_label = 'Playlist'
    node_tag = 'Playlist'

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(BaseNode):
    _ver = '0.0.1'
    node_label = 'Playlist'
    node_tag = 'Playlist'

    def __init__(self):
        self._opencv_setting_dict = {}
        self._last_output = {}
        self._playlists = []
        self._user_playlists = []

    def get_tool_template(self):
        all_names = [p['playlist_name'] for p in self._playlists + self._user_playlists]
        tmpl = dict(_TOOL_TEMPLATE)
        tmpl['available_playlists'] = all_names
        return tmpl

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        self._opencv_setting_dict = opencv_setting_dict or {}
        w = self._opencv_setting_dict.get('process_width', 280)
        self._playlists = _load_library()

        tag = str(node_id) + ':' + self.node_tag
        self.tag_node_name = tag

        tag_in      = tag + ':' + self.TYPE_JSON + ':Input01'
        tag_in_val  = tag + ':' + self.TYPE_JSON + ':Input01Value'
        tag_out     = tag + ':' + self.TYPE_JSON + ':Output01'
        tag_out_val = tag + ':' + self.TYPE_JSON + ':Output01Value'

        self._tag_enabled    = tag + ':EnabledValue'
        self._tag_select     = tag + ':SelectValue'
        self._tag_upload_btn = tag + ':UploadBtn'
        self._tag_received   = tag + ':ReceivedValue'
        self._tag_out_val    = tag_out_val
        self._tag = tag

        playlist_names = [p['playlist_name'] for p in self._playlists]

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            with dpg.node_attribute(tag=tag_in, attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text(tag=tag_in_val, default_value='Super JSON input')

            with dpg.node_attribute(tag=tag + ':ParamsAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_checkbox(tag=self._tag_enabled, label='Enabled', default_value=True)
                dpg.add_text(default_value='Select Playlist')
                default_pl = playlist_names[0] if playlist_names else ''
                dpg.add_combo(tag=self._tag_select, items=playlist_names,
                              default_value=default_pl, width=w)
                dpg.add_button(tag=self._tag_upload_btn, label='Upload Playlist JSON',
                               width=w, callback=self._cb_upload)

            with dpg.node_attribute(tag=tag + ':ReceivedAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(default_value='Received JSON')
                dpg.add_input_text(tag=self._tag_received, default_value='',
                                   multiline=True, width=w, height=80, readonly=True)

            with dpg.node_attribute(tag=tag_out, attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(tag=tag_out_val, default_value='JSON Output')

        return self

    def _cb_upload(self, sender, app_data, user_data=None):
        dpg.add_file_dialog(
            directory_selector=False,
            show=True,
            modal=True,
            callback=self._cb_file_selected,
            tag=self._tag + ':FileDialog',
            height=400,
        )
        with dpg.file_extension('.json', parent=self._tag + ':FileDialog'):
            pass

    def _cb_file_selected(self, sender, app_data, user_data=None):
        path = app_data.get('file_path_name', '')
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Accept either a single playlist dict or a list in 'playlists' key
            if isinstance(data, dict) and 'playlist_name' in data:
                self._user_playlists = [data]
            elif isinstance(data, dict) and 'playlists' in data:
                self._user_playlists = data['playlists']
            elif isinstance(data, list):
                self._user_playlists = data
            # Refresh combo
            all_names = [p['playlist_name'] for p in self._playlists + self._user_playlists]
            try:
                dpg.configure_item(self._tag_select, items=all_names)
                if self._user_playlists:
                    dpg_set_value(self._tag_select, self._user_playlists[0]['playlist_name'])
            except (SystemError, AttributeError):
                pass
        except Exception:
            pass

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
            action_data = super_json['actions'].get('Playlist', {})
        else:
            action_data = {}

        if action_data:
            self._last_output = action_data
            try:
                dpg_set_value(self._tag_enabled, bool(action_data.get('enabled', True)))
                if action_data.get('playlist_name'):
                    dpg_set_value(self._tag_select, str(action_data['playlist_name']))
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
        try:
            d[self._tag_enabled] = dpg_get_value(self._tag_enabled)
            d[self._tag_select]  = dpg_get_value(self._tag_select)
        except (SystemError, AttributeError):
            pass
        return d

    def set_setting_dict(self, node_id, setting_dict):
        for k in [self._tag_enabled, self._tag_select]:
            if k in setting_dict:
                try:
                    dpg_set_value(k, setting_dict[k])
                except (SystemError, AttributeError):
                    pass
