#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AmbianceAgent node — LLM-driven ambiance orchestration via OpenRouter, Google AI Studio, or Groq."""

import copy
import hashlib
import json
import logging
import os
import queue
import threading
import time

import requests
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

_LOG = logging.getLogger(__name__)

OPENROUTER_API_URL = 'https://openrouter.ai/api/v1'
OPENROUTER_MODELS_URL = f'{OPENROUTER_API_URL}/models'

GOOGLE_AI_API_URL = 'https://generativelanguage.googleapis.com/v1beta'
GOOGLE_AI_MODELS_URL = f'{GOOGLE_AI_API_URL}/models'

GROQ_API_URL = 'https://api.groq.com/openai/v1'
GROQ_MODELS_URL = f'{GROQ_API_URL}/models'

PROVIDER_OPENROUTER = 'OpenRouter'
PROVIDER_GOOGLE_AI = 'Google AI Studio'
PROVIDER_GROQ = 'Groq'
PROVIDERS = [PROVIDER_OPENROUTER, PROVIDER_GOOGLE_AI, PROVIDER_GROQ]

GROQ_DEFAULT_MODELS = [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'llama3-70b-8192',
    'llama3-8b-8192',
    'mixtral-8x7b-32768',
    'gemma2-9b-it',
]

GOOGLE_AI_DEFAULT_MODELS = [
    'gemini-2.0-flash-lite',
    'gemini-2.0-flash',
    'gemini-1.5-flash-8b',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
]

_AGENT_TYPE = 'AmbianceAgent'

_SYSTEM_PROMPT = (
    "You are an expert ambiance designer and poet. "
    "Analyse the provided sensor data and user prompt, then select and configure "
    "the available tools to create the requested atmosphere. "
    "All descriptive text fields in the JSON response (atmosphere, sensory_notes, mood, "
    "poetic_note, rationale, description, and any text passed to actions such as Text2Speech) MUST be "
    "written in the same language as the user_prompt. "
    "The top-level 'description' field AND the 'actions.Text2Speech.text' field MUST contain "
    "a rich, lyrical, poetic narration that explains WHY each parameter across ALL configured action nodes "
    "was chosen — what emotion, memory, or sensation each setting evokes — "
    "written as a flowing poem or prose. "
    "Cover every configured parameter (fragrances, lighting, sound, temperature, etc.) "
    "by explaining its sensory or emotional role, not by restating its numeric value. "
    "NEVER recite numeric intensities, percentages, durations, or raw parameter values. "
    "NEVER produce a welcome menu or enumerate available options to the user. "
    "The Text2Speech narration is heard by the user as a sensory journey, not a configuration report. "
    "Ensure all text fields are valid UTF-8. "
    "Return ONLY a single valid JSON object matching the required schema — "
    "no markdown fences, no commentary, no chain-of-thought text."
)

