#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""FragranceComposition node — receives Super JSON from Agent and extracts its action."""

import json
import logging
import os

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

_LOG = logging.getLogger(__name__)

_TOOL_TEMPLATE = {
    'tool_name': 'FragranceComposition',
    'description': 'Creates a multi-fragrance olfactory composition.',
    'parameters': {
        'enabled': 'boolean',
        'duration': 'integer  # seconds — applies to the whole composition',
        'pause': 'integer  # seconds between repetitions — applies to the whole composition',
        'repetitions': 'integer  # number of repetitions — applies to the whole composition',
        'intensity': 'float  # 0.0 to 1.0 — applies to the whole composition',
        'fragrances': [
            {
                'name': 'string  # fragrance name from catalog',
                'composition_percent': 'float  # must sum to 100 across all fragrances',
            }
        ],
    },
}

_CATALOG_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'AgentNode', 'fragrance_catalog.json'
)

_MAX_FRAGRANCES = 12


def _load_catalog():
    try:
        path = os.path.normpath(_CATALOG_PATH)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [fr['name'] for fr in data.get('fragrances', [])]
    except Exception:
        return [
            'Citron', 'Orange', 'Bergamote', 'Pamplemousse',
            'Menthe', 'Eucalyptus', 'Lavande', 'Ylang-Ylang',
            'Jasmin', 'Rose', 'Santal', 'Vetiver',
            'Patchouli', 'Gingembre', 'Cannelle', 'Vanille',
        ]


