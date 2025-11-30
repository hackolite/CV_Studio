#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Position Prediction Node for CV_Studio.

This node uses pose estimation data to predict future positions of body keypoints
using a Kalman filter-based prediction model.
"""

import copy
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node

from node.TimeseriesNode.position_prediction.kalman_position_filter import (
    MultiKeypointTracker,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FactoryNode:
    """Factory for creating PositionPrediction nodes."""

    node_label = 'PositionPrediction'
    node_tag = 'PositionPrediction'

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
        """
        Create and add a PositionPrediction node to the editor.

        Parameters
        ----------
        parent : int
            Parent DearPyGui node editor ID.
        node_id : int
            Unique node ID.
        pos : list
            Node position [x, y].
        opencv_setting_dict : dict
            OpenCV settings dictionary.
        callback : callable
            Callback function (unused).

        Returns
        -------
        Node
            The created node instance.
        """
        node = Node()
        node.tag_node_name = str(node_id) + ':' + self.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02Value'
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04'
        node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        node.tag_node_output03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

        # OpenCV settings
        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create black texture for preview
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

        logger.debug(f"Creating position prediction node: {node.node_label}")
        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Input: Pose Estimation results
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input Pose Data',
                )

            # Output: Visualization
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Prediction steps
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input02_value_name,
                    label="Pred Steps",
                    width=small_window_w - 80,
                    default_value=5,
                    min_value=1,
                    max_value=30,
                    callback=None,
                )

            # Process noise
            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label="Process Noise",
                    width=small_window_w - 80,
                    default_value=0.1,
                    min_value=0.01,
                    max_value=1.0,
                    callback=None,
                )

            # Measurement noise
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input04_value_name,
                    label="Meas. Noise",
                    width=small_window_w - 80,
                    default_value=0.5,
                    min_value=0.01,
                    max_value=2.0,
                    callback=None,
                )

            # Elapsed time output
            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='Elapsed time(ms)',
                    )

            # Prediction results output
            with dpg.node_attribute(
                    tag=node.tag_node_output03_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output03_value_name,
                    default_value='Prediction Results',
                )

        return node


class Node(Node):
    """Position Prediction Node implementation."""

    _ver = '0.0.1'

    node_label = 'PositionPrediction'
    node_tag = 'PositionPrediction'

    _opencv_setting_dict = None
    _tracker_instances = {}

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
        """
        Update the node with new data.

        Parameters
        ----------
        node_id : int
            Node ID.
        connection_list : list
            List of connections to this node.
        node_image_dict : dict
            Dictionary of images from other nodes.
        node_result_dict : dict
            Dictionary of results from other nodes.
        node_audio_dict : dict
            Dictionary of audio data from other nodes.

        Returns
        -------
        dict
            Output data with image, json, and audio.
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        output_value03_tag = tag_node_name + ':' + self.TYPE_JSON + ':Output03Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get parameters
        prediction_steps = int(dpg_get_value(input_value02_tag))
        process_noise = float(dpg_get_value(input_value03_tag))
        measurement_noise = float(dpg_get_value(input_value04_tag))

        # Find connected pose estimation node
        src_node_name = ''
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                src_node_name = connection_info_src[1]
                connection_info_src = ':'.join(connection_info_src)
                break

        # Get frame and pose results
        frame = node_image_dict.get(connection_info_src, None)
        pose_result = node_result_dict.get(connection_info_src, {})

        # Create or get tracker for this node
        tracker_key = tag_node_name
        if tracker_key not in self._tracker_instances:
            self._tracker_instances[tracker_key] = MultiKeypointTracker(
                num_keypoints=17,
                dt=1.0,
                process_noise=process_noise,
                measurement_noise=measurement_noise,
            )
        tracker = self._tracker_instances[tracker_key]

        # Update tracker noise parameters if changed
        for kf in tracker.filters.values():
            kf._process_noise = process_noise
            kf._Q = np.eye(4) * process_noise
            kf._measurement_noise = measurement_noise
            kf._R = np.eye(2) * measurement_noise

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        result = {}
        predictions = {}

        if frame is not None and pose_result:
            # Get pose estimation results
            results_list = pose_result.get('results_list', [])

            if results_list:
                # Update tracker with current observations
                updated_states = tracker.process_pose_results(results_list)

                # Predict future positions
                predictions = tracker.predict_all_positions(n_steps=prediction_steps)

                result['current_states'] = updated_states
                result['predictions'] = predictions
                result['prediction_steps'] = prediction_steps
                result['source_node'] = src_node_name
                result['model_name'] = pose_result.get('model_name', 'Unknown')

        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')

        # Draw visualization
        if frame is not None:
            debug_frame = copy.deepcopy(frame)
            debug_frame = self._draw_predictions(
                debug_frame,
                pose_result,
                predictions,
                prediction_steps,
            )

            texture = self.convert_cv_to_dpg(
                debug_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": frame, "json": result, "audio": None}

    def _draw_predictions(self, image, pose_result, predictions, prediction_steps):
        """
        Draw current keypoints and predicted positions on the image.

        Parameters
        ----------
        image : ndarray
            Input image.
        pose_result : dict
            Pose estimation results.
        predictions : dict
            Predicted positions for each keypoint.
        prediction_steps : int
            Number of prediction steps.

        Returns
        -------
        ndarray
            Image with drawn predictions.
        """
        debug_image = copy.deepcopy(image)

        results_list = pose_result.get('results_list', [])
        score_th = pose_result.get('score_th', 0.3)

        # Draw current keypoints (green)
        for results in results_list:
            for keypoint_id, keypoint_data in results.items():
                if keypoint_id == 'bbox':
                    continue
                if isinstance(keypoint_id, int) and len(keypoint_data) >= 2:
                    x, y = int(keypoint_data[0]), int(keypoint_data[1])
                    score = keypoint_data[2] if len(keypoint_data) > 2 else 1.0

                    if score >= score_th:
                        # Current position (green)
                        cv2.circle(debug_image, (x, y), 5, (0, 255, 0), -1)

        # Draw predicted positions (red)
        for keypoint_id, predicted_pos in predictions.items():
            pred_x, pred_y = int(predicted_pos[0]), int(predicted_pos[1])
            # Predicted position (red)
            cv2.circle(debug_image, (pred_x, pred_y), 5, (0, 0, 255), -1)

            # Draw prediction trajectory line (yellow) from current to predicted
            for results in results_list:
                if keypoint_id in results:
                    curr_x = int(results[keypoint_id][0])
                    curr_y = int(results[keypoint_id][1])
                    cv2.line(debug_image, (curr_x, curr_y), (pred_x, pred_y), (0, 255, 255), 1)
                    break

        # Add text label
        cv2.putText(
            debug_image,
            f"Prediction: {prediction_steps} steps",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        return debug_image

    def close(self, node_id):
        """Close the node and clean up resources."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        if tag_node_name in self._tracker_instances:
            del self._tracker_instances[tag_node_name]

    def get_setting_dict(self, node_id):
        """Get current settings as a dictionary."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'

        prediction_steps = int(dpg_get_value(input_value02_tag))
        process_noise = float(dpg_get_value(input_value03_tag))
        measurement_noise = float(dpg_get_value(input_value04_tag))

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = prediction_steps
        setting_dict[input_value03_tag] = process_noise
        setting_dict[input_value04_tag] = measurement_noise

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Set settings from a dictionary."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'

        prediction_steps = setting_dict.get(input_value02_tag, 5)
        process_noise = setting_dict.get(input_value03_tag, 0.1)
        measurement_noise = setting_dict.get(input_value04_tag, 0.5)

        dpg_set_value(input_value02_tag, prediction_steps)
        dpg_set_value(input_value03_tag, process_noise)
        dpg_set_value(input_value04_tag, measurement_noise)
