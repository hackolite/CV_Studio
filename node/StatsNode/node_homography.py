#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import time
import copy
import numpy as np
import cv2
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node

_HISTORY_WINDOW_SIZE = 60  # number of positions kept per player for kinematics


class FactoryNode:
    node_label = 'Homography'
    node_tag = 'Homography'

    # Sport options shown in the combobox
    SPORT_OPTIONS = ['Tennis', 'Badminton', 'Paddle']

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
        # Input 1: Master keypoints from pose estimation (for homography calculation)
        node.tag_node_input_master_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input_master_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        # Input 2: Points to transform
        node.tag_node_input_points_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input_points_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        # Static: sport template selector
        node.tag_node_sport_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Sport'
        node.tag_node_sport_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':SportValue'
        # Output: Transformed coordinates
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        if node.tag_node_name not in node._slot_id:
            node._slot_id[node.tag_node_name] = 2

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            with dpg.node_attribute(
                tag=node.tag_node_input_master_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_master_json_value_name,
                    default_value='Master Keypoints (Pose)',
                )

            # Sport template combobox
            with dpg.node_attribute(
                tag=node.tag_node_sport_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_sport_value_name,
                    label='Sport Template',
                    items=self.SPORT_OPTIONS,
                    default_value='Tennis',
                    width=160,
                )
                dpg.add_button(
                    label='Add Input',
                    callback=node._add_slot,
                    user_data=node.tag_node_name,
                )

            with dpg.node_attribute(
                tag=node.tag_node_input_points_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_points_json_value_name,
                    default_value='Points to Transform',
                )

            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='Transformed Coordinates',
                )

            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output02_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='Elapsed time(ms)',
                    )

        return node


