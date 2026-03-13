#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Word Cloud – visual node that renders a word cloud from VLM text output.

Takes the JSON output of the VLM node (``{"TEXT": "...", "type": "..."}``) and
produces a beautiful word-cloud image.  The image is also forwarded as a JSON
output so it can be wired into a Concat node.

Colourmap options:
    viridis, plasma, inferno, magma, cool, hot, rainbow, ocean

The node also exposes a ``max_words`` slider (10 – 200) to control density.
"""
import re
import io
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg
from PIL import Image
from wordcloud import WordCloud, STOPWORDS

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode

# ── Canvas dimensions ─────────────────────────────────────────────────────
CANVAS_W = 480
CANVAS_H = 320

# ── Colourmaps available ──────────────────────────────────────────────────
COLOURMAPS = [
    'viridis', 'plasma', 'inferno', 'magma',
    'cool', 'hot', 'rainbow', 'ocean',
]

DEFAULT_COLOURMAP = 'plasma'
DEFAULT_MAX_WORDS = 80
DEFAULT_DELTA_T = 30  # seconds – rolling time window for word accumulation

# ── Colour pairs (background, fallback text) per colourmap ───────────────
_BG_COLOUR = {
    'viridis': (15, 15, 30),
    'plasma':  (10, 5, 25),
    'inferno': (10, 5, 10),
    'magma':   (10, 8, 12),
    'cool':    (5, 20, 30),
    'hot':     (20, 5, 5),
    'rainbow': (10, 10, 10),
    'ocean':   (5, 15, 25),
}


# ── Helper functions ──────────────────────────────────────────────────────

def _clean_text(text):
    """Remove Florence2 task tokens and normalise the text."""
    # Remove <TOKEN> style markers
    text = re.sub(r'<[A-Z_]+>', ' ', text)
    # Remove stray punctuation runs, keep alphanumeric + apostrophe + hyphen
    text = re.sub(r"[^a-zA-ZÀ-ÿ0-9' \-]", ' ', text)
    return text.strip()


def _render_word_cloud(text, colourmap=DEFAULT_COLOURMAP, max_words=DEFAULT_MAX_WORDS,
                       width=CANVAS_W, height=CANVAS_H):
    """Render a word cloud from *text* and return a BGR uint8 numpy array.

    Parameters
    ----------
    text : str
        Raw text (e.g. from VLM JSON "TEXT" field).
    colourmap : str
        Matplotlib colourmap name used to colour words.
    max_words : int
        Maximum number of words rendered.
    width, height : int
        Output image dimensions.

    Returns
    -------
    numpy.ndarray
        BGR uint8 image.
    """
    bg_rgb = _BG_COLOUR.get(colourmap, (10, 10, 10))
    bg_hex = '#{:02x}{:02x}{:02x}'.format(*bg_rgb)

    cleaned = _clean_text(text)
    if not cleaned:
        # Nothing to display – return a dark placeholder.
        # bg_rgb is stored as (R, G, B); np.full needs BGR order for OpenCV.
        canvas = np.full((height, width, 3), bg_rgb[::-1], dtype=np.uint8)
        font = cv2.FONT_HERSHEY_SIMPLEX
        msg = 'Waiting for text...'
        (tw, th), _ = cv2.getTextSize(msg, font, 0.7, 1)
        cv2.putText(
            canvas, msg,
            ((width - tw) // 2, (height + th) // 2),
            font, 0.7, (180, 180, 180), 1, cv2.LINE_AA,
        )
        return canvas

    wc = WordCloud(
        width=width,
        height=height,
        background_color=bg_hex,
        colormap=colourmap,
        max_words=max_words,
        stopwords=STOPWORDS,
        prefer_horizontal=0.85,
        min_font_size=10,
        max_font_size=None,
        relative_scaling=0.5,
        collocations=False,
        margin=6,
    ).generate(cleaned)

    # Convert PIL Image (RGB) → numpy array → BGR
    pil_img = wc.to_image()
    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return bgr


def _render_blank(width=CANVAS_W, height=CANVAS_H):
    """Return a dark placeholder canvas."""
    return np.zeros((height, width, 3), dtype=np.uint8)


# ── DearPyGui Factory ─────────────────────────────────────────────────────

class FactoryNode:
    node_label = 'Word Cloud'
    node_tag = 'WordCloud'

    def __init__(self):
        pass

    def add_node(
        self, parent, node_id, pos=[0, 0],
        callback=None, opencv_setting_dict=None,
    ):
        node = WordCloudNode()
        node.tag_node_name = '{}:{}'.format(node_id, node.node_tag)
        tag_node_name = node.tag_node_name

        # ── Input – JSON from VLM ─────────────────────────────────────
        node.tag_node_input_json_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':InputJson'
        )
        node.tag_node_input_json_value_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':InputJsonValue'
        )

        # ── Outputs ───────────────────────────────────────────────────
        node.tag_node_output_image_name = (
            tag_node_name + ':' + node.TYPE_IMAGE + ':OutputImage'
        )
        node.tag_node_output_image_value_name = (
            tag_node_name + ':' + node.TYPE_IMAGE + ':OutputImageValue'
        )
        node.tag_node_output_json_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        )
        node.tag_node_output_json_value_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'
        )

        # ── Static widget tags ────────────────────────────────────────
        tag_colourmap_name = tag_node_name + ':Colourmap'
        tag_colourmap_value = tag_node_name + ':ColourmapValue'
        tag_max_words_name = tag_node_name + ':MaxWords'
        tag_max_words_value = tag_node_name + ':MaxWordsValue'
        tag_delta_t_name = tag_node_name + ':DeltaT'
        tag_delta_t_value = tag_node_name + ':DeltaTValue'

        node._opencv_setting_dict = opencv_setting_dict or {}

        # Initial blank texture
        blank = _render_blank(CANVAS_W, CANVAS_H)
        blank_tex = node.convert_cv_to_dpg(blank, CANVAS_W, CANVAS_H)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                CANVAS_W,
                CANVAS_H,
                blank_tex,
                tag=node.tag_node_output_image_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
            tag=tag_node_name, parent=parent,
            label=node.node_label, pos=pos,
        ):
            # ── JSON input ────────────────────────────────────────────
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='VLM JSON',
                )

            # ── Colourmap combo ───────────────────────────────────────
            with dpg.node_attribute(
                tag=tag_colourmap_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=tag_colourmap_value,
                    items=COLOURMAPS,
                    default_value=DEFAULT_COLOURMAP,
                    width=240,
                    label='Colourmap',
                )

            # ── Max words slider ──────────────────────────────────────
            with dpg.node_attribute(
                tag=tag_max_words_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=tag_max_words_value,
                    default_value=DEFAULT_MAX_WORDS,
                    min_value=10,
                    max_value=200,
                    width=240,
                    label='Max words',
                )

            # ── Delta T slider (rolling time window in seconds) ───────
            with dpg.node_attribute(
                tag=tag_delta_t_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=tag_delta_t_value,
                    default_value=DEFAULT_DELTA_T,
                    min_value=5,
                    max_value=300,
                    width=240,
                    label='ΔT (s)',
                )

            # ── Image output ──────────────────────────────────────────
            with dpg.node_attribute(
                tag=node.tag_node_output_image_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output_image_value_name)

            # ── JSON output (text for Concat) ─────────────────────────
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_button(
                    tag=node.tag_node_output_json_value_name,
                    label='Text →',
                    width=240,
                    enabled=False,
                )

        return node


# ── Node logic ─────────────────────────────────────────────────────────────

class WordCloudNode(BaseNode):
    _ver = '0.0.1'

    def __init__(self):
        super().__init__()
        self.node_label = 'Word Cloud'
        self.node_tag = 'WordCloud'
        self._last_frame = None
        self._last_colourmap = DEFAULT_COLOURMAP
        self._last_max_words = DEFAULT_MAX_WORDS
        self._last_delta_t = DEFAULT_DELTA_T
        # Rolling buffer: list of (timestamp, text) pairs
        self._text_buffer = []
        # Track last text appended to buffer to avoid duplicate entries
        self._last_appended_text = ''
        # Combined text used for the last render (to detect changes)
        self._last_combined_text = ''

    def update(
        self, node_id, connection_list, node_image_dict,
        node_result_dict, node_audio_dict,
    ):
        tag_node_name = '{}:{}'.format(node_id, self.node_tag)
        output_tex_tag = '{}:{}:OutputImageValue'.format(
            tag_node_name, self.TYPE_IMAGE,
        )
        tag_colourmap_value = tag_node_name + ':ColourmapValue'
        tag_max_words_value = tag_node_name + ':MaxWordsValue'

        # ── Retrieve connected JSON ───────────────────────────────────
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

        # ── Extract text from JSON ────────────────────────────────────
        text = ''
        if isinstance(input_json, dict):
            text = str(input_json.get('TEXT', ''))
        elif isinstance(input_json, str):
            text = input_json

        # ── Read UI settings ──────────────────────────────────────────
        colourmap = dpg_get_value(tag_colourmap_value) or DEFAULT_COLOURMAP
        try:
            max_words = int(dpg_get_value(tag_max_words_value))
        except (ValueError, TypeError):
            max_words = DEFAULT_MAX_WORDS
        tag_delta_t_value = tag_node_name + ':DeltaTValue'
        try:
            delta_t = int(dpg_get_value(tag_delta_t_value))
            if delta_t < 1:
                delta_t = DEFAULT_DELTA_T
        except (ValueError, TypeError):
            delta_t = DEFAULT_DELTA_T

        # ── Update rolling text buffer ────────────────────────────────
        now = time.time()
        # Append text to buffer when it changes (new observation)
        if text and text != self._last_appended_text:
            self._text_buffer.append((now, text))
            self._last_appended_text = text
        # Prune entries older than delta_t
        cutoff = now - delta_t
        self._text_buffer = [
            (ts, txt) for ts, txt in self._text_buffer if ts >= cutoff
        ]
        # Build combined text from the rolling window
        combined = ' '.join(txt for _, txt in self._text_buffer)

        # ── Regenerate only when something changed ────────────────────
        changed = (
            combined != self._last_combined_text
            or colourmap != self._last_colourmap
            or max_words != self._last_max_words
            or delta_t != self._last_delta_t
        )

        if changed or self._last_frame is None:
            self._last_combined_text = combined
            self._last_colourmap = colourmap
            self._last_max_words = max_words
            self._last_delta_t = delta_t
            self._last_frame = _render_word_cloud(combined, colourmap, max_words)

        frame = self._last_frame

        # ── Update texture ────────────────────────────────────────────
        texture = self.convert_cv_to_dpg(frame, CANVAS_W, CANVAS_H)
        try:
            dpg_set_value(output_tex_tag, texture)
        except (SystemError, AttributeError):
            pass

        # ── Build JSON output (for Concat / downstream nodes) ─────────
        # Always return a dict so downstream nodes can rely on a consistent
        # API contract regardless of whether text is available.
        json_out = {'TEXT': combined}

        return {'image': frame, 'json': json_out, 'audio': None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = '{}:{}'.format(node_id, self.node_tag)
        pos = dpg.get_item_pos(tag_node_name)
        tag_colourmap_value = tag_node_name + ':ColourmapValue'
        tag_max_words_value = tag_node_name + ':MaxWordsValue'
        tag_delta_t_value = tag_node_name + ':DeltaTValue'
        return {
            'ver': self._ver,
            'pos': pos,
            tag_colourmap_value: dpg_get_value(tag_colourmap_value),
            tag_max_words_value: dpg_get_value(tag_max_words_value),
            tag_delta_t_value: dpg_get_value(tag_delta_t_value),
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = '{}:{}'.format(node_id, self.node_tag)
        tag_colourmap_value = tag_node_name + ':ColourmapValue'
        tag_max_words_value = tag_node_name + ':MaxWordsValue'
        tag_delta_t_value = tag_node_name + ':DeltaTValue'
        if tag_colourmap_value in setting_dict:
            dpg_set_value(tag_colourmap_value, setting_dict[tag_colourmap_value])
        if tag_max_words_value in setting_dict:
            dpg_set_value(tag_max_words_value, int(setting_dict[tag_max_words_value]))
        if tag_delta_t_value in setting_dict:
            dpg_set_value(tag_delta_t_value, int(setting_dict[tag_delta_t_value]))
