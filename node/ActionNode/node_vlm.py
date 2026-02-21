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


def _vlm_request_worker(result_queue, server, model, caption, frame):
    """Run a VLM HTTP request in a subprocess.

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
        payload = {'model': model, 'caption': caption, 'image': img_b64}
        response = requests.post(
            server.rstrip('/') + '/vlm',
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        result_text = data.get('result', data.get('text', str(data)))
        result_queue.put({'text': result_text})
    except requests.exceptions.ConnectionError:
        result_queue.put({'error': 'Connection error'})
    except requests.exceptions.Timeout:
        result_queue.put({'error': 'Timeout'})
    except requests.exceptions.HTTPError as e:
        result_queue.put({'error': f'HTTP {e.response.status_code}'})
    except Exception as e:
        result_queue.put({'error': f'Error: {str(e)[:40]}'})


class FactoryNode:
    node_label = 'VLM'
    node_tag = 'VLM'

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Adds a VLM (Vision Language Model) node to the processing graph."""

        node = VLMNode()
        node.tag_node_name = f"{node_id}:{node.node_tag}"

        tag_node_name = node.tag_node_name

        # JSON Input (boolean trigger)
        node.tag_node_input_json_name = tag_node_name + ':' + node.TYPE_JSON + ':InputJson'
        node.tag_node_input_json_value_name = tag_node_name + ':' + node.TYPE_JSON + ':InputJsonValue'

        # Image Input
        node.tag_node_input_image_name = tag_node_name + ':' + node.TYPE_IMAGE + ':InputImage'
        node.tag_node_input_image_value_name = tag_node_name + ':' + node.TYPE_IMAGE + ':InputImageValue'

        # Image Output
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

        tag_node_caption_name = tag_node_name + ':Caption'
        tag_node_caption_value_name = tag_node_name + ':CaptionValue'

        tag_node_server_name = tag_node_name + ':Server'
        tag_node_server_value_name = tag_node_name + ':ServerValue'

        tag_node_delay_name = tag_node_name + ':Delay'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        tag_node_status_name = tag_node_name + ':Status'
        tag_node_status_value_name = tag_node_name + ':StatusValue'

        # Set opencv settings
        node._opencv_setting_dict = opencv_setting_dict or {}
        small_window_w = node._opencv_setting_dict.get('process_width', 240)
        small_window_h = node._opencv_setting_dict.get('process_height', 135)

        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(black_image, small_window_w, small_window_h)

        # Text canvas for the output: same width as the input image (bounding box)
        canvas_w = small_window_w
        node.TEXT_CANVAS_W = small_window_w
        # Ensure the minimum display height is at least as large as the canvas width
        # so the text area is never wider than tall (portrait orientation).
        canvas_min_h = canvas_w
        node.TEXT_CANVAS_MIN_H = canvas_min_h
        canvas_h = VLMNode.TEXT_CANVAS_H
        black_canvas = np.zeros((canvas_h, canvas_w, 3))
        canvas_texture = node.convert_cv_to_dpg(black_canvas, canvas_w, canvas_h)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
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

            # Image input
            with dpg.node_attribute(
                tag=node.tag_node_input_image_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_image(node.tag_node_input_image_value_name)

            # Model combobox
            with dpg.node_attribute(
                tag=tag_node_model_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=tag_node_model_value_name,
                    label="Model",
                    items=VLMNode.MODELS,
                    default_value=VLMNode.MODELS[0],
                    width=240,
                )

            # Caption text field
            with dpg.node_attribute(
                tag=tag_node_caption_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_node_caption_value_name,
                    label="Caption",
                    default_value=VLMNode.DEFAULT_CAPTION,
                    width=240,
                )

            # Server address field
            with dpg.node_attribute(
                tag=tag_node_server_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_node_server_value_name,
                    label="Server",
                    default_value=VLMNode.DEFAULT_SERVER,
                    width=240,
                )

            # Insensitivity delay slider
            with dpg.node_attribute(
                tag=tag_node_delay_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=tag_node_delay_value_name,
                    label="Insensitivity Delay (s)",
                    default_value=VLMNode.DEFAULT_INSENSITIVITY_DELAY,
                    min_value=0.0,
                    max_value=60.0,
                    width=240,
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

            # Image output
            with dpg.node_attribute(
                tag=node.tag_node_output_image_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(
                    node.tag_node_output_image_value_name,
                    tag=node.tag_node_output_canvas_image_name,
                    height=canvas_min_h,
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
    _ver = '0.0.1'

    MODELS = ['florence-base', 'moondream']
    DEFAULT_CAPTION = 'Describe the image'
    DEFAULT_SERVER = 'http://localhost:5000'
    DEFAULT_INSENSITIVITY_DELAY = 0.0

    MAX_LINES = 20
    TEXT_CANVAS_W = 320       # reduced by ~1/3 (was 480)
    TEXT_CANVAS_H = 680       # max texture height; 20 lines * 32px + 40px margin
    TEXT_CANVAS_MIN_H = 227   # ~1/3 of TEXT_CANVAS_H, minimum display height
    TEXT_LINE_HEIGHT = 32
    TEXT_FONT_SCALE = 0.9
    TEXT_THICKNESS = 2
    TEXT_MARGIN = 10

    def __init__(self):
        super().__init__()
        self.node_label = 'VLM'
        self.node_tag = 'VLM'
        self._last_result_text = ''
        self._text_lines = deque(maxlen=self.MAX_LINES)  # rolling 20-line buffer
        self._new_lines_count = 0  # number of lines from the latest API response
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

    def _wrap_text_to_lines(self, text, max_width):
        """Wrap text into lines that fit within max_width pixels at the canvas font size."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        words = text.split()
        lines = []
        current_line = ''
        for word in words:
            test_line = (current_line + ' ' + word).strip()
            (tw, _), _ = cv2.getTextSize(
                test_line, font, self.TEXT_FONT_SCALE, self.TEXT_THICKNESS
            )
            if tw <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def _render_text_canvas(self):
        """Render the rolling 20-line text buffer onto a black canvas with large clear text.

        The most recently arrived lines are rendered in red; all older lines are white.
        Empty spacer lines (inserted between responses) advance the vertical position
        without drawing text, creating visual separation between responses.
        """
        canvas = np.zeros((self.TEXT_CANVAS_H, self.TEXT_CANVAS_W, 3), dtype=np.uint8)
        font = cv2.FONT_HERSHEY_SIMPLEX
        lines = list(self._text_lines)
        # When _new_lines_count is 0 (no response yet), treat all lines as new (red).
        new_start = len(lines) - self._new_lines_count if self._new_lines_count > 0 else 0
        for i, line in enumerate(lines):
            y = self.TEXT_MARGIN + (i + 1) * self.TEXT_LINE_HEIGHT
            # Defensive guard: the deque is bounded to MAX_LINES so this should never trigger
            if y > self.TEXT_CANVAS_H - self.TEXT_MARGIN:
                break
            if not line:  # spacer line: advance position without drawing
                continue
            color = (0, 0, 255) if i >= new_start else (255, 255, 255)  # red=new, white=old (BGR)
            cv2.putText(
                canvas, line,
                (self.TEXT_MARGIN, y),
                font, self.TEXT_FONT_SCALE, color,
                self.TEXT_THICKNESS, cv2.LINE_AA,
            )
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
        tag_node_caption_value_name = f"{tag_node_name}:CaptionValue"
        tag_node_server_value_name = f"{tag_node_name}:ServerValue"
        tag_node_delay_value_name = f"{tag_node_name}:DelayValue"
        tag_node_status_value_name = f"{tag_node_name}:StatusValue"
        tag_node_input_image_value_name = f"{tag_node_name}:{self.TYPE_IMAGE}:InputImageValue"
        tag_node_output_image_value_name = f"{tag_node_name}:{self.TYPE_IMAGE}:OutputImageValue"
        tag_node_output_canvas_image_name = f"{tag_node_name}:CanvasImage"

        small_window_w = self._opencv_setting_dict.get('process_width', 240) if self._opencv_setting_dict else 240
        small_window_h = self._opencv_setting_dict.get('process_height', 135) if self._opencv_setting_dict else 135

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

        # Update input image preview
        if frame is not None:
            texture = self.convert_cv_to_dpg(frame, small_window_w, small_window_h)
            try:
                dpg_set_value(tag_node_input_image_value_name, texture)
            except (SystemError, AttributeError):
                pass

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
        model = dpg_get_value(tag_node_model_value_name) or self.MODELS[0]
        caption = dpg_get_value(tag_node_caption_value_name) or self.DEFAULT_CAPTION
        server = dpg_get_value(tag_node_server_value_name) or self.DEFAULT_SERVER
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
                    result_text = result['text']
                    self._last_result_text = result_text
                    max_text_w = self.TEXT_CANVAS_W - 2 * self.TEXT_MARGIN
                    new_lines = self._wrap_text_to_lines(result_text, max_text_w)
                    # Only display the latest response – clear previous text
                    self._text_lines.clear()
                    for line in new_lines:
                        self._text_lines.append(line)
                    self._new_lines_count = len(new_lines)
                    output_frame = self._render_text_canvas()
                    self._pending_frame = output_frame
                    texture = self.convert_cv_to_dpg(output_frame, self.TEXT_CANVAS_W, self.TEXT_CANVAS_H)
                    try:
                        dpg_set_value(tag_node_output_image_value_name, texture)
                        # Dynamically resize: small for short text, grows for long text
                        n_lines = len(self._text_lines)
                        needed_h = 2 * self.TEXT_MARGIN + n_lines * self.TEXT_LINE_HEIGHT
                        display_h = max(self.TEXT_CANVAS_MIN_H, min(needed_h, self.TEXT_CANVAS_H))
                        dpg.configure_item(tag_node_output_canvas_image_name, height=display_h)
                    except (SystemError, AttributeError):
                        pass
                    short_status = result_text[:40] + ('...' if len(result_text) > 40 else '')
                    dpg_set_value(tag_node_status_value_name, short_status)
                self._is_requesting = False
            except queue.Empty:
                pass

        # Check if we're in insensitivity period
        if current_time < self._insensitivity_end_time:
            remaining = self._insensitivity_end_time - current_time
            dpg_set_value(tag_node_status_value_name, f'Next API call in {remaining:.1f}s')
            json_out = {"TEXT": self._last_result_text} if self._last_result_text else None
            return {"image": self._pending_frame, "json": json_out, "audio": None}

        # Launch request in a subprocess when action fires and not already busy
        if should_act and frame is not None and not self._is_requesting:
            self._is_requesting = True
            self._insensitivity_end_time = current_time + insensitivity_delay
            dpg_set_value(tag_node_status_value_name, 'Requesting...')
            self._result_queue = multiprocessing.Queue()
            self._request_process = multiprocessing.Process(
                target=_vlm_request_worker,
                args=(self._result_queue, server, model, caption, frame.copy()),
                daemon=True,
            )
            self._request_process.start()

        json_out = {"TEXT": self._last_result_text} if self._last_result_text else None
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
        tag_node_caption_value_name = tag_node_name + ':CaptionValue'
        tag_node_server_value_name = tag_node_name + ':ServerValue'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_model_value_name] = dpg_get_value(tag_node_model_value_name)
        setting_dict[tag_node_caption_value_name] = dpg_get_value(tag_node_caption_value_name)
        setting_dict[tag_node_server_value_name] = dpg_get_value(tag_node_server_value_name)
        setting_dict[tag_node_delay_value_name] = float(dpg_get_value(tag_node_delay_value_name))
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_model_value_name = tag_node_name + ':ModelValue'
        tag_node_caption_value_name = tag_node_name + ':CaptionValue'
        tag_node_server_value_name = tag_node_name + ':ServerValue'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        dpg_set_value(tag_node_model_value_name,
                      setting_dict.get(tag_node_model_value_name, self.MODELS[0]))
        dpg_set_value(tag_node_caption_value_name,
                      setting_dict.get(tag_node_caption_value_name, self.DEFAULT_CAPTION))
        dpg_set_value(tag_node_server_value_name,
                      setting_dict.get(tag_node_server_value_name, self.DEFAULT_SERVER))
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
