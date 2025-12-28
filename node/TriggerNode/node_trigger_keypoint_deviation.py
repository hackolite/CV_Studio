#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import copy
import numpy as np
import cv2
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


class FactoryNode:
    node_label = 'CourtKeypointDeviation'
    node_tag = 'TriggerKeypointDeviation'

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
        
        # Image input for court color analysis
        node.tag_node_input_image_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input_image_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        
        # JSON input for keypoints (to extract court region)
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        
        # Parameter: CUT detection threshold
        node.tag_node_input_cut_threshold_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input_cut_threshold_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        
        # Parameter: Color dominance threshold (percentage)
        node.tag_node_input_dominance_threshold_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04'
        node.tag_node_input_dominance_threshold_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04Value'
        
        # Output: Trigger boolean
        node.tag_node_output_bool_name = node.tag_node_name + ':' + node.TYPE_BOOLEAN + ':Output01'
        node.tag_node_output_bool_value_name = node.tag_node_name + ':' + node.TYPE_BOOLEAN + ':Output01Value'
        
        # Output: Distance value (histogram difference)
        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Output02'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Output02Value'
        
        # Output: Pass-through JSON
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'
        
        # Output: Time measurement
        node.tag_node_output_time_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output04'
        node.tag_node_output_time_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output04Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Input: Image for court color analysis
            with dpg.node_attribute(
                tag=node.tag_node_input_image_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_image_value_name,
                    default_value='Court Image Input',
                )

            # Input: Keypoints JSON (for court region)
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Keypoints JSON Input',
                )

            # Parameter: CUT detection threshold
            with dpg.node_attribute(
                tag=node.tag_node_input_cut_threshold_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input_cut_threshold_value_name,
                    label="CUT Threshold",
                    width=small_window_w - 80,
                    default_value=0.3,
                    min_value=0.1,
                    max_value=1.0,
                    callback=None,
                )

            # Parameter: Color dominance threshold
            with dpg.node_attribute(
                tag=node.tag_node_input_dominance_threshold_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input_dominance_threshold_value_name,
                    label="Color Dominance %",
                    width=small_window_w - 80,
                    default_value=0.75,
                    min_value=0.5,
                    max_value=0.95,
                    callback=None,
                )

            # Output: Trigger boolean
            with dpg.node_attribute(
                tag=node.tag_node_output_bool_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_bool_value_name,
                    default_value='Trigger: False',
                )

            # Output: Distance value
            with dpg.node_attribute(
                tag=node.tag_node_output_float_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_float_value_name,
                    default_value='Distance: 0.0',
                )

            # Output: Pass-through JSON
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='Keypoints JSON Output',
                )

            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output_time_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output_time_value_name,
                        default_value='Elapsed time(ms)',
                    )

        return node


