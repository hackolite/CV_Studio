#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import cv2
import numpy as np
import dearpygui.dearpygui as dpg
import librosa
import soundfile as sf
import subprocess
import tempfile
import os
import shutil
import logging

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node

# Set up logger for this module
logger = logging.getLogger(__name__)


class FactoryNode:
    node_label = "Video"
    node_tag = "Video"

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
        node = VideoNode()

        node.tag_node_name = str(node_id) + ":" + self.node_tag
        node.tag_node_input01_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input01"
        )

        node.tag_node_input02_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":Input02"
        )
        node.tag_node_input02_value_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":Input02Value"
        )

        node.tag_node_input04_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input04"
        )
        node.tag_node_input04_value_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input04Value"
        )

        node.tag_node_input05_name = (
            node.tag_node_name + ":" + node.TYPE_FLOAT + ":Input05"
        )
        node.tag_node_input05_value_name = (
            node.tag_node_name + ":" + node.TYPE_FLOAT + ":Input05Value"
        )

        node.tag_node_input06_name = (
            node.tag_node_name + ":" + node.TYPE_FLOAT + ":Input06"
        )
        node.tag_node_input06_value_name = (
            node.tag_node_name + ":" + node.TYPE_FLOAT + ":Input06Value"
        )

        node.tag_node_input07_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input07"
        )
        node.tag_node_input07_value_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input07Value"
        )

        node.tag_node_output01_name = (
            node.tag_node_name + ":" + node.TYPE_IMAGE + ":Output01"
        )
        node.tag_node_output01_value_name = (
            node.tag_node_name + ":" + node.TYPE_IMAGE + ":Output01Value"
        )

        node.tag_node_output02_name = (
            node.tag_node_name + ":" + node.TYPE_TIME_MS + ":Output02"
        )
        node.tag_node_output02_value_name = (
            node.tag_node_name + ":" + node.TYPE_TIME_MS + ":Output02Value"
        )

        node.tag_node_button_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":Button"
        )
        node.tag_node_button_value_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":ButtonValue"
        )

        node.tag_node_output_audio_name = (
            node.tag_node_name + ":" + node.TYPE_AUDIO + ":OutputAudio"
        )
        node.tag_node_output_audio_value_name = (
            node.tag_node_name + ":" + node.TYPE_AUDIO + ":OutputAudioValue"
        )

        node.tag_node_output_json_name = (
            node.tag_node_name + ":" + node.TYPE_JSON + ":OutputJson"
        )
        node.tag_node_output_json_value_name = (
            node.tag_node_name + ":" + node.TYPE_JSON + ":OutputJsonValue"
        )

        node.tag_node_queue_info_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":QueueInfo"
        )
        node.tag_node_queue_info_value_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":QueueInfoValue"
        )

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict["input_window_width"]
        small_window_h = node._opencv_setting_dict["input_window_height"]
        use_pref_counter = node._opencv_setting_dict["use_pref_counter"]

        black_image = np.zeros((small_window_h, small_window_w, 3))
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
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(
                    dpg.mvThemeCol_Button, (255, 255, 153, 255)
                )  # Yellow background
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255)
                )  # Yellow on hover
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255)
                )  # Yellow on press

        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            modal=True,
            height=int(small_window_h * 3),
            callback=node._callback_file_select,
            id="movie_select:" + str(node_id),
        ):
            dpg.add_file_extension("Movie (*.mp4 *.avi){.mp4,.avi}")
            dpg.add_file_extension("", color=(150, 255, 150, 255))

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
                dpg.add_button(
                    label="Select Movie",
                    width=node._small_window_w,
                    callback=lambda: dpg.show_item(
                        "movie_select:" + str(node_id),
                    ),
                )

            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            with dpg.node_attribute(
                tag=node.tag_node_input02_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    label="Loop",
                    tag=node.tag_node_input02_value_name,
                    callback=None,
                    user_data=node.tag_node_name,
                    default_value=True,
                )

            with dpg.node_attribute(
                tag=node.tag_node_input04_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input04_value_name,
                    label="Target FPS",
                    width=node._small_window_w - 80,
                    default_value=24,
                    min_value=1,
                    max_value=120,
                    callback=None,
                )

            with dpg.node_attribute(
                tag=node.tag_node_input05_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input05_value_name,
                    label="Speed",
                    width=node._small_window_w - 80,
                    default_value=1.0,
                    min_value=0.25,
                    max_value=4.0,
                    callback=None,
                )

            with dpg.node_attribute(
                tag=node.tag_node_input06_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input06_value_name,
                    label="Chunk Size (s)",
                    width=node._small_window_w - 80,
                    default_value=2.0,
                    min_value=0.5,
                    max_value=10.0,
                    callback=None,
                )

            with dpg.node_attribute(
                tag=node.tag_node_input07_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input07_value_name,
                    label="Queue Chunks",
                    width=node._small_window_w - 80,
                    default_value=4,
                    min_value=1,
                    max_value=20,
                    callback=None,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output02_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value="elapsed time(ms)",
                    )

            # Bouton Start avec thème jaune
            with dpg.node_attribute(
                tag=node.tag_node_button_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn_start = dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node._small_window_w,
                    callback=node._button,
                    user_data=node.tag_node_name,
                )
                dpg.bind_item_theme(btn_start, yellow_button_theme)

            # Outputs audio, json, float, elapsed time as disabled yellow buttons
            def add_yellow_disabled_button(label, tag):
                btn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node._small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                return btn

            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)

            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = add_yellow_disabled_button(
                    "JSON", node.tag_node_output_json_value_name
                )

            # Queue size information label
            with dpg.node_attribute(
                tag=node.tag_node_queue_info_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_queue_info_value_name,
                    default_value="Queue: Image=0/0 Audio=0/0",
                )

        return node


