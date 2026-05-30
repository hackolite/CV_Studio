#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Normalize node – normalizes audio amplitude to a target peak or RMS level.

Essential pre-processing for AI audio classification to ensure consistent
input levels regardless of microphone gain or distance.

Audio in → Audio out (compatible with AudioClassifier, ImageConcat, Decibel).
"""
import time
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode
from src.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_TARGET_DB = -3.0


def normalize_peak(audio_data, target_db=-3.0):
    """Normalize audio so peak amplitude matches target_db.

    Args:
        audio_data: float32 audio samples.
        target_db: Target peak level in dBFS.

    Returns:
        np.ndarray: Normalized audio (float32).
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    audio = audio_data.astype(np.float32)
    peak = np.max(np.abs(audio))
    if peak < 1e-10:
        return audio

    target_linear = 10 ** (target_db / 20.0)
    gain = target_linear / peak
    return (audio * gain).astype(np.float32)


def normalize_rms(audio_data, target_db=-20.0):
    """Normalize audio so RMS level matches target_db.

    Args:
        audio_data: float32 audio samples.
        target_db: Target RMS level in dBFS.

    Returns:
        np.ndarray: Normalized audio (float32), clipped to [-1, 1].
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    audio = audio_data.astype(np.float32)
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 1e-10:
        return audio

    target_linear = 10 ** (target_db / 20.0)
    gain = target_linear / rms
    result = audio * gain
    return np.clip(result, -1.0, 1.0).astype(np.float32)


class FactoryNode:
    node_label = 'Normalize'
    node_tag = 'Normalize'

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=[0, 0],
        opencv_setting_dict=None,
        callback=None,
    ):
        node = Node()
        node.tag_node_name = str(node_id) + ':' + self.node_tag

        # Audio input
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01Value'

        # Mode selector (peak / rms)
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'

        # Target level (dB)
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'

        # Audio output
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Output01Value'

        # Performance counter
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = opencv_setting_dict.get('process_width', 240) if opencv_setting_dict else 240
        use_pref_counter = opencv_setting_dict.get('use_pref_counter', False) if opencv_setting_dict else False

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input Audio',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=['peak', 'rms'],
                    default_value='peak',
                    width=small_window_w,
                    label='Mode',
                    tag=node.tag_node_input02_value_name,
                    callback=callback,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label='Target (dB)',
                    default_value=DEFAULT_TARGET_DB,
                    min_value=-40.0,
                    max_value=0.0,
                    width=small_window_w,
                    callback=callback,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output01_value_name,
                    default_value='Output Audio',
                )

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

        return node


class Node(BaseNode):
    _ver = '0.0.1'

    node_label = 'Normalize'
    node_tag = 'Normalize'

    def __init__(self):
        self._opencv_setting_dict = None

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        use_pref_counter = False
        if self._opencv_setting_dict:
            use_pref_counter = self._opencv_setting_dict.get('use_pref_counter', False)

        try:
            mode = dpg_get_value(input_value02_tag)
            target_db = dpg_get_value(input_value03_tag)
        except Exception:
            mode = 'peak'
            target_db = DEFAULT_TARGET_DB

        # Get audio input
        audio_data = None
        sample_rate = DEFAULT_SAMPLE_RATE
        input_audio_entry = None

        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_AUDIO:
                src_key = ':'.join(connection_info[0].split(':')[:2])
                audio_dict_entry = node_audio_dict.get(src_key, None)
                if audio_dict_entry is not None:
                    input_audio_entry = audio_dict_entry
                    if isinstance(audio_dict_entry, dict):
                        audio_data = audio_dict_entry.get('data', None)
                        sample_rate = audio_dict_entry.get('sample_rate', DEFAULT_SAMPLE_RATE)
                    elif isinstance(audio_dict_entry, (list, tuple)) and len(audio_dict_entry) == 2:
                        audio_data, sample_rate = audio_dict_entry
                break

        if use_pref_counter:
            start_time = time.monotonic()

        processed_audio = None
        if audio_data is not None:
            try:
                if mode == 'rms':
                    processed_audio = normalize_rms(audio_data, target_db)
                else:
                    processed_audio = normalize_peak(audio_data, target_db)
            except Exception as e:
                logger.error(f"Error in normalize: {e}", exc_info=True)
                processed_audio = audio_data

        if use_pref_counter:
            elapsed_time = int((time.monotonic() - start_time) * 1000)
            try:
                dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception:
                pass

        audio_output = None
        if processed_audio is not None:
            audio_output = {'data': processed_audio, 'sample_rate': sample_rate}
            if isinstance(input_audio_entry, dict):
                for k in ('chunk_index', 'step_duration', 'pts_ms'):
                    if k in input_audio_entry:
                        audio_output[k] = input_audio_entry[k]

        return {"image": None, "json": None, "audio": audio_output}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'

        return {
            'ver': self._ver,
            'pos': pos,
            'mode': dpg_get_value(input_value02_tag),
            'target_db': dpg_get_value(input_value03_tag),
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'

        dpg_set_value(input_value02_tag, setting_dict.get('mode', 'peak'))
        dpg_set_value(input_value03_tag, setting_dict.get('target_db', DEFAULT_TARGET_DB))
