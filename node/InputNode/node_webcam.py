#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import queue
import threading
import numpy as np
import dearpygui.dearpygui as dpg

# Try to import sounddevice, but handle gracefully if not available
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError) as e:
    SOUNDDEVICE_AVAILABLE = False
    print(f"⚠️ sounddevice not available: {e}")
    print("   Webcam audio capture will be unavailable.")

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


class FactoryNode:
    node_label = 'Webcam'
    node_tag = 'Webcam'
    

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

        node = WebcamNode()
        node._opencv_setting_dict = opencv_setting_dict
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input01Value'
        
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'


        node.tag_node_button_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Button'
        node.tag_node_button_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ButtonValue'


        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        # Audio device selector tag
        node.tag_node_input_audio_device_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':InputAudioDevice'
        node.tag_node_input_audio_device_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':InputAudioDeviceValue'

        #node._opencv_setting_dict = opencv_setting_dict
        node.opencv_setting_dict = opencv_setting_dict
        node.small_window_w = opencv_setting_dict['input_window_width']
        node.small_window_h = opencv_setting_dict['input_window_height']
        
        node._small_window_w = node._opencv_setting_dict['input_window_width']
        node._small_window_h = node._opencv_setting_dict['input_window_height']
        
        device_no_list = opencv_setting_dict['device_no_list']
        use_pref_counter = opencv_setting_dict['use_pref_counter']

        # Get available audio input devices
        audio_input_devices = ['(No audio)']
        if SOUNDDEVICE_AVAILABLE:
            try:
                devices = sd.query_devices()
                for i, d in enumerate(devices):
                    if d['max_input_channels'] > 0:
                        audio_input_devices.append(f"{i}: {d['name']}")
            except Exception as e:
                print(f"⚠️ Error querying audio devices: {e}")
                audio_input_devices = ['sounddevice not available']

        black_image = np.zeros((node.small_window_w, node.small_window_h, 3))
        
        
        black_texture = node.convert_cv_to_dpg(
            black_image,
            node.small_window_w,
            node.small_window_h,
        )


        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                node.small_window_w,
                node.small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )


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
 
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    device_no_list,
                    width=node.small_window_w - 100,
                    label="Video Device",
                    tag=node.tag_node_input01_value_name,
                )

            # Audio device selector
            with dpg.node_attribute(
                    tag=node.tag_node_input_audio_device_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    audio_input_devices,
                    width=node.small_window_w - 100,
                    label="Audio Device",
                    tag=node.tag_node_input_audio_device_value_name,
                    default_value=audio_input_devices[0],
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)


            # Bouton Start avec thème jaune
            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn_start = dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node._small_window_w,
                    callback=node._button,
                    user_data=node.tag_node_name,
                )
                
                dpg.bind_item_theme(btn_start, yellow_button_theme)

            # Outputs audio, json, float, elapsed time as disabled yellow buttons
            def add_yellow_disabled_button(label, tag):
                btn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node._small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                return btn



            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)
        
        return node
    