class FactoryNode:
    node_label = 'FragranceComposition'
    node_tag = 'FragranceComposition'

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(BaseNode):
    _ver = '0.0.1'
    node_label = 'FragranceComposition'
    node_tag = 'FragranceComposition'

    def __init__(self):
        self._opencv_setting_dict = {}
        self._last_output = {}
        self._catalog = []
        self._num_fragrances = 1
        self._frag_slots = []   # list of dicts with widget tags per slot
        # Composition-level params (set from JSON, not displayed)
        self._comp_duration = 120
        self._comp_pause = 30
        self._comp_repetitions = 2
        self._comp_intensity = 0.5

    def get_tool_template(self):
        tmpl = dict(_TOOL_TEMPLATE)
        tmpl['available_fragrance_names'] = self._catalog
        return tmpl

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        self._opencv_setting_dict = opencv_setting_dict or {}
        w = self._opencv_setting_dict.get('process_width', 300)
        self._catalog = _load_catalog()

        tag = str(node_id) + ':' + self.node_tag
        self.tag_node_name = tag
        self._node_id = node_id
        self._parent = parent
        self._w = w

        tag_in      = tag + ':' + self.TYPE_JSON + ':Input01'
        tag_in_val  = tag + ':' + self.TYPE_JSON + ':Input01Value'
        tag_out     = tag + ':' + self.TYPE_JSON + ':Output01'
        tag_out_val = tag + ':' + self.TYPE_JSON + ':Output01Value'

        self._tag_enabled   = tag + ':EnabledValue'
        self._tag_total     = tag + ':TotalValue'
        self._tag_received  = tag + ':ReceivedValue'
        self._tag_out_val   = tag_out_val

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            with dpg.node_attribute(tag=tag_in, attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text(tag=tag_in_val, default_value='Super JSON input')

            with dpg.node_attribute(tag=tag + ':CtrlAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_checkbox(tag=self._tag_enabled, label='Enabled', default_value=True)
                dpg.add_text(tag=self._tag_total, default_value='Total: 0 %')
                dpg.add_button(label='+ Add Fragrance', width=w,
                               callback=self._cb_add_frag,
                               user_data=(node_id, parent))
                dpg.add_button(label='- Remove', width=w,
                               callback=self._cb_remove_frag,
                               user_data=(node_id, parent))

            with dpg.node_attribute(tag=tag + ':ReceivedAttr', attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(default_value='Received JSON')
                dpg.add_input_text(tag=self._tag_received, default_value='',
                                   multiline=True, width=w, height=90, readonly=True)

            # Create first slot
            self._create_slot(tag, parent, 0)

            with dpg.node_attribute(tag=tag_out, attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(tag=tag_out_val, default_value='JSON Output')

        return self

    # ── Slot management ───────────────────────────────────────────────────

    def _slot_tags(self, idx):
        tag = self.tag_node_name
        return {
            'attr':        tag + f':FragAttr{idx}',
            'name':        tag + f':FragName{idx}',
            'composition': tag + f':FragComp{idx}',
        }

    def _create_slot(self, tag, parent, idx):
        st = self._slot_tags(idx)
        if dpg.does_item_exist(st['attr']):
            return
        w = self._w
        default_frag = self._catalog[idx % len(self._catalog)] if self._catalog else ''
        with dpg.node_attribute(
            tag=st['attr'],
            attribute_type=dpg.mvNode_Attr_Static,
            parent=tag,
        ):
            dpg.add_text(default_value=f'— Fragrance {idx + 1} —')
            dpg.add_combo(tag=st['name'], items=self._catalog,
                          default_value=default_frag, width=w,
                          callback=self._cb_update_total)
            dpg.add_slider_float(tag=st['composition'],
                                 default_value=100.0 / max(self._num_fragrances, 1),
                                 min_value=0.0, max_value=100.0, width=w,
                                 callback=self._cb_update_total)
        self._cb_update_total(None, None)

    def _cb_add_frag(self, sender, app_data, user_data):
        node_id, parent = user_data
        tag = str(node_id) + ':' + self.node_tag
        if self._num_fragrances < _MAX_FRAGRANCES:
            self._create_slot(tag, parent, self._num_fragrances)
            self._num_fragrances += 1
            self._cb_update_total(None, None)

    def _cb_remove_frag(self, sender, app_data, user_data):
        node_id, parent = user_data
        tag = str(node_id) + ':' + self.node_tag
        if self._num_fragrances > 1:
            idx = self._num_fragrances - 1
            st = self._slot_tags(idx)
            try:
                if dpg.does_item_exist(st['attr']):
                    dpg.delete_item(st['attr'])
                self._num_fragrances -= 1
                self._cb_update_total(None, None)
            except (SystemError, AttributeError):
                pass

    def _cb_update_total(self, sender, app_data, user_data=None):
        total = 0.0
        for i in range(self._num_fragrances):
            st = self._slot_tags(i)
            try:
                total += float(dpg_get_value(st['composition']))
            except (SystemError, AttributeError, TypeError):
                pass
        label = f'Total: {total:.1f} %'
        if abs(total - 100.0) > 0.5:
            label += '  ⚠ must equal 100 %'
        try:
            dpg_set_value(self._tag_total, label)
        except (SystemError, AttributeError):
            pass

    def _read_fragrances(self):
        result = []
        for i in range(self._num_fragrances):
            st = self._slot_tags(i)
            try:
                result.append({
                    'name': dpg_get_value(st['name']),
                    'composition_percent': float(dpg_get_value(st['composition'])),
                })
            except (SystemError, AttributeError, TypeError, ValueError):
                pass
        return result

    # ── update() ──────────────────────────────────────────────────────────

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
                    _LOG.debug('[FragranceComposition] Received super_json from %s: actions=%s',
                               src_key, list((data.get('actions') or {}).keys()))
                else:
                    _LOG.debug('[FragranceComposition] Source %s returned no dict data (%r)', src_key, data)
                break

        if super_json and isinstance(super_json.get('actions'), dict):
            action_data = super_json['actions'].get('FragranceComposition', {})
            if action_data:
                _LOG.info('[FragranceComposition] action_data received: fragrances=%d',
                          len(action_data.get('fragrances', [])))
            else:
                _LOG.debug('[FragranceComposition] No FragranceComposition action in super_json')
        else:
            action_data = {}
            if super_json:
                _LOG.warning('[FragranceComposition] super_json has no "actions" dict: %r', super_json)

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

        # Always build current output from GUI state
        fragrances = self._read_fragrances()
        enabled = False
        try:
            enabled = bool(dpg_get_value(self._tag_enabled))
        except (SystemError, AttributeError):
            pass
        if not action_data:
            self._last_output = {
                'enabled': enabled,
                'duration': self._comp_duration,
                'pause': self._comp_pause,
                'repetitions': self._comp_repetitions,
                'intensity': self._comp_intensity,
                'fragrances': fragrances,
            }

        return {'image': None, 'json': self._last_output, 'audio': None}

    def _apply_action(self, data):
        # Store composition-level params (hidden — not displayed in UI)
        if 'duration' in data:
            self._comp_duration = int(data['duration'])
        if 'pause' in data:
            self._comp_pause = int(data['pause'])
        if 'repetitions' in data:
            self._comp_repetitions = int(data['repetitions'])
        if 'intensity' in data:
            self._comp_intensity = float(data['intensity'])

        fragrances = data.get('fragrances', [])
        tag = self.tag_node_name
        # Ensure we have enough slots, incrementing explicitly to avoid relying on side effects
        while self._num_fragrances < len(fragrances) and self._num_fragrances < _MAX_FRAGRANCES:
            self._create_slot(tag, self._parent, self._num_fragrances)
            self._num_fragrances += 1

        for i, fr in enumerate(fragrances[:_MAX_FRAGRANCES]):
            st = self._slot_tags(i)
            try:
                name = str(fr.get('name', ''))
                if name and dpg.does_item_exist(st['name']):
                    dpg_set_value(st['name'], name)
                if 'composition_percent' in fr and dpg.does_item_exist(st['composition']):
                    dpg_set_value(st['composition'], float(fr['composition_percent']))
            except (SystemError, AttributeError, TypeError, ValueError):
                pass
        try:
            dpg_set_value(self._tag_enabled, bool(data.get('enabled', True)))
        except (SystemError, AttributeError):
            pass
        self._cb_update_total(None, None)

    # ── Persistence ───────────────────────────────────────────────────────

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag = self.tag_node_name
        pos = dpg.get_item_pos(tag)
        d = {
            'ver': self._ver,
            'pos': pos,
            'num_fragrances': self._num_fragrances,
            'comp_duration': self._comp_duration,
            'comp_pause': self._comp_pause,
            'comp_repetitions': self._comp_repetitions,
            'comp_intensity': self._comp_intensity,
        }
        try:
            d[self._tag_enabled] = dpg_get_value(self._tag_enabled)
        except (SystemError, AttributeError):
            pass
        for i in range(self._num_fragrances):
            for k in self._slot_tags(i).values():
                try:
                    d[k] = dpg_get_value(k)
                except (SystemError, AttributeError):
                    pass
        return d

    def set_setting_dict(self, node_id, setting_dict):
        self._comp_duration = int(setting_dict.get('comp_duration', self._comp_duration))
        self._comp_pause = int(setting_dict.get('comp_pause', self._comp_pause))
        self._comp_repetitions = int(setting_dict.get('comp_repetitions', self._comp_repetitions))
        self._comp_intensity = float(setting_dict.get('comp_intensity', self._comp_intensity))
        saved_n = setting_dict.get('num_fragrances', 1)
        tag = self.tag_node_name
        while self._num_fragrances < saved_n and self._num_fragrances < _MAX_FRAGRANCES:
            self._create_slot(tag, self._parent, self._num_fragrances)
            self._num_fragrances += 1
        try:
            if self._tag_enabled in setting_dict:
                dpg_set_value(self._tag_enabled, setting_dict[self._tag_enabled])
        except (SystemError, AttributeError):
            pass
        for i in range(self._num_fragrances):
            for k in self._slot_tags(i).values():
                if k in setting_dict:
                    try:
                        dpg_set_value(k, setting_dict[k])
                    except (SystemError, AttributeError):
                        pass
        self._cb_update_total(None, None)
