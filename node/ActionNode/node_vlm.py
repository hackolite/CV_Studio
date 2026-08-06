#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import multiprocessing
import queue
import time
from collections import deque

import cv2
import numpy as np
import requests
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode

OPENROUTER_API_URL = 'https://openrouter.ai/api/v1'
OPENROUTER_MODELS_URL = f'{OPENROUTER_API_URL}/models'


def fetch_free_vision_models():
    """Fetch free vision-capable models from OpenRouter.

    Returns a list of model IDs (strings) ending with ``:free`` that declare
    an image input modality.  Falls back to a hard-coded minimal list when the
    network is unavailable.
    """
    fallback = [
        'meta-llama/llama-4-scout:free',
        'google/gemini-2.0-flash-exp:free',
        'qwen/qwen2.5-vl-72b-instruct:free',
    ]
    try:
        response = requests.get(OPENROUTER_MODELS_URL, timeout=10)
        response.raise_for_status()
        data = response.json().get('data', [])
        vision_free = []
        for model in data:
            model_id = model.get('id', '')
            if not model_id.endswith(':free'):
                continue
            arch = model.get('architecture', {})
            modality = arch.get('input_modalities') or arch.get('modality', '')
            if isinstance(modality, str):
                modality = [modality]
            if any('image' in m.lower() or 'vision' in m.lower() for m in modality):
                vision_free.append(model_id)
        return vision_free if vision_free else fallback
    except Exception:
        return fallback


def _vlm_request_worker(result_queue, api_key, model, prompt, frame):
    """Run an OpenRouter VLM request in a subprocess.

    Runs entirely outside the main process so the GUI event loop is never
    blocked.  Results are returned through *result_queue* as a dict:
      - ``{'text': <str>}`` on success
      - ``{'error': <str>}`` on failure
    """
    try:
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            result_queue.put({'error': 'Encode error'})
            return
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        headers = {
            'Authorization': 'Bearer ' + api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{img_b64}',
                            },
                        },
                        {
                            'type': 'text',
                            'text': prompt,
                        },
                    ],
                }
            ],
        }
        response = requests.post(
            f'{OPENROUTER_API_URL}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        result_text = (
            data.get('choices', [{}])[0]
            .get('message', {})
            .get('content', str(data))
        )
        result_queue.put({'text': result_text})
    except requests.exceptions.ConnectionError:
        result_queue.put({'error': 'Connection error'})
    except requests.exceptions.Timeout:
        result_queue.put({'error': 'Timeout'})
    except requests.exceptions.HTTPError as e:
        result_queue.put({'error': f'HTTP {e.response.status_code}'})
    except Exception as e:
        result_queue.put({'error': f'Error: {str(e)[:60]}'})


