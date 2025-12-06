#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import numpy as np
import dearpygui.dearpygui as dpg
from scipy import signal

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Constants
DEFAULT_SAMPLE_RATE = 22050
GAIN_THRESHOLD = 0.01  # Minimum gain value (in dB) to apply filtering
NYQUIST_MARGIN = 100  # Frequency margin from Nyquist frequency for filter stability


def apply_equalizer(audio_data, sample_rate, gains):
    """
    Apply a standard 5-band equalizer to audio data.
    
    Args:
        audio_data (np.ndarray or None): Mono audio samples as float32 numpy array.
                                         Can be None or empty array.
        sample_rate (int): Sample rate in Hz (e.g., 22050, 44100)
        gains (dict): Dictionary with keys 'bass', 'mid_bass', 'mid', 'mid_treble', 'treble'
                     Values are gain adjustments in dB (typically -20 to +20)
    
    Returns:
        tuple: (processed_audio, band_levels)
            - processed_audio (np.ndarray or None): Processed audio data as float32 numpy array, normalized to [-1.0, 1.0].
                                                    Returns None if input is None, or empty array if input is empty.
            - band_levels (dict): Dictionary with RMS levels for each band (0.0 to 1.0)
                                 Keys: 'bass', 'mid_bass', 'mid', 'mid_treble', 'treble'
    
    Raises:
        No exceptions are raised. Invalid inputs return the original data or None with zero levels.
    """
    if audio_data is None or len(audio_data) == 0:
        # Return zero levels for all bands
        zero_levels = {
            'bass': 0.0,
            'mid_bass': 0.0,
            'mid': 0.0,
            'mid_treble': 0.0,
            'treble': 0.0
        }
        return audio_data, zero_levels
    
    # Define frequency bands (in Hz)
    # Bass: 20-250 Hz
    # Mid-Bass: 250-500 Hz
    # Mid: 500-2000 Hz
    # Mid-Treble: 2000-6000 Hz
    # Treble: 6000-20000 Hz
    
    bands = [
        ('bass', 20, 250),
        ('mid_bass', 250, 500),
        ('mid', 500, 2000),
        ('mid_treble', 2000, 6000),
        ('treble', 6000, min(20000, sample_rate // 2 - NYQUIST_MARGIN))
    ]
    
    # Start with the original signal
    output = np.zeros_like(audio_data, dtype=np.float32)
    
    # Dictionary to store band levels (RMS)
    band_levels = {}
    
    for band_name, low_freq, high_freq in bands:
        gain_db = gains.get(band_name, 0.0)
        
        # Skip if gain is zero (no change)
        if abs(gain_db) < GAIN_THRESHOLD:
            # Add the original band without modification
            if low_freq == 20:
                # Low-pass for bass
                sos = signal.butter(4, high_freq, btype='low', fs=sample_rate, output='sos')
            elif high_freq >= sample_rate // 2 - NYQUIST_MARGIN:
                # High-pass for treble
                sos = signal.butter(4, low_freq, btype='high', fs=sample_rate, output='sos')
            else:
                # Band-pass for mid frequencies
                sos = signal.butter(4, [low_freq, high_freq], btype='band', fs=sample_rate, output='sos')
            
            filtered = signal.sosfilt(sos, audio_data)
            output += filtered
            
            # Calculate RMS level for this band
            rms_level = np.sqrt(np.mean(filtered ** 2))
            band_levels[band_name] = min(rms_level, 1.0)
        else:
            # Convert dB to linear gain
            gain_linear = 10 ** (gain_db / 20.0)
            
            # Create bandpass filter for this frequency range
            if low_freq == 20:
                # Low-pass filter for bass
                sos = signal.butter(4, high_freq, btype='low', fs=sample_rate, output='sos')
            elif high_freq >= sample_rate // 2 - NYQUIST_MARGIN:
                # High-pass filter for treble
                sos = signal.butter(4, low_freq, btype='high', fs=sample_rate, output='sos')
            else:
                # Band-pass filter for mid frequencies
                sos = signal.butter(4, [low_freq, high_freq], btype='band', fs=sample_rate, output='sos')
            
            # Apply filter and gain
            filtered = signal.sosfilt(sos, audio_data)
            output += filtered * gain_linear
            
            # Calculate RMS level for this band (after gain applied)
            rms_level = np.sqrt(np.mean((filtered * gain_linear) ** 2))
            band_levels[band_name] = min(rms_level, 1.0)
    
    # Normalize to prevent clipping
    max_val = np.max(np.abs(output))
    if max_val > 1.0:
        output = output / max_val
    
    return output.astype(np.float32), band_levels


class FactoryNode:
    node_label = 'Equalizer'
    node_tag = 'Equalizer'
    
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
        
        # Bass gain
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02Value'
        
        # Mid-Bass gain
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        
        # Mid gain
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04Value'
        
        # Mid-Treble gain
        node.tag_node_input05_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input05'
        node.tag_node_input05_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input05Value'
        
        # Treble gain
        node.tag_node_input06_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input06'
        node.tag_node_input06_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input06Value'
        
        # Band level meters (using consistent naming pattern)
        node.tag_node_bass_level_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':BassLevel'
        node.tag_node_mid_bass_level_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':MidBassLevel'
        node.tag_node_mid_level_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':MidLevel'
        node.tag_node_mid_treble_level_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':MidTrebleLevel'
        node.tag_node_treble_level_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':TrebleLevel'
        
        # Audio output
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Output01Value'
        
        # Performance counter
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict.get('process_width', 240) if opencv_setting_dict else 240
        use_pref_counter = node._opencv_setting_dict.get('use_pref_counter', False) if opencv_setting_dict else False

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

            # Bass gain slider (20-250 Hz)
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    default_value=0.0,
                    min_value=-20.0,
                    max_value=20.0,
                    width=small_window_w - 20,
                    label="Bass (dB)",
                    tag=node.tag_node_input02_value_name,
                    callback=callback,
                )

            # Mid-Bass gain slider (250-500 Hz)
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    default_value=0.0,
                    min_value=-20.0,
                    max_value=20.0,
                    width=small_window_w - 20,
                    label="Mid-Bass (dB)",
                    tag=node.tag_node_input03_value_name,
                    callback=callback,
                )

            # Mid gain slider (500-2000 Hz)
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    default_value=0.0,
                    min_value=-20.0,
                    max_value=20.0,
                    width=small_window_w - 20,
                    label="Mid (dB)",
                    tag=node.tag_node_input04_value_name,
                    callback=callback,
                )

            # Mid-Treble gain slider (2000-6000 Hz)
            with dpg.node_attribute(
                    tag=node.tag_node_input05_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    default_value=0.0,
                    min_value=-20.0,
                    max_value=20.0,
                    width=small_window_w - 20,
                    label="Mid-Treble (dB)",
                    tag=node.tag_node_input05_value_name,
                    callback=callback,
                )

            # Treble gain slider (6000-20000 Hz)
            with dpg.node_attribute(
                    tag=node.tag_node_input06_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    default_value=0.0,
                    min_value=-20.0,
                    max_value=20.0,
                    width=small_window_w - 20,
                    label="Treble (dB)",
                    tag=node.tag_node_input06_value_name,
                    callback=callback,
                )

            # Band level meters
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':BandLevels',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("Band Levels:")
                dpg.add_progress_bar(
                    label="Bass",
                    tag=node.tag_node_bass_level_name,
                    default_value=0.0,
                    overlay="Bass: 0.00",
                    width=small_window_w - 20,
                )
                dpg.add_progress_bar(
                    label="Mid-Bass",
                    tag=node.tag_node_mid_bass_level_name,
                    default_value=0.0,
                    overlay="Mid-Bass: 0.00",
                    width=small_window_w - 20,
                )
                dpg.add_progress_bar(
                    label="Mid",
                    tag=node.tag_node_mid_level_name,
                    default_value=0.0,
                    overlay="Mid: 0.00",
                    width=small_window_w - 20,
                )
                dpg.add_progress_bar(
                    label="Mid-Treble",
                    tag=node.tag_node_mid_treble_level_name,
                    default_value=0.0,
                    overlay="Mid-Treble: 0.00",
                    width=small_window_w - 20,
                )
                dpg.add_progress_bar(
                    label="Treble",
                    tag=node.tag_node_treble_level_name,
                    default_value=0.0,
                    overlay="Treble: 0.00",
                    width=small_window_w - 20,
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

    node_label = 'Equalizer'
    node_tag = 'Equalizer'

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
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'  # Bass
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'  # Mid-Bass
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'  # Mid
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'  # Mid-Treble
        input_value06_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input06Value'  # Treble
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        
        # Band level meter tags
        bass_level_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':BassLevel'
        mid_bass_level_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':MidBassLevel'
        mid_level_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':MidLevel'
        mid_treble_level_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':MidTrebleLevel'
        treble_level_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':TrebleLevel'

        # Handle case when _opencv_setting_dict is None
        if self._opencv_setting_dict is None:
            use_pref_counter = False
        else:
            use_pref_counter = self._opencv_setting_dict.get('use_pref_counter', False)

        # Get the equalizer settings
        try:
            bass_gain = dpg_get_value(input_value02_tag)
            mid_bass_gain = dpg_get_value(input_value03_tag)
            mid_gain = dpg_get_value(input_value04_tag)
            mid_treble_gain = dpg_get_value(input_value05_tag)
            treble_gain = dpg_get_value(input_value06_tag)
        except Exception as e:
            logger.debug(f"Could not get equalizer values from DPG: {e}")
            bass_gain = 0.0
            mid_bass_gain = 0.0
            mid_gain = 0.0
            mid_treble_gain = 0.0
            treble_gain = 0.0

        # Get audio input
        audio_data = None
        sample_rate = DEFAULT_SAMPLE_RATE
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_AUDIO:
                connection_info_src = ':'.join(connection_info[0].split(':')[:2])
                audio_dict_entry = node_audio_dict.get(connection_info_src, None)
                if audio_dict_entry is not None:
                    # Handle dictionary format
                    if isinstance(audio_dict_entry, dict):
                        audio_data = audio_dict_entry.get('data', None)
                        if audio_data is None:
                            logger.warning("Audio dictionary missing 'data' key")
                        sample_rate = audio_dict_entry.get('sample_rate', DEFAULT_SAMPLE_RATE)
                    # Handle legacy tuple format for backward compatibility
                    elif isinstance(audio_dict_entry, (list, tuple)) and len(audio_dict_entry) == 2:
                        audio_data, sample_rate = audio_dict_entry
                    else:
                        logger.warning(f"Unexpected audio data format: {type(audio_dict_entry)}, expected dict or tuple")
                break

        processed_audio = None
        band_levels = None
        
        if audio_data is not None and use_pref_counter:
            start_time = time.monotonic()

        if audio_data is not None:
            try:
                # Prepare gains dictionary
                gains = {
                    'bass': bass_gain,
                    'mid_bass': mid_bass_gain,
                    'mid': mid_gain,
                    'mid_treble': mid_treble_gain,
                    'treble': treble_gain
                }
                
                # Apply equalizer - now returns both processed audio and band levels
                processed_audio, band_levels = apply_equalizer(audio_data, sample_rate, gains)
                
            except Exception as e:
                logger.error(f"Error applying equalizer: {e}", exc_info=True)
                processed_audio = audio_data  # Fall back to original audio
                band_levels = None
        
        # Update band level meters
        if band_levels is not None:
            try:
                dpg_set_value(bass_level_tag, band_levels.get('bass', 0.0))
                dpg.configure_item(bass_level_tag, overlay=f"Bass: {band_levels.get('bass', 0.0):.2f}")
                dpg_set_value(mid_bass_level_tag, band_levels.get('mid_bass', 0.0))
                dpg.configure_item(mid_bass_level_tag, overlay=f"Mid-Bass: {band_levels.get('mid_bass', 0.0):.2f}")
                dpg_set_value(mid_level_tag, band_levels.get('mid', 0.0))
                dpg.configure_item(mid_level_tag, overlay=f"Mid: {band_levels.get('mid', 0.0):.2f}")
                dpg_set_value(mid_treble_level_tag, band_levels.get('mid_treble', 0.0))
                dpg.configure_item(mid_treble_level_tag, overlay=f"Mid-Treble: {band_levels.get('mid_treble', 0.0):.2f}")
                dpg_set_value(treble_level_tag, band_levels.get('treble', 0.0))
                dpg.configure_item(treble_level_tag, overlay=f"Treble: {band_levels.get('treble', 0.0):.2f}")
            except (SystemError, ValueError, Exception) as e:
                # Log error but don't fail the audio processing
                logger.debug(f"Error updating band level meters: {e}")
        else:
            # Reset meters to zero when no audio or error
            try:
                dpg_set_value(bass_level_tag, 0.0)
                dpg.configure_item(bass_level_tag, overlay="Bass: 0.00")
                dpg_set_value(mid_bass_level_tag, 0.0)
                dpg.configure_item(mid_bass_level_tag, overlay="Mid-Bass: 0.00")
                dpg_set_value(mid_level_tag, 0.0)
                dpg.configure_item(mid_level_tag, overlay="Mid: 0.00")
                dpg_set_value(mid_treble_level_tag, 0.0)
                dpg.configure_item(mid_treble_level_tag, overlay="Mid-Treble: 0.00")
                dpg_set_value(treble_level_tag, 0.0)
                dpg.configure_item(treble_level_tag, overlay="Treble: 0.00")
            except (SystemError, ValueError, Exception):
                # DPG may not be initialized or widgets may not exist yet
                pass

        if processed_audio is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            try:
                dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception as e:
                logger.debug(f"Could not set performance counter value: {e}")

        # Prepare output audio in the expected format
        audio_output = None
        if processed_audio is not None:
            audio_output = {
                'data': processed_audio,
                'sample_rate': sample_rate
            }

        return {"image": None, "json": None, "audio": audio_output}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'
        input_value06_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input06Value'

        pos = dpg.get_item_pos(tag_node_name)
        
        bass_gain = dpg_get_value(input_value02_tag)
        mid_bass_gain = dpg_get_value(input_value03_tag)
        mid_gain = dpg_get_value(input_value04_tag)
        mid_treble_gain = dpg_get_value(input_value05_tag)
        treble_gain = dpg_get_value(input_value06_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict['bass_gain'] = bass_gain
        setting_dict['mid_bass_gain'] = mid_bass_gain
        setting_dict['mid_gain'] = mid_gain
        setting_dict['mid_treble_gain'] = mid_treble_gain
        setting_dict['treble_gain'] = treble_gain

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input05Value'
        input_value06_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input06Value'

        bass_gain = setting_dict.get('bass_gain', 0.0)
        mid_bass_gain = setting_dict.get('mid_bass_gain', 0.0)
        mid_gain = setting_dict.get('mid_gain', 0.0)
        mid_treble_gain = setting_dict.get('mid_treble_gain', 0.0)
        treble_gain = setting_dict.get('treble_gain', 0.0)
        
        dpg_set_value(input_value02_tag, bass_gain)
        dpg_set_value(input_value03_tag, mid_bass_gain)
        dpg_set_value(input_value04_tag, mid_gain)
        dpg_set_value(input_value05_tag, mid_treble_gain)
        dpg_set_value(input_value06_tag, treble_gain)
