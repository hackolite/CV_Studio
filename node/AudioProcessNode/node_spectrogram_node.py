#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Spectrogram Node - Converts audio to spectrogram visualization
"""
import time
import os

import cv2
import numpy as np
import dearpygui.dearpygui as dpg
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node

# Import spectrogram utility functions from the existing module
from node.AudioProcessNode.node_spectrogram import (
    fourier_transformation,
    make_logscale,
    REFERENCE_AMPLITUDE
)


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
        node = SpectrogramNode()
        node.tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Input: Audio
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01Value'
        
        # Output: Image (spectrogram)
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        
        # Output: Processing time
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        
        # Static parameter: FFT size (binsize)
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02Value'
        
        # Static parameter: Colormap
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input03Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create black placeholder image
        black_image = np.zeros((small_window_h, small_window_w, 3))
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
                label=node.node_label,
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

            # Image output (spectrogram visualization)
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # FFT size parameter
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    ['512', '1024', '2048', '4096'],
                    default_value='1024',
                    width=small_window_w - 0,
                    label="FFT Size",
                    tag=node.tag_node_input02_value_name,
                )

            # Colormap parameter
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    ['jet', 'viridis', 'plasma', 'inferno', 'magma', 'hot', 'cool'],
                    default_value='jet',
                    width=small_window_w - 0,
                    label="Colormap",
                    tag=node.tag_node_input03_value_name,
                )

            # Processing time output
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


class SpectrogramNode(Node):
    _ver = '0.0.1'

    node_label = 'Spectrogram'
    node_tag = 'Spectrogram'

    _opencv_setting_dict = None

    def __init__(self):
        super().__init__()
        # Set node-specific attributes after parent init
        self.node_label = 'Spectrogram'
        self.node_tag = 'Spectrogram'

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get audio input from connection
        audio_data = self._get_audio_input(connection_list, node_audio_dict)
        
        if audio_data is None:
            # No audio input, return None
            return {"image": None, "json": None, "audio": None}

        # Get parameters
        fft_size_str = dpg_get_value(input_value02_tag)
        fft_size = int(fft_size_str)
        colormap = dpg_get_value(input_value03_tag)

        # Start timing
        if use_pref_counter:
            start_time = time.monotonic()

        # Generate spectrogram
        try:
            spectrogram_image = self._generate_spectrogram(
                audio_data,
                fft_size=fft_size,
                colormap=colormap
            )
        except Exception as e:
            print(f"Error generating spectrogram: {e}")
            return {"image": None, "json": None, "audio": None}

        # Update timing
        if use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')

        # Update output texture
        if spectrogram_image is not None:
            texture = self.convert_cv_to_dpg(
                spectrogram_image,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": spectrogram_image, "json": None, "audio": None}

    def _get_audio_input(self, connection_list, node_audio_dict):
        """Get audio data from input connection"""
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_AUDIO:
                connection_info_src = ':'.join(connection_info[0].split(':')[:2])
                audio_data = node_audio_dict.get(connection_info_src, None)
                return audio_data
        return None

    def _generate_spectrogram(self, audio_data, fft_size=1024, colormap='jet'):
        """
        Generate spectrogram image from audio data.
        
        Args:
            audio_data: Dictionary with 'samples' (numpy array) and 'sample_rate' (int)
            fft_size: FFT window size (binsize)
            colormap: Matplotlib colormap name
            
        Returns:
            BGR image as numpy array
        """
        if not isinstance(audio_data, dict):
            print(f"Warning: audio_data is not a dict, type: {type(audio_data)}")
            return None
            
        if 'samples' not in audio_data or 'sample_rate' not in audio_data:
            print(f"Warning: audio_data missing required keys: {audio_data.keys() if isinstance(audio_data, dict) else 'N/A'}")
            return None

        samples = audio_data['samples']
        sample_rate = audio_data['sample_rate']

        if samples is None or len(samples) == 0:
            return None

        # Ensure samples is 1D (mono)
        if len(samples.shape) > 1:
            samples = samples.mean(axis=1)

        # Convert to int16 if needed (for compatibility with scipy.io.wavfile)
        if samples.dtype != np.int16:
            # Normalize to [-1, 1] if needed
            if samples.max() > 1.0 or samples.min() < -1.0:
                samples = samples / np.max(np.abs(samples))
            samples = (samples * 32767).astype(np.int16)

        try:
            # Perform Fourier transformation
            s = fourier_transformation(samples, fft_size)
            
            # Apply logarithmic scale
            sshow, freq = make_logscale(s, factor=1.0, sr=sample_rate)
            
            # Convert to decibels
            ims = 20. * np.log10(np.abs(sshow) / REFERENCE_AMPLITUDE)
            
            timebins, freqbins = np.shape(ims)
            
            # Create figure and plot
            fig = plt.figure(figsize=(8, 4))
            plt.imshow(
                np.transpose(ims),
                origin="lower",
                aspect="auto",
                cmap=colormap,
                interpolation="none"
            )
            
            # Add axis labels
            xlocs = np.float32(np.linspace(0, timebins-1, 5))
            plt.xticks(
                xlocs,
                ["%.02f" % l for l in ((xlocs*len(samples)/timebins)+(0.5*fft_size))/sample_rate]
            )
            
            ylocs = np.int16(np.round(np.linspace(0, freqbins-1, 10)))
            plt.yticks(ylocs, ["%.02f" % freq[i] for i in ylocs])
            
            plt.xlabel('Time (s)')
            plt.ylabel('Frequency (Hz)')
            
            # Convert figure to image
            fig.canvas.draw()
            
            # Get image as numpy array (updated for newer matplotlib versions)
            buf = fig.canvas.buffer_rgba()
            img = np.asarray(buf)
            
            # Convert RGBA to BGR for OpenCV
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            
            plt.close(fig)
            
            return img
            
        except Exception as e:
            print(f"Error in spectrogram generation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def close(self, node_id):
        """Cleanup method"""
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'

        fft_size = dpg_get_value(input_value02_tag)
        colormap = dpg_get_value(input_value03_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = fft_size
        setting_dict[input_value03_tag] = colormap

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'

        fft_size = setting_dict.get(input_value02_tag, '1024')
        colormap = setting_dict.get(input_value03_tag, 'jet')

        dpg_set_value(input_value02_tag, fft_size)
        dpg_set_value(input_value03_tag, colormap)
