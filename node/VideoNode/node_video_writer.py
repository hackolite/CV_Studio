#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import datetime
import traceback

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.utils.logging import get_logger, get_logs_directory
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    # Fallback for get_logs_directory if src.utils.logging import fails
    # This ensures crash logging works even if the main logging system is unavailable
    # Duplicates logic from src/utils/logging.py line 14-30 intentionally for robustness
    def get_logs_directory():
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / 'logs'
        logs_dir.mkdir(exist_ok=True)
        return logs_dir

# Removed audio/video merging dependencies - video-only mode
# No longer using ffmpeg, soundfile, or background worker

def slow_motion_interpolation(prev_frame, next_frame, alpha):
    """ Generates smooth intermediate frame between 2 images """
    return cv2.addWeighted(prev_frame, 1 - alpha, next_frame, alpha, 0)


def create_crash_log(operation_name, exception, tag_node_name=None):
    """
    Create a detailed crash log file when an error occurs in video operations.
    
    This function is called when critical operations fail (stream setup, recording, merging).
    It creates a timestamped log file in the logs directory with:
    - Full stack trace
    - Exception details
    - Node identification
    - Timestamp
    
    Args:
        operation_name: Name of the operation that failed (e.g., "recording_start", "audio_merge")
        exception: The exception that was caught
        tag_node_name: Optional node tag for identification
        
    Returns:
        Path to the created log file
    """
    try:
        logs_dir = get_logs_directory()
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create descriptive filename
        node_suffix = f"_{tag_node_name.replace(':', '_')}" if tag_node_name else ""
        log_filename = f"crash_{operation_name}{node_suffix}_{timestamp}.log"
        log_path = logs_dir / log_filename
        
        # Gather crash information
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write(f"CV Studio VideoWriter Crash Log\n")
            f.write("="*70 + "\n")
            f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Operation: {operation_name}\n")
            if tag_node_name:
                f.write(f"Node: {tag_node_name}\n")
            f.write(f"Exception Type: {type(exception).__name__}\n")
            f.write(f"Exception Message: {str(exception)}\n")
            f.write("="*70 + "\n\n")
            
            f.write("Full Stack Trace:\n")
            f.write("-"*70 + "\n")
            f.write(traceback.format_exc())
            f.write("\n")
            
            f.write("="*70 + "\n")
            f.write("End of crash log\n")
            f.write("="*70 + "\n")
        
        logger.error(f"[VideoWriter] Crash log created: {log_path}")
        return log_path
        
    except Exception as log_error:
        # If we can't even create the log file, log to console
        logger.error(f"[VideoWriter] Failed to create crash log: {log_error}")
        logger.error(f"[VideoWriter] Original error: {exception}")
        logger.error(traceback.format_exc())
        return None


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
        node.tag_node_progress_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Progress'


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

            # Add format selector
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_name + ':Format',
                    items=['MP4', 'AVI', 'MKV'],
                    default_value='MP4',
                    width=small_window_w,
                    label='Format',
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
    _ver = '0.0.3'

    node_label = 'VideoWriter'
    node_tag = 'VideoWriter'

    _opencv_setting_dict = None

    _video_writer_dict = {}  # Store active cv2.VideoWriter instances: {node: writer}
    
    _start_label = 'Start'
    _stop_label = 'Stop'

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
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        connection_info_src = ''
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = connection_info_src.split(':')[:2]
            connection_info_src = ':'.join(connection_info_src)

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        writer_width = self._opencv_setting_dict['video_writer_width']
        writer_height = self._opencv_setting_dict['video_writer_height']

        frame = node_image_dict.get(connection_info_src, None)

        if frame is not None:
            # Shallow copy - frame data will be resized immediately
            rec_frame = frame.copy()

            # Direct write to VideoWriter if recording is active
            if tag_node_name in self._video_writer_dict:
                writer_frame = cv2.resize(rec_frame,
                                          (writer_width, writer_height),
                                          interpolation=cv2.INTER_CUBIC)
                self._video_writer_dict[tag_node_name].write(writer_frame)

                # Add red recording indicator
                rec_frame = cv2.circle(rec_frame, (10, 10),
                                       50, (0, 0, 255),
                                       thickness=-1)

            texture = self.convert_cv_to_dpg(
                rec_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(input_value01_tag, texture)
        else:
            label = dpg.get_item_label(tag_node_button_value_name)
            if label == self._stop_label and self._prev_frame_flag:

                self._recording_button(None, None, tag_node_name)

                black_image = np.zeros((small_window_w, small_window_h, 3))

                texture = self.convert_cv_to_dpg(
                    black_image,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(input_value01_tag, texture)

        if frame is not None:
            self._prev_frame_flag = True
        else:
            self._prev_frame_flag = False

        return {"image":frame, "json":None, "audio":None}



    def close(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Release video writer if active
        if tag_node_name in self._video_writer_dict:
            self._video_writer_dict[tag_node_name].release()
            self._video_writer_dict.pop(tag_node_name)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass


    
    def _recording_button(self, sender, data, user_data):
        tag_node_name = user_data
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)

        if label == self._start_label:
            # Start recording
            datetime_now = datetime.datetime.now()
            startup_time_text = datetime_now.strftime('%Y%m%d_%H%M%S')
            
            writer_width = self._opencv_setting_dict['video_writer_width']
            writer_height = self._opencv_setting_dict['video_writer_height']
            writer_fps = self._opencv_setting_dict['video_writer_fps']
            video_writer_directory = self._opencv_setting_dict['video_writer_directory']

            os.makedirs(video_writer_directory, exist_ok=True)

            # Get selected format
            format_tag = tag_node_name + ':Format'
            video_format = dpg_get_value(format_tag)
            
            # Determine file extension and codec
            format_config = {
                'AVI': {'ext': '.avi', 'codec': 'MJPG'},
                'MKV': {'ext': '.mkv', 'codec': 'FFV1'},
                'MP4': {'ext': '.mp4', 'codec': 'mp4v'}
            }
            
            config = format_config.get(video_format, format_config['MP4'])
            file_path = os.path.join(video_writer_directory, f'{startup_time_text}{config["ext"]}')

            # Create video writer - direct frame-by-frame writing
            self._video_writer_dict[tag_node_name] = cv2.VideoWriter(
                file_path,
                cv2.VideoWriter_fourcc(*config['codec']),
                writer_fps,
                (writer_width, writer_height),
            )
            
            logger.info(f"[VideoWriter] Started recording {video_format}: {file_path}")
            dpg.set_item_label(tag_node_button_value_name, self._stop_label)
            
        elif label == self._stop_label:
            # Stop recording
            if tag_node_name in self._video_writer_dict:
                self._video_writer_dict[tag_node_name].release()
                self._video_writer_dict.pop(tag_node_name)
                logger.info(f"[VideoWriter] Stopped recording")
            
            dpg.set_item_label(tag_node_button_value_name, self._start_label)

