#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import numpy as np
import dearpygui.dearpygui as dpg
import queue
import threading

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
        
        # Audio indicator (blinking light)
        node.tag_node_indicator_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Indicator'

        # Queue info
        node.tag_node_queue_info_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":QueueInfo"
        )
        node.tag_node_queue_info_value_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":QueueInfoValue"
        )

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
                    default_value=3.0,
                    min_value=0.1,
                    max_value=10.0,
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

            # Audio indicator (blinking light)
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':AudioIndicator',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    default_value="Audio: ",
                    tag=node.tag_node_indicator_name,
                    color=(128, 128, 128, 255),  # Gray by default
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

            # Queue size information label
            with dpg.node_attribute(
                tag=node.tag_node_queue_info_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_queue_info_value_name,
                    default_value="Queue: Image=0/0 Audio=0/0",
                )
        
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
        # Non-blocking audio stream
        self._audio_stream = None
        self._audio_buffer = queue.Queue(maxsize=10)  # Limit buffer size to prevent memory issues
        self._current_sample_rate = 44100
        self._lock = threading.Lock()
        # UI update throttling to prevent lag
        self._ui_update_counter = 0
        self._ui_update_interval = 15  # Update UI every N frames
        self._last_indicator_state = None  # Track last state to avoid redundant updates

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream - runs in separate thread"""
        # Note: Avoid heavy operations here as this runs frequently
        # Only log status if there's an actual issue
        if status and status.input_overflow:
            # Only print on actual errors to avoid performance impact
            pass  # Could log to a file if needed
        
        # Copy audio data to buffer (non-blocking)
        try:
            # Make a copy to avoid issues with the buffer being reused
            audio_copy = indata.copy()
            self._audio_buffer.put_nowait(audio_copy)
        except queue.Full:
            # Buffer is full, discard oldest data by clearing and adding new
            try:
                self._audio_buffer.get_nowait()  # Remove oldest
                self._audio_buffer.put_nowait(audio_copy)
            except queue.Empty:
                pass
    
    def _start_stream(self, device_idx, sample_rate, chunk_duration):
        """Start the non-blocking audio stream"""
        with self._lock:
            # Stop existing stream if any
            self._stop_stream()
            
            try:
                # Calculate blocksize for the chunk duration
                blocksize = int(sample_rate * chunk_duration)
                
                # Create and start the input stream
                self._audio_stream = sd.InputStream(
                    device=device_idx,
                    channels=1,
                    samplerate=sample_rate,
                    blocksize=blocksize,
                    dtype='float32',
                    callback=self._audio_callback,
                )
                self._current_sample_rate = sample_rate
                self._audio_stream.start()
                print(f"🎤 Audio stream started (device: {device_idx}, sample_rate: {sample_rate}, blocksize: {blocksize})")
            except Exception as e:
                print(f"⚠️ Error starting audio stream: {e}")
                self._audio_stream = None
    
    def _stop_stream(self):
        """Stop the audio stream and clear the buffer"""
        if self._audio_stream is not None:
            try:
                self._audio_stream.stop()
                self._audio_stream.close()
                print("🛑 Audio stream stopped")
            except Exception as e:
                print(f"⚠️ Error stopping audio stream: {e}")
            finally:
                self._audio_stream = None
        
        # Clear the buffer
        while not self._audio_buffer.empty():
            try:
                self._audio_buffer.get_nowait()
            except queue.Empty:
                break
    
    def _update_indicator_throttled(self, indicator_tag, state):
        """Update the visual indicator with throttling to prevent lag
        
        Args:
            indicator_tag: Tag of the indicator widget
            state: 'active' for green recording state, 'inactive' for gray idle state
        """
        # Only update UI every N frames to prevent lag
        self._ui_update_counter += 1
        
        # Determine if we should update
        should_update = False
        
        # Update if state has changed (immediate feedback)
        if self._last_indicator_state != state:
            should_update = True
            self._ui_update_counter = 0  # Reset counter on state change
        # Update if we've reached the interval (periodic refresh)
        elif self._ui_update_counter >= self._ui_update_interval:
            should_update = True
            self._ui_update_counter = 0  # Reset counter after periodic update
        
        # Perform the UI update if needed
        if should_update:
            try:
                if state == 'active':
                    dpg.set_value(indicator_tag, "Audio: ●")
                    dpg.configure_item(indicator_tag, color=(0, 255, 0, 255))
                else:  # inactive
                    dpg.set_value(indicator_tag, "Audio: ")
                    dpg.configure_item(indicator_tag, color=(128, 128, 128, 255))
                self._last_indicator_state = state
            except (SystemError, ValueError, Exception):
                # DPG may not be initialized or widget may not exist yet
                pass
    
    def _button_callback(self, sender, app_data, user_data):
        """Toggle recording on/off"""
        self._is_recording = not self._is_recording
        
        if self._is_recording:
            dpg.set_item_label(sender, "Stop")
            print(f"🎤 Microphone recording started for node {user_data}")
        else:
            dpg.set_item_label(sender, "Start")
            # Stop the stream when recording is stopped
            self._stop_stream()
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
        indicator_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Indicator'

        # Get settings
        device_str = dpg_get_value(input_value01_tag)
        sample_rate_str = dpg_get_value(input_value02_tag)
        chunk_duration = dpg_get_value(input_value03_tag)

        audio_data = None
        sample_rate = 44100  # Default
        
        if not SOUNDDEVICE_AVAILABLE:
            return {"image": None, "json": None, "audio": None}
        
        if not self._is_recording or not device_str or device_str in ['No microphone detected', 'sounddevice not available']:
            # Reset indicator when not recording (throttled)
            self._update_indicator_throttled(indicator_tag, 'inactive')
            return {"image": None, "json": None, "audio": None}
        
        try:
            # Parse device index from string "idx: name"
            device_idx = int(device_str.split(':')[0])
            sample_rate = int(sample_rate_str)
            
            # Start stream if not already running or settings changed
            with self._lock:
                stream_needs_restart = (
                    self._audio_stream is None or 
                    not self._audio_stream.active or
                    self._current_sample_rate != sample_rate
                )
            
            if stream_needs_restart:
                self._start_stream(device_idx, sample_rate, chunk_duration)
            
            # Try to get audio data from buffer (non-blocking)
            try:
                audio_data = self._audio_buffer.get_nowait()
                # Flatten to ensure it's 1D
                audio_data = audio_data.flatten()
                
                # Update indicator to show recording is active (throttled to prevent lag)
                self._update_indicator_throttled(indicator_tag, 'active')
                
                # Create audio dict in the expected format
                audio_output = {
                    'data': audio_data,
                    'sample_rate': sample_rate
                }
                
                # Update queue info before returning
                self.update_queue_info_display(tag_node_name, node_image_dict, node_audio_dict)
                
                return {"image": None, "json": None, "audio": audio_output}
                
            except queue.Empty:
                # No audio data available yet, return None
                # This is normal during startup or if processing is faster than recording
                # Still update queue info
                self.update_queue_info_display(tag_node_name, node_image_dict, node_audio_dict)
                return {"image": None, "json": None, "audio": None}
            
        except Exception as e:
            print(f"⚠️ Error in microphone update: {e}")
            # Update queue info even on error
            self.update_queue_info_display(tag_node_name, node_image_dict, node_audio_dict)
            return {"image": None, "json": None, "audio": None}



    def close(self, node_id):
        """Clean up when node is deleted"""
        self._is_recording = False
        self._stop_stream()

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
