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

        # Create black image for initialization with alpha channel
        black_image = np.zeros((small_window_h, small_window_w, 4), dtype=np.uint8)
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        # Create texture for output image with RGBA support
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output_image_value_name,
                format=dpg.mvFormat_Float_rgba,
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
                    default_value='JSON',
                )

            # Image Output
            with dpg.node_attribute(
                tag=node.tag_node_output_image_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(default_value='Image')
                dpg.add_image(node.tag_node_output_image_value_name)

            # JSON Output
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='JSON',
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
    _ver = '0.0.2'

    node_label = 'TennisCourt'
    node_tag = 'TennisCourt'

    _opencv_setting_dict = None
    
    # Default court dimensions (in meters) - Tennis
    COURT_WIDTH_M = 10.97  # Doubles court width
    COURT_LENGTH_M = 23.77  # Full court length
    
    # Court dimensions per sport (width, length)
    COURT_DIMS = {
        'Tennis':   (10.97, 23.77),
        'Badminton': (6.10, 13.40),
        'Paddle':   (10.00, 20.00),
    }
    
    # Visualization constants
    VISUALIZATION_WIDTH = 300
    VISUALIZATION_HEIGHT = 400
    VISUALIZATION_MARGIN = 30
    
    # NMS threshold for filtering duplicate detections
    NMS_IOU_THRESHOLD = 0.5

    def __init__(self):
        """Initialize the TennisCourt visualization node."""
        # Position tracking for persistent visualization
        self._last_positions_by_label = {}
        self._player_positions_history = {}
        # Active court dimensions (updated each frame based on selected sport template)
        self._active_court_width = self.COURT_WIDTH_M
        self._active_court_length = self.COURT_LENGTH_M

    def _update_player_positions(self, transformed_points, labels):
        """
        Update position history and last positions for each label.
        
        Args:
            transformed_points: list of [x, y] coordinates in meters
            labels: list of label strings for each point
        """
        if transformed_points is None or labels is None:
            # No data to update - this is normal when no detections are present
            return
        
        for i, point in enumerate(transformed_points):
            if i < len(labels):
                label = labels[i]
                x, y = point[0], point[1]
                
                # Update last position for this label
                self._last_positions_by_label[label] = (x, y)
                
                # Add to position history for averaging
                if label not in self._player_positions_history:
                    self._player_positions_history[label] = []
                self._player_positions_history[label].append((x, y))
    
    def _get_average_positions_by_label(self):
        """
        Get average positions for each label based on history.
        
        Returns:
            dict mapping label to average [x, y] coordinates
        """
        averages = {}
        for label, positions in self._player_positions_history.items():
            if positions:
                x_avg = sum(p[0] for p in positions) / len(positions)
                y_avg = sum(p[1] for p in positions) / len(positions)
                averages[label] = [x_avg, y_avg]
        return averages
    
    def _nms(self, bboxes, scores, iou_threshold):
        """
        Apply Non-Maximum Suppression to filter overlapping bounding boxes.
        
        Args:
            bboxes: numpy array of bounding boxes in format [x1, y1, x2, y2]
            scores: numpy array of confidence scores for each bbox
            iou_threshold: IoU threshold for suppression (boxes with IoU > threshold are suppressed)
            
        Returns:
            list of indices to keep
        """
        if len(bboxes) == 0:
            return []
        
        # Convert to numpy arrays if needed
        bboxes = np.array(bboxes, dtype=np.float32)
        scores = np.array(scores, dtype=np.float32)
        
        x1 = bboxes[:, 0]
        y1 = bboxes[:, 1]
        x2 = bboxes[:, 2]
        y2 = bboxes[:, 3]
        
        # Calculate areas of all boxes (using modern continuous coordinates without +1)
        areas = (x2 - x1) * (y2 - y1)
        
        # Sort by scores in descending order
        order = np.argsort(scores)[::-1]
        
        keep = []
        while order.size > 0:
            # Pick the box with highest score
            i = order[0]
            keep.append(i)
            
            # Calculate IoU of this box with all remaining boxes
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            # Calculate intersection (using continuous coordinates)
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            
            # Calculate IoU
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            
            # Keep only boxes with IoU below threshold
            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]
        
        return keep
    
    def _apply_nms_to_tracking(self, transformed_points, bboxes, scores, class_ids, labels):
        """
        Apply NMS to filter duplicate tracking detections based on bounding box overlap.
        This ensures tennis court display is synchronized with MOT display by removing duplicates.
        
        Args:
            transformed_points: list of [x, y] coordinates in meters
            bboxes: list of bounding boxes [x1, y1, x2, y2]
            scores: list of confidence scores
            class_ids: list of class IDs
            labels: list of label strings (can be None)
            
        Returns:
            tuple of (filtered_transformed_points, filtered_labels, filtered_class_ids)
        """
        # If no bboxes or invalid data, return as-is
        if not bboxes or len(bboxes) == 0:
            return transformed_points, labels, class_ids
        
        # Validate array lengths match (including labels if not None)
        expected_length = len(bboxes)
        if len(transformed_points) != expected_length or len(class_ids) != expected_length:
            return transformed_points, labels, class_ids
        
        # Also validate labels length if it's not None
        if labels is not None and len(labels) != expected_length:
            return transformed_points, labels, class_ids
        
        # Use scores if available, otherwise use uniform scores (all equal priority)
        if scores and len(scores) == len(bboxes):
            nms_scores = scores
        else:
            # No scores available - use uniform scores (all boxes have equal priority)
            # In this case, NMS will still work based on IoU but ordering might differ
            nms_scores = [1.0] * len(bboxes)
        
        # Apply NMS to get indices to keep
        keep_indices = self._nms(bboxes, nms_scores, self.NMS_IOU_THRESHOLD)
        
        # Filter all data by kept indices
        filtered_transformed_points = [transformed_points[i] for i in keep_indices]
        filtered_labels = [labels[i] for i in keep_indices] if labels else None
        filtered_class_ids = [class_ids[i] for i in keep_indices] if class_ids else None
        
        return filtered_transformed_points, filtered_labels, filtered_class_ids

    def _draw_tennis_court(self, image, template, scale=40, offset_x=50, offset_y=50):
        """
        Draw tennis court based on template coordinates.
        Inspired by Tennis-Tracker repository (github.com/abhroroy365/Tennis-Tracker)
        
        Args:
            image: numpy array to draw on (supports both BGR and BGRA)
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
        has_alpha = (img.shape[2] == 4) if len(img.shape) == 3 else False
        
        # Convert template coordinates to image coordinates
        # Flip Y axis: template y=0 (near baseline) should be at bottom of image
        # template y=23.77 (far baseline) should be at top of image
        def template_to_image(x, y):
            px = int(x * scale + offset_x)
            # Flip Y: invert the Y coordinate relative to court length
            py = int((self.COURT_LENGTH_M - y) * scale + offset_y)
            return (px, py)
        
        # Color definitions (BGRA format if alpha channel present, otherwise BGR)
        if has_alpha:
            line_color = (255, 255, 255, 255)  # White with full opacity
            court_color = (0, 150, 0, 255)     # Green background with full opacity
            net_color = (255, 0, 0, 255)       # Blue for net with full opacity
            keypoint_color = (0, 0, 255, 255)  # Red for keypoints with full opacity
        else:
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

    def _draw_generic_court_lines(self, img, template, scale, offset_x, offset_y, court_width_m, court_length_m):
        """Draw court lines generically using template keypoints (used for Badminton & Paddle)."""
        if template is None or 'keypoints' not in template:
            return img
        img = img.copy()
        has_alpha = (img.shape[2] == 4) if len(img.shape) == 3 else False

        if has_alpha:
            line_color = (255, 255, 255, 255)
            court_color = (0, 100, 180, 255)   # Blue-ish background (non-tennis sports)
            net_color = (0, 0, 255, 255)
            keypoint_color = (0, 255, 0, 255)
        else:
            line_color = (255, 255, 255)
            court_color = (0, 100, 180)
            net_color = (0, 0, 255)
            keypoint_color = (0, 255, 0)
        line_thickness = 2

        def to_px(x, y):
            return (int(x * scale + offset_x),
                    int((court_length_m - y) * scale + offset_y))

        # Court background
        w_px = int(court_width_m * scale)
        l_px = int(court_length_m * scale)
        cv2.rectangle(img, (offset_x, offset_y), (offset_x + w_px, offset_y + l_px), court_color, -1)

        kp_dict = {kp['name']: (kp['x'], kp['y']) for kp in template['keypoints']}
        sport = template.get('sport', '')

        if sport == 'Badminton':
            # Outer boundary (doubles)
            cv2.rectangle(img, to_px(0, 0), to_px(court_width_m, court_length_m), line_color, line_thickness)
            # Singles sidelines
            for name_l, name_r in [
                ('near_baseline_left_single_corner', 'far_baseline_left_single_corner'),
                ('near_baseline_right_single_corner', 'far_baseline_right_single_corner'),
            ]:
                if name_l in kp_dict and name_r in kp_dict:
                    cv2.line(img, to_px(*kp_dict[name_l]), to_px(*kp_dict[name_r]), line_color, line_thickness)
            # Near short service line
            if 'near_short_service_line_left' in kp_dict and 'near_short_service_line_right' in kp_dict:
                cv2.line(img, to_px(*kp_dict['near_short_service_line_left']),
                         to_px(*kp_dict['near_short_service_line_right']), line_color, line_thickness)
            # Far short service line (symmetric)
            near_y = kp_dict.get('near_short_service_line_left', (None, None))[1]
            if near_y is not None:
                far_y = court_length_m - near_y
                cv2.line(img, to_px(kp_dict['near_short_service_line_left'][0], far_y),
                         to_px(kp_dict['near_short_service_line_right'][0], far_y), line_color, line_thickness)
            # Long service lines (doubles)
            for name in ('far_long_service_line_left', 'far_long_service_line_right'):
                if name in kp_dict:
                    x, y = kp_dict[name]
                    near_lng_y = court_length_m - y  # symmetric near long service line
                    cv2.line(img, to_px(0 if 'left' in name else court_width_m, near_lng_y),
                             to_px(court_width_m if 'right' in name else 0, near_lng_y),
                             line_color, line_thickness)
            if 'far_long_service_line_left' in kp_dict and 'far_long_service_line_right' in kp_dict:
                y_far = kp_dict['far_long_service_line_left'][1]
                cv2.line(img, to_px(kp_dict['far_long_service_line_left'][0], y_far),
                         to_px(kp_dict['far_long_service_line_right'][0], y_far), line_color, line_thickness)
            # Center line (full length)
            center_x = court_width_m / 2
            cv2.line(img, to_px(center_x, 0), to_px(center_x, court_length_m), line_color, line_thickness)
            # Net
            if 'left_net_post' in kp_dict and 'right_net_post' in kp_dict:
                cv2.line(img, to_px(*kp_dict['left_net_post']),
                         to_px(*kp_dict['right_net_post']), net_color, line_thickness)

        elif sport == 'Paddle':
            # Outer boundary
            cv2.rectangle(img, to_px(0, 0), to_px(court_width_m, court_length_m), line_color, line_thickness)
            # Service lines
            for name_l, name_r in [
                ('near_service_line_left', 'near_service_line_right'),
                ('far_service_line_left',  'far_service_line_right'),
            ]:
                if name_l in kp_dict and name_r in kp_dict:
                    cv2.line(img, to_px(*kp_dict[name_l]), to_px(*kp_dict[name_r]), line_color, line_thickness)
            # Center line (between service lines only)
            if 'near_center_T' in kp_dict and 'far_center_T' in kp_dict:
                cv2.line(img, to_px(*kp_dict['near_center_T']),
                         to_px(*kp_dict['far_center_T']), line_color, line_thickness)
            # Net
            if 'left_net_post' in kp_dict and 'right_net_post' in kp_dict:
                cv2.line(img, to_px(*kp_dict['left_net_post']),
                         to_px(*kp_dict['right_net_post']), net_color, line_thickness)

        # Keypoint dots
        for kp in template['keypoints']:
            cv2.circle(img, to_px(kp['x'], kp['y']), 5, keypoint_color, -1)

        return img

    def _draw_sport_court(self, image, template, scale, offset_x, offset_y):
        """Dispatch to the appropriate sport court drawing method."""
        if template is None:
            return image
        sport = template.get('sport', 'Tennis')
        court_w = template.get('court_width', self.COURT_WIDTH_M)
        court_l = template.get('court_length', self.COURT_LENGTH_M)
        if sport == 'Tennis':
            return self._draw_tennis_court(image, template, scale, offset_x, offset_y)
        else:
            return self._draw_generic_court_lines(image, template, scale, offset_x, offset_y, court_w, court_l)

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
                # Flip Y axis to match court flip
                py = int((self._active_court_length - y_meters) * scale + offset_y)
                
                # Draw point as colored circle (similar to Tennis-Tracker style)
                # Using 5px radius for clean, visible markers
                cv2.circle(img, (px, py), 5, player_color, -1)
                
                # Draw player number
                cv2.putText(img, str(i+1), (px + 8, py + 3),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, player_color, 1)
                
                # Display court coordinates only (no image coordinates)
                coord_text = f"({x_meters:.2f}, {y_meters:.2f})m"
                
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

    def _draw_player_positions_with_labels(self, image, transformed_points, labels=None, input_points=None, scale=40, offset_x=50, offset_y=50):
        """
        Draw player positions on the court with labels.
        
        Args:
            image: numpy array to draw on (supports both BGR and BGRA)
            transformed_points: list of [x, y] coordinates in meters
            labels: list of label strings for each point
            input_points: optional list of original [x, y] coordinates in pixels (for display)
            scale: pixels per meter (same as court drawing)
            offset_x, offset_y: offset from top-left corner (same as court drawing)
            
        Returns:
            image with points drawn
        """
        if transformed_points is None or len(transformed_points) == 0:
            return image
        
        img = image.copy()
        has_alpha = (img.shape[2] == 4) if len(img.shape) == 3 else False
        
        # Color scheme: Yellow for players (BGRA if alpha channel, else BGR)
        if has_alpha:
            player_color = (0, 255, 255, 255)  # Yellow in BGRA
        else:
            player_color = (0, 255, 255)  # Yellow in BGR
        
        # Track which labels have been drawn in this frame to avoid duplicates
        drawn_labels = set()
        
        # Draw positions (filtering out balls, invalid labels, and avoiding duplicates)
        for i, point in enumerate(transformed_points):
            if len(point) >= 2:
                # Get label for this point
                label = labels[i] if labels and i < len(labels) else None
                
                # Skip if label is None (object not classified by ReId)
                if label is None:
                    continue
                
                # Skip if this is a ball
                if 'ball' in label.lower():
                    continue
                
                # Skip if we've already drawn this label in this frame
                if label in drawn_labels:
                    continue
                
                drawn_labels.add(label)
                
                x_meters, y_meters = point[0], point[1]
                px = int(x_meters * scale + offset_x)
                # Flip Y axis to match court flip
                py = int((self._active_court_length - y_meters) * scale + offset_y)
                
                # Draw position as larger yellow circle (increased from 5 to 8 pixels)
                cv2.circle(img, (px, py), 8, player_color, -1)
                
                # Draw label in yellow (no coordinate info)
                cv2.putText(img, label, (px + 10, py + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, player_color, 2)
        
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
        
        # Determine what to draw
        template = None
        transformed_points = None
        labels = None
        input_points = None
        scale = None
        offset_x = None
        offset_y = None
        
        if json_data is not None:
            # Extract template and transformed points
            template = json_data.get('template', None)
            transformed_points = json_data.get('transformed_points', None)
            input_points = json_data.get('input_points', None)  # Original image coordinates
            
            # Initialize labels as None by default
            labels = None
            
            # Extract labels from bboxes and class_ids (from object detection)
            if 'bboxes' in json_data and 'class_ids' in json_data and 'class_names' in json_data:
                class_ids = json_data.get('class_ids', [])
                class_names = json_data.get('class_names', {})
                bboxes = json_data.get('bboxes', [])
                scores = json_data.get('scores', [])
                
                # Create labels for each detected object
                labels = []
                for class_id in class_ids:
                    if isinstance(class_names, dict):
                        label = class_names.get(class_id, None)
                    elif isinstance(class_names, list) and class_id < len(class_names):
                        label = class_names[class_id]
                    else:
                        label = None
                    labels.append(label)
                
                # Apply NMS to filter duplicate detections
                # This synchronizes the tennis court display with MOT display
                if transformed_points is not None and bboxes and len(bboxes) > 0:
                    transformed_points, labels, class_ids = self._apply_nms_to_tracking(
                        transformed_points, bboxes, scores, class_ids, labels
                    )
            
            # Update position history if we have new data
            if transformed_points is not None and labels is not None:
                self._update_player_positions(transformed_points, labels)
            elif transformed_points is None:
                # If we received JSON data but no transformed_points, it means
                # MOT is stopped or no detections - clear the display
                self._last_positions_by_label = {}
                self._player_positions_history = {}
            
            # Store template for future use
            if template is not None:
                self._last_template = template
        else:
            # No new data received - use last known template
            template = getattr(self, '_last_template', None)
        
        # Always draw (even if no new data) to maintain persistent visualization
        if template is not None:
            # Update active court dimensions based on selected sport
            sport = template.get('sport', 'Tennis')
            court_w, court_l = self.COURT_DIMS.get(sport, (self.COURT_WIDTH_M, self.COURT_LENGTH_M))
            # Also check template-embedded dimensions (in case of custom templates)
            court_w = template.get('court_width', court_w)
            court_l = template.get('court_length', court_l)
            self._active_court_width = court_w
            self._active_court_length = court_l

            # Create blank image with alpha channel (BGRA) for transparency
            output_image = np.zeros((small_window_h, small_window_w, 4), dtype=np.uint8)
            
            # Calculate scale to fit court in image
            scale_x = (small_window_w - self.VISUALIZATION_MARGIN) / court_w
            scale_y = (small_window_h - self.VISUALIZATION_MARGIN) / court_l
            base_scale = min(scale_x, scale_y)
            
            # Reduce court size to leave comfortable margins
            scale = base_scale / 1.5
            
            # Center the court
            court_width_px = int(court_w * scale)
            court_length_px = int(court_l * scale)
            offset_x = (small_window_w - court_width_px) // 2
            offset_y = (small_window_h - court_length_px) // 2
            
            # Draw the court using the sport-appropriate method
            output_image = self._draw_sport_court(output_image, template, scale, offset_x, offset_y)
            
            # Draw last known positions (persistent display)
            if self._last_positions_by_label:
                last_labels = list(self._last_positions_by_label.keys())
                last_points = [list(self._last_positions_by_label[label]) for label in last_labels]
                output_image = self._draw_player_positions_with_labels(
                    output_image, last_points, last_labels, None, scale, offset_x, offset_y
                )
            
            # Prepare output JSON (pass through with visualization metadata)
            if json_data is not None:
                output_json = copy.deepcopy(json_data)
            else:
                output_json = {}
            
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
                # Display full image with margins (no cropping)
                # This shows the court with 1/6 extra space on top and bottom
                texture = self.convert_cv_to_dpg(
                    output_image,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(output_image_value_tag, texture)
            except Exception:
                pass  # DPG not initialized (e.g., in tests)

        return {"image": output_image, "json": output_json, "audio": None}
    
    def convert_cv_to_dpg(self, image, width, height):
        """
        Convert OpenCV image to DPG texture format, supporting both BGR and BGRA.
        Overrides parent class to add BGRA support for transparency.
        
        Args:
            image: numpy array in BGR or BGRA format
            width: target width
            height: target height
            
        Returns:
            texture data as float array
        """
        # Ensure image is uint8 for cv2.cvtColor compatibility
        if image.dtype != np.uint8:
            # Convert float images (0-1 range) to uint8 (0-255 range)
            if image.dtype in [np.float32, np.float64]:
                # Clip values to valid range and scale to 0-255
                image = np.clip(image, 0.0, 1.0)
                image = (image * 255).astype(np.uint8)
            else:
                # For other dtypes, clip to valid uint8 range
                image = np.clip(image, 0, 255).astype(np.uint8)
        
        resize_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        
        # Check if image has alpha channel
        if len(resize_image.shape) == 3 and resize_image.shape[2] == 4:
            # BGRA -> RGBA conversion for DPG
            data = cv2.cvtColor(resize_image, cv2.COLOR_BGRA2RGBA)
        else:
            # BGR -> RGB conversion for DPG
            data = np.flip(resize_image, 2)
        
        data = data.ravel()
        data = np.asarray(data, dtype=np.float32)
        texture_data = np.true_divide(data, 255.0)
        
        return texture_data

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
