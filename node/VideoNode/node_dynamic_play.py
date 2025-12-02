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
    _ver = '0.1.0'

    node_label = 'DynamicPlay'
    node_tag = 'DynamicPlay'

    _opencv_setting_dict = None

    _max_slot_number = 9
    _slot_id = {}
    
    # Hand detection state - MODIFIED for master stream + overlay architecture
    _active_overlay_index = {}  # Per-node active overlay stream (None = no overlay)
    _overlay_position = {}  # Per-node overlay position (x, y)
    _overlay_size = {}  # Per-node overlay size (width, height)
    _is_dragging = {}  # Per-node dragging state
    _drag_offset = {}  # Per-node drag offset from pinch point to overlay corner
    
    # Hand pose estimation model
    _hand_model = None
    
    # Overlay constants
    _MIN_OVERLAY_SIZE = 100  # Minimum overlay size in pixels
    _MAX_OVERLAY_SIZE = 800  # Maximum overlay size in pixels
    _BASE_PINCH_DISTANCE = 100  # Base pinch distance in pixels for reference
    _DEFAULT_OVERLAY_WIDTH = 320  # Default overlay width
    _DEFAULT_OVERLAY_HEIGHT = 240  # Default overlay height

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

    def _is_pinching(self, keypoints):
        """Check if hand is in pinch gesture (thumb and index close together)"""
        if keypoints is None:
            return False, None
        
        pinch_distance = self._calculate_pinch_distance(keypoints)
        if pinch_distance is None:
            return False, None
        
        # Consider it a pinch if thumb and index are close together (< 40 pixels)
        is_pinch = pinch_distance < 40
        
        # Return midpoint between thumb and index as pinch position
        if is_pinch and 4 in keypoints and 8 in keypoints:
            thumb_tip = keypoints[4]
            index_tip = keypoints[8]
            pinch_pos = (
                (thumb_tip[0] + index_tip[0]) // 2,
                (thumb_tip[1] + index_tip[1]) // 2
            )
            return True, pinch_pos
        
        return False, None

    def _draw_overlay(self, master_frame, overlay_frame, position, size):
        """Draw overlay frame on master frame at specified position and size"""
        if overlay_frame is None:
            return master_frame
        
        x, y = position
        width, height = size
        
        # Ensure overlay size is within bounds
        width = max(self._MIN_OVERLAY_SIZE, min(width, self._MAX_OVERLAY_SIZE))
        height = max(self._MIN_OVERLAY_SIZE, min(height, self._MAX_OVERLAY_SIZE))
        
        # Resize overlay to target size
        resized_overlay = cv2.resize(overlay_frame, (width, height))
        
        # Get master frame dimensions
        master_h, master_w = master_frame.shape[:2]
        
        # Ensure position keeps overlay within bounds
        x = max(0, min(x, master_w - width))
        y = max(0, min(y, master_h - height))
        
        # Create a copy of master frame
        result = master_frame.copy()
        
        # Draw border around overlay
        border_thickness = 3
        cv2.rectangle(result, (x-border_thickness, y-border_thickness), 
                     (x+width+border_thickness, y+height+border_thickness), 
                     (0, 255, 255), border_thickness)
        
        # Overlay the frame
        result[y:y+height, x:x+width] = resized_overlay
        
        return result

    def _create_grid_buttons(self, frame, num_slots):
        """Create visual button grid based on number of slots"""
        height, width = frame.shape[:2]
        
        # Calculate grid layout
        if num_slots <= 1:
            cols, rows = 1, 1
        elif num_slots <= 2:
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

    def _draw_buttons_and_check_click(self, frame, buttons, hand_keypoints, active_overlay_index):
        """Draw button grid and check for hand clicks to activate overlays"""
        clicked_index = None
        is_pointing, point_pos = self._is_pointing(hand_keypoints)
        
        for button in buttons:
            x1, y1, x2, y2 = button['bounds']
            index = button['index']
            
            # Determine button color
            if index == active_overlay_index:
                color = (0, 255, 0)  # Green for active overlay
                thickness = 3
            else:
                color = (255, 255, 255)  # White for inactive
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
        if self.tag_node_name not in self._active_overlay_index:
            self._active_overlay_index[self.tag_node_name] = None
        if self.tag_node_name not in self._overlay_position:
            self._overlay_position[self.tag_node_name] = (50, 50)
        if self.tag_node_name not in self._overlay_size:
            self._overlay_size[self.tag_node_name] = (self._DEFAULT_OVERLAY_WIDTH, self._DEFAULT_OVERLAY_HEIGHT)
        if self.tag_node_name not in self._is_dragging:
            self._is_dragging[self.tag_node_name] = False
        if self.tag_node_name not in self._drag_offset:
            self._drag_offset[self.tag_node_name] = (0, 0)

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
        # Slot 0 is the MASTER stream (background with hand detection)
        # Slots 1+ are OVERLAY streams (can be activated as picture-in-picture)
        frames = {}
        for slot_index in range(slot_num):
            node_id_name = connection_info_src_dict.get(slot_index, None)
            if node_id_name:
                frame = node_image_dict.get(node_id_name, None)
                if frame is not None:
                    frames[slot_index] = copy.deepcopy(frame)

        # Process frames with new master + overlay architecture
        output_frame = None
        if len(frames) > 0:
            # Get master stream (slot 0)
            master_frame = frames.get(0, None)
            
            if master_frame is None and len(frames) > 0:
                # If no master stream, use first available frame as master
                master_frame = frames[min(frames.keys())]
            
            if master_frame is not None:
                # Detect hand in master frame
                hand_landmarks = self._detect_hands(master_frame)
                height, width = master_frame.shape[:2]
                hand_keypoints = self._get_hand_keypoints(hand_landmarks, width, height)
                
                # Create button grid (for slots 1+, overlay streams)
                num_overlay_slots = max(0, slot_num - 1)  # Exclude master stream
                buttons = []
                if num_overlay_slots > 0:
                    buttons = self._create_grid_buttons(master_frame, num_overlay_slots)
                
                # Draw buttons on master frame
                display_frame = copy.deepcopy(master_frame)
                
                # Check for button clicks to activate overlays
                active_overlay = self._active_overlay_index[self.tag_node_name]
                if num_overlay_slots > 0:
                    display_frame, clicked_index = self._draw_buttons_and_check_click(
                        display_frame, buttons, hand_keypoints, active_overlay
                    )
                    
                    # Handle button click (overlay activation)
                    if clicked_index is not None:
                        # Map button index to slot index (add 1 to skip master slot)
                        overlay_slot = clicked_index + 1
                        if overlay_slot in frames:
                            # Toggle overlay: if already active, deactivate it
                            if active_overlay == clicked_index:
                                self._active_overlay_index[self.tag_node_name] = None
                            else:
                                self._active_overlay_index[self.tag_node_name] = clicked_index
                                # Reset overlay to default position and size
                                self._overlay_position[self.tag_node_name] = (50, 50)
                                self._overlay_size[self.tag_node_name] = (
                                    self._DEFAULT_OVERLAY_WIDTH, 
                                    self._DEFAULT_OVERLAY_HEIGHT
                                )
                
                # Handle pinch gestures for dragging and resizing overlay
                active_overlay = self._active_overlay_index[self.tag_node_name]
                if active_overlay is not None and hand_keypoints:
                    is_pinch, pinch_pos = self._is_pinching(hand_keypoints)
                    
                    if is_pinch and pinch_pos:
                        # Get pinch distance for resizing
                        pinch_distance = self._calculate_pinch_distance(hand_keypoints)
                        
                        if not self._is_dragging[self.tag_node_name]:
                            # Start dragging
                            self._is_dragging[self.tag_node_name] = True
                            # Calculate offset from pinch point to overlay position
                            overlay_pos = self._overlay_position[self.tag_node_name]
                            self._drag_offset[self.tag_node_name] = (
                                overlay_pos[0] - pinch_pos[0],
                                overlay_pos[1] - pinch_pos[1]
                            )
                        
                        # Update overlay position (drag)
                        offset_x, offset_y = self._drag_offset[self.tag_node_name]
                        new_x = pinch_pos[0] + offset_x
                        new_y = pinch_pos[1] + offset_y
                        self._overlay_position[self.tag_node_name] = (new_x, new_y)
                        
                        # Update overlay size based on pinch distance (resize)
                        if pinch_distance is not None:
                            # Map pinch distance to overlay size
                            # Small pinch (50px) -> MIN_SIZE, Large pinch (200px) -> MAX_SIZE
                            size_ratio = (pinch_distance - 50) / (200 - 50)
                            size_ratio = max(0, min(1, size_ratio))  # Clamp to [0, 1]
                            
                            new_width = int(self._MIN_OVERLAY_SIZE + 
                                          size_ratio * (self._MAX_OVERLAY_SIZE - self._MIN_OVERLAY_SIZE))
                            # Maintain aspect ratio based on original overlay
                            overlay_slot = active_overlay + 1
                            if overlay_slot in frames:
                                overlay_frame = frames[overlay_slot]
                                oh, ow = overlay_frame.shape[:2]
                                aspect_ratio = ow / oh
                                new_height = int(new_width / aspect_ratio)
                                self._overlay_size[self.tag_node_name] = (new_width, new_height)
                    else:
                        # Stop dragging when pinch is released
                        self._is_dragging[self.tag_node_name] = False
                
                # Draw active overlay on master frame
                active_overlay = self._active_overlay_index[self.tag_node_name]
                if active_overlay is not None:
                    overlay_slot = active_overlay + 1
                    if overlay_slot in frames:
                        overlay_frame = frames[overlay_slot]
                        overlay_pos = self._overlay_position[self.tag_node_name]
                        overlay_size = self._overlay_size[self.tag_node_name]
                        display_frame = self._draw_overlay(
                            display_frame, overlay_frame, overlay_pos, overlay_size
                        )
                        
                        # Add overlay info text
                        info_text = f"Overlay: {active_overlay + 1} | Size: {overlay_size[0]}x{overlay_size[1]}"
                        cv2.putText(display_frame, info_text, (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                else:
                    # No overlay active
                    if num_overlay_slots > 0:
                        info_text = "Point at button to activate overlay"
                        cv2.putText(display_frame, info_text, (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
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
        if tag_node_name in self._active_overlay_index:
            del self._active_overlay_index[tag_node_name]
        if tag_node_name in self._overlay_position:
            del self._overlay_position[tag_node_name]
        if tag_node_name in self._overlay_size:
            del self._overlay_size[tag_node_name]
        if tag_node_name in self._is_dragging:
            del self._is_dragging[tag_node_name]
        if tag_node_name in self._drag_offset:
            del self._drag_offset[tag_node_name]

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
