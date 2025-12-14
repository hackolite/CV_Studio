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
    _is_playing = {}  # Track playback state per node

    _min_val = 1
    _max_val = 10

    def __init__(self):
        super().__init__()  # Call parent constructor
        self._min_val = 1
        self._max_val = 1000

        self._small_window_w = 240
        self._small_window_h = 135

        self._start_label = "Start"
        self._stop_label = "Stop"
        self.node_tag = "Video"
        self.node_label = "Video"

        # Audio data storage - stores audio chunks in memory as numpy arrays
        self._audio_chunks = {}  # Store audio chunks in memory
        self._chunk_metadata = {}  # Metadata for chunk-to-frame mapping
        # Track which nodes have had their queues resized to prevent redundant resize operations on every frame
        self._queues_resized = {}
        
        # Track converted CFR videos to clean them up later
        self._converted_videos = {}

    def _safe_cleanup_temp_file(self, file_path):
        """
        Safely clean up a temporary file with error handling.
        
        Args:
            file_path: Path to the temporary file to delete
        """
        if file_path:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"[Video] Cleaned up temporary file: {file_path}")
            except (OSError, FileNotFoundError) as cleanup_error:
                logger.warning(f"[Video] Failed to clean up temporary file: {cleanup_error}")
    
    def _detect_vfr(self, video_path):
        """
        Detect if a video has variable frame rate (VFR).
        
        Args:
            video_path: Path to the video file
            
        Returns:
            True if VFR is detected, False if CFR or detection fails
        """
        try:
            # Validate video path exists and is a file
            if not video_path or not os.path.isfile(video_path):
                logger.warning(f"[Video] Invalid video path for VFR detection: {video_path}")
                return False
            
            # Verify ffprobe is available
            if not shutil.which('ffprobe'):
                logger.warning("[Video] ffprobe not found, assuming CFR")
                return False
            
            # Use ffprobe to get frame rate information
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-count_packets",
                    "-show_entries", "stream=r_frame_rate,avg_frame_rate",
                    "-of", "csv=p=0",
                    video_path
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            output = result.stdout.strip()
            if output:
                lines = output.split('\n')
                if len(lines) >= 1:
                    # Parse r_frame_rate and avg_frame_rate
                    rates = lines[0].split(',')
                    if len(rates) >= 2:
                        r_frame_rate = rates[0]
                        avg_frame_rate = rates[1]
                        
                        # Parse fractions (e.g., "30000/1001" -> 29.97)
                        def parse_frame_rate(rate_str):
                            if '/' in rate_str:
                                num, den = rate_str.split('/')
                                return float(num) / float(den)
                            return float(rate_str)
                        
                        try:
                            r_fps = parse_frame_rate(r_frame_rate)
                            avg_fps = parse_frame_rate(avg_frame_rate)
                            
                            # If r_frame_rate and avg_frame_rate differ significantly, it's likely VFR
                            # Allow small difference due to rounding (0.1 fps tolerance)
                            if abs(r_fps - avg_fps) > 0.1:
                                logger.info(f"[Video] VFR detected: r_frame_rate={r_fps:.2f}, avg_frame_rate={avg_fps:.2f}")
                                return True
                            else:
                                logger.info(f"[Video] CFR detected: frame_rate={r_fps:.2f}")
                                return False
                        except (ValueError, ZeroDivisionError) as e:
                            logger.warning(f"[Video] Failed to parse frame rates ({r_frame_rate}, {avg_frame_rate}): {e}, assuming CFR")
                            return False
            
            logger.info("[Video] Could not determine frame rate mode, assuming CFR")
            return False
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"[Video] ffprobe failed, assuming CFR: {e}")
            return False
        except Exception as e:
            logger.warning(f"[Video] VFR detection failed, assuming CFR: {e}")
            return False
    
    def _get_accurate_fps(self, video_path):
        """
        Get accurate FPS from video using ffprobe.
        
        This method uses ffprobe to get the actual average frame rate (avg_frame_rate),
        which is more reliable than OpenCV's CAP_PROP_FPS, especially for VFR videos
        that have been converted to CFR.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            float: Accurate FPS, or None if extraction fails
        """
        try:
            # Validate video path exists and is a file
            if not video_path or not os.path.isfile(video_path):
                logger.warning(f"[Video] Invalid video path for FPS extraction: {video_path}")
                return None
            
            # Verify ffprobe is available
            if not shutil.which('ffprobe'):
                logger.warning("[Video] ffprobe not found, cannot extract accurate FPS")
                return None
            
            # Use ffprobe to get avg_frame_rate (most reliable for CFR videos)
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=avg_frame_rate",
                    "-of", "csv=p=0",
                    video_path
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            output = result.stdout.strip()
            if output:
                # Parse avg_frame_rate (e.g., "24000/1001" -> 23.976)
                if '/' in output:
                    parts = output.split('/')
                    if len(parts) != 2:
                        logger.warning(f"[Video] Invalid FPS format: {output}")
                        return None
                    num, den = parts
                    den_float = float(den)
                    if den_float == 0:
                        logger.warning(f"[Video] FPS denominator is zero: {output}")
                        return None
                    fps = float(num) / den_float
                else:
                    fps = float(output)
                
                logger.info(f"[Video] Extracted accurate FPS: {fps:.3f}")
                return fps
            
            logger.warning("[Video] No FPS information from ffprobe")
            return None
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"[Video] ffprobe failed: {e}")
            return None
        except (ValueError, ZeroDivisionError) as e:
            logger.warning(f"[Video] Failed to parse FPS: {e}")
            return None
        except Exception as e:
            logger.warning(f"[Video] FPS extraction failed: {e}")
            return None
    
    def _convert_vfr_to_cfr(self, video_path, target_fps=None):
        """
        Convert a VFR (Variable Frame Rate) video to CFR (Constant Frame Rate).
        
        Args:
            video_path: Path to the VFR video file
            target_fps: Target FPS for CFR conversion. If None, uses the average FPS of the video.
            
        Returns:
            Path to the converted CFR video, or original path if conversion fails
        """
        cfr_video_path = None
        
        try:
            # Validate video path exists and is a file
            if not video_path or not os.path.isfile(video_path):
                logger.warning(f"[Video] Invalid video path for conversion: {video_path}")
                return video_path
            
            # Verify ffmpeg is available
            if not shutil.which('ffmpeg'):
                logger.warning("[Video] ffmpeg not found, cannot convert VFR to CFR")
                return video_path
            
            # Create temporary file for CFR video
            # Use the same directory as the original video to ensure we have write permissions
            video_dir = os.path.dirname(video_path)
            video_name = os.path.basename(video_path)
            # Get file extension safely
            _, ext = os.path.splitext(video_name)
            if not ext:
                ext = ".mp4"  # Default to mp4 if no extension
            
            # Create temp file in the same directory with secure naming
            # Use tempfile for secure temporary file creation
            with tempfile.NamedTemporaryFile(
                suffix=f"_cfr{ext}",
                prefix="cvstudio_",
                dir=video_dir if video_dir else None,
                delete=False
            ) as tmp_video:
                cfr_video_path = tmp_video.name
            
            logger.info(f"[Video] Converting VFR to CFR: {video_path} -> {cfr_video_path}")
            
            # Build ffmpeg command for VFR to CFR conversion
            # Key points:
            # 1. -vsync cfr: Force constant frame rate by duplicating/dropping frames
            # 2. -r: Set output frame rate (if target_fps specified)
            # 3. -c:v libx264: Re-encode video (necessary for proper CFR)
            # 4. -preset fast: Balance between speed and quality
            # 5. -crf 18: High quality (lower CRF = higher quality, 18 is visually lossless)
            # 6. -c:a copy: Copy audio stream without re-encoding
            
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vsync", "cfr",  # Force constant frame rate
            ]
            
            # Add target FPS if specified
            if target_fps is not None:
                ffmpeg_cmd.extend(["-r", str(target_fps)])
            
            ffmpeg_cmd.extend([
                "-c:v", "libx264",      # Video codec
                "-preset", "fast",      # Encoding speed
                "-crf", "18",           # Quality (18 = visually lossless)
                "-c:a", "copy",         # Copy audio without re-encoding
                "-y",                   # Overwrite output file
                cfr_video_path
            ])
            
            logger.debug(f"[Video] Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
            
            # Run ffmpeg conversion
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Verify the converted file exists and has content
            if os.path.exists(cfr_video_path) and os.path.getsize(cfr_video_path) > 0:
                logger.info(f"[Video] VFR to CFR conversion successful: {cfr_video_path}")
                return cfr_video_path
            else:
                logger.error("[Video] CFR video file is empty or doesn't exist")
                if os.path.exists(cfr_video_path):
                    os.unlink(cfr_video_path)
                return video_path
                
        except subprocess.CalledProcessError as e:
            logger.error(f"[Video] ffmpeg conversion failed: {e.stderr if e.stderr else str(e)}")
            # Clean up failed conversion file
            self._safe_cleanup_temp_file(cfr_video_path)
            return video_path
        except Exception as e:
            logger.error(f"[Video] VFR to CFR conversion failed: {e}", exc_info=True)
            # Clean up any partial conversion file
            self._safe_cleanup_temp_file(cfr_video_path)
            return video_path

    def _preprocess_video(self, node_id, movie_path, target_fps=24):
        """
        Pre-process video by extracting and chunking audio into memory.
        
        This method:
        0. Detects VFR and converts to CFR if necessary (NEW)
        1. Extracts video metadata (FPS, frame count) using OpenCV
        2. Extracts audio using ffmpeg (WAV used temporarily during extraction only)
        3. Chunks audio into per-frame segments based on FPS and stores all chunks in memory as numpy arrays
        4. Stores metadata for frame-to-chunk mapping
        5. Dynamically resizes queues based on FPS (4 seconds = 4 * fps)
        
        Note: Each audio chunk corresponds to exactly ONE frame for perfect synchronization.
        Audio chunk size = sample_rate / fps samples per frame.
        
        Args:
            node_id: Node identifier
            movie_path: Path to video file
            target_fps: Target FPS for playback (default: 24)
        """
        if not movie_path or not os.path.exists(movie_path):
            logger.warning(f"[Video] Video file not found: {movie_path}")
            return
        
        logger.info(f"[Video] Pre-processing video: {movie_path}")
        
        # Clean up any previous chunks for this node
        self._cleanup_audio_chunks(node_id)
        
        # Step 0: Detect VFR and convert to CFR if necessary
        # This is critical for proper audio-video synchronization
        is_vfr = self._detect_vfr(movie_path)
        if is_vfr:
            logger.info("[Video] VFR detected, converting to CFR...")
            # Convert using target_fps to ensure consistent frame rate
            cfr_video_path = self._convert_vfr_to_cfr(movie_path, target_fps=target_fps)
            
            # If conversion succeeded, use the CFR video for the rest of preprocessing
            if cfr_video_path != movie_path:
                logger.info(f"[Video] Using CFR video: {cfr_video_path}")
                # Store the converted video path for cleanup later
                old_converted = self._converted_videos.get(node_id)
                if old_converted and os.path.exists(old_converted):
                    try:
                        os.unlink(old_converted)
                        logger.debug(f"[Video] Cleaned up old CFR video: {old_converted}")
                    except Exception as e:
                        logger.warning(f"[Video] Failed to clean up old CFR video: {e}")
                
                self._converted_videos[node_id] = cfr_video_path
                movie_path = cfr_video_path
            else:
                logger.warning("[Video] VFR to CFR conversion failed, using original video")
        else:
            logger.info("[Video] CFR video detected, no conversion needed")
        
        try:
            # Step 1: Extract video metadata
            # CRITICAL FIX: Use ffprobe to get accurate FPS instead of OpenCV
            # OpenCV's CAP_PROP_FPS is unreliable for VFR videos and can cause:
            # - Incorrect audio chunking (wrong samples_per_frame)
            # - Wrong reconstruction FPS in VideoWriter
            # - Audio/video desynchronization and audio distortion
            logger.debug("[Video] Extracting video metadata...")
            
            # Get accurate FPS using ffprobe (reliable for CFR videos)
            fps = self._get_accurate_fps(movie_path)
            
            # Fallback to OpenCV if ffprobe fails
            cap = cv2.VideoCapture(movie_path)
            if fps is None or fps <= 0:
                fps = cap.get(cv2.CAP_PROP_FPS)
                logger.warning(f"[Video] Using OpenCV FPS (ffprobe failed): {fps}")
                if fps <= 0:
                    fps = target_fps  # Ultimate fallback to target_fps
                    logger.warning(f"[Video] Using target_fps as fallback: {fps}")
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            logger.info(f"[Video] Metadata: FPS={fps:.3f}, Frames={frame_count}")
            
            # Step 2: Extract audio using ffmpeg directly to WAV (faster than librosa)
            logger.debug("[Video] Extracting audio with ffmpeg...")
            
            # Create temporary WAV file for full audio extraction
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                tmp_audio_path = tmp_audio.name
            
            try:
                # Use ffmpeg to extract audio as WAV - most efficient for spectrogram conversion
                # Audio is resampled to 44100 Hz for consistency across the pipeline
                # This ensures sample rate (samples per second in Hz) is uniform for:
                # - Audio chunk sizing: chunk_samples = chunk_duration * sample_rate
                # - Queue population frequency throughout workflow (input → concat → videowriter)
                subprocess.run(
                    [
                        "ffmpeg",
                        "-i", movie_path,
                        "-vn",  # No video
                        "-acodec", "pcm_s16le",  # WAV codec
                        "-ar", "44100",  # Sample rate: 44100 Hz
                        "-ac", "1",  # Mono
                        "-y", tmp_audio_path,
                    ],
                    check=True,
                    capture_output=True,
                )
                
                # Load audio to get samples and sample rate (should be 44100 Hz after resampling)
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
            
            # Step 3: Chunk audio by FPS - one audio chunk per frame
            # Calculate samples per frame based on sample rate and FPS
            # Formula: chunk_samples = sample_rate / fps
            # Example: 44100 Hz / 24 fps = 1837.5 samples per frame
            # This ensures each audio chunk corresponds to exactly ONE video frame
            logger.debug(f"[Video] Chunking audio by FPS: {fps} fps, {sr} Hz")
            
            # Calculate samples per frame (one chunk = one frame worth of audio)
            # Keep as float to maintain precision and avoid cumulative drift
            samples_per_frame = sr / fps
            
            audio_chunks = []
            chunk_start_times = []
            chunk_idx = 0
            
            # Create one audio chunk per frame
            # Use frame index to calculate exact boundaries, avoiding cumulative rounding errors
            # Use frame_count from video metadata to ensure exact number of chunks
            total_frames = frame_count
            
            for frame_idx in range(total_frames):
                # Calculate exact start and end positions for this frame using fractional precision
                # This ensures no cumulative drift over many frames
                start_float = frame_idx * samples_per_frame
                end_float = (frame_idx + 1) * samples_per_frame
                
                # Use round() instead of int() to avoid gaps/overlaps in audio
                # This ensures seamless audio continuity without discontinuities that cause graininess
                start = round(start_float)
                end = round(end_float)
                
                # Extract chunk
                # Last chunk handling: if we're at the end or past the audio array bounds
                if end >= len(y) or frame_idx == total_frames - 1:
                    # Last chunk: extract remaining audio
                    chunk = y[start:]
                    # Pad with zeros to maintain consistent chunk size
                    expected_size = round(samples_per_frame)
                    padding_needed = expected_size - len(chunk)
                    if padding_needed > 0:
                        chunk = np.pad(chunk, (0, padding_needed), mode='constant', constant_values=0)
                else:
                    chunk = y[start:end]
                
                # Store chunk in memory as numpy array
                audio_chunks.append(chunk)
                chunk_start_times.append(start / sr)
                chunk_idx += 1
            
            # Store all audio chunks in memory
            self._audio_chunks[node_id] = audio_chunks
            
            # Verify all chunks have consistent size (allowing for last chunk)
            expected_chunk_size = round(samples_per_frame)
            if len(audio_chunks) > 0:
                first_size = len(audio_chunks[0])
                last_size = len(audio_chunks[-1])
                
                # Check first chunk (should be expected size or expected size + 1 due to rounding)
                # Allow ±1 sample variance due to rounding of fractional samples_per_frame
                if first_size < expected_chunk_size or first_size > expected_chunk_size + 1:
                    logger.warning(f"[Video] First chunk size unexpected - expected: {expected_chunk_size}, got: {first_size}")
                
                # Last chunk should be padded to expected size
                if last_size != expected_chunk_size:
                    logger.warning(f"[Video] Last chunk size unexpected - expected: {expected_chunk_size} (padded), got: {last_size}")
                    
            logger.info(f"[Video] Created {len(audio_chunks)} audio chunks (1 per frame) with ~{expected_chunk_size} samples each")
            
            # Step 4: Calculate dynamic queue sizes
            # IMPORTANT: Audio and video queues must have the SAME size for synchronization
            # Queue size = 4 seconds worth of frames = 4 * fps
            # This ensures:
            # - Each audio chunk corresponds to exactly one frame
            # - Audio queue size = Image queue size = 4 * fps
            # - Consistent queue population frequency throughout the workflow:
            #   input/video → concat [audio, image] → videowriter
            # Example: at 24 fps, both queues = 4 * 24 = 96 frames/chunks
            queue_size_seconds = 4  # 4 seconds of buffer
            image_queue_size = int(queue_size_seconds * fps)
            audio_queue_size = int(queue_size_seconds * fps)  # Same as image queue
            
            logger.info(f"[Video] Calculated queue sizes: Image={image_queue_size}, Audio={audio_queue_size} (both = 4 * {fps} fps)")
            
            # Step 5: Store metadata
            self._chunk_metadata[node_id] = {
                'fps': fps,
                'sr': sr,
                'samples_per_frame': samples_per_frame,  # NEW: samples per frame for FPS-based chunking
                'chunk_start_times': chunk_start_times,
                'num_frames': frame_count,
                'num_chunks': len(audio_chunks),
                'image_queue_size': image_queue_size,
                'audio_queue_size': audio_queue_size,
            }
            
            logger.info(f"[Video] Pre-processing complete: Frames={frame_count}, Audio Chunks={len(audio_chunks)} (1 per frame), FPS={fps}, Samples/Frame={samples_per_frame:.2f}")
            
        except Exception as e:
            logger.error(f"[Video] Failed to pre-process video: {e}", exc_info=True)
    
    def _cleanup_audio_chunks(self, node_id):
        """
        Clean up in-memory audio chunks and converted CFR videos for a node.
        
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
        
        # Clean up converted CFR video file
        if node_id in self._converted_videos:
            cfr_video_path = self._converted_videos[node_id]
            if os.path.exists(cfr_video_path):
                try:
                    os.unlink(cfr_video_path)
                    logger.debug(f"[Video] Cleaned up CFR video: {cfr_video_path}")
                except Exception as e:
                    logger.warning(f"[Video] Failed to clean up CFR video: {e}")
            del self._converted_videos[node_id]
    
    def _get_audio_chunk_for_frame(self, node_id, frame_number):
        """
        Get the audio chunk data for a specific frame number from memory.
        
        With FPS-based chunking, chunk_index = frame_number - 1 (0-indexed chunks).
        Each audio chunk corresponds to exactly ONE frame.
        
        Args:
            node_id: Node identifier
            frame_number: Current frame number (1-indexed)
            
        Returns:
            Dictionary with 'data' (numpy array) and 'sample_rate' (int), or None if not available
        """
        if node_id not in self._chunk_metadata or node_id not in self._audio_chunks:
            return None
        
        metadata = self._chunk_metadata[node_id]
        sr = metadata['sr']
        
        # With FPS-based chunking, chunk index directly corresponds to frame number
        # frame_number is 1-indexed (first frame = 1), but chunks are 0-indexed
        chunk_index = frame_number - 1
        
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
        """Toggle playback state when Start/Stop button is clicked"""
        node_id = user_data.split(":")[0]
        
        # Toggle playback state
        is_playing = self._is_playing.get(node_id, False)
        self._is_playing[node_id] = not is_playing
        
        # Update button label
        if self._is_playing[node_id]:
            dpg.set_item_label(sender, self._stop_label)
            logger.info(f"[Video] Started playback for node {node_id}")
        else:
            dpg.set_item_label(sender, self._start_label)
            logger.info(f"[Video] Stopped playback for node {node_id}")

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
            
            # Use converted CFR video if available, otherwise use original
            actual_movie_path = self._converted_videos.get(str(node_id), movie_path)
            if actual_movie_path and os.path.exists(actual_movie_path):
                self._video_capture[str(node_id)] = cv2.VideoCapture(actual_movie_path)
                logger.debug(f"[Video] Opened video capture: {actual_movie_path}")
            elif movie_path and os.path.exists(movie_path):
                # Fallback to original if CFR doesn't exist
                self._video_capture[str(node_id)] = cv2.VideoCapture(movie_path)
                logger.debug(f"[Video] Opened video capture: {movie_path}")
            
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
        
        # Check if playback is active (video should only play when Start button is clicked)
        is_playing = self._is_playing.get(str(node_id), False)
        
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
        # Only read frames if playback is active (Start button has been clicked)
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
        
        # Get metadata to pass through pipeline
        metadata = {}
        if str(node_id) in self._chunk_metadata:
            chunk_meta = self._chunk_metadata[str(node_id)]
            video_fps = chunk_meta.get('fps', 30.0)  # Actual video FPS
            metadata = {
                'target_fps': target_fps,  # FPS from slider (authoritative for output)
                'samples_per_frame': chunk_meta.get('samples_per_frame', 44100 / video_fps),  # NEW: samples per frame (use video_fps, not target_fps)
                'video_fps': video_fps,  # Actual video FPS
                'sample_rate': chunk_meta.get('sr', 44100),
                'chunking_mode': 'fps_based'  # NEW: indicates FPS-based chunking (1 chunk per frame)
            }
        
        # Return frame via IMAGE output and audio chunk data via AUDIO output
        # Include the FPS-based timestamp so it can be used for synchronization
        # Include metadata about FPS and chunk settings for downstream nodes
        return {
            "image": frame, 
            "json": None, 
            "audio": audio_chunk_data,
            "timestamp": frame_timestamp,
            "metadata": metadata  # Pass FPS and chunk info to VideoWriter
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

        pos = dpg.get_item_pos(tag_node_name)

        loop_flag = dpg_get_value(tag_node_input02_value_name)
        target_fps_value = dpg_get_value(tag_node_input04_value_name)
        target_fps = int(target_fps_value) if target_fps_value is not None else 24
        playback_speed_value = dpg_get_value(tag_node_input05_value_name)
        playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0

        setting_dict = {}
        setting_dict["ver"] = self._ver
        setting_dict["pos"] = pos
        setting_dict[tag_node_input02_value_name] = loop_flag
        setting_dict[tag_node_input04_value_name] = target_fps
        setting_dict[tag_node_input05_value_name] = playback_speed

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

        loop_flag = setting_dict[tag_node_input02_value_name]
        target_fps = int(setting_dict.get(tag_node_input04_value_name, 24))
        playback_speed = float(setting_dict.get(tag_node_input05_value_name, 1.0))

        dpg_set_value(tag_node_input02_value_name, loop_flag)
        dpg_set_value(tag_node_input04_value_name, target_fps)
        dpg_set_value(tag_node_input05_value_name, playback_speed)

    def _callback_file_select(self, sender, data):
        if data["file_name"] != ".":
            node_id = sender.split(":")[1]
            self._movie_filepath[node_id] = data["file_path_name"]
            tag_node_name = str(node_id) + ":" + self.node_tag
            
            # Get target FPS from slider
            tag_node_input04_value_name = (
                tag_node_name + ":" + self.TYPE_INT + ":Input04Value"
            )
            target_fps_value = dpg_get_value(tag_node_input04_value_name)
            target_fps = int(target_fps_value) if target_fps_value is not None else 24
            
            # Preprocess video (chunk size and queue size are calculated automatically based on FPS)
            self._preprocess_video(
                node_id, 
                data["file_path_name"], 
                target_fps=target_fps
            )
