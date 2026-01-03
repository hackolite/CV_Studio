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
    node_label = 'Homography'
    node_tag = 'Homography'

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
        # Output: Transformed coordinates
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

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
    _ver = '0.0.1'

    node_label = 'Homography'
    node_tag = 'Homography'

    _opencv_setting_dict = None

    # Tennis court template in meters (real-world coordinates)
    # Origin at bottom-left corner of doubles court
    # NOTE: Keypoints are ordered to match TennisKeyPoints model output (indices 0-13)
    TENNIS_COURT_TEMPLATE = {
        "units": "meters",
        "origin": "bottom_left_corner_outside_doubles",
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

    def __init__(self):
        self._homography_matrix = None

    def _get_template_points(self):
        """Get template points as numpy array for homography calculation."""
        points = []
        for kp in self.TENNIS_COURT_TEMPLATE["keypoints"]:
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

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Find connections
        master_keypoints_src = ''
        points_to_transform_src = ''
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            connection_target = connection_info[1]
            
            # Match case-insensitively or use both Json and JSON
            if connection_type == self.TYPE_JSON or connection_type.upper() == 'JSON':
                # Check which input this connects to
                if ':Input01' in connection_target:
                    # Master keypoints input
                    master_keypoints_src = connection_info[0]
                    master_keypoints_src = master_keypoints_src.split(':')[:2]
                    master_keypoints_src = ':'.join(master_keypoints_src)
                elif ':Input02' in connection_target:
                    # Points to transform input
                    points_to_transform_src = connection_info[0]
                    points_to_transform_src = points_to_transform_src.split(':')[:2]
                    points_to_transform_src = ':'.join(points_to_transform_src)

        # Get JSON data
        master_json_data = node_result_dict.get(master_keypoints_src, None) if master_keypoints_src else None
        points_json_data = node_result_dict.get(points_to_transform_src, None) if points_to_transform_src else None

        if use_pref_counter and (master_json_data is not None or points_json_data is not None):
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
                        'template': self.TENNIS_COURT_TEMPLATE,
                        'detected_keypoints': detected_keypoints.tolist(),
                        'transformed_points': None,
                        'input_points': None
                    }
        
        # If we have points to transform and a valid homography matrix
        if points_json_data is not None and self._homography_matrix is not None:
            # Extract points from input
            points_to_transform = None
            bboxes_list = None  # Store original bboxes for reference
            
            if isinstance(points_json_data, dict):
                # Check for 'bboxes' field (from ObjectDetection node)
                if 'bboxes' in points_json_data:
                    bboxes_list = points_json_data['bboxes']
                    # Extract bottom-center points from bounding boxes
                    points_to_transform = self._extract_bottom_center_from_bboxes(bboxes_list)
                    print(f"[Homography] Extracted {len(points_to_transform) if points_to_transform is not None else 0} player positions from bboxes")
                # Check for 'keypoints' field (structured input)
                elif 'keypoints' in points_json_data:
                    keypoints = points_json_data['keypoints']
                    points_to_transform = []
                    for kp in keypoints:
                        if isinstance(kp, dict) and 'x' in kp and 'y' in kp:
                            points_to_transform.append([kp['x'], kp['y']])
                    points_to_transform = np.array(points_to_transform, dtype=np.float32)
                # Check for direct points array
                elif 'points' in points_json_data:
                    points_to_transform = np.array(points_json_data['points'], dtype=np.float32)
            elif isinstance(points_json_data, (list, np.ndarray)):
                points_to_transform = np.array(points_json_data, dtype=np.float32)
            
            # Transform the points
            if points_to_transform is not None and len(points_to_transform) > 0:
                transformed = self._transform_points(points_to_transform, self._homography_matrix)
                
                if output_data is None:
                    output_data = {
                        'homography_matrix': self._homography_matrix.tolist(),
                        'template': self.TENNIS_COURT_TEMPLATE,
                    }
                
                output_data['input_points'] = points_to_transform.tolist()
                output_data['transformed_points'] = transformed.tolist() if transformed is not None else None
                
                # Store original bboxes if available
                if bboxes_list is not None:
                    output_data['bboxes'] = bboxes_list
                
                # Pass through class information for label-based averaging
                if 'class_ids' in points_json_data:
                    output_data['class_ids'] = points_json_data['class_ids']
                if 'class_names' in points_json_data:
                    output_data['class_names'] = points_json_data['class_names']
                if 'scores' in points_json_data:
                    output_data['scores'] = points_json_data['scores']
                
                # Display coordinate transformation in console
                CONSOLE_WIDTH = 70  # Character width for console output
                print("\n" + "="*CONSOLE_WIDTH)
                print("[Homography] Coordinate Transformation:")
                print("="*CONSOLE_WIDTH)
                if transformed is not None:
                    for i, (orig, trans) in enumerate(zip(points_to_transform, transformed)):
                        # Display label if available
                        label = ""
                        if 'class_ids' in points_json_data and 'class_names' in points_json_data:
                            class_ids = points_json_data['class_ids']
                            class_names = points_json_data['class_names']
                            if i < len(class_ids):
                                class_id = class_ids[i]
                                if isinstance(class_names, dict):
                                    label = f" ({class_names.get(class_id, f'Object {class_id}')})"
                                elif isinstance(class_names, list) and class_id < len(class_names):
                                    label = f" ({class_names[class_id]})"
                        
                        print(f"  Player {i+1}{label}:")
                        print(f"    Image coordinates (pixels): ({orig[0]:.1f}, {orig[1]:.1f})")
                        print(f"    Court coordinates (meters): ({trans[0]:.2f}, {trans[1]:.2f})")
                print("="*CONSOLE_WIDTH + "\n")

        if use_pref_counter and (master_json_data is not None or points_json_data is not None):
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            try:
                dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception:
                pass  # DPG not initialized (e.g., in tests)

        return {"image": None, "json": output_data, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        try:
            pos = dpg.get_item_pos(tag_node_name)
        except Exception:
            pos = [0, 0]  # Default position if DPG not initialized

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
