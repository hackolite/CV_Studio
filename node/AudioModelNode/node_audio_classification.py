#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AudioClassification node — ONNX audio classification pipeline.

Takes raw audio (from AUDIO connection) → mel spectrogram → ONNX model
→ top-K class predictions output as JSON + spectrogram overlay image.

Model format: ONNX (.onnx), expected input shape (1, 1, n_mels, T) float32.
Inference is performed via onnxruntime — no PyTorch required at runtime.

Model management mirrors the ObjectDetection node:
  - Models are stored in a persistent registry (audio_models_registry.json).
  - Users add models via a yellow "Add Model" button → file dialog → preview/confirm
    modal → the model is copied to node/AudioModelNode/models/ and registered.
  - All registered models appear in a combo dropdown for selection.
"""
import ast
import json
import os
import shutil
import time
import copy

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode
from node.DLNode.object_detection.onnx_session_utils import make_session
from node.AudioModelNode import audio_models_registry
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_AUDIO_MODEL_BASE = os.path.dirname(os.path.abspath(__file__))
_UPLOADS_DIR = os.path.join(_AUDIO_MODEL_BASE, "models")

# librosa is imported lazily so the app starts even when it is not installed
_librosa = None


def _get_librosa():
    global _librosa
    if _librosa is None:
        try:
            import librosa
            _librosa = librosa
        except ImportError:
            logger.error("[AudioClassification] librosa is not installed.")
    return _librosa


# ---------------------------------------------------------------------------
# Default hyper-parameters — match the ESC-50 Colab training script
# ---------------------------------------------------------------------------
_DEFAULT_SR = 22050
_DEFAULT_N_MELS = 128
_DEFAULT_MAX_SEC = 5
_DEFAULT_TOP_K = 3
_DEFAULT_HOP_LENGTH = 512   # must match training (librosa default but made explicit)
_DEFAULT_N_FFT = 2048        # must match training (librosa default but made explicit)

# YAMNet was trained on 16 kHz mono audio (Google AudioSet / YAMNet paper).
# The mel-CNN ONNX exported here expects the same 16 kHz pre-processing.
_YAMNET_TARGET_SR = 16000

# Qualcomm/Google YAMNet mel-spectrogram parameters (from the YAMNet paper):
#   window = 25 ms → 400 samples at 16 kHz
#   fft    = 512 points (next power-of-two ≥ 400, as in tf.signal.stft)
#   hop    = 10 ms → 160 samples at 16 kHz
# These differ from the ESC-50 defaults (n_fft=2048, hop=512) and MUST be
# used when running this model; using the wrong parameters produces a mel
# that looks nothing like the training data → completely random predictions.
#
# Note: the TF YAMNet reference uses frame_length=400 (window) but
# fft_length=512 (zero-padded FFT).  In librosa this is expressed as
# n_fft=512 (FFT size) + win_length=400 (window size), giving 257 frequency
# bins instead of 201, which better captures the 125–7500 Hz mel range.
_YAMNET_N_FFT = 512        # FFT size (next power of 2 ≥ window length)
_YAMNET_WIN_LENGTH = 400   # STFT window length (25 ms at 16 kHz)
_YAMNET_HOP_LENGTH = 160

# Qualcomm YAMNet model architecture:
#   Input shape: [1, 1, 96, 64]  → [batch, channel, TIME=96, MELS=64]
#   This is TIME-MAJOR format: dim[2] = time frames, dim[3] = mel bins.
#   The standard ESC-50 convention is MELS-FIRST: dim[2]=n_mels, dim[3]=T.
# n_mels = 64 (NOT 96) and fixed_time = 96 (NOT 64).
_YAMNET_N_MELS = 64
_YAMNET_FIXED_TIME = 96  # number of time frames per inference patch

# Mel normalisation: the Google/Qualcomm YAMNet model was trained on
# log(mel_spectrogram + 1e-3), NOT on power_to_db values.
# Feeding dB-scale inputs causes every ReLU in the network to output zero.
_YAMNET_MEL_NORM = "log_offset"  # "power_to_db" is the ESC-50 default

# The YAMNet model output 'class_scores' contains per-class sigmoid
# probabilities (independent [0,1] scores, sum ≠ 1.0).
# Applying a second softmax on top of sigmoid scores spreads probability
# mass uniformly → predictions look completely random.
_YAMNET_OUTPUT_ACTIVATION = "sigmoid"  # "softmax" is the ESC-50 default

# YAMNet mel filter bank frequency bounds (from the original YAMNet paper and
# reference implementation):
#   fmin = 125 Hz  (librosa default is 0 Hz — wrong for this model)
#   fmax = 7500 Hz (librosa default is sr/2 = 8000 Hz — wrong for this model)
# Using the librosa defaults changes which frequencies each mel bin captures,
# shifting all predictions away from the training distribution.
_YAMNET_FMIN = 125
_YAMNET_FMAX = 7500

# Minimum RMS energy threshold below which inference is skipped and "Silence"
# is reported instead.  When the microphone captures only background hiss the
# mel spectrogram is flat at log(~0 + 1e-3) = -6.9, and the model almost
# always outputs "Sound effect" = 1.0 because that is its learned catch-all
# for near-silent inputs.  Skipping inference avoids false positives.
_YAMNET_SILENCE_RMS_THRESHOLD = 1e-3

_N_MELS_OPTIONS = [64, 96, 128, 256]
_MAX_SEC_OPTIONS = [1, 2, 3, 5, 10]
_TOP_K_OPTIONS = [1, 3, 5, 10]


# ---------------------------------------------------------------------------
# Built-in class label sets
# ---------------------------------------------------------------------------
try:
    from node.DLNode.classification.esc50_class_names import esc50_class_names as _ESC50_NAMES
except Exception:
    _ESC50_NAMES = {i: f"class_{i}" for i in range(50)}

try:
    from node.DLNode.classification.yamnet_class_names import yamnet_class_names as _YAMNET_NAMES
except Exception:
    _YAMNET_NAMES = {i: f"class_{i}" for i in range(521)}


# ---------------------------------------------------------------------------
# Built-in model catalogue
# ---------------------------------------------------------------------------
_BUILTIN_AUDIO_MODELS = [
    {
        "name": "YAMNet",
        "path": os.path.join(_UPLOADS_DIR, "yamnet.onnx"),
        "class_names": _YAMNET_NAMES,
        # ----------------------------------------------------------------
        # YAMNet was originally trained on 16 kHz audio; set target_sr so
        # the pipeline automatically resamples any incoming audio to this rate.
        "target_sr": _YAMNET_TARGET_SR,
        # ----------------------------------------------------------------
        # STFT / mel-filter parameters that MUST match the training recipe.
        # Using ESC-50 defaults (n_fft=2048, hop=512) would produce a mel
        # spectrogram that looks nothing like training data → random outputs.
        "n_fft": _YAMNET_N_FFT,
        "win_length": _YAMNET_WIN_LENGTH,
        "hop_length": _YAMNET_HOP_LENGTH,
        # ----------------------------------------------------------------
        # Architecture: Input [1,1,96,64] is TIME-MAJOR (dim[2]=TIME=96,
        # dim[3]=MELS=64).  The catalogue overrides the auto-detected values
        # from inspect_audio_onnx to ensure correctness.
        "n_mels": _YAMNET_N_MELS,
        "fixed_time": _YAMNET_FIXED_TIME,
        # When mel_transpose=True the pipeline computes mel as (n_mels, T),
        # then transposes the last two dims so the tensor fed to the model
        # becomes (1, 1, TIME=fixed_time, MELS=n_mels).
        "mel_transpose": True,
        # ----------------------------------------------------------------
        # Mel normalisation: model was trained on log(mel + 1e-3) not dB.
        # Feeding dB values causes all-zero activations → uniform predictions.
        "mel_norm": _YAMNET_MEL_NORM,
        # ----------------------------------------------------------------
        # Output: per-class sigmoid scores in [0,1] (NOT softmax logits).
        # Applying softmax on top of sigmoid outputs collapses the confidence
        # signal and produces near-uniform predictions.
        "output_activation": _YAMNET_OUTPUT_ACTIVATION,
        # ----------------------------------------------------------------
        # Mel filter bank frequency bounds (from the YAMNet reference implementation).
        # librosa defaults (fmin=0, fmax=sr/2=8000) are WRONG for this model.
        # Using wrong bounds changes which frequencies map to each mel bin, shifting
        # the entire mel feature distribution away from the training data.
        "fmin": _YAMNET_FMIN,
        "fmax": _YAMNET_FMAX,
        # ----------------------------------------------------------------
        # Silence gate: skip inference when audio RMS is below this level.
        # Near-silent frames produce a flat mel at log(1e-3)=-6.9 that the model
        # consistently maps to "Sound effect"=1.0 (its catch-all for uncertainty).
        "silence_rms_threshold": _YAMNET_SILENCE_RMS_THRESHOLD,
    },
]


# ---------------------------------------------------------------------------
# Audio-specific ONNX inspector
# ---------------------------------------------------------------------------

def inspect_audio_onnx(model_path: str) -> dict:
    """Inspect an ONNX audio classification model.

    Returns a dict with:
      input_name   (str)  – first input tensor name
      input_shape  (list) – e.g. [1, 1, 128, 431]
      n_mels       (int)  – detected from input_shape[2], 0 if dynamic
      output_name  (str)  – first output tensor name
      output_shape (list) – e.g. [1, 50]
      num_classes  (int)  – detected from output_shape[1], 0 if unknown
      class_names  (dict) – {int: str} from ONNX metadata, or empty dict
    """
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"ONNX model not found: {model_path}")

    session = make_session(model_path, providers=["CPUExecutionProvider"])

    inp = session.get_inputs()[0]
    out = session.get_outputs()[0]
    input_shape = list(inp.shape)
    output_shape = list(out.shape)

    # n_mels from input shape: (batch, channels, n_mels, time)
    n_mels = 0
    if len(input_shape) == 4 and isinstance(input_shape[2], int) and input_shape[2] > 0:
        n_mels = input_shape[2]

    # num_classes from output shape: (batch, num_classes)
    num_classes = 0
    if len(output_shape) >= 2 and isinstance(output_shape[-1], int) and output_shape[-1] > 0:
        num_classes = output_shape[-1]

    # Embedded class names (try "names", "labels", or "classes" metadata keys)
    class_names: dict = {}
    try:
        meta = session.get_modelmeta().custom_metadata_map
        for key in ("names", "labels", "classes"):
            if key in meta:
                raw = meta[key]
                parsed = None
                try:
                    parsed = ast.literal_eval(raw)
                except Exception:
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        # "classes" key: comma-separated string (e.g. "dog,cat,bird")
                        items = [s.strip() for s in raw.split(",") if s.strip()]
                        if items:
                            parsed = items
                if isinstance(parsed, dict):
                    class_names = {int(k): str(v) for k, v in parsed.items()}
                elif isinstance(parsed, list):
                    class_names = {i: str(v) for i, v in enumerate(parsed)}
                if class_names:
                    if num_classes == 0:
                        num_classes = len(class_names)
                    break
    except Exception as exc:
        logger.debug(f"[AudioClassification] Could not read ONNX metadata: {exc}")

    # Implicit model_type detection from input shape:
    #   4-D (batch, channels, n_mels, time) → mel_cnn  (current default pipeline)
    #   1-D or 2-D (batch, samples) or (samples,)      → waveform  (e.g. YAMNet)
    ndim = len(input_shape)
    if ndim == 4:
        model_type = "mel_cnn"
    elif ndim in (1, 2):
        model_type = "waveform"
    else:
        # Fallback: treat any other rank as mel_cnn (safest default)
        model_type = "mel_cnn"

    # Extract target_sr from ONNX metadata if the exporter embedded it
    target_sr = 0
    try:
        meta = session.get_modelmeta().custom_metadata_map
        for key in ("sample_rate", "sr", "target_sr", "samplerate"):
            if key in meta:
                try:
                    target_sr = int(meta[key])
                    break
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass

    # Extract n_fft / hop_length from ONNX metadata if the exporter embedded them
    n_fft_meta = 0
    hop_length_meta = 0
    try:
        meta = session.get_modelmeta().custom_metadata_map
        for key in ("n_fft", "fft_size", "window_length"):
            if key in meta:
                try:
                    n_fft_meta = int(meta[key])
                    break
                except (ValueError, TypeError):
                    pass
        for key in ("hop_length", "hop_size", "stride"):
            if key in meta:
                try:
                    hop_length_meta = int(meta[key])
                    break
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass

    logger.info(
        f"[AudioClassification] ONNX inspected: input={input_shape}, "
        f"output={output_shape}, n_mels={n_mels}, num_classes={num_classes}, "
        f"embedded_labels={len(class_names)}, model_type={model_type}, "
        f"target_sr={target_sr if target_sr > 0 else '(not set)'}, "
        f"n_fft={n_fft_meta if n_fft_meta > 0 else '(not set)'}, "
        f"hop_length={hop_length_meta if hop_length_meta > 0 else '(not set)'}"
    )

    # Detect fixed time axis and n_mels from the input tensor dimensions.
    #
    # Two tensor conventions exist in practice:
    #   1. Mels-first (ESC-50 style): [batch, ch, N_MELS, T]  → dim[2] < dim[3] typically
    #   2. Time-first (YAMNet style): [batch, ch, TIME, N_MELS] → dim[2] > dim[3] typically
    #
    # Heuristic: when dim[3] < dim[2] we assume time-first layout because
    # common mel-bin counts (64, 96, 128, …) are all less than typical time-frame
    # counts for a multi-second window.  The catalogue always overrides this for
    # built-in models, so the heuristic only matters for custom uploads.
    fixed_time = 0
    mel_transpose = False  # True → model expects (TIME, MELS) layout
    if ndim == 4:
        d2 = input_shape[2] if isinstance(input_shape[2], int) else 0
        d3 = input_shape[3] if isinstance(input_shape[3], int) else 0
        if d2 > 0 and d3 > 0 and d3 < d2:
            # Time-first: dim[2] = TIME (fixed_time), dim[3] = N_MELS
            n_mels = d3
            fixed_time = d2
            mel_transpose = True
        elif d2 > 0 and d3 > 0:
            # Mels-first: dim[2] = N_MELS, dim[3] = TIME
            n_mels = d2
            fixed_time = d3

    return {
        "input_name": inp.name,
        "input_shape": input_shape,
        "n_mels": n_mels,
        "fixed_time": fixed_time,
        "mel_transpose": mel_transpose,
        "output_name": out.name,
        "output_shape": output_shape,
        "num_classes": num_classes,
        "class_names": class_names,
        "model_type": model_type,
        "target_sr": target_sr,
        "n_fft": n_fft_meta,
        "hop_length": hop_length_meta,
    }


# ---------------------------------------------------------------------------
# Mel spectrogram helper — pure numpy, no PyTorch
# ---------------------------------------------------------------------------

def audio_to_mel_array(audio_data: np.ndarray, sample_rate: int,
                        n_mels: int, max_sec: int,
                        n_fft: int = None, hop_length: int = None,
                        win_length: int = None,
                        mel_norm: str = "power_to_db",
                        fmin: float = 0.0, fmax: float = 0.0) -> np.ndarray:
    """Convert 1-D float32 audio → (1, n_mels, T) float32 numpy array.

    Matches the ESC-50 training pre-processing by default:
      - pad / crop to `max_sec * sample_rate` samples (most recent samples kept)
      - librosa.feature.melspectrogram → power_to_db

    Pass explicit `n_fft` and `hop_length` to override the defaults when the
    model was trained with different STFT parameters (e.g. YAMNet uses
    n_fft=512, win_length=400, hop_length=160 instead of the ESC-50 defaults
    of 2048/512).

    Pass ``win_length`` to use a different window size from the FFT size.
    The TF YAMNet reference uses frame_length=400 (window) with fft_length=512
    (zero-padded): ``n_fft=512, win_length=400, hop_length=160``.

    Pass ``mel_norm="log_offset"`` for models trained on
    ``log(mel_spectrogram + 1e-3)`` (Google/Qualcomm YAMNet).  The default
    ``"power_to_db"`` matches the ESC-50 training setup.

    Pass ``fmin``/``fmax`` (Hz) to set the mel filter bank frequency bounds.
    The Google/Qualcomm YAMNet reference implementation uses fmin=125 Hz and
    fmax=7500 Hz; librosa defaults (0 Hz and sr/2) produce a different mel
    feature distribution and degrade prediction quality for this model.
    """
    librosa = _get_librosa()
    if librosa is None:
        return None

    _n_fft = n_fft if n_fft and n_fft > 0 else _DEFAULT_N_FFT
    _hop = hop_length if hop_length and hop_length > 0 else _DEFAULT_HOP_LENGTH

    max_len = sample_rate * max_sec

    y = np.asarray(audio_data, dtype=np.float32)
    if y.ndim > 1:
        y = np.mean(y, axis=-1)

    # Clip to [-1, 1] as expected by YAMNet and the standard audio pipeline.
    # Microphone audio via sounddevice (float32) is already in this range;
    # this safeguard prevents extreme values from shifting mel spectrogram values
    # when audio arrives from other sources.
    y = np.clip(y, -1.0, 1.0)

    if len(y) < max_len:
        y = np.pad(y, (0, max_len - len(y)))
    else:
        y = y[-max_len:]  # keep the most recent samples

    mel_kwargs = {}
    if fmin and fmin > 0.0:
        mel_kwargs["fmin"] = fmin
    if fmax and fmax > 0.0:
        mel_kwargs["fmax"] = fmax
    if win_length and win_length > 0:
        mel_kwargs["win_length"] = win_length

    mel = librosa.feature.melspectrogram(
        y=y, sr=sample_rate, n_mels=n_mels,
        n_fft=_n_fft, hop_length=_hop,
        **mel_kwargs,
    )
    if mel_norm == "log_offset":
        # Google / Qualcomm YAMNet normalization: log(mel + 1e-3)
        mel_out = np.log(mel + 1e-3).astype(np.float32)
    else:
        mel_out = librosa.power_to_db(mel).astype(np.float32)

    return mel_out[np.newaxis]  # (1, n_mels, T)


# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------

def mel_array_to_bgr_image(mel_2d: np.ndarray, width: int, height: int) -> np.ndarray:
    """Render a (n_mels, T) or (1, n_mels, T) mel array as a BGR image."""
    arr = mel_2d.squeeze() if mel_2d.ndim == 3 else mel_2d
    vmin, vmax = arr.min(), arr.max()
    if vmax > vmin:
        norm = ((arr - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    else:
        norm = np.zeros_like(arr, dtype=np.uint8)
    bgr = cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO)
    bgr = np.flipud(bgr)
    bgr = cv2.resize(bgr, (width, height), interpolation=cv2.INTER_LINEAR)
    return bgr


def overlay_predictions(bgr_image: np.ndarray, predictions: list) -> np.ndarray:
    """Draw top-K label/score lines onto a BGR image."""
    out = copy.deepcopy(bgr_image)
    y_offset = 16
    for rank, (label, score) in enumerate(predictions):
        text = f"#{rank+1} {label}: {score:.3f}"
        cv2.putText(out, text, (4, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
        y_offset += 16
    return out


# ===========================================================================
# FactoryNode — creates the DearPyGui node widget
# ===========================================================================

class FactoryNode:
    node_label = "AudioClassification"
    node_tag = "AudioClassification"

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=None,
        opencv_setting_dict=None,
        callback=None,
    ):
        if pos is None:
            pos = [0, 0]

        # Ensure the registry is loaded before building UI
        Node._load_models_from_registry()

        node = Node()
        node.tag_node_name = str(node_id) + ":" + self.node_tag

        # ---- tag helpers ----
        _tn = node.tag_node_name

        node.tag_node_input01_name = _tn + ":" + node.TYPE_AUDIO + ":Input01"
        node.tag_node_input01_value_name = _tn + ":" + node.TYPE_AUDIO + ":Input01Value"

        node.tag_node_output01_name = _tn + ":" + node.TYPE_IMAGE + ":Output01"
        node.tag_node_output01_value_name = _tn + ":" + node.TYPE_IMAGE + ":Output01Value"

        node.tag_node_output_json_name = _tn + ":" + node.TYPE_JSON + ":OutputJson"
        node.tag_node_output_json_value_name = _tn + ":" + node.TYPE_JSON + ":OutputJsonValue"

        node.tag_node_output_audio_name = _tn + ":" + node.TYPE_AUDIO + ":OutputAudio"
        node.tag_node_output_audio_value_name = _tn + ":" + node.TYPE_AUDIO + ":OutputAudioValue"

        node.tag_node_output02_name = _tn + ":" + node.TYPE_TIME_MS + ":Output02"
        node.tag_node_output02_value_name = _tn + ":" + node.TYPE_TIME_MS + ":Output02Value"

        # Option tags
        node.tag_model_combo = _tn + ":OPT:ModelCombo"
        node.tag_n_mels = _tn + ":OPT:NMels"
        node.tag_max_sec = _tn + ":OPT:MaxSec"
        node.tag_top_k = _tn + ":OPT:TopK"
        node.tag_label_source = _tn + ":OPT:LabelSource"

        # Preview dialog tags
        preview_window_tag  = "audio_preview_window:"  + str(node_id)
        preview_name_tag    = "audio_preview_name:"    + str(node_id)
        preview_details_tag = "audio_preview_details:" + str(node_id)
        preview_status_tag  = "audio_preview_status:"  + str(node_id)
        preview_confirm_tag = "audio_preview_confirm:" + str(node_id)
        preview_cancel_tag  = "audio_preview_cancel:"  + str(node_id)
        preview_quit_tag    = "audio_preview_quit:"    + str(node_id)

        node.tag_preview_window  = preview_window_tag
        node.tag_preview_name    = preview_name_tag
        node.tag_preview_details = preview_details_tag
        node.tag_preview_status  = preview_status_tag
        node.tag_preview_confirm = preview_confirm_tag
        node.tag_preview_cancel  = preview_cancel_tag
        node.tag_preview_quit    = preview_quit_tag

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict["process_width"]
        small_window_h = node._opencv_setting_dict["process_height"]
        use_pref_counter = node._opencv_setting_dict["use_pref_counter"]

        # Initial black texture
        black_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        black_texture = node.convert_cv_to_dpg(black_image, small_window_w, small_window_h)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # ---- File dialog for ONNX model (shown when Add Model is clicked) ----
        onnx_dialog_tag = "audio_onnx_select:" + str(node_id)
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            modal=True,
            height=400,
            callback=node._callback_onnx_select,
            tag=onnx_dialog_tag,
        ):
            dpg.add_file_extension("ONNX model (*.onnx){.onnx}")
            dpg.add_file_extension("", color=(150, 255, 150, 255))
        node.tag_upload_file_dialog = onnx_dialog_tag

        # ---- Preview / confirmation modal ----
        def _on_upload_confirm(sender, app_data, user_data):
            node._do_confirm_upload()

        def _on_close_preview(sender, app_data, user_data):
            node._close_upload_preview()

        with dpg.window(
            label="Audio ONNX Model Preview",
            tag=preview_window_tag,
            modal=True,
            show=False,
            width=430,
            no_close=True,
        ):
            dpg.add_text("Model name (editable):")
            dpg.add_input_text(tag=preview_name_tag, width=410)
            dpg.add_separator()
            dpg.add_group(tag=preview_details_tag)
            dpg.add_separator()
            dpg.add_text("", tag=preview_status_tag)
            dpg.add_spacer(height=4)
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="  Confirm Upload  ",
                    tag=preview_confirm_tag,
                    callback=_on_upload_confirm,
                )
                dpg.add_spacer(width=10)
                dpg.add_button(
                    label="  Cancel  ",
                    tag=preview_cancel_tag,
                    callback=_on_close_preview,
                )
                dpg.add_spacer(width=10)
                dpg.add_button(
                    label="  Quit  ",
                    tag=preview_quit_tag,
                    callback=_on_close_preview,
                    show=False,
                )

        # ---- Yellow button theme ----
        with dpg.theme() as yellow_btn_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 220, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 235, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (220, 190, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))

        # ---- Yellow JSON output theme ----
        with dpg.theme() as yellow_out_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # ---- Node UI ----
        model_names = list(Node._model_path_setting.keys())
        default_model = model_names[0] if model_names else ""

        with dpg.node(tag=_tn, parent=parent, label=self.node_label, pos=pos):

            # Audio input
            with dpg.node_attribute(
                tag=node.tag_node_input01_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value="Audio input",
                )

            # Spectrogram preview image output
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # ---- Model selector combo ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:ModelCombo",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=model_names,
                    default_value=default_model,
                    width=small_window_w,
                    label="Model",
                    tag=node.tag_model_combo,
                    callback=callback,
                )

            # ---- Option: N_Mels ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:NMels",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=[str(v) for v in _N_MELS_OPTIONS],
                    default_value=str(_DEFAULT_N_MELS),
                    width=small_window_w,
                    label="N Mels",
                    tag=node.tag_n_mels,
                    callback=callback,
                )

            # ---- Option: Max audio length (seconds) ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:MaxSec",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=[str(v) for v in _MAX_SEC_OPTIONS],
                    default_value=str(_DEFAULT_MAX_SEC),
                    width=small_window_w,
                    label="Max seconds",
                    tag=node.tag_max_sec,
                    callback=callback,
                )

            # ---- Option: Top-K ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:TopK",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=[str(v) for v in _TOP_K_OPTIONS],
                    default_value=str(_DEFAULT_TOP_K),
                    width=small_window_w,
                    label="Top-K",
                    tag=node.tag_top_k,
                    callback=callback,
                )

            # ---- Option: Label source ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:LabelSource",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=["ONNX metadata", "ESC-50 (built-in)", "YAMNet (built-in)"],
                    default_value="ONNX metadata",
                    width=small_window_w,
                    label="Labels",
                    tag=node.tag_label_source,
                    callback=callback,
                )

            # ---- JSON output ----
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                json_btn = dpg.add_button(
                    label="JSON",
                    tag=node.tag_node_output_json_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(json_btn, yellow_out_theme)

            # ---- Audio passthrough output ----
            with dpg.node_attribute(
                tag=node.tag_node_output_audio_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                audio_btn = dpg.add_button(
                    label="Audio",
                    tag=node.tag_node_output_audio_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(audio_btn, yellow_out_theme)

            # ---- Performance counter ----
            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output02_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value="elapsed time(ms)",
                    )

            # ---- Add Model button (yellow, opens upload file dialog) ----
            node.tag_upload_btn = _tn + ":UploadONNX"

            def _on_add_model_clicked(sender, app_data, user_data):
                logger.info(
                    f"[AudioUpload] 'Add Model' clicked — "
                    f"showing file dialog '{onnx_dialog_tag}'"
                )
                dpg.show_item(onnx_dialog_tag)

            with dpg.node_attribute(
                tag=_tn + ":UploadAttr",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                upload_btn = dpg.add_button(
                    label=u"Add Model",
                    tag=node.tag_upload_btn,
                    width=small_window_w,
                    callback=_on_add_model_clicked,
                )
                dpg.bind_item_theme(upload_btn, yellow_btn_theme)

        return node


# ===========================================================================
# Node — registry, upload workflow, ONNX inference + update logic
# ===========================================================================

class Node(BaseNode):
    _ver = "0.0.3"

    node_label = "AudioClassification"
    node_tag = "AudioClassification"

    _opencv_setting_dict = None

    # -----------------------------------------------------------------------
    # Class-level model registry (shared across all instances)
    # -----------------------------------------------------------------------
    _model_path_setting: dict = {}       # name → onnx file path (str)
    _model_class_names: dict = {}        # name → {int: str}
    _model_n_mels: dict = {}             # name → int (0 = use UI value)
    _model_type: dict = {}               # name → "mel_cnn" | "waveform"
    _model_fixed_time: dict = {}         # name → int (0 = dynamic / no constraint)
    _model_target_sr: dict = {}          # name → int (0 = use incoming SR / no resample)
    _model_n_fft: dict = {}              # name → int (0 = use _DEFAULT_N_FFT)
    _model_win_length: dict = {}         # name → int (0 = same as n_fft, no separate window)
    _model_hop_length: dict = {}         # name → int (0 = use _DEFAULT_HOP_LENGTH)
    # Mel filter bank frequency bounds (0 = use librosa default)
    _model_fmin: dict = {}               # name → float (Hz)
    _model_fmax: dict = {}               # name → float (Hz; 0 = sr/2)
    # Mel-spectrogram layout: False = (MELS, TIME) standard; True = (TIME, MELS) YAMNet
    _model_mel_transpose: dict = {}
    # Mel normalisation applied before inference:
    #   "power_to_db"  – ESC-50 default (librosa.power_to_db)
    #   "log_offset"   – Google/Qualcomm YAMNet: log(mel + 1e-3)
    _model_mel_norm: dict = {}
    # How to interpret the raw model output:
    #   "softmax"  – treat as logits, apply softmax (ESC-50 default)
    #   "sigmoid"  – treat as per-class sigmoid scores, use directly (YAMNet)
    _model_output_activation: dict = {}
    # Minimum RMS energy below which inference is skipped (0.0 = disabled)
    _model_silence_rms_threshold: dict = {}

    # -----------------------------------------------------------------------
    # Per-instance inference state
    # -----------------------------------------------------------------------
    _session = None          # onnxruntime.InferenceSession
    _input_name = None       # str
    _active_model_name = None  # str  — name of the currently-loaded model

    def __init__(self):
        self._session = None
        self._input_name = None
        self._active_model_name = None

    # ------------------------------------------------------------------
    # Registry helpers
    # ------------------------------------------------------------------

    @classmethod
    def _register_model(cls, name: str, path: str, class_names: dict, n_mels: int,
                         model_type: str = "mel_cnn", fixed_time: int = 0,
                         target_sr: int = 0, n_fft: int = 0, win_length: int = 0,
                         hop_length: int = 0,
                         fmin: float = 0.0, fmax: float = 0.0,
                         mel_transpose: bool = False,
                         mel_norm: str = "power_to_db",
                         output_activation: str = "softmax",
                         silence_rms_threshold: float = 0.0):
        """Add one model to the class-level runtime dictionaries.

        Args:
            target_sr:               Expected input sample rate (Hz). 0 = no forced resampling.
            n_fft:                   STFT FFT size used during training. 0 = _DEFAULT_N_FFT.
                                     Qualcomm/Google YAMNet: 512 (zero-padded from 400-sample window).
            win_length:              STFT window size (samples). 0 = same as n_fft (no zero-padding).
                                     Qualcomm/Google YAMNet: 400 (25 ms at 16 kHz).
            hop_length:              STFT hop size used during training. 0 = _DEFAULT_HOP_LENGTH.
                                     Qualcomm/Google YAMNet: 160 (10 ms at 16 kHz).
            fmin:                    Mel filter bank lower bound (Hz). 0 = librosa default (0 Hz).
                                     Qualcomm/Google YAMNet: 125 Hz.
            fmax:                    Mel filter bank upper bound (Hz). 0 = librosa default (sr/2).
                                     Qualcomm/Google YAMNet: 7500 Hz.
            mel_transpose:           When True, the model expects (TIME, MELS) tensor layout
                                     (YAMNet input shape [1,1,96,64] = [batch,ch,TIME,MELS]).
                                     The pipeline transposes mel to match before inference.
            mel_norm:                Mel normalisation applied before inference.
                                     "power_to_db" (ESC-50 default) or "log_offset" (YAMNet).
            output_activation:       How to interpret raw model output.
                                     "softmax" = treat as logits and apply softmax (ESC-50 default).
                                     "sigmoid" = per-class sigmoid scores, use directly (YAMNet).
            silence_rms_threshold:   RMS energy below which inference is skipped and "Silence"
                                     is reported. 0.0 = disabled. YAMNet default: 1e-3.
        """
        cls._model_path_setting[name] = path
        cls._model_class_names[name] = class_names
        cls._model_n_mels[name] = n_mels
        cls._model_type[name] = model_type
        cls._model_fixed_time[name] = fixed_time
        cls._model_target_sr[name] = target_sr
        cls._model_n_fft[name] = n_fft
        cls._model_win_length[name] = win_length
        cls._model_hop_length[name] = hop_length
        cls._model_fmin[name] = float(fmin)
        cls._model_fmax[name] = float(fmax)
        cls._model_mel_transpose[name] = mel_transpose
        cls._model_mel_norm[name] = mel_norm
        cls._model_output_activation[name] = output_activation
        cls._model_silence_rms_threshold[name] = float(silence_rms_threshold)

    @classmethod
    def _load_models_from_registry(cls):
        """Populate runtime dicts from the persistent registry (idempotent)."""
        try:
            entries = audio_models_registry.load_registry()
        except Exception as exc:
            logger.warning(f"[AudioUpload] Could not read registry: {exc}")
            return
        for entry in entries:
            name = entry.get("name", "")
            path = entry.get("path", "")
            if not name or not path:
                continue
            if name in cls._model_path_setting:
                continue  # already loaded
            raw_classes = entry.get("class_names", {})
            class_names = {int(k): str(v) for k, v in raw_classes.items()}
            n_mels = int(entry.get("n_mels", 0))
            model_type = entry.get("model_type", "mel_cnn")
            fixed_time = int(entry.get("fixed_time", 0))
            target_sr = int(entry.get("target_sr", 0))
            n_fft = int(entry.get("n_fft", 0))
            win_length = int(entry.get("win_length", 0))
            hop_length = int(entry.get("hop_length", 0))
            fmin = float(entry.get("fmin", 0.0))
            fmax = float(entry.get("fmax", 0.0))
            mel_transpose = bool(entry.get("mel_transpose", False))
            mel_norm = entry.get("mel_norm", "power_to_db")
            output_activation = entry.get("output_activation", "softmax")
            silence_rms_threshold = float(entry.get("silence_rms_threshold", 0.0))
            cls._register_model(name, path, class_names, n_mels, model_type, fixed_time,
                                 target_sr=target_sr, n_fft=n_fft, win_length=win_length,
                                 hop_length=hop_length,
                                 fmin=fmin, fmax=fmax,
                                 mel_transpose=mel_transpose, mel_norm=mel_norm,
                                 output_activation=output_activation,
                                 silence_rms_threshold=silence_rms_threshold)
            logger.info(f"[AudioUpload] Loaded model from registry: {name}")

    @classmethod
    def _ensure_builtin_models(cls):
        """Seed built-in ONNX models (e.g. yamnet.onnx) into the registry if present on disk.

        Runs once at module load time so that built-in models appear in the combo
        without requiring the user to upload them manually.  Entries whose ONNX
        file is not yet on disk are silently skipped (e.g. stripped builds).
        The model_type is auto-detected via inspect_audio_onnx:
          4-D input  → "mel_cnn"
          1-D/2-D    → "waveform"
        """
        try:
            existing = {e.get("name") for e in audio_models_registry.load_registry()}
        except Exception as exc:
            logger.warning(f"[AudioBuiltin] Could not read registry: {exc}")
            return

        for meta in _BUILTIN_AUDIO_MODELS:
            name = meta["name"]
            path = meta["path"]
            if not os.path.isfile(path):
                logger.debug(f"[AudioBuiltin] Skipping '{name}' — ONNX not found: {path}")
                continue

            try:
                info = inspect_audio_onnx(path)
            except Exception as exc:
                logger.warning(f"[AudioBuiltin] Could not inspect '{name}': {exc}")
                continue

            # Prefer labels embedded in the ONNX; fall back to built-in list
            class_names = info.get("class_names") or meta.get("class_names", {})

            # For built-ins the catalogue is the authoritative source for all
            # training-related parameters.  inspect_audio_onnx provides sensible
            # auto-detected values as a fallback for custom uploads only.
            def _cat(key, fallback=0):
                """Catalogue hint → ONNX-inspected value → fallback."""
                return meta.get(key, fallback) or info.get(key, fallback)

            n_mels = int(_cat("n_mels"))
            model_type = meta.get("model_type") or info.get("model_type", "mel_cnn")
            fixed_time = int(_cat("fixed_time"))
            target_sr = int(_cat("target_sr"))
            n_fft = int(_cat("n_fft"))
            win_length = int(meta.get("win_length", 0))
            hop_length = int(_cat("hop_length"))
            fmin = float(meta.get("fmin", 0.0))
            fmax = float(meta.get("fmax", 0.0))
            mel_transpose = bool(meta.get("mel_transpose", info.get("mel_transpose", False)))
            mel_norm = meta.get("mel_norm") or info.get("mel_norm", "power_to_db")
            output_activation = meta.get("output_activation", "softmax")
            silence_rms_threshold = float(meta.get("silence_rms_threshold", 0.0))

            # Always refresh in-memory registration
            cls._register_model(name, path, class_names, n_mels, model_type, fixed_time,
                                 target_sr=target_sr, n_fft=n_fft, win_length=win_length,
                                 hop_length=hop_length,
                                 fmin=fmin, fmax=fmax,
                                 mel_transpose=mel_transpose, mel_norm=mel_norm,
                                 output_activation=output_activation,
                                 silence_rms_threshold=silence_rms_threshold)

            entry = {
                "name": name,
                "path": path,
                "n_mels": n_mels,
                "fixed_time": fixed_time,
                "target_sr": target_sr,
                "n_fft": n_fft,
                "win_length": win_length,
                "hop_length": hop_length,
                "fmin": fmin,
                "fmax": fmax,
                "mel_transpose": mel_transpose,
                "mel_norm": mel_norm,
                "output_activation": output_activation,
                "silence_rms_threshold": silence_rms_threshold,
                "num_classes": info.get("num_classes", len(class_names)),
                "model_type": model_type,
                "class_names": {str(k): v for k, v in class_names.items()},
            }
            try:
                # Always write/update built-in entries so that the registry stays in
                # sync with the catalogue (e.g. after a code update that changes
                # n_fft or hop_length for a built-in model).
                audio_models_registry.save_entry(entry)
                if name in existing:
                    logger.debug(f"[AudioBuiltin] Updated registry entry for built-in: {name}")
                else:
                    logger.info(f"[AudioBuiltin] Registered built-in model: {name} "
                                f"(model_type={model_type}, mel_norm={mel_norm}, "
                                f"output_activation={output_activation})")
            except Exception as exc:
                logger.warning(f"[AudioBuiltin] Could not persist '{name}': {exc}")

    # ------------------------------------------------------------------
    # Upload callbacks (mirrors ObjectDetection node)
    # ------------------------------------------------------------------

    def _callback_onnx_select(self, sender, data, user_data=None):
        """Handle ONNX file selection — inspect and show preview dialog."""
        logger.info(f"[AudioUpload] File dialog callback — data={data}")
        if data.get("file_name") == ".":
            return
        onnx_path = data.get("file_path_name", "")
        if not onnx_path or not os.path.isfile(onnx_path):
            logger.warning(f"[AudioUpload] No valid file: '{onnx_path}'")
            return

        try:
            meta = inspect_audio_onnx(onnx_path)
        except Exception as exc:
            logger.error(f"[AudioUpload] Inspection failed: {exc}", exc_info=True)
            try:
                dpg.delete_item(self.tag_preview_details, children_only=True)
                dpg.add_text(
                    f"Inspection error: {exc}",
                    parent=self.tag_preview_details,
                    color=(255, 100, 100, 255),
                )
                self._set_upload_preview_actions(upload_succeeded=False)
                dpg.set_value(self.tag_preview_status, "")
                dpg.show_item(self.tag_preview_window)
            except Exception:
                pass
            return

        class_names = meta.get("class_names", {})
        if not class_names:
            num_classes = meta.get("num_classes", 0)
            if num_classes > 0:
                class_names = {i: f"class_{i}" for i in range(num_classes)}

        self._pending_onnx_path = onnx_path
        self._pending_meta = meta
        self._pending_class_names = class_names

        # Populate preview dialog
        base_name = os.path.splitext(os.path.basename(onnx_path))[0]
        dpg.set_value(self.tag_preview_name, base_name)
        dpg.delete_item(self.tag_preview_details, children_only=True)

        n_mels = meta.get("n_mels", 0)
        num_cls = meta.get("num_classes", len(class_names))
        in_shape = meta.get("input_shape", [])
        out_shape = meta.get("output_shape", [])
        target_sr_val = int(meta.get("target_sr", 0))
        n_fft_val = int(meta.get("n_fft", 0))
        hop_length_val = int(meta.get("hop_length", 0))
        mel_transpose_val = bool(meta.get("mel_transpose", False))
        mel_norm_val = meta.get("mel_norm", "power_to_db")
        output_act_val = meta.get("output_activation", "softmax")

        model_type = meta.get("model_type", "mel_cnn")
        dpg.add_text(f"Model type        : {model_type}  (auto-detected)", parent=self.tag_preview_details)
        dpg.add_text(f"Input shape       : {in_shape}", parent=self.tag_preview_details)
        dpg.add_text(f"Output shape      : {out_shape}", parent=self.tag_preview_details)
        dpg.add_text(
            f"N Mels            : {n_mels if n_mels > 0 else '(dynamic — use UI value)'}",
            parent=self.tag_preview_details,
        )
        dpg.add_text(
            f"Target SR         : {target_sr_val if target_sr_val > 0 else '(not set — no resampling)'}",
            parent=self.tag_preview_details,
        )
        dpg.add_text(
            f"N FFT             : {n_fft_val if n_fft_val > 0 else f'(not set — default {_DEFAULT_N_FFT})'}",
            parent=self.tag_preview_details,
        )
        dpg.add_text(
            f"Hop length        : {hop_length_val if hop_length_val > 0 else f'(not set — default {_DEFAULT_HOP_LENGTH})'}",
            parent=self.tag_preview_details,
        )
        dpg.add_text(
            f"Mel layout        : {'time-first (transpose)' if mel_transpose_val else 'mels-first (standard)'}",
            parent=self.tag_preview_details,
        )
        dpg.add_text(
            f"Mel norm          : {mel_norm_val}",
            parent=self.tag_preview_details,
        )
        dpg.add_text(
            f"Output activation : {output_act_val}",
            parent=self.tag_preview_details,
        )
        dpg.add_text(f"Num classes       : {num_cls}", parent=self.tag_preview_details)

        if class_names:
            dpg.add_text("Class list:", parent=self.tag_preview_details)
            max_show = 40
            for cid, cname in sorted(class_names.items(), key=lambda x: x[0])[:max_show]:
                dpg.add_text(f"  {cid}: {cname}", parent=self.tag_preview_details)
            if len(class_names) > max_show:
                dpg.add_text(
                    f"  … and {len(class_names) - max_show} more classes",
                    parent=self.tag_preview_details,
                )
        else:
            dpg.add_text(
                "(No class names found — ESC-50 labels will be used)",
                parent=self.tag_preview_details,
                color=(255, 200, 100, 255),
            )

        self._set_upload_preview_actions(upload_succeeded=False)
        dpg.set_value(self.tag_preview_status, "")
        dpg.show_item(self.tag_preview_window)

    def _set_upload_preview_actions(self, upload_succeeded: bool):
        """Toggle confirm/cancel ↔ quit buttons."""
        dpg.configure_item(self.tag_preview_confirm, show=not upload_succeeded)
        dpg.configure_item(self.tag_preview_cancel, show=not upload_succeeded)
        dpg.configure_item(self.tag_preview_quit, show=upload_succeeded)

    def _close_upload_preview(self):
        dpg.hide_item(self.tag_preview_window)

    def _do_confirm_upload(self):
        """Copy ONNX to models/ dir, register, update combobox."""
        onnx_path = getattr(self, "_pending_onnx_path", None)
        meta = getattr(self, "_pending_meta", None)
        class_names = getattr(self, "_pending_class_names", None)

        if not onnx_path or meta is None:
            dpg.set_value(self.tag_preview_status, "No pending upload — select a file first.")
            return

        custom_name = dpg.get_value(self.tag_preview_name).strip()
        if not custom_name:
            custom_name = os.path.splitext(os.path.basename(onnx_path))[0]

        # Copy ONNX file to local models/ directory
        os.makedirs(_UPLOADS_DIR, exist_ok=True)
        dest_path = onnx_path
        try:
            basename = os.path.basename(onnx_path)
            candidate = os.path.join(_UPLOADS_DIR, basename)
            if os.path.abspath(onnx_path) != os.path.abspath(candidate):
                shutil.copy2(onnx_path, candidate)
                dest_path = candidate
                logger.info(f"[AudioUpload] Copied ONNX to: {dest_path}")
            else:
                logger.info("[AudioUpload] Source and destination are the same — skipping copy.")
        except Exception as exc:
            logger.warning(f"[AudioUpload] Could not copy ONNX: {exc}")
            dest_path = onnx_path

        try:
            Node._finalise_upload(self, dest_path, meta, class_names, custom_name=custom_name)
            dpg.set_value(
                self.tag_preview_status,
                f"\u2713 Model '{custom_name}' added successfully!",
            )
            self._set_upload_preview_actions(upload_succeeded=True)
            logger.info(f"[AudioUpload] Upload confirmed for '{custom_name}'.")
        except Exception as exc:
            logger.error(f"[AudioUpload] Finalise failed: {exc}", exc_info=True)
            dpg.set_value(self.tag_preview_status, f"\u2717 Upload failed: {exc}")
            self._set_upload_preview_actions(upload_succeeded=False)

        self._pending_onnx_path = None
        self._pending_meta = None
        self._pending_class_names = None

    @staticmethod
    def _finalise_upload(node, onnx_path: str, meta: dict, class_names: dict,
                          custom_name: str = None):
        """Register model in runtime dicts + persistent registry + update combobox."""
        base = custom_name if custom_name else os.path.splitext(os.path.basename(onnx_path))[0]
        name = base
        counter = 1
        while name in Node._model_path_setting:
            name = f"{base}_{counter}"
            counter += 1

        n_mels = meta.get("n_mels", 0)
        num_classes = meta.get("num_classes", len(class_names))
        model_type = meta.get("model_type", "mel_cnn")
        fixed_time = meta.get("fixed_time", 0)
        target_sr = int(meta.get("target_sr", 0))
        n_fft = int(meta.get("n_fft", 0))
        win_length = int(meta.get("win_length", 0))
        hop_length = int(meta.get("hop_length", 0))
        fmin = float(meta.get("fmin", 0.0))
        fmax = float(meta.get("fmax", 0.0))
        mel_transpose = bool(meta.get("mel_transpose", False))
        mel_norm = meta.get("mel_norm", "power_to_db")
        output_activation = meta.get("output_activation", "softmax")
        silence_rms_threshold = float(meta.get("silence_rms_threshold", 0.0))

        logger.info(
            f"[AudioUpload] Registering '{name}' — "
            f"n_mels={n_mels}, classes={num_classes}, model_type={model_type}, "
            f"fixed_time={fixed_time}, target_sr={target_sr if target_sr > 0 else 'none'}, "
            f"n_fft={n_fft if n_fft > 0 else 'default'}, "
            f"win_length={win_length if win_length > 0 else 'same as n_fft'}, "
            f"hop_length={hop_length if hop_length > 0 else 'default'}, "
            f"fmin={fmin if fmin > 0 else 'default'}, fmax={fmax if fmax > 0 else 'default'}, "
            f"mel_norm={mel_norm}, output_activation={output_activation}"
        )

        Node._register_model(name, onnx_path, class_names, n_mels, model_type, fixed_time,
                              target_sr=target_sr, n_fft=n_fft, win_length=win_length,
                              hop_length=hop_length,
                              fmin=fmin, fmax=fmax,
                              mel_transpose=mel_transpose, mel_norm=mel_norm,
                              output_activation=output_activation,
                              silence_rms_threshold=silence_rms_threshold)

        registry_entry = {
            "name": name,
            "path": onnx_path,
            "class_names": {str(k): v for k, v in class_names.items()},
            "n_mels": n_mels,
            "fixed_time": fixed_time,
            "target_sr": target_sr,
            "n_fft": n_fft,
            "win_length": win_length,
            "hop_length": hop_length,
            "fmin": fmin,
            "fmax": fmax,
            "mel_transpose": mel_transpose,
            "mel_norm": mel_norm,
            "output_activation": output_activation,
            "silence_rms_threshold": silence_rms_threshold,
            "num_classes": num_classes,
            "model_type": model_type,
        }
        try:
            audio_models_registry.save_entry(registry_entry)
            logger.info(f"[AudioUpload] Registry entry saved for '{name}'.")
        except Exception as exc:
            logger.warning(f"[AudioUpload] Could not save registry entry for '{name}': {exc}")

        # Update the model combobox
        try:
            current_items = dpg.get_item_configuration(node.tag_model_combo).get("items", [])
            if name not in current_items:
                current_items = list(current_items) + [name]
            dpg.configure_item(node.tag_model_combo, items=current_items, default_value=name)
            logger.info(f"[AudioUpload] Model combo updated — '{name}' selected.")
        except Exception as exc:
            logger.warning(f"[AudioUpload] Could not update model combo: {exc}")

    # ------------------------------------------------------------------
    # ONNX session management
    # ------------------------------------------------------------------

    def _ensure_session(self, model_name: str, use_gpu: bool = False) -> bool:
        """Load (or reuse) an onnxruntime session for the named model."""
        if self._session is not None and model_name == self._active_model_name:
            return True

        path = Node._model_path_setting.get(model_name, "")
        if not path or not os.path.isfile(path):
            return False

        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if use_gpu else
            ["CPUExecutionProvider"]
        )
        try:
            self._session = make_session(path, providers=providers)
            self._input_name = self._session.get_inputs()[0].name
            self._active_model_name = model_name
            logger.info(f"[AudioClassification] Session ready: {model_name}")
            return True
        except Exception as exc:
            logger.error(
                f"[AudioClassification] Failed to create session for '{model_name}': {exc}",
                exc_info=True,
            )
            self._session = None
            return False

    # ------------------------------------------------------------------
    # Main update loop
    # ------------------------------------------------------------------

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        _tn = str(node_id) + ":" + self.node_tag
        output_img_tag = _tn + ":" + self.TYPE_IMAGE + ":Output01Value"
        output_json_tag = _tn + ":" + self.TYPE_JSON + ":OutputJsonValue"
        output_time_tag = _tn + ":" + self.TYPE_TIME_MS + ":Output02Value"

        if self._opencv_setting_dict is None:
            small_window_w, small_window_h = 240, 135
            use_pref_counter = False
            use_gpu = False
        else:
            small_window_w = self._opencv_setting_dict["process_width"]
            small_window_h = self._opencv_setting_dict["process_height"]
            use_pref_counter = self._opencv_setting_dict["use_pref_counter"]
            use_gpu = self._opencv_setting_dict.get("use_gpu", False)

        # ---- Read options ----
        try:
            model_name = dpg_get_value(_tn + ":OPT:ModelCombo") or ""
            n_mels_ui = int(dpg_get_value(_tn + ":OPT:NMels") or _DEFAULT_N_MELS)
            max_sec = int(dpg_get_value(_tn + ":OPT:MaxSec") or _DEFAULT_MAX_SEC)
            top_k = int(dpg_get_value(_tn + ":OPT:TopK") or _DEFAULT_TOP_K)
            label_source = dpg_get_value(_tn + ":OPT:LabelSource") or "ONNX metadata"
        except Exception as exc:
            logger.debug(f"[AudioClassification] Could not read DPG values: {exc}")
            model_name = ""
            n_mels_ui = _DEFAULT_N_MELS
            max_sec = _DEFAULT_MAX_SEC
            top_k = _DEFAULT_TOP_K
            label_source = "ONNX metadata"

        # Determine effective n_mels: prefer the value baked into the model
        n_mels_model = Node._model_n_mels.get(model_name, 0)
        n_mels = n_mels_model if n_mels_model > 0 else n_mels_ui

        # Implicit model type — read from registry (no UI combo)
        model_type = Node._model_type.get(model_name, "mel_cnn")

        # Per-model STFT and mel parameters (0/default = use module-level defaults)
        model_n_fft = Node._model_n_fft.get(model_name, 0)
        model_win_length = Node._model_win_length.get(model_name, 0)
        model_hop_length = Node._model_hop_length.get(model_name, 0)
        model_fmin = Node._model_fmin.get(model_name, 0.0)
        model_fmax = Node._model_fmax.get(model_name, 0.0)
        model_mel_norm = Node._model_mel_norm.get(model_name, "power_to_db")
        model_mel_transpose = Node._model_mel_transpose.get(model_name, False)
        model_output_activation = Node._model_output_activation.get(model_name, "softmax")
        model_silence_rms_threshold = Node._model_silence_rms_threshold.get(model_name, 0.0)

        # Sync N_Mels UI to match model
        if n_mels_model > 0 and str(n_mels_model) in [str(v) for v in _N_MELS_OPTIONS]:
            try:
                dpg_set_value(_tn + ":OPT:NMels", str(n_mels_model))
            except Exception:
                pass

        # ---- Choose class-name dict ----
        model_class_names = Node._model_class_names.get(model_name, {})
        if label_source == "ONNX metadata" and model_class_names:
            class_names = model_class_names
        elif label_source == "YAMNet (built-in)":
            class_names = _YAMNET_NAMES
        else:
            class_names = _ESC50_NAMES

        # ---- Get AUDIO input ----
        audio_data = None
        sample_rate = _DEFAULT_SR
        _input_audio_entry = None  # Full entry dict — preserved for passthrough metadata

        for connection_info in connection_list:
            parts = connection_info[0].split(":")
            if len(parts) < 3:
                continue
            if parts[2] == self.TYPE_AUDIO:
                src_key = ":".join(parts[:2])
                entry = node_audio_dict.get(src_key, None)
                if entry is not None:
                    if isinstance(entry, dict):
                        audio_data = entry.get("data", None)
                        sample_rate = entry.get("sample_rate", _DEFAULT_SR)
                        _input_audio_entry = entry
                    elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                        audio_data, sample_rate = entry
                break

        if audio_data is None:
            return {"image": None, "json": None, "audio": None}

        # ---- Performance timer start ----
        if use_pref_counter:
            start_time = time.monotonic()

        # Preserve the original (unmodified) audio for the passthrough output.
        # Resampling below is only for feeding the ONNX model; the passthrough
        # must always carry the original audio at the original sample rate so
        # downstream nodes (e.g. VideoWriter) receive full-fidelity audio.
        passthrough_audio_data = audio_data
        passthrough_sample_rate = sample_rate

        # ---- Resample audio to match the model's expected sample rate ----
        # When the microphone (or other audio source) runs at a different rate from
        # the SR used during model training, the mel spectrogram will have different
        # frequency-time characteristics → wrong predictions.  We transparently
        # resample so the model always receives audio at its expected rate.
        # NOTE: only the local mel_audio_data / mel_sample_rate variables are
        # modified here; passthrough_audio_data / passthrough_sample_rate stay
        # at the original values.
        mel_audio_data = audio_data
        mel_sample_rate = sample_rate
        target_sr_for_model = Node._model_target_sr.get(model_name, 0)
        if target_sr_for_model > 0 and int(sample_rate) != target_sr_for_model:
            librosa = _get_librosa()
            if librosa is not None:
                y_rs = np.asarray(audio_data, dtype=np.float32)
                if y_rs.ndim > 1:
                    y_rs = np.mean(y_rs, axis=-1)
                orig_sr = int(sample_rate)
                mel_audio_data = librosa.resample(
                    y_rs,
                    orig_sr=orig_sr,
                    target_sr=target_sr_for_model,
                )
                mel_sample_rate = target_sr_for_model
                logger.debug(
                    f"[AudioClassification] Resampled audio "
                    f"{orig_sr} → {target_sr_for_model} Hz for model '{model_name}'"
                )

        # ---- Build mel array ----
        mel_arr = audio_to_mel_array(
            mel_audio_data, mel_sample_rate, n_mels, max_sec,
            n_fft=model_n_fft if model_n_fft > 0 else None,
            hop_length=model_hop_length if model_hop_length > 0 else None,
            win_length=model_win_length if model_win_length > 0 else None,
            mel_norm=model_mel_norm,
            fmin=model_fmin,
            fmax=model_fmax,
        )
        if mel_arr is None:
            # Even when the spectrogram cannot be built (e.g. silence or audio
            # too short), the original audio must still flow downstream so the
            # VideoWriter can include it in the final recording.
            return {
                "image": None,
                "json": None,
                "audio": {
                    "data": passthrough_audio_data,
                    "sample_rate": passthrough_sample_rate,
                },
            }

        # ---- Render mel as preview (shown even without a model) ----
        bgr_preview = mel_array_to_bgr_image(mel_arr, small_window_w, small_window_h)
        result_json = None

        # ---- Silence / energy gate ----
        # When audio is near-silent the mel spectrogram is a flat matrix at
        # log(~0 + 1e-3) = -6.9.  For YAMNet (and similar models) this flat
        # pattern consistently maps to "Sound effect" = 1.0, because the
        # model was never explicitly trained on "silence" and uses that class
        # as a catch-all for uncertain inputs.  Skipping inference avoids the
        # false positive and reports a meaningful "Silence" label instead.
        _is_silent = False
        if model_silence_rms_threshold > 0.0 and model_name:
            y_check = np.asarray(audio_data, dtype=np.float32)
            if y_check.ndim > 1:
                y_check = np.mean(y_check, axis=-1)
            rms = float(np.sqrt(np.mean(y_check ** 2)))
            if rms < model_silence_rms_threshold:
                _is_silent = True
                logger.debug(
                    f"[AudioClassification] Silence gate: RMS={rms:.2e} < "
                    f"threshold={model_silence_rms_threshold:.2e} — skipping inference"
                )
                silence_label = "Silence"
                bgr_preview = overlay_predictions(bgr_preview, [(silence_label, 0.0)])
                result_json = {
                    "scores": [0.0],
                    "class_ids": [-1],
                    "class_names": {"-1": silence_label},
                    "score_th": 0.0,
                    "model": model_name,
                    "n_mels": n_mels,
                    "sample_rate": sample_rate,
                }
                try:
                    dpg.configure_item(output_json_tag, label=silence_label)
                except Exception:
                    pass

        # ---- ONNX inference ----
        if not _is_silent and model_name and self._ensure_session(model_name, use_gpu=use_gpu):
            try:
                if model_type == "waveform":
                    # Waveform pipeline: flatten audio, feed as (1, N) or (N,) float32
                    y = np.asarray(audio_data, dtype=np.float32)
                    if y.ndim > 1:
                        y = np.mean(y, axis=-1)
                    inp_shape = self._session.get_inputs()[0].shape
                    # If model expects 2-D (batch, samples) wrap accordingly
                    if len(inp_shape) == 2:
                        x = y[np.newaxis].astype(np.float32)  # (1, N)
                    else:
                        x = y.astype(np.float32)              # (N,)
                    outputs = self._session.run(None, {self._input_name: x})
                    logits = outputs[0].flatten().astype(np.float32)
                else:
                    # mel_cnn pipeline (default)
                    fixed_t = Node._model_fixed_time.get(model_name, 0)
                    if model_mel_transpose and fixed_t > 0:
                        # Time-major format: model expects (batch, ch, TIME, MELS)
                        # mel_arr shape: (1, n_mels, T) = e.g. (1, 64, 497)
                        # → take LAST fixed_t frames from T dimension (newest audio)
                        # → transpose to (TIME, MELS) = (96, 64)
                        # → add batch/channel dims → (1, 1, 96, 64)
                        t_actual = mel_arr.shape[2]
                        if t_actual >= fixed_t:
                            mel_patch = mel_arr[:, :, -fixed_t:]   # (1, n_mels, fixed_t)
                        else:
                            pad_w = fixed_t - t_actual
                            mel_patch = np.pad(mel_arr, ((0,0),(0,0),(pad_w, 0)),
                                               mode="constant")  # pre-pad (silence at start)
                        # Transpose last two dims: (1, n_mels, fixed_t) → (1, fixed_t, n_mels)
                        mel_transposed = mel_patch.transpose(0, 2, 1)   # (1, TIME, MELS)
                        x = mel_transposed[np.newaxis].astype(np.float32)  # (1, 1, TIME, MELS)
                    else:
                        # Mels-first format (standard ESC-50 style):
                        # model expects (batch, ch, MELS, TIME)
                        x = mel_arr[np.newaxis].astype(np.float32)  # (1, 1, n_mels, T)
                        # Crop / pad the time axis when the model requires a fixed T.
                        # Take the LAST fixed_t frames so that inference always uses the
                        # most recent audio (the rolling buffer appends new samples at the
                        # end, so the newest frames are at the right of the time axis).
                        if fixed_t > 0:
                            t_actual = x.shape[3]
                            if t_actual > fixed_t:
                                x = x[:, :, :, -fixed_t:]   # newest audio is at the end
                            elif t_actual < fixed_t:
                                pad_w = fixed_t - t_actual
                                x = np.pad(x, ((0, 0), (0, 0), (0, 0), (0, pad_w)),
                                           mode="constant")
                    outputs = self._session.run(None, {self._input_name: x})
                    logits = outputs[0].flatten().astype(np.float32)

                # ---- Convert raw model output to probability scores ----
                if model_output_activation == "sigmoid":
                    # The model's output is already per-class sigmoid probabilities
                    # (e.g. Qualcomm YAMNet: class_scores in [0,1], sum ≠ 1).
                    # Using these directly preserves the confidence signal.
                    # Applying softmax on top of sigmoid outputs is incorrect and
                    # causes the predictions to look uniformly random.
                    probs = np.clip(logits, 0.0, 1.0)
                else:
                    # Standard logit → softmax (ESC-50 style)
                    logits -= logits.max()  # numerical stability
                    probs = np.exp(logits)
                    probs /= probs.sum()

                num_classes = len(probs)
                actual_k = min(top_k, num_classes)
                top_ids = np.argsort(probs)[::-1][:actual_k]
                top_scores = probs[top_ids]

                predictions = [
                    (class_names.get(int(idx), f"class_{idx}"), float(score))
                    for idx, score in zip(top_ids, top_scores)
                ]

                bgr_preview = overlay_predictions(bgr_preview, predictions)

                result_json = {
                    "scores": [float(top_scores[r]) for r in range(actual_k)],
                    "class_ids": [int(top_ids[r]) for r in range(actual_k)],
                    "class_names": {
                        str(int(top_ids[r])): class_names.get(int(top_ids[r]), f"class_{top_ids[r]}")
                        for r in range(actual_k)
                    },
                    "score_th": 0.0,
                    "model": model_name,
                    "n_mels": n_mels,
                    "sample_rate": sample_rate,
                }

                # Update JSON button label with top-1 result summary
                top_label = class_names.get(int(top_ids[0]), f"class_{top_ids[0]}")
                top_score = float(top_scores[0])
                try:
                    dpg.configure_item(
                        output_json_tag,
                        label=f"{top_label} ({top_score:.2f})",
                    )
                except Exception:
                    pass

            except Exception as exc:
                logger.error(f"[AudioClassification] Inference error: {exc}", exc_info=True)

        # ---- Update texture ----
        try:
            texture = self.convert_cv_to_dpg(bgr_preview, small_window_w, small_window_h)
            dpg_set_value(output_img_tag, texture)
        except Exception as exc:
            logger.debug(f"[AudioClassification] Could not set texture: {exc}")

        # ---- Performance timer end ----
        if use_pref_counter:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            try:
                dpg_set_value(output_time_tag, str(elapsed_ms).zfill(4) + "ms")
            except Exception:
                pass

        if passthrough_audio_data is not None:
            _passthrough = {
                "data": passthrough_audio_data,
                "sample_rate": passthrough_sample_rate,
            }
            # Preserve sync metadata (chunk_index, step_duration, pts_ms) from the
            # input audio entry so that downstream deduplication in VideoWriter and
            # ImageConcat works correctly when AudioClassification is in the chain.
            if isinstance(_input_audio_entry, dict):
                for _k in ("chunk_index", "step_duration", "pts_ms"):
                    if _k in _input_audio_entry:
                        _passthrough[_k] = _input_audio_entry[_k]
            _audio_out = _passthrough
        else:
            _audio_out = None
        return {
            "image": bgr_preview,
            "json": result_json,
            "audio": _audio_out,
        }

    # ------------------------------------------------------------------
    # Settings persistence (export / import JSON)
    # ------------------------------------------------------------------

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        _tn = str(node_id) + ":" + self.node_tag
        try:
            pos = dpg.get_item_pos(_tn)
        except Exception:
            pos = [0, 0]

        def _safe(tag, default=""):
            try:
                return dpg_get_value(tag)
            except Exception:
                return default

        return {
            "ver": self._ver,
            "pos": pos,
            "model_name": _safe(_tn + ":OPT:ModelCombo", ""),
            "n_mels": _safe(_tn + ":OPT:NMels", str(_DEFAULT_N_MELS)),
            "max_sec": _safe(_tn + ":OPT:MaxSec", str(_DEFAULT_MAX_SEC)),
            "top_k": _safe(_tn + ":OPT:TopK", str(_DEFAULT_TOP_K)),
            "label_source": _safe(_tn + ":OPT:LabelSource", "ONNX metadata"),
        }

    def set_setting_dict(self, node_id, setting_dict):
        _tn = str(node_id) + ":" + self.node_tag

        def _safe_set(tag, value):
            try:
                dpg_set_value(tag, value)
            except Exception:
                pass

        # Reload registry so previously-registered models are available
        Node._load_models_from_registry()

        model_name = setting_dict.get("model_name", "")
        if model_name and model_name in Node._model_path_setting:
            _safe_set(_tn + ":OPT:ModelCombo", model_name)
        _safe_set(_tn + ":OPT:NMels", setting_dict.get("n_mels", str(_DEFAULT_N_MELS)))
        _safe_set(_tn + ":OPT:MaxSec", setting_dict.get("max_sec", str(_DEFAULT_MAX_SEC)))
        _safe_set(_tn + ":OPT:TopK", setting_dict.get("top_k", str(_DEFAULT_TOP_K)))
        _safe_set(_tn + ":OPT:LabelSource", setting_dict.get("label_source", "ONNX metadata"))


# Load registry entries at module-import time so models appear in the combo
# even before the first node is added.
Node._ensure_builtin_models()
Node._load_models_from_registry()

