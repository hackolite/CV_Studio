#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hand Tracking Node - Specialized tracker for hand pose estimation.
This node tracks multiple hands across frames and maintains their identities.
"""
import copy
import time

import numpy as np
import cv2
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node

from node.TrackerNode.hand_tracker.hand_tracker import HandTracker
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FactoryNode:
    node_label = 'HandTracking'
    node_tag = 'HandTracking'
    

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
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        black_image = np.zeros((small_window_h, small_window_w, 3))
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
                    default_value='Input Image',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Hand Pose Data',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

            with dpg.node_attribute(
                    tag=node.tag_node_output_json_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='Hand Tracking Results',
                )

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'Hand Tracking'
    node_tag = 'HandTracking'

    _opencv_setting_dict = None

    _tracker_instance = {}

    def __init__(self):
        pass


    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        output_json_tag = tag_node_name + ':' + self.TYPE_JSON + ':Output03Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get connections
        image_connection_info_src = ''
        json_connection_info_src = ''
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_IMAGE:
                image_connection_info_src = connection_info[0]
                image_connection_info_src = image_connection_info_src.split(':')[:2]
                image_connection_info_src = ':'.join(image_connection_info_src)
            elif connection_type == self.TYPE_JSON:
                json_connection_info_src = connection_info[0]
                json_connection_info_src = json_connection_info_src.split(':')[:2]
                json_connection_info_src = ':'.join(json_connection_info_src)

        # Get input data
        frame = node_image_dict.get(image_connection_info_src, None)
        pose_result = node_result_dict.get(json_connection_info_src, {})

        # Initialize tracker if needed
        if node_id not in self._tracker_instance:
            self._tracker_instance[node_id] = HandTracker(
                max_distance=100.0,
                max_frames_disappeared=30,
            )

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        result = {}
        debug_frame = None
        
        if frame is not None:
            # Check if we have hand pose estimation results
            model_name = pose_result.get('model_name', '')
            results_list = pose_result.get('results_list', [])
            
            # Only track if the pose estimation is using MediaPipe Hands
            if 'MediaPipe Hands' in model_name and results_list:
                logger.debug(f"Tracking {len(results_list)} hands")
                
                # Track hands
                hand_ids, tracked_results = self._tracker_instance[node_id](
                    frame, results_list
                )
                
                # Store results
                result['hand_ids'] = hand_ids
                result['tracked_hands'] = tracked_results
                result['model_name'] = model_name
                
                # Draw tracking visualization
                debug_frame = copy.deepcopy(frame)
                debug_frame = self._draw_hand_tracking(
                    debug_frame, tracked_results
                )
            else:
                # No hand data or wrong model type
                logger.debug(f"No hand tracking data. Model: {model_name}")
                debug_frame = copy.deepcopy(frame) if frame is not None else np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)

        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')

        # Update output image
        if debug_frame is not None:
            texture = self.convert_cv_to_dpg(
                debug_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": frame, "json": result, "audio": None}

    def _draw_hand_tracking(self, image, tracked_results):
        """
        Draw hand tracking visualization on the image.
        
        Args:
            image: Input image
            tracked_results: List of tracked hand results with hand_id
            
        Returns:
            Image with tracking visualization
        """
        # Color palette for different hand IDs
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
        ]
        
        for hand_result in tracked_results:
            hand_id = hand_result.get('hand_id', 0)
            color = colors[hand_id % len(colors)]
            
            # Draw keypoints
            for keypoint_id in range(21):
                if keypoint_id in hand_result:
                    landmark_x, landmark_y = hand_result[keypoint_id][0], hand_result[keypoint_id][1]
                    cv2.circle(image, (int(landmark_x), int(landmark_y)), 4, color, -1)
            
            # Draw skeleton connections
            connections = [
                # Thumb
                (2, 3), (3, 4),
                # Index finger
                (5, 6), (6, 7), (7, 8),
                # Middle finger
                (9, 10), (10, 11), (11, 12),
                # Ring finger
                (13, 14), (14, 15), (15, 16),
                # Pinky
                (17, 18), (18, 19), (19, 20),
                # Palm
                (0, 1), (1, 2), (2, 5), (5, 9), (9, 13), (13, 17), (17, 0),
            ]
            
            for start_idx, end_idx in connections:
                if start_idx in hand_result and end_idx in hand_result:
                    start_pt = tuple(map(int, hand_result[start_idx][:2]))
                    end_pt = tuple(map(int, hand_result[end_idx][:2]))
                    cv2.line(image, start_pt, end_pt, color, 2)
            
            # Draw hand ID and label
            palm_center = hand_result.get('palm_moment', [0, 0])
            label = hand_result.get('label', '')
            text = f"ID:{hand_id} {label}"
            
            cv2.putText(
                image, text, 
                (int(palm_center[0]) - 30, int(palm_center[1]) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA
            )
        
        return image

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
