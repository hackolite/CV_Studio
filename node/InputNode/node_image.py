#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
#from node_editor.util import convert_cv_to_dpg
from node.basenode import Node


class FactoryNode:
    node_label = 'Image'
    node_tag = 'Image'
    

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


        node = ImageNode()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input01'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'


        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloat'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloatValue'






        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['input_window_width']
        node.small_window_h = node._opencv_setting_dict['input_window_height']
        
        # Initialize size for this node instance
        node._node_widths[str(node_id)] = node.small_window_w
        node._node_heights[str(node_id)] = node.small_window_h


        black_image = np.zeros((node.small_window_w, node.small_window_h, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            node.small_window_w,
            node.small_window_h,
        )


        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                node.small_window_w,
                node.small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.file_dialog(
                directory_selector=False,
                show=False,
                modal=True,
                height=int(node.small_window_h * 3),
                callback=node._callback_file_select,
                id='image_select:' + str(node_id),
        ):
            dpg.add_file_extension(
                'Image (*.bmp *.jpg *.png *.gif){.bmp,.jpg,.png,.gif}')
            dpg.add_file_extension('', color=(150, 255, 150, 255))


                # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))          # Yellow background
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 128, 255)) # Light yellow on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 64, 255))   # Darker yellow on press
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))                # Black text for better readability
        
        # Outputs audio, json, float, elapsed time as disabled yellow buttons
        def add_yellow_disabled_button(label, tag):
            btn = dpg.add_button(
                label=label,
                tag=tag,
                enabled=False,
                width=node.small_window_w
                
            )
            dpg.bind_item_theme(btn, yellow_button_theme)
            return btn  
        
        # Callback for resizing
        def resize_callback(sender, app_data, user_data):
            nid = user_data
            width = dpg.get_value(f"width_slider:{nid}")
            height = dpg.get_value(f"height_slider:{nid}")
            node._node_widths[str(nid)] = width
            node._node_heights[str(nid)] = height
        
        
        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='Select Image',
                    width=node.small_window_w,
                    callback=lambda: dpg.show_item(
                        'image_select:' + str(node_id), ),
                )
            
            # Add resize controls
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':ResizeControls',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("Resize:")
                dpg.add_slider_int(
                    tag=f"width_slider:{node_id}",
                    label="Width",
                    default_value=node.small_window_w,
                    min_value=80,
                    max_value=800,
                    width=node.small_window_w - 60,
                    callback=resize_callback,
                    user_data=node_id,
                )
                dpg.add_slider_int(
                    tag=f"height_slider:{node_id}",
                    label="Height",
                    default_value=node.small_window_h,
                    min_value=60,
                    max_value=600,
                    width=node.small_window_w - 60,
                    callback=resize_callback,
                    user_data=node_id,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)
                
                # Outputs
            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Static):
                    add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                    
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                    add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)

            with dpg.node_attribute(tag=node.tag_node_output_float_name, attribute_type=dpg.mvNode_Attr_Static):
                    add_yellow_disabled_button("Float", node.tag_node_output_float_value_name)
                    
        return node
        




class ImageNode(Node):
    _ver = '0.0.1'

    node_label = 'Image'
    node_tag = 'Image'

    _opencv_setting_dict = None

    _image = {}
    _image_filepath = {}
    _prev_image_filepath = {}
    _node_widths = {}  # Store width for each node instance
    _node_heights = {}  # Store height for each node instance
    _prev_node_widths = {}  # Track previous width to detect changes
    _prev_node_heights = {}  # Track previous height to detect changes

    def __init__(self):
        super().__init__()  # Call parent constructor
        self.node_label = 'Image'
        self.node_tag = 'Image'

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

        # Get dynamic sizes from sliders
        small_window_w = self._node_widths.get(str(node_id), self._opencv_setting_dict['input_window_width'])
        small_window_h = self._node_heights.get(str(node_id), self._opencv_setting_dict['input_window_height'])
        
        # Check if size changed
        prev_w = self._prev_node_widths.get(str(node_id), small_window_w)
        prev_h = self._prev_node_heights.get(str(node_id), small_window_h)
        size_changed = (prev_w != small_window_w or prev_h != small_window_h)

        image_path = self._image_filepath.get(str(node_id), None)
        prev_image_path = self._prev_image_filepath.get(str(node_id), None)
        if prev_image_path != image_path:
            self._image[str(node_id)] = cv2.imread(image_path)
            self._prev_image_filepath[str(node_id)] = image_path


        frame = self._image.get(str(node_id), None)


        if frame is not None:
            # Recreate texture if size changed
            if size_changed:
                if dpg.does_item_exist(output_value01_tag):
                    dpg.delete_item(output_value01_tag)
                
                black_image = np.zeros((small_window_h, small_window_w, 3))
                black_texture = self.convert_cv_to_dpg(
                    black_image,
                    small_window_w,
                    small_window_h,
                )
                with dpg.texture_registry(show=False):
                    dpg.add_raw_texture(
                        small_window_w,
                        small_window_h,
                        black_texture,
                        tag=output_value01_tag,
                        format=dpg.mvFormat_Float_rgb,
                    )
                
                # Update previous size
                self._prev_node_widths[str(node_id)] = small_window_w
                self._prev_node_heights[str(node_id)] = small_window_h
            
            texture = self.convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass

    def _callback_file_select(self, sender, data):
        if data['file_name'] != '.':
            node_id = sender.split(':')[1]
            self._image_filepath[node_id] = data['file_path_name']
