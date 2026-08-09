#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Text2Speech node — receives Super JSON from Agent and vocalizes the text action."""

import json
import subprocess
import threading

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

_VOCALIZERS = ['piper', 'espeak', 'festival', 'edge-tts', 'coqui']

_TOOL_TEMPLATE = {
    'tool_name': 'Text2Speech',
    'description': (
        'Converts text to speech using the configured vocalizer. '
        'Use to narrate ambiance descriptions, alerts, or guided experiences.'
    ),
    'parameters': {
        'enabled': 'boolean',
        'text': 'string  # text to vocalize',
        'vocalizer': 'string  # one of: piper, espeak, festival, edge-tts, coqui',
        'speed': 'float  # speech rate multiplier, 0.5 to 2.0',
        'pitch': 'float  # pitch shift, 0.5 to 2.0',
        'volume': 'float  # output volume, 0.0 to 1.0',
    },
}


def _speak_piper(text, speed, pitch, volume):
    """Invoke piper TTS and pipe raw audio to aplay for playback."""
    try:
        piper = subprocess.Popen(
            ['piper', '--output-raw'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        aplay = subprocess.Popen(
            ['aplay', '-r', '22050', '-f', 'S16_LE', '-t', 'raw', '-'],
            stdin=piper.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        piper.stdin.write(text.encode('utf-8'))
        piper.stdin.close()
        piper.wait(timeout=30)
        aplay.wait(timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass


def _speak_espeak(text, speed, pitch, volume):
    try:
        rate = int(175 * speed)
        pitch_val = int(50 * pitch)
        vol = int(100 * volume)
        subprocess.Popen(
            ['espeak', '-s', str(rate), '-p', str(pitch_val), '-a', str(vol), text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, OSError):
        pass


def _speak(vocalizer, text, speed, pitch, volume):
    if not text:
        return
    if vocalizer == 'piper':
        _speak_piper(text, speed, pitch, volume)
    elif vocalizer == 'espeak':
        _speak_espeak(text, speed, pitch, volume)
    # festival, edge-tts, coqui: placeholders — extend as needed


class FactoryNode:
    node_label = 'Text2Speech'
    node_tag = 'Text2Speech'

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(BaseNode):
    _ver = '0.0.1'
    node_label = 'Text2Speech'
    node_tag = 'Text2Speech'

    def __init__(self):
        self._opencv_setting_dict = {}
        self._last_output = {}
        self._speak_thread = None

    def get_tool_template(self):
        return _TOOL_TEMPLATE

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        self._opencv_setting_dict = opencv_setting_dict or {}
        w = self._opencv_setting_dict.get('process_width', 280)

        tag = str(node_id) + ':' + self.node_tag
        self.tag_node_name = tag

        tag_in      = tag + ':' + self.TYPE_JSON + ':Input01'
        tag_in_val  = tag + ':' + self.TYPE_JSON + ':Input01Value'
        tag_out     = tag + ':' + self.TYPE_JSON + ':Output01'
        tag_out_val = tag + ':' + self.TYPE_JSON + ':Output01Value'

        self._tag_enabled    = tag + ':EnabledValue'
        self._tag_text       = tag + ':TextValue'
        self._tag_vocalizer  = tag + ':VocalizerValue'
        self._tag_speed      = tag + ':SpeedValue'
        self._tag_pitch      = tag + ':PitchValue'
        self._tag_volume     = tag + ':VolumeValue'
        self._tag_received   = tag + ':ReceivedValue'
        self._tag_status     = tag + ':StatusValue'
        self._tag_out_val    = tag_out_val

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            # ── JSON input ────────────────────────────────────────────────
            with dpg.node_attribute(tag=tag_in, attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text(tag=tag_in_val, default_value='Super JSON input')

            # ── Parameters ───────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ParamsAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(tag=self._tag_enabled, label='Enabled', default_value=True)
                dpg.add_combo(
                    tag=self._tag_vocalizer,
                    label='Vocalizer',
                    items=_VOCALIZERS,
                    default_value='piper',
                    width=w,
                )
                dpg.add_input_text(
                    tag=self._tag_text,
                    hint='Text to vocalize...',
                    multiline=True,
                    width=w,
                    height=70,
                )
                dpg.add_slider_float(
                    tag=self._tag_speed,
                    label='Speed',
                    default_value=1.0,
                    min_value=0.5,
                    max_value=2.0,
                    width=w,
                )
                dpg.add_slider_float(
                    tag=self._tag_pitch,
                    label='Pitch',
                    default_value=1.0,
                    min_value=0.5,
                    max_value=2.0,
                    width=w,
                )
                dpg.add_slider_float(
                    tag=self._tag_volume,
                    label='Volume',
                    default_value=0.8,
                    min_value=0.0,
                    max_value=1.0,
                    width=w,
                )
                dpg.add_text(tag=self._tag_status, default_value='[*] idle')

            # ── Received JSON display ─────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ReceivedAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(default_value='Received JSON')
                dpg.add_input_text(
                    tag=self._tag_received,
                    default_value='',
                    multiline=True,
                    width=w,
                    height=80,
                    readonly=True,
                )

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
            action_data = super_json['actions'].get('Text2Speech', {})
        else:
            action_data = {}

        if action_data and action_data.get('enabled', True):
            self._apply_action(action_data)
            self._last_output = action_data
            try:
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

    def _apply_action(self, data):
        try:
            enabled = bool(data.get('enabled', True))
            dpg_set_value(self._tag_enabled, enabled)
            text = str(data.get('text', ''))
            dpg_set_value(self._tag_text, text)
            vocalizer = str(data.get('vocalizer', 'piper'))
            if vocalizer in _VOCALIZERS:
                dpg_set_value(self._tag_vocalizer, vocalizer)
            if 'speed' in data:
                dpg_set_value(self._tag_speed, float(data['speed']))
            if 'pitch' in data:
                dpg_set_value(self._tag_pitch, float(data['pitch']))
            if 'volume' in data:
                dpg_set_value(self._tag_volume, float(data['volume']))
        except (SystemError, AttributeError, TypeError, ValueError):
            pass

        # Fire TTS in background if enabled and text is provided
        if data.get('enabled', True) and data.get('text'):
            try:
                voc = dpg_get_value(self._tag_vocalizer)
                spd = float(dpg_get_value(self._tag_speed))
                pit = float(dpg_get_value(self._tag_pitch))
                vol = float(dpg_get_value(self._tag_volume))
                txt = str(dpg_get_value(self._tag_text))
            except (SystemError, AttributeError, TypeError, ValueError):
                return
            if not (self._speak_thread and self._speak_thread.is_alive()):
                self._speak_thread = threading.Thread(
                    target=_speak, args=(voc, txt, spd, pit, vol), daemon=True
                )
                self._speak_thread.start()
                try:
                    dpg_set_value(self._tag_status, '[>] speaking...')
                except (SystemError, AttributeError):
                    pass
            else:
                # Previous utterance still playing — skip silently but update status
                try:
                    dpg_set_value(self._tag_status, '[~] busy — request skipped')
                except (SystemError, AttributeError):
                    pass

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag = self.tag_node_name
        pos = dpg.get_item_pos(tag)
        d = {'ver': self._ver, 'pos': pos}
        for k in [self._tag_enabled, self._tag_text, self._tag_vocalizer,
                  self._tag_speed, self._tag_pitch, self._tag_volume]:
            try:
                d[k] = dpg_get_value(k)
            except (SystemError, AttributeError):
                pass
        return d

    def set_setting_dict(self, node_id, setting_dict):
        for k in [self._tag_enabled, self._tag_text, self._tag_vocalizer,
                  self._tag_speed, self._tag_pitch, self._tag_volume]:
            if k in setting_dict:
                try:
                    dpg_set_value(k, setting_dict[k])
                except (SystemError, AttributeError):
                    pass
