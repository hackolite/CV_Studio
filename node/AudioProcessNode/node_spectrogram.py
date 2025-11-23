#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import cv2
import numpy as np
import dearpygui.dearpygui as dpg
import librosa

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode

# Import STFT-based functions from spectrogram_utils
from node.InputNode.spectrogram_utils import (
    fourier_transformation,
    make_logscale,
    create_spectrogram_from_audio,
    apply_colormap_to_spectrogram,
    REFERENCE_AMPLITUDE
)


def create_mel_spectrogram(audio_data, sample_rate=22050):
    """Create mel spectrogram using librosa"""
    mel_spec = librosa.feature.melspectrogram(y=audio_data, sr=sample_rate, n_fft=2048, hop_length=512, n_mels=128)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    mel_spec_db_transposed = np.transpose(mel_spec_db)
    spec_image = apply_colormap_to_spectrogram(mel_spec_db_transposed, method='cv2', cmap='INFERNO')
    spec_image = np.flipud(spec_image)
    return spec_image


def create_stft_spectrogram(audio_data, sample_rate=22050):
    """Create STFT spectrogram using librosa"""
    stft = librosa.stft(audio_data, n_fft=2048, hop_length=512)
    stft_db = librosa.amplitude_to_db(np.abs(stft), ref=np.max)
    stft_db_transposed = np.transpose(stft_db)
    spec_image = apply_colormap_to_spectrogram(stft_db_transposed, method='cv2', cmap='VIRIDIS')
    spec_image = np.flipud(spec_image)
    return spec_image


def create_chromagram(audio_data, sample_rate=22050):
    """Create chromagram using librosa"""
    chroma = librosa.feature.chroma_stft(y=audio_data, sr=sample_rate, n_fft=2048, hop_length=512)
    chroma_transposed = np.transpose(chroma)
    spec_image = apply_colormap_to_spectrogram(chroma_transposed, method='cv2', cmap='PLASMA')
    spec_image = np.flipud(spec_image)
    return spec_image


def create_mfcc(audio_data, sample_rate=22050):
    """Create MFCC using librosa"""
    mfcc = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_fft=2048, hop_length=512, n_mfcc=20)
    mfcc_transposed = np.transpose(mfcc)
    spec_image = apply_colormap_to_spectrogram(mfcc_transposed, method='cv2', cmap='JET')
    spec_image = np.flipud(spec_image)
    return spec_image


def create_stft_custom(audio_data, sample_rate=22050, binsize=1024, colormap="jet"):
    """Create STFT spectrogram using custom fourier_transformation method"""
    return create_spectrogram_from_audio(audio_data, sample_rate, binsize, colormap)


class FactoryNode:
    node_label = 'Spectrogram'
    node_tag = 'Spectrogram'
    
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
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create black texture for initial display
        black_image = np.zeros((small_window_w, small_window_h, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        # Register texture
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Create node UI
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

            # Method selector
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=['mel', 'stft', 'stft_custom', 'chromagram', 'mfcc'],
                    default_value='mel',
                    width=small_window_w - 0,
                    label="Method",
                    tag=node.tag_node_input02_value_name,
                    callback=callback,
                )

            # Image output
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

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

    node_label = 'Spectrogram'
    node_tag = 'Spectrogram'

    _opencv_setting_dict = None

    def __init__(self):
        pass

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
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        # Handle case when _opencv_setting_dict is None
        if self._opencv_setting_dict is None:
            small_window_w = 240
            small_window_h = 135
            use_pref_counter = False
        else:
            small_window_w = self._opencv_setting_dict['process_width']
            small_window_h = self._opencv_setting_dict['process_height']
            use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get the selected method
        try:
            method = dpg_get_value(input_value02_tag)
        except:
            method = 'mel'  # Default method if dpg is not available

        # Get audio input
        audio_data = None
        sample_rate = 22050  # Default sample rate
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_AUDIO:
                connection_info_src = ':'.join(connection_info[0].split(':')[:2])
                audio_tuple = node_audio_dict.get(connection_info_src, None)
                if audio_tuple is not None and len(audio_tuple) == 2:
                    audio_data, sample_rate = audio_tuple
                break

        frame = None
        
        if audio_data is not None and use_pref_counter:
            start_time = time.monotonic()

        if audio_data is not None:
            try:
                # Create spectrogram based on selected method
                if method == 'mel':
                    frame = create_mel_spectrogram(audio_data, sample_rate)
                elif method == 'stft':
                    frame = create_stft_spectrogram(audio_data, sample_rate)
                elif method == 'chromagram':
                    frame = create_chromagram(audio_data, sample_rate)
                elif method == 'mfcc':
                    frame = create_mfcc(audio_data, sample_rate)
                elif method == 'stft_custom':
                    frame = create_stft_custom(audio_data, sample_rate, binsize=1024, colormap="jet")
                else:
                    # Default to mel
                    frame = create_mel_spectrogram(audio_data, sample_rate)
            except Exception as e:
                print(f"Error creating spectrogram: {e}")
                frame = None

        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            try:
                dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')
            except:
                pass  # Ignore if DPG is not available

        if frame is not None:
            try:
                texture = self.convert_cv_to_dpg(
                    frame,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(output_value01_tag, texture)
            except:
                pass  # Ignore if DPG is not available

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'

        pos = dpg.get_item_pos(tag_node_name)
        method = dpg_get_value(input_value02_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict['method'] = method

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'

        method = setting_dict.get('method', 'mel')
        dpg_set_value(input_value02_tag, method)