class Node(Node):
    _ver = '0.0.2'

    node_label = 'Homography'
    node_tag = 'Homography'

    _opencv_setting_dict = None

    _slot_id = {}
    _max_slot_number = 9

    # -----------------------------------------------------------------------
    # Tennis court template (real-world coordinates, meters)
    # Origin at bottom-left corner of doubles court.
    # Keypoints are ordered to match TennisKeyPoints model output (indices 0-13).
    # -----------------------------------------------------------------------
    TENNIS_COURT_TEMPLATE = {
        "sport": "Tennis",
        "units": "meters",
        "origin": "bottom_left_corner_outside_doubles",
        "court_width": 10.97,
        "court_length": 23.77,
        "keypoints": [
            # Index 0: Far baseline left singles corner (top-left singles)
            {"id": 0,  "name": "far_baseline_left_single_corner", "x": 1.37, "y": 23.77},
            # Index 1: Far baseline right singles corner (top-right singles)
            {"id": 1,  "name": "far_baseline_right_single_corner", "x": 9.60, "y": 23.77},
            # Index 2: Near baseline left doubles corner (bottom-left doubles)
            {"id": 2,  "name": "near_baseline_left_double_corner", "x": 0.00, "y": 0.00},
            # Index 3: Near baseline right doubles corner (bottom-right doubles)
            {"id": 3,  "name": "near_baseline_right_double_corner", "x": 10.97, "y": 0.00},
            # Index 4: Far baseline left service projection (top-left service line)
            {"id": 4,  "name": "far_baseline_left_service_projection", "x": 1.37, "y": 18.285},
            # Index 5: Near baseline left singles corner (bottom-left singles)
            {"id": 5,  "name": "near_baseline_left_single_corner", "x": 1.37, "y": 0.00},
            # Index 6: Far baseline right service projection (top-right service line)
            {"id": 6,  "name": "far_baseline_right_service_projection", "x": 9.60, "y": 18.285},
            # Index 7: Near baseline right singles corner (bottom-right singles)
            {"id": 7,  "name": "near_baseline_right_single_corner", "x": 9.60, "y": 0.00},
            # Index 8: Service box left top corner (near-left service line)
            {"id": 8,  "name": "service_box_left_top_corner", "x": 1.37, "y": 5.485},
            # Index 9: Service box right top corner (near-right service line)
            {"id": 9,  "name": "service_box_right_top_corner", "x": 9.60, "y": 5.485},
            # Index 10: Left singles sideline midpoint (left mid-court)
            {"id": 10, "name": "left_singles_sideline_midpoint", "x": 1.37, "y": 11.885},
            # Index 11: Right singles sideline midpoint (right mid-court)
            {"id": 11, "name": "right_singles_sideline_midpoint", "x": 9.60, "y": 11.885},
            # Index 12: Center service line top T (far center T)
            {"id": 12, "name": "center_service_line_top_T", "x": 5.485, "y": 18.285},
            # Index 13: Center service line bottom T (near center T)
            {"id": 13, "name": "center_service_line_bottom_T", "x": 5.485, "y": 5.485}
        ]
    }

    # -----------------------------------------------------------------------
    # Badminton court template (BWF official, doubles – 6.1 m × 13.4 m)
    # 14 keypoints mapped to the same topological positions as the tennis
    # template so the same TennisKeyPoints ONNX model can be used.
    #
    #  y=0   : near baseline (bottom of image)
    #  y=13.4: far baseline  (top of image)
    #  x=0   : left doubles sideline
    #  x=6.1 : right doubles sideline
    #  x=0.46 / x=5.64: singles sidelines (0.46 m alleys)
    #  y=4.72 = net(6.7) − short_service(1.98) → near short service line
    #  y=8.68 = net(6.7) + short_service(1.98) → far  short service line
    #  y=0.76 / y=12.64: doubles long service lines
    # -----------------------------------------------------------------------
    BADMINTON_COURT_TEMPLATE = {
        "sport": "Badminton",
        "units": "meters",
        "origin": "bottom_left_corner_doubles",
        "court_width": 6.1,
        "court_length": 13.4,
        "keypoints": [
            # Index 0 → far_baseline_left_single  (top-left singles)
            {"id": 0,  "name": "far_baseline_left_single_corner",         "x": 0.46, "y": 13.40},
            # Index 1 → far_baseline_right_single (top-right singles)
            {"id": 1,  "name": "far_baseline_right_single_corner",        "x": 5.64, "y": 13.40},
            # Index 2 → near_baseline_left_double
            {"id": 2,  "name": "near_baseline_left_double_corner",        "x": 0.00, "y": 0.00},
            # Index 3 → near_baseline_right_double
            {"id": 3,  "name": "near_baseline_right_double_corner",       "x": 6.10, "y": 0.00},
            # Index 4 → far long service line left (doubles)
            {"id": 4,  "name": "far_long_service_line_left",              "x": 0.46, "y": 12.64},
            # Index 5 → near_baseline_left_single
            {"id": 5,  "name": "near_baseline_left_single_corner",        "x": 0.46, "y": 0.00},
            # Index 6 → far long service line right (doubles)
            {"id": 6,  "name": "far_long_service_line_right",             "x": 5.64, "y": 12.64},
            # Index 7 → near_baseline_right_single
            {"id": 7,  "name": "near_baseline_right_single_corner",       "x": 5.64, "y": 0.00},
            # Index 8 → near short service line left
            {"id": 8,  "name": "near_short_service_line_left",            "x": 0.46, "y": 4.72},
            # Index 9 → near short service line right
            {"id": 9,  "name": "near_short_service_line_right",           "x": 5.64, "y": 4.72},
            # Index 10 → left net post (net mid-court)
            {"id": 10, "name": "left_net_post",                           "x": 0.00, "y": 6.70},
            # Index 11 → right net post
            {"id": 11, "name": "right_net_post",                          "x": 6.10, "y": 6.70},
            # Index 12 → far short service center T
            {"id": 12, "name": "far_short_service_center_T",              "x": 3.05, "y": 8.68},
            # Index 13 → near short service center T
            {"id": 13, "name": "near_short_service_center_T",             "x": 3.05, "y": 4.72},
        ]
    }

    # -----------------------------------------------------------------------
    # Padel court template (FIP official – 20 m × 10 m)
    # No singles/doubles distinction; service boxes split by center line.
    #  y=0   : near baseline
    #  y=20  : far  baseline
    #  y=3   : near service line  (3 m from baseline)
    #  y=17  : far  service line  (20−3)
    #  y=10  : net
    #  x=5   : center line
    # -----------------------------------------------------------------------
    PADDLE_COURT_TEMPLATE = {
        "sport": "Paddle",
        "units": "meters",
        "origin": "bottom_left_corner",
        "court_width": 10.0,
        "court_length": 20.0,
        "keypoints": [
            # Index 0 → far_baseline_left
            {"id": 0,  "name": "far_baseline_left_corner",                "x": 0.00, "y": 20.00},
            # Index 1 → far_baseline_right
            {"id": 1,  "name": "far_baseline_right_corner",               "x": 10.00, "y": 20.00},
            # Index 2 → near_baseline_left
            {"id": 2,  "name": "near_baseline_left_corner",               "x": 0.00, "y": 0.00},
            # Index 3 → near_baseline_right
            {"id": 3,  "name": "near_baseline_right_corner",              "x": 10.00, "y": 0.00},
            # Index 4 → far service line left projection
            {"id": 4,  "name": "far_service_line_left",                   "x": 0.00, "y": 17.00},
            # Index 5 → near_baseline_left (no alley in padel → same as index 2)
            {"id": 5,  "name": "near_baseline_left_inner",                "x": 0.00, "y": 0.00},
            # Index 6 → far service line right projection
            {"id": 6,  "name": "far_service_line_right",                  "x": 10.00, "y": 17.00},
            # Index 7 → near_baseline_right (same as index 3)
            {"id": 7,  "name": "near_baseline_right_inner",               "x": 10.00, "y": 0.00},
            # Index 8 → near service line left
            {"id": 8,  "name": "near_service_line_left",                  "x": 0.00, "y": 3.00},
            # Index 9 → near service line right
            {"id": 9,  "name": "near_service_line_right",                 "x": 10.00, "y": 3.00},
            # Index 10 → left net post
            {"id": 10, "name": "left_net_post",                           "x": 0.00, "y": 10.00},
            # Index 11 → right net post
            {"id": 11, "name": "right_net_post",                          "x": 10.00, "y": 10.00},
            # Index 12 → far center T (center line × far service line)
            {"id": 12, "name": "far_center_T",                            "x": 5.00, "y": 17.00},
            # Index 13 → near center T (center line × near service line)
            {"id": 13, "name": "near_center_T",                           "x": 5.00, "y": 3.00},
        ]
    }

    # Lookup by sport name
    SPORT_TEMPLATES = {}  # populated after class definition

    def __init__(self):
        self._homography_matrix = None
        self._selected_template = self.TENNIS_COURT_TEMPLATE
        # Per-player kinematics tracking
        # {label: [(court_x, court_y, timestamp), ...]}
        self._player_history = {}
        # Per-player maximum speed observed (m/s)
        self._player_max_speed = {}
        self._last_call_time = None

    def _get_template_points(self):
        """Get template points as numpy array for homography calculation."""
        points = []
        for kp in self._selected_template["keypoints"]:
            points.append([kp["x"], kp["y"]])
        return np.array(points, dtype=np.float32)

    def _calculate_homography(self, detected_keypoints):
        """
        Calculate homography matrix from detected keypoints to real-world coordinates.
        
        Args:
            detected_keypoints: numpy array of shape (N, 2) with detected keypoint positions in image
            
        Returns:
            homography_matrix: 3x3 transformation matrix, or None if calculation fails
        """
        template_points = self._get_template_points()
        
        # Ensure we have the same number of points
        if detected_keypoints.shape[0] != template_points.shape[0]:
            return None
            
        # Need at least 4 points for homography
        if detected_keypoints.shape[0] < 4:
            return None
            
        try:
            # Calculate homography from image coordinates to real-world coordinates
            # detected_keypoints: source points (in image)
            # template_points: destination points (real-world)
            H, mask = cv2.findHomography(detected_keypoints, template_points, cv2.RANSAC, 5.0)
            return H
        except Exception as e:
            print(f"Error calculating homography: {e}")
            return None

    def _extract_bottom_center_from_bboxes(self, bboxes):
        """
        Extract bottom-center points from bounding boxes.
        For player detection, the bottom-center of the bbox represents the player's position on the ground.
        
        Args:
            bboxes: list of bounding boxes in format [x1, y1, x2, y2]
            
        Returns:
            points: numpy array of shape (N, 2) with bottom-center coordinates
        """
        if not bboxes or len(bboxes) == 0:
            return None
        
        points = []
        for i, bbox in enumerate(bboxes):
            # Validate bbox format
            if not isinstance(bbox, (list, tuple, np.ndarray)) or len(bbox) < 4:
                print(f"Warning: Invalid bbox format at index {i}, skipping: {bbox}")
                continue
                
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            
            # Validate bbox coordinates
            if x2 <= x1 or y2 <= y1:
                print(f"Warning: Invalid bbox coordinates at index {i} (x2 <= x1 or y2 <= y1), skipping: {bbox}")
                continue
            
            # Bottom center: x is center of bbox, y is bottom of bbox
            center_x = (x1 + x2) / 2.0
            bottom_y = y2
            points.append([center_x, bottom_y])
        
        if len(points) == 0:
            return None
            
        return np.array(points, dtype=np.float32)

    def _transform_points(self, points, homography_matrix):
        """
        Transform points using homography matrix.
        
        Args:
            points: numpy array of shape (N, 2) or list of points
            homography_matrix: 3x3 homography matrix
            
        Returns:
            transformed_points: numpy array of transformed coordinates
        """
        if homography_matrix is None:
            return None
            
        # Convert to numpy array if needed
        if not isinstance(points, np.ndarray):
            points = np.array(points, dtype=np.float32)
        
        # Reshape if needed
        if len(points.shape) == 1:
            points = points.reshape(-1, 2)
            
        # Transform points using perspective transform
        try:
            # Add homogeneous coordinate
            points_h = np.column_stack([points, np.ones(points.shape[0])])
            # Apply transformation
            transformed_h = homography_matrix @ points_h.T
            # Convert back from homogeneous coordinates
            transformed = (transformed_h[:2, :] / transformed_h[2, :]).T
            return transformed
        except Exception as e:
            print(f"Error transforming points: {e}")
            return None

    def _calculate_averages_by_label(self, transformed_points, class_ids, class_names):
        """
        Calculate average x and y coordinates for each unique label.
        
        Args:
            transformed_points: numpy array of transformed coordinates
            class_ids: list of class IDs for each point
            class_names: dict or list of class names
            
        Returns:
            dict mapping label to average coordinates [x, y]
        """
        if transformed_points is None or len(transformed_points) == 0:
            # No points to average - this is expected when no detections are present
            return {}
        
        # Group points by label
        label_points = {}
        for i, point in enumerate(transformed_points):
            if i < len(class_ids):
                class_id = class_ids[i]
                # Get label from class_names
                if isinstance(class_names, dict):
                    label = class_names.get(class_id, None)
                elif isinstance(class_names, list) and class_id < len(class_names):
                    label = class_names[class_id]
                else:
                    label = None
                
                # Skip objects without valid ReId labels
                if label is None:
                    continue
                
                # Add point to this label's list
                if label not in label_points:
                    label_points[label] = []
                label_points[label].append(point)
        
        # Calculate average for each label
        averages = {}
        for label, points in label_points.items():
            points_array = np.array(points)
            avg_x = np.mean(points_array[:, 0])
            avg_y = np.mean(points_array[:, 1])
            averages[label] = [float(avg_x), float(avg_y)]
        
        return averages

    def _compute_player_kinematics(self, averages_by_label, current_time):
        """Compute speed, acceleration and cumulative distance per player.

        Args:
            averages_by_label: dict ``{label: [court_x, court_y]}`` from the
                current frame (real-world metres).
            current_time: monotonic timestamp (seconds).

        Returns:
            dict ``{label: {speed_ms, acceleration_ms2, distance_m, position}}``
        """
        stats = {}
        for label, (cx, cy) in averages_by_label.items():
            history = self._player_history.setdefault(label, [])
            history.append((float(cx), float(cy), current_time))

            # Keep a rolling window of the last _HISTORY_WINDOW_SIZE positions
            if len(history) > _HISTORY_WINDOW_SIZE:
                self._player_history[label] = history[-_HISTORY_WINDOW_SIZE:]
                history = self._player_history[label]

            if len(history) < 2:
                stats[label] = {
                    'speed_ms': 0.0,
                    'max_speed_ms': self._player_max_speed.get(label, 0.0),
                    'acceleration_ms2': 0.0,
                    'distance_m': 0.0,
                    'position': [round(cx, 3), round(cy, 3)],
                }
                continue

            # Instantaneous speed between the last two positions
            x1, y1, t1 = history[-2]
            x2, y2, t2 = history[-1]
            dt = t2 - t1
            if dt < 1e-6:
                speed = 0.0
            else:
                speed = float(np.hypot(x2 - x1, y2 - y1)) / dt  # m/s

            # Track max speed observed for this player
            prev_max = self._player_max_speed.get(label, 0.0)
            if speed > prev_max:
                self._player_max_speed[label] = speed
            max_speed = self._player_max_speed[label]

            # Instantaneous acceleration between the last three positions
            if len(history) >= 3:
                x0, y0, t0 = history[-3]
                dt01 = t1 - t0
                if dt01 < 1e-6:
                    prev_speed = 0.0
                else:
                    prev_speed = float(np.hypot(x1 - x0, y1 - y0)) / dt01
                accel = (speed - prev_speed) / max(dt, 1e-6)
            else:
                accel = 0.0

            # Total distance over the entire history window – vectorised
            pts = np.array([(h[0], h[1]) for h in history], dtype=np.float32)
            deltas = np.diff(pts, axis=0)
            total_dist = float(np.sum(np.linalg.norm(deltas, axis=1)))

            stats[label] = {
                'speed_ms': round(speed, 3),
                'max_speed_ms': round(max_speed, 3),
                'acceleration_ms2': round(accel, 3),
                'distance_m': round(total_dist, 3),
                'position': [round(cx, 3), round(cy, 3)],
            }

        return stats

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        sport_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':SportValue'

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Read selected sport template from combobox (preserve existing if DPG not available)
        selected_sport = dpg_get_value(sport_value_tag)
        if selected_sport:
            self._selected_template = self.SPORT_TEMPLATES.get(selected_sport, self.TENNIS_COURT_TEMPLATE)
        else:
            # DPG not initialised (e.g. in tests) – keep whatever is already selected
            selected_sport = self._selected_template.get('sport', 'Tennis')

        # Find connections – Input01 is master keypoints; Input02..N are dynamic transform inputs
        master_keypoints_src = ''
        dynamic_inputs_src = {}  # {slot_number: src_key}

        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            connection_target = connection_info[1]

            if connection_type == self.TYPE_JSON or connection_type.upper() == 'JSON':
                m = re.search(r':Input(\d+)$', connection_target)
                if m:
                    slot_num = int(m.group(1))
                    src = ':'.join(connection_info[0].split(':')[:2])
                    if slot_num == 1:
                        master_keypoints_src = src
                    elif slot_num >= 2:
                        dynamic_inputs_src[slot_num] = src

        # Get JSON data
        master_json_data = node_result_dict.get(master_keypoints_src, None) if master_keypoints_src else None
        # Collect all dynamic input data (for backward compat, also expose slot 2 as points_json_data)
        dynamic_json_data = {
            slot: node_result_dict.get(src, None)
            for slot, src in dynamic_inputs_src.items()
        }
        points_json_data = dynamic_json_data.get(2, None)

        if use_pref_counter and (master_json_data is not None or any(v is not None for v in dynamic_json_data.values())):
            start_time = time.monotonic()

        # Process homography
        output_data = None

        if master_json_data is not None:
            # Extract keypoints from pose estimation output
            if isinstance(master_json_data, dict) and 'results_list' in master_json_data:
                detected_keypoints = master_json_data['results_list']

                # Calculate homography matrix
                if isinstance(detected_keypoints, np.ndarray):
                    self._homography_matrix = self._calculate_homography(detected_keypoints)

                    # Prepare output data
                    output_data = {
                        'homography_matrix': self._homography_matrix.tolist() if self._homography_matrix is not None else None,
                        'template': self._selected_template,
                        'sport': selected_sport,
                        'detected_keypoints': detected_keypoints.tolist(),
                        'transformed_points': None,
                        'input_points': None,
                        'transformed_inputs': {},
                    }

        # Process each dynamic input slot
        if self._homography_matrix is not None and dynamic_json_data:
            if output_data is None:
                output_data = {
                    'homography_matrix': self._homography_matrix.tolist(),
                    'template': self._selected_template,
                    'sport': selected_sport,
                    'transformed_inputs': {},
                }
            if 'transformed_inputs' not in output_data:
                output_data['transformed_inputs'] = {}

            for slot_num in sorted(dynamic_json_data.keys()):
                slot_json_data = dynamic_json_data[slot_num]
                if slot_json_data is None:
                    continue

                slot_result = self._process_single_input(slot_json_data, slot_num)
                if slot_result is not None:
                    output_data['transformed_inputs'][slot_num] = slot_result

                    # Backward compatibility: expose slot 2 fields at the top level
                    if slot_num == 2:
                        output_data['input_points'] = slot_result.get('input_points')
                        output_data['transformed_points'] = slot_result.get('transformed_points')
                        if 'bboxes' in slot_result:
                            output_data['bboxes'] = slot_result['bboxes']
                        if 'class_ids' in slot_result:
                            output_data['class_ids'] = slot_result['class_ids']
                        if 'class_names' in slot_result:
                            output_data['class_names'] = slot_result['class_names']
                        if 'scores' in slot_result:
                            output_data['scores'] = slot_result['scores']
                        if 'averages_by_label' in slot_result:
                            output_data['averages_by_label'] = slot_result['averages_by_label']
                        if 'player_stats' in slot_result:
                            output_data['player_stats'] = slot_result['player_stats']

        if use_pref_counter and (master_json_data is not None or any(v is not None for v in dynamic_json_data.values())):
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            try:
                dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception:
                pass  # DPG not initialized (e.g., in tests)

        return {"image": None, "json": output_data, "audio": None}

    def _process_single_input(self, points_json_data, slot_num):
        """Extract, transform points from one dynamic input and return a result dict."""
        points_to_transform = None
        bboxes_list = None

        if isinstance(points_json_data, dict):
            if 'bboxes' in points_json_data:
                bboxes_list = points_json_data['bboxes']
                points_to_transform = self._extract_bottom_center_from_bboxes(bboxes_list)
                print(
                    f"[Homography] Input{str(slot_num).zfill(2)}: Extracted "
                    f"{len(points_to_transform) if points_to_transform is not None else 0} "
                    f"player positions from bboxes"
                )
            elif 'keypoints' in points_json_data:
                keypoints = points_json_data['keypoints']
                pts = []
                for kp in keypoints:
                    if isinstance(kp, dict) and 'x' in kp and 'y' in kp:
                        pts.append([kp['x'], kp['y']])
                points_to_transform = np.array(pts, dtype=np.float32) if pts else None
            elif 'points' in points_json_data:
                points_to_transform = np.array(points_json_data['points'], dtype=np.float32)
        elif isinstance(points_json_data, (list, np.ndarray)):
            points_to_transform = np.array(points_json_data, dtype=np.float32)

        if points_to_transform is None or len(points_to_transform) == 0:
            return None

        transformed = self._transform_points(points_to_transform, self._homography_matrix)
        if transformed is None:
            return None

        result = {
            'input_points': points_to_transform.tolist(),
            'transformed_points': transformed.tolist(),
        }

        if bboxes_list is not None:
            result['bboxes'] = bboxes_list

        if isinstance(points_json_data, dict):
            if 'class_ids' in points_json_data:
                result['class_ids'] = points_json_data['class_ids']
            if 'class_names' in points_json_data:
                result['class_names'] = points_json_data['class_names']
            if 'scores' in points_json_data:
                result['scores'] = points_json_data['scores']

        # Calculate averages by label
        averages_by_label = {}
        if (
            isinstance(points_json_data, dict)
            and 'class_ids' in points_json_data
            and 'class_names' in points_json_data
        ):
            averages_by_label = self._calculate_averages_by_label(
                transformed,
                points_json_data['class_ids'],
                points_json_data['class_names'],
            )
            result['averages_by_label'] = averages_by_label

        # Compute per-player kinematics
        if averages_by_label:
            current_time = time.monotonic()
            player_stats = self._compute_player_kinematics(averages_by_label, current_time)
            result['player_stats'] = player_stats

        # Console output
        CONSOLE_WIDTH = 70
        print("\n" + "=" * CONSOLE_WIDTH)
        print(f"[Homography] Input{str(slot_num).zfill(2)} Coordinate Transformation:")
        print("=" * CONSOLE_WIDTH)
        for i, (orig, trans) in enumerate(zip(points_to_transform, transformed)):
            label = ""
            if isinstance(points_json_data, dict) and 'class_ids' in points_json_data and 'class_names' in points_json_data:
                class_ids = points_json_data['class_ids']
                class_names = points_json_data['class_names']
                if i < len(class_ids):
                    class_id = class_ids[i]
                    if isinstance(class_names, dict):
                        label = f" ({class_names.get(class_id, f'Object {class_id}')})"
                    elif isinstance(class_names, list) and class_id < len(class_names):
                        label = f" ({class_names[class_id]})"
            print(f"  Object {i+1}{label}:")
            print(f"    Image coordinates (pixels): ({orig[0]:.1f}, {orig[1]:.1f})")
            print(f"    Court coordinates (meters): ({trans[0]:.2f}, {trans[1]:.2f})")

        if averages_by_label:
            print("\n" + "-" * CONSOLE_WIDTH)
            print("[Homography] Average Positions by Label:")
            print("-" * CONSOLE_WIDTH)
            for lbl, avg_coords in averages_by_label.items():
                print(f"  {lbl}:")
                print(f"    Average court coordinates (meters): ({avg_coords[0]:.2f}, {avg_coords[1]:.2f})")

        player_stats = result.get('player_stats', {})
        if player_stats:
            print("\n" + "-" * CONSOLE_WIDTH)
            print("[Homography] Player Kinematics:")
            print("-" * CONSOLE_WIDTH)
            for lbl, s in player_stats.items():
                print(f"  {lbl}:")
                print(f"    Speed:        {s['speed_ms']:.3f} m/s")
                print(f"    Max Speed:    {s['max_speed_ms']:.3f} m/s")
                print(f"    Acceleration: {s['acceleration_ms2']:.3f} m/s²")
                print(f"    Distance:     {s['distance_m']:.3f} m")

        print("=" * CONSOLE_WIDTH + "\n")

        return result

    def close(self, node_id):
        pass

    def _add_slot(self, sender, data, user_data):
        tag_node_name = user_data

        if self._max_slot_number > self._slot_id[tag_node_name]:
            self._slot_id[tag_node_name] += 1
            slot_number = self._slot_id[tag_node_name]

            prev_slot_number = slot_number - 1
            before_tag = (
                tag_node_name + ':' + self.TYPE_JSON + ':Input'
                + str(prev_slot_number).zfill(2)
            )

            tag_input_name = (
                tag_node_name + ':' + self.TYPE_JSON + ':Input'
                + str(slot_number).zfill(2)
            )
            tag_input_value_name = tag_input_name + 'Value'

            with dpg.node_attribute(
                tag=tag_input_name,
                attribute_type=dpg.mvNode_Attr_Input,
                parent=tag_node_name,
                before=before_tag,
            ):
                dpg.add_text(
                    tag=tag_input_value_name,
                    default_value='Points to Transform',
                )

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        sport_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':SportValue'
        try:
            pos = dpg.get_item_pos(tag_node_name)
        except Exception:
            pos = [0, 0]  # Default position if DPG not initialized

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict['sport'] = dpg_get_value(sport_value_tag) or 'Tennis'
        setting_dict['slot_id'] = self._slot_id.get(tag_node_name, 2)

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        sport_value_tag = tag_node_name + ':' + self.TYPE_TEXT + ':SportValue'
        try:
            dpg_set_value(sport_value_tag, setting_dict.get('sport', 'Tennis'))
        except Exception:
            pass

        slot_number = int(setting_dict.get('slot_id', 2))
        for slot_idx in range(3, slot_number + 1):
            self._add_slot(None, None, tag_node_name)


# Populate SPORT_TEMPLATES after the class is fully defined
Node.SPORT_TEMPLATES = {
    'Tennis': Node.TENNIS_COURT_TEMPLATE,
    'Badminton': Node.BADMINTON_COURT_TEMPLATE,
    'Paddle': Node.PADDLE_COURT_TEMPLATE,
}
