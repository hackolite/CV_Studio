#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg
import librosa
import librosa.display

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC

from node.basenode import Node

def create_spectrogram(audio_data, sample_rate=22050, n_fft=2048, hop_length=512):
    """
    Create a spectrogram from audio data.
    
    Args:
        audio_data: numpy array of audio samples
        sample_rate: sample rate of the audio
        n_fft: FFT window size
        hop_length: number of samples between successive frames
        
    Returns:
        RGB image of the spectrogram
    """
    if audio_data is None or len(audio_data) == 0:
        return None
    
    # Compute mel spectrogram
    mel_spec = librosa.feature.melspectrogram(
        y=audio_data, 
        sr=sample_rate, 
        n_fft=n_fft, 
        hop_length=hop_length
    )
    
    # Convert to decibels
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    # Normalize to 0-255 range
    mel_spec_normalized = cv2.normalize(mel_spec_db, None, 0, 255, cv2.NORM_MINMAX)
    mel_spec_uint8 = mel_spec_normalized.astype(np.uint8)
    
    # Apply colormap
    colored_spec = cv2.applyColorMap(mel_spec_uint8, cv2.COLORMAP_INFERNO)
    
    # Convert BGR to RGB
    colored_spec_rgb = cv2.cvtColor(colored_spec, cv2.COLOR_BGR2RGB)
    
    # Flip vertically so low frequencies are at the bottom
    colored_spec_rgb = np.flipud(colored_spec_rgb)
    
    return colored_spec_rgb


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
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']


        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )


        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )


        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
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
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

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


class Node(Node):
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
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get audio input from connections
        audio_data = None
        sample_rate = 22050  # default sample rate
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_AUDIO:
                connection_info_src = ':'.join(connection_info[0].split(':')[:2])
                audio_dict_entry = node_audio_dict.get(connection_info_src, None)
                
                if audio_dict_entry is not None and isinstance(audio_dict_entry, dict):
                    audio_data = audio_dict_entry.get('data', None)
                    sample_rate = audio_dict_entry.get('sample_rate', 22050)
                break

        frame = None
        
        if audio_data is not None and use_pref_counter:
            start_time = time.monotonic()

        if audio_data is not None:
            frame = create_spectrogram(audio_data, sample_rate)

        if audio_data is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')

        if frame is not None:
            texture = self.convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