_RESPONSE_SCHEMA = {
    "agent": {"type": _AGENT_TYPE},
    "description": (
        "<rich, lyrical, poetic narration explaining WHY each parameter across all configured "
        "action nodes was chosen — the emotion, memory, or sensation each setting evokes. "
        "Cover every parameter (fragrances, lighting, sound, temperature, etc.) poetically. "
        "NO numeric values. NO enumeration of available options.>"
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
            "enabled": "<boolean — true to activate vocalization, false to mute>",
            "text": (
                "<same lyrical narration as 'description' — a sensory journey explaining WHY "
                "each parameter across all configured action nodes was chosen, "
                "what emotion or sensation it evokes. Never list parameters by value or number.>"
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


def _fetch_google_ai_models(api_key=''):
    """Fetch available Gemini text models from Google AI Studio."""
    if api_key:
        try:
            resp = requests.get(
                GOOGLE_AI_MODELS_URL,
                params={'key': api_key},
                timeout=10,
            )
            resp.raise_for_status()
            models = [
                m['name'].replace('models/', '')
                for m in resp.json().get('models', [])
                if 'generateContent' in m.get('supportedGenerationMethods', [])
                and 'gemini' in m.get('name', '').lower()
            ]
            if models:
                return models
        except Exception:
            pass
    return list(GOOGLE_AI_DEFAULT_MODELS)


def _llm_worker(result_queue, api_key, model, messages):
    """Call OpenRouter chat completions in a background thread."""
    _LOG.info('[AmbianceAgent] LLM request → model=%s  messages=%d', model, len(messages))
    user_msg = next((m['content'] for m in messages if m['role'] == 'user'), '')
    _LOG.debug('[AmbianceAgent] LLM user payload: %s', user_msg[:500])
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
        _LOG.info('[AmbianceAgent] LLM response received (%d chars): %s...', len(text), text[:200])
        result_queue.put({'text': text})
    except requests.exceptions.ConnectionError as e:
        _LOG.error('[AmbianceAgent] LLM connection error: %s', e)
        result_queue.put({'error': 'Connection error'})
    except requests.exceptions.Timeout:
        _LOG.error('[AmbianceAgent] LLM request timed out after 60 s')
        result_queue.put({'error': 'Timeout'})
    except requests.exceptions.HTTPError as e:
        _LOG.error('[AmbianceAgent] LLM HTTP error %s: %s', e.response.status_code, e.response.text[:300])
        result_queue.put({'error': f'HTTP {e.response.status_code}'})
    except Exception as e:
        _LOG.error('[AmbianceAgent] LLM unexpected error: %s', e, exc_info=True)
        result_queue.put({'error': f'Error: {str(e)[:80]}'})


def _google_ai_worker(result_queue, api_key, model, messages):
    """Call Google AI Studio (Gemini) generateContent in a background thread."""
    _LOG.info('[AmbianceAgent] Google AI request → model=%s  messages=%d', model, len(messages))
    try:
        # Convert OpenAI-style messages to Gemini format
        contents = []
        system_text = None
        has_user_message = False
        for m in messages:
            role = m.get('role', 'user')
            content = m.get('content', '')
            if role == 'system':
                system_text = content
            elif role == 'user':
                contents.append({'role': 'user', 'parts': [{'text': content}]})
                has_user_message = True
            elif role == 'assistant':
                contents.append({'role': 'model', 'parts': [{'text': content}]})

        # If only a system message exists with no user messages, treat it as user
        if not has_user_message and system_text:
            contents = [{'role': 'user', 'parts': [{'text': system_text}]}]
            system_text = None  # already used as the sole user turn; don't duplicate

        payload = {'contents': contents}
        if system_text and has_user_message:
            payload['systemInstruction'] = {'parts': [{'text': system_text}]}

        url = f'{GOOGLE_AI_API_URL}/models/{model}:generateContent'
        resp = requests.post(
            url,
            params={'key': api_key},
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (data.get('candidates', [{}])[0]
                .get('content', {})
                .get('parts', [{}])[0]
                .get('text', str(data)))
        _LOG.info('[AmbianceAgent] Google AI response received (%d chars): %s...', len(text), text[:200])
        result_queue.put({'text': text})
    except requests.exceptions.ConnectionError as e:
        _LOG.error('[AmbianceAgent] Google AI connection error: %s', e)
        result_queue.put({'error': 'Connection error'})
    except requests.exceptions.Timeout:
        _LOG.error('[AmbianceAgent] Google AI request timed out after 60 s')
        result_queue.put({'error': 'Timeout'})
    except requests.exceptions.HTTPError as e:
        _LOG.error('[AmbianceAgent] Google AI HTTP error %s: %s', e.response.status_code, e.response.text[:300])
        result_queue.put({'error': f'HTTP {e.response.status_code}'})
    except Exception as e:
        _LOG.error('[AmbianceAgent] Google AI unexpected error: %s', e, exc_info=True)
        result_queue.put({'error': f'Error: {str(e)[:80]}'})


def _fetch_groq_models(api_key=''):
    """Fetch available chat models from Groq."""
    if api_key:
        try:
            resp = requests.get(
                GROQ_MODELS_URL,
                headers={'Authorization': 'Bearer ' + api_key},
                timeout=10,
            )
            resp.raise_for_status()
            models = [
                m['id'] for m in resp.json().get('data', [])
                if m.get('id') and m.get('object') == 'model'
                and not any(exc in m['id'] for exc in ('whisper', 'tts', 'speech'))
            ]
            if models:
                return sorted(models)
        except Exception:
            pass
    return list(GROQ_DEFAULT_MODELS)


def _groq_worker(result_queue, api_key, model, messages):
    """Call Groq chat completions (OpenAI-compatible) in a background thread."""
    _LOG.info('[AmbianceAgent] Groq request → model=%s  messages=%d', model, len(messages))
    try:
        headers = {
            'Authorization': 'Bearer ' + api_key,
            'Content-Type': 'application/json',
        }
        payload = {'model': model, 'messages': messages}
        resp = requests.post(
            f'{GROQ_API_URL}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (data.get('choices', [{}])[0]
                .get('message', {})
                .get('content', str(data)))
        _LOG.info('[AmbianceAgent] Groq response received (%d chars): %s...', len(text), text[:200])
        result_queue.put({'text': text})
    except requests.exceptions.ConnectionError as e:
        _LOG.error('[AmbianceAgent] Groq connection error: %s', e)
        result_queue.put({'error': 'Connection error'})
    except requests.exceptions.Timeout:
        _LOG.error('[AmbianceAgent] Groq request timed out after 60 s')
        result_queue.put({'error': 'Timeout'})
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        _HTTP_HINTS = {401: 'invalid API key', 429: 'rate limited', 403: 'forbidden'}
        hint = _HTTP_HINTS.get(status, e.response.text[:80])
        _LOG.error('[AmbianceAgent] Groq HTTP error %s: %s', status, e.response.text[:300])
        result_queue.put({'error': f'HTTP {status} – {hint}'})
    except Exception as e:
        _LOG.error('[AmbianceAgent] Groq unexpected error: %s', e, exc_info=True)
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
        self._state_lock = threading.Lock()
        self._cooldown_start = None
        self._cooldown_s = 30
        self._error_cooldown_s = 15
        self._last_output = {}
        self._available_models = []
        self._tag_provider = None
        self._last_input_hash = None
        # Start/Stop button state
        self._execute_active = False   # True when user pressed Start
        self._tag_startstop = None
        self._cancel_flag = threading.Event()  # set to request cancellation

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
        tag_provider = tag + ':ProviderValue'
        tag_prompt   = tag + ':PromptValue'
        tag_startstop = tag + ':StartStopBtn'
        tag_status   = tag + ':StatusValue'
        tag_summary  = tag + ':SummaryValue'
        tag_out      = tag + ':' + self.TYPE_JSON + ':Output01'
        tag_out_val  = tag + ':' + self.TYPE_JSON + ':Output01Value'

        tag_description = tag + ':DescriptionValue'

        # store refs
        self._tag_apikey      = tag_apikey
        self._tag_model       = tag_model
        self._tag_provider    = tag_provider
        self._tag_prompt      = tag_prompt
        self._tag_startstop   = tag_startstop
        self._tag_status      = tag_status
        self._tag_summary     = tag_summary
        self._tag_out_val     = tag_out_val
        self._tag_description = tag_description
        self._node_id         = node_id

        self._available_models = []
        # Fetch models in background so the GUI is not blocked
        threading.Thread(target=self._bg_fetch_models, daemon=True).start()

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

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

            # ── Start / Stop button ──────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ExecuteAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=tag_startstop,
                    label='▶ Start',
                    width=w,
                    callback=self._cb_startstop,
                )
                # Reflect any pre-restored state (set_setting_dict called before add_node)
                self._update_startstop_ui()

            # ── Provider dropdown ────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ProviderAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=tag_provider,
                    items=PROVIDERS,
                    default_value=PROVIDER_OPENROUTER,
                    width=w,
                    callback=self._cb_provider_changed,
                )

            # ── API Key ──────────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ApiKeyAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_apikey,
                    hint='sk-or-... (OpenRouter) / AIza... (Google AI) / gsk_... (Groq)',
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
        """Fetch models in a background thread based on current provider, then update the combo."""
        provider = self._get_current_provider()
        if provider == PROVIDER_GOOGLE_AI:
            api_key = ''
            try:
                api_key = dpg_get_value(self._tag_apikey).strip()
            except (SystemError, AttributeError):
                pass
            models = _fetch_google_ai_models(api_key)
        elif provider == PROVIDER_GROQ:
            api_key = ''
            try:
                api_key = dpg_get_value(self._tag_apikey).strip()
            except (SystemError, AttributeError):
                pass
            models = _fetch_groq_models(api_key)
        else:
            models = _fetch_free_text_models()
        self._available_models = models
        default = models[0] if models else ''
        try:
            dpg.configure_item(self._tag_model, items=models, default_value=default)
        except (SystemError, AttributeError):
            pass

    def _cb_provider_changed(self, sender, app_data, user_data=None):
        """Called when the provider dropdown changes — refresh model list."""
        threading.Thread(target=self._bg_fetch_models, daemon=True).start()

    def _cb_scan_models(self, sender, app_data, user_data=None):
        threading.Thread(target=self._bg_fetch_models, daemon=True).start()

    def _cb_startstop(self, sender, app_data, user_data=None):
        """Toggle Start/Stop state. Start also triggers a model scan."""
        if not self._execute_active:
            # Switch to active (Start)
            self._execute_active = True
            self._cancel_flag.clear()
            self._update_startstop_ui()
            # Auto-scan models when starting
            threading.Thread(target=self._bg_fetch_models, daemon=True).start()
        else:
            # Switch to stopped (Stop) — cancel any hanging request
            self._execute_active = False
            self._cancel_flag.set()
            with self._state_lock:
                if self._state == 'RUNNING':
                    # Put a sentinel so update() sees the cancellation immediately
                    try:
                        self._llm_queue.put_nowait({'error': 'Cancelled by user'})
                    except Exception:
                        pass
                    self._state = 'READY'
                    self._set_status('[*] READY')
            self._update_startstop_ui()

    def _update_startstop_ui(self):
        """Update the Start/Stop button label to reflect current state."""
        try:
            if self._tag_startstop and dpg.does_item_exist(self._tag_startstop):
                if self._execute_active:
                    dpg.configure_item(self._tag_startstop, label='■ Stop')
                else:
                    dpg.configure_item(self._tag_startstop, label='▶ Start')
        except (SystemError, AttributeError):
            pass

    def _get_current_provider(self):
        """Return the currently selected provider string."""
        try:
            if self._tag_provider:
                return dpg_get_value(self._tag_provider)
        except (SystemError, AttributeError):
            pass
        return PROVIDER_OPENROUTER

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
                            _LOG.debug('[AmbianceAgent] Discovered tool: %s', tmpl.get('tool_name', child_node_id))
                    except Exception as exc:
                        _LOG.warning('[AmbianceAgent] Could not get tool template from %s: %s', child_node_id, exc)
        _LOG.info('[AmbianceAgent] Tools discovered: %s', [t.get('tool_name') for t in tools])
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
                        _LOG.debug('[AmbianceAgent] input_%d ← %s : %s', i, src_key, src_data)
                    else:
                        _LOG.debug('[AmbianceAgent] input_%d ← %s : no dict data (got %r)', i, src_key, src_data)
                    break

        # ── Read controls ────────────────────────────────────────────────
        execute = self._execute_active

        cooldown_s = self._cooldown_s

        # ── Poll LLM thread result ────────────────────────────────────────
        if self._state == 'RUNNING':
            try:
                result = self._llm_queue.get_nowait()
                if 'error' in result:
                    _LOG.error('[AmbianceAgent] LLM error: %s', result['error'])
                    self._set_status(f'[!] ERROR: {result["error"]}')
                    self._state = 'COOLDOWN'
                    self._cooldown_start = time.time()
                    self._cooldown_current_s = self._error_cooldown_s
                else:
                    _LOG.info('[AmbianceAgent] LLM response received — parsing JSON...')
                    parsed = self._parse_llm_response(result['text'])
                    if parsed:
                        actions = list((parsed.get('actions') or {}).keys())
                        _LOG.info('[AmbianceAgent] LLM response parsed OK — actions: %s', actions)
                        _LOG.debug('[AmbianceAgent] LLM full parsed output: %s',
                                   json.dumps(parsed, ensure_ascii=False)[:500])
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
                    else:
                        _LOG.warning('[AmbianceAgent] Failed to parse LLM response as JSON — raw: %s',
                                     result['text'][:300])
                    self._state = 'COOLDOWN'
                    self._cooldown_start = time.time()
                    self._cooldown_current_s = cooldown_s
                    self._set_status('[~] COOLDOWN')
            except queue.Empty:
                self._set_status('[>] RUNNING...')

        # ── Cooldown countdown ────────────────────────────────────────────
        if self._state == 'COOLDOWN':
            elapsed = time.time() - self._cooldown_start
            remaining = getattr(self, '_cooldown_current_s', cooldown_s) - elapsed
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
                for input_key, val in aggregated.items():
                    if isinstance(val, dict) and val.get('prompt'):
                        prompt = str(val['prompt'])
                        _LOG.info('[AmbianceAgent] Prompt picked up from %s: %r', input_key, prompt)
                        break

            _LOG.info('[AmbianceAgent] Execute triggered — model=%r  prompt=%r  aggregated_keys=%s',
                      model, prompt, list(aggregated.keys()))

            # Skip LLM call if all connected inputs are empty JSON objects
            if aggregated and all(v == {} for v in aggregated.values()):
                _LOG.debug('[AmbianceAgent] All inputs are empty JSON — skipping LLM call')
                return {'image': None, 'json': self._last_output, 'audio': None}

            if not api_key:
                _LOG.error('[AmbianceAgent] API key missing — cannot call LLM')
                self._set_status('[!] ERROR: API key missing')
            elif not model:
                _LOG.error('[AmbianceAgent] No model selected — cannot call LLM')
                self._set_status('[!] ERROR: No model selected')
            else:
                # ── MD5 deduplication — skip if inputs unchanged ──────────
                input_hash = hashlib.md5(
                    json.dumps({'prompt': prompt, 'inputs': aggregated},
                               sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
                if input_hash == self._last_input_hash:
                    _LOG.debug('[AmbianceAgent] Inputs unchanged (hash=%s) — skipping LLM call', input_hash)
                    return {'image': None, 'json': self._last_output, 'audio': None}
                self._last_input_hash = input_hash

                # Discover tools from child node instances
                tools = self._discover_tools(node_result_dict)

                messages = self._build_messages(aggregated, prompt, tools)
                self._state = 'RUNNING'
                self._set_status('[>] RUNNING...')
                provider = self._get_current_provider()
                if provider == PROVIDER_GOOGLE_AI:
                    worker = _google_ai_worker
                elif provider == PROVIDER_GROQ:
                    worker = _groq_worker
                else:
                    worker = _llm_worker
                self._llm_thread = threading.Thread(
                    target=worker,
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
        # Build a dynamic response_schema that includes an entry in 'actions' for each discovered tool
        schema = copy.deepcopy(_RESPONSE_SCHEMA)
        for tool in tools:
            tool_name = tool.get('tool_name')
            if tool_name and tool_name not in schema['actions']:
                # Provide the tool's parameter structure as a hint to the LLM
                schema['actions'][tool_name] = tool.get('parameters', {})
        _LOG.info('[AmbianceAgent] Building messages — tools=%s  prompt=%r',
                  [t.get('tool_name') for t in tools], prompt[:120] if prompt else '')
        user_content = {
            'sensor_data': data,
            'user_prompt': prompt,
            'available_tools': tools,
            'response_schema': schema,
            'instruction': (
                'Based on the sensor data and user prompt, decide which tools to use '
                'and with which parameters. Only use tools listed in available_tools. '
                'Return a single JSON object matching response_schema exactly. '
                'For each tool you use, add an entry under "actions" keyed by the tool_name '
                'and fill in all required parameters as described by the tool template. '
                'The "description" field and "actions.Text2Speech.text" field MUST be '
                'a lyrical, poetic narration that explains WHY each parameter across ALL '
                'configured action nodes was selected — what emotion, memory, or sensation '
                'each setting evokes — written as flowing prose or a short poem. '
                'Cover every parameter poetically (fragrances, lighting, sound, temperature, etc.). '
                'Do NOT recite numeric values or raw parameter names, '
                'do NOT produce a welcome message, option list, or configuration menu.'
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
            'execute_active': self._execute_active,
        }
        for k in [self._tag_apikey, self._tag_model, self._tag_provider,
                  self._tag_prompt, self._tag_description]:
            try:
                d[k] = dpg_get_value(k)
            except (SystemError, AttributeError):
                pass
        return d

    def set_setting_dict(self, node_id, setting_dict):
        self.num_inputs = setting_dict.get('num_inputs', self._NUM_INPUTS_DEFAULT)
        self._execute_active = setting_dict.get('execute_active', False)
        self._update_startstop_ui()
        for k in [self._tag_apikey, self._tag_model, self._tag_provider,
                  self._tag_prompt, self._tag_description]:
            if k in setting_dict:
                try:
                    dpg_set_value(k, setting_dict[k])
                except (SystemError, AttributeError):
                    pass