class WebcamNode(Node):
    _ver = '0.0.1'

    node_label = 'Webcam'
    node_tag = 'Webcam'

    # Default audio settings
    _SAMPLE_RATE = 16000
    _CHUNK_DURATION = 1.0  # seconds

    def __init__(self):
        super().__init__()

        self._small_window_w = 240
        self._small_window_h = 135
        self.small_window_w = 240
        self.small_window_h = 135
        self._start_label = "Start"
        self.node_tag = "Webcam"
        self.node_label = "Webcam"
        self._start_label = "Webcam"

        # Audio stream state
        self._audio_stream = None
        self._audio_buffer = queue.Queue(maxsize=10)
        self._current_audio_device = None
        self._lock = threading.Lock()

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream - runs in a separate thread."""
        audio_copy = indata.copy()
        try:
            self._audio_buffer.put_nowait(audio_copy)
        except queue.Full:
            # Drop oldest, add newest
            try:
                self._audio_buffer.get_nowait()
                self._audio_buffer.put_nowait(audio_copy)
            except queue.Empty:
                pass

    def _start_audio_stream(self, device_idx, sample_rate=16000):
        """Start the audio input stream."""
        self._stop_audio_stream()
        try:
            chunk_samples = int(sample_rate * self._CHUNK_DURATION)
            self._audio_stream = sd.InputStream(
                device=device_idx,
                channels=1,
                samplerate=sample_rate,
                blocksize=chunk_samples,
                dtype='float32',
                callback=self._audio_callback,
            )
            self._audio_stream.start()
            print(f"🎤 Webcam audio stream started (device: {device_idx}, sample_rate: {sample_rate})")
        except Exception as e:
            print(f"⚠️ Error starting webcam audio stream: {e}")
            self._audio_stream = None

    def _stop_audio_stream(self):
        """Stop the audio input stream and clear the buffer."""
        if self._audio_stream is not None:
            try:
                self._audio_stream.stop()
                self._audio_stream.close()
                print("🛑 Webcam audio stream stopped")
            except Exception as e:
                print(f"⚠️ Error stopping webcam audio stream: {e}")
            finally:
                self._audio_stream = None
        while not self._audio_buffer.empty():
            try:
                self._audio_buffer.get_nowait()
            except queue.Empty:
                break

    def _button(self, sender, app_data, user_data):
        print(f"Button clicked for {user_data}")
    
    
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
        input_audio_device_tag = tag_node_name + ':' + self.TYPE_TEXT + ':InputAudioDeviceValue'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'

        device_no_list = self.opencv_setting_dict['device_no_list']
        camera_capture_list = self.opencv_setting_dict['camera_capture_list']
        small_window_w = self.opencv_setting_dict['input_window_width']
        small_window_h = self.opencv_setting_dict['input_window_height']

        camera_no = dpg_get_value(self.tag_node_input01_value_name)
        camera_capture = None
        
        if camera_no != '':
            camera_no = int(camera_no)
            camera_index = device_no_list.index(camera_no)
            camera_capture = camera_capture_list[camera_index]

        frame = None
        if camera_capture is not None:
            ret, frame = camera_capture.read()

        if frame is not None:
            texture = self.convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        # --- Audio capture ---
        audio_output = None
        json_output = None

        if SOUNDDEVICE_AVAILABLE:
            audio_device_str = dpg_get_value(input_audio_device_tag)
            if audio_device_str and audio_device_str not in ('(No audio)', 'sounddevice not available', ''):
                try:
                    audio_device_idx = int(audio_device_str.split(':')[0])
                except (ValueError, IndexError):
                    audio_device_idx = None

                if audio_device_idx is not None:
                    # Start or restart stream if device changed
                    with self._lock:
                        stream_needs_restart = (
                            self._audio_stream is None or
                            not self._audio_stream.active or
                            self._current_audio_device != audio_device_idx
                        )
                    if stream_needs_restart:
                        self._current_audio_device = audio_device_idx
                        self._start_audio_stream(audio_device_idx, self._SAMPLE_RATE)

                    # Get audio data (non-blocking)
                    try:
                        raw_audio = self._audio_buffer.get_nowait()
                        audio_data = raw_audio.flatten()
                        chunk_timestamp = time.time()
                        audio_output = {
                            'data': audio_data,
                            'sample_rate': self._SAMPLE_RATE,
                            'timestamp': chunk_timestamp,
                            'channels': 1,
                            'output_mode': 'Full Signal',
                        }
                        json_output = {
                            'timestamp': chunk_timestamp,
                            'sample_rate': self._SAMPLE_RATE,
                            'channels': 1,
                            'chunk_duration': self._CHUNK_DURATION,
                            'samples': len(audio_data),
                            'audio_device': audio_device_str,
                        }
                    except queue.Empty:
                        pass  # No new audio frame ready yet
            else:
                # No audio device selected — stop stream if running
                self._stop_audio_stream()

        return {"image": frame, "json": json_output, "audio": audio_output}

    def close(self, node_id):
        self._stop_audio_stream()

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
