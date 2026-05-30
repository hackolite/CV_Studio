#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Compressor node – dynamic range compression for audio.

Reduces the dynamic range so quiet sounds are boosted and loud sounds are
attenuated.  Particularly useful before AI classification to make detection
less sensitive to volume variations.

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
DEFAULT_THRESHOLD_DB = -20.0
DEFAULT_RATIO = 4.0
DEFAULT_ATTACK_MS = 10.0
DEFAULT_RELEASE_MS = 100.0
DEFAULT_MAKEUP_DB = 0.0


def apply_compressor(audio_data, sample_rate, threshold_db=-20.0, ratio=4.0,
                     attack_ms=10.0, release_ms=100.0, makeup_db=0.0):
    """Apply dynamic range compression.

    Args:
        audio_data: float32 audio samples.
        sample_rate: Hz.
        threshold_db: Level above which compression starts (dBFS).
        ratio: Compression ratio (e.g., 4:1 means 4 dB above threshold → 1 dB).
        attack_ms: Time to reach full compression.
        release_ms: Time to release compression.
        makeup_db: Post-compression gain.

    Returns:
        np.ndarray: Compressed audio (float32).
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    audio = audio_data.astype(np.float64)
    n = len(audio)

    # Convert parameters
    threshold_linear = 10 ** (threshold_db / 20.0)
    attack_coeff = 1.0 - np.exp(-1.0 / max(1, int(sample_rate * attack_ms / 1000.0)))
    release_coeff = 1.0 - np.exp(-1.0 / max(1, int(sample_rate * release_ms / 1000.0)))
    makeup_linear = 10 ** (makeup_db / 20.0)

    # Envelope follower + gain computation
    envelope = 0.0
    output = np.zeros(n, dtype=np.float64)

    for i in range(n):
        abs_sample = abs(audio[i])

        # Smooth envelope
        if abs_sample > envelope:
            envelope += attack_coeff * (abs_sample - envelope)
        else:
            envelope += release_coeff * (abs_sample - envelope)

        # Compute gain reduction
        if envelope > threshold_linear:
            # Amount over threshold in dB
            over_db = 20.0 * np.log10(max(envelope, 1e-10) / threshold_linear)
            # Compressed amount
            compressed_db = over_db / ratio
            # Gain reduction in dB
            gain_reduction_db = over_db - compressed_db
            gain = 10 ** (-gain_reduction_db / 20.0)
        else:
            gain = 1.0

        output[i] = audio[i] * gain * makeup_linear

    # Clip to prevent overflow
    output = np.clip(output, -1.0, 1.0)
    return output.astype(np.float32)


class FactoryNode:
    node_label = 'Compressor'
    node_tag = 'Compressor'

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

        # Threshold
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02Value'

        # Ratio
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'

        # Attack
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04Value'

        # Release
        node.tag_node_input05_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input05'
        node.tag_node_input05_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input05Value'

        # Makeup gain
        node.tag_node_input06_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input06'
        node.tag_node_input06_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input06Value'

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
                dpg.add_slider_float(
                    tag=node.tag_node_input02_value_name,
                    label='Threshold (dB)',
                    default_value=DEFAULT_THRESHOLD_DB,
                    min_value=-60.0,
                    max_value=0.0,
                    width=small_window_w,
                    callback=callback,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label='Ratio',
                    default_value=DEFAULT_RATIO,
                    min_value=1.0,
                    max_value=20.0,
                    width=small_window_w,
                    callback=callback,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input04_value_name,
                    label='Attack (ms)',
                    default_value=DEFAULT_ATTACK_MS,
                    min_value=0.1,
                    max_value=200.0,
                    width=small_window_w,
                    callback=callback,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input05_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input05_value_name,
                    label='Release (ms)',
                    default_value=DEFAULT_RELEASE_MS,
                    min_value=1.0,
                    max_value=1000.0,
                    width=small_window_w,
                    callback=callback,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input06_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input06_value_name,
                    label='Makeup (dB)',
                    default_value=DEFAULT_MAKEUP_DB,
                    min_value=0.0,
                    max_value=30.0,
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

    node_label = 'Compressor'
    node_tag = 'Compressor'

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
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'
        input_value06_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input06Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        use_pref_counter = False
        if self._opencv_setting_dict:
            use_pref_counter = self._opencv_setting_dict.get('use_pref_counter', False)

        try:
            threshold_db = dpg_get_value(input_value02_tag)
            ratio = dpg_get_value(input_value03_tag)
            attack_ms = dpg_get_value(input_value04_tag)
            release_ms = dpg_get_value(input_value05_tag)
            makeup_db = dpg_get_value(input_value06_tag)
        except Exception:
            threshold_db = DEFAULT_THRESHOLD_DB
            ratio = DEFAULT_RATIO
            attack_ms = DEFAULT_ATTACK_MS
            release_ms = DEFAULT_RELEASE_MS
            makeup_db = DEFAULT_MAKEUP_DB

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
                processed_audio = apply_compressor(
                    audio_data, sample_rate, threshold_db, ratio,
                    attack_ms, release_ms, makeup_db
                )
            except Exception as e:
                logger.error(f"Error in compressor: {e}", exc_info=True)
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
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'
        input_value06_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input06Value'

        return {
            'ver': self._ver,
            'pos': pos,
            'threshold_db': dpg_get_value(input_value02_tag),
            'ratio': dpg_get_value(input_value03_tag),
            'attack_ms': dpg_get_value(input_value04_tag),
            'release_ms': dpg_get_value(input_value05_tag),
            'makeup_db': dpg_get_value(input_value06_tag),
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'
        input_value06_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input06Value'

        dpg_set_value(input_value02_tag, setting_dict.get('threshold_db', DEFAULT_THRESHOLD_DB))
        dpg_set_value(input_value03_tag, setting_dict.get('ratio', DEFAULT_RATIO))
        dpg_set_value(input_value04_tag, setting_dict.get('attack_ms', DEFAULT_ATTACK_MS))
        dpg_set_value(input_value05_tag, setting_dict.get('release_ms', DEFAULT_RELEASE_MS))
        dpg_set_value(input_value06_tag, setting_dict.get('makeup_db', DEFAULT_MAKEUP_DB))
