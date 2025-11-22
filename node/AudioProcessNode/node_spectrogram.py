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

# Default spectrogram method
DEFAULT_SPECTROGRAM_METHOD = 'mel'

def create_mel_spectrogram(audio_data, sample_rate=22050, n_fft=2048, hop_length=512):
    """
    Create a mel spectrogram from audio data.
    
    Args:
        audio_data: numpy array of audio samples
        sample_rate: sample rate of the audio
        n_fft: FFT window size
        hop_length: number of samples between successive frames
        
    Returns:
        RGB image of the mel spectrogram
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


def create_stft_spectrogram(audio_data, sample_rate=22050, n_fft=2048, hop_length=512):
    """
    Create a STFT (Short-Time Fourier Transform) linear frequency spectrogram.
    
    Args:
        audio_data: numpy array of audio samples
        sample_rate: sample rate of the audio
        n_fft: FFT window size
        hop_length: number of samples between successive frames
        
    Returns:
        RGB image of the STFT spectrogram
    """
    if audio_data is None or len(audio_data) == 0:
        return None
    
    # Compute STFT
    stft = librosa.stft(
        y=audio_data,
        n_fft=n_fft,
        hop_length=hop_length
    )
    
    # Convert to magnitude and then to decibels
    stft_db = librosa.amplitude_to_db(np.abs(stft), ref=np.max)
    
    # Normalize to 0-255 range
    stft_normalized = cv2.normalize(stft_db, None, 0, 255, cv2.NORM_MINMAX)
    stft_uint8 = stft_normalized.astype(np.uint8)
    
    # Apply colormap
    colored_spec = cv2.applyColorMap(stft_uint8, cv2.COLORMAP_VIRIDIS)
    
    # Convert BGR to RGB
    colored_spec_rgb = cv2.cvtColor(colored_spec, cv2.COLOR_BGR2RGB)
    
    # Flip vertically so low frequencies are at the bottom
    colored_spec_rgb = np.flipud(colored_spec_rgb)
    
    return colored_spec_rgb


def create_chromagram(audio_data, sample_rate=22050, n_fft=2048, hop_length=512):
    """
    Create a chromagram (pitch class representation).
    
    Args:
        audio_data: numpy array of audio samples
        sample_rate: sample rate of the audio
        n_fft: FFT window size
        hop_length: number of samples between successive frames
        
    Returns:
        RGB image of the chromagram
    """
    if audio_data is None or len(audio_data) == 0:
        return None
    
    # Compute chromagram
    chroma = librosa.feature.chroma_stft(
        y=audio_data,
        sr=sample_rate,
        n_fft=n_fft,
        hop_length=hop_length
    )
    
    # Normalize to 0-255 range
    chroma_normalized = cv2.normalize(chroma, None, 0, 255, cv2.NORM_MINMAX)
    chroma_uint8 = chroma_normalized.astype(np.uint8)
    
    # Apply colormap
    colored_spec = cv2.applyColorMap(chroma_uint8, cv2.COLORMAP_PLASMA)
    
    # Convert BGR to RGB
    colored_spec_rgb = cv2.cvtColor(colored_spec, cv2.COLOR_BGR2RGB)
    
    # Flip vertically for consistency
    colored_spec_rgb = np.flipud(colored_spec_rgb)
    
    return colored_spec_rgb


def create_mfcc(audio_data, sample_rate=22050, n_fft=2048, hop_length=512, n_mfcc=20):
    """
    Create MFCC (Mel-Frequency Cepstral Coefficients) visualization.
    
    Args:
        audio_data: numpy array of audio samples
        sample_rate: sample rate of the audio
        n_fft: FFT window size
        hop_length: number of samples between successive frames
        n_mfcc: number of MFCCs to compute
        
    Returns:
        RGB image of the MFCC visualization
    """
    if audio_data is None or len(audio_data) == 0:
        return None
    
    # Compute MFCCs
    mfccs = librosa.feature.mfcc(
        y=audio_data,
        sr=sample_rate,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mfcc=n_mfcc
    )
    
    # Normalize to 0-255 range
    mfcc_normalized = cv2.normalize(mfccs, None, 0, 255, cv2.NORM_MINMAX)
    mfcc_uint8 = mfcc_normalized.astype(np.uint8)
    
    # Apply colormap
    colored_spec = cv2.applyColorMap(mfcc_uint8, cv2.COLORMAP_JET)
    
    # Convert BGR to RGB
    colored_spec_rgb = cv2.cvtColor(colored_spec, cv2.COLOR_BGR2RGB)
    
    # Flip vertically for consistency
    colored_spec_rgb = np.flipud(colored_spec_rgb)
    
    return colored_spec_rgb


def create_spectrogram(audio_data, sample_rate=22050, n_fft=2048, hop_length=512, method=DEFAULT_SPECTROGRAM_METHOD):
    """
    Create a spectrogram from audio data using the specified method.
    
    Args:
        audio_data: numpy array of audio samples
        sample_rate: sample rate of the audio
        n_fft: FFT window size
        hop_length: number of samples between successive frames
        method: spectrogram method ('mel', 'stft', 'chromagram', 'mfcc')
        
    Returns:
        RGB image of the spectrogram
    """
    if method == 'mel':
        return create_mel_spectrogram(audio_data, sample_rate, n_fft, hop_length)
    elif method == 'stft':
        return create_stft_spectrogram(audio_data, sample_rate, n_fft, hop_length)
    elif method == 'chromagram':
        return create_chromagram(audio_data, sample_rate, n_fft, hop_length)
    elif method == 'mfcc':
        return create_mfcc(audio_data, sample_rate, n_fft, hop_length)
    else:
        # Default to mel spectrogram
        return create_mel_spectrogram(audio_data, sample_rate, n_fft, hop_length)


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
        node.tag_node_method_name = node.tag_node_name + ':Method'

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
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_method_name,
                    items=['mel', 'stft', 'chromagram', 'mfcc'],
                    default_value=DEFAULT_SPECTROGRAM_METHOD,
                    width=150,
                    label='Method',
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
        method_tag = tag_node_name + ':Method'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get selected spectrogram method
        method = dpg_get_value(method_tag)
        if method is None:
            method = DEFAULT_SPECTROGRAM_METHOD

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
            frame = create_spectrogram(
                audio_data, 
                sample_rate, 
                n_fft=2048, 
                hop_length=512, 
                method=method
            )

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
        method_tag = tag_node_name + ':Method'

        pos = dpg.get_item_pos(tag_node_name)
        method = dpg_get_value(method_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict['method'] = method if method is not None else DEFAULT_SPECTROGRAM_METHOD

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        method_tag = tag_node_name + ':Method'
        
        method = setting_dict.get('method', DEFAULT_SPECTROGRAM_METHOD)
        dpg_set_value(method_tag, method)
