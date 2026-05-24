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

_N_MELS_OPTIONS = [64, 128, 256]
_MAX_SEC_OPTIONS = [1, 2, 3, 5, 10]
_TOP_K_OPTIONS = [1, 3, 5, 10]


# ---------------------------------------------------------------------------
# ESC-50 class labels (used when no labels are embedded in the ONNX file)
# ---------------------------------------------------------------------------
try:
    from node.DLNode.classification.esc50_class_names import esc50_class_names as _ESC50_NAMES
except Exception:
    _ESC50_NAMES = {i: f"class_{i}" for i in range(50)}


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

    # Embedded class names (try "names" or "labels" metadata keys)
    class_names: dict = {}
    try:
        meta = session.get_modelmeta().custom_metadata_map
        for key in ("names", "labels"):
            if key in meta:
                raw = meta[key]
                try:
                    parsed = ast.literal_eval(raw)
                except Exception:
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        parsed = None
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

    logger.info(
        f"[AudioClassification] ONNX inspected: input={input_shape}, "
        f"output={output_shape}, n_mels={n_mels}, num_classes={num_classes}, "
        f"embedded_labels={len(class_names)}"
    )
    return {
        "input_name": inp.name,
        "input_shape": input_shape,
        "n_mels": n_mels,
        "output_name": out.name,
        "output_shape": output_shape,
        "num_classes": num_classes,
        "class_names": class_names,
    }


# ---------------------------------------------------------------------------
# Mel spectrogram helper — pure numpy, no PyTorch
# ---------------------------------------------------------------------------

def audio_to_mel_array(audio_data: np.ndarray, sample_rate: int,
                        n_mels: int, max_sec: int) -> np.ndarray:
    """Convert 1-D float32 audio → (1, n_mels, T) float32 numpy array.

    Matches the ESC-50 training pre-processing:
      - pad / crop to `max_sec * sample_rate` samples
      - librosa.feature.melspectrogram → power_to_db
    """
    librosa = _get_librosa()
    if librosa is None:
        return None

    max_len = sample_rate * max_sec

    y = np.asarray(audio_data, dtype=np.float32)
    if y.ndim > 1:
        y = np.mean(y, axis=-1)

    if len(y) < max_len:
        y = np.pad(y, (0, max_len - len(y)))
    else:
        y = y[:max_len]

    mel = librosa.feature.melspectrogram(
        y=y, sr=sample_rate, n_mels=n_mels,
        n_fft=_DEFAULT_N_FFT, hop_length=_DEFAULT_HOP_LENGTH,
    )
    mel_db = librosa.power_to_db(mel).astype(np.float32)

    return mel_db[np.newaxis]  # (1, n_mels, T)


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
                    items=["ONNX metadata", "ESC-50 (built-in)"],
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
                    label=u"📂 Add Model",
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
    _model_path_setting: dict = {}   # name → onnx file path (str)
    _model_class_names: dict = {}    # name → {int: str}
    _model_n_mels: dict = {}         # name → int (0 = use UI value)

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
    def _register_model(cls, name: str, path: str, class_names: dict, n_mels: int):
        """Add one model to the class-level runtime dictionaries."""
        cls._model_path_setting[name] = path
        cls._model_class_names[name] = class_names
        cls._model_n_mels[name] = n_mels

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
            cls._register_model(name, path, class_names, n_mels)
            logger.info(f"[AudioUpload] Loaded model from registry: {name}")

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

        dpg.add_text(f"Input shape  : {in_shape}", parent=self.tag_preview_details)
        dpg.add_text(f"Output shape : {out_shape}", parent=self.tag_preview_details)
        dpg.add_text(
            f"N Mels       : {n_mels if n_mels > 0 else '(dynamic — use UI value)'}",
            parent=self.tag_preview_details,
        )
        dpg.add_text(f"Num classes  : {num_cls}", parent=self.tag_preview_details)

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

        logger.info(
            f"[AudioUpload] Registering '{name}' — "
            f"n_mels={n_mels}, classes={num_classes}"
        )

        Node._register_model(name, onnx_path, class_names, n_mels)

        registry_entry = {
            "name": name,
            "path": onnx_path,
            "class_names": {str(k): v for k, v in class_names.items()},
            "n_mels": n_mels,
            "num_classes": num_classes,
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
        else:
            class_names = _ESC50_NAMES

        # ---- Get AUDIO input ----
        audio_data = None
        sample_rate = _DEFAULT_SR

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
                    elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                        audio_data, sample_rate = entry
                break

        if audio_data is None:
            return {"image": None, "json": None, "audio": None}

        # ---- Performance timer start ----
        if use_pref_counter:
            start_time = time.monotonic()

        # ---- Build mel array ----
        mel_arr = audio_to_mel_array(audio_data, sample_rate, n_mels, max_sec)
        if mel_arr is None:
            return {"image": None, "json": None, "audio": None}

        # ---- Render mel as preview (shown even without a model) ----
        bgr_preview = mel_array_to_bgr_image(mel_arr, small_window_w, small_window_h)
        result_json = None

        # ---- ONNX inference ----
        if model_name and self._ensure_session(model_name, use_gpu=use_gpu):
            try:
                x = mel_arr[np.newaxis].astype(np.float32)  # (1, 1, n_mels, T)

                outputs = self._session.run(None, {self._input_name: x})
                logits = outputs[0].flatten().astype(np.float32)

                # Softmax
                logits -= logits.max()
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
                    "predictions": [
                        {
                            "rank": r + 1,
                            "class_id": int(top_ids[r]),
                            "class_name": class_names.get(int(top_ids[r]), f"class_{top_ids[r]}"),
                            "score": float(top_scores[r]),
                        }
                        for r in range(actual_k)
                    ],
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

        return {"image": bgr_preview, "json": result_json, "audio": None}

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
Node._load_models_from_registry()