class FactoryNode:
    node_label = 'VLM'
    node_tag = 'VLM'

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Adds a VLM (Vision Language Model) node using OpenRouter free models."""

        # Fetch available free vision models at node creation time
        available_models = fetch_free_vision_models()

        node = VLMNode()
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        node._available_models = available_models

        tag_node_name = node.tag_node_name

        # JSON Input (boolean trigger)
        node.tag_node_input_json_name = tag_node_name + ':' + node.TYPE_JSON + ':InputJson'
        node.tag_node_input_json_value_name = tag_node_name + ':' + node.TYPE_JSON + ':InputJsonValue'

        # Image Input
        node.tag_node_input_image_name = tag_node_name + ':' + node.TYPE_IMAGE + ':InputImage'
        node.tag_node_input_image_value_name = tag_node_name + ':' + node.TYPE_IMAGE + ':InputImageValue'

        # Image Output (text canvas)
        node.tag_node_output_image_name = tag_node_name + ':' + node.TYPE_IMAGE + ':OutputImage'
        node.tag_node_output_image_value_name = tag_node_name + ':' + node.TYPE_IMAGE + ':OutputImageValue'

        # JSON Text Output
        node.tag_node_output_json_name = tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        # Canvas image display widget (separate from texture tag to allow dynamic height)
        node.tag_node_output_canvas_image_name = tag_node_name + ':CanvasImage'

        # Static widget tags
        tag_node_model_name = tag_node_name + ':Model'
        tag_node_model_value_name = tag_node_name + ':ModelValue'

        tag_node_apikey_name = tag_node_name + ':ApiKey'
        tag_node_apikey_value_name = tag_node_name + ':ApiKeyValue'

        tag_node_prompt_name = tag_node_name + ':Prompt'
        tag_node_prompt_value_name = tag_node_name + ':PromptValue'

        tag_node_delay_name = tag_node_name + ':Delay'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        tag_node_countdown_name = tag_node_name + ':Countdown'
        tag_node_countdown_value_name = tag_node_name + ':CountdownValue'

        tag_node_status_name = tag_node_name + ':Status'
        tag_node_status_value_name = tag_node_name + ':StatusValue'

        # Set opencv settings
        node._opencv_setting_dict = opencv_setting_dict or {}
        small_window_w = node._opencv_setting_dict.get('process_width', 240)

        # Text canvas for the output
        canvas_w = small_window_w
        node.TEXT_CANVAS_W = canvas_w
        canvas_h = VLMNode.TEXT_CANVAS_H   # fixed height – never changes at runtime
        black_canvas = np.zeros((canvas_h, canvas_w, 3))
        canvas_texture = node.convert_cv_to_dpg(black_canvas, canvas_w, canvas_h)

        # Dummy texture for the (unused) input slot – kept so connection logic works
        small_window_h = node._opencv_setting_dict.get('process_height', 135)
        black_image = np.zeros((small_window_h, small_window_w, 3))
        dummy_texture = node.convert_cv_to_dpg(black_image, small_window_w, small_window_h)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                dummy_texture,
                tag=node.tag_node_input_image_value_name,
                format=dpg.mvFormat_Float_rgb,
            )
            dpg.add_raw_texture(
                canvas_w,
                canvas_h,
                canvas_texture,
                tag=node.tag_node_output_image_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):
            # JSON boolean trigger input
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Trigger JSON (bool)',
                )

            # Image input (hidden preview – connector still available)
            with dpg.node_attribute(
                tag=node.tag_node_input_image_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(default_value='Image input')

            # OpenRouter API key field
            with dpg.node_attribute(
                tag=tag_node_apikey_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_node_apikey_value_name,
                    hint='OpenRouter API key (sk-or-...)',
                    default_value=VLMNode.DEFAULT_API_KEY,
                    width=240,
                )

            # Model combobox (populated with free vision models fetched at startup)
            with dpg.node_attribute(
                tag=tag_node_model_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                default_model = available_models[0] if available_models else ''
                dpg.add_combo(
                    tag=tag_node_model_value_name,
                    items=available_models,
                    default_value=default_model,
                    width=240,
                )

            # Prompt / question field
            with dpg.node_attribute(
                tag=tag_node_prompt_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_node_prompt_value_name,
                    default_value=VLMNode.DEFAULT_PROMPT,
                    width=240,
                    multiline=True,
                    height=60,
                )

            # Insensitivity delay slider
            with dpg.node_attribute(
                tag=tag_node_delay_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=tag_node_delay_value_name,
                    label='Delay (s)',
                    default_value=VLMNode.DEFAULT_INSENSITIVITY_DELAY,
                    min_value=0.0,
                    max_value=60.0,
                    width=180,
                )

            # Countdown display (updated each frame during insensitivity period)
            with dpg.node_attribute(
                tag=tag_node_countdown_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=tag_node_countdown_value_name,
                    default_value='',
                )

            # Status indicator
            with dpg.node_attribute(
                tag=tag_node_status_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=tag_node_status_value_name,
                    default_value='Ready',
                )

            # Text-canvas output (image connector carrying the rendered text)
            with dpg.node_attribute(
                tag=node.tag_node_output_image_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(
                    node.tag_node_output_image_value_name,
                    tag=node.tag_node_output_canvas_image_name,
                    width=canvas_w,
                    height=canvas_h,
                )

            # JSON text output
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_button(
                    tag=node.tag_node_output_json_value_name,
                    label='Text',
                    width=240,
                    enabled=False,
                )

        return node


class VLMNode(BaseNode):
    _ver = '0.0.3'

    DEFAULT_API_KEY = ''
    DEFAULT_PROMPT = 'Describe this image in detail.'
    DEFAULT_INSENSITIVITY_DELAY = 0.0

    MAX_LINES = 50
    TEXT_CANVAS_W = 220       # canvas width (overridden per-node in add_node)
    TEXT_CANVAS_H = 400       # fixed canvas height – never resized dynamically
    TEXT_FONT_SCALE_MAX = 1.0 # maximum font scale (used when text is short)
    TEXT_FONT_SCALE_MIN = 0.30
    TEXT_THICKNESS = 1
    TEXT_MARGIN = 8

    def __init__(self):
        super().__init__()
        self.node_label = 'VLM'
        self.node_tag = 'VLM'
        self._available_models = []
        self._last_result_text = ''
        self._last_prompt = ''
        self._text_lines = deque(maxlen=self.MAX_LINES)
        self._is_requesting = False
        self._request_process = None
        self._result_queue = None
        self._pending_frame = None
        self._insensitivity_end_time = 0

    def _encode_image(self, frame):
        """Encode a BGR OpenCV frame to a base64 JPEG string."""
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            return None
        return base64.b64encode(buffer).decode('utf-8')

    @staticmethod
    def _word_color(word):
        """Return a BGR color for a word based on its semantic category.

        - Numbers / percentages  → gold
        - ALL-CAPS abbreviations → orange
        - Capitalised words      → light cyan (possible proper nouns / key terms)
        - Everything else        → white
        """
        clean = word.strip('.,!?;:()[]{}"\'-_*#')
        if not clean:
            return (255, 255, 255)
        # Numbers (integers, floats, percentages)
        try:
            float(clean.rstrip('%'))
            return (30, 200, 255)   # gold / amber (BGR)
        except ValueError:
            pass
        # ALL-CAPS abbreviations (≥ 2 alpha chars, e.g. AI, VLM, GPS)
        if len(clean) >= 2 and clean.isupper() and clean.isalpha():
            return (0, 165, 255)    # orange (BGR)
        # Capitalised words (proper nouns, start of key phrases)
        if len(clean) >= 2 and clean[0].isupper():
            return (180, 230, 100)  # soft lime-green (BGR)
        return (255, 255, 255)      # white

    def _wrap_at_scale(self, text, max_width, scale):
        """Word-wrap *text* so each line fits within *max_width* pixels at *scale*."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        words = text.split()
        lines = []
        current = ''
        for word in words:
            test = (current + ' ' + word).strip()
            (tw, _), _ = cv2.getTextSize(test, font, scale, self.TEXT_THICKNESS)
            if tw <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines if lines else ['']

    def _wrap_text_to_lines(self, text, max_width):
        """Wrap at the maximum font scale (kept for legacy compatibility)."""
        return self._wrap_at_scale(text, max_width, self.TEXT_FONT_SCALE_MAX)

    def _render_text_canvas(self):
        """Render the last VLM response on a fixed-size canvas.

        The font scale is computed iteratively so that all lines fit inside
        the canvas height.  Each word is coloured by category (numbers, proper
        nouns, abbreviations) to improve readability.  The canvas size is
        always TEXT_CANVAS_H × TEXT_CANVAS_W – it is never resized.
        """
        canvas = np.zeros((self.TEXT_CANVAS_H, self.TEXT_CANVAS_W, 3), dtype=np.uint8)
        text = self._last_result_text
        if not text:
            return canvas

        font = cv2.FONT_HERSHEY_SIMPLEX
        margin = self.TEXT_MARGIN
        max_w = self.TEXT_CANVAS_W - 2 * margin
        avail_h = self.TEXT_CANVAS_H - 2 * margin

        # ── iterative adaptive font scale ────────────────────────────────────
        scale = self.TEXT_FONT_SCALE_MAX
        lines = self._wrap_at_scale(text, max_w, scale)
        for _ in range(5):
            n = max(len(lines), 1)
            (_, ch), bl = cv2.getTextSize('Mg', font, scale, self.TEXT_THICKNESS)
            lh = ch + bl + max(3, int(ch * 0.25))   # text height + descender + spacing
            new_scale = scale * (avail_h / (n * lh))
            new_scale = max(self.TEXT_FONT_SCALE_MIN, min(self.TEXT_FONT_SCALE_MAX, new_scale))
            if abs(new_scale - scale) < 0.02:
                break
            scale = new_scale
            lines = self._wrap_at_scale(text, max_w, scale)

        # ── final line-height at the chosen scale ────────────────────────────
        (_, ch), bl = cv2.getTextSize('Mg', font, scale, self.TEXT_THICKNESS)
        lh = ch + bl + max(3, int(ch * 0.25))
        thickness = max(1, int(scale * 2))

        # Cache wrapped lines for any external callers that inspect _text_lines
        self._text_lines = deque(lines, maxlen=self.MAX_LINES)

        # ── render word-by-word with per-word colours ────────────────────────
        for i, line in enumerate(lines):
            y = margin + ch + i * lh
            if y > self.TEXT_CANVAS_H - margin:
                break
            x = margin
            for word in line.split():
                color = self._word_color(word)
                cv2.putText(canvas, word, (x, y), font, scale, color,
                            thickness, cv2.LINE_AA)
                (ww, _), _ = cv2.getTextSize(word + ' ', font, scale, thickness)
                x += ww

        return canvas

    def _draw_text_on_image(self, frame, text):
        """Draw wrapped text overlay on a copy of the frame (kept for legacy use)."""
        output = frame.copy()
        h, w = output.shape[:2]

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        color = (255, 255, 255)
        bg_color = (0, 0, 0)
        line_height = 20
        margin = 8

        # Wrap text manually
        words = text.split()
        lines = []
        current_line = ''
        max_width = w - 2 * margin

        for word in words:
            test_line = (current_line + ' ' + word).strip()
            (tw, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
            if tw <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Draw semi-transparent background for text area
        overlay = output.copy()
        text_area_h = len(lines) * line_height + 2 * margin
        cv2.rectangle(overlay, (0, 0), (w, text_area_h), bg_color, -1)
        cv2.addWeighted(overlay, 0.6, output, 0.4, 0, output)

        # Draw each line
        for i, line in enumerate(lines):
            y = margin + (i + 1) * line_height - 4
            cv2.putText(output, line, (margin, y), font, font_scale, color, thickness, cv2.LINE_AA)

        return output

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        tag_node_name = f"{node_id}:{self.node_tag}"
        tag_node_model_value_name = f"{tag_node_name}:ModelValue"
        tag_node_apikey_value_name = f"{tag_node_name}:ApiKeyValue"
        tag_node_prompt_value_name = f"{tag_node_name}:PromptValue"
        tag_node_delay_value_name = f"{tag_node_name}:DelayValue"
        tag_node_countdown_value_name = f"{tag_node_name}:CountdownValue"
        tag_node_status_value_name = f"{tag_node_name}:StatusValue"
        tag_node_output_image_value_name = f"{tag_node_name}:{self.TYPE_IMAGE}:OutputImageValue"
        tag_node_output_canvas_image_name = f"{tag_node_name}:CanvasImage"

        # Find connected JSON trigger and image sources
        connection_info_trigger = None
        connection_info_image = None

        for connection_info in connection_list:
            parts = connection_info[0].split(':')
            if len(parts) < 3:
                continue
            connection_type = parts[2]
            target = connection_info[1]

            if connection_type == self.TYPE_JSON and 'InputJson' in target:
                connection_info_trigger = connection_info[0]
            elif connection_type == self.TYPE_IMAGE and 'InputImage' in target:
                connection_info_image = connection_info[0]

        # Get trigger JSON
        trigger_json = {}
        if connection_info_trigger:
            src_key = ':'.join(connection_info_trigger.split(':')[:2])
            trigger_json = node_result_dict.get(src_key, {})

        # Get image frame
        frame = None
        if connection_info_image:
            src_key = ':'.join(connection_info_image.split(':')[:2])
            frame = node_image_dict.get(src_key, None)

        # Determine if action is triggered
        should_act = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_act = trigger_json['BOOL']
            else:
                for value in trigger_json.values():
                    if isinstance(value, bool) and value:
                        should_act = True
                        break

        # Get configuration values
        api_key = dpg_get_value(tag_node_apikey_value_name) or self.DEFAULT_API_KEY
        model = dpg_get_value(tag_node_model_value_name) or (self._available_models[0] if self._available_models else '')
        prompt = dpg_get_value(tag_node_prompt_value_name) or self.DEFAULT_PROMPT
        try:
            insensitivity_delay = float(dpg_get_value(tag_node_delay_value_name))
        except (ValueError, TypeError):
            insensitivity_delay = self.DEFAULT_INSENSITIVITY_DELAY

        current_time = time.time()

        # Poll the result queue from a previously launched process (non-blocking)
        if self._result_queue is not None:
            try:
                result = self._result_queue.get_nowait()
                self._result_queue.close()
                self._result_queue = None
                if 'error' in result:
                    dpg_set_value(tag_node_status_value_name, result['error'])
                else:
                    self._last_result_text = result['text']
                    output_frame = self._render_text_canvas()
                    self._pending_frame = output_frame
                    texture = self.convert_cv_to_dpg(output_frame, self.TEXT_CANVAS_W, self.TEXT_CANVAS_H)
                    try:
                        dpg_set_value(tag_node_output_image_value_name, texture)
                        # Canvas size is fixed – no dynamic resizing
                    except (SystemError, AttributeError):
                        pass
                    dpg_set_value(tag_node_status_value_name, 'Ready')
                self._is_requesting = False
            except queue.Empty:
                pass

        # Check if we're in insensitivity period
        if current_time < self._insensitivity_end_time:
            remaining = self._insensitivity_end_time - current_time
            dpg_set_value(tag_node_status_value_name, f'Next API call in {remaining:.1f}s')
            dpg_set_value(tag_node_countdown_value_name, f'⏳ {remaining:.1f}s')
            json_out = {"TEXT": self._last_result_text, "prompt": self._last_prompt} if self._last_result_text else None
            return {"image": self._pending_frame, "json": json_out, "audio": None}
        else:
            dpg_set_value(tag_node_countdown_value_name, '')

        # Launch request in a subprocess when action fires and not already busy
        if should_act and frame is not None and not self._is_requesting:
            if not api_key:
                dpg_set_value(tag_node_status_value_name, 'No API key set')
            elif not model:
                dpg_set_value(tag_node_status_value_name, 'No model selected')
            else:
                self._is_requesting = True
                self._last_prompt = prompt
                self._insensitivity_end_time = current_time + insensitivity_delay
                dpg_set_value(tag_node_status_value_name, 'Requesting...')
                self._result_queue = multiprocessing.Queue()
                self._request_process = multiprocessing.Process(
                    target=_vlm_request_worker,
                    args=(self._result_queue, api_key, model, prompt, frame.copy()),
                    daemon=True,
                )
                self._request_process.start()

        json_out = {"TEXT": self._last_result_text, "prompt": self._last_prompt} if self._last_result_text else None
        return {"image": self._pending_frame, "json": json_out, "audio": None}

    def close(self, node_id):
        """Clean up when node is closed."""
        self._is_requesting = False
        if self._request_process and self._request_process.is_alive():
            self._request_process.terminate()
            self._request_process.join(timeout=1.0)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_model_value_name = tag_node_name + ':ModelValue'
        tag_node_apikey_value_name = tag_node_name + ':ApiKeyValue'
        tag_node_prompt_value_name = tag_node_name + ':PromptValue'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_model_value_name] = dpg_get_value(tag_node_model_value_name)
        setting_dict[tag_node_apikey_value_name] = dpg_get_value(tag_node_apikey_value_name)
        setting_dict[tag_node_prompt_value_name] = dpg_get_value(tag_node_prompt_value_name)
        setting_dict[tag_node_delay_value_name] = float(dpg_get_value(tag_node_delay_value_name))
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_model_value_name = tag_node_name + ':ModelValue'
        tag_node_apikey_value_name = tag_node_name + ':ApiKeyValue'
        tag_node_prompt_value_name = tag_node_name + ':PromptValue'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        default_model = self._available_models[0] if self._available_models else ''
        dpg_set_value(tag_node_model_value_name,
                      setting_dict.get(tag_node_model_value_name, default_model))
        dpg_set_value(tag_node_apikey_value_name,
                      setting_dict.get(tag_node_apikey_value_name, self.DEFAULT_API_KEY))
        dpg_set_value(tag_node_prompt_value_name,
                      setting_dict.get(tag_node_prompt_value_name, self.DEFAULT_PROMPT))
        dpg_set_value(tag_node_delay_value_name,
                      float(setting_dict.get(tag_node_delay_value_name, self.DEFAULT_INSENSITIVITY_DELAY)))


# Test code to verify that the node displays correctly
if __name__ == "__main__":
    dpg.create_context()

    opencv_setting_dict = {
        'process_width': 240,
        'process_height': 135,
    }

    with dpg.window(label="Test VLM Node", width=900, height=700):
        with dpg.node_editor(label="Node Editor"):
            factory = FactoryNode()
            factory.add_node(
                parent=dpg.last_item(),
                node_id=1,
                pos=[100, 100],
                opencv_setting_dict=opencv_setting_dict,
            )

    dpg.create_viewport(title='Test VLM Node', width=1000, height=800)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
