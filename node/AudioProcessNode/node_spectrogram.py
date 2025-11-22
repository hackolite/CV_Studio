#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import numpy as np
import cv2
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from node.InputNode.spectrogram_utils import (
    fourier_transformation, 
    make_logscale, 
    create_spectrogram_from_audio,
    REFERENCE_AMPLITUDE
)

DEFAULT_SPECTROGRAM_METHOD = 'stft_custom'

# Available spectrogram methods for future combo box implementation
SPECTROGRAM_METHODS = {
    'stft_custom': 'STFT Custom',
}
# Placeholder for combo box - dpg.add_combo(items=['stft_custom'], ...)
SPECTROGRAM_METHOD_ITEMS = ['stft_custom']

# ---------------------------
# Générateur de spectrogramme
# ---------------------------
def create_spectrogram_custom(audio_data, sample_rate=22050, n_fft=1024, hop_length=512):
    """
    Crée un spectrogramme compatible avec le modèle pré-entraîné.
    """
    if audio_data is None or len(audio_data) == 0:
        return None

    # STFT custom
    S = fourier_transformation(audio_data, n_fft)
    # Log scale
    S_log, freqs_log = make_logscale(S, sr=sample_rate, factor=1.0)
    # Convert to magnitude and dB
    ims = 20. * np.log10(np.abs(S_log) / REFERENCE_AMPLITUDE)
    # Transpose to get correct orientation (frequencies on Y-axis)
    ims_transposed = np.transpose(ims)
    # Normalisation
    S_norm = cv2.normalize(ims_transposed, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    # Colormap JET
    colored = cv2.applyColorMap(S_norm, cv2.COLORMAP_JET)
    # BGR → RGB
    colored_rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
    # Flip vertical
    return np.flipud(colored_rgb)

# Alias for backwards compatibility with tests
def create_stft_custom(audio_data, sample_rate=22050, n_fft=1024, hop_length=512):
    """Alias for create_spectrogram_custom for backwards compatibility."""
    return create_spectrogram_custom(audio_data, sample_rate, n_fft, hop_length)

# ---------------------------
# Factory Node
# ---------------------------
class FactoryNode:
    node_label = 'Spectrogram'
    node_tag = 'Spectrogram'

    def add_node(self, parent, node_id, pos=[0,0], opencv_setting_dict=None, callback=None):
        node = Node()
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        node.tag_node_input_name = f"{node.tag_node_name}:{node.TYPE_AUDIO}:Input01"
        node.tag_node_input_value = f"{node.tag_node_name}:{node.TYPE_AUDIO}:Input01Value"
        node.tag_node_output_name = f"{node.tag_node_name}:{node.TYPE_IMAGE}:Output01"
        node.tag_node_output_value = f"{node.tag_node_name}:{node.TYPE_IMAGE}:Output01Value"
        node.tag_node_time_value = f"{node.tag_node_name}:{node.TYPE_TIME_MS}:Output02Value"

        node._opencv_setting_dict = opencv_setting_dict
        w, h = node._opencv_setting_dict['process_width'], node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        black_img = np.zeros((h, w, 3))
        black_tex = node.convert_cv_to_dpg(black_img, w, h)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(w, h, black_tex, tag=node.tag_node_output_value, format=dpg.mvFormat_Float_rgb)

        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):
            with dpg.node_attribute(tag=node.tag_node_input_name, attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text(tag=node.tag_node_input_value, default_value="Input Audio")
            with dpg.node_attribute(tag=node.tag_node_output_name, attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_image(node.tag_node_output_value)
            if use_pref_counter:
                with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                    dpg.add_text(tag=node.tag_node_time_value, default_value="elapsed time(ms)")

        return node

# ---------------------------
# Node
# ---------------------------
class Node(Node):
    _ver = '1.0.0'
    node_label = 'Spectrogram'
    node_tag = 'Spectrogram'
    _opencv_setting_dict = None

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        tag_node_name = f"{node_id}:{self.node_tag}"
        output_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output01Value"
        time_tag = f"{tag_node_name}:{self.TYPE_TIME_MS}:Output02Value"

        w, h = self._opencv_setting_dict['process_width'], self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Récupère l'audio depuis les connections
        audio_data, sample_rate = None, 22050
        for conn in connection_list:
            if conn[0].split(':')[2] == self.TYPE_AUDIO:
                src = ':'.join(conn[0].split(':')[:2])
                audio_dict_entry = node_audio_dict.get(src, None)
                if audio_dict_entry:
                    audio_data = audio_dict_entry.get('data', None)
                    sample_rate = audio_dict_entry.get('sample_rate', 22050)
                break

        frame = None
        if audio_data is not None and use_pref_counter:
            start = time.monotonic()

        if audio_data is not None:
            frame = create_spectrogram_custom(audio_data, sample_rate=sample_rate)

        if audio_data is not None and use_pref_counter:
            elapsed = int((time.monotonic() - start) * 1000)
            dpg_set_value(time_tag, f"{elapsed:04d}ms")

        if frame is not None:
            texture = self.convert_cv_to_dpg(frame, w, h)
            dpg_set_value(output_tag, texture)

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        pos = dpg.get_item_pos(f"{node_id}:{self.node_tag}")
        return {'ver': self._ver, 'pos': pos, 'method': DEFAULT_SPECTROGRAM_METHOD}

    def set_setting_dict(self, node_id, setting_dict):
        pass

