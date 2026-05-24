#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AudioClassification node — ESC-50 / ResNet18 pipeline.

Takes raw audio (from AUDIO connection) → mel spectrogram → PyTorch ResNet
→ top-K class predictions output as JSON + spectrogram overlay image.

Supported backbones (1-channel input, same as ESC-50 training):
  ResNet18 / ResNet34 / ResNet50

Model file format: PyTorch state-dict (.pth) saved with torch.save(model.state_dict(), …)
"""
import os
import time
import copy

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Optional heavy imports — loaded lazily so the app starts even without them
_torch = None
_torchvision_models = None
_librosa = None


def _lazy_imports():
    global _torch, _torchvision_models, _librosa
    if _torch is None:
        try:
            import torch
            _torch = torch
        except ImportError:
            logger.error("PyTorch is not installed. AudioClassification node requires torch.")
    if _torchvision_models is None:
        try:
            from torchvision import models
            _torchvision_models = models
        except ImportError:
            logger.error("torchvision is not installed. AudioClassification node requires torchvision.")
    if _librosa is None:
        try:
            import librosa
            _librosa = librosa
        except ImportError:
            logger.error("librosa is not installed. AudioClassification node requires librosa.")


# ---------------------------------------------------------------------------
# Default hyper-parameters — match the ESC-50 + ResNet18 Colab notebook
# ---------------------------------------------------------------------------
_DEFAULT_SR = 22050
_DEFAULT_N_MELS = 128
_DEFAULT_MAX_SEC = 5
_DEFAULT_NUM_CLASSES = 50
_DEFAULT_TOP_K = 5
_DEFAULT_BACKBONE = "ResNet18"

_BACKBONES = ["ResNet18", "ResNet34", "ResNet50"]
_N_MELS_OPTIONS = [64, 128, 256]
_MAX_SEC_OPTIONS = [1, 2, 3, 5, 10]
_TOP_K_OPTIONS = [1, 3, 5, 10]


# ---------------------------------------------------------------------------
# ESC-50 class labels (used when no custom label file is loaded)
# ---------------------------------------------------------------------------
try:
    from node.DLNode.classification.esc50_class_names import esc50_class_names as _ESC50_NAMES
except Exception:
    _ESC50_NAMES = {i: f"class_{i}" for i in range(50)}


# ---------------------------------------------------------------------------
# Mel spectrogram helper
# ---------------------------------------------------------------------------

def audio_to_mel_tensor(audio_data: np.ndarray, sample_rate: int,
                         n_mels: int, max_sec: int):
    """Convert 1-D float32 audio → (1, n_mels, T) float32 PyTorch tensor.

    Matches the ESC-50 training pre-processing:
      - pad / crop to `max_sec * sample_rate` samples
      - librosa.feature.melspectrogram → power_to_db
    """
    _lazy_imports()
    if _torch is None or _librosa is None:
        return None

    max_len = sample_rate * max_sec

    # Ensure float32 mono
    y = np.asarray(audio_data, dtype=np.float32)
    if y.ndim > 1:
        y = np.mean(y, axis=-1)

    if len(y) < max_len:
        y = np.pad(y, (0, max_len - len(y)))
    else:
        y = y[:max_len]

    mel = _librosa.feature.melspectrogram(y=y, sr=sample_rate, n_mels=n_mels)
    mel_db = _librosa.power_to_db(mel).astype(np.float32)

    tensor = _torch.tensor(mel_db).unsqueeze(0)  # (1, n_mels, T)
    return tensor


# ---------------------------------------------------------------------------
# Model builder — mirrors ESC-50 training architecture
# ---------------------------------------------------------------------------

def build_resnet_audio(backbone: str, num_classes: int):
    """Return a ResNet with 1-channel first conv (for mel spectrogram input)."""
    _lazy_imports()
    if _torch is None or _torchvision_models is None:
        return None

    import torch.nn as nn

    if backbone == "ResNet18":
        model = _torchvision_models.resnet18(weights=None)
    elif backbone == "ResNet34":
        model = _torchvision_models.resnet34(weights=None)
    elif backbone == "ResNet50":
        model = _torchvision_models.resnet50(weights=None)
    else:
        model = _torchvision_models.resnet18(weights=None)

    # Replace first conv: 3-channel → 1-channel (greyscale mel)
    model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
    # Replace final FC for the chosen number of classes
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


# ---------------------------------------------------------------------------
# Visualization helper
# ---------------------------------------------------------------------------

def mel_tensor_to_bgr_image(tensor, width: int, height: int) -> np.ndarray:
    """Render a (1, H, W) mel tensor as a BGR image for DearPyGui display."""
    mel = tensor.squeeze(0).numpy()  # (H, W)
    # Normalize to 0-255
    vmin, vmax = mel.min(), mel.max()
    if vmax > vmin:
        mel_norm = ((mel - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    else:
        mel_norm = np.zeros_like(mel, dtype=np.uint8)
    # Apply INFERNO colormap like the Spectrogram node
    mel_bgr = cv2.applyColorMap(mel_norm, cv2.COLORMAP_INFERNO)
    mel_bgr = np.flipud(mel_bgr)
    mel_bgr = cv2.resize(mel_bgr, (width, height), interpolation=cv2.INTER_LINEAR)
    return mel_bgr


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

        # Option tags (all TYPE_TEXT for simplicity)
        node.tag_backbone = _tn + ":OPT:Backbone"
        node.tag_n_mels = _tn + ":OPT:NMels"
        node.tag_max_sec = _tn + ":OPT:MaxSec"
        node.tag_num_classes = _tn + ":OPT:NumClasses"
        node.tag_top_k = _tn + ":OPT:TopK"
        node.tag_model_path_text = _tn + ":OPT:ModelPathText"
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

        # ---- File dialog for .pth model ----
        pth_dialog_tag = _tn + ":PthDialog"
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            modal=True,
            height=400,
            callback=node._callback_model_select,
            user_data=node,
            tag=pth_dialog_tag,
        ):
            dpg.add_file_extension("PyTorch model (*.pth){.pth}")
            dpg.add_file_extension("", color=(150, 255, 150, 255))
        node.tag_pth_dialog = pth_dialog_tag

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

            # ---- Option: Backbone ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:Backbone",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=_BACKBONES,
                    default_value=_DEFAULT_BACKBONE,
                    width=small_window_w,
                    label="Backbone",
                    tag=node.tag_backbone,
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

            # ---- Option: Num classes ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:NumClasses",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_int(
                    default_value=_DEFAULT_NUM_CLASSES,
                    min_value=2,
                    max_value=1000,
                    width=small_window_w,
                    label="Num classes",
                    tag=node.tag_num_classes,
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

            # ---- Option: Label source (ESC-50 built-in or custom JSON) ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:LabelSource",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    items=["ESC-50 (built-in)", "Custom JSON"],
                    default_value="ESC-50 (built-in)",
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

            # ---- Load model button ----
            with dpg.node_attribute(
                tag=_tn + ":Attr:LoadModel",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                def _open_pth_dialog(sender, app_data, user_data):
                    dpg.show_item(pth_dialog_tag)

                load_btn = dpg.add_button(
                    label=u"📂 Load .pth model",
                    width=small_window_w,
                    callback=_open_pth_dialog,
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
# Node — update logic and settings persistence
# ===========================================================================

class Node(BaseNode):
    _ver = "0.0.1"

    node_label = "AudioClassification"
    node_tag = "AudioClassification"

    _opencv_setting_dict = None

    # Runtime state (per-instance)
    _model = None
    _model_device = "cpu"
    _model_backbone = None
    _model_num_classes = None
    _model_path = None
    _class_names = None  # dict {int: str}

    def __init__(self):
        self._model = None
        self._model_backbone = None
        self._model_num_classes = None
        self._model_path = None
        self._class_names = None

    # ------------------------------------------------------------------
    # File-dialog callbacks
    # ------------------------------------------------------------------

    def _callback_model_select(self, sender, data, user_data=None):
        if data.get("file_name") == ".":
            return
        path = data.get("file_path_name", "")
        if not path or not os.path.isfile(path):
            return
        try:
            dpg_set_value(self.tag_model_path_text, path)
        except Exception:
            pass
        # Invalidate cached model so it is reloaded on next update
        self._model = None
        self._model_path = path
        logger.info(f"[AudioClassification] Model path set to: {path}")

    def _callback_label_select(self, sender, data, user_data=None):
        if data.get("file_name") == ".":
            return
        path = data.get("file_path_name", "")
        if not path or not os.path.isfile(path):
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            # Accept {int: str} or {"0": "cat", …}
            self._class_names = {int(k): str(v) for k, v in raw.items()}
            logger.info(f"[AudioClassification] Loaded {len(self._class_names)} labels from {path}")
        except Exception as exc:
            logger.error(f"[AudioClassification] Failed to load labels: {exc}")

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _ensure_model(self, backbone: str, num_classes: int, model_path: str):
        """Load (or reload) the PyTorch model if parameters changed."""
        _lazy_imports()
        if _torch is None or _torchvision_models is None:
            return False

        params_changed = (
            backbone != self._model_backbone
            or num_classes != self._model_num_classes
            or model_path != self._model_path
        )

        if self._model is not None and not params_changed:
            return True  # already loaded, nothing to do

        if not model_path or not os.path.isfile(model_path):
            return False

        try:
            model = build_resnet_audio(backbone, num_classes)
            if model is None:
                return False

            device = "cuda" if _torch.cuda.is_available() else "cpu"
            state = _torch.load(model_path, map_location=device)

            # Support both raw state-dict and checkpoint dicts
            if isinstance(state, dict) and "state_dict" in state:
                state = state["state_dict"]
            elif isinstance(state, dict) and "model_state_dict" in state:
                state = state["model_state_dict"]

            model.load_state_dict(state, strict=False)
            model.to(device)
            model.eval()

            self._model = model
            self._model_device = device
            self._model_backbone = backbone
            self._model_num_classes = num_classes
            self._model_path = model_path
            logger.info(f"[AudioClassification] Model loaded: {backbone}, {num_classes} classes, device={device}")
            return True
        except Exception as exc:
            logger.error(f"[AudioClassification] Model load error: {exc}", exc_info=True)
            self._model = None
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
        else:
            small_window_w = self._opencv_setting_dict["process_width"]
            small_window_h = self._opencv_setting_dict["process_height"]
            use_pref_counter = self._opencv_setting_dict["use_pref_counter"]

        # ---- Read options ----
        try:
            backbone = dpg_get_value(_tn + ":OPT:Backbone") or _DEFAULT_BACKBONE
            n_mels = int(dpg_get_value(_tn + ":OPT:NMels") or _DEFAULT_N_MELS)
            max_sec = int(dpg_get_value(_tn + ":OPT:MaxSec") or _DEFAULT_MAX_SEC)
            num_classes = int(dpg_get_value(_tn + ":OPT:NumClasses") or _DEFAULT_NUM_CLASSES)
            top_k = int(dpg_get_value(_tn + ":OPT:TopK") or _DEFAULT_TOP_K)
            label_source = dpg_get_value(_tn + ":OPT:LabelSource") or "ESC-50 (built-in)"
            model_path_ui = dpg_get_value(_tn + ":OPT:ModelPathText") or ""
        except Exception as exc:
            logger.debug(f"[AudioClassification] Could not read DPG values: {exc}")
            backbone = _DEFAULT_BACKBONE
            n_mels = _DEFAULT_N_MELS
            max_sec = _DEFAULT_MAX_SEC
            num_classes = _DEFAULT_NUM_CLASSES
            top_k = _DEFAULT_TOP_K
            label_source = "ESC-50 (built-in)"
            model_path_ui = ""

        # Normalise "(no model loaded)" placeholder
        if model_path_ui == "(no model loaded)":
            model_path_ui = ""

        # Sync model_path from UI (handles session restore)
        if model_path_ui and model_path_ui != self._model_path:
            self._model_path = model_path_ui
            self._model = None  # force reload

        # ---- Choose class-name dict ----
        if label_source == "Custom JSON" and self._class_names is not None:
            class_names = self._class_names
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

        # ---- Build mel tensor ----
        mel_tensor = audio_to_mel_tensor(audio_data, sample_rate, n_mels, max_sec)
        if mel_tensor is None:
            return {"image": None, "json": None, "audio": None}

        # ---- Render mel as preview image (done even without a model) ----
        bgr_preview = mel_tensor_to_bgr_image(mel_tensor, small_window_w, small_window_h)
        result_json = None

        # ---- Inference ----
        model_loaded = self._ensure_model(backbone, num_classes, model_path_ui)
        if model_loaded and self._model is not None:
            try:
                _lazy_imports()
                import torch

                # Add batch dimension: (1, 1, n_mels, T)
                x = mel_tensor.unsqueeze(0).to(self._model_device)

                with torch.no_grad():
                    logits = self._model(x)  # (1, num_classes)
                    probs = torch.softmax(logits, dim=1).squeeze(0)  # (num_classes,)

                actual_k = min(top_k, num_classes)
                scores, indices = torch.topk(probs, actual_k)

                predictions = []
                for score, idx in zip(scores.cpu().numpy(), indices.cpu().numpy()):
                    label = class_names.get(int(idx), f"class_{idx}")
                    predictions.append((label, float(score)))

                # Overlay predictions on preview
                bgr_preview = overlay_predictions(bgr_preview, predictions)

                result_json = {
                    "predictions": [
                        {"rank": r + 1, "class_id": int(indices[r].cpu()),
                         "class_name": class_names.get(int(indices[r].cpu()), f"class_{int(indices[r].cpu())}"),
                         "score": float(scores[r].cpu())}
                        for r in range(actual_k)
                    ],
                    "backbone": backbone,
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
            "backbone": _safe(_tn + ":OPT:Backbone", _DEFAULT_BACKBONE),
            "n_mels": _safe(_tn + ":OPT:NMels", str(_DEFAULT_N_MELS)),
            "max_sec": _safe(_tn + ":OPT:MaxSec", str(_DEFAULT_MAX_SEC)),
            "num_classes": _safe(_tn + ":OPT:NumClasses", _DEFAULT_NUM_CLASSES),
            "top_k": _safe(_tn + ":OPT:TopK", str(_DEFAULT_TOP_K)),
            "label_source": _safe(_tn + ":OPT:LabelSource", "ESC-50 (built-in)"),
            "model_path": _safe(_tn + ":OPT:ModelPathText", ""),
        }

    def set_setting_dict(self, node_id, setting_dict):
        _tn = str(node_id) + ":" + self.node_tag

        def _safe_set(tag, value):
            try:
                dpg_set_value(tag, value)
            except Exception:
                pass

        _safe_set(_tn + ":OPT:Backbone", setting_dict.get("backbone", _DEFAULT_BACKBONE))
        _safe_set(_tn + ":OPT:NMels", setting_dict.get("n_mels", str(_DEFAULT_N_MELS)))
        _safe_set(_tn + ":OPT:MaxSec", setting_dict.get("max_sec", str(_DEFAULT_MAX_SEC)))
        num_cls = setting_dict.get("num_classes", _DEFAULT_NUM_CLASSES)
        _safe_set(_tn + ":OPT:NumClasses", int(num_cls) if isinstance(num_cls, str) else num_cls)
        _safe_set(_tn + ":OPT:TopK", setting_dict.get("top_k", str(_DEFAULT_TOP_K)))
        _safe_set(_tn + ":OPT:LabelSource", setting_dict.get("label_source", "ESC-50 (built-in)"))
        model_path = setting_dict.get("model_path", "")
        if model_path:
            _safe_set(_tn + ":OPT:ModelPathText", model_path)
