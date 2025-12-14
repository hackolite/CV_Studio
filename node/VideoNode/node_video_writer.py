#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import copy
import datetime
import json
import subprocess
import tempfile
import traceback
import threading
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
#from node_editor.util import convert_cv_to_dpg
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

try:
    import ffmpeg
    import soundfile as sf
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    sf = None
    logger.warning("FFmpeg or soundfile not available")

# Import background worker
try:
    from node.VideoNode.video_worker import VideoBackgroundWorker, ProgressEvent, WorkerState
    WORKER_AVAILABLE = True
except ImportError:
    WORKER_AVAILABLE = False
    logger.warning("video_worker module not available, using legacy sync mode")

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
            
            # Add progress bar for encoding/merge operation
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_progress_bar(
                    label="Progress",
                    tag=node.tag_node_progress_name,
                    default_value=0.0,
                    overlay="Ready",
                    width=small_window_w,
                    show=True,  # Always visible for state feedback
                )
            
            # Add detailed progress info text
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_name + ':ProgressInfo',
                    default_value="",
                    show=False,  # Hidden by default
                )
            
            # Add control buttons for pause/resume/cancel (hidden by default)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                with dpg.group(tag=node.tag_node_name + ':ControlGroup', horizontal=True, show=False):
                    dpg.add_button(
                        label="Pause",
                        tag=node.tag_node_name + ':PauseButton',
                        width=int(small_window_w / 3) - 5,
                        callback=node._pause_button,
                        user_data=node.tag_node_name,
                    )
                    dpg.add_button(
                        label="Resume",
                        tag=node.tag_node_name + ':ResumeButton',
                        width=int(small_window_w / 3) - 5,
                        callback=node._resume_button,
                        user_data=node.tag_node_name,
                        show=False,
                    )
                    dpg.add_button(
                        label="Cancel",
                        tag=node.tag_node_name + ':CancelButton',
                        width=int(small_window_w / 3) - 5,
                        callback=node._cancel_button,
                        user_data=node.tag_node_name,
                    )

        return node



