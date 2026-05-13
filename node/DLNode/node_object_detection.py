#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Object Detection node for CvStudio.

A single inference class (CustomONNX) handles all ONNX-based detection.
All models — built-in and user-uploaded — are managed through a persistent
registry (custom_models_registry.json).  Users add their own models via the
"Add Model" dialog which combines a file picker and an optional class-name
editor.
"""

import copy
import os
import time

import cv2
import dearpygui.dearpygui as dpg
import numpy as np

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from node.DLNode.object_detection.CustomONNX.custom_onnx import CustomONNX
from node.DLNode.object_detection.coco_class_names import coco_class_names
from node.DLNode.object_detection import onnx_inspector
from node.DLNode.object_detection import custom_models_registry
from src.utils.logging import get_logger
from src.utils.gpu_utils import get_execution_providers

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Built-in models
# All inference goes through CustomONNX; these entries are written to the
# registry on first run so they appear in the model combo alongside any
# user-uploaded models.
# ---------------------------------------------------------------------------

_OBJECT_DETECTION_BASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'object_detection'
)

_COCO_CLASSES = {k: v for k, v in coco_class_names.items()}

_BUILTIN_MODELS = [
    {
        'name': 'YOLOX-Nano(416x416)',
        'path': os.path.join(_OBJECT_DETECTION_BASE, 'YOLOX', 'model', 'yolox_nano.onnx'),
        'output_format': 'yolox',
        'input_width': 416,
        'input_height': 416,
        'num_classes': 80,
        'class_names': _COCO_CLASSES,
    },
    {
        'name': 'YOLOX-Tiny(416x416)',
        'path': os.path.join(_OBJECT_DETECTION_BASE, 'YOLOX', 'model', 'yolox_tiny.onnx'),
        'output_format': 'yolox',
        'input_width': 416,
        'input_height': 416,
        'num_classes': 80,
        'class_names': _COCO_CLASSES,
    },
    {
        'name': 'YOLOX-S(640x640)',
        'path': os.path.join(_OBJECT_DETECTION_BASE, 'YOLOX', 'model', 'yolox_s.onnx'),
        'output_format': 'yolox',
        'input_width': 640,
        'input_height': 640,
        'num_classes': 80,
        'class_names': _COCO_CLASSES,
    },
    {
        'name': 'YOLO11Nano',
        'path': os.path.join(_OBJECT_DETECTION_BASE, 'YOLO', 'model', 'yolo11_n.onnx'),
        'output_format': 'yolo11',
        'input_width': 608,
        'input_height': 416,
        'num_classes': 80,
        'class_names': _COCO_CLASSES,
    },
    {
        'name': 'FreeYOLO-Nano(640x640)',
        'path': os.path.join(_OBJECT_DETECTION_BASE, 'FreeYOLO', 'model', 'yolo_free_nano_640x640.onnx'),
        'output_format': 'yolox',
        'input_width': 640,
        'input_height': 640,
        'num_classes': 80,
        'class_names': _COCO_CLASSES,
    },
    {
        'name': 'FreeYOLO-CrowdHuman(640x640)',
        'path': os.path.join(_OBJECT_DETECTION_BASE, 'FreeYOLO', 'model', 'yolo_free_nano_crowdhuman_640x640.onnx'),
        'output_format': 'yolox',
        'input_width': 640,
        'input_height': 640,
        'num_classes': 1,
        'class_names': {0: 'person'},
    },
    {
        'name': 'Light-Weight Person Detector',
        'path': os.path.join(_OBJECT_DETECTION_BASE, 'LightWeightPersonDetector', 'model', 'model.onnx'),
        'output_format': 'yolox',
        'input_width': 192,
        'input_height': 192,
        'num_classes': 1,
        'class_names': {0: 'person'},
    },
    {
        'name': 'YOLOTENNIS',
        'path': os.path.join(_OBJECT_DETECTION_BASE, 'TennisYOLO', 'model', 'tennis.onnx'),
        'output_format': 'yolo11',
        'input_width': 608,
        'input_height': 608,
        'num_classes': 3,
        'class_names': {0: 'player1', 1: 'player2', 2: 'ball'},
    },
]

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_class_names_text(text: str) -> dict:
    """Parse class names entered in the upload dialog textarea.

    Accepts two formats (can be mixed):
      * ``name``          – one name per line, index assigned automatically (0-based)
      * ``id: name``      – explicit integer id followed by the class name

    Returns a ``{int_id: str_name}`` dict, or an empty dict if *text* is blank.
    """
    result = {}
    auto_idx = 0
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if ':' in line:
            parts = line.split(':', 1)
            try:
                class_id = int(parts[0].strip())
                result[class_id] = parts[1].strip()
                auto_idx = class_id + 1
                continue
            except ValueError:
                pass
        result[auto_idx] = line
        auto_idx += 1
    return result


def get_class_rejection_dropdown_items(class_name_dict):
    """Return sorted ``["id: name", ...]`` list for the rejection combo."""
    return [f"{class_id}: {class_name_dict[class_id]}"
            for class_id in sorted(class_name_dict.keys())]



class FactoryNode:
    node_label = 'ObjectDetection'
    node_tag = 'ObjectDetection'
    

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

        
        node = Node()
        node.tag_node_name = str(node_id) + ':' + self.node_tag
        
        node.tag_node_input_image_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input_image_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        
        node.tag_node_input_text_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        node.tag_node_input_text_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'
        

        node.tag_node_input_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        
        # Tag for rejected classes input field
        node.tag_node_rejected_classes_name = node.tag_node_name + ':RejectedClasses'
        node.tag_node_rejected_classes_value_name = node.tag_node_name + ':RejectedClassesValue'
        
        # Tag for draw bounding boxes checkbox
        node.tag_node_draw_bbox_name = node.tag_node_name + ':DrawBBox'
        node.tag_node_draw_bbox_value_name = node.tag_node_name + ':DrawBBoxValue'

        # Callback to update rejected classes dropdown when model changes
        def on_model_change(sender, app_data, user_data):
            """Update the rejected classes dropdown when model selection changes"""
            selected_model = app_data
            if selected_model in node._model_class_name_list:
                class_names = node._model_class_name_list[selected_model]
                class_items = get_class_rejection_dropdown_items(class_names)
                # Update the dropdown items
                dpg.configure_item(node.tag_node_rejected_classes_value_name, items=class_items)
                # Clear the rejected classes selection to avoid invalid class IDs
                dpg_set_value(node.tag_node_rejected_classes_value_name, "")

        node.tag_node_output_image_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output_image = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        
        node.tag_node_output_result_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output_result = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output_json = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'
        
        
        

        node.tag_provider_select_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Provider'
        node.tag_provider_select_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':ProviderValue'
        node._opencv_setting_dict = opencv_setting_dict
        

        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']
        use_gpu = node._opencv_setting_dict['use_gpu']


        black_image = np.zeros((small_window_w, small_window_h, 3))
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
                tag=node.tag_node_output_image,
                format=dpg.mvFormat_Float_rgb,
            )

        # Create yellow theme for JSON button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=node.tag_node_input_image_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_image_value_name,
                    default_value='Image',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output_image_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output_image)

            with dpg.node_attribute(
                    tag=node.tag_node_input_text_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    list(node._model_class.keys()),
                    default_value=list(node._model_class.keys())[0],
                    width=small_window_w,
                    tag=node.tag_node_input_text_value_name,
                    callback=on_model_change,
                )
            if use_gpu:

                with dpg.node_attribute(
                        tag=node.tag_provider_select_name,
                        attribute_type=dpg.mvNode_Attr_Static,
                ):
                    dpg.add_radio_button(
                        ("CPU", "GPU"),
                        tag=node.tag_provider_select_value_name,
                        default_value='CPU',
                        horizontal=True,
                    )

            with dpg.node_attribute(
                    tag=node.tag_node_input_float_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input_float_value_name,
                    label="score",
                    width=small_window_w - 80,
                    default_value=0.3,
                    min_value=node._min_val,
                    max_value=node._max_val,
                    callback=None,
                )

            # Rejected classes dropdown
            with dpg.node_attribute(
                    tag=node.tag_node_rejected_classes_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                # Get class names for the default model to populate dropdown
                default_model = list(node._model_class.keys())[0]
                default_class_names = node._model_class_name_list[default_model]
                class_items = get_class_rejection_dropdown_items(default_class_names)
                
                dpg.add_combo(
                    tag=node.tag_node_rejected_classes_value_name,
                    label="Reject",
                    items=class_items,
                    width=small_window_w - 80,
                    default_value="",
                )
            
            # Draw bounding boxes checkbox
            with dpg.node_attribute(
                    tag=node.tag_node_draw_bbox_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_draw_bbox_value_name,
                    label="Draw Bounding Boxes",
                    default_value=True,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output_result_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output_result,
                        default_value='elapsed time(ms)',
                    )
            
            # JSON output button
            with dpg.node_attribute(
                    tag=node.tag_node_output_json_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="JSON",
                    tag=node.tag_node_output_json,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)

            # ---- Add model button (opens upload dialog on click) ------------
            node.tag_upload_btn = node.tag_node_name + ':UploadONNX'

            with dpg.node_attribute(
                    tag=node.tag_node_name + ':UploadAttr',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                with dpg.theme() as green_btn_theme:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 160, 60, 255))
                        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 200, 80, 255))
                        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (40, 120, 40, 255))

                upload_btn = dpg.add_button(
                    label=u"📂 Add Model",
                    tag=node.tag_upload_btn,
                    width=small_window_w,
                    callback=lambda s, a, u: Node._open_upload_dialog(u),
                    user_data=node,
                )
                dpg.bind_item_theme(upload_btn, green_btn_theme)



        return node




class Node(Node):
    _ver = '0.0.1'
    node_label = 'ObjectDetection'
    node_tag = 'ObjectDetection'

    _min_val = 0.0
    _max_val = 1.0

    _opencv_setting_dict = None

    DEFAULT_DRAW_BBOX = True

    # All models (built-in + user-uploaded) populated from the registry at load time.
    _model_class: dict = {}           # name → CustomONNX factory callable
    _model_path_setting: dict = {}    # name → onnx file path
    _model_class_name_list: dict = {} # name → {int_id: str_name}

    _model_instance: dict = {}

    # Temporary storage for pending upload state (keyed by node tag)
    _pending_upload: dict = {}

    def __init__(self):
        pass

    @classmethod
    def _ensure_builtin_models(cls):
        """Write built-in model entries to the registry if they are not already there.

        This runs once at module load time so that built-in ONNX files appear in the
        model combo without requiring the user to upload them manually.  Entries are
        skipped when the ONNX file does not exist on disk (e.g., stripped builds).
        """
        try:
            existing = {e.get('name') for e in custom_models_registry.load_registry()}
        except Exception as exc:
            logger.warning(f"[Builtin] Could not read registry: {exc}")
            return
        for meta in _BUILTIN_MODELS:
            name = meta['name']
            path = meta['path']
            if name in existing:
                continue
            if not os.path.isfile(path):
                logger.debug(f"[Builtin] Skipping '{name}' — ONNX file not found: {path}")
                continue
            # Registry always stores class_names with string keys
            entry = {
                'name': name,
                'path': path,
                'output_format': meta['output_format'],
                'input_width': meta['input_width'],
                'input_height': meta['input_height'],
                'num_classes': meta['num_classes'],
                'class_names': {str(k): v for k, v in meta['class_names'].items()},
            }
            try:
                custom_models_registry.save_entry(entry)
                logger.info(f"[Builtin] Registered built-in model: {name}")
            except Exception as exc:
                logger.warning(f"[Builtin] Could not register '{name}': {exc}")

    @classmethod
    def _load_custom_models_from_registry(cls):
        """Load all models (built-in and user-uploaded) from the registry.

        Populates ``_model_class``, ``_model_path_setting`` and
        ``_model_class_name_list``.  Called once at module load time and again
        after each successful upload.
        """
        try:
            entries = custom_models_registry.load_registry()
        except Exception as exc:
            logger.warning(f"Failed to load models registry: {exc}")
            return
        for entry in entries:
            name = entry.get('name', '')
            path = entry.get('path', '')
            if not name or not path:
                continue
            if name in cls._model_class:
                continue
            raw_classes = entry.get('class_names', {})
            class_names = {int(k): str(v) for k, v in raw_classes.items()}
            if not class_names:
                num_classes = int(entry.get('num_classes', 0))
                class_names = (
                    {i: f"class_{i}" for i in range(num_classes)}
                    if num_classes > 0
                    else dict(coco_class_names)
                )
            output_fmt = entry.get('output_format', 'yolo11')
            in_w = int(entry.get('input_width', 640))
            in_h = int(entry.get('input_height', 640))
            cls._register_custom_model(name, path, class_names, output_fmt, in_w, in_h)
            logger.info(f"Loaded model from registry: {name}")

    @classmethod
    def _register_custom_model(cls, name, path, class_names, output_fmt, in_w, in_h):
        """Add a model to the class-level runtime dictionaries."""
        def _make_factory(p, fmt, w, h):
            def factory(model_path, providers=None):
                if providers is None:
                    providers = ['CPUExecutionProvider']
                return CustomONNX(
                    model_path=p,
                    input_width=w,
                    input_height=h,
                    output_format=fmt,
                    providers=providers,
                )
            return factory

        cls._model_class[name] = _make_factory(path, output_fmt, in_w, in_h)
        cls._model_path_setting[name] = path
        cls._model_class_name_list[name] = class_names

    # ------------------------------------------------------------------
    # Upload dialog
    # ------------------------------------------------------------------

    @staticmethod
    def _open_upload_dialog(node):
        """Create and show the Add Model modal dialog.

        The dialog contains:
        * an ONNX file path input with a Browse button (opens a file dialog),
        * an info label that shows detected format/dims after file selection,
        * a multiline class names editor (pre-filled from embedded ONNX metadata
          when available, empty otherwise so the user can type their own names),
        * Cancel and Add Model buttons.
        """
        dialog_tag = node.tag_node_name + ':UploadModal'
        file_dialog_tag = dialog_tag + ':FileDialog'
        onnx_path_tag = dialog_tag + ':OnnxPath'
        info_tag = dialog_tag + ':Info'
        classes_tag = dialog_tag + ':ClassNames'

        # Clean up any previous instance of the dialog
        for tag in (dialog_tag, file_dialog_tag):
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)

        # ---- file dialog (top-level, shown from Browse button) ---------
        def _on_browse_select(sender, app_data):
            selections = app_data.get("selections", {})
            if not selections:
                return
            onnx_path = list(selections.values())[0]
            dpg.set_value(onnx_path_tag, onnx_path)
            # Inspect and pre-fill
            try:
                meta = onnx_inspector.inspect_onnx_model(onnx_path)
                fmt = meta.get("output_format", "unknown")
                w = meta.get("input_width", 640)
                h = meta.get("input_height", 640)
                n = meta.get("num_classes", 0)
                dpg.set_value(info_tag,
                              f"Format: {fmt}  |  Input: {w}×{h}  |  Classes detected: {n}")
                class_names = meta.get("class_names", {})
                if class_names:
                    lines = "\n".join(
                        f"{k}: {v}" for k, v in sorted(class_names.items())
                    )
                    dpg.set_value(classes_tag, lines)
                else:
                    dpg.set_value(classes_tag, "")
                Node._pending_upload[node.tag_node_name] = {
                    "path": onnx_path, "meta": meta
                }
            except Exception as exc:
                dpg.set_value(info_tag, f"Inspection error: {exc}")
                logger.error(f"[Upload] ONNX inspection failed: {exc}")

        with dpg.file_dialog(
            tag=file_dialog_tag,
            label="Select ONNX model",
            width=600,
            height=400,
            show=False,
            modal=True,
            callback=_on_browse_select,
            cancel_callback=lambda s, a: None,
        ):
            dpg.add_file_extension(".onnx", color=(0, 200, 100, 255))
            dpg.add_file_extension(".*")

        # ---- modal window -----------------------------------------------
        def _on_add_model():
            onnx_path = dpg.get_value(onnx_path_tag).strip()
            if not onnx_path or not os.path.isfile(onnx_path):
                logger.warning("[Upload] No valid ONNX file path provided.")
                return

            # Re-inspect if no pending meta (e.g. path typed manually)
            pending = Node._pending_upload.get(node.tag_node_name)
            if not pending or pending.get("path") != onnx_path:
                try:
                    meta = onnx_inspector.inspect_onnx_model(onnx_path)
                except Exception as exc:
                    logger.error(f"[Upload] Inspection failed: {exc}")
                    return
                Node._pending_upload[node.tag_node_name] = {
                    "path": onnx_path, "meta": meta
                }

            # Parse class names from the text area
            classes_text = dpg.get_value(classes_tag).strip()
            class_names = _parse_class_names_text(classes_text) if classes_text else {}

            # Fall back to embedded names → generic names
            if not class_names:
                meta = Node._pending_upload[node.tag_node_name]["meta"]
                class_names = meta.get("class_names", {})
                if not class_names:
                    num_classes = meta.get("num_classes", 0)
                    if num_classes > 0:
                        class_names = {i: f"class_{i}" for i in range(num_classes)}
                    else:
                        class_names = dict(coco_class_names)

            dpg.delete_item(dialog_tag)
            Node._finalise_upload(node, class_names)

        try:
            vp_w = dpg.get_viewport_width()
            vp_h = dpg.get_viewport_height()
        except Exception:
            vp_w, vp_h = 1280, 720
        dlg_w, dlg_h = 540, 440
        dlg_x = max(0, (vp_w - dlg_w) // 2)
        dlg_y = max(0, (vp_h - dlg_h) // 2)

        with dpg.window(
            tag=dialog_tag,
            label="Add ONNX Model",
            modal=True,
            width=dlg_w,
            height=dlg_h,
            pos=[dlg_x, dlg_y],
            no_resize=False,
            on_close=lambda: (
                dpg.delete_item(file_dialog_tag)
                if dpg.does_item_exist(file_dialog_tag) else None
            ),
        ):
            dpg.add_text("ONNX Model File:")
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag=onnx_path_tag,
                    width=390,
                    hint="Path to .onnx file (or use Browse)",
                )
                dpg.add_button(
                    label="Browse",
                    callback=lambda: dpg.show_item(file_dialog_tag),
                )

            dpg.add_text("", tag=info_tag)
            dpg.add_separator()

            dpg.add_text("Class names (optional — one per line):")
            dpg.add_text(
                "Formats accepted:  'person'  or  '0: person'",
                color=(180, 180, 180, 255),
            )
            dpg.add_input_text(
                tag=classes_tag,
                multiline=True,
                width=520,
                height=160,
                hint="0: person\n1: car\n2: truck\n...",
            )

            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Cancel",
                    width=130,
                    callback=lambda: dpg.delete_item(dialog_tag),
                )
                dpg.add_spacer(width=220)
                dpg.add_button(
                    label="Add Model",
                    width=130,
                    callback=lambda: _on_add_model(),
                )

    @staticmethod
    def _finalise_upload(node, class_names: dict):
        """Register the custom model and refresh the node UI dropdowns."""
        pending = Node._pending_upload.pop(node.tag_node_name, None)
        if pending is None:
            logger.warning("[Upload] _finalise_upload called but no pending upload found.")
            return

        onnx_path = pending["path"]
        meta = pending["meta"]

        # Display name = filename without extension, made unique
        base = os.path.splitext(os.path.basename(onnx_path))[0]
        name = base
        counter = 1
        while name in Node._model_class:
            name = f"{base}_{counter}"
            counter += 1

        output_fmt = meta.get("output_format", "yolo11")
        in_w = meta.get("input_width", 640)
        in_h = meta.get("input_height", 640)
        num_classes = meta.get("num_classes", len(class_names))

        logger.info(
            f"[Upload] Registering '{name}' — format='{output_fmt}', "
            f"input={in_w}x{in_h}, classes={num_classes}"
        )

        Node._register_custom_model(name, onnx_path, class_names, output_fmt, in_w, in_h)

        registry_entry = {
            "name": name,
            "path": onnx_path,
            "class_names": {str(k): v for k, v in class_names.items()},
            "output_format": output_fmt,
            "input_width": in_w,
            "input_height": in_h,
            "num_classes": num_classes,
        }
        try:
            custom_models_registry.save_entry(registry_entry)
            logger.info(f"[Upload] Registry entry saved for '{name}'.")
        except Exception as exc:
            logger.warning(f"[Upload] Could not save registry entry for '{name}': {exc}")

        # Update model combobox
        model_combo_tag = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'
        try:
            current_items = dpg.get_item_configuration(model_combo_tag).get("items", [])
            if name not in current_items:
                current_items = list(current_items) + [name]
            dpg.configure_item(model_combo_tag, items=current_items, default_value=name)
            logger.info(f"[Upload] Model dropdown updated — '{name}' selected.")
        except Exception as exc:
            logger.warning(f"[Upload] Could not update model dropdown: {exc}")

        # Update rejected-classes dropdown
        try:
            class_items = get_class_rejection_dropdown_items(class_names)
            dpg.configure_item(node.tag_node_rejected_classes_value_name, items=class_items)
            dpg_set_value(node.tag_node_rejected_classes_value_name, "")
        except Exception as exc:
            logger.warning(f"[Upload] Could not update classes dropdown: {exc}")

    def _per_class_nms(self, bboxes, scores, class_ids):
        """Apply NMS per class to keep only the best detection per class.
        
        DEPRECATED: This method is no longer used as it was limiting detections to
        only 1 object per class. The method is kept for backward compatibility but
        should not be called. All detections from the model are now passed through
        without per-class filtering.
        
        Args:
            bboxes: List or numpy array of bounding boxes [x1, y1, x2, y2]
            scores: List or numpy array of confidence scores
            class_ids: List or numpy array of class IDs
            
        Returns:
            Filtered bboxes, scores, class_ids (as numpy arrays)
        """
        if len(bboxes) == 0:
            return np.array([]), np.array([]), np.array([])
        
        # Convert to numpy arrays
        bboxes = np.array(bboxes)
        scores = np.array(scores)
        class_ids = np.array(class_ids)
        
        # Get unique classes
        unique_classes = np.unique(class_ids)
        
        keep_indices = []
        
        for class_id in unique_classes:
            # Get indices for this class
            class_mask = class_ids == class_id
            class_bboxes = bboxes[class_mask]
            class_scores = scores[class_mask]
            class_indices = np.where(class_mask)[0]
            
            # If only one detection for this class, keep it
            if len(class_bboxes) == 1:
                keep_indices.append(class_indices[0])
                continue
            
            # Sort by score (descending)
            sorted_indices = np.argsort(-class_scores)
            
            # Keep the highest scoring detection for this class
            # This ensures only 1 bounding box per class
            keep_indices.append(class_indices[sorted_indices[0]])
        
        keep_indices = np.array(keep_indices)
        
        return bboxes[keep_indices], scores[keep_indices], class_ids[keep_indices]



    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict,):
            data = {}
            try:
                
                self.tag_node_name = str(node_id) + ':' + self.node_tag
                tag_node_output_image = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
                self.tag_provider_select_value_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':ProviderValue'
                self.tag_node_rejected_classes_value_name = self.tag_node_name + ':RejectedClassesValue'
                self.tag_node_draw_bbox_value_name = self.tag_node_name + ':DrawBBoxValue'

                small_window_w = self._opencv_setting_dict['process_width']
                small_window_h = self._opencv_setting_dict['process_height']
                use_pref_counter = self._opencv_setting_dict['use_pref_counter']
                use_gpu = self._opencv_setting_dict['use_gpu']


                for connection_info in connection_list:
                    connection_type = connection_info[0].split(':')[2]
                    if connection_type == self.TYPE_FLOAT:
                        source_tag = connection_info[0] + 'Value'
                        destination_tag = connection_info[1] + 'Value'
                        logger.debug(f"Linking float: {source_tag} -> {destination_tag}")
                        input_value = round(float(dpg_get_value(source_tag)), 3)
                        input_value = max([self._min_val, input_value])
                        input_value = min([self._max_val, input_value])
                        dpg_set_value(destination_tag, input_value)

                frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)
                if frame is not None:
                    logger.debug(f"Frame shape: {frame.shape}")


                try:
                    score_th = round(float(dpg_get_value(self.tag_node_input_float_value_name)), 3)
                except:
                    score_th = 0.3

                provider = 'CPU'
                if use_gpu:
                    provider = dpg_get_value(self.tag_provider_select_value_name)



                model_name = dpg_get_value(self.tag_node_input_text_value_name)
                # Fallback to first available model if the saved name is not registered
                if model_name not in self._model_class:
                    fallback = list(self._model_class.keys())[0]
                    logger.warning(
                        f"Model '{model_name}' not found in registry; falling back to '{fallback}'."
                    )
                    model_name = fallback
                model_path = self._model_path_setting[model_name]
                model_class = self._model_class[model_name]
                class_name_dict = self._model_class_name_list[model_name]

                model_name_with_provider = model_name + '_' + provider

                if frame is not None:
                    if model_name_with_provider not in self._model_instance:
                        if provider == 'CPU':
                            providers = ['CPUExecutionProvider']
                            self._model_instance[
                                model_name_with_provider] = model_class(
                                    model_path,
                                    providers=providers,
                                )
                        else:
                            self._model_instance[
                                model_name_with_provider] = model_class(model_path)


                if frame is not None and use_pref_counter:
                    start_time = time.monotonic()

                result = {}
                debug_frame = None
                if frame is not None:

                    bboxes, scores, class_ids = self._model_instance[
                        model_name_with_provider](frame)
                    
                    # Apply class rejection filter
                    if len(bboxes) > 0:
                        try:
                            rejected_classes_str = dpg_get_value(self.tag_node_rejected_classes_value_name)
                            if rejected_classes_str and rejected_classes_str.strip():
                                # Log the raw rejection string
                                logger.debug(f"Class rejection filter input: '{rejected_classes_str}'")
                                
                                # Parse the rejected class IDs
                                rejected_classes = set()
                                
                                # Handle dropdown format "0: person" or legacy format "0,1,2"
                                # Split by comma first
                                for class_str in rejected_classes_str.split(','):
                                    class_str = class_str.strip()
                                    if class_str:
                                        try:
                                            # If format is "ID: name", extract just the ID part
                                            if ':' in class_str:
                                                class_id_str = class_str.split(':')[0].strip()
                                                rejected_classes.add(int(class_id_str))
                                            else:
                                                # Legacy format: just the number
                                                rejected_classes.add(int(class_str))
                                        except ValueError:
                                            # Skip invalid class IDs
                                            pass
                                
                                # Validate rejected classes against model's class dictionary
                                valid_class_ids = set(class_name_dict.keys())
                                invalid_classes = rejected_classes - valid_class_ids
                                
                                if invalid_classes:
                                    logger.warning(f"Invalid class IDs for model '{model_name}': {invalid_classes}. "
                                                 f"Valid class IDs for this model: {sorted(valid_class_ids)}")
                                    # Filter out invalid class IDs
                                    rejected_classes = rejected_classes & valid_class_ids
                                
                                # Log before filtering
                                logger.debug(f"Before class rejection: {len(bboxes)} detections, class_ids={class_ids.tolist()}")
                                logger.debug(f"Rejected classes (validated): {rejected_classes}")
                                
                                # Filter out rejected classes
                                if rejected_classes:
                                    keep_mask = np.array([class_id not in rejected_classes for class_id in class_ids])
                                    bboxes = bboxes[keep_mask]
                                    scores = scores[keep_mask]
                                    class_ids = class_ids[keep_mask]
                                    
                                    # Log after filtering
                                    logger.debug(f"After class rejection: {len(bboxes)} detections, class_ids={class_ids.tolist()}")
                                    logger.info(f"Class rejection filter: Excluded {rejected_classes}, kept {len(bboxes)} detections")
                        except Exception as e:
                            logger.warning(f"Error applying class rejection filter: {e}")

                    if len(bboxes) > 0:
                        result['bboxes'] = bboxes.tolist()
                        result['scores'] = scores.tolist()
                        result['class_ids'] = class_ids.tolist()
                        result['class_names'] = class_name_dict
                        result['score_th'] = score_th
                        logger.debug(f"JSON output: {len(bboxes)} detections, class_ids={class_ids.tolist()}")
                    else:
                        result['bboxes'] = []
                        result['scores'] = []
                        result['class_ids'] = []
                        result['class_names'] = class_name_dict
                        result['score_th'] = score_th
                        logger.debug(f"JSON output: 0 detections (all filtered out or no detections)")


                if frame is not None and use_pref_counter:
                    elapsed_time = time.monotonic() - start_time
                    elapsed_time = int(elapsed_time * 1000)
                    dpg_set_value(self.tag_node_output_result,
                                  str(elapsed_time).zfill(4) + 'ms')

                # Get the draw bounding boxes checkbox state
                draw_bbox = dpg_get_value(self.tag_node_draw_bbox_value_name)
                if draw_bbox is None:
                    draw_bbox = self.DEFAULT_DRAW_BBOX

                # Separate displayed image from output image
                # Display image: ALWAYS show bounding boxes for visualization
                # Output image: Respect checkbox setting (for video saving vs tracking)
                display_frame = None
                output_frame = None
                
                if frame is not None:
                    # Display image: ALWAYS draw bounding boxes (for user feedback)
                    display_frame = copy.deepcopy(frame)
                    display_frame = self.draw_object_detection_info(
                        display_frame,
                        score_th,
                        bboxes,
                        scores,
                        class_ids,
                        class_name_dict,
                    )
                    
                    # Output image: Respect checkbox setting
                    if draw_bbox:
                        # When checked: send frame WITH bounding boxes (for video recording)
                        output_frame = copy.deepcopy(frame)
                        output_frame = self.draw_object_detection_info(
                            output_frame,
                            score_th,
                            bboxes,
                            scores,
                            class_ids,
                            class_name_dict,
                        )
                    else:
                        # When unchecked: send clean frame (for tracking)
                        output_frame = frame
                    
                    # Update UI texture with display frame (always has bboxes)
                    texture = self.convert_cv_to_dpg(
                        display_frame,
                        small_window_w,
                        small_window_h,
                    )
                    dpg_set_value(tag_node_output_image, texture)

                data["image"] = output_frame if output_frame is not None else frame
                data["json"] = result
                data["audio"] = None
                return data
            except Exception as e:
                    logger.error(f"Error in object detection: {e}", exc_info=True)


    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = self.tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = self.tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        rejected_classes_tag = self.tag_node_name + ':RejectedClassesValue'
        draw_bbox_tag = self.tag_node_name + ':DrawBBoxValue'


        model_name = dpg_get_value(input_value02_tag)

        score_th = round(float(dpg_get_value(input_value03_tag)), 3)
        
        rejected_classes = dpg_get_value(rejected_classes_tag) if dpg_get_value(rejected_classes_tag) else ""
        
        draw_bbox = dpg_get_value(draw_bbox_tag)
        if draw_bbox is None:
            draw_bbox = self.DEFAULT_DRAW_BBOX

        pos = dpg.get_item_pos(self.tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = model_name
        setting_dict[input_value03_tag] = score_th
        setting_dict[rejected_classes_tag] = rejected_classes
        setting_dict[draw_bbox_tag] = draw_bbox

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = self.tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = self.tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        rejected_classes_tag = self.tag_node_name + ':RejectedClassesValue'
        draw_bbox_tag = self.tag_node_name + ':DrawBBoxValue'

        model_name = setting_dict[input_value02_tag]
        score_th = setting_dict[input_value03_tag]
        rejected_classes = setting_dict.get(rejected_classes_tag, "")
        draw_bbox = setting_dict.get(draw_bbox_tag, self.DEFAULT_DRAW_BBOX)

        # If model_name is a custom model saved in registry but not yet in memory, reload it
        if model_name and model_name not in self._model_class:
            entry = custom_models_registry.get_entry(model_name)
            if entry:
                raw_classes = entry.get('class_names', {})
                class_names_restored = {int(k): str(v) for k, v in raw_classes.items()}
                if not class_names_restored:
                    num_classes = int(entry.get('num_classes', 0))
                    if num_classes > 0:
                        class_names_restored = {i: f"class_{i}" for i in range(num_classes)}
                    else:
                        class_names_restored = dict(coco_class_names)
                Node._register_custom_model(
                    model_name,
                    entry['path'],
                    class_names_restored,
                    entry.get('output_format', 'yolo11'),
                    int(entry.get('input_width', 640)),
                    int(entry.get('input_height', 640)),
                )
                logger.info(f"Restored custom model from registry on set_setting_dict: {model_name}")
            else:
                logger.warning(f"Saved model '{model_name}' not found in registry; using default.")
                model_name = list(self._model_class.keys())[0]

        # Update model dropdown to include the model name if missing
        try:
            current_items = dpg.get_item_configuration(input_value02_tag).get("items", [])
            if model_name and model_name not in current_items:
                dpg.configure_item(input_value02_tag, items=list(current_items) + [model_name])
        except Exception:
            pass

        dpg_set_value(self.tag_node_input_text_value_name, model_name)
        dpg_set_value(self.tag_node_input_float_value_name, score_th)
        
        # Update the dropdown items to match the loaded model's classes
        if model_name in self._model_class_name_list:
            class_names = self._model_class_name_list[model_name]
            class_items = get_class_rejection_dropdown_items(class_names)
            try:
                dpg.configure_item(rejected_classes_tag, items=class_items)
            except:
                pass  # Ignore if the UI element doesn't exist yet
        
        # Set rejected classes if the tag exists in settings
        if rejected_classes_tag in setting_dict:
            try:
                dpg_set_value(rejected_classes_tag, rejected_classes)
            except:
                pass  # Ignore if the UI element doesn't exist yet
        
        # Set draw bounding boxes checkbox
        try:
            dpg_set_value(draw_bbox_tag, draw_bbox)
        except:
            pass  # Ignore if the UI element doesn't exist yet




    def draw_object_detection_info(
            self,
            image,
            score_th,
            bboxes,
            scores,
            class_ids,
            class_names,
            thickness=3,
        ):
            debug_image = copy.deepcopy(image)
            logger.debug(f"Drawing object detection info on image with shape: {debug_image.shape}")
            
            # Calculate adaptive font scale and thickness based on image size
            # Use the smaller dimension to ensure text is always readable
            image_height, image_width = debug_image.shape[:2]
            min_dimension = min(image_height, image_width)
            
            # Scale font size: base size of 0.9 for ~640px, scale proportionally
            font_scale = max(0.3, min(2.0, (min_dimension / 640.0) * 0.9))
            
            # Scale thickness: base thickness of 3 for ~640px, scale proportionally
            adaptive_thickness = max(1, int((min_dimension / 640.0) * thickness))
            
            for bbox, score, class_id in zip(bboxes, scores, class_ids):
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

                if score_th > score:
                    continue

                color = self.get_color(class_id)

                debug_image = cv2.rectangle(
                    debug_image,
                    (x1, y1),
                    (x2, y2),
                    color,
                    thickness=adaptive_thickness,
                )


                score = '%.2f' % score
                text = '%s:%s(%s)' % (int(class_id), str(
                    class_names.get(int(class_id), str(int(class_id)))), score)
                
                # Calculate text size to position it better
                (text_width, text_height), baseline = cv2.getTextSize(
                    text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, adaptive_thickness
                )
                
                # Position text above the bounding box with some padding
                text_y = max(y1 - 5, text_height + 5)
                
                debug_image = cv2.putText(
                    debug_image,
                    text,
                    (x1, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    color,
                    thickness=adaptive_thickness,
                )

            return debug_image



    def get_color(self, index):
        temp_index = abs(int(index + 35)) * 3
        color = (
            (29 * temp_index) % 255,
            (17 * temp_index) % 255,
            (37 * temp_index) % 255,
        )
        return color

# Seed the registry with built-in models (skips entries already present)
Node._ensure_builtin_models()
# Load all models (built-in + user-uploaded) into runtime dictionaries
Node._load_custom_models_from_registry()
