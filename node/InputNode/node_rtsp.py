#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import subprocess
import threading
import shutil
import queue
import multiprocessing as mp

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
from node.VideoNode.sync import FramePacket

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


def _get_ffmpeg_exe():
    """Return the path to a usable ffmpeg executable."""
    try:
        if imageio_ffmpeg is not None:
            return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return shutil.which("ffmpeg")


class FactoryNode:
    node_label = 'RTSP'
    node_tag = 'RTSP'
    

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


        node = RtspNode()
        
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'
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



        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['input_window_width']
        node.small_window_h = node._opencv_setting_dict['input_window_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']


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
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # Create default (inactive) theme for audio button
        with dpg.theme() as default_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (66, 66, 70, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (80, 80, 85, 255))

        node.yellow_button_theme = yellow_button_theme
        node.default_button_theme = default_button_theme


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
                dpg.add_input_text(
                    tag=node.tag_node_input01_value_name,
                    label='URL',
                    width=node.small_window_w - 30,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node.small_window_w,
                    callback=node._button,
                    user_data=node.tag_node_name,
                )


            def add_yellow_disabled_button(label, tag):
                btn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node._small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                return btn

            # Audio toggle button (clickable)
            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                btn_audio = dpg.add_button(
                    label="Audio",
                    tag=node.tag_node_output_audio_value_name,
                    width=node._small_window_w,
                    callback=node._toggle_audio,
                )
                dpg.bind_item_theme(btn_audio, default_button_theme)

            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)
        
        return node






def receive_image_process(rtsp_url, image_queue, request):
    while request.value != 0:
        try:
            rtsp_capture = cv2.VideoCapture(rtsp_url)
            while request.value != 0:
                try:
                    ret, frame = rtsp_capture.read()
                    if ret:
                        if image_queue.qsize() == 0:
                            image_queue.put(frame)
                        time.sleep(0.001)
                    else:
                        time.sleep(1)
                        rtsp_capture.release()
                        rtsp_capture = cv2.VideoCapture(rtsp_url)
                except Exception as e:
                    print(f'[RTSP] Read error for {rtsp_url}: {e}')
                    time.sleep(1)
                    try:
                        rtsp_capture.release()
                    except Exception:
                        pass
                    break
        except Exception as e:
            print(f'[RTSP] Connection error for {rtsp_url}: {e}')
            time.sleep(1)


