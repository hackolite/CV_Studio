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
        
        # Use dedicated visualization dimensions for tennis court display
        small_window_w = Node.VISUALIZATION_WIDTH
        small_window_h = Node.VISUALIZATION_HEIGHT
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
    # Display dimensions: 600x800 (1:1.33 aspect ratio) provides adequate space
    # for tennis court (10.97m x 23.77m, 1:2.17 physical aspect ratio) with margins
    VISUALIZATION_WIDTH = 600   # Display width in pixels
    VISUALIZATION_HEIGHT = 800  # Display height in pixels
    VISUALIZATION_MARGIN = 60   # Total margin in pixels (30px on each side)

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
        
        # Draw doubles boundary using the new keypoint names
        # Doubles court corners: near_baseline_left/right_double_corner and far_baseline_left/right_single_corner
        doubles_corners = [
            'near_baseline_left_double_corner',   # Bottom-left (0, 0)
            'near_baseline_right_double_corner',  # Bottom-right (10.97, 0)
        ]
        
        # For top corners, we need to use the far baseline points
        # but extend them to doubles width since we only have singles corners at far end
        if all(k in kp_dict for k in ['near_baseline_left_double_corner', 'near_baseline_right_double_corner']):
            # Draw doubles rectangle using known coordinates
            bl = template_to_image(0.00, 0.00)      # Bottom-left doubles
            br = template_to_image(10.97, 0.00)     # Bottom-right doubles
            tr = template_to_image(10.97, 23.77)    # Top-right doubles
            tl = template_to_image(0.00, 23.77)     # Top-left doubles
            
            pts_doubles = np.array([bl, br, tr, tl], np.int32)
            cv2.polylines(img, [pts_doubles], True, line_color, line_thickness)
        
        # Draw singles boundary using the new keypoint names
        singles_corners = [
            'near_baseline_left_single_corner',   # Bottom-left singles
            'near_baseline_right_single_corner',  # Bottom-right singles
            'far_baseline_right_single_corner',   # Top-right singles
            'far_baseline_left_single_corner',    # Top-left singles
        ]
        
        if all(k in kp_dict for k in singles_corners):
            pts_singles = np.array([
                template_to_image(*kp_dict['near_baseline_left_single_corner']),
                template_to_image(*kp_dict['near_baseline_right_single_corner']),
                template_to_image(*kp_dict['far_baseline_right_single_corner']),
                template_to_image(*kp_dict['far_baseline_left_single_corner']),
            ], np.int32)
            cv2.polylines(img, [pts_singles], True, line_color, line_thickness)
        
        # Draw near service line (bottom service boxes)
        if all(k in kp_dict for k in ['service_box_left_top_corner', 'service_box_right_top_corner']):
            pt1 = template_to_image(*kp_dict['service_box_left_top_corner'])
            pt2 = template_to_image(*kp_dict['service_box_right_top_corner'])
            cv2.line(img, pt1, pt2, line_color, line_thickness)
        
        # Draw far service line (top service boxes)
        if all(k in kp_dict for k in ['far_baseline_left_service_projection', 'far_baseline_right_service_projection']):
            pt1 = template_to_image(*kp_dict['far_baseline_left_service_projection'])
            pt2 = template_to_image(*kp_dict['far_baseline_right_service_projection'])
            cv2.line(img, pt1, pt2, line_color, line_thickness)
        
        # Draw center service line (between center T's)
        if all(k in kp_dict for k in ['center_service_line_bottom_T', 'center_service_line_top_T']):
            pt1 = template_to_image(*kp_dict['center_service_line_bottom_T'])
            pt2 = template_to_image(*kp_dict['center_service_line_top_T'])
            cv2.line(img, pt1, pt2, line_color, line_thickness)
        
        # Draw center T's (horizontal lines at service lines connecting to center line)
        # Near center T (bottom)
        if all(k in kp_dict for k in ['center_service_line_bottom_T', 'service_box_left_top_corner', 'service_box_right_top_corner']):
            center_y = kp_dict['center_service_line_bottom_T'][1]
            left_x = kp_dict['service_box_left_top_corner'][0]
            right_x = kp_dict['service_box_right_top_corner'][0]
            pt1 = template_to_image(left_x, center_y)
            pt2 = template_to_image(right_x, center_y)
            cv2.line(img, pt1, pt2, line_color, line_thickness)
        
        # Far center T (top)
        if all(k in kp_dict for k in ['center_service_line_top_T', 'far_baseline_left_service_projection', 'far_baseline_right_service_projection']):
            center_y = kp_dict['center_service_line_top_T'][1]
            left_x = kp_dict['far_baseline_left_service_projection'][0]
            right_x = kp_dict['far_baseline_right_service_projection'][0]
            pt1 = template_to_image(left_x, center_y)
            pt2 = template_to_image(right_x, center_y)
            cv2.line(img, pt1, pt2, line_color, line_thickness)
        
        # Draw NET LINE at center of court (inspired by Tennis-Tracker)
        # Net is at half court length (11.885m from each baseline)
        # Use the midpoint keypoints to draw the net
        if all(k in kp_dict for k in ['left_singles_sideline_midpoint', 'right_singles_sideline_midpoint']):
            net_y = kp_dict['left_singles_sideline_midpoint'][1]
            net_start = template_to_image(0, net_y)
            net_end = template_to_image(self.COURT_WIDTH_M, net_y)
            cv2.line(img, net_start, net_end, net_color, line_thickness)
        
        # Draw keypoint circles (inspired by Tennis-Tracker mini_court.py)
        # Draw circles at major court corners for visual reference
        for kp in keypoints:
            pt = template_to_image(kp['x'], kp['y'])
            cv2.circle(img, pt, 5, keypoint_color, -1)
        
        return img

    def _draw_transformed_points(self, image, transformed_points, input_points=None, scale=40, offset_x=50, offset_y=50):
        """
        Draw transformed points on the court visualization.
        Inspired by Tennis-Tracker repository for better point visualization.
        
        Args:
            image: numpy array to draw on
            transformed_points: list of [x, y] coordinates in meters
            input_points: optional list of original [x, y] coordinates in pixels (for display)
            scale: pixels per meter (same as court drawing)
            offset_x, offset_y: offset from top-left corner (same as court drawing)
            
        Returns:
            image with points drawn
        """
        if transformed_points is None or len(transformed_points) == 0:
            return image
        
        img = image.copy()
        
        # Color scheme for high visibility
        # White for players/objects (high contrast against green court)
        player_color = (255, 255, 255)  # White
        text_bg_color = (0, 0, 0)  # Black background for text
        
        # Draw each transformed point
        for i, point in enumerate(transformed_points):
            if len(point) >= 2:
                x_meters, y_meters = point[0], point[1]
                px = int(x_meters * scale + offset_x)
                py = int(y_meters * scale + offset_y)
                
                # Draw point as colored circle (similar to Tennis-Tracker style)
                # Using 5px radius for clean, visible markers
                cv2.circle(img, (px, py), 5, player_color, -1)
                
                # Draw player number
                cv2.putText(img, str(i+1), (px + 8, py + 3),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, player_color, 1)
                
                # Display coordinates (court coordinates)
                coord_text = f"({x_meters:.2f}, {y_meters:.2f})m"
                
                # Add original image coordinates if available
                if input_points is not None and i < len(input_points):
                    orig_pt = input_points[i]
                    coord_text = f"Img:({orig_pt[0]:.0f},{orig_pt[1]:.0f}) Court:({x_meters:.2f},{y_meters:.2f})m"
                
                # Calculate text size for background
                (text_width, text_height), baseline = cv2.getTextSize(
                    coord_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1
                )
                
                # Position text near the point (below and to the right)
                text_x = px + 10
                text_y = py + 20
                
                # Ensure text stays within image bounds
                if text_x + text_width > img.shape[1]:
                    text_x = px - text_width - 10
                if text_y + text_height > img.shape[0]:
                    text_y = py - 10
                
                # Draw black background rectangle for text
                cv2.rectangle(img, 
                            (text_x - 2, text_y - text_height - 2),
                            (text_x + text_width + 2, text_y + baseline),
                            text_bg_color, -1)
                
                # Draw coordinate text
                cv2.putText(img, coord_text, (text_x, text_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.35, player_color, 1)
        
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

        # Use dedicated visualization dimensions for tennis court display
        small_window_w = self.VISUALIZATION_WIDTH
        small_window_h = self.VISUALIZATION_HEIGHT
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
            input_points = json_data.get('input_points', None)  # Original image coordinates
            
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
            
            # Draw transformed points if available (with original image coordinates)
            if transformed_points is not None:
                output_image = self._draw_transformed_points(output_image, transformed_points, input_points, scale, offset_x, offset_y)
            
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
