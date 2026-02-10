#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import time
import logging

import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
#from node_editor.util import convert_cv_to_dpg

from node.TrackerNode.mot.motpy.motpy import Motpy
from node.TrackerNode.mot.bytetrack.mc_bytetrack import MultiClassByteTrack
from node.TrackerNode.mot.norfair.mc_norfair import MultiClassNorfair
from node.TrackerNode.mot.iou_tracker.iou_tracker import MultiClassIOUTracker
from node.TrackerNode.mot.sort.mc_sort import MultiClassSORT
from node.TrackerNode.mot.centertrack.mc_centertrack import MultiClassCenterTrack
from node.TrackerNode.mot.ocsort.mc_ocsort import MultiClassOCSORT
from node.TrackerNode.mot.botsort.mc_botsort import MultiClassBotSORT
from node.TrackerNode.mot.kalman.mc_kalman import MultiClassKalmanFilter
from src.utils.logging import get_logger

logger = get_logger(__name__)

#from node.draw_node.draw_util.draw_util import draw_multi_object_tracking_info

class FactoryNode:
    node_label = 'MultiObjectTracking'
    node_tag = 'MultiObjectTracking'
    

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
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input03Value'
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input04Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        node.tag_node_output03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'
        
        # Tag for confidence threshold slider
        node.tag_node_confidence_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':ConfThresh'
        node.tag_node_confidence_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':ConfThreshValue'
        
        # Tag for enable/disable tracking checkbox
        node.tag_node_enable_checkbox_name = node.tag_node_name + ':EnableCheckbox'


        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']


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
                tag=node.tag_node_output01_value_name,
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
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Image',
                )

            # JSON input for enable/disable tracking (boolean)
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input03_value_name,
                    default_value='JSON Start/Stop (boolean)',
                )

            # JSON input for detection data (from ReId or ObjectDetection)
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input04_value_name,
                    default_value='JSON Detections',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(default_value='Image')
                dpg.add_image(node.tag_node_output01_value_name)

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    list(node._model_class.keys()),
                    default_value=list(node._model_class.keys())[0],
                    width=small_window_w,
                    tag=node.tag_node_input02_value_name,
                )

            # Confidence threshold slider
            with dpg.node_attribute(
                    tag=node.tag_node_confidence_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_confidence_value_name,
                    label="confidence",
                    width=small_window_w - 80,
                    default_value=0.0,
                    min_value=0.0,
                    max_value=1.0,
                    callback=None,
                )
            
            # Enable/Disable tracking checkbox
            with dpg.node_attribute(
                    tag=node.tag_node_enable_checkbox_name + ':Attribute',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_enable_checkbox_name,
                    label="Enable Tracking",
                    default_value=True,
                    callback=None,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

            # JSON output button
            with dpg.node_attribute(
                    tag=node.tag_node_output03_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(default_value='JSON')
                btn = dpg.add_button(
                    label="Tracking Data",
                    tag=node.tag_node_output03_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)

        return node

class Node(Node):
    _ver = '0.0.1'

    node_label = 'MOT'
    node_tag = 'MultiObjectTracking'

    _opencv_setting_dict = None

    # モデル設定
    _model_class = {
        'motpy': Motpy,
        'ByteTrack': MultiClassByteTrack,
        'Norfair': MultiClassNorfair,
        'IOU Tracker': MultiClassIOUTracker,
        'SORT': MultiClassSORT,
        'CenterTrack': MultiClassCenterTrack,
        'OC-SORT': MultiClassOCSORT,
        'BoT-SORT': MultiClassBotSORT,
        'Kalman Filter': MultiClassKalmanFilter,
    }

    _model_instance = {}
    _class_name_dict = None
    _track_id_dict = {}
    _previous_tracking_state = {}  # Track previous tracking_enabled state per node

    def __init__(self):
        pass

    def _is_valid_detection_format(self, data):
        """
        Validate that the data contains the required detection format.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            bool: True if data contains valid detection format
        """
        required_keys = ['bboxes', 'scores', 'class_ids', 'class_names']
        
        if not isinstance(data, dict):
            logger.debug(f"Invalid detection format: expected dict, got {type(data).__name__}")
            return False
        
        # Check for required keys
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            logger.debug(f"Invalid detection format: missing required keys {missing_keys}. Found keys: {list(data.keys())}")
            return False
        
        # Check that values are lists, tuples, or dict for class_names
        for key in required_keys:
            if key == 'class_names':
                # class_names can be either a dict (mapping class_id -> name) or a list
                if not isinstance(data[key], (list, tuple, dict)):
                    logger.debug(f"Invalid detection format: '{key}' must be a list, tuple, or dict, got {type(data[key]).__name__}")
                    return False
            else:
                if not isinstance(data[key], (list, tuple)):
                    logger.debug(f"Invalid detection format: '{key}' must be a list or tuple, got {type(data[key]).__name__}")
                    return False
        
        # Check that all lists have the same length (consistency check)
        # Exclude class_names from length check if it's a dict
        is_dict_class_names = isinstance(data['class_names'], dict)
        keys_to_check = [k for k in required_keys if not (k == 'class_names' and is_dict_class_names)]
        lengths = [len(data[key]) for key in keys_to_check]
        if len(set(lengths)) > 1:
            logger.warning(f"Detection format validation failed: inconsistent lengths {dict(zip(keys_to_check, lengths))}")
            return False
        
        return True



    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        confidence_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':ConfThreshValue'
        enable_checkbox_tag = tag_node_name + ':EnableCheckbox'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']


        src_node_name = ''
        connection_info_src = ''
        json_connection_info_src = ''
        json_detection_connection_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_INT:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = int(dpg_get_value(source_tag))
                input_value = max([self._min_val, input_value])
                input_value = min([self._max_val, input_value])
                dpg_set_value(destination_tag, input_value)
            elif connection_type == self.TYPE_IMAGE:

                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                src_node_name = connection_info_src[1]
                connection_info_src = ':'.join(connection_info_src)
            elif connection_type == self.TYPE_JSON or connection_type.upper() == 'JSON':
                # Determine if this is Input03 (boolean) or Input04 (detections)
                destination_tag = connection_info[1]
                if 'Input03' in destination_tag:
                    # JSON input for enable/disable tracking
                    json_connection_info_src = connection_info[0]
                    json_connection_info_src = json_connection_info_src.split(':')[:2]
                    json_connection_info_src = ':'.join(json_connection_info_src)
                elif 'Input04' in destination_tag:
                    # JSON input for detection data
                    json_detection_connection_src = connection_info[0]
                    json_detection_connection_src = json_detection_connection_src.split(':')[:2]
                    json_detection_connection_src = ':'.join(json_detection_connection_src)

            else:
                logger.warning(f'Unknown connection type: {connection_type}')
                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'
                logger.debug(f"Source value: {dpg_get_value(source_tag)}")


        frame = node_image_dict.get(connection_info_src, None)
        
        # Get tracking enabled state from checkbox (primary control)
        checkbox_enabled = dpg_get_value(enable_checkbox_tag)
        if checkbox_enabled is None:
            checkbox_enabled = True  # Default to enabled if checkbox value not found
        
        # Get JSON input for enable/disable tracking (secondary control for backward compatibility)
        # JSON input can override checkbox if connected
        tracking_enabled = checkbox_enabled
        if json_connection_info_src:
            json_data = node_result_dict.get(json_connection_info_src, None)
            if json_data is not None:
                # Extract boolean value from JSON
                if isinstance(json_data, dict):
                    tracking_enabled = json_data.get('enabled', checkbox_enabled)
                elif isinstance(json_data, bool):
                    tracking_enabled = json_data


        model_name = dpg_get_value(input_value02_tag)
        model_class = self._model_class[model_name]

        model_name_with_provider = tag_node_name + ':' + model_name

        # Check if tracking state changed from disabled to enabled (stop->start transition)
        previous_state = self._previous_tracking_state.get(node_id, None)
        if previous_state is False and tracking_enabled:
            # Transition from stop to start: reset MOT state
            logger.info(f"Tracking re-enabled for node {node_id}, resetting MOT state")
            if model_name_with_provider in self._model_instance:
                del self._model_instance[model_name_with_provider]
            if node_id in self._track_id_dict:
                self._track_id_dict[node_id] = {}
        
        # Update tracking state for next iteration
        self._previous_tracking_state[node_id] = tracking_enabled

        if frame is not None:
            if model_name_with_provider not in self._model_instance:

                self._model_instance[model_name_with_provider] = model_class()


        if frame is not None and use_pref_counter:
            start_time = time.monotonic()


        result = {}
        if frame is not None and tracking_enabled:
            logger.debug(f"Processing tracking for node: {src_node_name}")
            
            # Get detection data from JSON input (Input04) if connected, otherwise fall back to node_result_dict
            node_result = {}
            if json_detection_connection_src:
                # Use JSON input from Input04
                node_result = node_result_dict.get(json_detection_connection_src, {})
                logger.debug(f"Using detection data from JSON input: {json_detection_connection_src}")
            elif connection_info_src:
                # Fall back to getting data from the image source node
                # This provides backward compatibility with existing pipelines
                node_result = node_result_dict.get(connection_info_src, {})
                logger.debug(f"Using detection data from image source node: {src_node_name}")
            
            # Validate that we have the required detection format
            if node_result and self._is_valid_detection_format(node_result):
                od_bboxes = node_result.get('bboxes', [])
                od_scores = node_result.get('scores', [])
                od_class_ids = node_result.get('class_ids', [])
                od_class_names = node_result.get('class_names', [])
                
                logger.debug(f"MOT received detections: {len(od_bboxes)} objects, class_ids={od_class_ids}")
                
                # Get confidence threshold from slider
                confidence_threshold = dpg_get_value(confidence_threshold_tag)
                
                # Filter detections based on confidence threshold
                if confidence_threshold > 0.0 and len(od_bboxes) > 0:
                    # Use numpy for efficient filtering
                    scores_array = np.array(od_scores)
                    mask = scores_array >= confidence_threshold
                    
                    od_bboxes = [bbox for bbox, keep in zip(od_bboxes, mask) if keep]
                    od_scores = scores_array[mask].tolist()
                    od_class_ids = [cid for cid, keep in zip(od_class_ids, mask) if keep]
                    
                    logger.debug(f"After confidence filtering ({confidence_threshold}): {len(od_bboxes)} objects remain")

                track_ids, t_bboxes, t_scores, t_class_ids = [], [], [], []
                track_ids, t_bboxes, t_scores, t_class_ids = self._model_instance[
                    model_name_with_provider](
                        frame,
                        od_bboxes,
                        od_scores,
                        od_class_ids,
                    )

                if node_id not in self._track_id_dict:
                    self._track_id_dict[node_id] = {}

                for track_id in track_ids:
                    if track_id not in self._track_id_dict[node_id]:
                        new_id = len(self._track_id_dict[node_id])
                        self._track_id_dict[node_id][track_id] = new_id

                result['track_ids'] = track_ids
                result['bboxes'] = t_bboxes
                result['scores'] = t_scores
                result['class_ids'] = t_class_ids
                result['class_names'] = od_class_names
                result['track_id_dict'] = self._track_id_dict[node_id]
            elif node_result:
                # node_result exists but doesn't have valid detection format
                required_keys = ['bboxes', 'scores', 'class_ids', 'class_names']
                found_keys = list(node_result.keys()) if isinstance(node_result, dict) else []
                logger.warning(
                    f"Node result has invalid detection format. "
                    f"Expected keys: {required_keys}, "
                    f"Found: {found_keys if isinstance(node_result, dict) else type(node_result).__name__}"
                )

        elif frame is not None and not tracking_enabled:
            # Tracking is disabled, output empty result (no data should be sent downstream)
            logger.debug(f"Tracking disabled, outputting empty result")
            # result remains empty dict - no bboxes, no tracking data
            # This ensures homography and tennis court receive no data and display nothing


        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')

        # Initialize output_frame for downstream nodes
        output_frame = None
        
        # Check if result has displayable data (bboxes that will be drawn)
        # Only send data if tracking is enabled AND there are bboxes to display
        has_displayable_bboxes = tracking_enabled and bool(result) and len(result.get('bboxes', [])) > 0
        
        if frame is not None:
            if has_displayable_bboxes:

                debug_frame = copy.deepcopy(frame)
                track_ids = result.get('track_ids', [])
                t_bboxes = result.get('bboxes', [])
                t_scores = result.get('scores', [])
                t_class_ids = result.get('class_ids', [])
                od_class_names = result.get('class_names', [])
                track_id_dict = result.get('track_id_dict', {})
                
                debug_frame = self.draw_multi_object_tracking_info(
                    debug_frame,
                    track_ids,
                    t_bboxes,
                    t_scores,
                    t_class_ids,
                    od_class_names,
                    track_id_dict,
                )
                # Return the frame with overlay for downstream nodes
                output_frame = debug_frame
            else:
                debug_frame = frame
                output_frame = frame  # Return original frame if no tracking data or tracking disabled
            texture = self.convert_cv_to_dpg(
                debug_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        # Only send result to downstream nodes if there are actual bboxes being displayed
        # This ensures homography only receives data that was actually displayed on screen
        json_output = result if has_displayable_bboxes else {}
        
        # Log JSON output with CID and TID for verification
        if json_output and logger.isEnabledFor(logging.DEBUG):
            # Reuse already extracted values from result
            track_ids = result.get('track_ids', [])
            class_ids = result.get('class_ids', [])
            class_names = result.get('class_names', [])
            logger.debug(f"MOT JSON Output - Node {node_id}:")
            logger.debug(f"  Track IDs (TID): {track_ids}")
            logger.debug(f"  Class IDs (CID): {class_ids}")
            logger.debug(f"  Class Names: {class_names}")
            logger.debug(f"  Total tracked objects: {len(track_ids)}")
        
        return {"image": output_frame, "json": json_output, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        confidence_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':ConfThreshValue'
        enable_checkbox_tag = tag_node_name + ':EnableCheckbox'

        # 選択モデル
        model_name = dpg_get_value(input_value02_tag)
        
        # Get confidence threshold value
        confidence_threshold = dpg_get_value(confidence_threshold_tag)
        
        # Get enable checkbox value
        enable_checkbox = dpg_get_value(enable_checkbox_tag)
        if enable_checkbox is None:
            enable_checkbox = True

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = model_name
        setting_dict[confidence_threshold_tag] = confidence_threshold
        setting_dict[enable_checkbox_tag] = enable_checkbox

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        confidence_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':ConfThreshValue'
        enable_checkbox_tag = tag_node_name + ':EnableCheckbox'

        model_name = setting_dict[input_value02_tag]

        dpg_set_value(input_value02_tag, model_name)
        
        # Set confidence threshold with default value for backward compatibility
        confidence_value = setting_dict.get(confidence_threshold_tag, 0.0)
        dpg_set_value(confidence_threshold_tag, confidence_value)
        
        # Set enable checkbox with default value for backward compatibility
        enable_checkbox_value = setting_dict.get(enable_checkbox_tag, True)
        dpg_set_value(enable_checkbox_tag, enable_checkbox_value)
