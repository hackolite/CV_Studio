#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SecurityAgent — LLM-driven security assessment via OpenRouter/Google AI/Groq.

Shares the AmbianceAgent engine (LLM call, tool discovery, cooldown, parsing)
and only specialises the system prompt and the node layout:

    ○ Enabled              <- boolean INPUT pin, wired from a boolean source
    ▶ Start
    ○ Inference            <- boolean INPUT pin, wired from a boolean source
    Cooldown slider (unlabelled)
    Provider (routing) combo
    API key (password)
    Model combo
    JsonInput   -> collapsible field showing the aggregated input JSON
    JsonOutput  -> collapsible field showing the JSON of the tools to use
    + Add Input / - Remove Input   <- immediately below JsonOutput
    Status / JSON output
    Input 1..N
"""

import copy
import json
import threading

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_set_value
from node.AgentNode.node_ambiance_agent import (
    PROVIDERS,
    PROVIDER_OPENROUTER,
    Node as AmbianceAgentNode,
)

_AGENT_TYPE = 'SecurityAgent'

_SYSTEM_PROMPT = (
    "You are an expert security analyst. "
    "Analyse the provided sensor data (cameras, motion sensors, access logs, etc.) "
    "and user prompt, then select and configure the available tools to respond to "
    "the detected security situation. "
    "Return ONLY a single valid JSON object matching the required schema — "
    "no markdown fences, no commentary, no chain-of-thought text."
)


class FactoryNode:
    node_label = _AGENT_TYPE
    node_tag = _AGENT_TYPE

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(AmbianceAgentNode):
    _ver = '0.0.1'
    node_label = _AGENT_TYPE
    node_tag = _AGENT_TYPE

    def __init__(self):
        super().__init__()
        self._enabled = True
        self._inference = True
        self._tag_enabled = None
        self._tag_enabled_slot = None
        self._tag_inference = None
        self._tag_inference_slot = None
        self._tag_json_input = None
        self._tag_json_output = None
        self._tag_input_mgmt = None
        self._show_json_input = True
        self._show_json_output = True
        self._last_json_input_text = None
        self._last_json_output_text = None

    # ------------------------------------------------------------------
    # GUI construction
    # ------------------------------------------------------------------

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        self._opencv_setting_dict = opencv_setting_dict or {}
        w = self._opencv_setting_dict.get('process_width', 320)

        tag = str(node_id) + ':' + self.node_tag
        self.tag_node_name = tag

        self._tag_enabled_slot = tag + ':' + self.TYPE_BOOLEAN + ':Input00'
        self._tag_enabled = self._tag_enabled_slot + 'Value'
        self._tag_startstop = tag + ':StartStopBtn'
        self._tag_inference_slot = tag + ':' + self.TYPE_BOOLEAN + ':Input01'
        self._tag_inference = self._tag_inference_slot + 'Value'
        self._tag_cooldown = tag + ':CooldownValue'
        self._tag_provider = tag + ':ProviderValue'
        self._tag_apikey = tag + ':ApiKeyValue'
        self._tag_model = tag + ':ModelValue'
        self._tag_prompt = tag + ':PromptValue'
        self._tag_description = tag + ':DescriptionValue'
        self._tag_summary = tag + ':SummaryValue'
        self._tag_json_input = tag + ':JsonInputValue'
        self._tag_json_output = tag + ':JsonOutputValue'
        self._tag_status = tag + ':StatusValue'
        self._tag_input_mgmt = tag + ':InputMgmt'
        self._node_id = node_id

        tag_out = tag + ':' + self.TYPE_JSON + ':Output01'
        self._tag_out_val = tag + ':' + self.TYPE_JSON + ':Output01Value'

        self._available_models = []
        threading.Thread(target=self._bg_fetch_models, daemon=True).start()

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            # ── Enable boolean input (wired from a boolean source) ────────
            with dpg.node_attribute(
                tag=self._tag_enabled_slot,
                attribute_type=dpg.mvNode_Attr_Input,
                shape=dpg.mvNode_PinShape_CircleFilled,
            ):
                dpg.add_text(
                    tag=self._tag_enabled,
                    default_value=self._bool_label('Enabled', self._enabled),
                )

            # ── Start / Stop button ──────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ExecuteAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=self._tag_startstop,
                    label='▶ Start',
                    width=w,
                    callback=self._cb_startstop,
                )
                self._update_startstop_ui()

            # ── Inference boolean input (wired from a boolean source) ─────
            with dpg.node_attribute(
                tag=self._tag_inference_slot,
                attribute_type=dpg.mvNode_Attr_Input,
                shape=dpg.mvNode_PinShape_CircleFilled,
            ):
                dpg.add_text(
                    tag=self._tag_inference,
                    default_value=self._bool_label('Inference', self._inference),
                )

            # ── Cooldown slider (no label) ───────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':CooldownAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=self._tag_cooldown,
                    default_value=self._cooldown_s,
                    min_value=5,
                    max_value=300,
                    width=w,
                )

            # ── Provider (routing) dropdown ──────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ProviderAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=self._tag_provider,
                    items=PROVIDERS,
                    default_value=PROVIDER_OPENROUTER,
                    width=w,
                    callback=self._cb_provider_changed,
                )

            # ── API key (password) ───────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ApiKeyAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=self._tag_apikey,
                    hint='sk-or-... (OpenRouter) / AIza... (Google AI) / gsk_... (Groq)',
                    width=w,
                    password=True,
                )

            # ── Model dropdown ───────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ModelAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                default_model = self._available_models[0] if self._available_models else ''
                dpg.add_combo(
                    tag=self._tag_model,
                    items=self._available_models,
                    default_value=default_model,
                    width=w,
                )

            # ── JsonInput (aggregated input JSON), collapsible ────────────
            with dpg.node_attribute(
                tag=tag + ':JsonInputAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='JsonInput',
                    width=w,
                    callback=self._cb_toggle_json_input,
                )
                dpg.add_input_text(
                    tag=self._tag_json_input,
                    default_value='',
                    multiline=True,
                    width=w,
                    height=100,
                    readonly=True,
                    show=self._show_json_input,
                )
                # Hidden field kept for the parent engine (LLM description
                # forwarded to Text2Speech) and for settings persistence.
                dpg.add_input_text(
                    tag=self._tag_description,
                    default_value='',
                    multiline=True,
                    width=w,
                    height=70,
                    show=False,
                )

            # ── JsonOutput (tools to use), collapsible ────────────────────
            with dpg.node_attribute(
                tag=tag + ':JsonOutputAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='JsonOutput',
                    width=w,
                    callback=self._cb_toggle_json_output,
                )
                dpg.add_input_text(
                    tag=self._tag_json_output,
                    default_value='',
                    multiline=True,
                    width=w,
                    height=130,
                    readonly=True,
                    show=self._show_json_output,
                )
                # Hidden field kept for the parent engine (decision summary).
                dpg.add_input_text(
                    tag=self._tag_summary,
                    default_value='',
                    multiline=True,
                    width=w,
                    height=130,
                    readonly=True,
                    show=False,
                )

            # ── Add / Remove input — immediately below JsonOutput ────────
            with dpg.node_attribute(
                tag=self._tag_input_mgmt,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(label='+ Add Input', width=w,
                               callback=self._cb_add_input,
                               user_data=(node_id, parent))
                dpg.add_button(label='- Remove Input', width=w,
                               callback=self._cb_remove_input,
                               user_data=(node_id, parent))

            # ── Status ───────────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':StatusAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(tag=self._tag_status, default_value='[*] READY')

            # ── JSON Output ──────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag_out,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(tag=self._tag_out_val, default_value='JSON Output')

            # ── JSON inputs ──────────────────────────────────────────────
            for i in range(self.num_inputs):
                self._create_input_slot(tag, parent, i)

        return self

    # ------------------------------------------------------------------
    # Slot helpers
    # ------------------------------------------------------------------

    def _create_input_slot(self, tag, parent, idx):
        """Create a JSON input slot at the bottom of the node."""
        slot_tag = tag + ':' + self.TYPE_JSON + f':Input{idx:02d}'
        if dpg.does_item_exist(slot_tag):
            return
        with dpg.node_attribute(
            tag=slot_tag,
            attribute_type=dpg.mvNode_Attr_Input,
            parent=tag,
        ):
            dpg.add_text(default_value=f'Input {idx + 1}')

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _cb_toggle_json_input(self, sender, app_data, user_data=None):
        self._show_json_input = not self._show_json_input
        self._set_show(self._tag_json_input, self._show_json_input)

    def _cb_toggle_json_output(self, sender, app_data, user_data=None):
        self._show_json_output = not self._show_json_output
        self._set_show(self._tag_json_output, self._show_json_output)

    @staticmethod
    def _set_show(item_tag, show):
        try:
            if item_tag and dpg.does_item_exist(item_tag):
                dpg.configure_item(item_tag, show=show)
        except (SystemError, AttributeError):
            pass

    # ------------------------------------------------------------------
    # Execution gating
    # ------------------------------------------------------------------

    def _is_enabled(self):
        """Both wired booleans must be true for the agent to run an inference."""
        return bool(self._enabled) and bool(self._inference)

    @staticmethod
    def _bool_label(name, value):
        return f'{name}: {bool(value)}'

    @staticmethod
    def _coerce_bool(value, fallback):
        """Convert the payload of a connected boolean source into a bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            text = value.strip().lower()
            if text in ('true', '1', 'on', 'yes'):
                return True
            if text in ('false', '0', 'off', 'no', ''):
                return False
            return bool(fallback)
        if isinstance(value, dict):
            for key in ('value', 'bool', 'boolean', 'trigger', 'state',
                        'enabled', 'result'):
                if key in value:
                    return Node._coerce_bool(value[key], fallback)
        return bool(fallback)

    def _read_wired_bool(self, connection_list, node_result_dict, slot_tag,
                         fallback):
        """Return the boolean carried by the link plugged into ``slot_tag``."""
        if not slot_tag:
            return bool(fallback)
        for conn in connection_list:
            if conn[1] != slot_tag:
                continue
            src_key = ':'.join(conn[0].split(':')[:2])
            try:
                src_data = node_result_dict.get(src_key)
            except AttributeError:
                return bool(fallback)
            return self._coerce_bool(src_data, fallback)
        return bool(fallback)

    def _refresh_bool_inputs(self, connection_list, node_result_dict):
        self._enabled = self._read_wired_bool(
            connection_list, node_result_dict, self._tag_enabled_slot,
            self._enabled)
        self._inference = self._read_wired_bool(
            connection_list, node_result_dict, self._tag_inference_slot,
            self._inference)
        for item_tag, name, value in (
            (self._tag_enabled, 'Enabled', self._enabled),
            (self._tag_inference, 'Inference', self._inference),
        ):
            if not item_tag:
                continue
            try:
                dpg_set_value(item_tag, self._bool_label(name, value))
            except (SystemError, AttributeError):
                pass

    # ------------------------------------------------------------------
    # update()
    # ------------------------------------------------------------------

    def update(self, node_id, connection_list, node_image_dict, node_result_dict,
               node_audio_dict):
        self._refresh_bool_inputs(connection_list, node_result_dict)
        self._refresh_json_input(connection_list, node_result_dict)
        self._refresh_json_output(node_result_dict)
        return super().update(node_id, connection_list, node_image_dict,
                              node_result_dict, node_audio_dict)

    def _refresh_json_input(self, connection_list, node_result_dict):
        """Display the aggregated JSON coming from the connected inputs."""
        aggregated = {}
        tag = self.tag_node_name
        for i in range(self.num_inputs):
            slot_tag = tag + ':' + self.TYPE_JSON + f':Input{i:02d}'
            for conn in connection_list:
                if conn[1] == slot_tag:
                    src_key = ':'.join(conn[0].split(':')[:2])
                    src_data = node_result_dict.get(src_key)
                    if isinstance(src_data, dict):
                        aggregated[f'input_{i}'] = src_data
                    break
        self._set_json_text(self._tag_json_input, aggregated, '_last_json_input_text')

    def _refresh_json_output(self, node_result_dict):
        """Display the JSON describing the tools the agent may use."""
        try:
            tools = self._discover_tools(node_result_dict)
        except (AttributeError, TypeError):
            tools = []
        self._set_json_text(self._tag_json_output, tools, '_last_json_output_text')

    def _set_json_text(self, item_tag, value, cache_attr):
        try:
            text = json.dumps(value, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(value)
        if getattr(self, cache_attr, None) == text:
            return
        setattr(self, cache_attr, text)
        try:
            dpg_set_value(item_tag, text)
        except (SystemError, AttributeError):
            pass

    # ------------------------------------------------------------------
    # LLM prompt
    # ------------------------------------------------------------------

    def _build_messages(self, data, prompt, tools):
        from node.AgentNode.node_ambiance_agent import _RESPONSE_SCHEMA
        schema = copy.deepcopy(_RESPONSE_SCHEMA)
        schema['agent'] = {'type': _AGENT_TYPE}
        for tool in tools:
            tool_name = tool.get('tool_name')
            if tool_name and tool_name not in schema['actions']:
                schema['actions'][tool_name] = tool.get('parameters', {})
        user_content = {
            'sensor_data': data,
            'user_prompt': prompt,
            'available_tools': tools,
            'response_schema': schema,
            'instruction': (
                'Based on the sensor data and user prompt, assess the security situation '
                'and decide which tools to activate. '
                'Only use tools listed in available_tools. '
                'Return a single JSON object matching response_schema exactly.'
            ),
        }
        return [
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': json.dumps(user_content, ensure_ascii=False)},
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def get_setting_dict(self, node_id):
        d = super().get_setting_dict(node_id)
        d['enabled'] = bool(self._enabled)
        d['inference'] = bool(self._inference)
        d['show_json_input'] = self._show_json_input
        d['show_json_output'] = self._show_json_output
        return d

    def set_setting_dict(self, node_id, setting_dict):
        super().set_setting_dict(node_id, setting_dict)
        self._enabled = bool(setting_dict.get('enabled', True))
        self._inference = bool(setting_dict.get('inference', True))
        self._show_json_input = bool(setting_dict.get('show_json_input', True))
        self._show_json_output = bool(setting_dict.get('show_json_output', True))
        try:
            if self._tag_enabled:
                dpg_set_value(self._tag_enabled,
                              self._bool_label('Enabled', self._enabled))
            if self._tag_inference:
                dpg_set_value(self._tag_inference,
                              self._bool_label('Inference', self._inference))
        except (SystemError, AttributeError):
            pass
        self._set_show(self._tag_json_input, self._show_json_input)
        self._set_show(self._tag_json_output, self._show_json_output)
