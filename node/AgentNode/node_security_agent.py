#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SecurityAgent — LLM-driven security assessment via OpenRouter/Google AI/Groq.

Shares the AmbianceAgent engine (LLM call, tool discovery, cooldown, parsing)
and only specialises the system prompt and the node layout:

    [x] Enabled            <- boolean gating the agent start
    ▶ Start
    Cooldown (s) slider
    Provider (routing) combo
    API key (password)
    Model combo
    ⚙ Settings 1  -> collapsible Description field
    ⚙ Settings 2  -> collapsible Summary field
    Status / JSON output
    Input 1..N
    + Add Input / - Remove Input   <- always at the very bottom
"""

import copy
import json
import threading

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
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
        self._tag_enabled = None
        self._tag_input_mgmt = None
        self._show_description = True
        self._show_summary = True

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

        self._tag_enabled = tag + ':EnabledValue'
        self._tag_startstop = tag + ':StartStopBtn'
        self._tag_cooldown = tag + ':CooldownValue'
        self._tag_provider = tag + ':ProviderValue'
        self._tag_apikey = tag + ':ApiKeyValue'
        self._tag_model = tag + ':ModelValue'
        self._tag_prompt = tag + ':PromptValue'
        self._tag_description = tag + ':DescriptionValue'
        self._tag_summary = tag + ':SummaryValue'
        self._tag_status = tag + ':StatusValue'
        self._tag_input_mgmt = tag + ':InputMgmt'
        self._node_id = node_id

        tag_out = tag + ':' + self.TYPE_JSON + ':Output01'
        self._tag_out_val = tag + ':' + self.TYPE_JSON + ':Output01Value'

        self._available_models = []
        threading.Thread(target=self._bg_fetch_models, daemon=True).start()

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            # ── Enable boolean (decides whether the agent may start) ──────
            with dpg.node_attribute(
                tag=tag + ':EnabledAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=self._tag_enabled,
                    label='Enabled',
                    default_value=self._enabled,
                    callback=self._cb_enabled_changed,
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

            # ── Cooldown slider ──────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':CooldownAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=self._tag_cooldown,
                    label='Cooldown (s)',
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

            # ── Text field 1 (Description), collapsible via Settings 1 ────
            with dpg.node_attribute(
                tag=tag + ':DescriptionAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='⚙ Settings 1',
                    width=w,
                    callback=self._cb_toggle_description,
                )
                dpg.add_input_text(
                    tag=self._tag_description,
                    hint='Description (text for Text2Speech)…',
                    multiline=True,
                    width=w,
                    height=70,
                    show=self._show_description,
                )

            # ── Text field 2 (Summary), collapsible via Settings 2 ────────
            with dpg.node_attribute(
                tag=tag + ':SummaryAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='⚙ Settings 2',
                    width=w,
                    callback=self._cb_toggle_summary,
                )
                dpg.add_input_text(
                    tag=self._tag_summary,
                    default_value='',
                    multiline=True,
                    width=w,
                    height=130,
                    readonly=True,
                    show=self._show_summary,
                )

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

            # ── Add / Remove input — always at the very bottom ───────────
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

        return self

    # ------------------------------------------------------------------
    # Slot helpers
    # ------------------------------------------------------------------

    def _create_input_slot(self, tag, parent, idx):
        """Create an input slot, keeping the Add/Remove buttons at the bottom."""
        slot_tag = tag + ':' + self.TYPE_JSON + f':Input{idx:02d}'
        if dpg.does_item_exist(slot_tag):
            return
        kwargs = {}
        mgmt_tag = self._tag_input_mgmt
        if mgmt_tag and dpg.does_item_exist(mgmt_tag):
            kwargs['before'] = mgmt_tag
        with dpg.node_attribute(
            tag=slot_tag,
            attribute_type=dpg.mvNode_Attr_Input,
            parent=tag,
            **kwargs,
        ):
            dpg.add_text(default_value=f'Input {idx + 1}')

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _cb_enabled_changed(self, sender, app_data, user_data=None):
        self._enabled = bool(app_data)

    def _cb_toggle_description(self, sender, app_data, user_data=None):
        self._show_description = not self._show_description
        self._set_show(self._tag_description, self._show_description)

    def _cb_toggle_summary(self, sender, app_data, user_data=None):
        self._show_summary = not self._show_summary
        self._set_show(self._tag_summary, self._show_summary)

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
        """The boolean placed before Start decides whether the agent may run."""
        try:
            if self._tag_enabled and dpg.does_item_exist(self._tag_enabled):
                return bool(dpg_get_value(self._tag_enabled))
        except (SystemError, AttributeError):
            pass
        return bool(self._enabled)

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
        d['enabled'] = self._is_enabled()
        d['show_description'] = self._show_description
        d['show_summary'] = self._show_summary
        return d

    def set_setting_dict(self, node_id, setting_dict):
        super().set_setting_dict(node_id, setting_dict)
        self._enabled = bool(setting_dict.get('enabled', True))
        self._show_description = bool(setting_dict.get('show_description', True))
        self._show_summary = bool(setting_dict.get('show_summary', True))
        try:
            if self._tag_enabled and dpg.does_item_exist(self._tag_enabled):
                dpg_set_value(self._tag_enabled, self._enabled)
        except (SystemError, AttributeError):
            pass
        self._set_show(self._tag_description, self._show_description)
        self._set_show(self._tag_summary, self._show_summary)
