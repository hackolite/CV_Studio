#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value, dpg_delete_item

from node.node_abc import DpgNodeABC
#from node_editor.util import convert_cv_to_dpg
from node.basenode import Node

logger = logging.getLogger(__name__)


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






        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['input_window_width']
        node.small_window_h = node._opencv_setting_dict['input_window_height']


        black_image = np.zeros((node.small_window_h, node.small_window_w, 3))
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
                    
        return node
        




class ImageNode(Node):
    _ver = '0.0.1'

    node_label = 'Image'
    node_tag = 'Image'

    _opencv_setting_dict = None

    _image = {}
    _image_filepath = {}
    _prev_image_filepath = {}
    _texture_cache = {}  # Cache converted textures to avoid repeated conversion

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

        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']


        image_path = self._image_filepath.get(str(node_id), None)
        prev_image_path = self._prev_image_filepath.get(str(node_id), None)
        
        # Performance optimization: only reload and convert texture when image path changes
        # to prevent UI freezing from repeated texture conversion of the same static image
        if prev_image_path != image_path:
            if image_path is not None:
                loaded_image = cv2.imread(image_path)
                if loaded_image is not None:
                    self._image[str(node_id)] = loaded_image
                    self._prev_image_filepath[str(node_id)] = image_path
                    
                    # Convert and cache the texture only when image loads successfully
                    texture = self.convert_cv_to_dpg(
                        loaded_image,
                        small_window_w,
                        small_window_h,
                    )
                    self._texture_cache[str(node_id)] = texture
                    dpg_set_value(output_value01_tag, texture)
                else:
                    # Image load failed - clear cached data
                    self._image[str(node_id)] = None
                    self._prev_image_filepath[str(node_id)] = image_path
                    if str(node_id) in self._texture_cache:
                        del self._texture_cache[str(node_id)]
            else:
                # No image path - clear cached data
                self._image[str(node_id)] = None
                self._prev_image_filepath[str(node_id)] = None
                if str(node_id) in self._texture_cache:
                    del self._texture_cache[str(node_id)]


        frame = self._image.get(str(node_id), None)

        return {"image": frame, "json": None, "audio": None}

    def close(self, node_id):
        # Clean up cached data for this node to prevent memory leaks
        node_id_str = str(node_id)
        if node_id_str in self._image:
            del self._image[node_id_str]
        if node_id_str in self._image_filepath:
            del self._image_filepath[node_id_str]
        if node_id_str in self._prev_image_filepath:
            del self._prev_image_filepath[node_id_str]
        if node_id_str in self._texture_cache:
            del self._texture_cache[node_id_str]
        # Delete the file_dialog widget (created outside the node hierarchy
        # so dpg.delete_item(node_widget) does not remove it automatically).
        # Leaving it as an orphan causes a duplicate-tag error on undo/re-add
        # on Windows where alias cleanup is stricter.
        dialog_tag = 'image_select:' + node_id_str
        try:
            if dpg.does_item_exist(dialog_tag):
                logger.debug(
                    "node_image.close: deleting orphan file_dialog tag=%s", dialog_tag,
                )
                dpg_delete_item(dialog_tag)
        except Exception as exc:
            logger.warning(
                "node_image.close: failed to delete file_dialog tag=%s: %s", dialog_tag, exc,
            )

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
