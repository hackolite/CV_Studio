#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Noise Gate node – silences audio below a configurable RMS threshold.

Useful as a pre-processing step before AI audio classification to remove
background noise and ensure only meaningful audio reaches the model.

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
# Gate defaults
DEFAULT_THRESHOLD_DB = -40.0
DEFAULT_ATTACK_MS = 5.0
DEFAULT_RELEASE_MS = 50.0


def apply_noise_gate(audio_data, threshold_db=-40.0, attack_ms=5.0, release_ms=50.0, sample_rate=16000):
    """Apply a simple noise gate to audio data.

    Samples whose local RMS is below *threshold_db* are attenuated to zero.
    A short attack/release envelope is applied to avoid clicks.

    Returns:
        np.ndarray: Gated audio (float32).
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    audio = audio_data.astype(np.float32)
    frame_len = max(1, int(sample_rate * 0.01))  # 10 ms frames

    # Compute per-sample RMS using a sliding window (simplified: per-frame)
    n = len(audio)
    envelope = np.zeros(n, dtype=np.float32)

    for start in range(0, n, frame_len):
        end = min(start + frame_len, n)
        frame = audio[start:end]
        rms = float(np.sqrt(np.mean(frame ** 2)))
        rms_db = 20.0 * np.log10(max(rms, 1e-10))
        gate_open = 1.0 if rms_db >= threshold_db else 0.0
        envelope[start:end] = gate_open

    # Smooth envelope with attack/release
    attack_samples = max(1, int(sample_rate * attack_ms / 1000.0))
    release_samples = max(1, int(sample_rate * release_ms / 1000.0))

    smoothed = np.zeros(n, dtype=np.float32)
    smoothed[0] = envelope[0]
    for i in range(1, n):
        if envelope[i] > smoothed[i - 1]:
            coeff = 1.0 - np.exp(-1.0 / attack_samples)
            smoothed[i] = smoothed[i - 1] + coeff * (envelope[i] - smoothed[i - 1])
        else:
            coeff = 1.0 - np.exp(-1.0 / release_samples)
            smoothed[i] = smoothed[i - 1] + coeff * (envelope[i] - smoothed[i - 1])

    return (audio * smoothed).astype(np.float32)


class FactoryNode:
    node_label = 'NoiseGate'
    node_tag = 'NoiseGate'

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

        # Threshold (dB)
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02Value'

        # Attack (ms)
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'

        # Release (ms)
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
            # Audio input
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input Audio',
                )

            # Threshold slider
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input02_value_name,
                    label='Threshold (dB)',
                    default_value=DEFAULT_THRESHOLD_DB,
                    min_value=-80.0,
                    max_value=0.0,
                    width=small_window_w,
                    callback=callback,
                )

            # Attack slider
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label='Attack (ms)',
                    default_value=DEFAULT_ATTACK_MS,
                    min_value=0.1,
                    max_value=100.0,
                    width=small_window_w,
                    callback=callback,
                )

            # Release slider
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input04_value_name,
                    label='Release (ms)',
                    default_value=DEFAULT_RELEASE_MS,
                    min_value=1.0,
                    max_value=500.0,
                    width=small_window_w,
                    callback=callback,
                )

            # Audio output
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output01_value_name,
                    default_value='Output Audio',
                )

            # Performance counter
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

    node_label = 'NoiseGate'
    node_tag = 'NoiseGate'

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
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        use_pref_counter = False
        if self._opencv_setting_dict:
            use_pref_counter = self._opencv_setting_dict.get('use_pref_counter', False)

        # Read parameters
        try:
            threshold_db = dpg_get_value(input_value02_tag)
            attack_ms = dpg_get_value(input_value03_tag)
            release_ms = dpg_get_value(input_value04_tag)
        except Exception:
            threshold_db = DEFAULT_THRESHOLD_DB
            attack_ms = DEFAULT_ATTACK_MS
            release_ms = DEFAULT_RELEASE_MS

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

        # Apply noise gate
        processed_audio = None
        if audio_data is not None:
            try:
                processed_audio = apply_noise_gate(
                    audio_data, threshold_db, attack_ms, release_ms, sample_rate
                )
            except Exception as e:
                logger.error(f"Error in noise gate: {e}", exc_info=True)
                processed_audio = audio_data

        if use_pref_counter:
            elapsed_time = int((time.monotonic() - start_time) * 1000)
            try:
                dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception:
                pass

        # Build output preserving metadata
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

        return {
            'ver': self._ver,
            'pos': pos,
            'threshold_db': dpg_get_value(input_value02_tag),
            'attack_ms': dpg_get_value(input_value03_tag),
            'release_ms': dpg_get_value(input_value04_tag),
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'

        dpg_set_value(input_value02_tag, setting_dict.get('threshold_db', DEFAULT_THRESHOLD_DB))
        dpg_set_value(input_value03_tag, setting_dict.get('attack_ms', DEFAULT_ATTACK_MS))
        dpg_set_value(input_value04_tag, setting_dict.get('release_ms', DEFAULT_RELEASE_MS))
