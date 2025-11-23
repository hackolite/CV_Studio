#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node


class FactoryNode:
    node_label = 'ObjHeatmap'
    node_tag = 'ObjHeatmap'
    

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

        # Alpha slider for transparency
        node.tag_node_alpha_name = node.tag_node_name + ':Alpha'
        node.tag_node_alpha_value_name = node.tag_node_name + ':AlphaValue'
        
        # Class selection dropdown
        node.tag_node_class_name = node.tag_node_name + ':Class'
        node.tag_node_class_value_name = node.tag_node_name + ':ClassValue'


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
            # Texture for input image display
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_input01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )
            # Texture for output heatmap
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )


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
                dpg.add_image(node.tag_node_input01_value_name)

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Input detection JSON',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Class selection dropdown
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_class_value_name,
                    label="Class",
                    items=["All", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                    default_value="All",
                    width=small_window_w - 100,
                )

            # Alpha slider
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_alpha_value_name,
                    label="Decay",
                    width=small_window_w - 80,
                    default_value=0.95,
                    min_value=0.5,
                    max_value=0.99,
                    callback=None,
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

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'ObjHeatmap'
    node_tag = 'ObjHeatmap'

    
    def __init__(self, opencv_setting_dict=None):
        super().__init__()

        if opencv_setting_dict is None:
            # Default values
            opencv_setting_dict = {
                'process_height': 400,
                'process_width': 600
            }

        self._opencv_setting_dict = opencv_setting_dict
        
        # Accumulator for heatmap
        self.heatmap_accum = np.zeros((
            self._opencv_setting_dict['process_height'],
            self._opencv_setting_dict['process_width']
        ), dtype=np.float32)

    def _prepare_image_for_display(self, image, target_width, target_height):
        """
        Prepare an image for display by resizing and converting to BGR format.
        
        Args:
            image: Input image (can be grayscale or color, various formats)
            target_width: Target width for resizing
            target_height: Target height for resizing
            
        Returns:
            Processed image ready for display (BGR format, correct size)
        """
        if image is None:
            return None
            
        # Make a copy to avoid modifying the original
        processed = image.copy()
        
        # Resize if needed
        if processed.shape[:2] != (target_height, target_width):
            processed = cv2.resize(processed, (target_width, target_height))
        
        # Ensure 3 channels (BGR)
        if len(processed.shape) == 2:
            # Convert grayscale (H, W) to BGR
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        elif len(processed.shape) == 3:
            if processed.shape[2] == 1:
                # Convert grayscale (H, W, 1) to BGR - need to squeeze first
                processed = cv2.cvtColor(processed.squeeze(axis=2), cv2.COLOR_GRAY2BGR)
            elif processed.shape[2] == 4:
                # Convert BGRA to BGR
                processed = cv2.cvtColor(processed, cv2.COLOR_BGRA2BGR)
        
        return processed


    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        alpha_tag = tag_node_name + ':AlphaValue'
        class_tag = tag_node_name + ':ClassValue'
        input_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get decay factor and selected class
        decay = dpg_get_value(alpha_tag)
        selected_class = dpg_get_value(class_tag)

        # Find connected sources for JSON and IMAGE data
        connection_info_src_json = ''
        connection_info_src_image = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                connection_info_src_json = connection_info[0]
                connection_info_src_json = connection_info_src_json.split(':')[:2]
                connection_info_src_json = ':'.join(connection_info_src_json)
            elif connection_type == self.TYPE_IMAGE:
                connection_info_src_image = connection_info[0]
                connection_info_src_image = connection_info_src_image.split(':')[:2]
                connection_info_src_image = ':'.join(connection_info_src_image)

        # Get detection data and input image
        node_result = node_result_dict.get(connection_info_src_json, {})
        input_image = node_image_dict.get(connection_info_src_image, None)
        
        # Update input image display
        if input_image is not None:
            display_input = self._prepare_image_for_display(
                input_image, small_window_w, small_window_h
            )
            
            # Update input texture
            input_texture = self.convert_cv_to_dpg(
                display_input,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(input_value01_tag, input_texture)
        
        if use_pref_counter:
            start_time = time.monotonic()

        heatmap_image = None
        
        if node_result and isinstance(node_result, dict):
            # Extract detection data
            bboxes = node_result.get('bboxes', [])
            scores = node_result.get('scores', [])
            class_ids = node_result.get('class_ids', [])
            
            if bboxes and scores:
                # Create temporary heatmap for current frame
                temp_heatmap = np.zeros_like(self.heatmap_accum)
                
                # Filter and add each detection to the heatmap based on selected class
                for idx, (bbox, score) in enumerate(zip(bboxes, scores)):
                    # Check if we should include this detection based on class filter
                    if selected_class != "All":
                        # Skip if class_ids not available or doesn't match selected class
                        if not class_ids or idx >= len(class_ids):
                            continue
                        try:
                            if int(class_ids[idx]) != int(selected_class):
                                continue
                        except (ValueError, TypeError):
                            # Skip if class_id cannot be converted to int
                            continue
                    
                    x1, y1, x2, y2 = map(int, bbox)
                    
                    # Clip coordinates to image bounds
                    x1 = max(0, min(x1, small_window_w - 1))
                    x2 = max(0, min(x2, small_window_w - 1))
                    y1 = max(0, min(y1, small_window_h - 1))
                    y2 = max(0, min(y2, small_window_h - 1))
                    
                    # Add score to the bounding box region
                    if x2 > x1 and y2 > y1:
                        temp_heatmap[y1:y2, x1:x2] += score
                
                # Apply decay and accumulate
                self.heatmap_accum = self.heatmap_accum * decay + temp_heatmap
            else:
                # No detections, just decay
                self.heatmap_accum = self.heatmap_accum * decay
        else:
            # No detection data, just decay
            self.heatmap_accum = self.heatmap_accum * decay
        
        # Normalize and create colored heatmap
        if self.heatmap_accum.max() > 0:
            heatmap_norm = np.clip(self.heatmap_accum / self.heatmap_accum.max(), 0, 1)
        else:
            heatmap_norm = self.heatmap_accum
        
        heatmap_display = (heatmap_norm * 255).astype(np.uint8)
        
        # Apply Gaussian blur for smoother appearance
        heatmap_display = cv2.GaussianBlur(heatmap_display, (25, 25), 0)
        
        # Apply colormap (JET colormap for hot-cold visualization)
        heatmap_colored = cv2.applyColorMap(heatmap_display, cv2.COLORMAP_JET)
        
        # Overlay heatmap with input image if available
        if input_image is not None:
            # Prepare input image for blending
            prepared_input = self._prepare_image_for_display(
                input_image, small_window_w, small_window_h
            )
            
            # Blend heatmap with input image (0.6 heatmap, 0.4 original image)
            heatmap_image = cv2.addWeighted(prepared_input, 0.4, heatmap_colored, 0.6, 0)
        else:
            # No input image, just use the heatmap
            heatmap_image = heatmap_colored

        if use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')

        if heatmap_image is not None:
            texture = self.convert_cv_to_dpg(
                heatmap_image,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": heatmap_image, "json": None, "audio": None}


    def close(self, node_id):
        pass


    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        alpha_tag = tag_node_name + ':AlphaValue'
        class_tag = tag_node_name + ':ClassValue'

        decay = dpg_get_value(alpha_tag)
        selected_class = dpg_get_value(class_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[alpha_tag] = decay
        setting_dict[class_tag] = selected_class

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        alpha_tag = tag_node_name + ':AlphaValue'
        class_tag = tag_node_name + ':ClassValue'

        decay = setting_dict.get(alpha_tag, 0.95)
        selected_class = setting_dict.get(class_tag, "All")
        dpg_set_value(alpha_tag, decay)
        dpg_set_value(class_tag, selected_class)
