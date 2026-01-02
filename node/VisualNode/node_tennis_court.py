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
    node_label = 'TennisCourt'
    node_tag = 'TennisCourt'

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
        # Input: Homography JSON from Homography node
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        # Output: Image with drawn tennis court and points
        node.tag_node_output_image_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output_image_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        # Output: JSON with transformed points
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output02'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output02Value'
        # Output: Elapsed time
        node.tag_node_output_time_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output03'
        node.tag_node_output_time_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output03Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create black image for initialization
        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        # Create texture for output image
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output_image_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # JSON Input
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Homography JSON',
                )

            # Image Output
            with dpg.node_attribute(
                tag=node.tag_node_output_image_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output_image_value_name)

            # JSON Output
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='Transformed Points JSON',
                )

            # Time Output
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

    node_label = 'TennisCourt'
    node_tag = 'TennisCourt'

    _opencv_setting_dict = None
    
    # Tennis court dimensions (in meters)
    COURT_WIDTH_M = 10.97  # Doubles court width
    COURT_LENGTH_M = 23.77  # Full court length
    
    # Visualization constants
    VISUALIZATION_MARGIN = 100  # Total margin in pixels (50px on each side)

    def __init__(self):
        pass

    def _draw_tennis_court(self, image, template, scale=40, offset_x=50, offset_y=50):
        """
        Draw tennis court based on template coordinates.
        Inspired by Tennis-Tracker repository (github.com/abhroroy365/Tennis-Tracker)
        
        Args:
            image: numpy array to draw on
            template: tennis court template with keypoints in meters
            scale: pixels per meter
            offset_x, offset_y: offset from top-left corner
            
        Returns:
            image with court drawn
        """
        if template is None or 'keypoints' not in template:
            return image
        
        img = image.copy()
        keypoints = template['keypoints']
        
        # Convert template coordinates to image coordinates
        def template_to_image(x, y):
            px = int(x * scale + offset_x)
            py = int(y * scale + offset_y)
            return (px, py)
        
        # Color definitions
        line_color = (255, 255, 255)  # White
        court_color = (0, 150, 0)     # Green background
        net_color = (255, 0, 0)       # Blue for net (like Tennis-Tracker) - BGR format
        keypoint_color = (0, 0, 255)  # Red for keypoints - BGR format
        line_thickness = 2
        
        # Draw green background (approximation of court area)
        court_width = int(self.COURT_WIDTH_M * scale)
        court_length = int(self.COURT_LENGTH_M * scale)
        cv2.rectangle(img, 
                     (offset_x, offset_y), 
                     (offset_x + court_width, offset_y + court_length),
                     court_color, -1)
        
        # Extract key points by name
        kp_dict = {kp['name']: (kp['x'], kp['y']) for kp in keypoints}
        
        # Draw doubles boundary
        if all(k in kp_dict for k in ['doubles_bl', 'doubles_br', 'doubles_tr', 'doubles_tl']):
            pts_doubles = np.array([
                template_to_image(*kp_dict['doubles_bl']),
                template_to_image(*kp_dict['doubles_br']),
                template_to_image(*kp_dict['doubles_tr']),
                template_to_image(*kp_dict['doubles_tl']),
            ], np.int32)
            cv2.polylines(img, [pts_doubles], True, line_color, line_thickness)
        
        # Draw singles boundary
        if all(k in kp_dict for k in ['singles_bl', 'singles_br', 'singles_tr', 'singles_tl']):
            pts_singles = np.array([
                template_to_image(*kp_dict['singles_bl']),
                template_to_image(*kp_dict['singles_br']),
                template_to_image(*kp_dict['singles_tr']),
                template_to_image(*kp_dict['singles_tl']),
            ], np.int32)
            cv2.polylines(img, [pts_singles], True, line_color, line_thickness)
        
        # Draw service boxes
        if all(k in kp_dict for k in ['service_bl', 'service_br']):
            pt1 = template_to_image(*kp_dict['service_bl'])
            pt2 = template_to_image(*kp_dict['service_br'])
            cv2.line(img, pt1, pt2, line_color, line_thickness)
        
        if all(k in kp_dict for k in ['service_tl', 'service_tr']):
            pt1 = template_to_image(*kp_dict['service_tl'])
            pt2 = template_to_image(*kp_dict['service_tr'])
            cv2.line(img, pt1, pt2, line_color, line_thickness)
        
        # Draw center line
        if all(k in kp_dict for k in ['center_t_bottom', 'center_t_top']):
            pt1 = template_to_image(*kp_dict['center_t_bottom'])
            pt2 = template_to_image(*kp_dict['center_t_top'])
            cv2.line(img, pt1, pt2, line_color, line_thickness)
        
        # Draw center T's (service line to singles sideline)
        if 'center_t_bottom' in kp_dict and 'singles_bl' in kp_dict:
            pt1 = template_to_image(*kp_dict['center_t_bottom'])
            pt2 = template_to_image(kp_dict['singles_bl'][0], kp_dict['center_t_bottom'][1])
            cv2.line(img, pt1, pt2, line_color, line_thickness)
            
            pt3 = template_to_image(*kp_dict['center_t_bottom'])
            pt4 = template_to_image(kp_dict['singles_br'][0], kp_dict['center_t_bottom'][1])
            cv2.line(img, pt3, pt4, line_color, line_thickness)
        
        if 'center_t_top' in kp_dict and 'singles_tl' in kp_dict:
            pt1 = template_to_image(*kp_dict['center_t_top'])
            pt2 = template_to_image(kp_dict['singles_tl'][0], kp_dict['center_t_top'][1])
            cv2.line(img, pt1, pt2, line_color, line_thickness)
            
            pt3 = template_to_image(*kp_dict['center_t_top'])
            pt4 = template_to_image(kp_dict['singles_tr'][0], kp_dict['center_t_top'][1])
            cv2.line(img, pt3, pt4, line_color, line_thickness)
        
        # Draw NET LINE at center of court (inspired by Tennis-Tracker)
        # Net is at half court length (11.88m from each baseline)
        if 'doubles_bl' in kp_dict and 'doubles_br' in kp_dict:
            net_y = self.COURT_LENGTH_M / 2.0  # Center of court
            net_start = template_to_image(0, net_y)
            net_end = template_to_image(self.COURT_WIDTH_M, net_y)
            cv2.line(img, net_start, net_end, net_color, line_thickness)
        
        # Draw keypoint circles (inspired by Tennis-Tracker mini_court.py)
        # Draw circles at major court corners for visual reference
        for kp in keypoints:
            pt = template_to_image(kp['x'], kp['y'])
            cv2.circle(img, pt, 5, keypoint_color, -1)
        
        return img

    def _draw_transformed_points(self, image, transformed_points, scale=40, offset_x=50, offset_y=50):
        """
        Draw transformed points on the court visualization.
        Inspired by Tennis-Tracker repository for better point visualization.
        
        Args:
            image: numpy array to draw on
            transformed_points: list of [x, y] coordinates in meters
            scale: pixels per meter (same as court drawing)
            offset_x, offset_y: offset from top-left corner (same as court drawing)
            
        Returns:
            image with points drawn
        """
        if transformed_points is None or len(transformed_points) == 0:
            return image
        
        img = image.copy()
        
        # Color scheme inspired by Tennis-Tracker
        # Green for players/objects (matches court theme)
        player_color = (0, 255, 0)  # Green
        
        # Draw each transformed point
        for i, point in enumerate(transformed_points):
            if len(point) >= 2:
                x_meters, y_meters = point[0], point[1]
                px = int(x_meters * scale + offset_x)
                py = int(y_meters * scale + offset_y)
                
                # Draw point as colored circle (similar to Tennis-Tracker style)
                # Using 5px radius for clean, visible markers
                cv2.circle(img, (px, py), 5, player_color, -1)
                
                # Optional: Draw point index for tracking
                # Smaller, less intrusive label
                cv2.putText(img, str(i), (px + 8, py + 3),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return img

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_image_value_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_time_value_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output03Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Find JSON input connection
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON or connection_type.upper() == 'JSON':
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)
                break

        # Get JSON data from Homography node
        json_data = node_result_dict.get(connection_info_src, None) if connection_info_src else None

        if use_pref_counter and json_data is not None:
            start_time = time.monotonic()

        # Create output image and JSON
        output_image = None
        output_json = None
        
        if json_data is not None:
            # Extract template and transformed points
            template = json_data.get('template', None)
            transformed_points = json_data.get('transformed_points', None)
            
            # Create blank image
            output_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
            
            # Calculate scale to fit court in image
            # Use class constants for court dimensions
            scale_x = (small_window_w - self.VISUALIZATION_MARGIN) / self.COURT_WIDTH_M
            scale_y = (small_window_h - self.VISUALIZATION_MARGIN) / self.COURT_LENGTH_M
            scale = min(scale_x, scale_y)  # Use smaller scale to fit both dimensions
            
            # Center the court
            court_width_px = int(self.COURT_WIDTH_M * scale)
            court_length_px = int(self.COURT_LENGTH_M * scale)
            offset_x = (small_window_w - court_width_px) // 2
            offset_y = (small_window_h - court_length_px) // 2
            
            # Draw tennis court
            output_image = self._draw_tennis_court(output_image, template, scale, offset_x, offset_y)
            
            # Draw transformed points if available
            if transformed_points is not None:
                output_image = self._draw_transformed_points(output_image, transformed_points, scale, offset_x, offset_y)
            
            # Prepare output JSON (pass through with visualization metadata)
            output_json = copy.deepcopy(json_data)
            output_json['visualization'] = {
                'scale': scale,
                'offset_x': offset_x,
                'offset_y': offset_y,
                'image_width': small_window_w,
                'image_height': small_window_h
            }

        if use_pref_counter and json_data is not None:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            try:
                dpg_set_value(output_time_value_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception:
                pass  # DPG not initialized (e.g., in tests)

        # Update texture if we have an output image
        if output_image is not None:
            try:
                texture = self.convert_cv_to_dpg(
                    output_image,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(output_image_value_tag, texture)
            except Exception:
                pass  # DPG not initialized (e.g., in tests)

        return {"image": output_image, "json": output_json, "audio": None}

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
