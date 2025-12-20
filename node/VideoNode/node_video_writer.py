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
VideoWriter Node - Simplified direct frame writing implementation

This node handles video recording in MP4, AVI, and MKV formats with minimal memory usage.
- Direct frame-by-frame writing (no queues)
- Immediate write operations
- Background finalization to prevent UI freeze
- No audio handling

Supported formats:
- MP4: H.264 codec (mp4v)
- AVI: MJPEG codec (MJPG)
- MKV: FFV1 codec (lossless)
"""

def create_crash_log(operation_name, exception, tag_node_name=None):
    """
    Create a detailed crash log file when an error occurs in video operations.
    
    Args:
        operation_name: Name of the operation that failed
        exception: The exception that was caught
        tag_node_name: Optional node tag for identification
        
    Returns:
        Path to the created log file
    """
    try:
        logs_dir = get_logs_directory()
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        node_suffix = f"_{tag_node_name.replace(':', '_')}" if tag_node_name else ""
        log_filename = f"crash_{operation_name}{node_suffix}_{timestamp}.log"
        log_path = logs_dir / log_filename
        
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

    # Dictionaries for managing video writing
    _video_writer_dict = {}      # {node: cv2.VideoWriter}
    _release_threads_dict = {}   # {node: threading.Thread}
    _frame_count_dict = {}       # {node: int}
    _writer_width_dict = {}      # {node: int} for frame resizing
    _writer_height_dict = {}     # {node: int} for frame resizing
    
    _start_label = 'Start'
    _stop_label = 'Stop'
    _finalizing_label = 'Finalizing...'
    
    # Configuration
    _RELEASE_TIMEOUT_SECONDS = 60.0
    
    # Hot-path optimization: Throttle texture uploads during recording
    # Display 1 frame every N frames to reduce CPU load
    _PREVIEW_THROTTLE = 10  # Update display every 10 frames during recording
    
    # FPS mapping for combo box values
    _FPS_MAP = {
        '24 FPS': 24,
        '25 FPS': 25,
        '30 FPS': 30,
        '60 FPS': 60
    }

    _prev_frame_flag = False
    _frame_counter_dict = {}  # {node: int} for throttling texture uploads

    def __init__(self):
        pass

    def _release_video_writer_async(self, tag_node_name, video_writer, tag_node_button_value_name):
        """
        Release video writer in background thread to prevent UI freeze.
        
        The cv2.VideoWriter.release() method can take 10-30+ seconds for large videos,
        especially with MJPEG (AVI) and FFV1 (MKV) codecs. Running this in a background
        thread prevents the UI from freezing.
        
        Args:
            tag_node_name: Node identifier
            video_writer: cv2.VideoWriter instance to release
            tag_node_button_value_name: Button tag to update when done
        """
        try:
            logger.info(f"[VideoWriter] Starting background finalization for {tag_node_name}")
            
            frame_count = self._frame_count_dict.get(tag_node_name, 0)
            
            # Release the video writer (can take 10-30+ seconds)
            video_writer.release()
            
            logger.info(f"[VideoWriter] Finalization completed for {tag_node_name}: {frame_count} frames written")
            
            # Update button label back to Start (thread-safe with DearPyGui)
            try:
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
            except (SystemError, RuntimeError) as gui_error:
                logger.debug(f"[VideoWriter] Could not update button (GUI may be shutting down): {gui_error}")
            
        except Exception as e:
            logger.error(f"[VideoWriter] Error during background finalization: {e}")
            logger.error(traceback.format_exc())
            create_crash_log("finalization", e, tag_node_name)
            
            try:
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
            except (SystemError, RuntimeError):
                pass
                
        finally:
            # Clean up tracking dictionaries
            self._release_threads_dict.pop(tag_node_name, None)
            self._frame_count_dict.pop(tag_node_name, None)
            self._frame_counter_dict.pop(tag_node_name, None)
            self._writer_width_dict.pop(tag_node_name, None)
            self._writer_height_dict.pop(tag_node_name, None)

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """
        REAL-TIME HOT PATH - Performance-critical method called every frame.
        
        DESIGN CONSTRAINTS:
        - Must never block the UI thread for long periods
        - Must avoid expensive operations when possible
        - Direct frame writing approach (no queues/threads)
        - Frame writing happens immediately in this method
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'

        # Parse connection to find source node
        connection_info_src = ''
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = connection_info_src.split(':')[:2]
            connection_info_src = ':'.join(connection_info_src)

        # Get display dimensions from config
        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']

        frame = node_image_dict.get(connection_info_src, None)
        
        # Check if currently recording (fast dict lookup)
        is_recording = tag_node_name in self._video_writer_dict

        if frame is not None:
            # ============ FRAME WRITING (DIRECT) ============
            # Write frame directly to video file if recording
            if is_recording:
                try:
                    video_writer = self._video_writer_dict[tag_node_name]
                    writer_width = self._writer_width_dict[tag_node_name]
                    writer_height = self._writer_height_dict[tag_node_name]
                    
                    # Resize and write frame directly
                    # Using INTER_LINEAR for better performance
                    writer_frame = cv2.resize(
                        frame,
                        (writer_width, writer_height),
                        interpolation=cv2.INTER_LINEAR
                    )
                    video_writer.write(writer_frame)
                    
                    # Update frame count
                    self._frame_count_dict[tag_node_name] = self._frame_count_dict.get(tag_node_name, 0) + 1
                    
                except Exception as e:
                    logger.error(f"[VideoWriter] Error writing frame for {tag_node_name}: {e}")
                    logger.error(traceback.format_exc())

            # ============ DISPLAY UPDATE (THROTTLED DURING RECORDING) ============
            # HOT PATH OPTIMIZATION: Reduce texture upload frequency during recording
            # Texture upload (convert_cv_to_dpg + dpg_set_value) is expensive:
            # - cv2.resize consumes CPU
            # - GPU texture upload has driver overhead
            # - At 30fps, this is 30 uploads/sec which causes lag
            
            should_update_display = True
            
            if is_recording:
                # Throttle: Only update display every Nth frame during recording
                # This reduces CPU/GPU load significantly while still showing progress
                frame_counter = self._frame_counter_dict.get(tag_node_name, 0)
                self._frame_counter_dict[tag_node_name] = frame_counter + 1
                
                # Only update display every _PREVIEW_THROTTLE frames (e.g., 1 in 10)
                should_update_display = (frame_counter % self._PREVIEW_THROTTLE == 0)
            
            if should_update_display:
                # CRITICAL: Upstream nodes must provide UI-sized frames
                # We accept frames "as is" without resizing
                # This assumes frame is already at (small_window_w, small_window_h)
                # If frame size doesn't match, resize as fallback (log warning)
                if frame.shape[1] != small_window_w or frame.shape[0] != small_window_h:
                    # Fallback resize - this should ideally not happen
                    # Upstream nodes should provide correctly-sized frames
                    display_frame = cv2.resize(frame, (small_window_w, small_window_h))
                else:
                    display_frame = frame
                
                # Convert and upload texture to GPU
                # NOTE: convert_cv_to_dpg performs a resize internally, but since
                # display_frame is already at the target size (small_window_w, small_window_h),
                # this resize becomes a no-op that just ensures format consistency
                texture = self.convert_cv_to_dpg(
                    display_frame,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(input_value01_tag, texture)
            
        else:
            # ============ NO FRAME - AUTO-STOP LOGIC ============
            # Use cached recording state
            if is_recording and self._prev_frame_flag:
                # Stream ended while recording - auto-stop
                self._recording_button(None, None, tag_node_name)

                # Clear display with black frame
                black_image = np.zeros((small_window_h, small_window_w, 3))
                texture = self.convert_cv_to_dpg(
                    black_image,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(input_value01_tag, texture)

        # Track frame presence for auto-stop detection
        self._prev_frame_flag = (frame is not None)

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        """
        Clean up resources when node is closed.
        
        Ensures video writers are released properly.
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        logger.info(f"[VideoWriter] Closing node {tag_node_name}")
        
        # Wait for finalization thread if active
        if tag_node_name in self._release_threads_dict:
            release_thread = self._release_threads_dict[tag_node_name]
            if release_thread.is_alive():
                logger.info(f"[VideoWriter] Waiting for background finalization to complete for {tag_node_name}")
                release_thread.join(timeout=self._RELEASE_TIMEOUT_SECONDS)
                if release_thread.is_alive():
                    logger.warning(f"[VideoWriter] Background finalization still running after {self._RELEASE_TIMEOUT_SECONDS}s for {tag_node_name}")
            self._release_threads_dict.pop(tag_node_name, None)
        
        # Release video writer if still active (fallback)
        if tag_node_name in self._video_writer_dict:
            try:
                self._video_writer_dict[tag_node_name].release()
                logger.info(f"[VideoWriter] Released video writer in close() for {tag_node_name}")
            except Exception as e:
                logger.error(f"[VideoWriter] Error releasing video writer in close(): {e}")
            self._video_writer_dict.pop(tag_node_name, None)
        
        # Clear tracking dictionaries
        self._frame_count_dict.pop(tag_node_name, None)
        self._frame_counter_dict.pop(tag_node_name, None)
        self._writer_width_dict.pop(tag_node_name, None)
        self._writer_height_dict.pop(tag_node_name, None)

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
        """
        Handle start/stop recording button clicks.
        
        Start: Creates video writer and background write thread
        Stop: Signals thread to stop and begins background finalization
        """
        tag_node_name = user_data
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)

        if label == self._start_label:
            # ============ START RECORDING ============
            try:
                datetime_now = datetime.datetime.now()
                startup_time_text = datetime_now.strftime('%Y%m%d_%H%M%S')
                
                # Get selected resolution
                resolution_tag = tag_node_name + ':Resolution'
                resolution_text = dpg_get_value(resolution_tag)
                
                # Parse resolution from text (e.g., "HD (1280x720)" -> 1280x720)
                resolution_map = {
                    'HD (1280x720)': (1280, 720),
                    '640x480': (640, 480),
                    '320x240': (320, 240)
                }
                writer_width, writer_height = resolution_map.get(resolution_text, (1280, 720))
                
                # Get selected FPS
                fps_tag = tag_node_name + ':FPS'
                fps_text = dpg_get_value(fps_tag)
                
                # Parse FPS from text using class constant
                writer_fps = self._FPS_MAP.get(fps_text, 24)
                
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

                # Create video writer
                video_writer = cv2.VideoWriter(
                    file_path,
                    cv2.VideoWriter_fourcc(*config['codec']),
                    writer_fps,
                    (writer_width, writer_height),
                )
                
                if not video_writer.isOpened():
                    logger.error(f"[VideoWriter] Failed to open video writer for {file_path}")
                    return
                
                # Store writer and dimensions for direct frame writing
                self._video_writer_dict[tag_node_name] = video_writer
                self._writer_width_dict[tag_node_name] = writer_width
                self._writer_height_dict[tag_node_name] = writer_height
                
                # Initialize counters
                self._frame_count_dict[tag_node_name] = 0
                self._frame_counter_dict[tag_node_name] = 0  # For throttling display updates
                
                # Disable resolution, format, and FPS dropdowns during recording
                dpg.configure_item(resolution_tag, enabled=False)
                dpg.configure_item(format_tag, enabled=False)
                dpg.configure_item(fps_tag, enabled=False)
                
                logger.info(f"[VideoWriter] Started direct frame-by-frame recording {video_format} at {resolution_text} {fps_text}: {file_path}")
                dpg.set_item_label(tag_node_button_value_name, self._stop_label)
                
            except Exception as e:
                logger.error(f"[VideoWriter] Error starting recording: {e}")
                logger.error(traceback.format_exc())
                create_crash_log("recording_start", e, tag_node_name)
                
                # Clean up on error
                self._video_writer_dict.pop(tag_node_name, None)
                self._writer_width_dict.pop(tag_node_name, None)
                self._writer_height_dict.pop(tag_node_name, None)
                self._frame_counter_dict.pop(tag_node_name, None)
            
        elif label == self._stop_label:
            # ============ STOP RECORDING ============
            try:
                # Re-enable resolution, format, and FPS dropdowns
                resolution_tag = tag_node_name + ':Resolution'
                format_tag = tag_node_name + ':Format'
                fps_tag = tag_node_name + ':FPS'
                dpg.configure_item(resolution_tag, enabled=True)
                dpg.configure_item(format_tag, enabled=True)
                dpg.configure_item(fps_tag, enabled=True)
                
                # Clean up dimensions and throttle counter
                self._writer_width_dict.pop(tag_node_name, None)
                self._writer_height_dict.pop(tag_node_name, None)
                self._frame_counter_dict.pop(tag_node_name, None)
                
                # Start background finalization
                if tag_node_name in self._video_writer_dict:
                    video_writer = self._video_writer_dict.pop(tag_node_name)
                    
                    # Update button to show we're finalizing
                    dpg.set_item_label(tag_node_button_value_name, self._finalizing_label)
                    
                    # Start background thread to release the video writer
                    release_thread = threading.Thread(
                        target=self._release_video_writer_async,
                        args=(tag_node_name, video_writer, tag_node_button_value_name),
                        daemon=False,  # Important: don't exit until finalization is done
                        name=f"VideoWriter-Release-{tag_node_name}"
                    )
                    self._release_threads_dict[tag_node_name] = release_thread
                    release_thread.start()
                    
                    frame_count = self._frame_count_dict.get(tag_node_name, 0)
                    logger.info(f"[VideoWriter] Stopped recording, finalizing in background ({frame_count} frames written)")
                    
            except Exception as e:
                logger.error(f"[VideoWriter] Error stopping recording: {e}")
                logger.error(traceback.format_exc())
                create_crash_log("recording_stop", e, tag_node_name)
