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
    """Retrieves live stream URL in low resolution (max 360p).
    
    Uses format selection that works better with OpenCV's VideoCapture:
    - Prefers non-HLS formats (avoids m3u8 playlists)
    - Falls back to lower quality if needed
    - Tries multiple format strategies
    """
    # Validate input URL
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty or whitespace")
    
    # Strategy 1: Try to get a progressive format (video+audio) that's not HLS
    # Progressive formats work best with OpenCV
    format_strategies = [
        "best[height<=480][protocol^=http][protocol!=m3u8_native]/best[height<=480][protocol^=https][protocol!=m3u8_native]/best[height<=480]",
        "best[height<=360][protocol^=http]/best[height<=360][protocol^=https]/best[height<=360]",
        "worstvideo[height>=240][height<=480]+worstaudio/worst[height>=240][height<=480]",
        "best[height<=480]",  # Final fallback
    ]
    
    last_error = None
    
    for format_spec in format_strategies:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": format_spec,
            # Additional options to help with stream compatibility
            "nocheckcertificate": True,
            "no_check_certificate": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info.get("url", None)
                
                if not video_url:
                    continue
                
                # Skip URLs that contain m3u8 (HLS) as they often don't work well with OpenCV
                if "m3u8" in video_url.lower():
                    # Try to find a better format if this is HLS
                    formats = info.get("formats", [])
                    # Look for non-HLS formats
                    non_hls_formats = [
                        f for f in formats 
                        if f.get("url") and "m3u8" not in f.get("url", "").lower()
                        and f.get("vcodec") != "none"
                        and f.get("height", 0) <= 480
                    ]
                    
                    if non_hls_formats:
                        # Sort by height (prefer lower resolution for performance)
                        non_hls_formats.sort(key=lambda x: x.get("height", 0))
                        video_url = non_hls_formats[0].get("url")
                
                # Try to open with OpenCV
                cap = cv2.VideoCapture(video_url)
                if cap.isOpened():
                    return cap
                else:
                    cap.release()
                    last_error = f"OpenCV failed to open stream with format: {format_spec}"
                    continue
                    
        except yt_dlp.utils.DownloadError as e:
            last_error = f"Failed to download video info: {e}"
            continue
        except Exception as e:
            last_error = f"Unexpected error with format {format_spec}: {e}"
            continue
    
    # If all strategies failed, raise an error
    error_msg = f"Failed to open YouTube stream after trying multiple formats. Last error: {last_error}"
    raise ValueError(error_msg)


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

        # Create blue theme for buttons when stream is active
        with dpg.theme() as blue_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (100, 149, 237, 255))  # Cornflower blue
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (65, 105, 225, 255))  # Royal blue on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (25, 25, 112, 255))  # Midnight blue on press
        
        # Store themes in node for later use
        node.yellow_button_theme = yellow_button_theme
        node.blue_button_theme = blue_button_theme

        
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
        self.yellow_button_theme = None
        self.blue_button_theme = None
        self.is_streaming = False  # Track streaming state
        
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
                # Release any existing capture before creating a new one
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                
                # Initialize the video capture
                print(f"Attempting to open YouTube stream: {youtube_url}")
                self.cap = get_light_live_stream_url(youtube_url)
                
                if self.cap is None or not self.cap.isOpened():
                    print("Error: Failed to open YouTube stream - OpenCV could not initialize the video capture")
                    self.cap = None
                    return
                
                print(f"YouTube stream started: {youtube_url}")
                self.is_streaming = True
                
                # Change button label to Stop
                dpg.set_item_label(tag_node_button_value_name, self._stop_label)
                
                # Change button theme to blue to indicate active stream
                if self.blue_button_theme is not None:
                    dpg.bind_item_theme(tag_node_button_value_name, self.blue_button_theme)
                    
            except ValueError as e:
                print(f"Error: {e}")
                self.cap = None
                self.is_streaming = False
            except Exception as e:
                print(f"Unexpected error: {e}")
                self.cap = None
                self.is_streaming = False
        
        elif label == self._stop_label:
            # Stopping the stream
            if self.cap is not None:
                self.cap.release()
                self.cap = None
                print("YouTube stream stopped")
            
            self.is_streaming = False
            
            # Change button label back to Start
            dpg.set_item_label(tag_node_button_value_name, self._start_label)
            
            # Change button theme back to yellow
            if self.yellow_button_theme is not None:
                dpg.bind_item_theme(tag_node_button_value_name, self.yellow_button_theme)
        

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
      """Updates the video stream image."""
      tag_node_name = f"{node_id}:{self.node_tag}"
      output_value01_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output01Value"

      self.current_time = time.time()

      if not hasattr(self, "_last_frame_time"):
        self._last_frame_time = 0
      
      # Always get the current frame interval from the slider
      try:
          slider_tag = f"{tag_node_name}:{self.TYPE_INT}:Input02Value"
          self._frame_interval = max(1, dpg_get_value(slider_tag)) / 1000  # ms -> s
      except (ValueError, KeyError, AttributeError, TypeError) as e:
          # Default to 33ms if slider value cannot be retrieved
          self._frame_interval = 0.033

      # Only try to read frames if streaming is active
      if self.cap is not None and self.is_streaming and self.current_time - self._last_frame_time >= self._frame_interval:
        try:
            ret, frame = self.cap.read()
        except Exception as e:
            print(f"YouTube node: Video read error: {e}")
            ret, frame = False, None

        if ret and frame is not None:
            # Update the frame and texture
            self._last_frame = frame
            texture = self.convert_cv_to_dpg(frame, self.small_window_w, self.small_window_h)
            dpg_set_value(output_value01_tag, texture)
            self._last_frame_time = self.current_time
        elif self.cap.isOpened():
            # Stream is open but no frame received - this can be normal for live streams
            # Don't spam console, just skip this frame
            pass

      return {"image": getattr(self, "_last_frame", None), "json": None, "audio": None}
    
    
    def close(self, node_id):
        """Clean up resources when node is closed."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_streaming = False

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
