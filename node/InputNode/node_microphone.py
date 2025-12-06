#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import numpy as np
import dearpygui.dearpygui as dpg

# Try to import sounddevice, but handle gracefully if not available
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError) as e:
    SOUNDDEVICE_AVAILABLE = False
    print(f"⚠️ sounddevice not available: {e}")
    print("   Microphone node will be available but non-functional.")
    print("   Install PortAudio library to enable microphone support.")

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


class FactoryNode:
    node_label = 'Microphone'
    node_tag = 'Microphone'
    
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
        node = MicrophoneNode()
        node._opencv_setting_dict = opencv_setting_dict
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        
        # Device selection input
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input01Value'
        
        # Sample rate input
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02Value'
        
        # Chunk duration input
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        
        # Audio output
        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'
        
        # JSON output
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'
        
        # Button control
        node.tag_node_button_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Button'
        node.tag_node_button_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ButtonValue'
        
        # Volume meters (using consistent naming pattern)
        node.tag_node_rms_meter_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':RMSMeter'
        node.tag_node_peak_meter_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':PeakMeter'

        node.opencv_setting_dict = opencv_setting_dict
        node.small_window_w = opencv_setting_dict['input_window_width']
        node.small_window_h = opencv_setting_dict['input_window_height']
        
        node._small_window_w = node._opencv_setting_dict['input_window_width']
        node._small_window_h = node._opencv_setting_dict['input_window_height']
        
        use_pref_counter = opencv_setting_dict['use_pref_counter']

        # Get available audio input devices
        input_devices = []
        input_device_indices = []
        
        if SOUNDDEVICE_AVAILABLE:
            try:
                devices = sd.query_devices()
                for idx, device in enumerate(devices):
                    if device['max_input_channels'] > 0:
                        input_devices.append(f"{idx}: {device['name']}")
                        input_device_indices.append(idx)
            except Exception as e:
                print(f"⚠️ Error querying audio devices: {e}")
        
        # If no input devices found, add a default entry
        if not input_devices:
            if SOUNDDEVICE_AVAILABLE:
                input_devices = ['No microphone detected']
            else:
                input_devices = ['sounddevice not available']
            input_device_indices = [-1]
        
        # Store device indices in node
        node.input_device_indices = input_device_indices

        # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))          # Yellow background
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255)) # Yellow on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))   # Yellow on press

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Device selection
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    input_devices,
                    width=node.small_window_w - 20,
                    label="Device",
                    tag=node.tag_node_input01_value_name,
                    default_value=input_devices[0] if input_devices else '',
                )

            # Sample rate selection
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    ['8000', '16000', '22050', '44100', '48000'],
                    width=node.small_window_w - 20,
                    label="Sample Rate",
                    tag=node.tag_node_input02_value_name,
                    default_value='44100',
                )

            # Chunk duration (in seconds)
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    label="Chunk (s)",
                    width=node.small_window_w - 20,
                    tag=node.tag_node_input03_value_name,
                    default_value=1.0,
                    min_value=0.1,
                    max_value=5.0,
                    format="%.1f",
                )

            # Start/Stop button
            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn_start = dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node._small_window_w,
                    callback=node._button_callback,
                    user_data=node.tag_node_name,
                )
                dpg.bind_item_theme(btn_start, yellow_button_theme)

            # Volume meters (RMS and Peak)
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':VolumeMeter',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("Volume Levels:")
                dpg.add_progress_bar(
                    label="RMS",
                    tag=node.tag_node_rms_meter_name,
                    default_value=0.0,
                    overlay="RMS: 0.00",
                    width=node._small_window_w - 20,
                )
                dpg.add_progress_bar(
                    label="Peak",
                    tag=node.tag_node_peak_meter_name,
                    default_value=0.0,
                    overlay="Peak: 0.00",
                    width=node._small_window_w - 20,
                )

            # Audio output
            with dpg.node_attribute(
                    tag=node.tag_node_output_audio_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="Audio",
                    tag=node.tag_node_output_audio_value_name,
                    width=node._small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                
            # JSON output
            with dpg.node_attribute(
                    tag=node.tag_node_output_json_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="JSON",
                    tag=node.tag_node_output_json_value_name,
                    width=node._small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
        
        return node


class MicrophoneNode(Node):
    _ver = '0.0.1'

    node_label = 'Microphone'
    node_tag = 'Microphone'

    def __init__(self):
        super().__init__()
        # Window dimensions
        self._small_window_w = 240
        self._small_window_h = 135
        self.small_window_w = 240
        self.small_window_h = 135
        self._start_label = "Start"
        # Override parent class defaults
        self.node_tag = "Microphone"
        self.node_label = "Microphone"
        self.input_device_indices = []
        self._is_recording = False

    def _button_callback(self, sender, app_data, user_data):
        """Toggle recording on/off"""
        self._is_recording = not self._is_recording
        
        if self._is_recording:
            dpg.set_item_label(sender, "Stop")
            print(f"🎤 Microphone recording started for node {user_data}")
        else:
            dpg.set_item_label(sender, "Start")
            print(f"🛑 Microphone recording stopped for node {user_data}")
    
    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_INT + ':Input01Value'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        rms_meter_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':RMSMeter'
        peak_meter_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':PeakMeter'

        # Get settings
        device_str = dpg_get_value(input_value01_tag)
        sample_rate_str = dpg_get_value(input_value02_tag)
        chunk_duration = dpg_get_value(input_value03_tag)

        audio_data = None
        sample_rate = 44100  # Default
        
        if not SOUNDDEVICE_AVAILABLE:
            return {"image": None, "json": None, "audio": None}
        
        if not self._is_recording or not device_str or device_str in ['No microphone detected', 'sounddevice not available']:
            # Reset meters when not recording
            try:
                dpg_set_value(rms_meter_tag, 0.0)
                dpg.configure_item(rms_meter_tag, overlay="RMS: 0.00")
                dpg_set_value(peak_meter_tag, 0.0)
                dpg.configure_item(peak_meter_tag, overlay="Peak: 0.00")
            except (SystemError, ValueError, Exception):
                # DPG may not be initialized or widget may not exist yet
                pass
            return {"image": None, "json": None, "audio": None}
        
        try:
            # Parse device index from string "idx: name"
            device_idx = int(device_str.split(':')[0])
            sample_rate = int(sample_rate_str)
            
            # Calculate number of samples for the chunk duration
            num_samples = int(sample_rate * chunk_duration)
            
            # Record audio chunk
            recording = sd.rec(
                frames=num_samples,
                samplerate=sample_rate,
                channels=1,
                dtype='float32',
                device=device_idx,
            )
            sd.wait()  # Wait until recording is finished
            
            # Convert to mono if needed and flatten
            audio_data = recording.flatten()
            
            # Calculate volume levels for meters
            # RMS (Root Mean Square) - average volume level
            rms_level = np.sqrt(np.mean(audio_data ** 2))
            
            # Peak level - maximum absolute amplitude
            peak_level = np.max(np.abs(audio_data))
            
            # Normalize to 0.0-1.0 range (assuming audio is already normalized to -1.0 to 1.0)
            rms_normalized = min(rms_level, 1.0)
            peak_normalized = min(peak_level, 1.0)
            
            # Update volume meters
            try:
                dpg_set_value(rms_meter_tag, rms_normalized)
                dpg.configure_item(rms_meter_tag, overlay=f"RMS: {rms_normalized:.2f}")
                dpg_set_value(peak_meter_tag, peak_normalized)
                dpg.configure_item(peak_meter_tag, overlay=f"Peak: {peak_normalized:.2f}")
            except (SystemError, ValueError, Exception) as e:
                # Log error but don't fail the audio capture
                print(f"⚠️ Error updating volume meters: {e}")
            
            # Create audio dict in the expected format
            audio_output = {
                'data': audio_data,
                'sample_rate': sample_rate
            }
            
        except Exception as e:
            print(f"⚠️ Error recording from microphone: {e}")
            return {"image": None, "json": None, "audio": None}

        return {"image": None, "json": None, "audio": audio_output}

    def close(self, node_id):
        """Clean up when node is deleted"""
        self._is_recording = False

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
