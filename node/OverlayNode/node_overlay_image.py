#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node


class FactoryNode:
    node_label = 'OverlayImage'
    node_tag = 'OverlayImage'
    
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
        node = OverlayImageNode()
        
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        # Input 1: Master/Base Image
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        # Input 2: Overlay Image
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input02Value'
        # Output: Combined Image
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        
        # UI controls
        node.tag_x_pos_name = node.tag_node_name + ':XPos'
        node.tag_x_pos_value_name = node.tag_node_name + ':XPosValue'
        node.tag_y_pos_name = node.tag_node_name + ':YPos'
        node.tag_y_pos_value_name = node.tag_node_name + ':YPosValue'
        node.tag_width_name = node.tag_node_name + ':Width'
        node.tag_width_value_name = node.tag_node_name + ':WidthValue'
        node.tag_height_name = node.tag_node_name + ':Height'
        node.tag_height_value_name = node.tag_node_name + ':HeightValue'
        node.tag_alpha_name = node.tag_node_name + ':Alpha'
        node.tag_alpha_value_name = node.tag_node_name + ':AlphaValue'
        
        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        
        # Create black image for initialization
        black_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )
        
        # Create texture for output
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )
        
        # Create node UI
        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Input for master image
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Master Image',
                )
            
            # Input for overlay image
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Overlay Image',
                )
            
            # Output image
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)
            
            # Position controls
            with dpg.node_attribute(
                    tag=node.tag_x_pos_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_x_pos_value_name,
                    label='X Position',
                    default_value=0,
                    min_value=-small_window_w,
                    max_value=small_window_w,
                    width=small_window_w - 80,
                )
            
            with dpg.node_attribute(
                    tag=node.tag_y_pos_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_y_pos_value_name,
                    label='Y Position',
                    default_value=0,
                    min_value=-small_window_h,
                    max_value=small_window_h,
                    width=small_window_w - 80,
                )
            
            # Size controls
            with dpg.node_attribute(
                    tag=node.tag_width_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_width_value_name,
                    label='Width',
                    default_value=0,  # 0 means use original size
                    min_value=0,
                    max_value=small_window_w * 2,  # Allow larger overlay images
                    width=small_window_w - 80,
                )
            
            with dpg.node_attribute(
                    tag=node.tag_height_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_height_value_name,
                    label='Height',
                    default_value=0,  # 0 means use original size
                    min_value=0,
                    max_value=small_window_h * 2,  # Allow larger overlay images
                    width=small_window_w - 80,
                )
            
            # Transparency control
            with dpg.node_attribute(
                    tag=node.tag_alpha_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_alpha_value_name,
                    label='Transparency',
                    default_value=1.0,
                    min_value=0.0,
                    max_value=1.0,
                    width=small_window_w - 80,
                )
        
        return node


