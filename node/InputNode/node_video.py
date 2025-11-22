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

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


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
                )  # Light yellow on hover
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255)
                )  # Darker yellow on press

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

        # Audio data storage
        self._audio_chunks = {}  # Store audio chunks
        self._chunk_metadata = {}  # Metadata for chunk-to-frame mapping

    def _preprocess_video(self, node_id, movie_path, chunk_duration=5.0, step_duration=1.0):
        """
        Pre-process video by extracting and chunking audio.
        
        This method:
        1. Extracts video metadata (FPS, frame count) using OpenCV
        2. Extracts audio using librosa
        3. Chunks audio into segments (chunk_duration with step_duration overlap)
        4. Stores metadata for frame-to-chunk mapping
        
        Args:
            node_id: Node identifier
            movie_path: Path to video file
            chunk_duration: Duration of each audio chunk in seconds (default: 5.0)
            step_duration: Step size between chunks in seconds (default: 1.0)
        """
        if not movie_path or not os.path.exists(movie_path):
            print(f"Video file not found: {movie_path}")
            return
        
        print(f"🎬 Pre-processing video: {movie_path}")
        
        try:
            # Step 1: Extract video metadata only (not frames to avoid memory issues)
            print("📹 Extracting video metadata...")
            cap = cv2.VideoCapture(movie_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # Default fallback
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            print(f"✅ Video metadata extracted (FPS: {fps}, Frames: {frame_count})")
            
            # Step 2: Extract audio
            print("🎵 Extracting audio...")
            try:
                y, sr = librosa.load(movie_path, sr=None)
            except Exception as e:
                print(f"⚠️ Direct audio load failed, trying ffmpeg extraction: {e}")
                # Fallback: extract audio via ffmpeg
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                    tmp_audio_path = tmp_audio.name
                
                try:
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-i", movie_path,
                            "-vn",
                            "-acodec", "pcm_s16le",
                            "-ar", "22050",
                            "-ac", "1",
                            "-y", tmp_audio_path,
                        ],
                        check=True,
                        capture_output=True,
                    )
                    y, sr = librosa.load(tmp_audio_path, sr=22050)
                finally:
                    if os.path.exists(tmp_audio_path):
                        os.unlink(tmp_audio_path)
            
            print(f"✅ Audio extracted (SR: {sr} Hz, Duration: {len(y)/sr:.2f}s)")
            
            # Step 2.5: Save extracted audio as MP3 file
            try:
                # Create audio filename based on video path
                video_dir = os.path.dirname(movie_path)
                video_basename = os.path.splitext(os.path.basename(movie_path))[0]
                audio_mp3_path = os.path.join(video_dir, f"{video_basename}_audio.mp3")
                
                # Use ffmpeg to convert the audio array to MP3
                # First save as temporary WAV, then convert to MP3
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                    tmp_wav_path = tmp_wav.name
                    sf.write(tmp_wav_path, y, sr)
                
                try:
                    # Convert WAV to MP3 using ffmpeg
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-i", tmp_wav_path,
                            "-codec:a", "libmp3lame",
                            "-qscale:a", "2",  # High quality MP3
                            "-y", audio_mp3_path,
                        ],
                        check=True,
                        capture_output=True,
                    )
                    print(f"💾 Audio saved as MP3: {audio_mp3_path}")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Failed to convert to MP3, saving as WAV instead: {e}")
                    # Fallback: keep the WAV file
                    audio_wav_path = os.path.join(video_dir, f"{video_basename}_audio.wav")
                    sf.write(audio_wav_path, y, sr)
                    print(f"💾 Audio saved as WAV: {audio_wav_path}")
                finally:
                    # Clean up temporary WAV file
                    if os.path.exists(tmp_wav_path):
                        os.unlink(tmp_wav_path)
                        
            except Exception as e:
                print(f"⚠️ Failed to save audio file: {e}")
            
            # Step 3: Chunk audio with sliding window
            print(f"✂️ Chunking audio (chunk: {chunk_duration}s, step: {step_duration}s)...")
            chunk_samples = int(chunk_duration * sr)
            step_samples = int(step_duration * sr)
            
            audio_chunks = []
            chunk_start_times = []
            start = 0
            chunk_idx = 0
            
            while (start + chunk_samples) <= len(y):
                end = start + chunk_samples
                chunk = y[start:end]
                audio_chunks.append(chunk)
                chunk_start_times.append(start / sr)
                chunk_idx += 1
                start += step_samples
            
            self._audio_chunks[node_id] = audio_chunks
            print(f"✅ Created {len(audio_chunks)} audio chunks")
            
            # Step 4: Store metadata
            self._chunk_metadata[node_id] = {
                'fps': fps,
                'sr': sr,
                'chunk_duration': chunk_duration,
                'step_duration': step_duration,
                'chunk_start_times': chunk_start_times,
                'num_frames': frame_count,
                'num_chunks': len(audio_chunks),
            }
            
            print(f"🎉 Pre-processing complete!")
            print(f"   Frames: {frame_count}, Chunks: {len(audio_chunks)}, FPS: {fps}")
            
        except Exception as e:
            print(f"❌ Failed to pre-process video: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_audio_chunk_for_frame(self, node_id, frame_number):
        """
        Get the audio chunk data for a specific frame number.
        
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
        chunk_index = max(0, min(chunk_index, len(self._audio_chunks[node_id]) - 1))
        
        # Return audio chunk in the format expected by audio processing nodes
        return {
            'data': self._audio_chunks[node_id][chunk_index],
            'sample_rate': sr
        }




    def _button(self, sender, app_data, user_data):
        print(f"Button clicked for {user_data}")

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

        video_capture = self._video_capture.get(str(node_id), None)

        loop_flag = dpg_get_value(tag_node_input02_value_name)

        skip_rate_value = dpg_get_value(tag_node_input03_value_name)
        skip_rate = int(skip_rate_value) if skip_rate_value is not None else 1
        target_fps_value = dpg_get_value(tag_node_input04_value_name)
        target_fps = int(target_fps_value) if target_fps_value is not None else 24
        playback_speed_value = dpg_get_value(tag_node_input05_value_name)
        playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0

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

        # Return frame via IMAGE output and audio chunk data via AUDIO output
        return {"image": frame, "json": None, "audio": audio_chunk_data}

    def close(self, node_id):
        pass

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

        pos = dpg.get_item_pos(tag_node_name)

        loop_flag = dpg_get_value(tag_node_input02_value_name)
        skip_rate_value = dpg_get_value(tag_node_input03_value_name)
        skip_rate = int(skip_rate_value) if skip_rate_value is not None else 1
        target_fps_value = dpg_get_value(tag_node_input04_value_name)
        target_fps = int(target_fps_value) if target_fps_value is not None else 24
        playback_speed_value = dpg_get_value(tag_node_input05_value_name)
        playback_speed = float(playback_speed_value) if playback_speed_value is not None else 1.0

        setting_dict = {}
        setting_dict["ver"] = self._ver
        setting_dict["pos"] = pos
        setting_dict[tag_node_input02_value_name] = loop_flag
        setting_dict[tag_node_input03_value_name] = skip_rate
        setting_dict[tag_node_input04_value_name] = target_fps
        setting_dict[tag_node_input05_value_name] = playback_speed

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

        loop_flag = setting_dict[tag_node_input02_value_name]
        skip_rate = int(setting_dict[tag_node_input03_value_name])
        target_fps = int(setting_dict.get(tag_node_input04_value_name, 24))
        playback_speed = float(setting_dict.get(tag_node_input05_value_name, 1.0))

        dpg_set_value(tag_node_input02_value_name, loop_flag)
        dpg_set_value(tag_node_input03_value_name, skip_rate)
        dpg_set_value(tag_node_input04_value_name, target_fps)
        dpg_set_value(tag_node_input05_value_name, playback_speed)

    def _callback_file_select(self, sender, data):
        if data["file_name"] != ".":
            node_id = sender.split(":")[1]
            self._movie_filepath[node_id] = data["file_path_name"]
            # Preprocess video and extract audio chunks
            self._preprocess_video(node_id, data["file_path_name"])