class RtspNode(Node):
    _ver = '0.0.1'

    node_label = 'RTSP'
    node_tag = 'RTSP'

    _opencv_setting_dict = None
    _start_label = 'Start'
    _stop_label = 'Stop'

    _rtsp_capture = {}

    _image_queue = {}
    _request = {}
    _process = {}

    def __init__(self):
        super().__init__()  # Call parent constructor
        self._min_val = 1
        self._max_val = 1000

        self._small_window_w = 240
        self._small_window_h = 135

        self._start_label = "Start"
        self._stop_label  = "Stop"
        
        self.node_tag = "RTSP"
        self.node_label = "RTSP"

        self.yellow_button_theme = None
        self.default_button_theme = None
        self.is_streaming = False
        self._frame_count = 0

        # Audio state
        self._audio_enabled = False
        self._audio_process = None
        self._audio_thread = None
        self._audio_queue = queue.Queue(maxsize=10)
        self._audio_sr = 16000
        self._audio_chunk_duration = 5.0  # seconds per chunk
        self._audio_url = None
        self._audio_stop_event = threading.Event()
        self._audio_chunk_counter = 0

    def _toggle_audio(self, sender, data, user_data=None):
        """Toggle audio extraction on/off."""
        self._audio_enabled = not self._audio_enabled
        if self._audio_enabled:
            dpg.bind_item_theme(sender, self.yellow_button_theme)
            # Start audio capture if currently streaming
            if self.is_streaming and self._audio_url:
                self._start_audio_capture()
        else:
            dpg.bind_item_theme(sender, self.default_button_theme)
            self._stop_audio_capture()

    def _start_audio_capture(self):
        """Start the ffmpeg subprocess to capture audio from the stream."""
        self._stop_audio_capture()

        if not self._audio_url:
            return

        ffmpeg_exe = _get_ffmpeg_exe()
        if ffmpeg_exe is None:
            print("❌ ffmpeg non trouvé pour l'extraction audio")
            return

        self._audio_stop_event.clear()
        self._audio_thread = threading.Thread(
            target=self._audio_reader_loop,
            args=(ffmpeg_exe, self._audio_url),
            daemon=True,
        )
        self._audio_thread.start()

    def _audio_reader_loop(self, ffmpeg_exe, audio_url):
        """Background thread: reads PCM audio from ffmpeg stdout."""
        try:
            cmd = [
                ffmpeg_exe,
                "-rtsp_transport", "tcp",
                "-i", audio_url,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", str(self._audio_sr),
                "-ac", "1",
                "-f", "s16le",
                "-",
            ]
            self._audio_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )

            bytes_per_chunk = int(self._audio_sr * self._audio_chunk_duration) * 2  # 16-bit mono

            while not self._audio_stop_event.is_set():
                raw = self._audio_process.stdout.read(bytes_per_chunk)
                if not raw:
                    break
                audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                chunk_idx = self._audio_chunk_counter
                self._audio_chunk_counter += 1
                audio_dict = {
                    'data': audio_np,
                    'sample_rate': self._audio_sr,
                    'channels': 1,
                    'chunk_index': chunk_idx,
                    'step_duration': self._audio_chunk_duration,
                }
                # Non-blocking put: discard old chunks if queue is full
                try:
                    self._audio_queue.put_nowait(audio_dict)
                except queue.Full:
                    try:
                        self._audio_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._audio_queue.put_nowait(audio_dict)

        except Exception as e:
            if not self._audio_stop_event.is_set():
                print(f"❌ Erreur audio reader RTSP: {e}")
        finally:
            if self._audio_process and self._audio_process.poll() is None:
                self._audio_process.kill()
                self._audio_process = None

    def _stop_audio_capture(self):
        """Stop the audio capture thread and ffmpeg process."""
        self._audio_stop_event.set()
        if self._audio_process and self._audio_process.poll() is None:
            self._audio_process.kill()
            self._audio_process = None
        if self._audio_thread and self._audio_thread.is_alive():
            self._audio_thread.join(timeout=2.0)
        self._audio_thread = None
        # Drain the queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']


        use_mp = self._opencv_setting_dict['use_multiprocessing_rtsp']


        rtsp_url = dpg_get_value(input_value01_tag)


        rtsp_capture = None
        image_queue = None
        if rtsp_url != '':
            if use_mp:
                # multiprocessing
                if rtsp_url in self._process:
                    # Restart subprocess if it has died unexpectedly
                    if not self._process[rtsp_url].is_alive():
                        self._image_queue[rtsp_url] = mp.Queue(maxsize=1)
                        self._request[rtsp_url] = mp.Value('i', 1)
                        self._process[rtsp_url] = mp.Process(
                            target=receive_image_process,
                            args=(rtsp_url, self._image_queue[rtsp_url],
                                  self._request[rtsp_url]),
                        )
                        self._process[rtsp_url].start()
                if rtsp_url in self._image_queue:
                    image_queue = self._image_queue[rtsp_url]
            else:
                # single-threaded
                if rtsp_url in self._rtsp_capture:
                    rtsp_capture = self._rtsp_capture[rtsp_url]


        if rtsp_url != '' and use_pref_counter:
            start_time = time.monotonic()


        frame = None
        if use_mp:
            # multiprocessing
            if image_queue is not None:
                num = image_queue.qsize()
                if num > 0:
                    frame = image_queue.get()
                    self._frame_count += 1
        else:
            # single-threaded
            if rtsp_capture is not None:
                try:
                    ret, frame = rtsp_capture.read()
                except Exception:
                    ret = False
                if not ret:
                    return {"image": None, "json": None, "audio": None}
                self._frame_count += 1


        if rtsp_url != '' and use_pref_counter:
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

        # Get audio chunk if audio is enabled
        audio_chunk_data = None
        if self._audio_enabled:
            try:
                audio_chunk_data = self._audio_queue.get_nowait()
            except queue.Empty:
                pass

        # Calculate FPS-based timestamp for this frame (approximate 30fps)
        frame_timestamp = None
        if self._frame_count > 0:
            frame_timestamp = self._frame_count / 30.0
        pts_ms = frame_timestamp * 1000.0 if frame_timestamp is not None else None

        # Inject pts_ms into audio dict for A/V sync alignment
        if audio_chunk_data is not None and pts_ms is not None:
            audio_chunk_data = dict(audio_chunk_data)
            audio_chunk_data["pts_ms"] = pts_ms

        # Build FramePacket JSON metadata (same as VideoNode and YouTubeNode)
        json_output = None
        if frame is not None and pts_ms is not None:
            audio_chunk_index = 0
            if isinstance(audio_chunk_data, dict):
                audio_chunk_index = audio_chunk_data.get("chunk_index", 0)
            now = time.monotonic()
            fp = FramePacket(
                frame_index=self._frame_count,
                pts_ms=pts_ms,
                audio_chunk_index=audio_chunk_index,
                image=frame,
                audio_data=audio_chunk_data,
                pipeline_entry_ts=now,
                pipeline_exit_ts=now,
            )
            json_output = fp.to_metadata()

        return {
            "image": frame,
            "json": json_output,
            "audio": audio_chunk_data,
            "timestamp": frame_timestamp,
        }

    def close(self, node_id):
        # Stop audio capture
        self._stop_audio_capture()
        # multiprocessing
        use_mp = self._opencv_setting_dict['use_multiprocessing_rtsp']
        if use_mp:
            # multiprocessing
            for rtsp_url in self._process.keys():
                self._request[rtsp_url].value = 0
                if self._process[rtsp_url].is_alive():
                    self._process[rtsp_url].terminate()
                    self._process[rtsp_url].join(timeout=2.0)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'

        pos = dpg.get_item_pos(tag_node_name)
        rtsp_url = dpg_get_value(tag_node_input01_value_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_input01_value_name] = rtsp_url

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'

        rtsp_url = setting_dict[tag_node_input01_value_name]

        dpg_set_value(tag_node_input01_value_name, rtsp_url)

    def _button(self, sender, data, user_data):
        tag_node_name = user_data
        input_value01_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)

        # RTSP URL
        rtsp_url = dpg_get_value(input_value01_tag)

        # multiprocessing
        use_mp = self._opencv_setting_dict['use_multiprocessing_rtsp']

        if label == self._start_label:
            if rtsp_url != '':
                if use_mp:
                    # multiprocessing
                    if not (rtsp_url in self._process):
                        self._image_queue[rtsp_url] = mp.Queue(maxsize=1)
                        self._request[rtsp_url] = mp.Value('i', 1)
                        self._process[rtsp_url] = mp.Process(
                            target=receive_image_process,
                            args=(rtsp_url, self._image_queue[rtsp_url],
                                  self._request[rtsp_url]),
                        )
                        self._process[rtsp_url].start()
                else:
                    # single-threaded
                    if not (rtsp_url in self._rtsp_capture):
                        rtsp_capture = cv2.VideoCapture(rtsp_url)
                        self._rtsp_capture[rtsp_url] = rtsp_capture

            self.is_streaming = True
            self._frame_count = 0
            self._audio_chunk_counter = 0

            # Use the same URL for audio extraction
            self._audio_url = rtsp_url
            if self._audio_enabled and self._audio_url:
                self._start_audio_capture()

            dpg.set_item_label(tag_node_button_value_name, self._stop_label)
        elif label == self._stop_label:
            if rtsp_url != '':
                if use_mp:
                    # multiprocessing
                    if rtsp_url in self._request:
                        self._request[rtsp_url].value = 0
                        if self._process[rtsp_url].is_alive():
                            self._process[rtsp_url].terminate()
                        self._image_queue.pop(rtsp_url)
                        self._request.pop(rtsp_url)
                        self._process.pop(rtsp_url)
                else:
                    # single-threaded
                    if rtsp_url in self._rtsp_capture:
                        self._rtsp_capture[rtsp_url].release()
                        self._rtsp_capture.pop(rtsp_url)

            self.is_streaming = False
            self._stop_audio_capture()
            self._audio_url = None
            dpg.set_item_label(tag_node_button_value_name, self._start_label)
