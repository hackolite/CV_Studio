#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Online Training node for CvStudio — Teacher-Student Knowledge Distillation.

This node implements real-time knowledge distillation:
- INPUT: An image + JSON result from a teacher object detection model
- PROCESSING: Student model inference + distillation score + optional backprop
- OUTPUT: Student predictions (image + JSON)

The student learns to replicate the teacher's detections in real-time.
At any point, the user can export the student's current ONNX model.
"""

import copy
import os
import shutil
import sys
import time

import cv2
import dearpygui.dearpygui as dpg
import numpy as np

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from node.DLNode.object_detection.CustomONNX.custom_onnx import CustomONNX
from node.DLNode.object_detection import onnx_inspector
from node.DLNode.online_training.student_trainer import StudentTrainer
from node.DLNode.online_training.distillation_loss import compute_distillation_score
from node.DLNode.online_training import student_models_registry
from src.utils.logging import get_logger
from src.utils.gpu_utils import get_execution_providers

logger = get_logger(__name__)

# Directory for student models
_ONLINE_TRAINING_BASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'online_training'
)

if getattr(sys, 'frozen', False):
    from src.utils.paths import get_models_dir
    _STUDENTS_DIR = get_models_dir('online_training')
else:
    _STUDENTS_DIR = os.path.join(_ONLINE_TRAINING_BASE, 'models')

# Built-in student model
_BUILTIN_STUDENT_MODELS = [
]


class FactoryNode:
    node_label = 'OnlineTraining'
    node_tag = 'OnlineTraining'

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

        # --- Input tags ---
        node.tag_node_input_image_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input_image_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'

        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'

        # --- Output tags ---
        node.tag_node_output_image_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output_image = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output02'
        node.tag_node_output_json = node.tag_node_name + ':' + node.TYPE_JSON + ':Output02Value'

        # --- Control tags ---
        node.tag_node_score_display = node.tag_node_name + ':ScoreDisplay'
        node.tag_node_stats_display = node.tag_node_name + ':StatsDisplay'
        node.tag_node_lr_slider = node.tag_node_name + ':LRSlider'
        node.tag_node_threshold_slider = node.tag_node_name + ':ThresholdSlider'
        node.tag_node_bbox_thickness_slider = node.tag_node_name + ':BboxThicknessSlider'
        node.tag_node_training_checkbox = node.tag_node_name + ':TrainingActive'
        node.tag_node_model_combo = node.tag_node_name + ':ModelCombo'

        node._opencv_setting_dict = opencv_setting_dict

        small_window_w = opencv_setting_dict['process_width']
        small_window_h = opencv_setting_dict['process_height']
        use_pref_counter = opencv_setting_dict['use_pref_counter']

        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image, small_window_w, small_window_h
        )

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output_image,
                format=dpg.mvFormat_Float_rgb,
            )

        # --- Themes ---
        with dpg.theme() as green_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (50, 200, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70, 220, 70, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (30, 180, 30, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 220, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 235, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (220, 190, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))

        with dpg.theme() as json_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # --- File dialog for student ONNX upload ---
        onnx_file_dialog_tag = "online_training_onnx_select:" + str(node_id)
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            modal=True,
            height=400,
            callback=lambda s, d, u: node._callback_student_onnx_select(s, d, u),
            tag=onnx_file_dialog_tag,
        ):
            dpg.add_file_extension("ONNX (*.onnx){.onnx}")
            dpg.add_file_extension("", color=(150, 255, 150, 255))
        node.tag_upload_file_dialog = onnx_file_dialog_tag

        # --- Export file dialog ---
        export_file_dialog_tag = "online_training_export:" + str(node_id)
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            modal=True,
            height=400,
            callback=lambda s, d, u: node._callback_export_student(s, d, u),
            tag=export_file_dialog_tag,
            default_filename="student_model.onnx",
        ):
            dpg.add_file_extension("ONNX (*.onnx){.onnx}")
        node.tag_export_file_dialog = export_file_dialog_tag

        # --- Build Node UI ---
        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Input: Image
            with dpg.node_attribute(
                tag=node.tag_node_input_image_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_image_value_name,
                    default_value='Image',
                )

            # Input: JSON (teacher result)
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Teacher JSON',
                )

            # Output: Image (student annotated)
            with dpg.node_attribute(
                tag=node.tag_node_output_image_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output_image)

            # Score threshold slider
            with dpg.node_attribute(
                tag=node.tag_node_name + ':ThresholdAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_threshold_slider,
                    label="score_th",
                    width=small_window_w - 80,
                    default_value=0.3,
                    min_value=0.0,
                    max_value=1.0,
                )

            # Learning rate slider
            with dpg.node_attribute(
                tag=node.tag_node_name + ':LRAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_lr_slider,
                    label="learning_rate",
                    width=small_window_w - 80,
                    default_value=0.0001,
                    min_value=0.00001,
                    max_value=0.01,
                    format="%.5f",
                )

            # Training active checkbox
            with dpg.node_attribute(
                tag=node.tag_node_name + ':TrainingAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_training_checkbox,
                    label="Training Active",
                    default_value=True,
                )

            # Bounding box thickness slider
            with dpg.node_attribute(
                tag=node.tag_node_name + ':BboxThicknessAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_bbox_thickness_slider,
                    label="bbox_thickness",
                    width=small_window_w - 80,
                    default_value=2,
                    min_value=1,
                    max_value=10,
                )

            # Score display
            with dpg.node_attribute(
                tag=node.tag_node_name + ':ScoreAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_score_display,
                    default_value='Score: -- | Avg: -- | Best: --',
                )

            # Stats display
            with dpg.node_attribute(
                tag=node.tag_node_name + ':StatsAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_stats_display,
                    default_value='Frames: 0 | Training: waiting',
                )

            # Output: JSON (student result)
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="Student JSON",
                    tag=node.tag_node_output_json,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, json_button_theme)

            # Student model combobox
            with dpg.node_attribute(
                tag=node.tag_node_name + ':ModelComboAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                model_names = Node._get_student_model_names()
                default_model = model_names[0] if model_names else ''
                dpg.add_combo(
                    model_names,
                    default_value=default_model,
                    width=small_window_w,
                    tag=node.tag_node_model_combo,
                    callback=lambda s, a, u: node._on_model_combo_change(a),
                )

            # Load Student Model button (upload new ONNX)
            def _on_load_student(sender, app_data, user_data):
                dpg.show_item(onnx_file_dialog_tag)

            with dpg.node_attribute(
                tag=node.tag_node_name + ':LoadStudentAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                load_btn = dpg.add_button(
                    label=u"Load Student ONNX",
                    tag=node.tag_node_name + ':LoadStudentBtn',
                    width=small_window_w,
                    callback=_on_load_student,
                )
                dpg.bind_item_theme(load_btn, yellow_button_theme)

            # Export Student Model button
            def _on_export_student(sender, app_data, user_data):
                dpg.show_item(export_file_dialog_tag)

            with dpg.node_attribute(
                tag=node.tag_node_name + ':ExportStudentAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                export_btn = dpg.add_button(
                    label=u"Export Student ONNX",
                    tag=node.tag_node_name + ':ExportStudentBtn',
                    width=small_window_w,
                    callback=_on_export_student,
                )
                dpg.bind_item_theme(export_btn, green_button_theme)

            # Reset button
            def _on_reset(sender, app_data, user_data):
                node._reset_student()

            with dpg.node_attribute(
                tag=node.tag_node_name + ':ResetAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label=u"Reset Student",
                    tag=node.tag_node_name + ':ResetBtn',
                    width=small_window_w,
                    callback=_on_reset,
                )

        return node


class Node(Node):
    _ver = '0.0.1'
    node_label = 'OnlineTraining'
    node_tag = 'OnlineTraining'

    _opencv_setting_dict = None
    _student_trainer: StudentTrainer = None
    _student_class_names: dict = {}

    # Class-level model registry cache
    _student_models: dict = {}  # {name: entry_dict}

    def __init__(self):
        pass

    @classmethod
    def _ensure_builtin_student_models(cls):
        """Register built-in student models to the registry if not already present."""
        try:
            existing = {e.get('name') for e in student_models_registry.load_registry()}
        except Exception as exc:
            logger.warning(f"[OnlineTraining] Could not read student registry: {exc}")
            return
        for meta in _BUILTIN_STUDENT_MODELS:
            name = meta['name']
            path = meta['path']
            if name in existing:
                continue
            if not os.path.isfile(path):
                logger.debug(f"[OnlineTraining] Skipping builtin '{name}' — file not found: {path}")
                continue
            try:
                student_models_registry.save_entry(meta)
                logger.info(f"[OnlineTraining] Registered built-in student model: {name}")
            except Exception as exc:
                logger.warning(f"[OnlineTraining] Could not register '{name}': {exc}")

    @classmethod
    def _load_student_models_from_registry(cls):
        """Load all student models from registry into class-level cache."""
        cls._student_models = {}
        try:
            entries = student_models_registry.load_registry()
        except Exception as exc:
            logger.warning(f"[OnlineTraining] Failed to load student registry: {exc}")
            return
        for entry in entries:
            name = entry.get('name', '')
            if name:
                cls._student_models[name] = entry

    @classmethod
    def _get_student_model_names(cls) -> list:
        """Return list of available student model names."""
        cls._load_student_models_from_registry()
        return list(cls._student_models.keys())

    def _on_model_combo_change(self, selected_name):
        """Handle student model selection from combobox."""
        if not selected_name:
            return
        entry = Node._student_models.get(selected_name)
        if entry is None:
            # Try reloading from registry
            Node._load_student_models_from_registry()
            entry = Node._student_models.get(selected_name)
        if entry is None:
            logger.warning(f"[OnlineTraining] Model '{selected_name}' not found in registry.")
            return

        self._load_student_from_entry(entry)

    def _load_student_from_entry(self, entry):
        """Load a student model from a registry entry dict."""
        path = entry.get('path', '')
        if not os.path.isfile(path):
            logger.warning(f"[OnlineTraining] Model file not found: {path}")
            return

        raw_classes = entry.get('class_names', {})
        class_names = {int(k): str(v) for k, v in raw_classes.items()}
        if not class_names:
            num_classes = entry.get('num_classes', 0)
            if num_classes > 0:
                class_names = {i: f"class_{i}" for i in range(num_classes)}

        self._student_class_names = class_names

        self._student_trainer = StudentTrainer(
            model_path=path,
            input_width=entry.get('input_width', 320),
            input_height=entry.get('input_height', 320),
            output_format=entry.get('output_format', 'yolo11'),
            num_classes=entry.get('num_classes', 80),
            learning_rate=0.0001,
            score_threshold=0.3,
            providers=["CPUExecutionProvider"],
        )
        logger.info(f"[OnlineTraining] Student model loaded: {entry.get('name')}")

    def _callback_student_onnx_select(self, sender, data, user_data=None):
        """Handle student ONNX file selection (upload)."""
        if data.get("file_name") == ".":
            return
        onnx_path = data.get("file_path_name", "")
        if not onnx_path or not os.path.isfile(onnx_path):
            logger.warning(f"[OnlineTraining] Invalid ONNX path: '{onnx_path}'")
            return

        try:
            meta = onnx_inspector.inspect_onnx_model(onnx_path)
            logger.info(
                f"[OnlineTraining] Student model inspected: format={meta.get('output_format')}, "
                f"input={meta.get('input_width')}x{meta.get('input_height')}, "
                f"classes={meta.get('num_classes')}"
            )
        except Exception as exc:
            logger.error(f"[OnlineTraining] ONNX inspection failed: {exc}", exc_info=True)
            return

        # Copy to students directory
        os.makedirs(_STUDENTS_DIR, exist_ok=True)
        basename = os.path.basename(onnx_path)
        dest_path = os.path.join(_STUDENTS_DIR, basename)
        if os.path.abspath(onnx_path) != os.path.abspath(dest_path):
            shutil.copy2(onnx_path, dest_path)

        # Extract class names
        class_names = meta.get("class_names", {})
        if not class_names:
            num_classes = meta.get("num_classes", 0)
            if num_classes > 0:
                class_names = {i: f"class_{i}" for i in range(num_classes)}

        # Determine display name — create registry entry if it doesn't exist
        base_name = os.path.splitext(basename)[0]
        name = base_name
        counter = 1
        while name in Node._student_models:
            name = f"{base_name}_{counter}"
            counter += 1

        output_fmt = meta.get("output_format", "yolo11")
        in_w = meta.get("input_width", 640)
        in_h = meta.get("input_height", 640)
        num_classes = meta.get("num_classes", len(class_names))

        # Save to registry
        registry_entry = {
            "name": name,
            "path": dest_path,
            "class_names": {str(k): v for k, v in class_names.items()},
            "output_format": output_fmt,
            "input_width": in_w,
            "input_height": in_h,
            "num_classes": num_classes,
        }
        try:
            student_models_registry.save_entry(registry_entry)
            logger.info(f"[OnlineTraining] Registry entry saved for '{name}'.")
        except Exception as exc:
            logger.warning(f"[OnlineTraining] Could not save registry entry for '{name}': {exc}")

        # Update class-level cache
        Node._student_models[name] = registry_entry

        # Update combobox
        combo_tag = self.tag_node_name + ':ModelCombo'
        try:
            current_items = dpg.get_item_configuration(combo_tag).get("items", [])
            if name not in current_items:
                current_items = list(current_items) + [name]
            dpg.configure_item(combo_tag, items=current_items, default_value=name)
            logger.info(f"[OnlineTraining] Model dropdown updated — '{name}' selected.")
        except Exception as exc:
            logger.warning(f"[OnlineTraining] Could not update model dropdown: {exc}")

        # Load the model
        self._load_student_from_entry(registry_entry)

    def _callback_export_student(self, sender, data, user_data=None):
        """Handle student ONNX export."""
        if data.get("file_name") == ".":
            return
        export_path = data.get("file_path_name", "")
        if not export_path:
            return

        if self._student_trainer is None:
            logger.warning("[OnlineTraining] No student model to export.")
            return

        try:
            self._student_trainer.export_onnx(export_path)
            logger.info(f"[OnlineTraining] Student model exported to: {export_path}")
        except Exception as exc:
            logger.error(f"[OnlineTraining] Export failed: {exc}", exc_info=True)

    def _reset_student(self):
        """Reset student model to original weights."""
        if self._student_trainer is not None:
            self._student_trainer.reset()
            logger.info("[OnlineTraining] Student model reset.")

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        data = {}
        try:
            self.tag_node_name = str(node_id) + ':' + self.node_tag
            tag_node_output_image = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'

            small_window_w = self._opencv_setting_dict['process_width']
            small_window_h = self._opencv_setting_dict['process_height']

            # --- Get input image ---
            frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)

            # --- Get the source image timestamp ---
            image_timestamp = None
            image_source_node = None
            for connection_info in connection_list:
                connection_type = connection_info[0].split(':')[2]
                if connection_type in [self.TYPE_IMAGE, self.TYPE_AUDIO]:
                    image_source_node = ':'.join(connection_info[0].split(':')[:2])
                    if connection_type == self.TYPE_IMAGE:
                        image_timestamp = node_image_dict.get_timestamp(image_source_node)
                    elif node_audio_dict is not None:
                        image_timestamp = node_audio_dict.get_timestamp(image_source_node)
                    break

            # --- Get teacher JSON from connected JSON input ---
            # The student receives the image before the teacher result is ready,
            # so we poll briefly to allow the teacher result to arrive.
            teacher_json = {}
            teacher_source_node = None
            for connection_info in connection_list:
                connection_type = connection_info[0].split(':')[2]
                if connection_type == self.TYPE_JSON:
                    teacher_source_node = ':'.join(connection_info[0].split(':')[:2])
                    break

            if teacher_source_node is not None:
                # Wait up to _MAX_TEACHER_WAIT for teacher result matching image timestamp
                _MAX_TEACHER_WAIT = 0.15  # seconds (150ms max wait)
                _POLL_INTERVAL = 0.01  # 10ms polling interval
                _TIMESTAMP_MATCH_TOLERANCE = 0.05  # 50ms — teacher/image timestamps considered matching
                waited = 0.0

                teacher_json = node_result_dict.get(teacher_source_node, {})
                teacher_timestamp = teacher_json.get('timestamp', None) if teacher_json else None

                # If teacher result is stale or absent, wait briefly for a fresh one
                if image_timestamp is not None and frame is not None:
                    while waited < _MAX_TEACHER_WAIT:
                        teacher_json = node_result_dict.get(teacher_source_node, {})
                        teacher_timestamp = teacher_json.get('timestamp', None) if teacher_json else None
                        if teacher_timestamp is not None and abs(teacher_timestamp - image_timestamp) < _TIMESTAMP_MATCH_TOLERANCE:
                            # Teacher result matches our image — proceed
                            break
                        time.sleep(_POLL_INTERVAL)
                        waited += _POLL_INTERVAL
                    else:
                        # Timed out — use whatever teacher data is available
                        teacher_json = node_result_dict.get(teacher_source_node, {})
                        if waited > 0:
                            logger.debug(
                                f"[OnlineTraining] Waited {waited:.3f}s for teacher result "
                                f"(image_ts={image_timestamp}, teacher_ts={teacher_timestamp})"
                            )

            # --- Get UI parameters ---
            score_th_tag = self.tag_node_name + ':ThresholdSlider'
            lr_tag = self.tag_node_name + ':LRSlider'
            training_tag = self.tag_node_name + ':TrainingActive'
            score_display_tag = self.tag_node_name + ':ScoreDisplay'
            stats_display_tag = self.tag_node_name + ':StatsDisplay'

            try:
                score_th = float(dpg_get_value(score_th_tag))
            except Exception:
                score_th = 0.3

            try:
                lr = float(dpg_get_value(lr_tag))
            except Exception:
                lr = 0.0001

            try:
                training_active = bool(dpg_get_value(training_tag))
            except Exception:
                training_active = True

            try:
                bbox_thickness = int(dpg_get_value(
                    self.tag_node_bbox_thickness_slider))
            except Exception:
                bbox_thickness = 2

            # --- Process ---
            result = {}
            output_frame = frame

            if frame is not None and self._student_trainer is not None:
                # Update trainer settings
                self._student_trainer.learning_rate = lr
                self._student_trainer.training_active = training_active
                self._student_trainer.score_threshold = score_th

                # Get teacher predictions
                teacher_bboxes = teacher_json.get('bboxes', [])
                teacher_scores_list = teacher_json.get('scores', [])
                teacher_class_ids = teacher_json.get('class_ids', [])
                teacher_score_th = teacher_json.get('score_th', 0.3)
                teacher_timestamp = teacher_json.get('timestamp', None)

                # Use the image timestamp as the authoritative frame timestamp
                # (falls back to current time if image timestamp is unavailable)
                frame_timestamp = image_timestamp if image_timestamp is not None else time.time()

                # Timestamp alignment check: reject stale teacher data.
                # _TIMESTAMP_MATCH_TOLERANCE (50ms) is used during the wait loop to detect
                # that the teacher result corresponds to *this* frame. _MAX_TEACHER_STALENESS
                # (500ms) is a broader safety net: if the teacher result is from a much older
                # frame (e.g., pipeline stall), we skip distillation entirely.
                _MAX_TEACHER_STALENESS = 0.5  # seconds
                timestamp_aligned = True
                if teacher_timestamp is not None and image_timestamp is not None:
                    staleness = abs(image_timestamp - teacher_timestamp)
                    if staleness > _MAX_TEACHER_STALENESS:
                        timestamp_aligned = False
                        logger.debug(
                            f"[OnlineTraining] Skipping stale teacher data "
                            f"(staleness={staleness:.3f}s > {_MAX_TEACHER_STALENESS}s)"
                        )
                elif teacher_timestamp is None and len(teacher_bboxes) == 0:
                    # No teacher data at all — still aligned but empty
                    timestamp_aligned = True

                # Filter teacher by its own threshold
                if len(teacher_scores_list) > 0 and timestamp_aligned:
                    t_scores_arr = np.array(teacher_scores_list)
                    t_mask = t_scores_arr >= teacher_score_th
                    teacher_bboxes = [b for b, m in zip(teacher_bboxes, t_mask) if m]
                    teacher_scores_list = [s for s, m in zip(teacher_scores_list, t_mask) if m]
                    teacher_class_ids = [c for c, m in zip(teacher_class_ids, t_mask) if m]
                elif not timestamp_aligned:
                    # Stale teacher data — still run student inference but skip distillation
                    teacher_bboxes = []
                    teacher_scores_list = []
                    teacher_class_ids = []

                # Perform training step
                step_result = self._student_trainer.train_step(
                    frame,
                    teacher_bboxes,
                    teacher_scores_list,
                    teacher_class_ids,
                    score_threshold=score_th,
                )

                # Build output JSON (same format as ObjectDetection)
                s_bboxes = step_result['student_bboxes']
                s_scores = step_result['student_scores']
                s_class_ids = step_result['student_class_ids']

                if len(s_bboxes) > 0:
                    result['bboxes'] = s_bboxes.tolist()
                    result['scores'] = s_scores.tolist()
                    result['class_ids'] = s_class_ids.tolist()
                else:
                    result['bboxes'] = []
                    result['scores'] = []
                    result['class_ids'] = []

                result['class_names'] = self._student_class_names
                result['score_th'] = score_th
                result['distillation'] = step_result['distillation']
                result['timestamp'] = frame_timestamp
                result['timestamp_aligned'] = timestamp_aligned

                # Expose distillation loss metrics as flat numeric dict
                # so ObjChart can display them directly
                distillation = step_result['distillation']
                result['distillation_losses'] = {
                    'score': distillation.get('score', 0.0),
                    'class_similarity': distillation.get('class_similarity', 0.0),
                    'count_ratio': distillation.get('count_ratio', 0.0),
                    'confidence_alignment': distillation.get('confidence_alignment', 0.0),
                    'spatial_coverage': distillation.get('spatial_coverage', 0.0),
                    'teacher_count': distillation.get('teacher_count', 0),
                    'student_count': distillation.get('student_count', 0),
                    # Hungarian-matched set-based distillation loss + chart
                    # metrics (lower loss = student closer to teacher).
                    'loss': distillation.get('loss', 0.0),
                    'loss_total': distillation.get('loss_total', 0.0),
                    'loss_box': distillation.get('loss_box', 0.0),
                    'loss_class': distillation.get('loss_class', 0.0),
                    'loss_iou': distillation.get('loss_iou', 0.0),
                    'loss_cardinality': distillation.get('loss_cardinality', 0.0),
                    'loss_fp': distillation.get('loss_fp', 0.0),
                    'loss_fn': distillation.get('loss_fn', 0.0),
                    'loss_cls_mismatch': distillation.get('loss_cls_mismatch', 0.0),
                    'cardinality_error': distillation.get('cardinality_error', 0),
                    'fp_count': distillation.get('fp_count', 0),
                    'fn_count': distillation.get('fn_count', 0),
                    'iou_mean_matched': distillation.get('iou_mean_matched', 0.0),
                    'class_mismatch_rate': distillation.get('class_mismatch_rate', 0.0),
                    'detection_score': distillation.get('detection_score', 0.0),
                    # Running best/current requested loss (lower = better student).
                    'current_loss': float(self._student_trainer.current_loss),
                    'best_loss': float(self._student_trainer.best_loss),
                    # Visible improvement of the student since the first frame.
                    'improvement': float(self._student_trainer.improvement),
                    'improvement_pct': float(self._student_trainer.improvement_pct),
                }

                # Draw student predictions on frame
                output_frame = copy.deepcopy(frame)
                distillation = step_result['distillation']

                # Draw student bounding boxes (green)
                for i in range(len(s_bboxes)):
                    bbox = s_bboxes[i]
                    score = s_scores[i]
                    class_id = int(s_class_ids[i])

                    if score < score_th:
                        continue

                    x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                    class_name = self._student_class_names.get(class_id, f"cls_{class_id}")
                    label = f"S:{class_name} {score:.2f}"

                    cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 255, 0), bbox_thickness)
                    cv2.putText(
                        output_frame, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1
                    )

                # Draw teacher bounding boxes (blue, dashed effect)
                for i in range(len(teacher_bboxes)):
                    bbox = teacher_bboxes[i]
                    x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                    cv2.rectangle(output_frame, (x1, y1), (x2, y2), (255, 100, 0), max(1, bbox_thickness - 1))

                # Draw score + loss overlay
                loss_val = distillation.get('loss', 0.0)
                score_text = f"Score: {distillation['score']:.2f} | Loss: {loss_val:.3f}"
                cv2.putText(
                    output_frame, score_text, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
                )

                stats = self._student_trainer.get_stats()
                best_loss = stats.get('best_loss', float('inf'))
                best_loss_text = f"{best_loss:.3f}" if best_loss != float('inf') else "--"
                improvement_pct = stats.get('improvement_pct', 0.0)
                avg_text = (
                    f"Best: {stats['best_score']:.2f} | BestLoss: {best_loss_text} "
                    f"| Improv: {improvement_pct:.1f}%"
                )
                cv2.putText(
                    output_frame, avg_text, (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1
                )

                # Update UI displays
                try:
                    dpg_set_value(
                        score_display_tag,
                        f"Score: {distillation['score']:.2f} | "
                        f"Loss: {loss_val:.3f} | "
                        f"BestLoss: {best_loss_text} | "
                        f"Improv: {improvement_pct:.1f}%"
                    )
                    training_status = "active" if training_active else "paused"
                    if not self._student_trainer.is_training_available:
                        training_status = "inference-only"
                    dpg_set_value(
                        stats_display_tag,
                        f"Frames: {stats['frames_processed']} | "
                        f"Training: {training_status} | "
                        f"Updates: {stats.get('adapter_updates', 0)}"
                    )
                except Exception:
                    pass

            elif frame is not None:
                # No student model loaded — show waiting message
                output_frame = copy.deepcopy(frame)
                cv2.putText(
                    output_frame, "Load a Student ONNX model", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
                )

            # Update display texture
            if output_frame is not None:
                texture = self.convert_cv_to_dpg(
                    output_frame, small_window_w, small_window_h
                )
                dpg_set_value(tag_node_output_image, texture)

            data["image"] = output_frame
            data["json"] = result
            data["audio"] = None
            return data

        except Exception as e:
            logger.error(f"[OnlineTraining] Error in update: {e}", exc_info=True)
            data["image"] = None
            data["json"] = {}
            data["audio"] = None
            return data

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        score_th_tag = self.tag_node_name + ':ThresholdSlider'
        lr_tag = self.tag_node_name + ':LRSlider'
        training_tag = self.tag_node_name + ':TrainingActive'
        model_combo_tag = self.tag_node_name + ':ModelCombo'

        pos = dpg.get_item_pos(self.tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[score_th_tag] = dpg_get_value(score_th_tag)
        setting_dict[lr_tag] = dpg_get_value(lr_tag)
        setting_dict[training_tag] = dpg_get_value(training_tag)
        setting_dict['student_model'] = dpg_get_value(model_combo_tag)

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        score_th_tag = self.tag_node_name + ':ThresholdSlider'
        lr_tag = self.tag_node_name + ':LRSlider'
        training_tag = self.tag_node_name + ':TrainingActive'
        model_combo_tag = self.tag_node_name + ':ModelCombo'

        try:
            dpg_set_value(score_th_tag, setting_dict.get(score_th_tag, 0.3))
            dpg_set_value(lr_tag, setting_dict.get(lr_tag, 0.0001))
            dpg_set_value(training_tag, setting_dict.get(training_tag, True))
            # Restore student model selection
            saved_model = setting_dict.get('student_model', '')
            if saved_model:
                dpg_set_value(model_combo_tag, saved_model)
                self._on_model_combo_change(saved_model)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level initialization
# ---------------------------------------------------------------------------
Node._ensure_builtin_student_models()
Node._load_student_models_from_registry()
