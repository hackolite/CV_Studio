#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import cv2
import numpy as np
from numpy.lib import stride_tricks
import dearpygui.dearpygui as dpg
import librosa
import matplotlib.cm
import matplotlib
import subprocess
import tempfile
import os

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
from node.InputNode.spectrogram_utils import apply_colormap_to_spectrogram

# Spectrogram processing constants
# Minimum amplitude threshold to prevent log10(0) which causes -inf values
SPECTROGRAM_EPSILON = 1e-10
# Default colormap for spectrograms (configurable)
DEFAULT_SPECTROGRAM_COLORMAP = 'INFERNO'


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

        node.tag_node_output03_name = (
            node.tag_node_name + ":" + node.TYPE_AUDIO + ":Output03"
        )
        node.tag_node_output03_value_name = (
            node.tag_node_name + ":" + node.TYPE_AUDIO + ":Output03Value"
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

        node.tag_node_output_float_name = (
            node.tag_node_name + ":" + node.TYPE_FLOAT + ":OutputFloat"
        )
        node.tag_node_output_float_value_name = (
            node.tag_node_name + ":" + node.TYPE_FLOAT + ":OutputFloatValue"
        )

        # Spectrogram tags
        # node.tag_node_spectrogram_name = node.tag_node_name + ":Spectrogram"
        # node.tag_node_spectrogram_value_name = node.tag_node_name + ":SpectrogramValue"
        node.tag_node_spectrogram_toggle_name = (
            node.tag_node_name + ":SpectrogramToggle"
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
            # Add spectrogram texture (initially black)
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output03_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(
                    dpg.mvThemeCol_Button, (255, 255, 0, 255)
                )  # Yellow background
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonHovered, (255, 255, 128, 255)
                )  # Light yellow on hover
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonActive, (255, 255, 64, 255)
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

            # Spectrogram toggle
            with dpg.node_attribute(
                tag=node.tag_node_output03_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_checkbox(
                    label="Show Spectrogram",
                    tag=node.tag_node_spectrogram_toggle_name,
                    default_value=False,
                )
                dpg.add_image(node.tag_node_output03_value_name)

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

            # with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
            #    btn = add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)

            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = add_yellow_disabled_button(
                    "JSON", node.tag_node_output_json_value_name
                )

            with dpg.node_attribute(
                tag=node.tag_node_output_float_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn = add_yellow_disabled_button(
                    "Float", node.tag_node_output_float_value_name
                )

        return node


def fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning):
    """
    Perform Short-Time Fourier Transform with windowing and overlap.
    
    Args:
        sig: Input signal
        frameSize: Size of each frame (window)
        overlapFac: Overlap factor (0.5 = 50% overlap)
        window: Window function to apply
    
    Returns:
        STFT matrix (complex values)
    """
    win = window(frameSize)
    hopSize = int(frameSize - np.floor(overlapFac * frameSize))
    samples = np.append(np.zeros(int(np.floor(frameSize/2.0))), sig)
    cols = np.ceil((len(samples) - frameSize) / float(hopSize)) + 1
    samples = np.append(samples, np.zeros(frameSize))
    frames = stride_tricks.as_strided(
        samples,
        shape=(int(cols), frameSize),
        strides=(samples.strides[0]*hopSize, samples.strides[0])
    ).copy()
    frames *= win
    return np.fft.rfft(frames)


def make_logscale(spec, sr=22050, factor=20.):
    """
    Apply logarithmic scaling to frequency bins for better low-frequency resolution.
    
    Args:
        spec: Spectrogram array (time x frequency)
        sr: Sample rate (default 22050 to match audio loading)
        factor: Scaling factor (higher = more emphasis on low frequencies)
    
    Returns:
        (newspec, freqs): Rescaled spectrogram and corresponding frequencies
    """
    timebins, freqbins = np.shape(spec)
    scale = np.linspace(0, 1, freqbins) ** factor
    scale *= (freqbins-1)/max(scale)
    scale = np.unique(np.round(scale))

    # Use same dtype as input for memory efficiency
    newspec = np.zeros([timebins, len(scale)], dtype=spec.dtype)
    for i in range(len(scale)):
        start = int(scale[i])
        end = int(scale[i+1]) if i < len(scale)-1 else freqbins
        newspec[:, i] = np.sum(spec[:, start:end], axis=1)

    allfreqs = np.abs(np.fft.fftfreq(freqbins*2, 1./sr)[:freqbins+1])
    freqs = [np.mean(allfreqs[int(scale[i]):int(scale[i+1])])
             if i < len(scale)-1 else np.mean(allfreqs[int(scale[i]):])
             for i in range(len(scale))]
    return newspec, freqs


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
    _current_block = {}  # Track current 5-second block for each node
    _block_start_frame = {}  # Starting frame of current block

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

        # Spectrogram storage
        self._spectrogram_texture = {}
        self._spectrogram_array = {}
        self._spectrogram_params = {}
        self._spectrogram_meta = {}
        
        # Spectrogram colormap configuration
        # Can be changed to 'VIRIDIS', 'JET', 'MAGMA', 'PLASMA', etc.
        self._spectrogram_colormap = DEFAULT_SPECTROGRAM_COLORMAP

    # def convert_cv_to_dpg(self, cv_img, w, h):
    #    return (np.zeros(w * h * 3, dtype=np.float32)).tobytes()

    def _prepare_spectrogram(self, node_id, movie_path, fmin=None, fmax=None):
        """
        Extract audio and compute spectrogram EXACTLY like training code.
        Uses matplotlib to generate the same visual output.
        """
        if not movie_path or not os.path.exists(movie_path):
            print(f"Video file not found: {movie_path}")
            return

        try:
            # Extract audio using ffmpeg
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                tmp_audio_path = tmp_audio.name

            try:
                subprocess.run([
                    "ffmpeg", "-i", movie_path,
                    "-vn", "-acodec", "pcm_s16le",
                    "-y", tmp_audio_path,
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # Read audio with scipy (SAME as training code) - preserves native sample rate
                import scipy.io.wavfile as wav
                samplerate, samples = wav.read(tmp_audio_path)
                
                # STFT parameters (SAME as training)
                binsize = 2**10
                
                # Compute STFT (SAME as training)
                s = fourier_transformation(samples, binsize)
                sshow, freq = make_logscale(s, factor=1.0, sr=samplerate)
                ims = 20. * np.log10(np.abs(sshow) / 10e-6)
                
                # Create matplotlib figure (SAME as training)
                import matplotlib
                matplotlib.use('Agg')  # Non-interactive backend
                import matplotlib.pyplot as plt
                
                timebins, freqbins = np.shape(ims)
                
                # Same figure size and colormap as training
                fig = plt.figure(figsize=(15, 7.5))
                plt.imshow(np.transpose(ims), origin="lower", aspect="auto", 
                          cmap="jet", interpolation="none")
                
                # Same axes as training
                xlocs = np.float32(np.linspace(0, timebins-1, 5))
                plt.xticks(xlocs, ["%.02f" % l for l in 
                                  ((xlocs*len(samples)/timebins)+(0.5*binsize))/samplerate])
                ylocs = np.int16(np.round(np.linspace(0, freqbins-1, 10)))
                plt.yticks(ylocs, ["%.02f" % freq[i] for i in ylocs])
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                    tmp_img_path = tmp_img.name
                
                plt.savefig(tmp_img_path, bbox_inches="tight")
                plt.close(fig)
                
                # Read the generated image
                S_bgr = cv2.imread(tmp_img_path)
                
                # Clean up temp image
                os.unlink(tmp_img_path)
                
            finally:
                # Clean up temp audio
                if os.path.exists(tmp_audio_path):
                    os.unlink(tmp_audio_path)

            # Store the spectrogram array
            self._spectrogram_array[node_id] = S_bgr

            # Get video metadata
            video_capture = self._video_capture.get(node_id, None)
            fps = 30.0
            if video_capture is not None:
                fps = video_capture.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 30.0

            # Store metadata for audio sync
            self._spectrogram_meta[node_id] = {
                "y": samples,
                "sr": samplerate,
                "hop_length": binsize // 2,
                "fps": fps,
            }

            print(f"Spectrogram prepared for node {node_id} (sr={samplerate}Hz)")

        except Exception as e:
            print(f"Failed to prepare spectrogram: {e}")
            import traceback
            traceback.print_exc()

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
            self._current_block[str(node_id)] = 0
            self._block_start_frame[str(node_id)] = 0

        video_capture = self._video_capture.get(str(node_id), None)

        loop_flag = dpg_get_value(tag_node_input02_value_name)

        skip_rate = int(dpg_get_value(tag_node_input03_value_name))
        target_fps = int(dpg_get_value(tag_node_input04_value_name))
        playback_speed = float(dpg_get_value(tag_node_input05_value_name))

        if video_capture is not None and use_pref_counter:
            start_time = time.monotonic()

        frame = None
        spectrogram_bgr = None
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
                            self._current_block[str(node_id)] = 0
                            self._block_start_frame[str(node_id)] = 0
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
                
                # Update 5-second block tracking
                # Calculate which 5-second block we're in based on frame count and FPS
                if video_capture is not None:
                    fps = video_capture.get(cv2.CAP_PROP_FPS)
                    if fps > 0:
                        current_frame = self._frame_count[str(node_id)]
                        frames_per_5s = int(fps * 5)  # Number of frames in 5 seconds
                        current_block = current_frame // frames_per_5s
                        
                        # Check if we've moved to a new block
                        prev_block = self._current_block.get(str(node_id), 0)
                        if current_block != prev_block:
                            self._current_block[str(node_id)] = current_block
                            self._block_start_frame[str(node_id)] = current_frame
                            print(f"Node {node_id}: Starting 5-second block {current_block} at frame {current_frame}")


        if video_capture is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + "ms")

        if frame is not None:
            # Resize frame to 224x224 for compatibility with DL models
            # This is the frame that will be passed to downstream nodes
            frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)
            
            texture = self.convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(tag_node_output_image, texture)

        # Update spectrogram display if toggle is enabled
        tag_node_spectrogram_toggle = tag_node_name + ":SpectrogramToggle"
        # tag_node_spectrogram_value = tag_node_name + ":SpectrogramValue"

        if dpg.does_item_exist(tag_node_spectrogram_toggle):
            show_spectrogram = dpg_get_value(tag_node_spectrogram_toggle)
            if show_spectrogram and str(node_id) in self._spectrogram_array:
                # Get the original spectrogram array
                full_spectrogram = self._spectrogram_array[str(node_id)]

                # Calculate current playback position
                if str(node_id) in self._spectrogram_meta and video_capture is not None:
                    meta = self._spectrogram_meta[str(node_id)]
                    fps = meta["fps"]
                    sr = meta["sr"]
                    hop_length = meta["hop_length"]
                    
                    # Get current frame
                    current_frame = self._frame_count.get(str(node_id), 0)
                    
                    # Calculate current TIME in seconds
                    current_time = current_frame / fps if fps > 0 else 0
                    
                    # Calculate which 5-second CHUNK we're in (like training code)
                    # chunk_duration = 5.0 seconds
                    # step_duration = 0.25 seconds
                    chunk_index = int(current_time / 0.25)  # Chunk every 0.25s
                    chunk_start_time = chunk_index * 0.25
                    chunk_end_time = chunk_start_time + 5.0
                    
                    # Convert to spectrogram columns
                    start_sample = int(chunk_start_time * sr)
                    end_sample = int(chunk_end_time * sr)
                    
                    start_col = int(start_sample / hop_length)
                    end_col = int(end_sample / hop_length)
                    
                    # Extract chunk window
                    start_col = max(0, start_col)
                    end_col = min(full_spectrogram.shape[1], end_col)
                    
                    spectrogram_chunk = full_spectrogram[:, start_col:end_col].copy()
                    
                    # Resize to 640x640 (same as training imgsz=640)
                    spectrogram_chunk = cv2.resize(spectrogram_chunk, (640, 640), 
                                                  interpolation=cv2.INTER_AREA)
                    
                    # Draw indicator at current position
                    relative_time = current_time - chunk_start_time
                    indicator_x = int((relative_time / 5.0) * 640)
                    if 0 <= indicator_x < 640:
                        cv2.line(spectrogram_chunk, (indicator_x, 0), 
                                (indicator_x, 639), (0, 255, 255), 2)
                    
                    spectrogram_bgr = spectrogram_chunk
                else:
                    # Fallback: show entire spectrogram
                    spectrogram_bgr = cv2.resize(full_spectrogram, (640, 640), 
                                                interpolation=cv2.INTER_AREA)

                # Convert to DPG texture format and update
                texture = self.convert_cv_to_dpg(
                    spectrogram_bgr, small_window_w, small_window_h
                )
                dpg_set_value(self.tag_node_output03_value_name, texture)

        return {"image": frame, "json": None, "audio": spectrogram_bgr}

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
        skip_rate = int(dpg_get_value(tag_node_input03_value_name))
        target_fps = int(dpg_get_value(tag_node_input04_value_name))
        playback_speed = float(dpg_get_value(tag_node_input05_value_name))

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
            # Trigger spectrogram preparation in background
            self._prepare_spectrogram(node_id, data["file_path_name"])
