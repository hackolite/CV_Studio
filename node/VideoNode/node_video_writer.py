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
    # This ensures crash logging works even if the main logging system is unavailable
    # Duplicates logic from src/utils/logging.py line 14-30 intentionally for robustness
    def get_logs_directory():
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / 'logs'
        logs_dir.mkdir(exist_ok=True)
        return logs_dir

"""
VideoWriter Node - Simplified video-only implementation

This node handles video recording in MP4, AVI, and MKV formats with minimal memory footprint.
- Direct frame-by-frame writing using cv2.VideoWriter
- No audio handling
- No buffering or queuing
- Accumulates frames directly from concat node

Supported formats:
- MP4: H.264 codec (mp4v)
- AVI: MJPEG codec (MJPG)
- MKV: FFV1 codec (lossless)
"""

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


class AsyncFrameWriter:
    """
    Asynchronous frame writer that runs in a background thread.
    
    This class prevents UI freezing by writing video frames in a separate thread.
    Each write() call on cv2.VideoWriter can take 10-50ms with high resolution
    and slow codecs (MJPEG, FFV1), which blocks the UI thread. By using a queue
    and background thread, the UI remains responsive.
    """
    
    def __init__(self, video_writer, max_queue_size=30):
        """
        Initialize the async frame writer.
        
        Args:
            video_writer: cv2.VideoWriter instance to write frames to
            max_queue_size: Maximum number of frames to buffer (default 30 = ~1 second at 30fps)
        """
        self.video_writer = video_writer
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self.writer_thread = None
        self.stop_event = threading.Event()
        self.error = None
        self.frames_written = 0
        self.frames_dropped = 0
        
    def start(self):
        """Start the background writer thread"""
        if self.writer_thread is not None:
            logger.warning("[AsyncFrameWriter] Writer thread already started")
            return
            
        self.stop_event.clear()
        self.writer_thread = threading.Thread(
            target=self._writer_worker,
            name="AsyncFrameWriter",
            daemon=True
        )
        self.writer_thread.start()
        logger.info("[AsyncFrameWriter] Background writer thread started")
        
    def write(self, frame):
        """
        Queue a frame for writing (non-blocking).
        
        Args:
            frame: Video frame to write
            
        Returns:
            True if frame was queued, False if queue is full (frame dropped)
        """
        if self.stop_event.is_set():
            return False
            
        try:
            # Non-blocking put with immediate timeout
            # If queue is full, drop the frame to avoid blocking UI
            self.frame_queue.put(frame, block=False)
            return True
        except queue.Full:
            self.frames_dropped += 1
            if self.frames_dropped % 10 == 1:  # Log every 10th dropped frame
                logger.warning(f"[AsyncFrameWriter] Frame queue full, dropped {self.frames_dropped} frames")
            return False
            
    def _writer_worker(self):
        """Background thread that writes frames to cv2.VideoWriter"""
        try:
            logger.info("[AsyncFrameWriter] Writer worker started")
            
            while not self.stop_event.is_set():
                try:
                    # Wait for a frame with timeout to check stop_event periodically
                    frame = self.frame_queue.get(timeout=0.1)
                    
                    # Write frame to video file (this can take 10-50ms)
                    self.video_writer.write(frame)
                    self.frames_written += 1
                    
                    self.frame_queue.task_done()
                    
                except queue.Empty:
                    # No frame available, continue loop to check stop_event
                    continue
                    
            # Process remaining frames in queue before stopping
            while not self.frame_queue.empty():
                try:
                    frame = self.frame_queue.get_nowait()
                    self.video_writer.write(frame)
                    self.frames_written += 1
                    self.frame_queue.task_done()
                except queue.Empty:
                    break
                    
            logger.info(f"[AsyncFrameWriter] Writer worker finished, wrote {self.frames_written} frames, dropped {self.frames_dropped} frames")
            
        except Exception as e:
            self.error = e
            logger.error(f"[AsyncFrameWriter] Error in writer worker: {e}")
            logger.error(traceback.format_exc())
            
    def stop(self, wait=True, timeout=10.0):
        """
        Stop the writer thread and optionally wait for it to finish.
        
        Args:
            wait: If True, wait for thread to finish writing remaining frames
            timeout: Maximum time to wait for thread to finish
        """
        if self.writer_thread is None:
            return
            
        # Signal thread to stop
        self.stop_event.set()
        
        if wait and self.writer_thread.is_alive():
            # Wait for queue to be empty
            try:
                self.frame_queue.join()
            except:
                pass
                
            # Wait for thread to finish
            self.writer_thread.join(timeout=timeout)
            
            if self.writer_thread.is_alive():
                logger.warning(f"[AsyncFrameWriter] Writer thread still alive after {timeout}s timeout")
        
        self.writer_thread = None


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
    _async_writer_dict = {}  # Store active AsyncFrameWriter instances: {node: async_writer}
    _release_threads_dict = {}  # Track background release threads: {node: thread}
    
    _start_label = 'Start'
    _stop_label = 'Stop'
    _finalizing_label = 'Finalizing...'
    
    # Timeout for waiting on background finalization threads during cleanup
    _RELEASE_TIMEOUT_SECONDS = 60.0

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
            # Async write to VideoWriter if recording is active
            if tag_node_name in self._async_writer_dict:
                # Resize and write via async writer to prevent UI freeze
                writer_frame = cv2.resize(frame,
                                          (writer_width, writer_height),
                                          interpolation=cv2.INTER_CUBIC)
                self._async_writer_dict[tag_node_name].write(writer_frame)

            # Copy frame for display with recording indicator
            rec_frame = frame.copy()
            if tag_node_name in self._async_writer_dict:
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
        
        # Stop async writer if active
        if tag_node_name in self._async_writer_dict:
            try:
                async_writer = self._async_writer_dict[tag_node_name]
                async_writer.stop(wait=True, timeout=10.0)
            except Exception as e:
                logger.error(f"[VideoWriter] Error stopping async writer in close(): {e}")
            self._async_writer_dict.pop(tag_node_name, None)
        
        # Wait for any background finalization to complete
        if tag_node_name in self._release_threads_dict:
            release_thread = self._release_threads_dict[tag_node_name]
            if release_thread.is_alive():
                logger.info(f"[VideoWriter] Waiting for background finalization to complete for {tag_node_name}")
                release_thread.join(timeout=self._RELEASE_TIMEOUT_SECONDS)
                if release_thread.is_alive():
                    logger.warning(f"[VideoWriter] Background finalization still running after {self._RELEASE_TIMEOUT_SECONDS}s for {tag_node_name}")
            self._release_threads_dict.pop(tag_node_name, None)
        
        # Release video writer if still active (fallback for edge cases)
        if tag_node_name in self._video_writer_dict:
            try:
                self._video_writer_dict[tag_node_name].release()
            except Exception as e:
                logger.error(f"[VideoWriter] Error releasing video writer in close(): {e}")
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

    
    def _release_video_writer_async(self, tag_node_name, async_writer, video_writer, tag_node_button_value_name):
        """
        Release video writer in background thread to prevent UI freeze.
        
        The cv2.VideoWriter.release() method can take 10-30+ seconds for large videos,
        especially with MJPEG (AVI) and FFV1 (MKV) codecs. Running this in a background
        thread prevents the UI from freezing.
        
        Args:
            tag_node_name: Node identifier
            async_writer: AsyncFrameWriter instance to stop first
            video_writer: cv2.VideoWriter instance to release
            tag_node_button_value_name: Button tag to update when done
        """
        try:
            logger.info(f"[VideoWriter] Starting background finalization for {tag_node_name}")
            
            # First, stop the async writer and wait for it to finish writing frames
            async_writer.stop(wait=True, timeout=10.0)
            
            # Release the video writer (can take 10-30+ seconds)
            video_writer.release()
            
            logger.info(f"[VideoWriter] Background finalization completed for {tag_node_name}")
            
            # Update button label back to Start (thread-safe with DearPyGui)
            dpg.set_item_label(tag_node_button_value_name, self._start_label)
            
        except Exception as e:
            logger.error(f"[VideoWriter] Error during background finalization: {e}")
            logger.error(traceback.format_exc())
            # Still update the button label even on error
            try:
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
            except (SystemError, RuntimeError) as gui_error:
                # DearPyGui may have been destroyed, log and continue
                logger.debug(f"[VideoWriter] Could not update button label (GUI may be shutting down): {gui_error}")
        finally:
            # Clean up thread tracking
            if tag_node_name in self._release_threads_dict:
                self._release_threads_dict.pop(tag_node_name, None)

    
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

            # Create video writer
            video_writer = cv2.VideoWriter(
                file_path,
                cv2.VideoWriter_fourcc(*config['codec']),
                writer_fps,
                (writer_width, writer_height),
            )
            
            # Wrap in async writer to prevent UI freeze during frame writing
            async_writer = AsyncFrameWriter(video_writer, max_queue_size=30)
            async_writer.start()
            
            # Store both for later access
            self._video_writer_dict[tag_node_name] = video_writer
            self._async_writer_dict[tag_node_name] = async_writer
            
            logger.info(f"[VideoWriter] Started recording {video_format}: {file_path}")
            dpg.set_item_label(tag_node_button_value_name, self._stop_label)
            
        elif label == self._stop_label:
            # Stop recording - use background thread to prevent UI freeze
            if tag_node_name in self._async_writer_dict:
                async_writer = self._async_writer_dict.pop(tag_node_name)
                video_writer = self._video_writer_dict.pop(tag_node_name)
                
                # Update button to show we're finalizing
                dpg.set_item_label(tag_node_button_value_name, self._finalizing_label)
                
                # Start background thread to stop async writer and release the video writer
                # This prevents UI freeze during video file finalization (can take 10-30+ seconds)
                # Use daemon=False to ensure video files are properly finalized before app exit
                release_thread = threading.Thread(
                    target=self._release_video_writer_async,
                    args=(tag_node_name, async_writer, video_writer, tag_node_button_value_name),
                    daemon=False,
                    name=f"VideoWriter-Release-{tag_node_name}"
                )
                self._release_threads_dict[tag_node_name] = release_thread
                release_thread.start()
                
                logger.info(f"[VideoWriter] Stopped recording, finalizing in background")

