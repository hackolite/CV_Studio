#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BandPass Filter node – high-pass, low-pass, or band-pass filtering.

Useful to isolate frequency ranges relevant for AI detection
(e.g., remove low-frequency rumble or high-frequency hiss before classification).

Audio in → Audio out (compatible with AudioClassifier, ImageConcat, Decibel).
"""
import time
import numpy as np
import dearpygui.dearpygui as dpg
from scipy import signal

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode
from src.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_LOW_CUT = 300.0
DEFAULT_HIGH_CUT = 8000.0
FILTER_ORDER = 4
NYQUIST_MARGIN = 50  # Hz margin from Nyquist


def apply_bandpass(audio_data, sample_rate, mode, low_cut, high_cut):
    """Apply frequency filter to audio.

    Args:
        audio_data: float32 samples.
        sample_rate: Hz.
        mode: 'highpass', 'lowpass', or 'bandpass'.
        low_cut: Low frequency cutoff (Hz).
        high_cut: High frequency cutoff (Hz).

    Returns:
        np.ndarray: Filtered audio (float32).
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    nyquist = sample_rate / 2.0
    audio = audio_data.astype(np.float64)

    try:
        if mode == 'highpass':
            freq = max(20.0, min(low_cut, nyquist - NYQUIST_MARGIN))
            sos = signal.butter(FILTER_ORDER, freq, btype='high', fs=sample_rate, output='sos')
        elif mode == 'lowpass':
            freq = max(20.0, min(high_cut, nyquist - NYQUIST_MARGIN))
            sos = signal.butter(FILTER_ORDER, freq, btype='low', fs=sample_rate, output='sos')
        else:  # bandpass
            lo = max(20.0, min(low_cut, nyquist - NYQUIST_MARGIN - 1))
            hi = max(lo + 1, min(high_cut, nyquist - NYQUIST_MARGIN))
            sos = signal.butter(FILTER_ORDER, [lo, hi], btype='band', fs=sample_rate, output='sos')

        filtered = signal.sosfilt(sos, audio)
        return filtered.astype(np.float32)
    except Exception as e:
        logger.error(f"Filter error: {e}")
        return audio_data


class FactoryNode:
    node_label = 'BandPassFilter'
    node_tag = 'BandPassFilter'

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

        # Mode selector
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'

        # Low cutoff
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'

        # High cutoff
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04Value'

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
                    items=['bandpass', 'highpass', 'lowpass'],
                    default_value='bandpass',
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
                    label='Low Cut (Hz)',
                    default_value=DEFAULT_LOW_CUT,
                    min_value=20.0,
                    max_value=8000.0,
                    width=small_window_w,
                    callback=callback,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input04_value_name,
                    label='High Cut (Hz)',
                    default_value=DEFAULT_HIGH_CUT,
                    min_value=100.0,
                    max_value=20000.0,
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

    node_label = 'BandPassFilter'
    node_tag = 'BandPassFilter'

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
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        use_pref_counter = False
        if self._opencv_setting_dict:
            use_pref_counter = self._opencv_setting_dict.get('use_pref_counter', False)

        try:
            mode = dpg_get_value(input_value02_tag)
            low_cut = dpg_get_value(input_value03_tag)
            high_cut = dpg_get_value(input_value04_tag)
        except Exception:
            mode = 'bandpass'
            low_cut = DEFAULT_LOW_CUT
            high_cut = DEFAULT_HIGH_CUT

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
                processed_audio = apply_bandpass(audio_data, sample_rate, mode, low_cut, high_cut)
            except Exception as e:
                logger.error(f"Error in bandpass filter: {e}", exc_info=True)
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
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'

        return {
            'ver': self._ver,
            'pos': pos,
            'mode': dpg_get_value(input_value02_tag),
            'low_cut': dpg_get_value(input_value03_tag),
            'high_cut': dpg_get_value(input_value04_tag),
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'

        dpg_set_value(input_value02_tag, setting_dict.get('mode', 'bandpass'))
        dpg_set_value(input_value03_tag, setting_dict.get('low_cut', DEFAULT_LOW_CUT))
        dpg_set_value(input_value04_tag, setting_dict.get('high_cut', DEFAULT_HIGH_CUT))
