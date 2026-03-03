#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Vigilance Gauge – visual node that displays the vigilance level from TinyBERT.

Takes the JSON output of the TinyBert Vigilance node (``{"vigilance": 1..5}``)
and renders a colour-coded gauge image (white text on black background) with
the level name and score.

Levels:
    1 → LOW       (green)
    2 → GUARDED   (yellow)
    3 → MEDIUM    (orange)
    4 → HIGH      (red)
    5 → CRITICAL  (purple)

When the upstream NLP model is still processing (no valid JSON), the display
blinks to provide visual feedback.
"""
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

# ── Vigilance level definitions ────────────────────────────────────────────
VIGILANCE_LEVELS = {
    1: {'label': 'LOW',      'color_bgr': (0, 200, 0)},       # green
    2: {'label': 'GUARDED',  'color_bgr': (0, 255, 255)},     # yellow
    3: {'label': 'MEDIUM',   'color_bgr': (0, 165, 255)},     # orange
    4: {'label': 'HIGH',     'color_bgr': (0, 0, 255)},       # red
    5: {'label': 'CRITICAL', 'color_bgr': (255, 0, 255)},     # purple
}

DEFAULT_LEVEL = 1

# Blink period in seconds (full on/off cycle)
BLINK_PERIOD = 0.6

# Canvas dimensions (matching VLM style)
CANVAS_W = 240
CANVAS_H = 240


def render_gauge(level, canvas_w=CANVAS_W, canvas_h=CANVAS_H):
    """Render a vigilance gauge image (white text on black background).

    Parameters
    ----------
    level : int
        Vigilance level 1‑5.
    canvas_w, canvas_h : int
        Output image size.

    Returns
    -------
    numpy.ndarray
        BGR uint8 image.
    """
    level = max(1, min(5, int(level)))
    info = VIGILANCE_LEVELS[level]
    label = info['label']
    color = info['color_bgr']

    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

    # ── Score text (e.g. "3 / 5") ─────────────────────────────────────────
    score_text = '{} / 5'.format(level)
    font = cv2.FONT_HERSHEY_SIMPLEX
    score_scale = 1.8
    score_thick = 4
    (sw, sh), _ = cv2.getTextSize(score_text, font, score_scale, score_thick)
    sx = (canvas_w - sw) // 2
    sy = canvas_h // 2 - 10
    cv2.putText(canvas, score_text, (sx, sy), font, score_scale,
                (255, 255, 255), score_thick, cv2.LINE_AA)

    # ── Level label (e.g. "HIGH") ──────────────────────────────────────────
    label_scale = 1.2
    label_thick = 3
    (lw, lh), _ = cv2.getTextSize(label, font, label_scale, label_thick)
    lx = (canvas_w - lw) // 2
    ly = sy + sh + 30
    cv2.putText(canvas, label, (lx, ly), font, label_scale,
                color, label_thick, cv2.LINE_AA)

    # ── Colour bar at the bottom ───────────────────────────────────────────
    bar_h = 18
    cv2.rectangle(canvas, (0, canvas_h - bar_h), (canvas_w, canvas_h),
                  color, -1)

    return canvas


def render_blank(canvas_w=CANVAS_W, canvas_h=CANVAS_H):
    """Return a blank (black) canvas used during the *off* phase of blink."""
    return np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)


# ── DearPyGui Factory ─────────────────────────────────────────────────────

class FactoryNode:
    node_label = 'Vigilance Gauge'
    node_tag = 'VigilanceGauge'

    def __init__(self):
        pass

    def add_node(
        self, parent, node_id, pos=[0, 0],
        callback=None, opencv_setting_dict=None,
    ):
        node = VigilanceGaugeNode()
        node.tag_node_name = '{}:{}'.format(node_id, node.node_tag)
        tag_node_name = node.tag_node_name

        # JSON input (from TinyBert Vigilance)
        node.tag_node_input_json_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':InputJson'
        )
        node.tag_node_input_json_value_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':InputJsonValue'
        )

        # Image output
        node.tag_node_output_image_name = (
            tag_node_name + ':' + node.TYPE_IMAGE + ':OutputImage'
        )
        node.tag_node_output_image_value_name = (
            tag_node_name + ':' + node.TYPE_IMAGE + ':OutputImageValue'
        )

        node._opencv_setting_dict = opencv_setting_dict or {}

        canvas_w = CANVAS_W
        canvas_h = CANVAS_H

        black_image = np.zeros((canvas_h, canvas_w, 3))
        black_texture = node.convert_cv_to_dpg(black_image, canvas_w, canvas_h)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                canvas_w,
                canvas_h,
                black_texture,
                tag=node.tag_node_output_image_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
            tag=tag_node_name, parent=parent,
            label=node.node_label, pos=pos,
        ):
            # JSON input attribute
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Vigilance JSON',
                )

            # Image output attribute
            with dpg.node_attribute(
                tag=node.tag_node_output_image_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output_image_value_name)

        return node


# ── Node logic ─────────────────────────────────────────────────────────────

class VigilanceGaugeNode(BaseNode):
    _ver = '0.0.1'

    def __init__(self):
        super().__init__()
        self.node_label = 'Vigilance Gauge'
        self.node_tag = 'VigilanceGauge'
        self._last_level = None
        self._thinking = False
        self._last_frame = None

    def update(
        self, node_id, connection_list, node_image_dict,
        node_result_dict, node_audio_dict,
    ):
        tag_node_name = '{}:{}'.format(node_id, self.node_tag)
        output_tag = '{}:{}:OutputImageValue'.format(
            tag_node_name, self.TYPE_IMAGE,
        )

        # Find connected JSON input
        input_json = {}
        for connection_info in connection_list:
            parts = connection_info[0].split(':')
            if len(parts) < 3:
                continue
            connection_type = parts[2]
            target = connection_info[1]
            if connection_type == self.TYPE_JSON and 'InputJson' in target:
                src_key = ':'.join(parts[:2])
                input_json = node_result_dict.get(src_key, {})
                break

        # Determine vigilance level
        vigilance = None
        if isinstance(input_json, dict):
            vigilance = input_json.get('vigilance')

        if vigilance is not None and 1 <= int(vigilance) <= 5:
            self._thinking = False
            self._last_level = int(vigilance)
        else:
            # No valid vigilance → NLP model is thinking or not connected
            self._thinking = True

        # Render frame
        if self._thinking:
            # Blink: alternate between last gauge (or blank) and blank
            phase = time.time() % BLINK_PERIOD
            if phase < BLINK_PERIOD / 2:
                if self._last_level is not None:
                    frame = render_gauge(self._last_level)
                else:
                    frame = render_blank()
            else:
                frame = render_blank()
        else:
            frame = render_gauge(self._last_level or DEFAULT_LEVEL)

        self._last_frame = frame

        # Update texture
        texture = self.convert_cv_to_dpg(frame, CANVAS_W, CANVAS_H)
        try:
            dpg_set_value(output_tag, texture)
        except (SystemError, AttributeError):
            pass

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = '{}:{}'.format(node_id, self.node_tag)
        pos = dpg.get_item_pos(tag_node_name)
        return {'ver': self._ver, 'pos': pos}

    def set_setting_dict(self, node_id, setting_dict):
        pass
