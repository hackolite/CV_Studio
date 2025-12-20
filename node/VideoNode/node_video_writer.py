#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import datetime
import traceback
import threading

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
    def get_logs_directory():
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / 'logs'
        logs_dir.mkdir(exist_ok=True)
        return logs_dir

"""
VideoWriter Node - Simplified for performance

This node handles video recording in MP4, AVI, and MKV formats.
- Direct frame-by-frame writing
- Minimal dictionary tracking
- Simplified error handling
- Background finalization to prevent UI freeze

Supported formats:
- MP4: H.264 codec (mp4v)
- AVI: MJPEG codec (MJPG)
- MKV: FFV1 codec (FFV1)
"""

def log_error(operation_name, exception, tag_node_name=None):
    """
    Simplified error logging - just log to logger without creating separate files.
    
    Args:
        operation_name: Name of the operation that failed
        exception: The exception that was caught
        tag_node_name: Optional node tag for identification
    """
    node_info = f" [{tag_node_name}]" if tag_node_name else ""
    logger.error(f"[VideoWriter{node_info}] Error in {operation_name}: {exception}")


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

            # Add resolution selector
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
            
            # Add format selector
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
            
            # Add FPS selector
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
    _ver = '0.0.4'

    node_label = 'VideoWriter'
    node_tag = 'VideoWriter'

    _opencv_setting_dict = None

    # Single dictionary for all recording state (simplified from 6 separate dicts)
    # Structure: {node_tag: {'writer': VideoWriter, 'width': int, 'height': int, 
    #                        'frame_count': int, 'display_counter': int}}
    _recording_state = {}
    _release_threads = {}  # {node: threading.Thread}
    
    # Backward compatibility - tests may reference these
    @property 
    def _video_writer_dict(self):
        """Backward compatibility property"""
        return {k: v['writer'] for k, v in self._recording_state.items()}
    
    @property
    def _release_threads_dict(self):
        """Backward compatibility property"""
        return self._release_threads
    
    _start_label = 'Start'
    _stop_label = 'Stop'
    _finalizing_label = 'Finalizing...'
    
    # Configuration
    _RELEASE_TIMEOUT_SECONDS = 60.0
    _PREVIEW_THROTTLE = 10  # Update display every 10 frames during recording
    
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

    def _release_video_writer_async(self, tag_node_name, video_writer, frame_count, tag_node_button_value_name):
        """
        Release video writer in background thread.
        
        Args:
            tag_node_name: Node identifier
            video_writer: cv2.VideoWriter instance to release
            frame_count: Number of frames written
            tag_node_button_value_name: Button tag to update when done
        """
        try:
            logger.info(f"[VideoWriter] Finalizing {tag_node_name}: {frame_count} frames")
            video_writer.release()
            logger.info(f"[VideoWriter] Finalization completed for {tag_node_name}")
            
            # Update button label
            try:
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
            except (SystemError, RuntimeError):
                pass  # GUI may be shutting down
            
        except Exception as e:
            logger.error(f"[VideoWriter] Error during finalization: {e}")
            log_error("finalization", e, tag_node_name)
            try:
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
            except (SystemError, RuntimeError):
                pass
                
        finally:
            # Clean up
            self._release_threads.pop(tag_node_name, None)
            self._recording_state.pop(tag_node_name, None)

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """
        Hot path - called every frame. Optimized for minimal overhead.
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'

        # Parse connection
        connection_info_src = ''
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = connection_info_src.split(':')[:2]
            connection_info_src = ':'.join(connection_info_src)

        # Get display dimensions
        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']

        frame = node_image_dict.get(connection_info_src, None)
        
        # Fast check: is recording active?
        state = self._recording_state.get(tag_node_name)
        is_recording = state is not None

        if frame is not None:
            # Write frame if recording
            if is_recording:
                try:
                    writer = state['writer']
                    # Resize and write
                    writer_frame = cv2.resize(
                        frame,
                        (state['width'], state['height']),
                        interpolation=cv2.INTER_LINEAR
                    )
                    writer.write(writer_frame)
                    state['frame_count'] += 1
                except Exception as e:
                    logger.error(f"[VideoWriter] Write error: {e}")

            # Update display (throttled during recording)
            should_update = True
            if is_recording:
                state['display_counter'] += 1
                should_update = (state['display_counter'] % self._PREVIEW_THROTTLE == 0)
            
            if should_update:
                # Resize if needed
                if frame.shape[1] != small_window_w or frame.shape[0] != small_window_h:
                    display_frame = cv2.resize(frame, (small_window_w, small_window_h))
                else:
                    display_frame = frame
                
                texture = self.convert_cv_to_dpg(display_frame, small_window_w, small_window_h)
                dpg_set_value(input_value01_tag, texture)
            
        else:
            # Auto-stop if stream ended
            if is_recording and self._prev_frame_flag:
                self._recording_button(None, None, tag_node_name)
                
                black_image = np.zeros((small_window_h, small_window_w, 3))
                texture = self.convert_cv_to_dpg(black_image, small_window_w, small_window_h)
                dpg_set_value(input_value01_tag, texture)

        self._prev_frame_flag = (frame is not None)
        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        """Clean up resources when node is closed."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Wait for finalization thread
        if tag_node_name in self._release_threads:
            thread = self._release_threads[tag_node_name]
            if thread.is_alive():
                logger.info(f"[VideoWriter] Waiting for finalization: {tag_node_name}")
                thread.join(timeout=self._RELEASE_TIMEOUT_SECONDS)
            self._release_threads.pop(tag_node_name, None)
        
        # Release writer if still active
        state = self._recording_state.get(tag_node_name)
        if state:
            try:
                state['writer'].release()
                logger.info(f"[VideoWriter] Released writer in close(): {tag_node_name}")
            except Exception as e:
                logger.error(f"[VideoWriter] Error releasing writer: {e}")
            self._recording_state.pop(tag_node_name, None)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        
        # Save resolution, format, and FPS settings
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
        
        # Restore resolution, format, and FPS settings
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
        """Handle start/stop recording button clicks."""
        tag_node_name = user_data
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)

        if label == self._start_label:
            # Start recording
            try:
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
                video_writer = cv2.VideoWriter(
                    file_path,
                    cv2.VideoWriter_fourcc(*config['codec']),
                    writer_fps,
                    (writer_width, writer_height),
                )
                
                if not video_writer.isOpened():
                    logger.error(f"[VideoWriter] Failed to open: {file_path}")
                    return
                
                # Store state in single dict
                self._recording_state[tag_node_name] = {
                    'writer': video_writer,
                    'width': writer_width,
                    'height': writer_height,
                    'frame_count': 0,
                    'display_counter': 0
                }
                
                # Disable UI during recording
                dpg.configure_item(resolution_tag, enabled=False)
                dpg.configure_item(format_tag, enabled=False)
                dpg.configure_item(fps_tag, enabled=False)
                
                logger.info(f"[VideoWriter] Started {video_format} at {resolution_text} {fps_text}: {file_path}")
                dpg.set_item_label(tag_node_button_value_name, self._stop_label)
                
            except Exception as e:
                logger.error(f"[VideoWriter] Start error: {e}")
                log_error("recording_start", e, tag_node_name)
                self._recording_state.pop(tag_node_name, None)
            
        elif label == self._stop_label:
            # Stop recording
            try:
                # Re-enable UI
                resolution_tag = tag_node_name + ':Resolution'
                format_tag = tag_node_name + ':Format'
                fps_tag = tag_node_name + ':FPS'
                dpg.configure_item(resolution_tag, enabled=True)
                dpg.configure_item(format_tag, enabled=True)
                dpg.configure_item(fps_tag, enabled=True)
                
                # Start background finalization
                state = self._recording_state.pop(tag_node_name, None)
                if state:
                    dpg.set_item_label(tag_node_button_value_name, self._finalizing_label)
                    
                    # Background release
                    thread = threading.Thread(
                        target=self._release_video_writer_async,
                        args=(tag_node_name, state['writer'], state['frame_count'], tag_node_button_value_name),
                        daemon=False,
                        name=f"VideoWriter-Release-{tag_node_name}"
                    )
                    self._release_threads[tag_node_name] = thread
                    thread.start()
                    
                    logger.info(f"[VideoWriter] Stopped, finalizing ({state['frame_count']} frames)")
                    
            except Exception as e:
                logger.error(f"[VideoWriter] Stop error: {e}")
                log_error("recording_stop", e, tag_node_name)
