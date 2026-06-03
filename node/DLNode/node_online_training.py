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

            # Load Student Model button
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

    def __init__(self):
        pass

    def _callback_student_onnx_select(self, sender, data, user_data=None):
        """Handle student ONNX file selection."""
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

        self._student_class_names = {int(k): str(v) for k, v in class_names.items()}

        # Create trainer
        self._student_trainer = StudentTrainer(
            model_path=dest_path,
            input_width=meta.get('input_width', 640),
            input_height=meta.get('input_height', 640),
            output_format=meta.get('output_format', 'yolo11'),
            num_classes=meta.get('num_classes', 80),
            learning_rate=0.0001,
            score_threshold=0.3,
            providers=["CPUExecutionProvider"],
        )

        logger.info(f"[OnlineTraining] Student model loaded: {basename}")

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
                # so ObjChart can display them directly (line 566-604 branch)
                distillation = step_result['distillation']
                matched = distillation.get('matched_count', 0)
                missed = distillation.get('missed_count', 0)
                fp = distillation.get('false_positive_count', 0)
                result['distillation_losses'] = {
                    'avg_iou': distillation.get('avg_iou', 0.0),
                    'score': distillation.get('score', 0.0),
                    'class_accuracy': distillation.get('class_accuracy', 0.0),
                    'avg_score_diff': distillation.get('avg_score_diff', 0.0),
                    'recall': matched / max(matched + missed, 1),
                    'precision': matched / max(matched + fp, 1),
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

                    cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        output_frame, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1
                    )

                # Draw teacher bounding boxes (blue, dashed effect)
                for i in range(len(teacher_bboxes)):
                    bbox = teacher_bboxes[i]
                    x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                    cv2.rectangle(output_frame, (x1, y1), (x2, y2), (255, 100, 0), 1)

                # Draw score overlay
                score_text = f"Score: {distillation['score']:.2f}"
                cv2.putText(
                    output_frame, score_text, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
                )

                stats = self._student_trainer.get_stats()
                avg_text = f"Avg: {stats['avg_score']:.2f} | Best: {stats['best_score']:.2f}"
                cv2.putText(
                    output_frame, avg_text, (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1
                )

                # Update UI displays
                try:
                    dpg_set_value(
                        score_display_tag,
                        f"Score: {distillation['score']:.2f} | "
                        f"Avg: {stats['avg_score']:.2f} | "
                        f"Best: {stats['best_score']:.2f}"
                    )
                    training_status = "active" if training_active else "paused"
                    if not self._student_trainer.is_training_available:
                        training_status = "inference-only"
                    dpg_set_value(
                        stats_display_tag,
                        f"Frames: {stats['frames_processed']} | Training: {training_status}"
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

        pos = dpg.get_item_pos(self.tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[score_th_tag] = dpg_get_value(score_th_tag)
        setting_dict[lr_tag] = dpg_get_value(lr_tag)
        setting_dict[training_tag] = dpg_get_value(training_tag)

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        score_th_tag = self.tag_node_name + ':ThresholdSlider'
        lr_tag = self.tag_node_name + ':LRSlider'
        training_tag = self.tag_node_name + ':TrainingActive'

        try:
            dpg_set_value(score_th_tag, setting_dict.get(score_th_tag, 0.3))
            dpg_set_value(lr_tag, setting_dict.get(lr_tag, 0.0001))
            dpg_set_value(training_tag, setting_dict.get(training_tag, True))
        except Exception:
            pass
