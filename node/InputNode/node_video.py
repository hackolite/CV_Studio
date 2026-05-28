#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
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
import threading

try:
    import imageio_ffmpeg
    _IMAGEIO_FFMPEG_AVAILABLE = True
except ImportError:
    _IMAGEIO_FFMPEG_AVAILABLE = False


def _get_ffmpeg_exe():
    """Return the path to a usable ffmpeg executable.

    Resolution order:
    1. imageio-ffmpeg bundled binary (cross-platform, no system install needed).
    2. ffmpeg binary found on the system PATH via shutil.which.

    Returns the executable path string, or None if no backend is found.
    """
    if _IMAGEIO_FFMPEG_AVAILABLE:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except RuntimeError:
            pass
    return shutil.which("ffmpeg")

from node_editor.util import dpg_get_value, dpg_set_value, _dpg_lock

from node.node_abc import DpgNodeABC
from node.basenode import Node
from node.VideoNode.sync import FramePacket

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

        node.tag_node_input03_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input03"
        )
        node.tag_node_input03_value_name = (
            node.tag_node_name + ":" + node.TYPE_INT + ":Input03Value"
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
            node.tag_node_name + ":" + node.TYPE_TEXT + ":Input06"
        )
        node.tag_node_input06_value_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":Input06Value"
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

        node.tag_node_progress_bar_name = node.tag_node_name + ":ProgressBar"

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
                dpg.add_text(default_value="Image")
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
                tag=node.tag_node_input03_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input03_value_name,
                    label="Skip Rate",
                    width=node._small_window_w - 80,
                    default_value=1,
                    min_value=node._min_val,
                    max_value=node._max_val,
                    callback=None,
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
                dpg.add_checkbox(
                    label="Frames only",
                    tag=node.tag_node_input06_value_name,
                    callback=None,
                    user_data=node.tag_node_name,
                    default_value=False,
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
                dpg.add_progress_bar(
                    tag=node.tag_node_progress_bar_name,
                    default_value=0.0,
                    width=node._small_window_w,
                    show=False,
                    overlay="",
                )

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
    _preprocessing_status = {}  # Track preprocessing status: 'loading', 'done', 'error', or None
    _preprocessing_threads = {}  # Track preprocessing threads for cleanup
    _preprocessing_progress = {}  # Track chunking progress 0.0–1.0 per node
    _is_playing = {}  # Track whether video is playing or paused

    def __init__(self):
        super().__init__()  # Call parent constructor
        self._min_val = 1
        self._max_val = 1000

        self._small_window_w = 240
        self._small_window_h = 135

        self._start_label = "Start"
        self.node_tag = "Video"
        self.node_label = "Video"

        # Audio data storage - now stores WAV file paths instead of numpy arrays
        self._audio_chunk_paths = {}  # Store paths to WAV chunk files
        self._chunk_metadata = {}  # Metadata for chunk-to-frame mapping
        self._chunk_temp_dirs = {}  # Track temporary directories for cleanup

    def _preprocess_video(self, node_id, movie_path, chunk_duration=5.0, step_duration=1.0, progress_callback=None):
        """
        Pre-process video by extracting and chunking audio as WAV files.
        
        This method:
        1. Extracts video metadata (FPS, frame count) using OpenCV
        2. Extracts audio using ffmpeg to WAV format (faster and more efficient)
        3. Chunks audio into segments and saves each as a WAV file
        4. Stores metadata and WAV file paths for frame-to-chunk mapping
        
        Args:
            node_id: Node identifier
            movie_path: Path to video file
            chunk_duration: Duration of each audio chunk in seconds (default: 5.0)
            step_duration: Step size between chunks in seconds (default: 1.0)
            progress_callback: Optional callable(float) receiving 0.0–1.0 progress values
        """
        def _report(p):
            self._preprocessing_progress[node_id] = p
            if progress_callback:
                progress_callback(p)

        if not movie_path or not os.path.exists(movie_path):
            logger.warning("Video file not found: %s", movie_path)
            return
        
        logger.info("Pre-processing video: %s", movie_path)
        _report(0.0)
        
        # Clean up any previous chunks for this node
        self._cleanup_audio_chunks(node_id)
        
        try:
            # Step 1: Extract video metadata only (not frames to avoid memory issues)
            logger.debug("Extracting video metadata...")
            cap = cv2.VideoCapture(movie_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # Default fallback
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            logger.info("Video metadata extracted: FPS=%s, Frames=%s", fps, frame_count)
            _report(0.10)
            
            # Step 2: Extract audio using ffmpeg directly to WAV (faster than librosa)
            logger.info("Extracting audio with ffmpeg to WAV format...")
            
            # Locate the ffmpeg binary (imageio-ffmpeg bundled binary or system PATH)
            ffmpeg_exe = _get_ffmpeg_exe()
            
            # Create temporary WAV file for full audio extraction
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                tmp_audio_path = tmp_audio.name
            
            try:
                if ffmpeg_exe is None:
                    raise FileNotFoundError(
                        "ffmpeg not found. Install the 'imageio-ffmpeg' Python package "
                        "(pip install imageio-ffmpeg) or add ffmpeg to your system PATH."
                    )
                # Use ffmpeg to extract audio as WAV - most efficient for spectrogram conversion
                subprocess.run(
                    [
                        ffmpeg_exe,
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
                logger.info("Audio extracted: SR=%s Hz, Duration=%.2fs", sr, len(y)/sr)
                
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.warning("ffmpeg audio extraction failed: %s", e)
                raise RuntimeError(
                    f"Audio extraction failed. Ensure 'imageio-ffmpeg' is installed "
                    f"(pip install imageio-ffmpeg) or that ffmpeg is available on your PATH.\n"
                    f"Original error: {e}"
                ) from e
            finally:
                # Clean up temporary full audio file
                if os.path.exists(tmp_audio_path):
                    os.unlink(tmp_audio_path)
            
            _report(0.35)

            # Step 3: Create temporary directory for audio chunks
            chunk_temp_dir = tempfile.mkdtemp(prefix=f"cv_studio_audio_{node_id}_")
            self._chunk_temp_dirs[node_id] = chunk_temp_dir
            logger.debug("Created temp directory for chunks: %s", chunk_temp_dir)
            
            try:
                # Step 4: Chunk audio with sliding window and save each as WAV
                logger.info("Chunking audio: chunk=%.1fs, step=%.1fs", chunk_duration, step_duration)
                chunk_samples = int(chunk_duration * sr)
                step_samples = int(step_duration * sr)

                # Pre-calculate estimated chunk count for progress reporting
                total_samples = len(y)
                estimated_chunks = max(1, (total_samples - chunk_samples) // step_samples + 1)
                if total_samples % step_samples > 0:
                    estimated_chunks += 1
                
                chunk_paths = []
                chunk_start_times = []
                start = 0
                chunk_idx = 0
                
                while (start + chunk_samples) <= len(y):
                    end = start + chunk_samples
                    chunk = y[start:end]
                    
                    # Save chunk as WAV file
                    chunk_path = os.path.join(chunk_temp_dir, f"chunk_{chunk_idx:04d}.wav")
                    sf.write(chunk_path, chunk, sr)
                    
                    chunk_paths.append(chunk_path)
                    chunk_start_times.append(start / sr)
                    chunk_idx += 1
                    start += step_samples

                    # Report progress: 35%–95% during chunking
                    chunk_progress = 0.35 + 0.60 * (chunk_idx / estimated_chunks)
                    _report(min(chunk_progress, 0.95))
                
                # Handle remaining audio: pad to chunk_duration if necessary
                remaining_samples = len(y) - start
                if remaining_samples > 0:
                    # Extract remaining audio
                    remaining_chunk = y[start:]
                    # Pad with zeros to reach chunk_samples (5 seconds)
                    padding_needed = chunk_samples - remaining_samples
                    padded_chunk = np.pad(remaining_chunk, (0, padding_needed), mode='constant', constant_values=0)
                    
                    # Save padded chunk as WAV file
                    chunk_path = os.path.join(chunk_temp_dir, f"chunk_{chunk_idx:04d}.wav")
                    sf.write(chunk_path, padded_chunk, sr)
                    
                    chunk_paths.append(chunk_path)
                    chunk_start_times.append(start / sr)
                    logger.debug("Padded last chunk: %.2fs -> %.1fs (+%.2fs silence)", remaining_samples/sr, chunk_duration, padding_needed/sr)
                
                # Store chunk paths instead of numpy arrays
                self._audio_chunk_paths[node_id] = chunk_paths
                
                # Verify all chunks are exactly chunk_duration by reading first and last
                if len(chunk_paths) > 0:
                    first_chunk, _ = sf.read(chunk_paths[0])
                    last_chunk, _ = sf.read(chunk_paths[-1])
                    first_duration = len(first_chunk) / sr
                    last_duration = len(last_chunk) / sr
                    
                    if abs(first_duration - chunk_duration) > 0.001 or abs(last_duration - chunk_duration) > 0.001:
                        logger.warning("Chunk duration mismatch - first: %.3fs, last: %.3fs", first_duration, last_duration)
                        
                logger.info("Created %d audio chunks (%.1fs each)", len(chunk_paths), chunk_duration)
                
                # Step 5: Store metadata
                self._chunk_metadata[node_id] = {
                    'fps': fps,
                    'sr': sr,
                    'chunk_duration': chunk_duration,
                    'step_duration': step_duration,
                    'chunk_start_times': chunk_start_times,
                    'num_frames': frame_count,
                    'num_chunks': len(chunk_paths),
                }

                _report(1.0)
                logger.info("Pre-processing complete!")
                logger.info("  Frames: %s, Chunks: %d, FPS: %s", frame_count, len(chunk_paths), fps)
                logger.debug("  All chunks saved as WAV files")
            
            except Exception as chunk_error:
                # If chunking fails, clean up the temp directory
                logger.error("Failed during audio chunking: %s", chunk_error)
                self._cleanup_audio_chunks(node_id)
                raise
            
        except Exception as e:
            logger.error("Failed to pre-process video: %s", e)
            import traceback
            traceback.print_exc()
    
    def _cleanup_audio_chunks(self, node_id):
        """
        Clean up temporary WAV chunk files for a node.
        
        Args:
            node_id: Node identifier
        """
        # Clean up temporary directory (which also removes all chunk files)
        if node_id in self._chunk_temp_dirs:
            temp_dir = self._chunk_temp_dirs[node_id]
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning("Failed to delete temp directory %s: %s", temp_dir, e)
            del self._chunk_temp_dirs[node_id]
        
        # Clean up chunk paths reference
        if node_id in self._audio_chunk_paths:
            del self._audio_chunk_paths[node_id]
        
        # Clean up metadata
        if node_id in self._chunk_metadata:
            del self._chunk_metadata[node_id]
    
    def _get_audio_chunk_for_frame(self, node_id, frame_number):
        """
        Get the audio chunk data for a specific frame number by loading from WAV file.
        
        Args:
            node_id: Node identifier
            frame_number: Current frame number
            
        Returns:
            Dictionary with 'data' (numpy array) and 'sample_rate' (int), or None if not available
        """
        if node_id not in self._chunk_metadata or node_id not in self._audio_chunk_paths:
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
        chunk_paths = self._audio_chunk_paths[node_id]
        chunk_index = max(0, min(chunk_index, len(chunk_paths) - 1))
        
        # Load audio chunk from WAV file
        chunk_path = None
        try:
            chunk_path = chunk_paths[chunk_index]
            if os.path.exists(chunk_path):
                audio_data, sample_rate = sf.read(chunk_path)
                # Return audio chunk in the format expected by audio processing nodes
                return {
                    'data': audio_data,
                    'sample_rate': sample_rate,
                    'chunk_index': chunk_index,
                }
        except Exception as e:
            if chunk_path:
                logger.warning("Failed to load audio chunk %s from %s: %s", chunk_index, chunk_path, e)
            else:
                logger.warning("Failed to load audio chunk %s: %s", chunk_index, e)
        
        return None




    def _button(self, sender, app_data, user_data):
        """Handle Start/Stop button press.

        When the video node is in full-pipeline mode (Frames only = OFF) and
        chunking has not yet been triggered, pressing Start begins the chunking
        process and shows a progress bar.  Once chunking completes playback
        starts automatically.  In all other states the button toggles
        play/pause as before.
        """
        tag_node_name = user_data
        node_id = tag_node_name.split(':')[0]
        tag_node_input06_value_name = tag_node_name + ":" + self.TYPE_TEXT + ":Input06Value"

        frames_only_mode = dpg_get_value(tag_node_input06_value_name)
        if frames_only_mode is None:
            frames_only_mode = False

        preprocessing_status = self._preprocessing_status.get(node_id, None)
        movie_path = self._movie_filepath.get(node_id, None)

        # Full-pipeline mode: trigger chunking when no audio chunks exist yet.
        # This covers two cases:
        #   1. First Start press after selecting a video in full-pipeline mode
        #      (preprocessing_status is None).
        #   2. The video was selected while "Frames only" was checked (the
        #      default), which marks status as 'done' without creating any
        #      audio chunks.  The user then unchecks "Frames only" and presses
        #      Start – chunking must still be triggered.
        has_chunks = node_id in self._audio_chunk_paths
        needs_chunking = preprocessing_status is None or (
            preprocessing_status == 'done' and not has_chunks
        )
        if not frames_only_mode and needs_chunking and movie_path:
            self._trigger_preprocessing(node_id, tag_node_name, movie_path)
            return

        # Ignore presses while chunking is in progress
        if preprocessing_status == 'loading':
            return

        # Normal play/pause toggle
        tag_node_button_value_name = tag_node_name + ":" + self.TYPE_TEXT + ":ButtonValue"
        current_state = self._is_playing.get(node_id, False)
        self._is_playing[node_id] = not current_state

        with _dpg_lock:
            if dpg.does_item_exist(tag_node_button_value_name):
                new_label = self._stop_label if self._is_playing[node_id] else self._start_label
                dpg.configure_item(tag_node_button_value_name, label=new_label)

        logger.debug("Button clicked for %s, playing: %s", user_data, self._is_playing[node_id])

    def _trigger_preprocessing(self, node_id, tag_node_name, movie_path):
        """Start the audio chunking pipeline and show a progress bar on the node.

        Called when the user presses Start in full-pipeline mode (Frames only =
        OFF) before chunking has started.  The progress bar is updated from the
        background thread; when complete, playback starts automatically.
        """
        tag_node_button_value_name = tag_node_name + ":" + self.TYPE_TEXT + ":ButtonValue"
        tag_node_progress_bar_name = tag_node_name + ":ProgressBar"

        self._preprocessing_status[node_id] = 'loading'
        self._preprocessing_progress[node_id] = 0.0

        with _dpg_lock:
            if dpg.does_item_exist(tag_node_button_value_name):
                dpg.configure_item(tag_node_button_value_name, label=self._loading_label)
            if dpg.does_item_exist(tag_node_progress_bar_name):
                dpg.configure_item(
                    tag_node_progress_bar_name,
                    show=True,
                    default_value=0.0,
                    overlay="0 %",
                )

        def progress_callback(p):
            self._preprocessing_progress[node_id] = p
            with _dpg_lock:
                if dpg.does_item_exist(tag_node_progress_bar_name):
                    dpg.set_value(tag_node_progress_bar_name, p)
                    dpg.configure_item(
                        tag_node_progress_bar_name,
                        overlay=f"{int(p * 100)} %",
                    )

        def preprocess_thread():
            try:
                logger.info("Starting video preprocessing for node %s...", node_id)
                chunk_dur = self._opencv_setting_dict.get('audio_chunk_duration', 5.0)
                step_dur = self._opencv_setting_dict.get('audio_chunk_step', 1.0)
                self._preprocess_video(
                    node_id, movie_path,
                    chunk_duration=chunk_dur,
                    step_duration=step_dur,
                    progress_callback=progress_callback,
                )
                logger.info("Video preprocessing complete for node %s", node_id)
                self._preprocessing_status[node_id] = 'done'

                # Auto-start playback
                self._is_playing[node_id] = True
                with _dpg_lock:
                    if dpg.does_item_exist(tag_node_button_value_name):
                        dpg.configure_item(tag_node_button_value_name, label=self._stop_label)
                    if dpg.does_item_exist(tag_node_progress_bar_name):
                        dpg.configure_item(tag_node_progress_bar_name, show=False)
            except Exception as e:
                logger.error("Error during video preprocessing for node %s: %s", node_id, e)
                import traceback
                traceback.print_exc()
                self._preprocessing_status[node_id] = 'error'
                with _dpg_lock:
                    if dpg.does_item_exist(tag_node_button_value_name):
                        dpg.configure_item(tag_node_button_value_name, label=self._start_label)
                    if dpg.does_item_exist(tag_node_progress_bar_name):
                        dpg.configure_item(tag_node_progress_bar_name, show=False)
            finally:
                if node_id in self._preprocessing_threads:
                    del self._preprocessing_threads[node_id]

        thread = threading.Thread(
            target=preprocess_thread,
            daemon=True,
            name=f"VideoPreprocess-{node_id}",
        )
        self._preprocessing_threads[node_id] = thread
        thread.start()
        logger.info("Chunking started for node %s - progress bar visible", node_id)


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
        tag_node_input03_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input03Value"
        )
        tag_node_input04_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input04Value"
        )
        tag_node_input05_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input05Value"
        )
        tag_node_input06_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":Input06Value"
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
        
        # Check if preprocessing is still in progress or has failed
        preprocessing_status = self._preprocessing_status.get(str(node_id), None)
        if preprocessing_status == 'loading':
            # Still loading - don't open video capture yet, just return None
            # This prevents the video from being opened before audio preprocessing is complete
            return {"image": None, "json": None, "audio": None, "timestamp": None}
        elif preprocessing_status == 'error':
            # Preprocessing failed - clear error status and continue without audio
            # Video can still be played, just without audio chunks
            self._preprocessing_status[str(node_id)] = 'done'
            logger.warning("Video node %s: Playing without audio (preprocessing failed)", node_id)
        
        if prev_movie_path != movie_path:
            video_capture = self._video_capture.get(str(node_id), None)
            if video_capture is not None:
                video_capture.release()
            self._video_capture[str(node_id)] = cv2.VideoCapture(movie_path)
            self._prev_movie_filepath[str(node_id)] = movie_path
            self._frame_count[str(node_id)] = 0
            self._last_frame_time[str(node_id)] = None
            self._loop_elapsed_time[str(node_id)] = 0.0  # Reset loop elapsed time for new video

        video_capture = self._video_capture.get(str(node_id), None)

        loop_flag = dpg_get_value(tag_node_input02_value_name)

        skip_rate_value = dpg_get_value(tag_node_input03_value_name)
        skip_rate = int(skip_rate_value) if skip_rate_value is not None else 1
        target_fps_value = dpg_get_value(tag_node_input04_value_name)
        target_fps = int(target_fps_value) if target_fps_value is not None else 24
        playback_speed_value = dpg_get_value(tag_node_input05_value_name)
        playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0
        start_time = time.monotonic()
        frames_only_mode = dpg_get_value(tag_node_input06_value_name)
        if frames_only_mode is None:
            frames_only_mode = False

        frame = None
        # Only read frames if video is playing
        is_playing = self._is_playing.get(str(node_id), False)
        
        if video_capture is not None and is_playing:
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

        # Get audio chunk data for this frame to pass to other audio nodes.
        # In "Frames only" mode audio preprocessing is skipped entirely, so
        # the audio output is always None.
        audio_chunk_data = None
        if not frames_only_mode:
            current_frame_num = self._frame_count.get(str(node_id), 0)
            if str(node_id) in self._audio_chunk_paths:
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
        
        # Frames are ALWAYS sent via IMAGE output, never in JSON
        # JSON output contains FramePacket metadata for downstream sync nodes
        json_output = None
        if frame is not None and frame_timestamp is not None:
            pts_ms = frame_timestamp * 1000.0
            audio_chunk_index = 0
            if isinstance(audio_chunk_data, dict):
                audio_chunk_index = audio_chunk_data.get("chunk_index", 0)
                # Tag the audio dict with the video-timeline PTS so that
                # AVDriftDetector compares both streams on the same clock.
                # Audio is fetched by frame index, so it is always aligned
                # with the video frame; the apparent "drift" produced by the
                # chunk-index fallback (chunk_idx * 1000 ms) is a false
                # positive caused by target_fps != native_fps.
                if "pts_ms" not in audio_chunk_data:
                    audio_chunk_data = dict(audio_chunk_data)
                    audio_chunk_data["pts_ms"] = pts_ms
            now = time.monotonic()
            fp = FramePacket(
                frame_index=current_frame_num,
                pts_ms=pts_ms,
                audio_chunk_index=audio_chunk_index,
                image=frame,
                audio_data=audio_chunk_data,
                pipeline_entry_ts=now,
                pipeline_exit_ts=now,
            )
            json_output = fp.to_metadata()
        
        # Return frame via IMAGE output and audio chunk data via AUDIO output
        # Include the FPS-based timestamp so it can be used for synchronization
        return {
            "image": frame, 
            "json": json_output, 
            "audio": audio_chunk_data,
            "timestamp": frame_timestamp
        }

    def close(self, node_id):
        """Clean up audio chunks, temporary files, and threads when node is closed."""
        node_id_str = str(node_id)
        
        # Clean up audio chunks
        self._cleanup_audio_chunks(node_id_str)
        
        # Clean up preprocessing status
        if node_id_str in self._preprocessing_status:
            del self._preprocessing_status[node_id_str]
        
        # Note: We don't need to explicitly stop preprocessing threads as they are daemon threads
        # and will be automatically terminated when the main thread exits
        if node_id_str in self._preprocessing_threads:
            del self._preprocessing_threads[node_id_str]

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ":" + self.node_tag
        tag_node_input02_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":Input02Value"
        )
        tag_node_input03_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input03Value"
        )
        tag_node_input04_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input04Value"
        )
        tag_node_input05_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input05Value"
        )
        tag_node_input06_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":Input06Value"
        )

        pos = dpg.get_item_pos(tag_node_name)

        loop_flag = dpg_get_value(tag_node_input02_value_name)
        skip_rate_value = dpg_get_value(tag_node_input03_value_name)
        skip_rate = int(skip_rate_value) if skip_rate_value is not None else 1
        target_fps_value = dpg_get_value(tag_node_input04_value_name)
        target_fps = int(target_fps_value) if target_fps_value is not None else 24
        playback_speed_value = dpg_get_value(tag_node_input05_value_name)
        playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0
        frames_only_mode = dpg_get_value(tag_node_input06_value_name)
        if frames_only_mode is None:
            frames_only_mode = False

        setting_dict = {}
        setting_dict["ver"] = self._ver
        setting_dict["pos"] = pos
        setting_dict[tag_node_input02_value_name] = loop_flag
        setting_dict[tag_node_input03_value_name] = skip_rate
        setting_dict[tag_node_input04_value_name] = target_fps
        setting_dict[tag_node_input05_value_name] = playback_speed
        setting_dict[tag_node_input06_value_name] = frames_only_mode

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ":" + self.node_tag
        tag_node_input02_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":Input02Value"
        )
        tag_node_input03_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input03Value"
        )
        tag_node_input04_value_name = (
            tag_node_name + ":" + self.TYPE_INT + ":Input04Value"
        )
        tag_node_input05_value_name = (
            tag_node_name + ":" + self.TYPE_FLOAT + ":Input05Value"
        )
        tag_node_input06_value_name = (
            tag_node_name + ":" + self.TYPE_TEXT + ":Input06Value"
        )

        loop_flag = setting_dict[tag_node_input02_value_name]
        skip_rate = int(setting_dict[tag_node_input03_value_name])
        target_fps = int(setting_dict.get(tag_node_input04_value_name, 24))
        playback_speed = float(setting_dict.get(tag_node_input05_value_name, 1.0))
        frames_only_mode = setting_dict.get(tag_node_input06_value_name, False)

        dpg_set_value(tag_node_input02_value_name, loop_flag)
        dpg_set_value(tag_node_input03_value_name, skip_rate)
        dpg_set_value(tag_node_input04_value_name, target_fps)
        dpg_set_value(tag_node_input05_value_name, playback_speed)
        dpg_set_value(tag_node_input06_value_name, frames_only_mode)

    def _callback_file_select(self, sender, data):
        """
        Callback when a video file is selected.
        - Always displays the first frame as a preview.
        - Frames only mode (checked): skips audio preprocessing entirely.
          The video can be played immediately, frames are delivered directly.
        - Full-pipeline mode (unchecked): stores the path and resets the
          chunking state.  Audio+video splitting and chunking are deferred
          until the user presses Start
          (handled by _button → _trigger_preprocessing).
        """
        if data["file_name"] != ".":
            node_id = sender.split(":")[1]
            file_path = data["file_path_name"]

            # Cancel any in-progress preprocessing for this node
            self._preprocessing_status[node_id] = None
            self._preprocessing_progress[node_id] = 0.0
            self._is_playing[node_id] = False
            self._movie_filepath[node_id] = file_path

            tag_node_name = str(node_id) + ":" + self.node_tag
            tag_node_input06_value_name = tag_node_name + ":" + self.TYPE_TEXT + ":Input06Value"
            tag_node_output_image = tag_node_name + ":" + self.TYPE_IMAGE + ":Output01Value"
            tag_node_button_value_name = tag_node_name + ":" + self.TYPE_TEXT + ":ButtonValue"
            tag_node_progress_bar_name = tag_node_name + ":ProgressBar"

            # Load and display first frame as preview
            try:
                preview_cap = cv2.VideoCapture(file_path)
                ret, first_frame = preview_cap.read()
                preview_cap.release()

                if ret and first_frame is not None:
                    texture = self.convert_cv_to_dpg(
                        first_frame,
                        self._small_window_w,
                        self._small_window_h,
                    )
                    with _dpg_lock:
                        if dpg.does_item_exist(tag_node_output_image):
                            dpg_set_value(tag_node_output_image, texture)
                    logger.debug("Preview: First frame displayed for %s", os.path.basename(file_path))
                else:
                    logger.warning("Could not read first frame from video: %s", file_path)
            except Exception as e:
                logger.warning("Error loading preview frame: %s", e)

            frames_only_mode = dpg_get_value(tag_node_input06_value_name)
            if frames_only_mode is None:
                frames_only_mode = False

            # Reset UI to a clean "ready" state
            with _dpg_lock:
                if dpg.does_item_exist(tag_node_button_value_name):
                    dpg.configure_item(tag_node_button_value_name, label=self._start_label)
                if dpg.does_item_exist(tag_node_progress_bar_name):
                    dpg.configure_item(tag_node_progress_bar_name, show=False)

            if frames_only_mode:
                # Frames only: skip all audio preprocessing, play immediately
                self._preprocessing_status[node_id] = 'done'
                logger.info("Video selected (frames only): %s - no audio processing", file_path)
            else:
                # Full-pipeline mode: wait for the user to press Start to begin
                # audio+video splitting, chunking, and frame cadence setup
                logger.info("Video selected (full pipeline): %s - press Start to begin chunking", file_path)

