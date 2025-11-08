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
DEFAULT_SPECTROGRAM_COLORMAP = 'JET'


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


import os
import pandas as pd
import scipy.io.wavfile as wav
import numpy as np
import matplotlib.pyplot as plt


import os
import numpy as np
import soundfile as sf
import librosa

def chunk_audio_wav_or_mp3(input_audio, output_folder, chunk_duration=5.0, step_duration=0.25):
    os.makedirs(output_folder, exist_ok=True)

    print(f"📥 Chargement : {input_audio}")
    try:
        # Chargement avec librosa : supporte .wav, .mp3, etc.
        data, rate = librosa.load(input_audio, sr=None, mono=True)
    except Exception as e:
        print(f"❌ Erreur lors de la lecture : {e}")
        return

    total_duration = len(data) / rate
    chunk_samples = int(chunk_duration * rate)
    step_samples = int(step_duration * rate)

    start = 0
    count = 1

    print(f"🔍 Fréquence d'échantillonnage : {rate} Hz")
    print("🚀 Découpage en cours...")

    while (start + chunk_samples) <= len(data):
        end = start + chunk_samples
        chunk = data[start:end]
        output_path = os.path.join(output_folder, f"chunk_{count}.wav")
        sf.write(output_path, chunk, rate)
        print(f"✅ chunk_{count}.wav : {start / rate:.2f}s → {end / rate:.2f}s")
        count += 1
        start += step_samples

    print(f"\n🎉 {count - 1} chunks enregistrés dans {output_folder}")





# Ta fonction plot_spectrogram
def plot_spectrogram(location, plotpath=None, binsize=2**10, colormap="jet"):
    samplerate, samples = wav.read(location)
    s = fourier_transformation(samples, binsize)
    sshow, freq = make_logscale(s, factor=1.0, sr=samplerate)
    ims = 20.*np.log10(np.abs(sshow)/10e-6) # amplitude to decibel

    timebins, freqbins = np.shape(ims)
    #print("timebins:", timebins, "freqbins:", freqbins)

    plt.figure(figsize=(15, 7.5))
    plt.imshow(np.transpose(ims), origin="lower", aspect="auto", cmap=colormap, interpolation="none")
    xlocs = np.float32(np.linspace(0, timebins-1, 5))
    plt.xticks(xlocs, ["%.02f" % l for l in ((xlocs*len(samples)/timebins)+(0.5*binsize))/samplerate])
    ylocs = np.int16(np.round(np.linspace(0, freqbins-1, 10)))
    plt.yticks(ylocs, ["%.02f" % freq[i] for i in ylocs])

    if plotpath:
        plt.savefig(plotpath, bbox_inches="tight")
    else:
        plt.show()
    plt.clf()

    return ims


def make_logscale(spec, sr=44100, factor=20.):
    timebins, freqbins = np.shape(spec)

    scale = np.linspace(0, 1, freqbins) ** factor
    scale *= (freqbins-1)/max(scale)
    scale = np.unique(np.round(scale))

    # create spectrogram with new freq bins
    newspec = np.complex128(np.zeros([timebins, len(scale)]))
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):], axis=1)
        else:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):int(scale[i+1])], axis=1)

    # list center freq of bins
    allfreqs = np.abs(np.fft.fftfreq(freqbins*2, 1./sr)[:freqbins+1])
    freqs = []
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            freqs += [np.mean(allfreqs[int(scale[i]):])]
        else:
            freqs += [np.mean(allfreqs[int(scale[i]):int(scale[i+1])])]

    return newspec, freqs
    
def fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning):
    win = window(frameSize)
    hopSize = int(frameSize - np.floor(overlapFac * frameSize))

    # zeros at beginning (thus center of 1st window should be for sample nr. 0)
    samples = np.append(np.zeros(int(np.floor(frameSize/2.0))), sig)
    # cols for windowing
    cols = np.ceil( (len(samples) - frameSize) / float(hopSize)) + 1
    # zeros at end (thus samples can be fully covered by frames)
    samples = np.append(samples, np.zeros(frameSize))

    frames = stride_tricks.as_strided(samples, shape=(int(cols), frameSize), strides=(samples.strides[0]*hopSize, samples.strides[0])).copy()
    frames *= win

    return np.fft.rfft(frames)    



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

        # Spectrogram storage
        self._spectrogram_texture = {}
        self._spectrogram_array = {}
        self._spectrogram_params = {}
        self._spectrogram_meta = {}
        
        # Spectrogram colormap configuration
        # Can be changed to 'VIRIDIS', 'JET', 'MAGMA', 'PLASMA', etc.
        self._spectrogram_colormap = DEFAULT_SPECTROGRAM_COLORMAP
        
        # New: Pre-processed data storage
        self._video_frames = {}  # Store extracted frames
        self._audio_chunks = {}  # Store audio chunks
        self._spectrogram_chunks = {}  # Store pre-computed spectrograms per chunk
        self._chunk_metadata = {}  # Metadata for chunk-to-frame mapping

    def _preprocess_video(self, node_id, movie_path, chunk_duration=5.0, step_duration=0.25):
        """
        Pre-process video by extracting all frames and generating spectrograms for audio chunks.
        
        This method:
        1. Extracts all video frames using OpenCV
        2. Extracts audio using librosa
        3. Chunks audio into segments (chunk_duration with step_duration overlap)
        4. Pre-computes spectrograms for each chunk
        5. Stores metadata for frame-to-chunk mapping
        
        Args:
            node_id: Node identifier
            movie_path: Path to video file
            chunk_duration: Duration of each audio chunk in seconds (default: 5.0)
            step_duration: Step size between chunks in seconds (default: 0.25)
        """
        if not movie_path or not os.path.exists(movie_path):
            print(f"Video file not found: {movie_path}")
            return
        
        print(f"🎬 Pre-processing video: {movie_path}")
        
        try:
            # Step 1: Extract all video frames
            print("📹 Extracting video frames...")
            cap = cv2.VideoCapture(movie_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # Default fallback
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            frames = []
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
                frame_idx += 1
                if frame_idx % 100 == 0:
                    print(f"  Extracted {frame_idx}/{frame_count} frames...")
            
            cap.release()
            self._video_frames[node_id] = frames
            print(f"✅ Extracted {len(frames)} frames (FPS: {fps})")
            
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
            
            # Step 4: Pre-compute spectrograms for each chunk
            print("🌈 Pre-computing spectrograms...")
            spectrogram_chunks = []
            binsize = 2**10  # 1024 samples
            
            for idx, chunk in enumerate(audio_chunks):
                if idx % 10 == 0:
                    print(f"  Processing chunk {idx}/{len(audio_chunks)}...")
                
                # Perform Fourier transformation
                s = fourier_transformation(chunk, binsize, overlapFac=0.5, window=np.hanning)
                
                # Apply logarithmic frequency scaling
                sshow, freq = make_logscale(spec=s, sr=sr, factor=1.0)
                
                # Convert to dB scale with epsilon to avoid log10(0)
                sshow_safe = np.maximum(np.abs(sshow), SPECTROGRAM_EPSILON)
                ims = 20. * np.log10(sshow_safe / 10e-6)
                
                # Replace non-finite values
                ims = np.nan_to_num(ims, nan=-80.0, posinf=0.0, neginf=-80.0)
                
                # Transpose for correct orientation (freq x time)
                ims_transposed = np.transpose(ims, (1, 0))
                
                # Apply colormap
                S_rgb = apply_colormap_to_spectrogram(
                    ims_transposed,
                    method='cv2',
                    cmap=self._spectrogram_colormap
                )
                
                # Flip vertically and convert to BGR
                S_rgb = np.flipud(S_rgb)
                S_bgr = cv2.cvtColor(S_rgb, cv2.COLOR_RGB2BGR)
                
                spectrogram_chunks.append(S_bgr)
            
            self._spectrogram_chunks[node_id] = spectrogram_chunks
            print(f"✅ Pre-computed {len(spectrogram_chunks)} spectrograms")
            
            # Step 5: Store metadata
            self._chunk_metadata[node_id] = {
                'fps': fps,
                'sr': sr,
                'chunk_duration': chunk_duration,
                'step_duration': step_duration,
                'chunk_start_times': chunk_start_times,
                'num_frames': len(frames),
                'num_chunks': len(audio_chunks),
            }
            
            print(f"🎉 Pre-processing complete!")
            print(f"   Frames: {len(frames)}, Chunks: {len(audio_chunks)}, FPS: {fps}")
            
        except Exception as e:
            print(f"❌ Failed to pre-process video: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_spectrogram_for_frame(self, node_id, frame_number):
        """
        Get the pre-computed spectrogram for a specific frame number.
        
        Args:
            node_id: Node identifier
            frame_number: Current frame number
            
        Returns:
            Pre-computed spectrogram (BGR image) or None if not available
        """
        if node_id not in self._chunk_metadata or node_id not in self._spectrogram_chunks:
            return None
        
        metadata = self._chunk_metadata[node_id]
        fps = metadata['fps']
        step_duration = metadata['step_duration']
        
        # Calculate current time from frame number
        current_time = frame_number / fps if fps > 0 else 0
        
        # Calculate chunk index based on step duration
        chunk_index = int(current_time / step_duration)
        
        # Clamp to valid range
        chunk_index = max(0, min(chunk_index, len(self._spectrogram_chunks[node_id]) - 1))
        
        return self._spectrogram_chunks[node_id][chunk_index]








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

        # Update spectrogram display if toggle is enabled
        tag_node_spectrogram_toggle = tag_node_name + ":SpectrogramToggle"

        if dpg.does_item_exist(tag_node_spectrogram_toggle):
            show_spectrogram = dpg_get_value(tag_node_spectrogram_toggle)
            
            if show_spectrogram and str(node_id) in self._spectrogram_chunks:
                # Get current frame number
                current_frame_num = self._frame_count.get(str(node_id), 0)
                
                # Get pre-computed spectrogram for this frame
                spectrogram_bgr = self._get_spectrogram_for_frame(str(node_id), current_frame_num)
                
                if spectrogram_bgr is not None:
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
            # NEW: Preprocess video, audio, and spectrograms BEFORE playback
            self._preprocess_video(node_id, data["file_path_name"])
