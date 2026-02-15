#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import time
import os

import numpy as np
import dearpygui.dearpygui as dpg
import cv2 
from node_editor.util import dpg_get_value, dpg_set_value

from node.basenode import Node
from node.DLNode.object_detection.YOLOX.yolox import YOLOX
from node.DLNode.object_detection.YOLO.yolo import YOLO
from node.DLNode.object_detection.TennisYOLO.yolotennis import YOLOTENNIS
from node.DLNode.object_detection.LightWeightPersonDetector.detector import LWPDetector
from node.DLNode.object_detection.FreeYOLO.freeyolo import FreeYOLO
from node.DLNode.object_detection.coco_class_names import coco_class_names
from node.DLNode.object_detection.coco_class_names_only_person import coco_class_names_only_person
from node.DLNode.object_detection.coco_class_names_tennis import coco_class_names_tennis
from src.utils.logging import get_logger
from src.utils.gpu_utils import get_execution_providers

logger = get_logger(__name__)


def get_class_rejection_dropdown_items(class_name_dict):
    """Generate dropdown items for class rejection with class IDs and names.
    
    Args:
        class_name_dict: Dictionary mapping class IDs to class names
        
    Returns:
        List of formatted strings for dropdown (e.g., ["0: person", "1: bicycle", ...])
    """
    items = []
    for class_id in sorted(class_name_dict.keys()):
        class_name = class_name_dict[class_id]
        items.append(f"{class_id}: {class_name}")
    return items



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
        
        return node




class Node(Node):
    _ver = '0.0.1'
    node_label = 'ObjectDetection'
    node_tag = 'ObjectDetection'


    _min_val = 0.0
    _max_val = 1.0

    _opencv_setting_dict = None
    
    # Default value for draw bounding boxes checkbox
    DEFAULT_DRAW_BBOX = True


    # Chemin de base pour les modèles
    _model_base_path = os.path.dirname(os.path.abspath(__file__)) + '/object_detection/'


    _model_class = {
        'YOLOX-Nano(416x416)': YOLOX,
        'YOLOX-Tiny(416x416)': YOLOX,
        'YOLOX-S(640x640)': YOLOX,
        'Light-Weight Person Detector': LWPDetector,
        'YOLOX-Nano(416x416)': YOLOX,
        'FreeYOLO-Nano(640x640)': FreeYOLO,
        'FreeYOLO-Nano-CrowdHuman(640x640)': FreeYOLO,
        'YOLO11Nano': YOLO,
        'YOLOTENNIS': YOLOTENNIS,

    }


    _model_path_setting = {
        'YOLOX-Nano(416x416)':
        _model_base_path + 'YOLOX/model/yolox_nano.onnx',
        'YOLOX-Tiny(416x416)':
        _model_base_path + 'YOLOX/model/yolox_tiny.onnx',
        'YOLOX-S(640x640)':
        _model_base_path + 'YOLOX/model/yolox_s.onnx',
        'YOLO11Nano' : _model_base_path + 'YOLO/model/yolo11_n.onnx',
        'FreeYOLO-Nano(640x640)':
        _model_base_path + 'FreeYOLO/model/yolo_free_nano_640x640.onnx',
        'FreeYOLO-Nano-CrowdHuman(640x640)':
        _model_base_path +
        'FreeYOLO/model/yolo_free_nano_crowdhuman_640x640.onnx',
         'Light-Weight Person Detector': 
        _model_base_path +
        'LightWeightPersonDetector/model/model.onnx',
        'YOLOTENNIS': 
        _model_base_path +
        'TennisYOLO/model/tennis.onnx'

    }


    _model_class_name_list = {
        'YOLOX-Nano(416x416)': coco_class_names,
        'YOLOX-Tiny(416x416)': coco_class_names,
        'YOLOX-S(640x640)': coco_class_names,
        'Light-Weight Person Detector': coco_class_names_only_person,
        'FreeYOLO-Nano(640x640)': coco_class_names,
        'FreeYOLO-Nano-CrowdHuman(640x640)': coco_class_names_only_person,
        'YOLO11Nano': coco_class_names,
        'YOLOTENNIS': coco_class_names_tennis
    }



    _model_instance = {}

    def __init__(self):
        pass

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
                    class_names[int(class_id)]), score)
                
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

