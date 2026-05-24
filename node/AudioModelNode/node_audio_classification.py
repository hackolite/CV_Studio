#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AudioClassification node — ONNX audio classification pipeline.

Takes raw audio (from AUDIO connection) → mel spectrogram → ONNX model
→ top-K class predictions output as JSON + spectrogram overlay image.

Model format: ONNX (.onnx), expected input shape (1, 1, n_mels, T) float32.
Inference is performed via onnxruntime — no PyTorch required at runtime.
"""
import ast
import json
import os
import time
import copy

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode
from node.DLNode.object_detection.onnx_session_utils import make_session
from src.utils.logging import get_logger

logger = get_logger(__name__)

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
_DEFAULT_TOP_K = 5

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

    mel = librosa.feature.melspectrogram(y=y, sr=sample_rate, n_mels=n_mels)
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
        node.tag_n_mels = _tn + ":OPT:NMels"
        node.tag_max_sec = _tn + ":OPT:MaxSec"
        node.tag_top_k = _tn + ":OPT:TopK"
        node.tag_model_path_text = _tn + ":OPT:ModelPathText"
        node.tag_model_info_text = _tn + ":OPT:ModelInfoText"
        node.tag_label_source = _tn + ":OPT:LabelSource"

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

        # ---- File dialog for ONNX model ----
        onnx_dialog_tag = _tn + ":OnnxDialog"
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            modal=True,
            height=400,
            callback=node._callback_model_select,
            user_data=node,
            tag=onnx_dialog_tag,
        ):
            dpg.add_file_extension("ONNX model (*.onnx){.onnx}")
            dpg.add_file_extension("", color=(150, 255, 150, 255))
        node.tag_onnx_dialog = onnx_dialog_tag

        # ---- File dialog for custom label JSON ----
        lbl_dialog_tag = _tn + ":LblDialog"
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            modal=True,
            height=400,
            callback=node._callback_label_select,
            user_data=node,
            tag=lbl_dialog_tag,
        ):
            dpg.add_file_extension("JSON (*.json){.json}")
            dpg.add_file_extension("", color=(150, 255, 150, 255))
        node.tag_lbl_dialog = lbl_dialog_tag

        # ---- Yellow button theme ----
        with dpg.theme() as yellow_btn_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 220, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 235, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (220, 190, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))

        # ---- Node UI ----
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
                    items=["ONNX metadata", "ESC-50 (built-in)", "Custom JSON"],
                    default_value="ONNX metadata",
                    width=small_window_w,
                    label="Labels",
                    tag=node.tag_label_source,
                    callback=callback,
                )

            # ---- Model path display ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:ModelPath",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    default_value="(no model loaded)",
                    width=small_window_w,
                    readonly=True,
                    tag=node.tag_model_path_text,
                )

            # ---- Model info (auto-populated after ONNX load) ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:ModelInfo",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    default_value="",
                    width=small_window_w,
                    readonly=True,
                    tag=node.tag_model_info_text,
                )

            # ---- Load ONNX model button ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:LoadModel",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                def _open_onnx_dialog(sender, app_data, user_data):
                    dpg.show_item(onnx_dialog_tag)

                load_btn = dpg.add_button(
                    label=u"📂 Load ONNX model",
                    width=small_window_w,
                    callback=_open_onnx_dialog,
                )
                dpg.bind_item_theme(load_btn, yellow_btn_theme)

            # ---- Load labels button ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:LoadLabels",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                def _open_lbl_dialog(sender, app_data, user_data):
                    dpg.show_item(lbl_dialog_tag)

                lbl_btn = dpg.add_button(
                    label=u"📋 Load labels (JSON)",
                    width=small_window_w,
                    callback=_open_lbl_dialog,
                )
                dpg.bind_item_theme(lbl_btn, yellow_btn_theme)

            # ---- JSON output ----
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                with dpg.theme() as yellow_out_theme:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

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

        return node


# ===========================================================================
# Node — ONNX inference + update logic
# ===========================================================================

class Node(BaseNode):
    _ver = "0.0.2"

    node_label = "AudioClassification"
    node_tag = "AudioClassification"

    _opencv_setting_dict = None

    # Runtime state (per-instance)
    _session = None          # onnxruntime.InferenceSession
    _input_name = None       # str
    _model_path = None       # str
    _onnx_num_classes = 0    # int, detected from ONNX output shape
    _onnx_n_mels = 0         # int, detected from ONNX input shape
    _onnx_class_names = None # dict {int: str} from ONNX metadata
    _custom_class_names = None  # dict loaded from custom JSON file

    def __init__(self):
        self._session = None
        self._input_name = None
        self._model_path = None
        self._onnx_num_classes = 0
        self._onnx_n_mels = 0
        self._onnx_class_names = None
        self._custom_class_names = None

    # ------------------------------------------------------------------
    # File-dialog callbacks
    # ------------------------------------------------------------------

    def _callback_model_select(self, sender, data, user_data=None):
        if data.get("file_name") == ".":
            return
        path = data.get("file_path_name", "")
        if not path or not os.path.isfile(path):
            return

        # Inspect the ONNX model
        try:
            meta = inspect_audio_onnx(path)
        except Exception as exc:
            logger.error(f"[AudioClassification] ONNX inspection failed: {exc}")
            return

        # Update UI
        try:
            dpg_set_value(self.tag_model_path_text, path)
            info = f"In:{meta['input_shape']}  Out:{meta['output_shape']}"
            dpg_set_value(self.tag_model_info_text, info)
            # Auto-populate N_Mels from ONNX input shape
            if meta["n_mels"] > 0:
                dpg_set_value(self.tag_n_mels, str(meta["n_mels"]))
        except Exception:
            pass

        # Store metadata and invalidate session
        self._model_path = path
        self._onnx_num_classes = meta["num_classes"]
        self._onnx_n_mels = meta["n_mels"]
        self._onnx_class_names = meta["class_names"] if meta["class_names"] else None
        self._session = None  # force reload on next update
        logger.info(
            f"[AudioClassification] ONNX model selected: {path} "
            f"(n_mels={meta['n_mels']}, num_classes={meta['num_classes']}, "
            f"embedded_labels={len(meta['class_names'])})"
        )

    def _callback_label_select(self, sender, data, user_data=None):
        if data.get("file_name") == ".":
            return
        path = data.get("file_path_name", "")
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                self._custom_class_names = {int(k): str(v) for k, v in raw.items()}
            elif isinstance(raw, list):
                self._custom_class_names = {i: str(v) for i, v in enumerate(raw)}
            logger.info(f"[AudioClassification] Loaded {len(self._custom_class_names)} labels from {path}")
        except Exception as exc:
            logger.error(f"[AudioClassification] Failed to load labels: {exc}")

    # ------------------------------------------------------------------
    # ONNX session loading
    # ------------------------------------------------------------------

    def _ensure_session(self, model_path: str, use_gpu: bool = False) -> bool:
        """Load (or reuse) an onnxruntime InferenceSession."""
        if self._session is not None and model_path == self._model_path:
            return True

        if not model_path or not os.path.isfile(model_path):
            return False

        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if use_gpu else
            ["CPUExecutionProvider"]
        )
        try:
            self._session = make_session(model_path, providers=providers)
            self._input_name = self._session.get_inputs()[0].name
            self._model_path = model_path
            logger.info(f"[AudioClassification] ONNX session ready: {model_path}")
            return True
        except Exception as exc:
            logger.error(f"[AudioClassification] Failed to create ONNX session: {exc}", exc_info=True)
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
            n_mels = int(dpg_get_value(_tn + ":OPT:NMels") or _DEFAULT_N_MELS)
            max_sec = int(dpg_get_value(_tn + ":OPT:MaxSec") or _DEFAULT_MAX_SEC)
            top_k = int(dpg_get_value(_tn + ":OPT:TopK") or _DEFAULT_TOP_K)
            label_source = dpg_get_value(_tn + ":OPT:LabelSource") or "ONNX metadata"
            model_path_ui = dpg_get_value(_tn + ":OPT:ModelPathText") or ""
        except Exception as exc:
            logger.debug(f"[AudioClassification] Could not read DPG values: {exc}")
            n_mels = _DEFAULT_N_MELS
            max_sec = _DEFAULT_MAX_SEC
            top_k = _DEFAULT_TOP_K
            label_source = "ONNX metadata"
            model_path_ui = ""

        if model_path_ui in ("(no model loaded)", ""):
            model_path_ui = ""

        # Sync model path from UI on session restore
        if model_path_ui and model_path_ui != self._model_path:
            self._session = None

        # ---- Choose class-name dict ----
        if label_source == "Custom JSON" and self._custom_class_names:
            class_names = self._custom_class_names
        elif label_source == "ONNX metadata" and self._onnx_class_names:
            class_names = self._onnx_class_names
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

        # ---- Render mel as preview image (shown even without a model) ----
        bgr_preview = mel_array_to_bgr_image(mel_arr, small_window_w, small_window_h)
        result_json = None

        # ---- ONNX inference ----
        if model_path_ui and self._ensure_session(model_path_ui, use_gpu=use_gpu):
            try:
                # Input shape expected by the model: (1, 1, n_mels, T)
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
                    "n_mels": n_mels,
                    "sample_rate": sample_rate,
                }
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
            "n_mels": _safe(_tn + ":OPT:NMels", str(_DEFAULT_N_MELS)),
            "max_sec": _safe(_tn + ":OPT:MaxSec", str(_DEFAULT_MAX_SEC)),
            "top_k": _safe(_tn + ":OPT:TopK", str(_DEFAULT_TOP_K)),
            "label_source": _safe(_tn + ":OPT:LabelSource", "ONNX metadata"),
            "model_path": _safe(_tn + ":OPT:ModelPathText", ""),
        }

    def set_setting_dict(self, node_id, setting_dict):
        _tn = str(node_id) + ":" + self.node_tag

        def _safe_set(tag, value):
            try:
                dpg_set_value(tag, value)
            except Exception:
                pass

        _safe_set(_tn + ":OPT:NMels", setting_dict.get("n_mels", str(_DEFAULT_N_MELS)))
        _safe_set(_tn + ":OPT:MaxSec", setting_dict.get("max_sec", str(_DEFAULT_MAX_SEC)))
        _safe_set(_tn + ":OPT:TopK", setting_dict.get("top_k", str(_DEFAULT_TOP_K)))
        _safe_set(_tn + ":OPT:LabelSource", setting_dict.get("label_source", "ONNX metadata"))
        model_path = setting_dict.get("model_path", "")
        if model_path and model_path != "(no model loaded)":
            _safe_set(_tn + ":OPT:ModelPathText", model_path)
