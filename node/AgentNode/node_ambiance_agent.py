#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AmbianceAgent node — LLM-driven ambiance orchestration via OpenRouter."""

import json
import os
import queue
import threading
import time

import requests
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

OPENROUTER_API_URL = 'https://openrouter.ai/api/v1'
OPENROUTER_MODELS_URL = f'{OPENROUTER_API_URL}/models'

_AGENT_TYPE = 'AmbianceAgent'

_SYSTEM_PROMPT = (
    "You are an expert ambiance designer and poet. "
    "Analyse the provided sensor data and user prompt, then select and configure "
    "the available tools to create the requested atmosphere. "
    "All descriptive text fields in the JSON response (atmosphere, sensory_notes, mood, "
    "poetic_note, rationale, description, and any text passed to actions such as Text2Speech) MUST be "
    "written in the same language as the user_prompt. "
    "The top-level 'description' field AND the 'actions.Text2Speech.text' field MUST contain "
    "a rich, lyrical, poetic narration that explains WHY each fragrance or parameter was chosen — "
    "the emotions, memories, or sensations they evoke — written as a flowing poem or prose, "
    "NOT as a list of ingredients or numeric values. "
    "NEVER recite numeric intensities, percentages, or durations. "
    "NEVER produce a welcome menu or enumerate fragrance options to the user. "
    "The Text2Speech narration is heard by the user as a sensory journey, not a configuration report. "
    "Ensure all text fields are valid UTF-8. "
    "Return ONLY a single valid JSON object matching the required schema — "
    "no markdown fences, no commentary, no chain-of-thought text."
)

_RESPONSE_SCHEMA = {
    "agent": {"type": _AGENT_TYPE},
    "description": (
        "<rich, lyrical, poetic narration explaining WHY the chosen fragrances and parameters "
        "were selected — the emotions, memories, or sensations they evoke. "
        "Written as flowing prose or poetry. NO numeric values. NO enumeration of options.>"
    ),
    "decision": {
        "atmosphere": "<overall atmosphere description>",
        "sensory_notes": "<detailed sensory experience: lights, scents, sounds, voice>",
        "mood": "<emotional quality of the ambiance>",
        "poetic_note": "<evocative, poetic description in 2-3 sentences>",
        "rationale": "<why these specific ingredients create the desired effect>",
    },
    "actions": {
        "Text2Speech": {
            "enabled": True,
            "text": (
                "<same lyrical narration as 'description' — a sensory journey explaining WHY "
                "each fragrance was chosen, what it evokes, never a list of parameters or numbers>"
            ),
        }
    },
}


def _fetch_free_text_models():
    """Fetch free text models from OpenRouter (no image modality required)."""
    fallback = [
        'meta-llama/llama-3.3-70b-instruct:free',
        'google/gemma-3-27b-it:free',
        'mistralai/mistral-7b-instruct:free',
    ]
    try:
        resp = requests.get(OPENROUTER_MODELS_URL, timeout=10)
        resp.raise_for_status()
        models = [m.get('id', '') for m in resp.json().get('data', [])
                  if m.get('id', '').endswith(':free')]
        return models if models else fallback
    except Exception:
        return fallback


def _llm_worker(result_queue, api_key, model, messages):
    """Call OpenRouter chat completions in a background thread."""
    try:
        headers = {
            'Authorization': 'Bearer ' + api_key,
            'Content-Type': 'application/json',
        }
        payload = {'model': model, 'messages': messages}
        resp = requests.post(
            f'{OPENROUTER_API_URL}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (data.get('choices', [{}])[0]
                .get('message', {})
                .get('content', str(data)))
        result_queue.put({'text': text})
    except requests.exceptions.ConnectionError:
        result_queue.put({'error': 'Connection error'})
    except requests.exceptions.Timeout:
        result_queue.put({'error': 'Timeout'})
    except requests.exceptions.HTTPError as e:
        result_queue.put({'error': f'HTTP {e.response.status_code}'})
    except Exception as e:
        result_queue.put({'error': f'Error: {str(e)[:80]}'})


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


