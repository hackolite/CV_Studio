#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node_editor import node_resizer

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
                
                # Add size selector
                with dpg.group(horizontal=True):
                    dpg.add_text("Size:")
                    node.tag_node_size_selector = node.tag_node_name + ':SizeSelector'
                    dpg.add_combo(
                        items=node_resizer.SIZE_PRESET_NAMES,
                        default_value="Small",
                        tag=node.tag_node_size_selector,
                        width=100,
                        callback=lambda: node.resize_node(node_id),
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
    _ver = '0.0.2'  # Bumped version for resize feature

    node_label = 'Image'
    node_tag = 'Image'

    _opencv_setting_dict = None

    _image = {}
    _image_filepath = {}
    _prev_image_filepath = {}
    _node_sizes = {}  # Store node sizes {node_id: (width, height)}

    def __init__(self):
        super().__init__()  # Call parent constructor
        self.node_label = 'Image'
        self.node_tag = 'Image'
    
    def resize_node(self, node_id):
        """Callback when node size is changed"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        size_selector_tag = tag_node_name + ':SizeSelector'
        
        # Get selected size
        size_name = dpg_get_value(size_selector_tag)
        width, height = node_resizer.get_size_from_preset(size_name)
        
        # Store the new size
        self._node_sizes[str(node_id)] = (width, height)
        
        # Update texture size
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        
        # Create new blank texture with new size
        black_image = np.zeros((width, height, 3))
        black_texture = self.convert_cv_to_dpg(black_image, width, height)
        
        # Delete old texture and create new one
        if dpg.does_item_exist(output_value01_tag):
            dpg.delete_item(output_value01_tag)
        
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                width,
                height,
                black_texture,
                tag=output_value01_tag,
                format=dpg.mvFormat_Float_rgb,
            )
        
        # Force update if we have an image loaded
        if str(node_id) in self._image and self._image[str(node_id)] is not None:
            frame = self._image[str(node_id)]
            texture = self.convert_cv_to_dpg(frame, width, height)
            dpg_set_value(output_value01_tag, texture)

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

        # Get size from stored sizes, or use defaults
        if str(node_id) in self._node_sizes:
            small_window_w, small_window_h = self._node_sizes[str(node_id)]
        else:
            small_window_w = self._opencv_setting_dict['input_window_width']
            small_window_h = self._opencv_setting_dict['input_window_height']


        image_path = self._image_filepath.get(str(node_id), None)
        prev_image_path = self._prev_image_filepath.get(str(node_id), None)
        if prev_image_path != image_path:
            self._image[str(node_id)] = cv2.imread(image_path)
            self._prev_image_filepath[str(node_id)] = image_path


        frame = self._image.get(str(node_id), None)


        if frame is not None:
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
        size_selector_tag = tag_node_name + ':SizeSelector'

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        
        # Save the selected size
        if dpg.does_item_exist(size_selector_tag):
            setting_dict['size_preset'] = dpg_get_value(size_selector_tag)
        
        # Save the actual size if stored
        if str(node_id) in self._node_sizes:
            setting_dict['node_size'] = self._node_sizes[str(node_id)]

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        size_selector_tag = tag_node_name + ':SizeSelector'
        
        # Restore size preset if saved
        if 'size_preset' in setting_dict and dpg.does_item_exist(size_selector_tag):
            dpg_set_value(size_selector_tag, setting_dict['size_preset'])
        
        # Restore node size if saved
        if 'node_size' in setting_dict:
            self._node_sizes[str(node_id)] = setting_dict['node_size']
            # Trigger resize to update the texture
            self.resize_node(node_id)

    def _callback_file_select(self, sender, data):
        if data['file_name'] != '.':
            node_id = sender.split(':')[1]
            self._image_filepath[node_id] = data['file_path_name']
