#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import datetime

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

"""
VideoWriter Node - Simplified for maximum performance

Direct frame-by-frame writing with minimal overhead.
Supports MP4, AVI, and MKV formats.
"""


class FactoryNode:
    node_label = 'VideoWriter'
    node_tag = 'VideoWriter'
    
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
        node = VideoWriterNode()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'

        node.tag_node_button_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Button'
        node.tag_node_button_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ButtonValue'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']

        black_image = np.zeros((small_window_w, small_window_h, 3))
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
                tag=node.tag_node_input01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_image(node.tag_node_input01_value_name)

            # Resolution selector
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_name + ':Resolution',
                    items=['HD (1280x720)', '640x480', '320x240'],
                    default_value='HD (1280x720)',
                    width=small_window_w,
                    label='',
                )
            
            # Format selector
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_name + ':Format',
                    items=['MP4', 'AVI', 'MKV'],
                    default_value='MP4',
                    width=small_window_w,
                    label='',
                )
            
            # FPS selector
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_name + ':FPS',
                    items=['24 FPS', '25 FPS', '30 FPS', '60 FPS'],
                    default_value='24 FPS',
                    width=small_window_w,
                    label='',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=small_window_w,
                    callback=node._recording_button,
                    user_data=node.tag_node_name,
                )

        return node


