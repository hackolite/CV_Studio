#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import copy
import numpy as np
import dearpygui.dearpygui as dpg
from sklearn.cluster import KMeans

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
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        
        node.tag_node_output_bool_name = node.tag_node_name + ':' + node.TYPE_BOOLEAN + ':Output01'
        node.tag_node_output_bool_value_name = node.tag_node_name + ':' + node.TYPE_BOOLEAN + ':Output01Value'
        
        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Output02'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Output02Value'
        
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'
        
        node.tag_node_input_threshold_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02'
        node.tag_node_input_threshold_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input02Value'
        
        node.tag_node_input_sample_count_name = node.tag_node_name + ':SampleCount'
        node.tag_node_input_sample_count_value_name = node.tag_node_name + ':SampleCountValue'
        
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
            # Input: Keypoints JSON
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Keypoints JSON Input',
                )

            # Parameter: Threshold distance
            with dpg.node_attribute(
                tag=node.tag_node_input_threshold_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input_threshold_value_name,
                    label="Threshold",
                    width=small_window_w - 80,
                    default_value=100.0,
                    min_value=10.0,
                    max_value=500.0,
                    callback=None,
                )

            # Parameter: Sample count for K-means training
            with dpg.node_attribute(
                tag=node.tag_node_input_sample_count_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_input_sample_count_value_name,
                    label="Sample Count",
                    items=["100", "200", "300"],
                    default_value="200",
                    width=small_window_w - 80,
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
    _ver = '0.0.1'

    node_label = 'CourtKeypointDeviation'
    node_tag = 'TriggerKeypointDeviation'

    _opencv_setting_dict = None

    def __init__(self):
        # K-means clustering data
        self._keypoints_buffer = []  # Store keypoints for K-means training
        self._kmeans_model = None  # Trained K-means model
        self._court_cluster_id = None  # ID of the cluster with least variation (court)
        self._training_complete = False  # Flag to indicate if K-means training is done
        self._last_trigger_state = False

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
        input_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_sample_count_tag = tag_node_name + ':SampleCountValue'

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get parameters
        threshold_distance = dpg_get_value(input_threshold_tag)
        sample_count_str = dpg_get_value(input_sample_count_tag)
        sample_count = int(sample_count_str)

        # Find JSON connection
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            # Match case-insensitively or use both Json and JSON
            if connection_type.upper() == self.TYPE_JSON.upper():
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)

        # Get JSON data
        json_data = node_result_dict.get(connection_info_src, None)

        if json_data is not None and use_pref_counter:
            start_time = time.monotonic()

        # Process keypoints and check for deviation
        trigger_state = False
        distance = 0.0
        output_json = None

        if json_data is not None and isinstance(json_data, dict):
            output_json = copy.deepcopy(json_data)
            
            # Extract keypoints from results_list
            if 'results_list' in json_data:
                results_list = json_data['results_list']
                
                # Convert keypoints to array if needed
                if isinstance(results_list, np.ndarray):
                    keypoints = results_list
                    
                    # Flatten keypoints to 1D array for K-means
                    if len(keypoints.shape) == 2 and keypoints.shape[0] >= 2:
                        keypoints_flat = keypoints.flatten()
                        
                        # Phase 1: Collect samples for K-means training
                        if not self._training_complete:
                            self._keypoints_buffer.append(keypoints_flat)
                            
                            # Check if we have enough samples
                            if len(self._keypoints_buffer) >= sample_count:
                                # Train K-means with 2 clusters
                                X = np.array(self._keypoints_buffer)
                                self._kmeans_model = KMeans(n_clusters=2, random_state=42, n_init=10)
                                self._kmeans_model.fit(X)
                                
                                # Identify which cluster has least variation (court cluster)
                                # Calculate variance for each cluster (sum of variances per dimension)
                                labels = self._kmeans_model.labels_
                                cluster_0_samples = X[labels == 0]
                                cluster_1_samples = X[labels == 1]
                                
                                # Calculate total variance (sum across all dimensions)
                                variance_0 = np.sum(np.var(cluster_0_samples, axis=0)) if len(cluster_0_samples) > 0 else float('inf')
                                variance_1 = np.sum(np.var(cluster_1_samples, axis=0)) if len(cluster_1_samples) > 0 else float('inf')
                                
                                # Court cluster is the one with least variation
                                self._court_cluster_id = 0 if variance_0 < variance_1 else 1
                                self._training_complete = True
                                
                                # Add training info to output
                                output_json['kmeans_info'] = {
                                    'training_complete': True,
                                    'samples_collected': len(self._keypoints_buffer),
                                    'court_cluster_id': int(self._court_cluster_id),
                                    'variance_cluster_0': float(variance_0),
                                    'variance_cluster_1': float(variance_1)
                                }
                            else:
                                # Still collecting samples
                                output_json['kmeans_info'] = {
                                    'training_complete': False,
                                    'samples_collected': len(self._keypoints_buffer),
                                    'samples_needed': sample_count
                                }
                        
                        # Phase 2: Classify new keypoints and trigger if not in court cluster
                        else:
                            # Predict which cluster this keypoint belongs to
                            keypoints_reshaped = keypoints_flat.reshape(1, -1)
                            predicted_cluster = self._kmeans_model.predict(keypoints_reshaped)[0]
                            
                            # Calculate distance to court cluster center
                            court_center = self._kmeans_model.cluster_centers_[self._court_cluster_id]
                            distance = np.linalg.norm(keypoints_flat - court_center)
                            
                            # Trigger if not in court cluster (primary condition)
                            if predicted_cluster != self._court_cluster_id:
                                trigger_state = True
                            # Also check threshold distance as secondary condition
                            elif threshold_distance is not None and distance > threshold_distance:
                                trigger_state = True
                            
                            # Add classification info to output
                            output_json['kmeans_info'] = {
                                'training_complete': True,
                                'predicted_cluster': int(predicted_cluster),
                                'court_cluster_id': int(self._court_cluster_id),
                                'is_court': predicted_cluster == self._court_cluster_id,
                                'distance_to_court': float(distance),
                                'threshold': float(threshold_distance) if threshold_distance is not None else 100.0
                            }
            
            # Add standard BOOL field to output JSON
            output_json['BOOL'] = trigger_state

        # Update UI outputs
        dpg_set_value(output_bool_tag, f'Trigger: {trigger_state}')
        dpg_set_value(output_float_tag, f'Distance: {distance:.2f}')

        if json_data is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_time_tag, str(elapsed_time).zfill(4) + 'ms')

        self._last_trigger_state = trigger_state

        return {"image": None, "json": output_json, "audio": None}

    def close(self, node_id):
        # Clear K-means data on close
        self._keypoints_buffer = []
        self._kmeans_model = None
        self._court_cluster_id = None
        self._training_complete = False

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_sample_count_tag = tag_node_name + ':SampleCountValue'
        
        threshold_distance = dpg_get_value(input_threshold_tag)
        sample_count = dpg_get_value(input_sample_count_tag)
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_threshold_tag] = threshold_distance
        setting_dict[input_sample_count_tag] = sample_count

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_threshold_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input02Value'
        input_sample_count_tag = tag_node_name + ':SampleCountValue'
        
        if input_threshold_tag in setting_dict:
            dpg_set_value(input_threshold_tag, setting_dict[input_threshold_tag])
        
        if input_sample_count_tag in setting_dict:
            dpg_set_value(input_sample_count_tag, setting_dict[input_sample_count_tag])
