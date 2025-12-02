#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import copy
import math

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node

# Import MediaPipe Hands for hand pose estimation
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


class FactoryNode:
    node_label = 'DynamicPlay'
    node_tag = 'DynamicPlay'
    

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
        node._value_history = {}

        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input00_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input00'
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'

        # Settings
        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']

        # Create black texture (height, width, channels)
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

        # Initialize slot counter
        if node.tag_node_name not in node._slot_id:
            node._slot_id[node.tag_node_name] = 1

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Output (displayed frame)
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Add slot button
            with dpg.node_attribute(
                    tag=node.tag_node_input00_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='Add Slot',
                    width=int(small_window_w / 3),
                    callback=node._add_slot,
                    user_data=node.tag_node_name,
                )
            
            # First input slot
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input BGR image',
                )

        return node



class Node(Node):
    _ver = '0.0.1'

    node_label = 'DynamicPlay'
    node_tag = 'DynamicPlay'

    _opencv_setting_dict = None

    _max_slot_number = 9
    _slot_id = {}
    
    # Hand detection state
    _selected_stream_index = {}  # Per-node selected stream
    _zoom_scale = {}  # Per-node zoom scale
    _zoom_center = {}  # Per-node zoom center (x, y)
    
    # Hand pose estimation model
    _hand_model = None
    
    # Zoom constants
    _MIN_ZOOM = 1.0
    _MAX_ZOOM = 3.0
    _BASE_PINCH_DISTANCE = 100  # Base pinch distance in pixels for 1x zoom

    def __init__(self):
        pass

    def _init_hand_model(self):
        """Initialize MediaPipe Hands model if not already initialized"""
        if self._hand_model is None and MEDIAPIPE_AVAILABLE:
            mp_hands = mp.solutions.hands
            self._hand_model = mp_hands.Hands(
                model_complexity=0,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5,
            )

    def _detect_hands(self, frame):
        """Detect hand landmarks in the frame"""
        if not MEDIAPIPE_AVAILABLE or self._hand_model is None:
            return None
        
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the image
        results = self._hand_model.process(image_rgb)
        
        if results.multi_hand_landmarks:
            return results.multi_hand_landmarks[0]  # Return first hand
        
        return None

    def _get_hand_keypoints(self, hand_landmarks, image_width, image_height):
        """Extract hand keypoints from landmarks"""
        if hand_landmarks is None:
            return None
        
        keypoints = {}
        for id, landmark in enumerate(hand_landmarks.landmark):
            x = min(int(landmark.x * image_width), image_width - 1)
            y = min(int(landmark.y * image_height), image_height - 1)
            keypoints[id] = (x, y)
        
        return keypoints

    def _calculate_pinch_distance(self, keypoints):
        """Calculate distance between thumb tip (4) and index finger tip (8)"""
        if keypoints is None or 4 not in keypoints or 8 not in keypoints:
            return None
        
        thumb_tip = keypoints[4]
        index_tip = keypoints[8]
        
        distance = math.sqrt(
            (thumb_tip[0] - index_tip[0])**2 + 
            (thumb_tip[1] - index_tip[1])**2
        )
        
        return distance

    def _is_pointing(self, keypoints):
        """Check if hand is in pointing gesture (index finger extended)"""
        if keypoints is None:
            return False, None
        
        # Index finger tip (8) and MCP (5)
        if 8 not in keypoints or 5 not in keypoints:
            return False, None
        
        index_tip = keypoints[8]
        index_mcp = keypoints[5]
        
        # Check if index finger is extended (tip is above MCP)
        is_extended = index_tip[1] < index_mcp[1]
        
        return is_extended, index_tip

    def _create_grid_buttons(self, frame, num_slots):
        """Create visual button grid based on number of slots"""
        height, width = frame.shape[:2]
        
        # Calculate grid layout
        if num_slots <= 2:
            cols, rows = min(num_slots, 2), 1
        elif num_slots <= 4:
            cols, rows = 2, 2
        elif num_slots <= 6:
            cols, rows = 3, 2
        else:
            cols, rows = 3, 3
        
        button_width = width // cols
        button_height = height // rows
        
        buttons = []
        for i in range(num_slots):
            row = i // cols
            col = i % cols
            
            x1 = col * button_width
            y1 = row * button_height
            x2 = x1 + button_width
            y2 = y1 + button_height
            
            buttons.append({
                'index': i,
                'bounds': (x1, y1, x2, y2),
                'center': (x1 + button_width // 2, y1 + button_height // 2)
            })
        
        return buttons

    def _draw_buttons_and_check_click(self, frame, buttons, hand_keypoints, selected_index):
        """Draw button grid and check for hand clicks"""
        clicked_index = None
        is_pointing, point_pos = self._is_pointing(hand_keypoints)
        
        for button in buttons:
            x1, y1, x2, y2 = button['bounds']
            index = button['index']
            
            # Determine button color
            if index == selected_index:
                color = (0, 255, 0)  # Green for selected
                thickness = 3
            else:
                color = (255, 255, 255)  # White for unselected
                thickness = 2
            
            # Draw button rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw button label
            label = f"{index + 1}"
            font_scale = 1.5
            text_thickness = 2
            (text_width, text_height), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_thickness
            )
            text_x = x1 + (x2 - x1 - text_width) // 2
            text_y = y1 + (y2 - y1 + text_height) // 2
            cv2.putText(frame, label, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, text_thickness)
            
            # Check if pointing at this button
            if is_pointing and point_pos:
                px, py = point_pos
                if x1 <= px <= x2 and y1 <= py <= y2:
                    # Highlight button being pointed at
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), thickness + 2)
                    clicked_index = index
        
        # Draw hand landmarks
        if hand_keypoints:
            for id, (x, y) in hand_keypoints.items():
                # Draw keypoint
                if id in [4, 8]:  # Thumb and index finger tips
                    cv2.circle(frame, (x, y), 8, (0, 255, 255), -1)
                else:
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
        
        return frame, clicked_index

    def _apply_zoom(self, frame, zoom_scale, center):
        """Apply zoom to frame based on pinch gesture"""
        if zoom_scale <= 1.0:
            return frame
        
        height, width = frame.shape[:2]
        cx, cy = center
        
        # Calculate crop region
        crop_width = int(width / zoom_scale)
        crop_height = int(height / zoom_scale)
        
        # Ensure center is within bounds
        cx = max(crop_width // 2, min(cx, width - crop_width // 2))
        cy = max(crop_height // 2, min(cy, height - crop_height // 2))
        
        # Crop
        x1 = cx - crop_width // 2
        y1 = cy - crop_height // 2
        x2 = x1 + crop_width
        y2 = y1 + crop_height
        
        cropped = frame[y1:y2, x1:x2]
        
        # Resize back to original size
        zoomed = cv2.resize(cropped, (width, height))
        
        return zoomed

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        self.output_value01_tag = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']

        # Initialize hand model
        self._init_hand_model()

        # Initialize state for this node if needed
        if self.tag_node_name not in self._selected_stream_index:
            self._selected_stream_index[self.tag_node_name] = 0
        if self.tag_node_name not in self._zoom_scale:
            self._zoom_scale[self.tag_node_name] = 1.0
        if self.tag_node_name not in self._zoom_center:
            self._zoom_center[self.tag_node_name] = (small_window_w // 2, small_window_h // 2)

        # Parse connections to get input streams
        connection_info_src_dict = {}
        for connection_info in connection_list:
            slot_number = re.sub(r'\D', '', connection_info[1].split(':')[-1])
            if slot_number == '':
                continue
            slot_number = int(slot_number) - 1

            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_IMAGE:
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)
                connection_info_src_dict[slot_number] = connection_info_src

        slot_num = self._slot_id[self.tag_node_name]

        # Get all input frames
        frames = {}
        for slot_index in range(slot_num):
            node_id_name = connection_info_src_dict.get(slot_index, None)
            if node_id_name:
                frame = node_image_dict.get(node_id_name, None)
                if frame is not None:
                    frames[slot_index] = copy.deepcopy(frame)

        # Process frames
        output_frame = None
        if len(frames) > 0:
            # Get selected stream
            selected_index = self._selected_stream_index[self.tag_node_name]
            
            # Ensure selected index is valid
            if selected_index >= len(frames):
                selected_index = 0
                self._selected_stream_index[self.tag_node_name] = 0
            
            # Get the currently selected frame
            selected_frame = frames.get(selected_index, None)
            
            if selected_frame is None and len(frames) > 0:
                # If selected frame is not available, use the first available frame
                selected_index = min(frames.keys())
                selected_frame = frames[selected_index]
                self._selected_stream_index[self.tag_node_name] = selected_index
            
            if selected_frame is not None:
                # Detect hand in selected frame
                hand_landmarks = self._detect_hands(selected_frame)
                height, width = selected_frame.shape[:2]
                hand_keypoints = self._get_hand_keypoints(hand_landmarks, width, height)
                
                # Create button grid
                buttons = self._create_grid_buttons(selected_frame, len(frames))
                
                # Draw buttons and check for clicks
                display_frame = copy.deepcopy(selected_frame)
                display_frame, clicked_index = self._draw_buttons_and_check_click(
                    display_frame, buttons, hand_keypoints, selected_index
                )
                
                # Handle button click (stream selection)
                if clicked_index is not None and clicked_index in frames:
                    self._selected_stream_index[self.tag_node_name] = clicked_index
                    # Reset zoom when switching streams
                    self._zoom_scale[self.tag_node_name] = 1.0
                
                # Handle pinch-to-zoom
                if hand_keypoints:
                    pinch_distance = self._calculate_pinch_distance(hand_keypoints)
                    if pinch_distance is not None:
                        # Map pinch distance to zoom scale
                        # Pinch distance maps proportionally to zoom level
                        zoom = max(self._MIN_ZOOM, min(self._MAX_ZOOM, 
                                                       pinch_distance / self._BASE_PINCH_DISTANCE))
                        self._zoom_scale[self.tag_node_name] = zoom
                        
                        # Update zoom center to index finger position
                        if 8 in hand_keypoints:
                            self._zoom_center[self.tag_node_name] = hand_keypoints[8]
                
                # Apply zoom
                zoom_scale = self._zoom_scale[self.tag_node_name]
                zoom_center = self._zoom_center[self.tag_node_name]
                display_frame = self._apply_zoom(display_frame, zoom_scale, zoom_center)
                
                # Add zoom indicator
                zoom_text = f"Zoom: {zoom_scale:.1f}x"
                cv2.putText(display_frame, zoom_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)
                
                # Add selected stream indicator
                stream_text = f"Stream: {selected_index + 1}/{len(frames)}"
                cv2.putText(display_frame, stream_text, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)
                
                output_frame = display_frame

        # Update texture
        if output_frame is not None:
            texture = self.convert_cv_to_dpg(
                output_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(self.output_value01_tag, texture)

        return {"image": output_frame, "json": None, "audio": None}

    def close(self, node_id):
        """Clean up resources"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Clean up state
        if tag_node_name in self._selected_stream_index:
            del self._selected_stream_index[tag_node_name]
        if tag_node_name in self._zoom_scale:
            del self._zoom_scale[tag_node_name]
        if tag_node_name in self._zoom_center:
            del self._zoom_center[tag_node_name]

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict['slot_id'] = self._slot_id[self.tag_node_name]

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag

        slot_number = int(setting_dict['slot_id'])
        for _ in range(slot_number - 1):
            self._add_slot(None, None, self.tag_node_name)

    def _add_slot(self, sender, data, user_data):
        """Add a new input slot for image streams"""
        tag_node_name = user_data

        if self._max_slot_number > self._slot_id[tag_node_name]:
            self._slot_id[tag_node_name] += 1

            before_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Input'
            before_tag += str(self._slot_id[tag_node_name] - 1).zfill(2)

            tag_node_inputXX_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Input'
            tag_node_inputXX_name += str(self._slot_id[tag_node_name]).zfill(2)

            tag_node_inputXX_value_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Input'
            tag_node_inputXX_value_name += str(
                self._slot_id[self.tag_node_name]).zfill(2) + 'Value'

            with dpg.node_attribute(
                    tag=tag_node_inputXX_name,
                    attribute_type=dpg.mvNode_Attr_Input,
                    parent=self.tag_node_name,
                    before=before_tag,
            ):
                dpg.add_text(
                    tag=tag_node_inputXX_value_name,
                    default_value='Input BGR image',
                )