class VideoWriterNode(Node):
    _ver = '0.0.5'

    node_label = 'VideoWriter'
    node_tag = 'VideoWriter'

    _opencv_setting_dict = None

    # Simple state tracking
    _video_writer_dict = {}  # {node: cv2.VideoWriter}
    _writer_settings_dict = {}  # {node: (width, height)}
    _release_threads_dict = {}  # Kept for backward compatibility (empty)
    
    _start_label = 'Start'
    _stop_label = 'Stop'
    
    # FPS mapping
    _FPS_MAP = {
        '24 FPS': 24,
        '25 FPS': 25,
        '30 FPS': 30,
        '60 FPS': 60
    }

    _prev_frame_flag = False

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
        """Hot path - minimal overhead."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'

        # Get source node
        connection_info_src = ''
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = connection_info_src.split(':')[:2]
            connection_info_src = ':'.join(connection_info_src)

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']

        frame = node_image_dict.get(connection_info_src, None)

        if frame is not None:
            # Write frame if recording
            if tag_node_name in self._video_writer_dict:
                writer = self._video_writer_dict[tag_node_name]
                writer_width, writer_height = self._writer_settings_dict[tag_node_name]
                
                #writer_frame = cv2.resize(frame, (writer_width, writer_height))
                #writer.write(writer_frame)

            # Update display
            texture = self.convert_cv_to_dpg(frame, small_window_w, small_window_h)
            dpg_set_value(input_value01_tag, texture)
        else:
            # Auto-stop if stream ended
            if tag_node_name in self._video_writer_dict and self._prev_frame_flag:
                self._recording_button(None, None, tag_node_name)
                
                black_image = np.zeros((small_window_h, small_window_w, 3))
                texture = self.convert_cv_to_dpg(black_image, small_window_w, small_window_h)
                dpg_set_value(input_value01_tag, texture)

        self._prev_frame_flag = (frame is not None)
        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        """Clean up when node is closed."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        if tag_node_name in self._video_writer_dict:
            self._video_writer_dict[tag_node_name].release()
            self._video_writer_dict.pop(tag_node_name, None)
            self._writer_settings_dict.pop(tag_node_name, None)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        
        # Save settings
        resolution_tag = tag_node_name + ':Resolution'
        format_tag = tag_node_name + ':Format'
        fps_tag = tag_node_name + ':FPS'
        
        if dpg.does_item_exist(resolution_tag):
            setting_dict['resolution'] = dpg_get_value(resolution_tag)
        if dpg.does_item_exist(format_tag):
            setting_dict['format'] = dpg_get_value(format_tag)
        if dpg.does_item_exist(fps_tag):
            setting_dict['fps'] = dpg_get_value(fps_tag)

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Restore settings
        resolution_tag = tag_node_name + ':Resolution'
        format_tag = tag_node_name + ':Format'
        fps_tag = tag_node_name + ':FPS'
        
        if 'resolution' in setting_dict and dpg.does_item_exist(resolution_tag):
            dpg_set_value(resolution_tag, setting_dict['resolution'])
        if 'format' in setting_dict and dpg.does_item_exist(format_tag):
            dpg_set_value(format_tag, setting_dict['format'])
        if 'fps' in setting_dict and dpg.does_item_exist(fps_tag):
            dpg_set_value(fps_tag, setting_dict['fps'])

    def _recording_button(self, sender, data, user_data):
        """Handle start/stop recording."""
        tag_node_name = user_data
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)

        if label == self._start_label:
            # Start recording
            datetime_now = datetime.datetime.now()
            startup_time_text = datetime_now.strftime('%Y%m%d_%H%M%S')
            
            # Get settings
            resolution_tag = tag_node_name + ':Resolution'
            resolution_text = dpg_get_value(resolution_tag)
            
            resolution_map = {
                'HD (1280x720)': (1280, 720),
                '640x480': (640, 480),
                '320x240': (320, 240)
            }
            writer_width, writer_height = resolution_map.get(resolution_text, (1280, 720))
            
            fps_tag = tag_node_name + ':FPS'
            fps_text = dpg_get_value(fps_tag)
            writer_fps = self._FPS_MAP.get(fps_text, 24)
            
            video_writer_directory = self._opencv_setting_dict['video_writer_directory']
            os.makedirs(video_writer_directory, exist_ok=True)

            # Get format
            format_tag = tag_node_name + ':Format'
            video_format = dpg_get_value(format_tag)
            
            format_config = {
                'AVI': {'ext': '.avi', 'codec': 'MJPG'},
                'MKV': {'ext': '.mkv', 'codec': 'FFV1'},
                'MP4': {'ext': '.mp4', 'codec': 'mp4v'}
            }
            
            config = format_config.get(video_format, format_config['MP4'])
            file_path = os.path.join(video_writer_directory, f'{startup_time_text}{config["ext"]}')

            # Create writer
            if tag_node_name not in self._video_writer_dict:
                video_writer = cv2.VideoWriter(
                    file_path,
                    cv2.VideoWriter_fourcc(*config['codec']),
                    writer_fps,
                    (writer_width, writer_height),
                )
                
                if video_writer.isOpened():
                    self._video_writer_dict[tag_node_name] = video_writer
                    self._writer_settings_dict[tag_node_name] = (writer_width, writer_height)
                    
                    # Disable UI during recording
                    dpg.configure_item(resolution_tag, enabled=False)
                    dpg.configure_item(format_tag, enabled=False)
                    dpg.configure_item(fps_tag, enabled=False)
                    
                    logger.info(f"[VideoWriter] Started {video_format} at {resolution_text} {fps_text}: {file_path}")
                    dpg.set_item_label(tag_node_button_value_name, self._stop_label)
                else:
                    logger.error(f"[VideoWriter] Failed to open: {file_path}")
            
        elif label == self._stop_label:
            # Stop recording
            if tag_node_name in self._video_writer_dict:
                self._video_writer_dict[tag_node_name].release()
                self._video_writer_dict.pop(tag_node_name, None)
                self._writer_settings_dict.pop(tag_node_name, None)
                
                # Re-enable UI
                resolution_tag = tag_node_name + ':Resolution'
                format_tag = tag_node_name + ':Format'
                fps_tag = tag_node_name + ':FPS'
                dpg.configure_item(resolution_tag, enabled=True)
                dpg.configure_item(format_tag, enabled=True)
                dpg.configure_item(fps_tag, enabled=True)
                
                logger.info(f"[VideoWriter] Stopped recording")
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