class VideoWriterNode(Node):
    _ver = '0.0.3'

    node_label = 'VideoWriter'
    node_tag = 'VideoWriter'

    _opencv_setting_dict = None

    _video_writer_dict = {}
    _mkv_metadata_dict = {}  # Store audio and JSON metadata for MKV files
    _mkv_file_handles = {}  # Store file handles for MKV metadata tracks
    _audio_samples_dict = {}  # Store audio samples per slot: {node: {slot_idx: {'samples': [], 'timestamp': float (indicative), 'sample_rate': int}}}
    _json_samples_dict = {}  # Store JSON samples per slot: {node: {slot_idx: {'samples': [], 'timestamp': float (indicative)}}}
    _recording_metadata_dict = {}  # Store metadata about ongoing recordings
    _merge_threads_dict = {}  # Store merge threads for async operations
    _merge_progress_dict = {}  # Store merge progress (0.0 to 1.0)
    _frame_count_dict = {}  # Track number of frames written during recording: {node: frame_count}
    _last_frame_dict = {}  # Store last frame for potential duplication: {node: frame}
    _source_metadata_dict = {}  # Store metadata from source nodes (e.g., target_fps from Video node)
    _stopping_state_dict = {}  # Track stopping state: {node: {'stopping': bool, 'required_frames': int, 'audio_chunks': int}}
    
    # Background worker instances
    _background_workers = {}  # Store VideoBackgroundWorker instances
    _worker_mode = {}  # Track which mode each node is using (legacy/worker)
    
    _start_label = 'Start'
    _stop_label = 'Stop'
    
    # Default values for audio/video parameters
    _DEFAULT_SAMPLE_RATE = 44100  # Default audio sample rate in Hz (matches video input extraction)
    _DEFAULT_FPS = 30  # Default video frames per second
    
    # Constants for file wait logic
    # These control the behavior when waiting for the video file to be written to disk
    # before starting the audio/video merge operation
    _FILE_WAIT_TIMEOUT = 5.0  # Maximum seconds to wait for video file (range: 1.0-10.0)
    _FILE_WAIT_INTERVAL = 0.1  # Check interval in seconds (range: 0.05-0.5)
    _FILE_FLUSH_DELAY = 0.1  # Additional delay after file exists to ensure flush (range: 0.05-0.5)

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
        tag_node_progress_name = tag_node_name + ':' + self.TYPE_TEXT + ':Progress'
        tag_progress_info_name = tag_node_name + ':ProgressInfo'

        # Check if using background worker mode
        using_worker = tag_node_name in self._background_workers
        
        # Update progress for background worker
        if using_worker and tag_node_name in self._background_workers:
            worker = self._background_workers[tag_node_name]
            
            # Get latest progress from worker
            if worker.is_active():
                progress_event = worker.progress_tracker.get_progress(worker.get_state())
                
                # Update progress bar
                if dpg.does_item_exist(tag_node_progress_name):
                    dpg.configure_item(tag_node_progress_name, show=True)
                    dpg.set_value(tag_node_progress_name, progress_event.percent / 100.0)
                    
                    # Create overlay text
                    if progress_event.state == WorkerState.ENCODING:
                        overlay = f"Encoding: {progress_event.percent:.1f}%"
                    elif progress_event.state == WorkerState.FLUSHING:
                        overlay = "Finalizing..."
                    elif progress_event.state == WorkerState.PAUSED:
                        overlay = "Paused"
                    else:
                        overlay = f"{progress_event.state.value}: {progress_event.percent:.1f}%"
                    
                    dpg.configure_item(tag_node_progress_name, overlay=overlay)
                
                # Update detailed info
                if dpg.does_item_exist(tag_progress_info_name):
                    dpg.configure_item(tag_progress_info_name, show=True)
                    
                    info_lines = []
                    info_lines.append(f"Frames: {progress_event.frames_encoded}")
                    if progress_event.total_frames:
                        info_lines.append(f"/{progress_event.total_frames}")
                    
                    if progress_event.encode_speed > 0:
                        info_lines.append(f" | {progress_event.encode_speed:.1f} fps")
                    
                    if progress_event.eta_seconds is not None and progress_event.eta_seconds > 0:
                        eta_min = int(progress_event.eta_seconds // 60)
                        eta_sec = int(progress_event.eta_seconds % 60)
                        info_lines.append(f" | ETA {eta_min}m {eta_sec}s")
                    
                    dpg.set_value(tag_progress_info_name, ''.join(info_lines))
            
            # Check if worker completed
            if worker.get_state() in [WorkerState.COMPLETED, WorkerState.ERROR, WorkerState.CANCELLED]:
                # Clean up worker
                self._background_workers.pop(tag_node_name, None)
                self._worker_mode.pop(tag_node_name, None)
                
                # Hide control buttons
                control_group_tag = tag_node_name + ':ControlGroup'
                if dpg.does_item_exist(control_group_tag):
                    dpg.configure_item(control_group_tag, show=False)
                
                # Update progress bar with final state
                if dpg.does_item_exist(tag_node_progress_name):
                    if worker.get_state() == WorkerState.COMPLETED:
                        dpg.configure_item(tag_node_progress_name, overlay="Complete")
                        dpg.set_value(tag_node_progress_name, 1.0)
                    elif worker.get_state() == WorkerState.ERROR:
                        dpg.configure_item(tag_node_progress_name, overlay="Error")
                    elif worker.get_state() == WorkerState.CANCELLED:
                        dpg.configure_item(tag_node_progress_name, overlay="Cancelled")
                
                # Hide detailed info
                if dpg.does_item_exist(tag_progress_info_name):
                    dpg.configure_item(tag_progress_info_name, show=False)
                    dpg.set_value(tag_progress_info_name, "")
                
                # Reset button label
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
        
        # Update merge progress bar for legacy mode if merge is in progress
        if not using_worker and tag_node_name in self._merge_progress_dict:
            progress = self._merge_progress_dict[tag_node_name]
            if dpg.does_item_exist(tag_node_progress_name):
                dpg.configure_item(tag_node_progress_name, show=True)
                dpg.set_value(tag_node_progress_name, progress)
                dpg.configure_item(tag_node_progress_name, overlay=f"Merging: {int(progress * 100)}%")
            
            # Check if merge thread has completed
            if tag_node_name in self._merge_threads_dict:
                thread = self._merge_threads_dict[tag_node_name]
                if not thread.is_alive():
                    # Thread completed, clean up
                    self._merge_threads_dict.pop(tag_node_name)
                    self._merge_progress_dict.pop(tag_node_name)
                    if dpg.does_item_exist(tag_node_progress_name):
                        dpg.configure_item(tag_node_progress_name, show=False)
                        dpg.set_value(tag_node_progress_name, 0.0)
                        dpg.configure_item(tag_node_progress_name, overlay="")

        connection_info_src = ''
        logger.debug(f"[VideoWriter] Processing connections: {connection_list}")
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = connection_info_src.split(':')[:2]
            connection_info_src = ':'.join(connection_info_src)

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        writer_width = self._opencv_setting_dict['video_writer_width']
        writer_height = self._opencv_setting_dict['video_writer_height']

        frame = node_image_dict.get(connection_info_src, None)
        
        # Get audio, JSON data, and metadata if available
        audio_data = node_audio_dict.get(connection_info_src, None)
        json_data = node_result_dict.get(connection_info_src, None)
        
        # Extract metadata from source node (e.g., target_fps from Video node)
        source_metadata = {}
        if isinstance(json_data, dict):
            source_metadata = json_data.get('metadata', {})
        
        # Store source metadata for use during recording
        # Class variable _source_metadata_dict is initialized at class level (line 217)
        if source_metadata and tag_node_name in self._video_writer_dict:
            self._source_metadata_dict[tag_node_name] = source_metadata
            logger.debug(f"[VideoWriter] Received metadata: {source_metadata}")


        if frame is not None:
            rec_frame = copy.deepcopy(frame)

            # Check if using background worker mode
            if tag_node_name in self._background_workers:
                # Background worker mode - push frame to worker queue
                worker = self._background_workers[tag_node_name]
                
                # Resize frame for encoding
                writer_frame = cv2.resize(rec_frame,
                                          (writer_width, writer_height),
                                          interpolation=cv2.INTER_CUBIC)
                
                # Extract audio data
                audio_chunk = None
                if audio_data is not None:
                    # Handle different audio data formats
                    if isinstance(audio_data, dict):
                        if 'data' in audio_data and 'sample_rate' in audio_data:
                            # Single audio chunk from video node
                            audio_chunk = audio_data['data']
                        else:
                            # Concat node output: {slot_idx: audio_chunk}
                            # Merge all slots into a single audio track
                            # Sort by slot index only (timestamps are indicative only)
                            audio_chunks = []
                            
                            for slot_idx in sorted(audio_data.keys()):
                                slot_audio = audio_data[slot_idx]
                                if isinstance(slot_audio, dict) and 'data' in slot_audio:
                                    audio_chunks.append(slot_audio['data'])
                                elif isinstance(slot_audio, np.ndarray):
                                    audio_chunks.append(slot_audio)
                            
                            if audio_chunks:
                                # Concatenate based on slot order only
                                audio_chunk = np.concatenate(audio_chunks)
                    elif isinstance(audio_data, np.ndarray):
                        audio_chunk = audio_data
                
                # Push to worker queue (non-blocking with backpressure)
                success = worker.push_frame(writer_frame, audio_chunk)
                if not success:
                    logger.warning(f"[VideoWriter] Frame dropped due to queue backpressure")
                
            elif tag_node_name in self._video_writer_dict:
                # Legacy mode - direct write to VideoWriter

                writer_frame = cv2.resize(rec_frame,
                                          (writer_width, writer_height),
                                          interpolation=cv2.INTER_CUBIC)
                self._video_writer_dict[tag_node_name].write(writer_frame)
                
                # Track frame count and store last frame for potential duplication
                if tag_node_name not in self._frame_count_dict:
                    self._frame_count_dict[tag_node_name] = 0
                self._frame_count_dict[tag_node_name] += 1
                self._last_frame_dict[tag_node_name] = writer_frame
                
                # Check if we're in stopping state and have enough frames
                if tag_node_name in self._stopping_state_dict:
                    stopping_info = self._stopping_state_dict[tag_node_name]
                    current_frames = self._frame_count_dict.get(tag_node_name, 0)
                    required_frames = stopping_info['required_frames']
                    
                    logger.debug(f"[VideoWriter] Stopping state: {current_frames}/{required_frames} frames")
                    
                    # Check if we've collected enough frames
                    if current_frames >= required_frames:
                        logger.info(f"[VideoWriter] Reached required frame count ({current_frames}/{required_frames}), finalizing recording")
                        # Finalize the recording (no recursive call)
                        self._finalize_recording(tag_node_name)
                
                # Collect audio samples per slot for final merge (for all formats)
                # Only collect audio if we're not in stopping state (audio collection stops when user presses stop)
                is_stopping = tag_node_name in self._stopping_state_dict
                if audio_data is not None and tag_node_name in self._audio_samples_dict and not is_stopping:
                    # audio_data can be a dict (from concat node with multiple slots) or a single chunk
                    if isinstance(audio_data, dict):
                        # Check if this is a multi-slot concat output or single audio chunk from video node
                        # Multi-slot: {0: audio_chunk, 1: audio_chunk, ...}
                        # Single chunk: {'data': array, 'sample_rate': int, 'timestamp': float}
                        
                        if 'data' in audio_data and 'sample_rate' in audio_data:
                            # Single audio chunk from video node (slot 0)
                            slot_idx = 0
                            if slot_idx not in self._audio_samples_dict[tag_node_name]:
                                self._audio_samples_dict[tag_node_name][slot_idx] = {
                                    'samples': [],
                                    'timestamp': audio_data.get('timestamp', float('inf')),
                                    'sample_rate': audio_data['sample_rate']
                                }
                            self._audio_samples_dict[tag_node_name][slot_idx]['samples'].append(audio_data['data'])
                            # Update sample rate if provided
                            if tag_node_name in self._recording_metadata_dict:
                                self._recording_metadata_dict[tag_node_name]['sample_rate'] = audio_data['sample_rate']
                            logger.debug(f"[VideoWriter] Collected single audio chunk, sample_rate={audio_data['sample_rate']}")
                        else:
                            # Concat node output: {slot_idx: audio_chunk}
                            # Collect audio samples per slot (will be merged by timestamp at recording end)
                            for slot_idx in audio_data.keys():
                                audio_chunk = audio_data[slot_idx]
                                
                                # Handle dict format from video node: {'data': array, 'sample_rate': int, 'timestamp': float}
                                if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
                                    timestamp = audio_chunk.get('timestamp', float('inf'))
                                    sample_rate = audio_chunk.get('sample_rate', self._DEFAULT_SAMPLE_RATE)
                                    
                                    # Initialize slot if not exists
                                    if slot_idx not in self._audio_samples_dict[tag_node_name]:
                                        self._audio_samples_dict[tag_node_name][slot_idx] = {
                                            'samples': [],
                                            'timestamp': timestamp,
                                            'sample_rate': sample_rate
                                        }
                                    
                                    # Append this frame's audio to the slot
                                    self._audio_samples_dict[tag_node_name][slot_idx]['samples'].append(audio_chunk['data'])
                                    
                                    # Update sample rate for recording metadata
                                    if tag_node_name in self._recording_metadata_dict:
                                        self._recording_metadata_dict[tag_node_name]['sample_rate'] = sample_rate
                                        
                                elif isinstance(audio_chunk, np.ndarray):
                                    # Plain numpy array - use default timestamp and sample rate
                                    if slot_idx not in self._audio_samples_dict[tag_node_name]:
                                        self._audio_samples_dict[tag_node_name][slot_idx] = {
                                            'samples': [],
                                            'timestamp': float('inf'),
                                            'sample_rate': self._DEFAULT_SAMPLE_RATE
                                        }
                                    self._audio_samples_dict[tag_node_name][slot_idx]['samples'].append(audio_chunk)
                    else:
                        # Single audio chunk as numpy array (slot 0)
                        if isinstance(audio_data, np.ndarray):
                            slot_idx = 0
                            if slot_idx not in self._audio_samples_dict[tag_node_name]:
                                self._audio_samples_dict[tag_node_name][slot_idx] = {
                                    'samples': [],
                                    'timestamp': float('inf'),
                                    'sample_rate': self._DEFAULT_SAMPLE_RATE
                                }
                            self._audio_samples_dict[tag_node_name][slot_idx]['samples'].append(audio_data)
                
                # Collect JSON samples per slot for final merge (for MKV format)
                if json_data is not None and tag_node_name in self._json_samples_dict:
                    # json_data can be a dict (from concat node with multiple slots) or a single chunk
                    if isinstance(json_data, dict):
                        # Concat node output: {slot_idx: json_chunk}
                        # Collect JSON samples per slot
                        for slot_idx, json_chunk in json_data.items():
                            # Validate JSON serializability before storing
                            try:
                                json.dumps(json_chunk)  # Test serialization
                            except (TypeError, ValueError) as e:
                                logger.warning(f"[VideoWriter] Skipping non-serializable JSON chunk for slot {slot_idx}: {e}")
                                continue
                            
                            # Initialize slot if not exists
                            if slot_idx not in self._json_samples_dict[tag_node_name]:
                                self._json_samples_dict[tag_node_name][slot_idx] = {
                                    'samples': [],
                                    'timestamp': float('inf')
                                }
                            
                            # Append this frame's JSON to the slot
                            self._json_samples_dict[tag_node_name][slot_idx]['samples'].append(json_chunk)
                    else:
                        # Single JSON chunk (slot 0)
                        # Validate JSON serializability before storing
                        try:
                            json.dumps(json_data)  # Test serialization
                            slot_idx = 0
                            if slot_idx not in self._json_samples_dict[tag_node_name]:
                                self._json_samples_dict[tag_node_name][slot_idx] = {
                                    'samples': [],
                                    'timestamp': float('inf')
                                }
                            self._json_samples_dict[tag_node_name][slot_idx]['samples'].append(json_data)
                        except (TypeError, ValueError) as e:
                            logger.warning(f"[VideoWriter] Skipping non-serializable JSON data: {e}")
                
                # Write audio and JSON data to MKV metadata tracks if applicable
                if tag_node_name in self._mkv_metadata_dict:
                    metadata = self._mkv_metadata_dict[tag_node_name]
                    file_base = metadata['file_path'].rsplit('.', 1)[0]
                    metadata_dir = file_base + '_metadata'
                    
                    # Write audio chunks if available
                    if audio_data is not None:
                        for slot_idx, audio_chunk in (audio_data.items() if isinstance(audio_data, dict) else enumerate([audio_data])):
                            # Create audio track file if not exists
                            if slot_idx not in metadata['audio_handles']:
                                audio_file = os.path.join(metadata_dir, f'audio_slot_{slot_idx}.jsonl')
                                metadata['audio_handles'][slot_idx] = open(audio_file, 'a')
                            
                            handle = metadata['audio_handles'][slot_idx]
                            # Store audio chunk as JSON (will be written to file)
                            handle.write(json.dumps({'slot': slot_idx, 'data': audio_chunk.tolist() if hasattr(audio_chunk, 'tolist') else str(audio_chunk)}) + '\n')
                            handle.flush()  # Ensure data is written
                    
                    # Write JSON data if available
                    if json_data is not None:
                        for slot_idx, json_chunk in (json_data.items() if isinstance(json_data, dict) else enumerate([json_data])):
                            # Create JSON track file if not exists
                            if slot_idx not in metadata['json_handles']:
                                json_file = os.path.join(metadata_dir, f'json_slot_{slot_idx}.jsonl')
                                metadata['json_handles'][slot_idx] = open(json_file, 'a')
                            
                            handle = metadata['json_handles'][slot_idx]
                            # Write JSON chunk
                            handle.write(json.dumps({'slot': slot_idx, 'data': json_chunk}) + '\n')
                            handle.flush()  # Ensure data is written


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

    def _close_metadata_handles(self, metadata):
        """Helper method to close all metadata file handles"""
        # Close all audio handles
        for handle in metadata.get('audio_handles', {}).values():
            if not handle.closed:
                handle.close()
        
        # Close all JSON handles
        for handle in metadata.get('json_handles', {}).values():
            if not handle.closed:
                handle.close()

    def _adapt_video_to_audio_duration(self, video_path, audio_samples, sample_rate, fps, temp_adapted_path):
        """
        Adapt video duration to match audio duration by duplicating the last frame if needed.
        
        This method uses frame-by-frame copying which is simple and reliable but may be slower
        for large videos. For production use with very long videos, consider implementing an
        alternative using ffmpeg's concat filter for better performance.
        
        Args:
            video_path: Path to the original video file
            audio_samples: List of numpy arrays containing audio samples
            sample_rate: Audio sample rate
            fps: Video frames per second (from input video settings)
            temp_adapted_path: Path to save the adapted video
            
        Returns:
            True if adaptation was needed and successful, False if no adaptation needed
        """
        cap = None
        out = None
        try:
            # Calculate required video duration from audio
            total_audio_samples = sum(len(samples) for samples in audio_samples)
            audio_duration = total_audio_samples / sample_rate
            
            # Open original video to get current frame count
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"[VideoWriter] Failed to open video for duration check: {video_path}")
                return False
            
            # Get frame count and validate it
            video_frame_count_raw = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            
            # Validate frame count (check for NaN, inf, or invalid values)
            if not np.isfinite(video_frame_count_raw) or video_frame_count_raw <= 0:
                logger.warning(f"[VideoWriter] Invalid frame count ({video_frame_count_raw}), cannot adapt video duration")
                return False
            
            video_frame_count = int(video_frame_count_raw)
            
            video_duration = video_frame_count / fps if fps > 0 else 0
            
            logger.info(f"[VideoWriter] Video duration: {video_duration:.2f}s ({video_frame_count} frames at {fps} fps)")
            logger.info(f"[VideoWriter] Audio duration: {audio_duration:.2f}s ({total_audio_samples} samples at {sample_rate} Hz)")
            
            # Calculate required frames for audio duration
            required_frames = int(audio_duration * fps)
            frames_to_add = required_frames - video_frame_count
            
            if frames_to_add <= 0:
                # Video is already long enough or longer than audio
                logger.info(f"[VideoWriter] No frame adaptation needed (video >= audio duration)")
                return False
            
            logger.info(f"[VideoWriter] Adapting video: adding {frames_to_add} frames to match audio duration")
            
            # Get video properties and validate them
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if width <= 0 or height <= 0:
                logger.error(f"[VideoWriter] Invalid video dimensions: {width}x{height}")
                return False
            
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            
            # Create new video writer with adapted path
            out = cv2.VideoWriter(temp_adapted_path, fourcc, fps, (width, height))
            if not out.isOpened():
                logger.error(f"[VideoWriter] Failed to create adapted video writer")
                return False
            
            # Copy all existing frames
            # Note: This reads/writes frames individually which may be slower for large videos.
            # For production use, consider using ffmpeg's concat filter for better performance.
            # However, this approach is simpler and works reliably across all video formats.
            last_frame = None
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                last_frame = frame
            
            # Duplicate last frame to fill the gap
            if last_frame is not None:
                for _ in range(frames_to_add):
                    out.write(last_frame)
                logger.info(f"[VideoWriter] Duplicated last frame {frames_to_add} times")
            else:
                # Handle edge case: empty video (no frames)
                logger.warning(f"[VideoWriter] Source video has no frames, cannot adapt duration")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[VideoWriter] Error adapting video duration: {e}", exc_info=True)
            return False
        finally:
            # Ensure resources are properly released
            if cap is not None:
                cap.release()
            if out is not None:
                out.release()

    def _merge_audio_video_ffmpeg(self, video_path, audio_samples, sample_rate, output_path, fps=None, video_format='MP4', progress_callback=None):
        """
        Merge video and audio using ffmpeg with audio priority.
        
        AUDIO PRIORITY WORKFLOW:
        This method ensures audio is built completely with guaranteed quality before merging.
        
        Workflow:
        1. Validate and filter audio samples
        2. Concatenate all audio samples (AUDIO BUILD)
        3. Calculate audio duration
        4. Write audio to WAV file (LOSSLESS, HIGH QUALITY)
        5. Adapt video to match audio duration (if needed)
        6. Merge using FFmpeg with 192k AAC bitrate (QUALITY GUARANTEE)
        
        Args:
            video_path: Path to the temporary video file (no audio)
            audio_samples: List of numpy arrays containing audio samples
            sample_rate: Audio sample rate (e.g., 22050, 44100)
            output_path: Path to the final output file with audio
            fps: Video frames per second (from input video settings) - used for duration adaptation
            video_format: Video format (AVI, MP4, MKV) - affects codec selection
            progress_callback: Optional callback function to report progress (0.0 to 1.0)
        
        Returns:
            True if successful, False otherwise
        """
        if not FFMPEG_AVAILABLE or sf is None:
            logger.warning("[VideoWriter] ffmpeg-python and soundfile are required for audio merging")
            return False
        
        try:
            # Verify video file exists
            if not os.path.exists(video_path):
                logger.error(f"[VideoWriter] Video file not found: {video_path}")
                return False
            
            # Report progress: Starting audio processing
            if progress_callback:
                progress_callback(0.1)
            
            # Step 1: Validate and filter audio samples
            if not audio_samples:
                logger.warning("[VideoWriter] No audio samples collected, merging only video")
                return False
            
            logger.debug(f"[VideoWriter] Merge: Received {len(audio_samples)} audio sample chunks")
            
            # Filter out empty or invalid arrays
            valid_samples = [sample for sample in audio_samples 
                           if isinstance(sample, np.ndarray) and sample.size > 0]
            
            if not valid_samples:
                logger.warning("[VideoWriter] No valid audio samples to merge")
                return False
            
            logger.debug(f"[VideoWriter] Merge: {len(valid_samples)} valid sample chunks after filtering")
            
            # Step 2: Concatenate all valid audio samples (AUDIO BUILD - PRIORITY STEP)
            # This is where audio is fully assembled before any video processing
            full_audio = np.concatenate(valid_samples)
            total_duration = len(full_audio) / sample_rate
            
            logger.info(f"[VideoWriter] Merge: Total audio duration = {total_duration:.2f}s at {sample_rate}Hz")
            logger.info(f"[VideoWriter] Audio built successfully with {len(full_audio)} samples at {sample_rate}Hz")
            
            # Step 3: Adapt video to match audio duration (AUDIO HAS PRIORITY)
            # Video is adapted to match audio, NOT the other way around
            actual_video_path = video_path
            if fps is not None and fps > 0:
                # Extract file extension safely using os.path.splitext
                video_base, video_ext = os.path.splitext(video_path)
                adapted_path = f"{video_base}_adapted{video_ext}"
                if self._adapt_video_to_audio_duration(video_path, valid_samples, sample_rate, fps, adapted_path):
                    actual_video_path = adapted_path
                    logger.info(f"[VideoWriter] Video adapted to match audio duration: {adapted_path}")
            
            # Report progress: Audio concatenated
            if progress_callback:
                progress_callback(0.3)
            
            # Step 4: Write audio to WAV file (QUALITY GUARANTEE)
            # WAV format is lossless and preserves full audio quality
            # No sample rate conversion, no compression
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
            
            try:
                # Write audio with native sample rate (NO CONVERSION - QUALITY PRESERVED)
                sf.write(temp_audio_path, full_audio, sample_rate)
                logger.info(f"[VideoWriter] Audio file written with guaranteed quality: {sample_rate}Hz WAV format")
                
                # Report progress: Audio file written
                if progress_callback:
                    progress_callback(0.5)
                
                # Use ffmpeg to merge video and audio (use adapted path if available)
                video_input = ffmpeg.input(actual_video_path)
                audio_input = ffmpeg.input(temp_audio_path)
                
                # Determine video codec based on format
                # AVI with MJPEG has timing issues, needs re-encoding to H.264
                # MP4 and MKV can use copy (no re-encoding needed)
                if video_format == 'AVI':
                    # Re-encode AVI to H.264 for proper timing and audio sync
                    # MJPEG in AVI containers has frame timing issues that cause slow playback
                    vcodec = 'libx264'
                    vcodec_preset = 'medium'  # Balance between speed and quality
                else:
                    # For MP4 and MKV, copy the video codec (no re-encoding)
                    vcodec = 'copy'
                    vcodec_preset = None
                
                # Step 5: Merge video and audio with HIGH QUALITY settings (AUDIO PRIORITY)
                # Audio quality is guaranteed through high bitrate and proper encoding
                # 
                # QUALITY PARAMETERS:
                # - audio_bitrate='192k': HIGH QUALITY AAC (prevents audio artifacts/distortion)
                #   This ensures audio has priority for quality over file size
                # - acodec='aac': AAC codec (industry standard for quality)
                # - avoid_negative_ts='make_zero': Perfect audio/video synchronization
                # - vsync='cfr': Constant frame rate (prevents drift)
                # - shortest=None: Stop when shortest stream ends
                # - vcodec: For AVI, re-encode to H.264; for others, copy codec
                output_params = {
                    'vcodec': vcodec,
                    'acodec': 'aac',
                    'audio_bitrate': '192k',  # AUDIO PRIORITY - High quality over file size
                    'shortest': None,
                    'vsync': 'cfr',
                    'avoid_negative_ts': 'make_zero',
                    'loglevel': 'error'
                }
                
                # Add preset for H.264 encoding (AVI only)
                if vcodec_preset:
                    output_params['preset'] = vcodec_preset
                
                output = ffmpeg.output(
                    video_input,
                    audio_input,
                    output_path,
                    **output_params
                )
                
                # Overwrite output file if it exists
                output = ffmpeg.overwrite_output(output)
                
                # Report progress: Starting ffmpeg merge
                if progress_callback:
                    progress_callback(0.7)
                
                # Run ffmpeg
                ffmpeg.run(output, capture_stdout=True, capture_stderr=True)
                
                # Report progress: Merge complete
                if progress_callback:
                    progress_callback(1.0)
                
                logger.info(f"[VideoWriter] Successfully merged audio and video to {output_path}")
                return True
                
            finally:
                # Clean up temporary audio file
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                
                # Clean up adapted video file if it was created
                if actual_video_path != video_path and os.path.exists(actual_video_path):
                    os.remove(actual_video_path)
                    logger.debug(f"[VideoWriter] Cleaned up adapted video: {actual_video_path}")
                    
        except Exception as e:
            logger.error(f"[VideoWriter] Error merging audio and video: {e}", exc_info=True)
            return False

    def close(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Cancel and wait for background worker if active
        if tag_node_name in self._background_workers:
            worker = self._background_workers[tag_node_name]
            logger.info(f"[VideoWriter] Cancelling background worker for {tag_node_name}")
            worker.cancel()
            self._background_workers.pop(tag_node_name, None)
        
        # Clean up worker mode tracking
        if tag_node_name in self._worker_mode:
            self._worker_mode.pop(tag_node_name)
        
        # Wait for any ongoing merge threads to complete
        if tag_node_name in self._merge_threads_dict:
            thread = self._merge_threads_dict[tag_node_name]
            if thread.is_alive():
                logger.info(f"[VideoWriter] Waiting for merge to complete for {tag_node_name}")
                thread.join(timeout=30)  # Wait up to 30 seconds
            self._merge_threads_dict.pop(tag_node_name, None)
        
        # Clean up merge progress
        if tag_node_name in self._merge_progress_dict:
            self._merge_progress_dict.pop(tag_node_name)
        
        if tag_node_name in self._video_writer_dict:
            self._video_writer_dict[tag_node_name].release()
            self._video_writer_dict.pop(tag_node_name)
        
        # Clean up stopping state
        if tag_node_name in self._stopping_state_dict:
            self._stopping_state_dict.pop(tag_node_name)
        
        # Clean up MKV metadata if exists
        if tag_node_name in self._mkv_metadata_dict:
            metadata = self._mkv_metadata_dict[tag_node_name]
            self._close_metadata_handles(metadata)
            self._mkv_metadata_dict.pop(tag_node_name)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass

    def _async_merge_thread(self, tag_node_name, temp_path, audio_samples, sample_rate, final_path, fps, video_format='MP4', json_samples=None):
        """
        Thread worker function to merge audio and video asynchronously.
        This runs in a separate thread to prevent UI freezing.
        
        Args:
            tag_node_name: Node identifier
            temp_path: Path to temporary video file
            audio_samples: List of concatenated audio samples
            sample_rate: Audio sample rate
            final_path: Final output file path
            fps: Video frames per second (from input video settings)
            video_format: Video format (AVI, MP4, MKV)
            json_samples: Dictionary of JSON samples per slot (for MKV)
        """
        def progress_callback(progress):
            """Update progress in the shared dict"""
            self._merge_progress_dict[tag_node_name] = progress
        
        try:
            # Initialize progress
            self._merge_progress_dict[tag_node_name] = 0.0
            
            # Wait for video file to be fully written (with timeout)
            elapsed = 0
            while not os.path.exists(temp_path) and elapsed < self._FILE_WAIT_TIMEOUT:
                time.sleep(self._FILE_WAIT_INTERVAL)
                elapsed += self._FILE_WAIT_INTERVAL
            
            if not os.path.exists(temp_path):
                logger.error(f"[VideoWriter] Temporary video file not found: {temp_path}")
                raise FileNotFoundError(f"Temporary video file not found: {temp_path}")
            
            # Additional small wait to ensure file is fully flushed
            time.sleep(self._FILE_FLUSH_DELAY)
            
            # Perform the merge with progress reporting (pass FPS for duration adaptation)
            success = self._merge_audio_video_ffmpeg(
                temp_path,
                audio_samples,
                sample_rate,
                final_path,
                fps=fps,
                video_format=video_format,
                progress_callback=progress_callback
            )
            
            if success:
                # For MKV format, save concatenated JSON metadata alongside the video
                if video_format == 'MKV' and json_samples:
                    try:
                        # Sort JSON samples by slot index only (timestamps are indicative only)
                        sorted_json_slots = sorted(
                            json_samples.items(),
                            key=lambda x: x[0]  # Sort by slot_idx only
                        )
                        
                        # Create metadata directory
                        file_base = final_path.rsplit('.', 1)[0]
                        metadata_dir = file_base + '_metadata'
                        os.makedirs(metadata_dir, exist_ok=True)
                        
                        # Save concatenated JSON stream per slot
                        for slot_idx, slot_data in sorted_json_slots:
                            if slot_data['samples']:
                                json_file = os.path.join(metadata_dir, f'json_slot_{slot_idx}_concat.json')
                                try:
                                    # Prepare data structure
                                    output_data = {
                                        'slot_idx': slot_idx,
                                        'timestamp': slot_data['timestamp'],
                                        'samples': slot_data['samples']
                                    }
                                    # Validate serializability by attempting to serialize
                                    json_str = json.dumps(output_data, indent=2)
                                    # Write validated JSON to file
                                    with open(json_file, 'w') as f:
                                        f.write(json_str)
                                    logger.info(f"[VideoWriter] Saved JSON metadata for slot {slot_idx} to: {json_file}")
                                except (TypeError, ValueError) as json_err:
                                    logger.error(f"[VideoWriter] JSON serialization error for slot {slot_idx}: {json_err}")
                                    # Attempt to save with default serialization (converts non-serializable to str)
                                    try:
                                        with open(json_file, 'w') as f:
                                            json.dump({
                                                'slot_idx': slot_idx,
                                                'timestamp': float(slot_data['timestamp']) if slot_data['timestamp'] != float('inf') else 'inf',
                                                'samples': str(slot_data['samples'])
                                            }, f, indent=2)
                                        logger.warning(f"[VideoWriter] Saved JSON metadata with fallback serialization for slot {slot_idx}")
                                    except Exception as fallback_err:
                                        logger.error(f"[VideoWriter] Failed to save JSON metadata even with fallback: {fallback_err}")
                    except Exception as json_error:
                        logger.error(f"[VideoWriter] Error saving JSON metadata: {json_error}", exc_info=True)
                
                # Remove temporary video file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                logger.info(f"[VideoWriter] Video with audio saved to: {final_path}")
            else:
                # If merge failed, rename temp file to final name
                if os.path.exists(temp_path):
                    os.rename(temp_path, final_path)
                logger.warning(f"[VideoWriter] Audio merge failed. Video without audio saved to: {final_path}")
                
        except Exception as e:
            # Critical error during audio/video merge - create crash log
            create_crash_log("audio_video_merge", e, tag_node_name)
            logger.error(f"[VideoWriter] Error in async merge thread: {e}", exc_info=True)
            # Try to save the temp file as final on error
            if os.path.exists(temp_path):
                try:
                    os.rename(temp_path, final_path)
                    logger.info(f"[VideoWriter] Video saved to: {final_path} (merge failed)")
                except Exception as rename_error:
                    logger.error(f"[VideoWriter] Error renaming temp file: {rename_error}")
        finally:
            # Clean up merge progress indicator
            if tag_node_name in self._merge_progress_dict:
                # Set to 1.0 to indicate completion before cleanup
                self._merge_progress_dict[tag_node_name] = 1.0
    


    def _finalize_recording(self, tag_node_name):
        """
        Finalize the recording by releasing resources and starting merge.
        
        AUDIO PRIORITY WORKFLOW:
        This method ensures audio is built first with guaranteed quality before merging with video.
        
        Workflow:
        1. Release video writer (video file closed)
        2. Build audio completely (concatenate all slots)
        3. Detect and preserve audio sample rate (no conversion)
        4. Start async merge thread (audio-first merge)
        
        This method is called either:
        1. When user clicks Stop and we already have enough frames
        2. When in stopping state and we reach the required frame count
        
        Args:
            tag_node_name: The node identifier
        """
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'
        
        # Step 1: Release video writer if in legacy mode
        # Video file is closed, no more frames can be written
        if tag_node_name in self._video_writer_dict:
            self._video_writer_dict[tag_node_name].release()
            self._video_writer_dict.pop(tag_node_name)
        
        # Step 2: Build audio completely before merge (AUDIO PRIORITY)
        # Merge audio and video if audio samples were collected
        if tag_node_name in self._audio_samples_dict and len(self._audio_samples_dict[tag_node_name]) > 0:
            if tag_node_name in self._recording_metadata_dict:
                metadata = self._recording_metadata_dict[tag_node_name]
                temp_path = metadata['temp_path']
                final_path = metadata['final_path']
                sample_rate = metadata['sample_rate']
                
                # Step 3: Process audio samples - AUDIO PRIORITY
                # Sort slots by slot index only, concatenate each slot, then merge
                # This ensures audio is built completely before video merge
                slot_audio_dict = self._audio_samples_dict[tag_node_name]
                
                # Sort slots by slot index only (timestamps are indicative only)
                # Video stream creation is based on actual accumulated data size, not timestamps
                sorted_slots = sorted(
                    slot_audio_dict.items(),
                    key=lambda x: x[0]  # Sort by slot_idx only
                )
                
                # Build final audio sample list in slot index order
                audio_samples_list = []
                # Track if we encounter mixed sample rates (use the first valid one)
                final_sample_rate = None
                
                for slot_idx, slot_data in sorted_slots:
                    # Concatenate all samples for this slot
                    if slot_data['samples']:
                        slot_concatenated = np.concatenate(slot_data['samples'])
                        audio_samples_list.append(slot_concatenated)
                    
                    # Step 4: Detect and preserve sample rate (QUALITY GUARANTEE)
                    # Use the first valid sample rate we encounter
                    # Note: All slots should have the same sample rate for proper merging
                    if final_sample_rate is None and 'sample_rate' in slot_data and slot_data['sample_rate'] is not None:
                        final_sample_rate = slot_data['sample_rate']
                
                # Use the detected sample rate, fallback to metadata default
                # NO SAMPLE RATE CONVERSION - Quality is guaranteed
                if final_sample_rate is not None:
                    sample_rate = final_sample_rate
                
                # Get video format and FPS for format-specific merging
                video_format = metadata.get('format', 'MP4')
                fps = metadata.get('fps', 30)  # Get FPS from recording metadata
                
                # Process JSON samples for MKV format
                json_samples_dict = None
                if video_format == 'MKV' and tag_node_name in self._json_samples_dict:
                    json_samples_dict = self._json_samples_dict[tag_node_name]
                
                # Step 5: Start merge in a separate thread to prevent UI freezing
                # At this point, audio is fully built and ready for merge
                # The merge thread will:
                # 1. Write audio to WAV file (lossless, high quality)
                # 2. Adapt video to match audio duration (if needed)
                # 3. Merge using FFmpeg with 192k AAC bitrate
                merge_thread = threading.Thread(
                    target=self._async_merge_thread,
                    args=(tag_node_name, temp_path, audio_samples_list, sample_rate, final_path, fps, video_format, json_samples_dict),
                    daemon=True
                )
                merge_thread.start()
                
                # Store thread reference for tracking
                self._merge_threads_dict[tag_node_name] = merge_thread
                
                logger.info(f"[VideoWriter] Started async merge for: {final_path} (format: {video_format})")
                
                # Clean up metadata
                self._recording_metadata_dict.pop(tag_node_name)
        else:
            # No audio samples, just rename temp file to final name
            if tag_node_name in self._recording_metadata_dict:
                metadata = self._recording_metadata_dict[tag_node_name]
                temp_path = metadata['temp_path']
                final_path = metadata['final_path']
                
                if os.path.exists(temp_path):
                    os.rename(temp_path, final_path)
                logger.info(f"[VideoWriter] Video without audio saved to: {final_path}")
                
                self._recording_metadata_dict.pop(tag_node_name)
        
        # Clean up audio samples
        if tag_node_name in self._audio_samples_dict:
            self._audio_samples_dict.pop(tag_node_name)
        
        # Clean up JSON samples
        if tag_node_name in self._json_samples_dict:
            self._json_samples_dict.pop(tag_node_name)
        
        # Clean up frame tracking
        if tag_node_name in self._frame_count_dict:
            self._frame_count_dict.pop(tag_node_name)
        if tag_node_name in self._last_frame_dict:
            self._last_frame_dict.pop(tag_node_name)
        
        # Clean up stopping state
        if tag_node_name in self._stopping_state_dict:
            self._stopping_state_dict.pop(tag_node_name)
        
        # Close metadata file handles if MKV
        if tag_node_name in self._mkv_metadata_dict:
            metadata = self._mkv_metadata_dict[tag_node_name]
            self._close_metadata_handles(metadata)
            self._mkv_metadata_dict.pop(tag_node_name)

        dpg.set_item_label(tag_node_button_value_name, self._start_label)
    
    def _recording_button(self, sender, data, user_data):
        tag_node_name = user_data
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)

        if label == self._start_label:

            datetime_now = datetime.datetime.now()
            
            startup_time_text = datetime_now.strftime('%Y%m%d_%H%M%S')
            writer_width = self._opencv_setting_dict['video_writer_width']
            writer_height = self._opencv_setting_dict['video_writer_height']
            writer_fps = self._opencv_setting_dict['video_writer_fps']
            video_writer_directory = self._opencv_setting_dict[
                'video_writer_directory']
            
            # Use target_fps from source metadata if available (from Video node slider)
            # This ensures output video FPS matches the input video node configuration
            if tag_node_name in self._source_metadata_dict:
                source_metadata = self._source_metadata_dict[tag_node_name]
                if 'target_fps' in source_metadata:
                    writer_fps = source_metadata['target_fps']
                    logger.info(f"[VideoWriter] Using target_fps from source: {writer_fps}")

            os.makedirs(video_writer_directory, exist_ok=True)

            # Get selected format
            format_tag = tag_node_name + ':Format'
            video_format = dpg_get_value(format_tag)
            
            # Determine file extension
            format_config = {
                'AVI': {'ext': '.avi', 'codec': 'MJPG'},
                'MKV': {'ext': '.mkv', 'codec': 'FFV1'},
                'MP4': {'ext': '.mp4', 'codec': 'mp4v'}
            }
            
            config = format_config.get(video_format, format_config['MP4'])
            file_path = os.path.join(video_writer_directory, f'{startup_time_text}{config["ext"]}')

            # Try to use background worker mode if available
            use_worker = WORKER_AVAILABLE and FFMPEG_AVAILABLE
            
            if use_worker and tag_node_name not in self._background_workers:
                # Start background worker
                try:
                    # Use chunk duration from source metadata if available (from Video node slider)
                    # Otherwise default to 3.0 seconds (matches node_video.py default)
                    # This ensures queue size is fps * chunk_duration * audio_queue_size for proper audio/video sync
                    chunk_duration = 3.0
                    if tag_node_name in self._source_metadata_dict:
                        source_metadata = self._source_metadata_dict[tag_node_name]
                        if 'chunk_duration' in source_metadata:
                            chunk_duration = source_metadata['chunk_duration']
                            logger.info(f"[VideoWriter] Using chunk_duration from source: {chunk_duration}s")
                    
                    worker = VideoBackgroundWorker(
                        output_path=file_path,
                        width=writer_width,
                        height=writer_height,
                        fps=writer_fps,
                        sample_rate=self._DEFAULT_SAMPLE_RATE,  # Default, will be updated from incoming audio
                        total_frames=None,  # Unknown initially
                        progress_callback=None,  # Progress is polled in update()
                        chunk_duration=chunk_duration  # Queue sizing based on chunk duration
                    )
                    worker.start()
                    
                    self._background_workers[tag_node_name] = worker
                    self._worker_mode[tag_node_name] = 'worker'
                    
                    logger.info(f"[VideoWriter] Started background worker for: {file_path}")
                    
                    # Show control buttons for pause/cancel
                    control_group_tag = tag_node_name + ':ControlGroup'
                    if dpg.does_item_exist(control_group_tag):
                        dpg.configure_item(control_group_tag, show=True)
                    
                    # Show pause button, hide resume button
                    pause_button_tag = tag_node_name + ':PauseButton'
                    resume_button_tag = tag_node_name + ':ResumeButton'
                    if dpg.does_item_exist(pause_button_tag):
                        dpg.configure_item(pause_button_tag, show=True)
                    if dpg.does_item_exist(resume_button_tag):
                        dpg.configure_item(resume_button_tag, show=False)
                    
                except Exception as e:
                    logger.error(f"[VideoWriter] Failed to start background worker: {e}")
                    logger.error(traceback.format_exc())
                    use_worker = False
            
            # Fallback to legacy mode if worker not available or failed
            if not use_worker and tag_node_name not in self._video_writer_dict:
                temp_file_path = os.path.join(video_writer_directory, f'{startup_time_text}_temp{config["ext"]}')
                
                # Create video writer with temporary path
                self._video_writer_dict[tag_node_name] = cv2.VideoWriter(
                    temp_file_path,
                    cv2.VideoWriter_fourcc(*config['codec']),
                    writer_fps,
                    (writer_width, writer_height),
                )
                
                # Initialize metadata tracking for MKV
                if video_format == 'MKV':
                    self._mkv_metadata_dict[tag_node_name] = {
                        'audio_handles': {},
                        'json_handles': {},
                        'file_path': file_path,
                    }
                    
                    # Create metadata track files (will be stored alongside video)
                    metadata_dir = os.path.join(video_writer_directory, f'{startup_time_text}_metadata')
                    os.makedirs(metadata_dir, exist_ok=True)
                
                # Initialize audio sample collection per slot
                self._audio_samples_dict[tag_node_name] = {}  # Dict of {slot_idx: {'samples': [], 'timestamp': float, 'sample_rate': int}}
                
                # Initialize JSON sample collection per slot
                self._json_samples_dict[tag_node_name] = {}  # Dict of {slot_idx: {'samples': [], 'timestamp': float}}
                
                # Store recording metadata for final merge
                self._recording_metadata_dict[tag_node_name] = {
                    'final_path': file_path,
                    'temp_path': temp_file_path,
                    'format': video_format,
                    'sample_rate': self._DEFAULT_SAMPLE_RATE,  # Default sample rate, can be adjusted based on input
                    'fps': writer_fps  # Store FPS from input video settings for duration adaptation
                }
                
                self._worker_mode[tag_node_name] = 'legacy'
                logger.info(f"[VideoWriter] Started legacy mode for: {file_path}")

            dpg.set_item_label(tag_node_button_value_name, self._stop_label)
            
        elif label == self._stop_label:
            
            # Check which mode we're using
            if tag_node_name in self._background_workers:
                # Background worker mode - stop the worker
                worker = self._background_workers[tag_node_name]
                worker.stop(wait=False)  # Don't block UI
                logger.info(f"[VideoWriter] Stopped background worker")
                
            elif tag_node_name in self._video_writer_dict:
                # Legacy mode - enter stopping state
                # Calculate required frames based on collected audio
                if tag_node_name in self._audio_samples_dict and len(self._audio_samples_dict[tag_node_name]) > 0:
                    # Count total audio elements across all slots
                    slot_audio_dict = self._audio_samples_dict[tag_node_name]
                    total_audio_samples = 0
                    total_audio_chunks = 0
                    sample_rate = self._DEFAULT_SAMPLE_RATE
                    
                    for slot_idx, slot_data in slot_audio_dict.items():
                        if slot_data['samples']:
                            total_audio_chunks += len(slot_data['samples'])
                            # Calculate total samples
                            for audio_chunk in slot_data['samples']:
                                total_audio_samples += len(audio_chunk)
                            # Get sample rate from first slot
                            if 'sample_rate' in slot_data and slot_data['sample_rate'] is not None:
                                sample_rate = slot_data['sample_rate']
                                break  # Use first valid sample rate
                    
                    # Calculate audio duration in seconds
                    # Protect against division by zero with sensible default
                    if sample_rate <= 0:
                        logger.warning(f"[VideoWriter] Invalid sample rate {sample_rate}, using default {self._DEFAULT_SAMPLE_RATE} Hz")
                        sample_rate = self._DEFAULT_SAMPLE_RATE
                    
                    audio_duration = total_audio_samples / sample_rate
                    
                    # Get FPS from recording metadata
                    fps = self._DEFAULT_FPS
                    if tag_node_name in self._recording_metadata_dict:
                        fps = self._recording_metadata_dict[tag_node_name].get('fps', self._DEFAULT_FPS)
                    
                    # Additional validation for FPS
                    if fps <= 0:
                        logger.warning(f"[VideoWriter] Invalid fps {fps}, using default {self._DEFAULT_FPS}")
                        fps = self._DEFAULT_FPS
                    
                    # Calculate required frames: audio_duration * fps
                    # This ensures we have enough video frames to cover the entire audio duration.
                    # For example: 3 seconds of audio at 30 fps requires 90 frames.
                    # Note: An alternative interpretation would multiply by the number of audio chunks,
                    # but this would be incorrect as it would produce far too many frames. We want to
                    # match the total duration, not duration per chunk times number of chunks.
                    required_frames = int(audio_duration * fps)
                    current_frames = self._frame_count_dict.get(tag_node_name, 0)
                    
                    logger.info(f"[VideoWriter] Stop requested - Audio: {total_audio_chunks} chunks, "
                               f"{total_audio_samples} samples, {audio_duration:.2f}s at {sample_rate}Hz")
                    logger.info(f"[VideoWriter] Current frames: {current_frames}, Required frames: {required_frames} (at {fps} fps)")
                    
                    if current_frames < required_frames:
                        # Enter stopping state - continue collecting frames but stop collecting audio
                        self._stopping_state_dict[tag_node_name] = {
                            'stopping': True,
                            'required_frames': required_frames,
                            'audio_chunks': total_audio_chunks
                        }
                        logger.info(f"[VideoWriter] Entering stopping state - need {required_frames - current_frames} more frames")
                        
                        # Update button label to indicate we're in stopping state
                        # This provides user feedback that the system is still processing
                        dpg.set_item_label(tag_node_button_value_name, "Stopping...")
                        
                        # Early return - will finalize when we have enough frames
                        return
                    else:
                        # We already have enough frames, proceed with normal stop
                        logger.info(f"[VideoWriter] Already have enough frames ({current_frames} >= {required_frames}), stopping immediately")
                
                # Use the new finalization method instead of duplicating code
                self._finalize_recording(tag_node_name)
    
    def _pause_button(self, sender, data, user_data):
        """Pause the background video encoding"""
        tag_node_name = user_data
        
        if tag_node_name in self._background_workers:
            worker = self._background_workers[tag_node_name]
            worker.pause()
            
            logger.info(f"[VideoWriter] Paused encoding for: {tag_node_name}")
            
            # Update UI - show resume button, hide pause button
            pause_button_tag = tag_node_name + ':PauseButton'
            resume_button_tag = tag_node_name + ':ResumeButton'
            
            if dpg.does_item_exist(pause_button_tag):
                dpg.configure_item(pause_button_tag, show=False)
            if dpg.does_item_exist(resume_button_tag):
                dpg.configure_item(resume_button_tag, show=True)
    
    def _resume_button(self, sender, data, user_data):
        """Resume the background video encoding"""
        tag_node_name = user_data
        
        if tag_node_name in self._background_workers:
            worker = self._background_workers[tag_node_name]
            worker.resume()
            
            logger.info(f"[VideoWriter] Resumed encoding for: {tag_node_name}")
            
            # Update UI - show pause button, hide resume button
            pause_button_tag = tag_node_name + ':PauseButton'
            resume_button_tag = tag_node_name + ':ResumeButton'
            
            if dpg.does_item_exist(pause_button_tag):
                dpg.configure_item(pause_button_tag, show=True)
            if dpg.does_item_exist(resume_button_tag):
                dpg.configure_item(resume_button_tag, show=False)
    
    def _cancel_button(self, sender, data, user_data):
        """Cancel the background video encoding"""
        tag_node_name = user_data
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'
        
        if tag_node_name in self._background_workers:
            worker = self._background_workers[tag_node_name]
            worker.cancel()
            
            logger.info(f"[VideoWriter] Cancelled encoding for: {tag_node_name}")
            
            # Clean up worker
            self._background_workers.pop(tag_node_name, None)
            self._worker_mode.pop(tag_node_name, None)
            
            # Update UI
            dpg.set_item_label(tag_node_button_value_name, self._start_label)
            
            # Hide control buttons
            control_group_tag = tag_node_name + ':ControlGroup'
            if dpg.does_item_exist(control_group_tag):
                dpg.configure_item(control_group_tag, show=False)
            
            # Reset progress bar
            tag_node_progress_name = tag_node_name + ':' + self.TYPE_TEXT + ':Progress'
            if dpg.does_item_exist(tag_node_progress_name):
                dpg.set_value(tag_node_progress_name, 0.0)
                dpg.configure_item(tag_node_progress_name, overlay="Cancelled")
            
            # Hide progress info
            tag_progress_info_name = tag_node_name + ':ProgressInfo'
            if dpg.does_item_exist(tag_progress_info_name):
                dpg.configure_item(tag_progress_info_name, show=False)
