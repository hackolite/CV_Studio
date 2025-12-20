#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import datetime
import traceback
import threading
import queue

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
VideoWriter Node - Optimized threaded implementation

This node handles video recording in MP4, AVI, and MKV formats with minimal UI lag.
- Threaded frame writing using queue.Queue
- Non-blocking frame submission
- Background finalization
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
    _ver = '0.0.4'

    node_label = 'VideoWriter'
    node_tag = 'VideoWriter'

    _opencv_setting_dict = None

    # Dictionaries for managing video writing
    _video_writer_dict = {}      # {node: cv2.VideoWriter}
    _write_queues_dict = {}      # {node: queue.Queue}
    _write_threads_dict = {}     # {node: threading.Thread}
    _release_threads_dict = {}   # {node: threading.Thread}
    _frame_count_dict = {}       # {node: int}
    _dropped_frames_dict = {}    # {node: int}
    
    _start_label = 'Start'
    _stop_label = 'Stop'
    _finalizing_label = 'Finalizing...'
    
    # Configuration
    _QUEUE_MAX_SIZE = 60  # Buffer up to 60 frames (2 seconds at 30fps)
    _RELEASE_TIMEOUT_SECONDS = 60.0
    _WRITE_THREAD_TIMEOUT = 5.0
    
    # Recording indicator configuration (for display frame)
    _INDICATOR_X = 10  # X position in pixels
    _INDICATOR_Y = 10  # Y position in pixels
    _INDICATOR_RADIUS = 5  # Radius in pixels (scaled for small display frame)
    _INDICATOR_COLOR = (0, 0, 255)  # BGR color (red)

    _prev_frame_flag = False

    def __init__(self):
        pass

    def _writer_thread(self, tag_node_name, video_writer, writer_width, writer_height):
        """
        Background thread that processes frames from the queue and writes them to disk.
        
        This thread runs continuously while recording is active, processing frames
        from the queue without blocking the UI thread.
        
        Args:
            tag_node_name: Node identifier
            video_writer: cv2.VideoWriter instance
            writer_width: Target video width
            writer_height: Target video height
        """
        write_queue = self._write_queues_dict.get(tag_node_name)
        if not write_queue:
            logger.error(f"[VideoWriter] No queue found for {tag_node_name}")
            return
        
        logger.info(f"[VideoWriter] Write thread started for {tag_node_name}")
        
        try:
            while True:
                try:
                    # Wait for frame with timeout to allow periodic checks
                    frame = write_queue.get(timeout=1.0)
                    
                    # None is the stop signal
                    if frame is None:
                        logger.info(f"[VideoWriter] Write thread received stop signal for {tag_node_name}")
                        break
                    
                    # Resize and write frame
                    # Using INTER_LINEAR instead of INTER_CUBIC for better performance
                    writer_frame = cv2.resize(
                        frame,
                        (writer_width, writer_height),
                        interpolation=cv2.INTER_LINEAR
                    )
                    video_writer.write(writer_frame)
                    
                    # Update frame count
                    self._frame_count_dict[tag_node_name] = self._frame_count_dict.get(tag_node_name, 0) + 1
                    
                    write_queue.task_done()
                    
                except queue.Empty:
                    # Timeout - check if we should continue
                    if tag_node_name not in self._write_queues_dict:
                        # Queue was removed, stop thread
                        break
                    continue
                    
        except Exception as e:
            logger.error(f"[VideoWriter] Error in write thread for {tag_node_name}: {e}")
            logger.error(traceback.format_exc())
            create_crash_log("write_thread", e, tag_node_name)
        
        logger.info(f"[VideoWriter] Write thread stopped for {tag_node_name}")

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
            dropped_count = self._dropped_frames_dict.get(tag_node_name, 0)
            
            # Release the video writer (can take 10-30+ seconds)
            video_writer.release()
            
            logger.info(f"[VideoWriter] Finalization completed for {tag_node_name}: {frame_count} frames written, {dropped_count} frames dropped")
            
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
            self._dropped_frames_dict.pop(tag_node_name, None)

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

        frame = node_image_dict.get(connection_info_src, None)

        if frame is not None:
            # Submit frame to write queue (non-blocking) - only copy when recording
            if tag_node_name in self._write_queues_dict:
                try:
                    # Use put_nowait to avoid blocking the UI thread
                    # If queue is full, drop the frame rather than waiting
                    # Only copy frame when actually recording to save memory
                    self._write_queues_dict[tag_node_name].put_nowait(frame.copy())
                except queue.Full:
                    # Track dropped frames
                    self._dropped_frames_dict[tag_node_name] = self._dropped_frames_dict.get(tag_node_name, 0) + 1
                    if self._dropped_frames_dict[tag_node_name] % 30 == 1:  # Log every 30 dropped frames
                        logger.warning(f"[VideoWriter] Frame dropped for {tag_node_name} - queue full (total dropped: {self._dropped_frames_dict[tag_node_name]})")

            # Prepare display frame with recording indicator
            # Memory optimization: Resize first, then draw indicator only if needed
            # This avoids making a full-size copy of potentially large frames from ImageConcat
            display_frame = cv2.resize(frame, (small_window_w, small_window_h))
            if tag_node_name in self._video_writer_dict:
                # Draw recording indicator on the already-resized display frame
                # This modifies display_frame in-place but it's already a copy from cv2.resize
                cv2.circle(
                    display_frame,
                    (self._INDICATOR_X, self._INDICATOR_Y),
                    self._INDICATOR_RADIUS,
                    self._INDICATOR_COLOR,
                    thickness=-1
                )

            texture = self.convert_cv_to_dpg(
                display_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(input_value01_tag, texture)
            
        else:
            # No frame received - check if we should auto-stop recording
            label = dpg.get_item_label(tag_node_button_value_name)
            if label == self._stop_label and self._prev_frame_flag:
                # Stream ended while recording - auto-stop
                self._recording_button(None, None, tag_node_name)

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
        
        Ensures all threads are stopped and video writers are released properly.
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        logger.info(f"[VideoWriter] Closing node {tag_node_name}")
        
        # Stop write thread if active
        if tag_node_name in self._write_threads_dict:
            write_thread = self._write_threads_dict[tag_node_name]
            if write_thread.is_alive():
                # Signal thread to stop
                if tag_node_name in self._write_queues_dict:
                    try:
                        self._write_queues_dict[tag_node_name].put(None, timeout=1.0)
                    except queue.Full:
                        pass
                
                # Wait for thread to finish
                write_thread.join(timeout=self._WRITE_THREAD_TIMEOUT)
                if write_thread.is_alive():
                    logger.warning(f"[VideoWriter] Write thread still running after {self._WRITE_THREAD_TIMEOUT}s for {tag_node_name}")
            
            self._write_threads_dict.pop(tag_node_name, None)
        
        # Clean up write queue
        if tag_node_name in self._write_queues_dict:
            self._write_queues_dict.pop(tag_node_name, None)
        
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
        self._dropped_frames_dict.pop(tag_node_name, None)

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
                
                # Store writer
                self._video_writer_dict[tag_node_name] = video_writer
                
                # Create queue for frames
                write_queue = queue.Queue(maxsize=self._QUEUE_MAX_SIZE)
                self._write_queues_dict[tag_node_name] = write_queue
                
                # Initialize counters
                self._frame_count_dict[tag_node_name] = 0
                self._dropped_frames_dict[tag_node_name] = 0
                
                # Start write thread
                write_thread = threading.Thread(
                    target=self._writer_thread,
                    args=(tag_node_name, video_writer, writer_width, writer_height),
                    daemon=True,
                    name=f"VideoWriter-Write-{tag_node_name}"
                )
                self._write_threads_dict[tag_node_name] = write_thread
                write_thread.start()
                
                logger.info(f"[VideoWriter] Started threaded recording {video_format}: {file_path}")
                dpg.set_item_label(tag_node_button_value_name, self._stop_label)
                
            except Exception as e:
                logger.error(f"[VideoWriter] Error starting recording: {e}")
                logger.error(traceback.format_exc())
                create_crash_log("recording_start", e, tag_node_name)
                
                # Clean up on error
                self._video_writer_dict.pop(tag_node_name, None)
                self._write_queues_dict.pop(tag_node_name, None)
                self._write_threads_dict.pop(tag_node_name, None)
            
        elif label == self._stop_label:
            # ============ STOP RECORDING ============
            try:
                # Signal write thread to stop
                if tag_node_name in self._write_queues_dict:
                    try:
                        self._write_queues_dict[tag_node_name].put(None, timeout=1.0)
                    except queue.Full:
                        logger.warning(f"[VideoWriter] Could not send stop signal to write thread (queue full)")
                
                # Wait for write thread to finish
                if tag_node_name in self._write_threads_dict:
                    write_thread = self._write_threads_dict.pop(tag_node_name)
                    write_thread.join(timeout=self._WRITE_THREAD_TIMEOUT)
                    if write_thread.is_alive():
                        logger.warning(f"[VideoWriter] Write thread did not stop cleanly for {tag_node_name}")
                
                # Clean up queue
                self._write_queues_dict.pop(tag_node_name, None)
                
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
                    dropped_count = self._dropped_frames_dict.get(tag_node_name, 0)
                    logger.info(f"[VideoWriter] Stopped recording, finalizing in background ({frame_count} frames written, {dropped_count} dropped)")
                    
            except Exception as e:
                logger.error(f"[VideoWriter] Error stopping recording: {e}")
                logger.error(traceback.format_exc())
                create_crash_log("recording_stop", e, tag_node_name)
