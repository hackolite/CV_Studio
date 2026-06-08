#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DistanceTracker node: receives TennisKeypoints from PoseEstimation, uses
k-means anomaly detection to flag when the keypoint configuration is far
from the learned normal clusters (kernel distance), and displays an alert
when the distance exceeds a user-defined threshold.
"""
import time
import copy
from collections import deque

import numpy as np
import dearpygui.dearpygui as dpg

try:
    from sklearn.cluster import KMeans
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Minimum samples before k-means is fitted
_MIN_SAMPLES_FOR_KMEANS = 30
# Maximum history window
_MAX_HISTORY_SIZE = 200
# Refit k-means every N new observations (0 = every frame)
_REFIT_INTERVAL = 5


class FactoryNode:
    node_label = 'DistanceTracker'
    node_tag = 'DistanceTracker'

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

        # Input 1: JSON from PoseEstimation (TennisKeypoints)
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'

        # Input 2: JSON boolean to enable/disable tracking
        node.tag_node_input_enable_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input_enable_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'

        # Static: alert threshold slider
        node.tag_node_threshold_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Threshold'
        node.tag_node_threshold_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':ThresholdValue'

        # Static: number of k-means clusters slider
        node.tag_node_nclusters_name = node.tag_node_name + ':' + node.TYPE_INT + ':NClusters'
        node.tag_node_nclusters_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':NClustersValue'

        # Static: distance display
        node.tag_node_distance_display_name = node.tag_node_name + ':TEXT:DistanceDisplay'
        node.tag_node_distance_display_value_name = node.tag_node_name + ':TEXT:DistanceDisplayValue'

        # Static: alert status display
        node.tag_node_alert_name = node.tag_node_name + ':TEXT:Alert'
        node.tag_node_alert_value_name = node.tag_node_name + ':TEXT:AlertValue'

        # Output 1: JSON with anomaly/distance information
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'

        # Output 2: Elapsed time
        node.tag_node_output_time_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output_time_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Yellow theme for JSON output button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # Red theme for alert indicator
        with dpg.theme() as red_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 80, 80, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 80, 80, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 80, 80, 255))

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # JSON Input from PoseEstimation
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='TennisKeypoints (Pose)',
                )

            # Enable/disable boolean input
            with dpg.node_attribute(
                tag=node.tag_node_input_enable_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_enable_value_name,
                    default_value='Enable (boolean)',
                )

            # Threshold slider
            with dpg.node_attribute(
                tag=node.tag_node_threshold_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_threshold_value_name,
                    label='Alert Threshold',
                    width=200,
                    default_value=100.0,
                    min_value=0.0,
                    max_value=500.0,
                )

            # n_clusters slider
            with dpg.node_attribute(
                tag=node.tag_node_nclusters_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_nclusters_value_name,
                    label='K-Means Clusters',
                    width=200,
                    default_value=3,
                    min_value=1,
                    max_value=10,
                )

            # Distance display
            with dpg.node_attribute(
                tag=node.tag_node_distance_display_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_distance_display_value_name,
                    default_value='Distance: -- (samples: 0)',
                )

            # Alert indicator
            with dpg.node_attribute(
                tag=node.tag_node_alert_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                alert_btn = dpg.add_button(
                    tag=node.tag_node_alert_value_name,
                    label='Status: Normal',
                    width=200,
                    enabled=False,
                )
                dpg.bind_item_theme(alert_btn, yellow_button_theme)

            # JSON output
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(default_value='JSON')
                out_btn = dpg.add_button(
                    label='Distance Data',
                    tag=node.tag_node_output_json_value_name,
                    width=200,
                    enabled=False,
                )
                dpg.bind_item_theme(out_btn, yellow_button_theme)

            # Time output
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

    node_label = 'DistanceTracker'
    node_tag = 'DistanceTracker'

    _opencv_setting_dict = None

    # Per-node state (keyed by str(node_id))
    _kp_history = {}        # deque of flattened keypoint vectors
    _kmeans_models = {}     # fitted KMeans models
    _refit_counter = {}     # counts new observations since last refit
    _last_distance = {}     # last computed kernel distance
    _is_alert = {}          # current alert status

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # K-means helpers
    # ------------------------------------------------------------------

    def _keypoints_to_signature(self, results_list):
        """Flatten an (N, 2) keypoints array to a 1-D signature vector."""
        arr = np.array(results_list, dtype=np.float32)
        return arr.flatten()

    def _fit_kmeans(self, node_id_str, n_clusters):
        """Fit KMeans on accumulated history for this node."""
        if not _SKLEARN_AVAILABLE:
            return
        history = self._kp_history.get(node_id_str)
        if history is None or len(history) < max(n_clusters, 2):
            return
        X = np.array(list(history), dtype=np.float32)
        n_clusters = min(n_clusters, len(X))
        km = KMeans(n_clusters=n_clusters, n_init='auto', max_iter=100, random_state=0)
        km.fit(X)
        self._kmeans_models[node_id_str] = km

    def _distance_to_nearest_centroid(self, node_id_str, signature):
        """Return Euclidean distance from signature to its nearest centroid.
        Returns -1.0 if model not yet fitted."""
        km = self._kmeans_models.get(node_id_str)
        if km is None:
            return -1.0
        dists = np.linalg.norm(km.cluster_centers_ - signature, axis=1)
        return float(np.min(dists))

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_time_value_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        threshold_value_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':ThresholdValue'
        nclusters_value_tag = tag_node_name + ':' + self.TYPE_INT + ':NClustersValue'
        distance_display_tag = tag_node_name + ':TEXT:DistanceDisplayValue'
        alert_tag = tag_node_name + ':TEXT:AlertValue'

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Read UI parameters (fallback to defaults if DPG not initialised)
        threshold = dpg_get_value(threshold_value_tag)
        threshold = float(threshold) if threshold is not None else 100.0
        n_clusters = dpg_get_value(nclusters_value_tag)
        n_clusters = int(n_clusters) if n_clusters is not None else 3

        # Find JSON input connections
        json_connection_info_src = ''
        enable_connection_info_src = ''

        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            connection_target = connection_info[1]

            if connection_type == self.TYPE_JSON or connection_type.upper() == 'JSON':
                if ':Input01' in connection_target:
                    json_connection_info_src = ':'.join(connection_info[0].split(':')[:2])
                elif ':Input02' in connection_target:
                    enable_connection_info_src = ':'.join(connection_info[0].split(':')[:2])

        # Retrieve data from connected nodes
        json_data = node_result_dict.get(json_connection_info_src, None) if json_connection_info_src else None

        tracking_enabled = True
        if enable_connection_info_src:
            enable_data = node_result_dict.get(enable_connection_info_src, None)
            if enable_data is not None:
                if isinstance(enable_data, dict):
                    tracking_enabled = bool(enable_data.get('enabled', True))
                elif isinstance(enable_data, bool):
                    tracking_enabled = enable_data

        if use_pref_counter and json_data is not None:
            start_time = time.monotonic()

        node_id_str = str(node_id)

        # Initialise per-node state
        if node_id_str not in self._kp_history:
            self._kp_history[node_id_str] = deque(maxlen=_MAX_HISTORY_SIZE)
            self._refit_counter[node_id_str] = 0
            self._last_distance[node_id_str] = -1.0
            self._is_alert[node_id_str] = False

        output_json = None
        kernel_distance = -1.0
        alert_active = False

        if json_data is not None and tracking_enabled:
            # Extract TennisKeypoints results_list from PoseEstimation output
            results_list = json_data.get('results_list', None)

            if results_list is not None and len(results_list) > 0:
                try:
                    signature = self._keypoints_to_signature(results_list)
                except Exception:
                    signature = None

                if signature is not None and len(signature) > 0:
                    # Accumulate history
                    self._kp_history[node_id_str].append(signature)
                    self._refit_counter[node_id_str] += 1
                    n_samples = len(self._kp_history[node_id_str])

                    # (Re)fit k-means once enough data accumulated
                    if (n_samples >= _MIN_SAMPLES_FOR_KMEANS and
                            _SKLEARN_AVAILABLE and
                            self._refit_counter[node_id_str] >= _REFIT_INTERVAL):
                        self._fit_kmeans(node_id_str, n_clusters)
                        self._refit_counter[node_id_str] = 0

                    # Compute distance to nearest centroid
                    kernel_distance = self._distance_to_nearest_centroid(node_id_str, signature)
                    self._last_distance[node_id_str] = kernel_distance
                    alert_active = (kernel_distance >= 0 and kernel_distance > threshold)
                    self._is_alert[node_id_str] = alert_active

                    # Update UI displays
                    n_samples_str = f'{n_samples}/{_MIN_SAMPLES_FOR_KMEANS}'
                    if kernel_distance >= 0:
                        dist_text = f'Distance: {kernel_distance:.2f} px (samples: {n_samples_str})'
                    else:
                        dist_text = f'Distance: -- (samples: {n_samples_str})'
                    try:
                        dpg_set_value(distance_display_tag, dist_text)
                        if alert_active:
                            dpg_set_value(alert_tag, 'ALERT: Distance too high!')
                        else:
                            dpg_set_value(alert_tag, 'Status: Normal')
                    except Exception:
                        pass  # DPG not initialised in tests

                    # Console output
                    logger.info('=' * 60)
                    logger.info('[DistanceTracker] K-Means Kernel Distance:')
                    logger.info(f'  Samples in history : {n_samples}')
                    logger.info(f'  K-Means clusters   : {n_clusters}')
                    dist_str = f'{kernel_distance:.3f} px' if kernel_distance >= 0 else 'not yet fitted'
                    logger.info(f'  Kernel distance    : {dist_str}')
                    logger.info(f'  Threshold          : {threshold:.1f} px')
                    logger.info(f'  Alert              : {"YES" if alert_active else "no"}')
                    logger.info('=' * 60)

            # Build output JSON
            output_json = {
                'kernel_distance': float(kernel_distance),
                'threshold': float(threshold),
                'alert': alert_active,
                'n_clusters': n_clusters,
                'n_samples': len(self._kp_history[node_id_str]),
                'tracking_enabled': True,
            }
            # Pass through PoseEstimation data for downstream nodes
            output_json.update(json_data)

        elif json_data is not None and not tracking_enabled:
            output_json = copy.deepcopy(json_data)
            output_json['tracking_enabled'] = False

        if use_pref_counter and json_data is not None:
            elapsed_time = int((time.monotonic() - start_time) * 1000)
            try:
                dpg_set_value(output_time_value_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception:
                pass

        return {'image': None, 'json': output_json, 'audio': None}

    def close(self, node_id):
        """Clean up per-node state when the node is closed."""
        node_id_str = str(node_id)
        for store in (self._kp_history, self._kmeans_models, self._refit_counter,
                      self._last_distance, self._is_alert):
            store.pop(node_id_str, None)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        threshold_value_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':ThresholdValue'
        nclusters_value_tag = tag_node_name + ':' + self.TYPE_INT + ':NClustersValue'
        try:
            pos = dpg.get_item_pos(tag_node_name)
        except Exception:
            pos = [0, 0]

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict['threshold'] = dpg_get_value(threshold_value_tag) or 100.0
        setting_dict['n_clusters'] = dpg_get_value(nclusters_value_tag) or 3
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        threshold_value_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':ThresholdValue'
        nclusters_value_tag = tag_node_name + ':' + self.TYPE_INT + ':NClustersValue'
        try:
            dpg_set_value(threshold_value_tag, float(setting_dict.get('threshold', 100.0)))
            dpg_set_value(nclusters_value_tag, int(setting_dict.get('n_clusters', 3)))
        except Exception:
            pass
