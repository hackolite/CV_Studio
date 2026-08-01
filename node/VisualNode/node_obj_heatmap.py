#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
from node.VisualNode.heatmap_utils import get_colormap, ensure_odd_blur_size, COLORMAP_NAMES
from node.DLNode.object_detection.coco_class_names import coco_class_names


def get_class_dropdown_items():
    """Generate dropdown items with class IDs and names from COCO dataset."""
    items = ["All"]
    for class_id, class_name in coco_class_names.items():
        items.append(f"{class_id}: {class_name}")
    return items

# Guard against division by zero when memory_seconds is extremely small
_MIN_MEMORY_SECONDS = 1e-6
# Assumed frame-rate used only for backward-compat conversion of old float-decay saves
_ASSUMED_FPS_FOR_COMPAT = 30.0

class FactoryNode:
    node_label = 'ObjHeatMap'
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
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Image',
                )

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
                    items=get_class_dropdown_items(),
                    default_value="All",
                    width=small_window_w - 100,
                )

            # Memory slider (seconds; 300 = ∞ full history from node creation)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_alpha_value_name,
                    label="Mmemory",
                    width=small_window_w - 80,
                    default_value=30,
                    min_value=1,
                    max_value=300,
                    callback=None,
                )

            # Blur slider
            node.tag_node_blur_name = node.tag_node_name + ':Blur'
            node.tag_node_blur_value_name = node.tag_node_name + ':BlurValue'
            
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_blur_value_name,
                    label="Blur",
                    width=small_window_w - 80,
                    default_value=25,
                    min_value=1,
                    max_value=99,
                    clamped=True,
                    callback=None,
                )

            # Colormap dropdown
            node.tag_node_colormap_name = node.tag_node_name + ':Colormap'
            node.tag_node_colormap_value_name = node.tag_node_name + ':ColormapValue'
            
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_colormap_value_name,
                    label="Colormap",
                    items=COLORMAP_NAMES,
                    default_value="JET",
                    width=small_window_w - 100,
                    callback=None,
                )

            # Blend Alpha slider
            node.tag_node_blend_name = node.tag_node_name + ':Blend'
            node.tag_node_blend_value_name = node.tag_node_name + ':BlendValue'
            
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_blend_value_name,
                    label="Blend Alpha",
                    width=small_window_w - 80,
                    default_value=0.6,
                    min_value=0.0,
                    max_value=1.0,
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

    node_label = 'ObjHeatMap'
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

        # Timestamp of the last processed frame (used for time-based decay)
        self._last_update_time = None

    def _build_dynamic_class_items(self, class_ids, class_names):
        """Build dynamic combobox items from model class data.

        Args:
            class_ids: list of detected class IDs from input JSON
            class_names: dict mapping class IDs (int or str) to human-readable names

        Returns:
            list of formatted strings like ["All", "0: person", "2: car"]
        """
        items = ["All"]
        seen_ids = set()

        if class_names:
            for key in class_names.keys():
                try:
                    seen_ids.add(int(key))
                except (ValueError, TypeError):
                    pass

        for cid in class_ids:
            try:
                seen_ids.add(int(cid))
            except (ValueError, TypeError):
                pass

        for cid in sorted(seen_ids):
            cid_str = str(cid)
            name = None
            if class_names:
                name = class_names.get(cid_str) or class_names.get(cid)
            if name is not None:
                items.append(f"{cid}: {name}")
            elif cid in coco_class_names:
                items.append(f"{cid}: {coco_class_names[cid]}")
            else:
                items.append(f"{cid}: class_{cid}")

        return items

    def _update_class_combo(self, class_combo_tag, items):
        """Update the class combo widget with new items, preserving current selection."""
        if not dpg.does_item_exist(class_combo_tag):
            return
        normalized = [str(i) for i in items if i is not None]
        if not normalized:
            return
        previous_value = dpg_get_value(class_combo_tag)
        dpg.configure_item(class_combo_tag, items=normalized)
        if previous_value not in normalized:
            dpg_set_value(class_combo_tag, normalized[0])

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
        blur_tag = tag_node_name + ':BlurValue'
        colormap_tag = tag_node_name + ':ColormapValue'
        blend_tag = tag_node_name + ':BlendValue'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get parameters
        memory_seconds = dpg_get_value(alpha_tag)  # int, 1–300; 300 = ∞
        selected_class = dpg_get_value(class_tag)
        blur_size = dpg_get_value(blur_tag)
        colormap_name = dpg_get_value(colormap_tag)
        blend_alpha = dpg_get_value(blend_tag)
        
        # Ensure blur_size is odd for GaussianBlur
        blur_size = ensure_odd_blur_size(blur_size)
        
        # Get colormap constant
        colormap = get_colormap(colormap_name)

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

        # Dynamically update class combo from incoming JSON detection data
        if node_result and isinstance(node_result, dict):
            incoming_class_ids = node_result.get('class_ids', [])
            incoming_class_names = node_result.get('class_names', {})
            if incoming_class_ids or incoming_class_names:
                dynamic_items = self._build_dynamic_class_items(
                    incoming_class_ids, incoming_class_names
                )
                self._update_class_combo(class_tag, dynamic_items)

        # Re-read selected_class after potential combo update
        selected_class = dpg_get_value(class_tag)

        # Compute time-based EMA decay factor (O(1), no history buffer needed).
        # memory_seconds == 300 → infinite accumulation (decay = 1.0, full history
        # from node creation).  For any finite T, decay = exp(-dt / T) so that
        # after T seconds without detections the accumulator has fallen to ~37 %.
        current_time = time.monotonic()
        if self._last_update_time is None:
            dt = 0.0
        else:
            dt = current_time - self._last_update_time
        self._last_update_time = current_time

        if memory_seconds >= 300:
            decay = 1.0  # full history — accumulate from node creation
        else:
            decay = np.exp(-dt / max(memory_seconds, _MIN_MEMORY_SECONDS))

        if use_pref_counter:
            start_time = time.monotonic()

        heatmap_image = None
        
        # Ensure heatmap accumulator has correct dimensions
        if self.heatmap_accum.shape != (small_window_h, small_window_w):
            # Resize the accumulator to match current processing dimensions
            self.heatmap_accum = cv2.resize(
                self.heatmap_accum, 
                (small_window_w, small_window_h),
                interpolation=cv2.INTER_LINEAR
            )
        
        # Only process and display heatmap if BOTH image and JSON data are present
        if input_image is not None and node_result and isinstance(node_result, dict):
            # Extract detection data
            bboxes = node_result.get('bboxes', [])
            scores = node_result.get('scores', [])
            class_ids = node_result.get('class_ids', [])
            
            # Calculate scaling factors from input image to processing window
            input_h, input_w = input_image.shape[:2]
            # Protect against division by zero (invalid input images)
            if input_w > 0 and input_h > 0:
                scale_x = small_window_w / input_w
                scale_y = small_window_h / input_h
            else:
                # Invalid input dimensions, use 1:1 scale (no scaling)
                scale_x = 1.0
                scale_y = 1.0
            
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
                            # Parse "ID: name" format or plain integer
                            if ":" in str(selected_class):
                                target_class_id = int(str(selected_class).split(":")[0].strip())
                            else:
                                target_class_id = int(selected_class)
                            if int(class_ids[idx]) != target_class_id:
                                continue
                        except (ValueError, TypeError, IndexError):
                            # Skip if class_id cannot be converted to int
                            continue
                    
                    # Scale coordinates from input image space to processing window space
                    x1, y1, x2, y2 = bbox
                    x1 = int(x1 * scale_x)
                    y1 = int(y1 * scale_y)
                    x2 = int(x2 * scale_x)
                    y2 = int(y2 * scale_y)
                    
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
            
            # Normalize and create colored heatmap
            if self.heatmap_accum.max() > 0:
                heatmap_norm = np.clip(self.heatmap_accum / self.heatmap_accum.max(), 0, 1)
            else:
                heatmap_norm = self.heatmap_accum
            
            heatmap_display = (heatmap_norm * 255).astype(np.uint8)
            
            # Apply Gaussian blur for smoother appearance with configurable kernel size
            heatmap_display = cv2.GaussianBlur(heatmap_display, (blur_size, blur_size), 0)
            
            # Apply colormap with configurable colormap
            heatmap_colored = cv2.applyColorMap(heatmap_display, colormap)
            
            # Prepare input image for blending
            prepared_input = self._prepare_image_for_display(
                input_image, small_window_w, small_window_h
            )
            
            # Blend heatmap with input image with configurable alpha
            heatmap_image = cv2.addWeighted(prepared_input, 1.0 - blend_alpha, heatmap_colored, blend_alpha, 0)

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
        blur_tag = tag_node_name + ':BlurValue'
        colormap_tag = tag_node_name + ':ColormapValue'
        blend_tag = tag_node_name + ':BlendValue'

        memory_seconds = dpg_get_value(alpha_tag)
        selected_class = dpg_get_value(class_tag)
        blur_size = dpg_get_value(blur_tag)
        colormap_name = dpg_get_value(colormap_tag)
        blend_alpha = dpg_get_value(blend_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[alpha_tag] = memory_seconds
        setting_dict[class_tag] = selected_class
        setting_dict[blur_tag] = blur_size
        setting_dict[colormap_tag] = colormap_name
        setting_dict[blend_tag] = blend_alpha

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        alpha_tag = tag_node_name + ':AlphaValue'
        class_tag = tag_node_name + ':ClassValue'
        blur_tag = tag_node_name + ':BlurValue'
        colormap_tag = tag_node_name + ':ColormapValue'
        blend_tag = tag_node_name + ':BlendValue'

        raw = setting_dict.get(alpha_tag, 30)
        # Backward compatibility: old saves stored a float decay (0.80–0.995).
        # Convert those to a rough equivalent in seconds so existing graphs
        # still load without crashing.  A decay of d applied at ~30 fps gives
        # a time constant of  T = -1 / (fps * ln(d)).  We assume 30 fps.
        if isinstance(raw, float) and raw < 1.0:
            import math
            try:
                memory_seconds = int(round(-1.0 / (_ASSUMED_FPS_FOR_COMPAT * math.log(raw))))
                memory_seconds = max(1, min(300, memory_seconds))
            except (ValueError, ZeroDivisionError):
                memory_seconds = 30
        else:
            memory_seconds = int(raw)

        selected_class = setting_dict.get(class_tag, "All")
        blur_size = setting_dict.get(blur_tag, 25)
        colormap_name = setting_dict.get(colormap_tag, "JET")
        blend_alpha = setting_dict.get(blend_tag, 0.6)

        dpg_set_value(alpha_tag, memory_seconds)
        dpg_set_value(class_tag, selected_class)
        dpg_set_value(blur_tag, blur_size)
        dpg_set_value(colormap_tag, colormap_name)
        dpg_set_value(blend_tag, blend_alpha)

