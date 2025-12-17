#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import threading
from threading import Lock

import cv2
import numpy as np
import dearpygui.dearpygui as dpg
import yt_dlp

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


def get_light_live_stream_url(url):
    """Retrieves live stream URL in low resolution (max 360p)."""
    # Validate input URL
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty or whitespace")
    
    ydl_opts = {
        "quiet": True,
        "format": "best[height<=400]",  # Limit to 360p to reduce load
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get("url", None)
            if not video_url:
                raise ValueError("No video URL found in the response")
            return cv2.VideoCapture(video_url)
    except yt_dlp.utils.DownloadError as e:
        raise ValueError(f"Failed to download video info: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error while processing URL: {e}")


class FactoryNode:
    node_label = 'YouTube'
    node_tag = 'YouTube'

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
        node = YoutubeNode()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'

        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02Value'

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
        use_pref_counter = node._opencv_setting_dict.get('use_pref_counter', False)

        
        
        
        
        black_image = np.zeros((node.small_window_h, node.small_window_w, 3), dtype=np.uint8)
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

        # Create yellow theme for buttons with white text
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

		
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
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input02_value_name,
                    label="Interval(ms)",
                    width=node.small_window_w - 110,
                    default_value=33,
                    min_value=node._min_val,
                    max_value=node._max_val,
                    callback=None,
                )

            # Bouton Start avec thème jaune
            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn_start = dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node.small_window_w,
                    callback=node.button,
                    user_data=node.tag_node_input01_value_name,
                )
                dpg.bind_item_theme(btn_start, yellow_button_theme)

            # Outputs audio, json, float, elapsed time as disabled yellow buttons
            def add_yellow_disabled_button(label, tag):
                btnn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node.small_window_w,
                    enabled=False,

                    
                )
                dpg.bind_item_theme(btnn, yellow_button_theme)
                return btnn

            #with dpg.node_attribute(tag=node.tag_node_output02_name, attribute_type=dpg.mvNode_Attr_Output):
            #    add_yellow_disabled_button("Elapsed time (ms)", node.tag_node_output02_value_name)

            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)

        return node



class YoutubeNode(Node):
    _ver = '0.0.1'

    node_label = 'YouTube'
    node_tag = 'YouTube'

    _opencv_setting_dict = None
    _start_label = 'Start'
    _stop_label = 'Stop'
    _loading_label = 'Loading...'

    _min_val = 1
    _max_val = 200

    _youtube_capture = {}
    _prev_read_time = {}


    def __init__(self):
        super().__init__()
        self._min_val = 1
        self._max_val = 1000
        self._start_label = "Start"
        self.node_tag = "YouTube"
        self.node_label = "YouTube"
        self.cap = None
        self.small_window_w = 240
        self.small_window_h = 135
        
        # State management
        self._is_playing = {}
        self._last_frame_time = {}
        self._last_frame = {}
        
    def convert_cv_to_dpg(self, cv_img, w, h):
        """Converts OpenCV image to DearPyGui format"""
        if cv_img is None:
            # Return black image if no image available
            return (np.zeros(w * h * 3, dtype=np.float32)).tobytes()
        
        # Resize image to desired size
        resized = cv2.resize(cv_img, (w, h))
        
        # Convert from BGR (OpenCV) to RGB
        rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize values from 0-255 to 0-1 (float32)
        normalized = rgb_image.astype(np.float32) / 255.0
        
        # Flatten array and return as bytes
        return normalized.flatten().tobytes()
    

    def button(self, sender, data, user_data):
        # user_data is the tag for the URL input field
        # We need to construct the button tag from the node name
        tag_parts = user_data.split(':')
        tag_node_name = ':'.join(tag_parts[:2])  # Get node_id:node_tag
        node_id = tag_parts[0]
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'
        
        # Get current button label to determine state
        label = dpg.get_item_label(tag_node_button_value_name)
        
        # Get the YouTube URL
        youtube_url = dpg.get_value(user_data)
        
        if label == self._start_label:
            # Starting the stream
            if not youtube_url or not isinstance(youtube_url, str) or not youtube_url.strip():
                print("Error: Please enter a valid YouTube URL")
                return
            
            try:
                # Initialize the video capture
                self.cap = get_light_live_stream_url(youtube_url)
                print(f"YouTube stream started: {youtube_url}")
                # Change button label to Stop
                dpg.set_item_label(tag_node_button_value_name, self._stop_label)
                # Set playing state
                self._is_playing[node_id] = True
            except ValueError as e:
                print(f"Error: {e}")
                self.cap = None
                self._is_playing[node_id] = False
            except Exception as e:
                print(f"Unexpected error: {e}")
                self.cap = None
                self._is_playing[node_id] = False
        
        elif label == self._stop_label:
            # Stopping the stream
            if self.cap is not None:
                self.cap.release()
                self.cap = None
                print("YouTube stream stopped")
            
            # Change button label back to Start
            dpg.set_item_label(tag_node_button_value_name, self._start_label)
            # Clear playing state
            self._is_playing[node_id] = False
        
    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        """Updates the video stream image."""
        tag_node_name = f"{node_id}:{self.node_tag}"
        output_value01_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output01Value"
        slider_tag = f"{tag_node_name}:{self.TYPE_INT}:Input02Value"

        current_time = time.time()
        
        # Initialize frame interval from slider
        try:
            frame_interval_ms = dpg_get_value(slider_tag)
            frame_interval = max(1, frame_interval_ms) / 1000.0  # ms -> s
        except:
            frame_interval = 0.033  # default 33 ms

        # Check if playback is active (similar to Video node)
        is_playing = self._is_playing.get(str(node_id), False)
        
        frame = None
        
        # Only read frames if playback is active and capture is initialized
        if self.cap is not None and is_playing:
            # Check if enough time has passed since last frame
            last_time = self._last_frame_time.get(str(node_id), None)
            should_read_frame = (last_time is None) or ((current_time - last_time) >= frame_interval)
            
            if should_read_frame:
                try:
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        # Store frame and update display
                        self._last_frame[str(node_id)] = frame
                        texture = self.convert_cv_to_dpg(frame, self.small_window_w, self.small_window_h)
                        dpg_set_value(output_value01_tag, texture)
                        self._last_frame_time[str(node_id)] = current_time
                    else:
                        # Use last frame if read fails
                        frame = self._last_frame.get(str(node_id), None)
                except Exception as e:
                    print(f"YouTube read error: {e}")
                    frame = self._last_frame.get(str(node_id), None)
            else:
                # Use last frame when not reading
                frame = self._last_frame.get(str(node_id), None)
        else:
            # Use last frame when not playing
            frame = self._last_frame.get(str(node_id), None)

        return {"image": frame, "json": None, "audio": None}
    
    
    def close(self, node_id):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'

        pos = dpg.get_item_pos(tag_node_name)
        youtube_url = dpg_get_value(tag_node_input01_value_name)
        interval_time = dpg_get_value(tag_node_input02_value_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_input01_value_name] = youtube_url
        setting_dict[tag_node_input02_value_name] = interval_time

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'

        youtube_url = setting_dict[tag_node_input01_value_name]
        interval_time = setting_dict[tag_node_input02_value_name]

        dpg_set_value(tag_node_input01_value_name, youtube_url)
        dpg_set_value(tag_node_input02_value_name, interval_time)