class Node(BaseNode):
    _ver = '0.0.1'
    node_label = _AGENT_TYPE
    node_tag = _AGENT_TYPE

    _NUM_INPUTS_DEFAULT = 2
    _MAX_INPUTS = 16

    def __init__(self):
        self.num_inputs = self._NUM_INPUTS_DEFAULT
        self._opencv_setting_dict = {}
        # LLM state
        self._llm_queue = queue.Queue()
        self._llm_thread = None
        self._state = 'READY'       # READY | RUNNING | COOLDOWN
        self._cooldown_start = None
        self._cooldown_s = 30
        self._last_output = {}
        self._available_models = []

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

        # ---- static controls ----
        tag_apikey   = tag + ':ApiKeyValue'
        tag_model    = tag + ':ModelValue'
        tag_prompt   = tag + ':PromptValue'
        tag_execute  = tag + ':ExecuteValue'
        tag_status   = tag + ':StatusValue'
        tag_summary  = tag + ':SummaryValue'
        tag_out      = tag + ':' + self.TYPE_JSON + ':Output01'
        tag_out_val  = tag + ':' + self.TYPE_JSON + ':Output01Value'

        tag_description = tag + ':DescriptionValue'

        # store refs
        self._tag_apikey      = tag_apikey
        self._tag_model       = tag_model
        self._tag_prompt      = tag_prompt
        self._tag_execute     = tag_execute
        self._tag_status      = tag_status
        self._tag_summary     = tag_summary
        self._tag_out_val     = tag_out_val
        self._tag_description = tag_description
        self._node_id         = node_id

        self._available_models = []
        # Fetch models in background so the GUI is not blocked
        threading.Thread(target=self._bg_fetch_models, daemon=True).start()

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            # ── Prompt (top) ──────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':PromptAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_prompt,
                    hint='Prompt',
                    multiline=True,
                    width=w,
                    height=70,
                )

            # ── Description (ambiance text / Text2Speech source) ──────────
            with dpg.node_attribute(
                tag=tag + ':DescriptionAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_description,
                    hint='Description (text for Text2Speech)…',
                    multiline=True,
                    width=w,
                    height=70,
                )

            # ── Dynamic JSON inputs ───────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':InputMgmt',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(label='+ Add Input', width=w,
                               callback=self._cb_add_input,
                               user_data=(node_id, parent))
                dpg.add_button(label='- Remove Input', width=w,
                               callback=self._cb_remove_input,
                               user_data=(node_id, parent))

            for i in range(self.num_inputs):
                self._create_input_slot(tag, parent, i)

            # ── Execute toggle ───────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ExecuteAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=tag_execute,
                    label='Execute Agent',
                    default_value=False,
                )

            # ── API Key ──────────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ApiKeyAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_apikey,
                    hint='OpenRouter API key (sk-or-...)',
                    width=w,
                )

            # ── Model dropdown (no label, auto-populated) ─────────────────
            with dpg.node_attribute(
                tag=tag + ':ModelAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                default_model = self._available_models[0] if self._available_models else ''
                dpg.add_combo(
                    tag=tag_model,
                    items=self._available_models,
                    default_value=default_model,
                    width=w,
                )

            # ── Status ───────────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':StatusAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(tag=tag_status, default_value='[*] READY')

            # ── Decision Summary (JSON) ───────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':SummaryAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_summary,
                    default_value='',
                    multiline=True,
                    width=w,
                    height=130,
                    readonly=True,
                )

            # ── JSON Output ───────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag_out,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(tag=tag_out_val, default_value='JSON Output')

        return self

    # ------------------------------------------------------------------
    # Slot helpers
    # ------------------------------------------------------------------

    def _create_input_slot(self, tag, parent, idx):
        slot_tag = tag + ':' + self.TYPE_JSON + f':Input{idx:02d}'
        if dpg.does_item_exist(slot_tag):
            return
        with dpg.node_attribute(
            tag=slot_tag,
            attribute_type=dpg.mvNode_Attr_Input,
            parent=tag,
        ):
            dpg.add_text(default_value=f'Input {idx + 1}')

    def _cb_add_input(self, sender, app_data, user_data):
        node_id, parent = user_data
        tag = str(node_id) + ':' + self.node_tag
        if self.num_inputs < self._MAX_INPUTS:
            self._create_input_slot(tag, parent, self.num_inputs)
            self.num_inputs += 1

    def _cb_remove_input(self, sender, app_data, user_data):
        node_id, parent = user_data
        tag = str(node_id) + ':' + self.node_tag
        if self.num_inputs > 1:
            slot_tag = tag + ':' + self.TYPE_JSON + f':Input{self.num_inputs - 1:02d}'
            try:
                if dpg.does_item_exist(slot_tag):
                    dpg.delete_item(slot_tag)
                self.num_inputs -= 1
            except (SystemError, AttributeError):
                pass

    def _bg_fetch_models(self):
        """Fetch free models in a background thread, then update the combo."""
        models = _fetch_free_text_models()
        self._available_models = models
        default = models[0] if models else ''
        try:
            dpg.configure_item(self._tag_model, items=models, default_value=default)
        except (SystemError, AttributeError):
            pass

    def _cb_scan_models(self, sender, app_data, user_data=None):
        models = _fetch_free_text_models()
        self._available_models = models
        default = models[0] if models else ''
        try:
            dpg.configure_item(self._tag_model, items=models, default_value=default)
        except (SystemError, AttributeError):
            pass

    def _discover_tools(self, node_result_dict):
        """Return list of tool-template dicts from connected child nodes."""
        tools = []
        seen = set()
        out_tag = self.tag_node_name + ':' + self.TYPE_JSON + ':Output01'

        node_link_list = getattr(node_result_dict, '_node_link_list', [])
        node_instances = getattr(node_result_dict, '_node_instances', {})
        # Defensive: node_instances must support .get(); if it's not a dict, skip discovery
        if not hasattr(node_instances, 'get'):
            return tools

        for link in node_link_list:
            src = link[0] if isinstance(link[0], str) else str(link[0])
            dst = link[1] if isinstance(link[1], str) else str(link[1])
            if src == out_tag or src.startswith(out_tag):
                child_node_id = ':'.join(dst.split(':')[:2])
                if child_node_id in seen:
                    continue
                seen.add(child_node_id)
                child_inst = node_instances.get(child_node_id)
                if child_inst is not None and hasattr(child_inst, 'get_tool_template'):
                    try:
                        tmpl = child_inst.get_tool_template()
                        if tmpl:
                            tools.append(tmpl)
                    except Exception:
                        pass
        return tools

    # ------------------------------------------------------------------
    # update()
    # ------------------------------------------------------------------

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        tag = self.tag_node_name

        # ── Aggregate inputs ─────────────────────────────────────────────
        aggregated = {}
        for i in range(self.num_inputs):
            slot_tag = tag + ':' + self.TYPE_JSON + f':Input{i:02d}'
            for conn in connection_list:
                if conn[1] == slot_tag:
                    src_key = ':'.join(conn[0].split(':')[:2])
                    src_data = node_result_dict.get(src_key)
                    if isinstance(src_data, dict):
                        aggregated[f'input_{i}'] = src_data
                    break

        # ── Read controls ────────────────────────────────────────────────
        try:
            execute = dpg_get_value(self._tag_execute)
        except (SystemError, AttributeError):
            execute = False

        cooldown_s = self._cooldown_s

        # ── Poll LLM thread result ────────────────────────────────────────
        if self._state == 'RUNNING':
            try:
                result = self._llm_queue.get_nowait()
                if 'error' in result:
                    self._set_status(f'[!] ERROR: {result["error"]}')
                    self._state = 'READY'
                else:
                    parsed = self._parse_llm_response(result['text'])
                    if parsed:
                        self._last_output = parsed
                        # Propagate description → description widget + Text2Speech text
                        description = parsed.get('description', '')
                        if description:
                            try:
                                dpg_set_value(self._tag_description, description)
                            except (SystemError, AttributeError):
                                pass
                            # Inject description as text for Text2Speech action
                            if isinstance(parsed.get('actions'), dict):
                                t2s = parsed['actions'].setdefault('Text2Speech', {})
                                if not t2s.get('text'):
                                    t2s['text'] = description
                        decision = parsed.get('decision', {})
                        try:
                            dpg_set_value(self._tag_summary,
                                          json.dumps(decision, indent=2, ensure_ascii=False))
                        except (SystemError, AttributeError):
                            pass
                    self._state = 'COOLDOWN'
                    self._cooldown_start = time.time()
                    self._set_status('[~] COOLDOWN')
            except queue.Empty:
                self._set_status('[>] RUNNING...')

        # ── Cooldown countdown ────────────────────────────────────────────
        if self._state == 'COOLDOWN':
            elapsed = time.time() - self._cooldown_start
            remaining = cooldown_s - elapsed
            if remaining <= 0:
                self._state = 'READY'
                self._set_status('[*] READY')
            else:
                self._set_status(f'[~] COOLDOWN — {int(remaining)} s remaining')

        # ── Trigger new execution ─────────────────────────────────────────
        if execute and self._state == 'READY':
            try:
                api_key = dpg_get_value(self._tag_apikey).strip()
            except (SystemError, AttributeError):
                api_key = ''
            try:
                model = dpg_get_value(self._tag_model).strip()
            except (SystemError, AttributeError):
                model = ''
            try:
                prompt = dpg_get_value(self._tag_prompt).strip()
            except (SystemError, AttributeError):
                prompt = ''

            # If no explicit prompt is typed, look for a 'prompt' key in any
            # connected input JSON (e.g. from a Speech2Text node).
            if not prompt:
                for val in aggregated.values():
                    if isinstance(val, dict) and val.get('prompt'):
                        prompt = str(val['prompt'])
                        break

            if not api_key:
                self._set_status('[!] ERROR: API key missing')
            elif not model:
                self._set_status('[!] ERROR: No model selected')
            else:
                # Discover tools from child node instances
                tools = self._discover_tools(node_result_dict)

                messages = self._build_messages(aggregated, prompt, tools)
                self._state = 'RUNNING'
                self._set_status('[>] RUNNING...')
                self._llm_thread = threading.Thread(
                    target=_llm_worker,
                    args=(self._llm_queue, api_key, model, messages),
                    daemon=True,
                )
                self._llm_thread.start()

        return {'image': None, 'json': self._last_output, 'audio': None}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, text):
        try:
            dpg_set_value(self._tag_status, text)
        except (SystemError, AttributeError):
            pass

    def _build_messages(self, data, prompt, tools):
        user_content = {
            'sensor_data': data,
            'user_prompt': prompt,
            'available_tools': tools,
            'response_schema': _RESPONSE_SCHEMA,
            'instruction': (
                'Based on the sensor data and user prompt, decide which tools to use '
                'and with which parameters. Only use tools listed in available_tools. '
                'Return a single JSON object matching response_schema exactly. '
                'The "description" field and "actions.Text2Speech.text" field MUST be '
                'a lyrical, poetic narration that explains WHY each chosen fragrance or setting '
                'was selected — what emotion, memory, or sensation it evokes — '
                'written as flowing prose or a short poem. '
                'Do NOT list fragrance options, do NOT recite numeric values, '
                'do NOT produce a welcome message or configuration menu.'
            ),
        }
        return [
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': json.dumps(user_content, ensure_ascii=False)},
        ]

    @staticmethod
    def _parse_llm_response(text):
        """Extract JSON from LLM response, stripping markdown fences if present."""
        text = text.strip()
        # Strip ```json ... ``` fences
        if text.startswith('```'):
            lines = text.splitlines()
            text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object within the text
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag = self.tag_node_name
        pos = dpg.get_item_pos(tag)
        d = {
            'ver': self._ver,
            'pos': pos,
            'num_inputs': self.num_inputs,
        }
        for k in [self._tag_apikey, self._tag_model, self._tag_prompt,
                  self._tag_execute, self._tag_description]:
            try:
                d[k] = dpg_get_value(k)
            except (SystemError, AttributeError):
                pass
        return d

    def set_setting_dict(self, node_id, setting_dict):
        self.num_inputs = setting_dict.get('num_inputs', self._NUM_INPUTS_DEFAULT)
        for k in [self._tag_apikey, self._tag_model, self._tag_prompt,
                  self._tag_execute, self._tag_description]:
            if k in setting_dict:
                try:
                    dpg_set_value(k, setting_dict[k])
                except (SystemError, AttributeError):
                    pass