class Node(Node):
    _ver = '0.0.2'

    node_label = 'CourtKeypointDeviation'
    node_tag = 'TriggerKeypointDeviation'

    _opencv_setting_dict = None
    
    # Algorithm constants
    STABLE_FRAME_COUNT = 5  # Number of frames to wait before setting master plan
    COURT_REGION_MARGIN = 10  # Margin in pixels around keypoints bounding box
    COLOR_QUANTIZATION_STEP = 32  # Step size for color quantization (groups similar colors)
    COLOR_SIMILARITY_THRESHOLD = 50  # Maximum color distance to consider colors similar
    RETURN_THRESHOLD_FACTOR = 0.5  # Strictness factor for returning to master plan
    EPSILON = 1e-10  # Small value to prevent division by zero

    def __init__(self):
        # Master plan: dominant color of the court from first stable frame
        self._master_plan_color = None  # (B, G, R) dominant color
        self._master_plan_histogram = None  # Histogram for comparison
        self._master_plan_set = False
        
        # Scene cut detection
        self._previous_histogram = None
        self._trigger_active = False  # Trigger state
        
        # Frame counter for stability check
        self._frame_counter = 0

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_bool_tag = tag_node_name + ':' + self.TYPE_BOOLEAN + ':Output01Value'
        output_float_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Output02Value'
        output_time_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output04Value'
        input_cut_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_dominance_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get parameters
        cut_threshold = dpg_get_value(input_cut_threshold_tag)
        dominance_threshold = dpg_get_value(input_dominance_tag)

        # Find connections
        image_connection_src = ''
        json_connection_src = ''
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_IMAGE:
                image_connection_src = connection_info[0]
                image_connection_src = image_connection_src.split(':')[:2]
                image_connection_src = ':'.join(image_connection_src)
            elif connection_type.upper() == self.TYPE_JSON.upper():
                json_connection_src = connection_info[0]
                json_connection_src = json_connection_src.split(':')[:2]
                json_connection_src = ':'.join(json_connection_src)

        # Get image and JSON data
        frame = node_image_dict.get(image_connection_src, None)
        json_data = node_result_dict.get(json_connection_src, None)

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # Process frame for scene cut detection
        histogram_distance = 0.0
        output_json = None

        if frame is not None:
            output_json = copy.deepcopy(json_data) if json_data is not None else {}
            
            # Extract court region from keypoints if available
            court_region = self._extract_court_region(frame, json_data)
            
            if court_region is not None and court_region.size > 0:
                self._frame_counter += 1
                
                # 1. Define MASTER PLAN on first stable frame
                if not self._master_plan_set and self._frame_counter >= self.STABLE_FRAME_COUNT:
                    dominant_color, dominance_ratio = self._get_dominant_color(court_region)
                    
                    if dominance_ratio >= dominance_threshold:
                        self._master_plan_color = dominant_color
                        self._master_plan_histogram = self._compute_histogram(court_region)
                        self._master_plan_set = True
                        self._trigger_active = False
                
                # 2. Detect scene CUT using histogram comparison
                if self._master_plan_set:
                    # Convert to grayscale and compute histogram
                    gray_court = cv2.cvtColor(court_region, cv2.COLOR_BGR2GRAY)
                    current_histogram = cv2.calcHist([gray_court], [0], None, [256], [0, 256])
                    current_histogram = current_histogram / (current_histogram.sum() + self.EPSILON)
                    
                    if self._previous_histogram is not None:
                        # Calculate Manhattan distance (L1)
                        histogram_distance = np.sum(np.abs(current_histogram - self._previous_histogram))
                        
                        # Detect CUT
                        if histogram_distance > cut_threshold:
                            self._trigger_active = True
                    
                    self._previous_histogram = current_histogram
                    
                    # 3. Check if we returned to MASTER PLAN
                    if self._trigger_active:
                        current_dominant_color, current_dominance = self._get_dominant_color(court_region)
                        
                        # Check if current color is close to master plan color
                        if self._is_color_similar(current_dominant_color, self._master_plan_color):
                            # Verify with histogram comparison
                            master_distance = np.sum(np.abs(current_histogram - self._master_plan_histogram))
                            
                            # If we're close to master plan, deactivate trigger
                            if master_distance < cut_threshold * self.RETURN_THRESHOLD_FACTOR:
                                self._trigger_active = False
                
                # Add trigger information to output JSON
                output_json['trigger_info'] = {
                    'triggered': self._trigger_active,
                    'histogram_distance': float(histogram_distance),
                    'cut_threshold': float(cut_threshold),
                    'master_plan_set': self._master_plan_set,
                    'frame_counter': self._frame_counter,
                    'master_color': self._master_plan_color.tolist() if self._master_plan_color is not None else None,
                }

        # Update UI outputs
        dpg_set_value(output_bool_tag, f'Trigger: {self._trigger_active}')
        dpg_set_value(output_float_tag, f'Hist Dist: {histogram_distance:.4f}')

        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_time_tag, str(elapsed_time).zfill(4) + 'ms')

        return {"image": None, "json": output_json, "audio": None}

    def _extract_court_region(self, frame, json_data):
        """Extract court region from frame using keypoints bounding box"""
        if json_data is None or 'results_list' not in json_data:
            # If no keypoints, use entire frame as court region
            return frame
        
        results_list = json_data['results_list']
        
        if isinstance(results_list, np.ndarray) and len(results_list.shape) == 2 and results_list.shape[0] >= 2:
            # Extract bounding box from keypoints
            x_coords = results_list[:, 0].astype(int)
            y_coords = results_list[:, 1].astype(int)
            
            # Add margin to bounding box
            x_min = max(0, np.min(x_coords) - self.COURT_REGION_MARGIN)
            x_max = min(frame.shape[1], np.max(x_coords) + self.COURT_REGION_MARGIN)
            y_min = max(0, np.min(y_coords) - self.COURT_REGION_MARGIN)
            y_max = min(frame.shape[0], np.max(y_coords) + self.COURT_REGION_MARGIN)
            
            # Extract region
            if x_max > x_min and y_max > y_min:
                return frame[y_min:y_max, x_min:x_max]
        
        return frame

    def _get_dominant_color(self, image):
        """Get dominant color and its ratio in the image"""
        # Reshape image to list of pixels
        pixels = image.reshape(-1, 3)
        
        # Quantize colors to reduce complexity
        pixels = (pixels // self.COLOR_QUANTIZATION_STEP) * self.COLOR_QUANTIZATION_STEP
        
        # Count color frequencies
        unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
        
        # Find most frequent color
        max_idx = np.argmax(counts)
        dominant_color = unique_colors[max_idx]
        dominance_ratio = counts[max_idx] / counts.sum()
        
        return dominant_color, dominance_ratio

    def _compute_histogram(self, image):
        """Compute normalized grayscale histogram"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        histogram = cv2.calcHist([gray], [0], None, [256], [0, 256])
        histogram = histogram / (histogram.sum() + self.EPSILON)
        return histogram

    def _is_color_similar(self, color1, color2, threshold=None):
        """Check if two colors are similar (Euclidean distance)"""
        if color1 is None or color2 is None:
            return False
        if threshold is None:
            threshold = self.COLOR_SIMILARITY_THRESHOLD
        distance = np.linalg.norm(color1 - color2)
        return distance < threshold

    def close(self, node_id):
        # Clear master data on close
        self._master_plan_color = None
        self._master_plan_histogram = None
        self._master_plan_set = False
        self._previous_histogram = None
        self._trigger_active = False
        self._frame_counter = 0

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_cut_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_dominance_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        
        cut_threshold = dpg_get_value(input_cut_threshold_tag)
        dominance_threshold = dpg_get_value(input_dominance_tag)
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_cut_threshold_tag] = cut_threshold
        setting_dict[input_dominance_tag] = dominance_threshold

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_cut_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_dominance_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        
        if input_cut_threshold_tag in setting_dict:
            dpg_set_value(input_cut_threshold_tag, setting_dict[input_cut_threshold_tag])
        if input_dominance_tag in setting_dict:
            dpg_set_value(input_dominance_tag, setting_dict[input_dominance_tag])
