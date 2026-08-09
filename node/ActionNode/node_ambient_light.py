#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AmbientLight node — receives Super JSON from Agent and extracts its action."""

import json

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

_VARIATION_TYPES = [
    'None', 'Static', 'Pulse', 'Breathing',
    'Slow Transition', 'Color Cycle', 'Sunset', 'Random Subtle',
]

_TOOL_TEMPLATE = {
    'tool_name': 'AmbientLight',
    'description': 'Controls ambient RGB lighting with configurable intensity and variation.',
    'parameters': {
        'enabled': 'boolean',
        'rgb': {'r': 'integer', 'g': 'integer', 'b': 'integer'},
        'intensity': 'float',
        'variation_type': 'string',
        'variation_speed': 'float',
        'duration': 'integer',
        'transition': 'integer',
    },
}


class FactoryNode:
    node_label = 'AmbientLight'
    node_tag = 'AmbientLight'

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(BaseNode):
    _ver = '0.0.1'
    node_label = 'AmbientLight'
    node_tag = 'AmbientLight'

    def __init__(self):
        self._opencv_setting_dict = {}
        self._last_output = {}

    def get_tool_template(self):
        return _TOOL_TEMPLATE

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        self._opencv_setting_dict = opencv_setting_dict or {}
        w = self._opencv_setting_dict.get('process_width', 280)

        tag = str(node_id) + ':' + self.node_tag
        self.tag_node_name = tag

        tag_in     = tag + ':' + self.TYPE_JSON + ':Input01'
        tag_in_val = tag + ':' + self.TYPE_JSON + ':Input01Value'
        tag_out    = tag + ':' + self.TYPE_JSON + ':Output01'
        tag_out_val= tag + ':' + self.TYPE_JSON + ':Output01Value'

        self._tag_enabled   = tag + ':EnabledValue'
        self._tag_r         = tag + ':RValue'
        self._tag_g         = tag + ':GValue'
        self._tag_b         = tag + ':BValue'
        self._tag_intensity = tag + ':IntensityValue'
        self._tag_vartype   = tag + ':VarTypeValue'
        self._tag_varspeed  = tag + ':VarSpeedValue'
        self._tag_duration  = tag + ':DurationValue'
        self._tag_transition= tag + ':TransitionValue'
        self._tag_received  = tag + ':ReceivedValue'
        self._tag_out_val   = tag_out_val

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            # ── JSON input ────────────────────────────────────────────────
            with dpg.node_attribute(tag=tag_in, attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text(tag=tag_in_val, default_value='Super JSON input')

            # ── Parameters ───────────────────────────────────────────────
            with dpg.node_attribute(tag=tag + ':ParamsAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_checkbox(tag=self._tag_enabled, label='Enabled', default_value=True)
                dpg.add_text(default_value='RGB')
                with dpg.group(horizontal=True):
                    dpg.add_slider_int(tag=self._tag_r, label='R', default_value=255,
                                       min_value=0, max_value=255, width=60)
                    dpg.add_slider_int(tag=self._tag_g, label='G', default_value=120,
                                       min_value=0, max_value=255, width=60)
                    dpg.add_slider_int(tag=self._tag_b, label='B', default_value=50,
                                       min_value=0, max_value=255, width=60)
                dpg.add_slider_float(tag=self._tag_intensity, label='Intensity',
                                     default_value=0.6, min_value=0.0, max_value=1.0, width=w)
                dpg.add_combo(tag=self._tag_vartype, label='Variation Type',
                              items=_VARIATION_TYPES, default_value='Static', width=w)
                dpg.add_slider_float(tag=self._tag_varspeed, label='Variation Speed',
                                     default_value=0.2, min_value=0.0, max_value=1.0, width=w)
                dpg.add_input_int(tag=self._tag_duration, label='Duration (s)',
                                  default_value=600, min_value=0, width=w)
                dpg.add_input_int(tag=self._tag_transition, label='Transition (s)',
                                  default_value=60, min_value=0, width=w)

            # ── Received JSON display ─────────────────────────────────────
            with dpg.node_attribute(tag=tag + ':ReceivedAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(default_value='Received JSON')
                dpg.add_input_text(tag=self._tag_received, default_value='',
                                   multiline=True, width=w, height=80, readonly=True)

            # ── JSON output ───────────────────────────────────────────────
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
            action_data = super_json['actions'].get('AmbientLight', {})
        else:
            action_data = {}

        if action_data:
            # Update GUI from agent decision
            self._apply_action(action_data)
            self._last_output = action_data
            try:
                dpg_set_value(self._tag_received, json.dumps(action_data, indent=2))
            except (SystemError, AttributeError):
                pass
        elif super_json is not None:
            # Super JSON received but no AmbientLight action
            self._last_output = {}
            try:
                dpg_set_value(self._tag_received, '{"enabled": false}')
            except (SystemError, AttributeError):
                pass

        return {'image': None, 'json': self._last_output, 'audio': None}

    def _apply_action(self, data):
        try:
            dpg_set_value(self._tag_enabled, bool(data.get('enabled', True)))
            rgb = data.get('rgb', {})
            if rgb:
                dpg_set_value(self._tag_r, int(rgb.get('r', 255)))
                dpg_set_value(self._tag_g, int(rgb.get('g', 120)))
                dpg_set_value(self._tag_b, int(rgb.get('b', 50)))
            if 'intensity' in data:
                dpg_set_value(self._tag_intensity, float(data['intensity']))
            if 'variation_type' in data:
                vt = str(data['variation_type']).title()
                dpg_set_value(self._tag_vartype, vt)
            if 'variation_speed' in data:
                dpg_set_value(self._tag_varspeed, float(data['variation_speed']))
            if 'duration' in data:
                dpg_set_value(self._tag_duration, int(data['duration']))
            if 'transition' in data:
                dpg_set_value(self._tag_transition, int(data['transition']))
        except (SystemError, AttributeError, TypeError, ValueError):
            pass

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag = self.tag_node_name
        pos = dpg.get_item_pos(tag)
        d = {'ver': self._ver, 'pos': pos}
        for k in [self._tag_enabled, self._tag_r, self._tag_g, self._tag_b,
                  self._tag_intensity, self._tag_vartype, self._tag_varspeed,
                  self._tag_duration, self._tag_transition]:
            try:
                d[k] = dpg_get_value(k)
            except (SystemError, AttributeError):
                pass
        return d

    def set_setting_dict(self, node_id, setting_dict):
        for k in [self._tag_enabled, self._tag_r, self._tag_g, self._tag_b,
                  self._tag_intensity, self._tag_vartype, self._tag_varspeed,
                  self._tag_duration, self._tag_transition]:
            if k in setting_dict:
                try:
                    dpg_set_value(k, setting_dict[k])
                except (SystemError, AttributeError):
                    pass
