#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node


class FactoryNode:
    node_label = 'Overlay'
    node_tag = 'Overlay'
    
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
        node = OverlayNode()
        
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        
        # UI controls for styling
        node.tag_font_scale_name = node.tag_node_name + ':FontScale'
        node.tag_font_scale_value_name = node.tag_node_name + ':FontScaleValue'
        node.tag_text_color_name = node.tag_node_name + ':TextColor'
        node.tag_text_color_value_name = node.tag_node_name + ':TextColorValue'
        node.tag_bg_color_name = node.tag_node_name + ':BgColor'
        node.tag_bg_color_value_name = node.tag_node_name + ':BgColorValue'
        node.tag_position_name = node.tag_node_name + ':Position'
        node.tag_position_value_name = node.tag_node_name + ':PositionValue'
        
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
            
            # Input for JSON overlay data
            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Overlay Data (JSON)',
                )
            
            # Output image with overlay
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)
            
            # Styling controls
            with dpg.node_attribute(
                    tag=node.tag_font_scale_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_font_scale_value_name,
                    label='Font Scale',
                    default_value=0.7,
                    min_value=0.3,
                    max_value=2.0,
                    width=small_window_w - 80,
                )
            
            with dpg.node_attribute(
                    tag=node.tag_text_color_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_color_edit(
                    tag=node.tag_text_color_value_name,
                    label='Text Color',
                    default_value=(255, 255, 255, 255),
                    no_alpha=True,
                    width=100,
                )
            
            with dpg.node_attribute(
                    tag=node.tag_bg_color_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_color_edit(
                    tag=node.tag_bg_color_value_name,
                    label='Background',
                    default_value=(0, 0, 0, 180),
                    alpha_preview=dpg.mvColorEdit_AlphaPreview,
                    width=100,
                )
            
            with dpg.node_attribute(
                    tag=node.tag_position_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_position_value_name,
                    label='Position',
                    items=['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right', 'Center'],
                    default_value='Top Right',
                    width=small_window_w - 80,
                )
        
        return node


class OverlayNode(Node):
    _ver = '1.0.0'
    
    node_label = 'Overlay'
    node_tag = 'Overlay'
    
    _opencv_setting_dict = None
    
    def __init__(self):
        super().__init__()
    
    def _flatten_dict(self, d, parent_key='', sep='_'):
        """Flatten nested dictionary for display"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _draw_overlay(self, image, data_dict, font_scale, text_color, bg_color, position):
        """Draw overlay information on image in a stylish way"""
        if image is None or data_dict is None:
            return image
        
        output_image = image.copy()
        height, width = output_image.shape[:2]
        
        # Flatten nested dictionaries
        flat_data = self._flatten_dict(data_dict)
        
        # Prepare text lines
        lines = []
        for key, value in flat_data.items():
            # Format the value nicely
            if isinstance(value, float):
                value_str = f"{value:.2f}"
            else:
                value_str = str(value)
            lines.append(f"{key}: {value_str}")
        
        if not lines:
            return output_image
        
        # Calculate text dimensions
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = max(1, int(font_scale * 2))
        padding = int(15 * font_scale)
        line_height = int(35 * font_scale)
        
        # Get max text width
        max_width = 0
        for line in lines:
            (text_w, text_h), _ = cv2.getTextSize(line, font, font_scale, thickness)
            max_width = max(max_width, text_w)
        
        # Calculate panel dimensions
        panel_width = max_width + padding * 2
        panel_height = len(lines) * line_height + padding * 2
        
        # Determine position
        if position == 'Top Left':
            x, y = padding, padding
        elif position == 'Top Right':
            x, y = width - panel_width - padding, padding
        elif position == 'Bottom Left':
            x, y = padding, height - panel_height - padding
        elif position == 'Bottom Right':
            x, y = width - panel_width - padding, height - panel_height - padding
        else:  # Center
            x, y = (width - panel_width) // 2, (height - panel_height) // 2
        
        # Ensure panel is within image bounds
        x = max(0, min(x, width - panel_width))
        y = max(0, min(y, height - panel_height))
        
        # Draw semi-transparent background panel
        overlay = output_image.copy()
        cv2.rectangle(
            overlay,
            (x, y),
            (x + panel_width, y + panel_height),
            (int(bg_color[2]), int(bg_color[1]), int(bg_color[0])),
            -1
        )
        
        # Apply transparency
        alpha = bg_color[3] / 255.0
        cv2.addWeighted(overlay, alpha, output_image, 1 - alpha, 0, output_image)
        
        # Draw border
        cv2.rectangle(
            output_image,
            (x, y),
            (x + panel_width, y + panel_height),
            (int(text_color[2] * 0.7), int(text_color[1] * 0.7), int(text_color[0] * 0.7)),
            2
        )
        
        # Draw text lines
        text_x = x + padding
        text_y = y + padding + int(25 * font_scale)
        
        for line in lines:
            cv2.putText(
                output_image,
                line,
                (text_x, text_y),
                font,
                font_scale,
                (int(text_color[2]), int(text_color[1]), int(text_color[0])),
                thickness,
                cv2.LINE_AA
            )
            text_y += line_height
        
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
        font_scale_tag = tag_node_name + ':FontScaleValue'
        text_color_tag = tag_node_name + ':TextColorValue'
        bg_color_tag = tag_node_name + ':BgColorValue'
        position_tag = tag_node_name + ':PositionValue'
        
        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        
        # Get input connections
        image_src = None
        json_data = None
        
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            
            if connection_type == self.TYPE_IMAGE:
                # Get source image
                connection_info_src = ':'.join(connection_info[0].split(':')[:2])
                image_src = node_image_dict.get(connection_info_src, None)
            
            elif connection_type == self.TYPE_JSON:
                # Get source JSON data
                connection_info_src = ':'.join(connection_info[0].split(':')[:2])
                json_data = node_result_dict.get(connection_info_src, {}).get('json', None)
        
        # Get UI settings
        font_scale = dpg_get_value(font_scale_tag)
        text_color = dpg_get_value(text_color_tag)
        bg_color = dpg_get_value(bg_color_tag)
        position = dpg_get_value(position_tag)
        
        # Draw overlay on image
        output_image = None
        if image_src is not None:
            output_image = self._draw_overlay(
                image_src,
                json_data,
                font_scale,
                text_color,
                bg_color,
                position
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
        font_scale_tag = tag_node_name + ':FontScaleValue'
        text_color_tag = tag_node_name + ':TextColorValue'
        bg_color_tag = tag_node_name + ':BgColorValue'
        position_tag = tag_node_name + ':PositionValue'
        
        pos = dpg.get_item_pos(tag_node_name)
        
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[font_scale_tag] = dpg_get_value(font_scale_tag)
        setting_dict[text_color_tag] = dpg_get_value(text_color_tag)
        setting_dict[bg_color_tag] = dpg_get_value(bg_color_tag)
        setting_dict[position_tag] = dpg_get_value(position_tag)
        
        return setting_dict
    
    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        font_scale_tag = tag_node_name + ':FontScaleValue'
        text_color_tag = tag_node_name + ':TextColorValue'
        bg_color_tag = tag_node_name + ':BgColorValue'
        position_tag = tag_node_name + ':PositionValue'
        
        if font_scale_tag in setting_dict:
            dpg_set_value(font_scale_tag, setting_dict[font_scale_tag])
        if text_color_tag in setting_dict:
            dpg_set_value(text_color_tag, setting_dict[text_color_tag])
        if bg_color_tag in setting_dict:
            dpg_set_value(bg_color_tag, setting_dict[bg_color_tag])
        if position_tag in setting_dict:
            dpg_set_value(position_tag, setting_dict[position_tag])