class OverlayImageNode(Node):
    _ver = '1.0.0'
    
    node_label = 'OverlayImage'
    node_tag = 'OverlayImage'
    
    _opencv_setting_dict = None
    
    def __init__(self):
        super().__init__()
        self.node_label = 'OverlayImage'
        self.node_tag = 'OverlayImage'
    
    def _overlay_image(self, master_image, overlay_image, x_pos, y_pos, width, height, alpha):
        """
        Overlay an image onto a master image with position, size, and transparency controls.
        Supports BGRA images with alpha channel for true transparency.
        
        Args:
            master_image (np.ndarray): Base image (numpy array, BGR or BGRA)
            overlay_image (np.ndarray): Image to overlay (numpy array, BGR or BGRA)
            x_pos (int): X position on master image (can be negative)
            y_pos (int): Y position on master image (can be negative)
            width (int): Width of overlay (0 means use original size)
            height (int): Height of overlay (0 means use original size)
            alpha (float): Transparency level (0.0 = fully transparent, 1.0 = fully opaque)
            
        Returns:
            np.ndarray: Combined image
        """
        if master_image is None or overlay_image is None:
            return master_image if master_image is not None else overlay_image
        
        output_image = master_image.copy()
        overlay = overlay_image.copy()
        
        # Resize overlay if width or height is specified
        if width > 0 or height > 0:
            overlay_h, overlay_w = overlay.shape[:2]
            
            # If only one dimension is specified, maintain aspect ratio
            if width > 0 and height == 0:
                aspect_ratio = overlay_h / overlay_w
                height = int(width * aspect_ratio)
            elif height > 0 and width == 0:
                aspect_ratio = overlay_w / overlay_h
                width = int(height * aspect_ratio)
            
            # Resize the overlay
            overlay = cv2.resize(overlay, (width, height), interpolation=cv2.INTER_AREA)
        
        overlay_h, overlay_w = overlay.shape[:2]
        master_h, master_w = output_image.shape[:2]
        
        # Calculate the region of interest on the master image
        # Handle negative positions and clipping
        
        # Overlay coordinates (what part of overlay to use)
        overlay_x1 = 0
        overlay_y1 = 0
        overlay_x2 = overlay_w
        overlay_y2 = overlay_h
        
        # Master image coordinates (where to place overlay)
        master_x1 = x_pos
        master_y1 = y_pos
        master_x2 = x_pos + overlay_w
        master_y2 = y_pos + overlay_h
        
        # Clip overlay if it starts before master image bounds
        if master_x1 < 0:
            overlay_x1 = -master_x1
            master_x1 = 0
        if master_y1 < 0:
            overlay_y1 = -master_y1
            master_y1 = 0
        
        # Clip overlay if it extends beyond master image bounds
        if master_x2 > master_w:
            overlay_x2 = overlay_w - (master_x2 - master_w)
            master_x2 = master_w
        if master_y2 > master_h:
            overlay_y2 = overlay_h - (master_y2 - master_h)
            master_y2 = master_h
        
        # Check if there's any overlap
        if master_x1 >= master_x2 or master_y1 >= master_y2 or overlay_x1 >= overlay_x2 or overlay_y1 >= overlay_y2:
            return output_image  # No overlap, return original
        
        # Extract the regions to blend
        overlay_region = overlay[overlay_y1:overlay_y2, overlay_x1:overlay_x2]
        master_region = output_image[master_y1:master_y2, master_x1:master_x2]
        
        # Ensure both regions have the same shape
        if overlay_region.shape[:2] != master_region.shape[:2]:
            return output_image  # Shape mismatch, return original
        
        # Check if overlay has alpha channel (BGRA)
        has_overlay_alpha = len(overlay_region.shape) == 3 and overlay_region.shape[2] == 4
        has_master_alpha = len(master_region.shape) == 3 and master_region.shape[2] == 4
        
        if has_overlay_alpha:
            # Proper alpha blending with BGRA overlay
            # Extract alpha channel from overlay
            overlay_alpha = overlay_region[:, :, 3:4] / 255.0 * alpha  # Apply global alpha
            overlay_bgr = overlay_region[:, :, :3]
            
            # Ensure master region has same number of channels
            if not has_master_alpha:
                # Master is BGR, convert to BGRA if needed
                master_bgr = master_region
            else:
                master_bgr = master_region[:, :, :3]
            
            # Alpha blending: result = overlay * alpha + master * (1 - alpha)
            blended_bgr = (overlay_bgr * overlay_alpha + master_bgr * (1 - overlay_alpha)).astype(np.uint8)
            
            if has_master_alpha:
                # Combine with master alpha channel
                blended = np.dstack([blended_bgr, master_region[:, :, 3]])
            else:
                blended = blended_bgr
        else:
            # No alpha channel, use simple weighted blending
            blended = cv2.addWeighted(overlay_region, alpha, master_region, 1 - alpha, 0)
        
        # Place the blended region back into the output image
        output_image[master_y1:master_y2, master_x1:master_x2] = blended
        
        return output_image
    
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
        x_pos_tag = tag_node_name + ':XPosValue'
        y_pos_tag = tag_node_name + ':YPosValue'
        width_tag = tag_node_name + ':WidthValue'
        height_tag = tag_node_name + ':HeightValue'
        alpha_tag = tag_node_name + ':AlphaValue'
        
        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        
        # Get input connections
        master_image = None
        overlay_image = None
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            
            if connection_type == self.TYPE_IMAGE:
                connection_info_src = ':'.join(connection_info[0].split(':')[:2])
                image = node_image_dict.get(connection_info_src, None)
                
                # Determine if this is master or overlay based on which input it's connected to
                destination = connection_info[1]
                if 'Input01' in destination:
                    master_image = image
                elif 'Input02' in destination:
                    overlay_image = image
        
        # Get UI settings
        x_pos = dpg_get_value(x_pos_tag)
        y_pos = dpg_get_value(y_pos_tag)
        width = dpg_get_value(width_tag)
        height = dpg_get_value(height_tag)
        alpha = dpg_get_value(alpha_tag)
        
        # Perform overlay
        output_image = self._overlay_image(
            master_image,
            overlay_image,
            x_pos,
            y_pos,
            width,
            height,
            alpha
        )
        
        # Update display
        if output_image is not None:
            texture = self.convert_cv_to_dpg(
                output_image,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)
        
        return {"image": output_image, "json": None, "audio": None}
    
    def close(self, node_id):
        pass
    
    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        x_pos_tag = tag_node_name + ':XPosValue'
        y_pos_tag = tag_node_name + ':YPosValue'
        width_tag = tag_node_name + ':WidthValue'
        height_tag = tag_node_name + ':HeightValue'
        alpha_tag = tag_node_name + ':AlphaValue'
        
        pos = dpg.get_item_pos(tag_node_name)
        
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[x_pos_tag] = dpg_get_value(x_pos_tag)
        setting_dict[y_pos_tag] = dpg_get_value(y_pos_tag)
        setting_dict[width_tag] = dpg_get_value(width_tag)
        setting_dict[height_tag] = dpg_get_value(height_tag)
        setting_dict[alpha_tag] = dpg_get_value(alpha_tag)
        
        return setting_dict
    
    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        x_pos_tag = tag_node_name + ':XPosValue'
        y_pos_tag = tag_node_name + ':YPosValue'
        width_tag = tag_node_name + ':WidthValue'
        height_tag = tag_node_name + ':HeightValue'
        alpha_tag = tag_node_name + ':AlphaValue'
        
        if x_pos_tag in setting_dict:
            dpg_set_value(x_pos_tag, setting_dict[x_pos_tag])
        if y_pos_tag in setting_dict:
            dpg_set_value(y_pos_tag, setting_dict[y_pos_tag])
        if width_tag in setting_dict:
            dpg_set_value(width_tag, setting_dict[width_tag])
        if height_tag in setting_dict:
            dpg_set_value(height_tag, setting_dict[height_tag])
        if alpha_tag in setting_dict:
            dpg_set_value(alpha_tag, setting_dict[alpha_tag])
