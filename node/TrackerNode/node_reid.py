#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import time

import numpy as np
import dearpygui.dearpygui as dpg
from sklearn.cluster import KMeans

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FactoryNode:
    node_label = 'ReId'
    node_tag = 'ReId'
    
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
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        node.tag_node_output03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

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

        # Create yellow theme for JSON button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # Initialize slot tracking for this node
        if node.tag_node_name not in node._slot_id:
            node._slot_id[node.tag_node_name] = 1
            node._slot_names[node.tag_node_name] = {1: "player1"}

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input Image',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Input JSON (ObjectDetection)',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Slot management section
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':SlotManagement',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='Add Slot',
                    width=int(small_window_w / 2),
                    callback=node._add_slot,
                    user_data=node.tag_node_name,
                )
                dpg.add_button(
                    label='Remove Slot',
                    width=int(small_window_w / 2),
                    callback=node._remove_slot,
                    user_data=node.tag_node_name,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

            # JSON output button
            with dpg.node_attribute(
                    tag=node.tag_node_output03_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="JSON",
                    tag=node.tag_node_output03_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'ReId'
    node_tag = 'ReId'

    _opencv_setting_dict = None

    # Slot management
    _max_slot_number = 20
    _slot_id = {}
    _slot_names = {}
    
    # ReId data structures
    _frame_counter = {}  # Track frames per node
    _feature_buffer = {}  # Store features from first 100 frames
    _centroids = {}  # Store computed centroids
    _kmeans_trained = {}  # Track if K-means is trained for each node
    
    def __init__(self):
        pass

    def _add_slot(self, sender, data, user_data):
        """Add a new slot with a default name (playerN)"""
        tag_node_name = user_data

        if self._max_slot_number > self._slot_id[tag_node_name]:
            self._slot_id[tag_node_name] += 1
            slot_number = self._slot_id[tag_node_name]
            
            # Generate default name
            default_name = f"player{slot_number}"
            self._slot_names[tag_node_name][slot_number] = default_name

            # Find position to insert (before the SlotManagement section)
            before_tag = tag_node_name + ':SlotManagement'

            # Create tag for the slot
            tag_node_slotXX_name = tag_node_name + ':Slot' + str(slot_number).zfill(2)
            tag_node_slotXX_value_name = tag_node_slotXX_name + 'Value'

            with dpg.node_attribute(
                    tag=tag_node_slotXX_name,
                    attribute_type=dpg.mvNode_Attr_Static,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_input_text(
                    tag=tag_node_slotXX_value_name,
                    default_value=default_name,
                    label=f"Slot {slot_number}",
                    callback=self._on_slot_name_change,
                    user_data=(tag_node_name, slot_number),
                    width=150,
                )

    def _remove_slot(self, sender, data, user_data):
        """Remove the last slot"""
        tag_node_name = user_data

        if self._slot_id[tag_node_name] > 1:
            slot_number = self._slot_id[tag_node_name]
            
            # Remove from slot names dictionary
            if slot_number in self._slot_names[tag_node_name]:
                del self._slot_names[tag_node_name][slot_number]
            
            # Remove the UI element
            tag_node_slotXX_name = tag_node_name + ':Slot' + str(slot_number).zfill(2)
            if dpg.does_item_exist(tag_node_slotXX_name):
                dpg.delete_item(tag_node_slotXX_name)
            
            self._slot_id[tag_node_name] -= 1

    def _on_slot_name_change(self, sender, app_data, user_data):
        """Callback when user changes a slot name"""
        tag_node_name, slot_number = user_data
        new_name = app_data
        self._slot_names[tag_node_name][slot_number] = new_name
        logger.info(f"Slot {slot_number} renamed to: {new_name}")

    def _extract_features(self, frame, bbox):
        """Extract simple color histogram features from a bounding box"""
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        
        # Ensure bbox is within frame boundaries
        h, w = frame.shape[:2]
        x1 = max(0, min(x1, w-1))
        x2 = max(0, min(x2, w))
        y1 = max(0, min(y1, h-1))
        y2 = max(0, min(y2, h))
        
        if x2 <= x1 or y2 <= y1:
            # Invalid bbox, return zero feature
            return np.zeros(48)
        
        # Extract ROI
        roi = frame[y1:y2, x1:x2]
        
        if roi.size == 0:
            return np.zeros(48)
        
        # Compute color histogram (16 bins per channel)
        hist_b = np.histogram(roi[:, :, 0], bins=16, range=(0, 256))[0]
        hist_g = np.histogram(roi[:, :, 1], bins=16, range=(0, 256))[0]
        hist_r = np.histogram(roi[:, :, 2], bins=16, range=(0, 256))[0]
        
        # Normalize and concatenate
        hist_b = hist_b / (hist_b.sum() + 1e-6)
        hist_g = hist_g / (hist_g.sum() + 1e-6)
        hist_r = hist_r / (hist_r.sum() + 1e-6)
        
        feature = np.concatenate([hist_b, hist_g, hist_r])
        return feature

    def _train_kmeans(self, node_id):
        """Train K-means clustering on collected features"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        if tag_node_name not in self._feature_buffer:
            return False
        
        features = self._feature_buffer[tag_node_name]
        if len(features) < 10:  # Need at least 10 samples
            return False
        
        # Number of clusters = number of slots
        n_clusters = self._slot_id.get(tag_node_name, 1)
        n_clusters = min(n_clusters, len(features))  # Can't have more clusters than samples
        
        if n_clusters < 1:
            return False
        
        # Train K-means
        try:
            features_array = np.array(features)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
            kmeans.fit(features_array)
            
            # Store centroids
            self._centroids[tag_node_name] = kmeans.cluster_centers_
            self._kmeans_trained[tag_node_name] = True
            
            logger.info(f"K-means trained for node {node_id} with {n_clusters} clusters from {len(features)} samples")
            return True
        except Exception as e:
            logger.error(f"Error training K-means: {e}")
            return False

    def _assign_to_centroid(self, feature, tag_node_name):
        """Assign a feature to the nearest centroid"""
        if tag_node_name not in self._centroids:
            return None
        
        centroids = self._centroids[tag_node_name]
        
        # Calculate distances to all centroids
        distances = np.linalg.norm(centroids - feature, axis=1)
        
        # Return the index of the nearest centroid
        nearest_idx = np.argmin(distances)
        return nearest_idx + 1  # 1-indexed for player numbers

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get connections
        src_image_node = ''
        src_json_node = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_IMAGE:
                connection_info_src = connection_info[0].split(':')[:2]
                src_image_node = ':'.join(connection_info_src)
            elif connection_type == self.TYPE_JSON:
                connection_info_src = connection_info[0].split(':')[:2]
                src_json_node = ':'.join(connection_info_src)

        # Get frame and JSON data
        frame = node_image_dict.get(src_image_node, None)
        json_data = node_result_dict.get(src_json_node, {})

        # Initialize frame counter
        if tag_node_name not in self._frame_counter:
            self._frame_counter[tag_node_name] = 0
            self._feature_buffer[tag_node_name] = []
            self._kmeans_trained[tag_node_name] = False

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        result = {}
        output_frame = None

        if frame is not None and json_data:
            self._frame_counter[tag_node_name] += 1
            frame_count = self._frame_counter[tag_node_name]

            # Extract object detection data (from ObjectDetection node)
            bboxes = json_data.get('bboxes', [])
            scores = json_data.get('scores', [])
            class_ids = json_data.get('class_ids', [])
            class_names = json_data.get('class_names', [])

            # Phase 1: Collect features for first 100 frames
            if frame_count <= 100:
                for bbox in bboxes:
                    feature = self._extract_features(frame, bbox)
                    self._feature_buffer[tag_node_name].append(feature)
                
                # Train K-means after 100 frames
                if frame_count == 100:
                    self._train_kmeans(node_id)
                
                # During training, pass through original data
                result = json_data.copy()
                output_frame = copy.deepcopy(frame)
            
            # Phase 2: Assign ReId labels using trained K-means
            elif self._kmeans_trained.get(tag_node_name, False):
                reid_class_ids = []  # Replace class_ids with ReId labels
                reid_class_names = []  # Replace class_names with slot names
                
                for bbox in bboxes:
                    feature = self._extract_features(frame, bbox)
                    slot_idx = self._assign_to_centroid(feature, tag_node_name)
                    
                    if slot_idx is not None:
                        # Get the custom name for this slot
                        slot_name = self._slot_names[tag_node_name].get(slot_idx, f"player{slot_idx}")
                        reid_class_ids.append(slot_idx - 1)  # 0-indexed for MOT compatibility
                        reid_class_names.append(slot_name)
                    else:
                        reid_class_ids.append(0)
                        reid_class_names.append("unknown")
                
                # Create output JSON with modified class_ids (ReId labels)
                # This format is compatible with MOT node input
                result = {
                    'bboxes': bboxes,
                    'scores': scores,
                    'class_ids': reid_class_ids,  # ReId labels replace original class_ids
                    'class_names': reid_class_names,  # Slot names replace original class_names
                }
                
                # Draw info on frame
                debug_frame = copy.deepcopy(frame)
                debug_frame = self._draw_reid_info(
                    debug_frame,
                    bboxes,
                    reid_class_names,
                    scores,
                )
                output_frame = debug_frame
            else:
                # K-means not trained, pass through
                result = json_data.copy()
                output_frame = copy.deepcopy(frame)
        
        elif frame is not None:
            output_frame = copy.deepcopy(frame)

        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')

        # Update display
        if output_frame is not None:
            texture = self.convert_cv_to_dpg(
                output_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)
        else:
            # Show black image
            black_image = np.zeros((small_window_h, small_window_w, 3))
            texture = self.convert_cv_to_dpg(
                black_image,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": output_frame, "json": result, "audio": None}

    def _draw_reid_info(self, image, bboxes, reid_names, scores):
        """Draw ReId information on the image"""
        import cv2
        
        for bbox, name, score in zip(bboxes, reid_names, scores):
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            
            # Get color based on name hash
            color = self._get_color_for_name(name)
            
            # Draw bounding box
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # Draw ReId label
            score_str = f'{score:.2f}'
            text = f'{name} ({score_str})'
            
            font_scale = 0.6
            thickness = 2
            
            cv2.putText(
                image,
                text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                color,
                thickness=thickness,
            )
        
        return image

    def _get_color_for_name(self, name):
        """Generate a consistent color for a name"""
        # Simple hash-based color generation
        hash_val = hash(name)
        r = (hash_val & 0xFF0000) >> 16
        g = (hash_val & 0x00FF00) >> 8
        b = (hash_val & 0x0000FF)
        return (b, g, r)  # BGR format for OpenCV

    def close(self, node_id):
        """Cleanup when node is closed"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        
        # Clean up data structures
        if tag_node_name in self._frame_counter:
            del self._frame_counter[tag_node_name]
        if tag_node_name in self._feature_buffer:
            del self._feature_buffer[tag_node_name]
        if tag_node_name in self._centroids:
            del self._centroids[tag_node_name]
        if tag_node_name in self._kmeans_trained:
            del self._kmeans_trained[tag_node_name]

    def get_setting_dict(self, node_id):
        """Save node settings"""
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict['slot_id'] = self._slot_id.get(tag_node_name, 1)
        setting_dict['slot_names'] = self._slot_names.get(tag_node_name, {1: "player1"})

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Load node settings"""
        tag_node_name = str(node_id) + ':' + self.node_tag

        # Restore slot count and names
        slot_number = int(setting_dict.get('slot_id', 1))
        slot_names = setting_dict.get('slot_names', {1: "player1"})
        
        # Initialize structures
        if tag_node_name not in self._slot_id:
            self._slot_id[tag_node_name] = 1
            self._slot_names[tag_node_name] = {1: "player1"}
        
        # Store the names
        self._slot_names[tag_node_name] = {}
        for slot_idx_str, name in slot_names.items():
            slot_idx = int(slot_idx_str) if isinstance(slot_idx_str, str) else slot_idx_str
            self._slot_names[tag_node_name][slot_idx] = name
        
        # Add slots (starting from 2 since 1 already exists)
        for slot_idx in range(2, slot_number + 1):
            self._add_slot(None, None, tag_node_name)
            # Update the name after creation
            slot_value_tag = tag_node_name + ':Slot' + str(slot_idx).zfill(2) + 'Value'
            if dpg.does_item_exist(slot_value_tag):
                slot_name = self._slot_names[tag_node_name].get(slot_idx, f"player{slot_idx}")
                dpg_set_value(slot_value_tag, slot_name)