class VideoNode(Node):
    _ver = "0.0.1"

    node_label = "Video"
    node_tag = "Video"

    _opencv_setting_dict = None
    _start_label = "Start"
    _stop_label = "Stop"
    _loading_label = "Loading..."

    _min_val = 1
    _max_val = 200

    _youtube_capture = {}
    _prev_read_time = {}

    _video_capture = {}
    _movie_filepath = {}
    _prev_movie_filepath = {}
    _frame_count = {}
    _last_frame_time = {}
    _loop_elapsed_time = {}  # Track cumulative time across loops for continuous timestamps

    _min_val = 1
    _max_val = 10

    def __init__(self):
        super().__init__()  # Call parent constructor
        self._min_val = 1
        self._max_val = 1000

        self._small_window_w = 240
        self._small_window_h = 135

        self._start_label = "Start"
        self.node_tag = "Video"
        self.node_label = "Video"

        # Audio data storage - stores audio chunks in memory as numpy arrays
        self._audio_chunks = {}  # Store audio chunks in memory
        self._chunk_metadata = {}  # Metadata for chunk-to-frame mapping
        # Track which nodes have had their queues resized to prevent redundant resize operations on every frame
        self._queues_resized = {}

    def _preprocess_video(self, node_id, movie_path, chunk_duration=2.0, step_duration=2.0, num_chunks_to_keep=4):
        """
        Pre-process video by extracting and chunking audio into memory.
        
        This method:
        1. Extracts video metadata (FPS, frame count) using OpenCV
        2. Extracts audio using ffmpeg (WAV used temporarily during extraction only)
        3. Chunks audio into segments and stores all chunks in memory as numpy arrays
        4. Stores metadata for frame-to-chunk mapping
        5. Dynamically resizes queues based on num_chunks_to_keep
        
        Note: All audio chunks are loaded into memory for fast access during playback.
        
        Args:
            node_id: Node identifier
            movie_path: Path to video file
            chunk_duration: Duration of each audio chunk in seconds (default: 2.0)
            step_duration: Step size between chunks in seconds (default: 2.0, no overlap)
            num_chunks_to_keep: Number of chunks to keep in queue (default: 4)
        """
        if not movie_path or not os.path.exists(movie_path):
            logger.warning(f"[Video] Video file not found: {movie_path}")
            return
        
        logger.info(f"[Video] Pre-processing video: {movie_path}")
        
        # Clean up any previous chunks for this node
        self._cleanup_audio_chunks(node_id)
        
        try:
            # Step 1: Extract video metadata only (not frames to avoid memory issues)
            logger.debug("[Video] Extracting video metadata...")
            cap = cv2.VideoCapture(movie_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # Default fallback
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            logger.info(f"[Video] Metadata: FPS={fps}, Frames={frame_count}")
            
            # Step 2: Extract audio using ffmpeg directly to WAV (faster than librosa)
            logger.debug("[Video] Extracting audio with ffmpeg...")
            
            # Create temporary WAV file for full audio extraction
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                tmp_audio_path = tmp_audio.name
            
            try:
                # Use ffmpeg to extract audio as WAV - most efficient for spectrogram conversion
                subprocess.run(
                    [
                        "ffmpeg",
                        "-i", movie_path,
                        "-vn",  # No video
                        "-acodec", "pcm_s16le",  # WAV codec
                        "-ar", "44100",  # Sample rate (ESC-50 native sample rate)
                        "-ac", "1",  # Mono
                        "-y", tmp_audio_path,
                    ],
                    check=True,
                    capture_output=True,
                )
                
                # Load audio to get samples and sample rate
                y, sr = sf.read(tmp_audio_path)
                logger.info(f"[Video] Audio extracted: SR={sr}Hz, Duration={len(y)/sr:.2f}s")
                
            except subprocess.CalledProcessError as e:
                logger.warning(f"[Video] ffmpeg extraction failed, trying librosa: {e}")
                # Fallback to librosa if ffmpeg fails
                y, sr = librosa.load(movie_path, sr=44100)
                logger.info(f"[Video] Audio extracted with librosa: SR={sr}Hz, Duration={len(y)/sr:.2f}s")
            finally:
                # Clean up temporary full audio file
                if os.path.exists(tmp_audio_path):
                    os.unlink(tmp_audio_path)
            
            # Step 3: Chunk audio with sliding window and store in memory
            logger.debug(f"[Video] Chunking audio: chunk={chunk_duration}s, step={step_duration}s")
            chunk_samples = int(chunk_duration * sr)
            step_samples = int(step_duration * sr)
            
            audio_chunks = []
            chunk_start_times = []
            start = 0
            chunk_idx = 0
            
            while (start + chunk_samples) <= len(y):
                end = start + chunk_samples
                chunk = y[start:end]
                
                # Store chunk in memory as numpy array
                audio_chunks.append(chunk)
                chunk_start_times.append(start / sr)
                chunk_idx += 1
                start += step_samples
            
            # Handle remaining audio: pad to chunk_duration if necessary
            remaining_samples = len(y) - start
            if remaining_samples > 0:
                # Extract remaining audio
                remaining_chunk = y[start:]
                # Pad with zeros to reach chunk_samples
                padding_needed = chunk_samples - remaining_samples
                padded_chunk = np.pad(remaining_chunk, (0, padding_needed), mode='constant', constant_values=0)
                
                # Store padded chunk in memory
                audio_chunks.append(padded_chunk)
                chunk_start_times.append(start / sr)
                logger.debug(f"[Video] Padded last chunk: {remaining_samples/sr:.2f}s → {chunk_duration}s")
            
            # Store all audio chunks in memory
            self._audio_chunks[node_id] = audio_chunks
            
            # Verify all chunks are exactly chunk_duration
            if len(audio_chunks) > 0:
                first_duration = len(audio_chunks[0]) / sr
                last_duration = len(audio_chunks[-1]) / sr
                
                if abs(first_duration - chunk_duration) > 0.001 or abs(last_duration - chunk_duration) > 0.001:
                    logger.warning(f"[Video] Chunk duration mismatch - first: {first_duration:.3f}s, last: {last_duration:.3f}s")
                    
            logger.info(f"[Video] Created {len(audio_chunks)} audio chunks in memory")
            
            # Step 4: Calculate dynamic queue sizes
            # Image queue: num_chunks * chunk_duration * fps
            image_queue_size = int(num_chunks_to_keep * chunk_duration * fps)
            # Audio queue: num_chunks
            audio_queue_size = num_chunks_to_keep
            
            logger.info(f"[Video] Calculated queue sizes: Image={image_queue_size}, Audio={audio_queue_size}")
            
            # Step 5: Store metadata
            self._chunk_metadata[node_id] = {
                'fps': fps,
                'sr': sr,
                'chunk_duration': chunk_duration,
                'step_duration': step_duration,
                'chunk_start_times': chunk_start_times,
                'num_frames': frame_count,
                'num_chunks': len(audio_chunks),
                'image_queue_size': image_queue_size,
                'audio_queue_size': audio_queue_size,
            }
            
            logger.info(f"[Video] Pre-processing complete: Frames={frame_count}, Chunks={len(audio_chunks)}, FPS={fps}")
            
        except Exception as e:
            logger.error(f"[Video] Failed to pre-process video: {e}", exc_info=True)
    
    def _cleanup_audio_chunks(self, node_id):
        """
        Clean up in-memory audio chunks for a node.
        
        Args:
            node_id: Node identifier
        """
        # Clean up audio chunks from memory
        if node_id in self._audio_chunks:
            del self._audio_chunks[node_id]
        
        # Clean up metadata
        if node_id in self._chunk_metadata:
            del self._chunk_metadata[node_id]
        
        # Clean up queue resize flag
        if node_id in self._queues_resized:
            del self._queues_resized[node_id]
    
    def _get_audio_chunk_for_frame(self, node_id, frame_number):
        """
        Get the audio chunk data for a specific frame number from memory.
        
        Args:
            node_id: Node identifier
            frame_number: Current frame number
            
        Returns:
            Dictionary with 'data' (numpy array) and 'sample_rate' (int), or None if not available
        """
        if node_id not in self._chunk_metadata or node_id not in self._audio_chunks:
            return None
        
        metadata = self._chunk_metadata[node_id]
        fps = metadata['fps']
        step_duration = metadata['step_duration']
        sr = metadata['sr']
        
        # Calculate current time from frame number
        current_time = frame_number / fps if fps > 0 else 0
        
        # Calculate chunk index based on step duration
        chunk_index = int(current_time / step_duration)
        
        # Clamp to valid range
        audio_chunks = self._audio_chunks[node_id]
        chunk_index = max(0, min(chunk_index, len(audio_chunks) - 1))
        
        # Get audio chunk from memory
        try:
            audio_data = audio_chunks[chunk_index]
            # Return audio chunk in the format expected by audio processing nodes
            return {
                'data': audio_data,
                'sample_rate': sr
            }
        except Exception as e:
            logger.warning(f"[Video] Failed to get audio chunk {chunk_index} from memory: {e}")
        
        return None




    def _button(self, sender, app_data, user_data):
        logger.debug(f"[Video] Button clicked for {user_data}")

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ":" + self.node_tag
        tag_node_input02_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":Input02Value"
        )
        tag_node_input04_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input04Value"
        )
        tag_node_input05_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input05Value"
        )
        tag_node_input06_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input06Value"
        )
        tag_node_input07_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input07Value"
        )

        output_value01_tag = tag_node_name + ":" + self.TYPE_IMAGE + ":Output01Value"
        tag_node_output_image = tag_node_name + ":" + self.TYPE_IMAGE + ":Output01Value"
        output_value02_tag = tag_node_name + ":" + self.TYPE_TIME_MS + ":Output02Value"

        small_window_w = self._small_window_w
        small_window_h = self._small_window_h
        use_pref_counter = self._opencv_setting_dict["use_pref_counter"]

        for connection_info in connection_list:
            connection_type = connection_info[0].split(":")[2]
            if connection_type == self.TYPE_INT:
                source_tag = connection_info[0] + "Value"
                destination_tag = connection_info[1] + "Value"

                input_value = int(dpg_get_value(source_tag))
                input_value = max([self._min_val, input_value])
                input_value = min([self._max_val, input_value])
                dpg_set_value(destination_tag, input_value)

        movie_path = self._movie_filepath.get(str(node_id), None)
        prev_movie_path = self._prev_movie_filepath.get(str(node_id), None)
        if prev_movie_path != movie_path:
            video_capture = self._video_capture.get(str(node_id), None)
            if video_capture is not None:
                video_capture.release()
            self._video_capture[str(node_id)] = cv2.VideoCapture(movie_path)
            self._prev_movie_filepath[str(node_id)] = movie_path
            self._frame_count[str(node_id)] = 0
            self._last_frame_time[str(node_id)] = None
            self._loop_elapsed_time[str(node_id)] = 0.0  # Reset loop elapsed time for new video
            # Reset queue resize flag so queues will be resized for the new video
            if str(node_id) in self._queues_resized:
                del self._queues_resized[str(node_id)]

        video_capture = self._video_capture.get(str(node_id), None)

        loop_flag = dpg_get_value(tag_node_input02_value_name)

        skip_rate = 1  # Skip rate is now fixed at 1 (no skipping)
        target_fps_value = dpg_get_value(tag_node_input04_value_name)
        target_fps = int(target_fps_value) if target_fps_value is not None else 24
        playback_speed_value = dpg_get_value(tag_node_input05_value_name)
        playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0
        chunk_size_value = dpg_get_value(tag_node_input06_value_name)
        chunk_size = float(chunk_size_value) if chunk_size_value is not None else 2.0
        
        # Apply dynamic queue sizing if metadata is available (only once per video load)
        if str(node_id) in self._chunk_metadata and str(node_id) not in self._queues_resized:
            metadata = self._chunk_metadata[str(node_id)]
            if 'image_queue_size' in metadata and 'audio_queue_size' in metadata:
                image_queue_size = metadata['image_queue_size']
                audio_queue_size = metadata['audio_queue_size']
                
                # Update queue sizes via queue manager
                try:
                    if hasattr(node_image_dict, 'resize_queue'):
                        node_image_dict.resize_queue(tag_node_name, "image", image_queue_size)
                        logger.info(f"[Video] Resized image queue to {image_queue_size}")
                    if hasattr(node_audio_dict, 'resize_queue'):
                        node_audio_dict.resize_queue(tag_node_name, "audio", audio_queue_size)
                        logger.info(f"[Video] Resized audio queue to {audio_queue_size}")
                    
                    # Mark queues as resized for this node
                    self._queues_resized[str(node_id)] = True
                except Exception as e:
                    logger.warning(f"[Video] Failed to resize queues: {e}")

        if video_capture is not None and use_pref_counter:
            start_time = time.monotonic()

        frame = None
        if video_capture is not None:
            # Check frame timing for playback speed control
            current_time = time.time()
            last_time = self._last_frame_time.get(str(node_id), None)

            # Calculate desired frame interval based on target FPS and playback speed
            # Lower speed = longer interval between frames (slower playback)
            # Higher speed = shorter interval between frames (faster playback)
            frame_interval = (
                (1.0 / target_fps) / playback_speed
                if target_fps > 0 and playback_speed > 0
                else 0
            )

            # Only read a new frame if enough time has passed
            should_read_frame = (last_time is None) or (
                (current_time - last_time) >= frame_interval
            )

            if should_read_frame:
                while True:
                    ret, frame = video_capture.read()
                    if not ret:
                        if loop_flag:
                            # Before looping, add the video duration to elapsed time
                            # to ensure continuous timestamps across loops
                            
                            # Try to get duration from metadata first
                            if str(node_id) in self._chunk_metadata:
                                # Use actual video FPS from metadata for accurate duration
                                metadata = self._chunk_metadata[str(node_id)]
                                num_frames = metadata.get('num_frames', 0)
                                actual_fps = metadata.get('fps', 30.0)
                                video_duration = num_frames / actual_fps if actual_fps > 0 else 0
                            else:
                                # Fallback: get duration from OpenCV video properties
                                # This ensures loop timestamps work even without audio preprocessing
                                total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                                actual_fps = video_capture.get(cv2.CAP_PROP_FPS)
                                if actual_fps <= 0:
                                    actual_fps = target_fps  # Final fallback to user setting
                                video_duration = total_frames / actual_fps
                                
                            # Add duration to elapsed time (initialized when video is loaded)
                            self._loop_elapsed_time[str(node_id)] += video_duration
                            
                            # Reset to beginning
                            video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            self._frame_count[str(node_id)] = 0
                            _, frame = video_capture.read()
                        else:
                            video_capture.release()
                            video_capture = None
                            self._movie_filepath.pop(str(node_id))
                            self._prev_movie_filepath.pop(str(node_id))
                            self._video_capture.pop(str(node_id))

                            break

                    self._frame_count[str(node_id)] += 1
                    if (self._frame_count[str(node_id)] % skip_rate) == 0:
                        break

                # Record the time when we successfully read a frame
                self._last_frame_time[str(node_id)] = current_time

        if video_capture is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + "ms")

        if frame is not None:
            texture = self.convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(tag_node_output_image, texture)

        # Get audio chunk data for this frame to pass to other audio nodes
        audio_chunk_data = None
        current_frame_num = self._frame_count.get(str(node_id), 0)
        if str(node_id) in self._audio_chunks:
            audio_chunk_data = self._get_audio_chunk_for_frame(str(node_id), current_frame_num)

        # Calculate FPS-based timestamp for this frame
        # The timestamp is based on the frame number and the target FPS
        # This ensures consistent timestamps regardless of processing speed
        # For looping videos, we add the cumulative elapsed time from previous loops
        frame_timestamp = None
        if frame is not None and target_fps > 0:
            # Base timestamp = current_frame_num / target_fps
            # Note: current_frame_num is 1-indexed (incremented before use in line 683)
            # so frame 1 has timestamp ~0.033s at 30 FPS, not 0s
            base_timestamp = current_frame_num / target_fps
            
            # Add elapsed time from previous loops to maintain continuous timestamps
            loop_offset = self._loop_elapsed_time.get(str(node_id), 0.0)
            frame_timestamp = base_timestamp + loop_offset
            
            # Inject timestamp into audio chunk data for synchronization
            # Audio timestamps are only added when video frames are available because
            # audio-video synchronization requires both streams to have valid timestamps
            # Copy the dict to avoid modifying the cached version
            if audio_chunk_data is not None and isinstance(audio_chunk_data, dict):
                audio_chunk_data = audio_chunk_data.copy()
                audio_chunk_data['timestamp'] = frame_timestamp
        
        # Update queue size information label
        tag_node_queue_info_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":QueueInfoValue"
        )
        
        # Get queue information (current size and max capacity) from the queue manager
        image_queue_size = 0
        image_queue_maxsize = 0
        audio_queue_size = 0
        audio_queue_maxsize = 0
        try:
            image_queue_info = node_image_dict.get_queue_info(tag_node_name)
            if image_queue_info.get("exists", False):
                image_queue_size = image_queue_info.get("size", 0)
                image_queue_maxsize = image_queue_info.get("maxsize", 0)
        except Exception as e:
            logger.debug(f"[Video] Failed to get image queue info: {e}")
        
        try:
            audio_queue_info = node_audio_dict.get_queue_info(tag_node_name)
            if audio_queue_info.get("exists", False):
                audio_queue_size = audio_queue_info.get("size", 0)
                audio_queue_maxsize = audio_queue_info.get("maxsize", 0)
        except Exception as e:
            logger.debug(f"[Video] Failed to get audio queue info: {e}")
        
        # Update the queue info label with current size and maximum capacity
        queue_info_text = f"Queue: Image={image_queue_size}/{image_queue_maxsize} Audio={audio_queue_size}/{audio_queue_maxsize}"
        dpg_set_value(tag_node_queue_info_value_name, queue_info_text)
        
        # Return frame via IMAGE output and audio chunk data via AUDIO output
        # Include the FPS-based timestamp so it can be used for synchronization
        return {
            "image": frame, 
            "json": None, 
            "audio": audio_chunk_data,
            "timestamp": frame_timestamp
        }

    def close(self, node_id):
        """Clean up audio chunks and temporary files when node is closed."""
        self._cleanup_audio_chunks(str(node_id))

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ":" + self.node_tag
        tag_node_input02_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":Input02Value"
        )
        tag_node_input04_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input04Value"
        )
        tag_node_input05_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input05Value"
        )
        tag_node_input06_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input06Value"
        )
        tag_node_input07_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input07Value"
        )

        pos = dpg.get_item_pos(tag_node_name)

        loop_flag = dpg_get_value(tag_node_input02_value_name)
        target_fps_value = dpg_get_value(tag_node_input04_value_name)
        target_fps = int(target_fps_value) if target_fps_value is not None else 24
        playback_speed_value = dpg_get_value(tag_node_input05_value_name)
        playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0
        chunk_size_value = dpg_get_value(tag_node_input06_value_name)
        chunk_size = float(chunk_size_value) if chunk_size_value is not None else 2.0
        queue_chunks_value = dpg_get_value(tag_node_input07_value_name)
        queue_chunks = int(queue_chunks_value) if queue_chunks_value is not None else 4

        setting_dict = {}
        setting_dict["ver"] = self._ver
        setting_dict["pos"] = pos
        setting_dict[tag_node_input02_value_name] = loop_flag
        setting_dict[tag_node_input04_value_name] = target_fps
        setting_dict[tag_node_input05_value_name] = playback_speed
        setting_dict[tag_node_input06_value_name] = chunk_size
        setting_dict[tag_node_input07_value_name] = queue_chunks

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ":" + self.node_tag
        tag_node_input02_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":Input02Value"
        )
        tag_node_input04_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input04Value"
        )
        tag_node_input05_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input05Value"
        )
        tag_node_input06_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input06Value"
        )
        tag_node_input07_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input07Value"
        )

        loop_flag = setting_dict[tag_node_input02_value_name]
        target_fps = int(setting_dict.get(tag_node_input04_value_name, 24))
        playback_speed = float(setting_dict.get(tag_node_input05_value_name, 1.0))
        chunk_size = float(setting_dict.get(tag_node_input06_value_name, 2.0))
        queue_chunks = int(setting_dict.get(tag_node_input07_value_name, 4))

        dpg_set_value(tag_node_input02_value_name, loop_flag)
        dpg_set_value(tag_node_input04_value_name, target_fps)
        dpg_set_value(tag_node_input05_value_name, playback_speed)
        dpg_set_value(tag_node_input06_value_name, chunk_size)
        dpg_set_value(tag_node_input07_value_name, queue_chunks)

    def _callback_file_select(self, sender, data):
        if data["file_name"] != ".":
            node_id = sender.split(":")[1]
            self._movie_filepath[node_id] = data["file_path_name"]
            tag_node_name = str(node_id) + ":" + self.node_tag
            
            # Get chunk size from slider
            tag_node_input06_value_name = (
                tag_node_name + ":" + self.TYPE_FLOAT + ":Input06Value"
            )
            chunk_size_value = dpg_get_value(tag_node_input06_value_name)
            chunk_size = float(chunk_size_value) if chunk_size_value is not None else 2.0
            
            # Get queue chunks from slider
            tag_node_input07_value_name = (
                tag_node_name + ":" + self.TYPE_INT + ":Input07Value"
            )
            num_chunks_value = dpg_get_value(tag_node_input07_value_name)
            num_chunks = int(num_chunks_value) if num_chunks_value is not None else 4
            
            # Preprocess video with chunk size and queue configuration
            self._preprocess_video(
                node_id, 
                data["file_path_name"], 
                chunk_duration=chunk_size, 
                step_duration=chunk_size,
                num_chunks_to_keep=num_chunks
            )
