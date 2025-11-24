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

class FactoryNode:
    node_label = 'Heatmap'
    node_tag = 'Heatmap'
    

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
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input03Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'


        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']


        black_image = np.zeros((small_window_w, small_window_h, 3))
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
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)


            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input03_value_name,
                    label="threshold",
                    width=small_window_w - 80,
                    default_value=127,
                    min_value=node._min_val,
                    max_value=node._max_val,
                    callback=None,
                )

            # Add Memory slider for heatmap memory control
            node.tag_node_input04_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04'
            node.tag_node_input04_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input04Value'
            
            with dpg.node_attribute(
                    tag=node.tag_node_input04_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input04_value_name,
                    label="Memory",
                    width=small_window_w - 80,
                    default_value=0.98,
                    min_value=0.80,
                    max_value=0.995,
                    callback=None,
                )

            # Add Blur slider for Gaussian blur kernel size
            node.tag_node_input05_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input05'
            node.tag_node_input05_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input05Value'
            
            with dpg.node_attribute(
                    tag=node.tag_node_input05_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input05_value_name,
                    label="Blur",
                    width=small_window_w - 80,
                    default_value=25,
                    min_value=1,
                    max_value=99,
                    clamped=True,
                    callback=None,
                )

            # Add Colormap dropdown
            node.tag_node_input06_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input06'
            node.tag_node_input06_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input06Value'
            
            with dpg.node_attribute(
                    tag=node.tag_node_input06_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_input06_value_name,
                    label="Colormap",
                    items=COLORMAP_NAMES,
                    default_value="JET",
                    width=small_window_w - 100,
                    callback=None,
                )

            # Add Blend Alpha slider for overlay transparency
            node.tag_node_input07_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input07'
            node.tag_node_input07_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input07Value'
            
            with dpg.node_attribute(
                    tag=node.tag_node_input07_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input07_value_name,
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

    node_label = 'Heatmap'
    node_tag = 'Heatmap'

    _min_val = 0
    _max_val = 255

    
    def __init__(self, opencv_setting_dict=None):
        super().__init__()

        if opencv_setting_dict is None:
            # Valeurs par défaut en cas de non-passage
            opencv_setting_dict = {
                'process_height': 400,
                'process_width': 600
            }

        self._opencv_setting_dict = opencv_setting_dict
        self.heatmap_accum = np.zeros((
            self._opencv_setting_dict['process_height'],
            self._opencv_setting_dict['process_width']
        ), dtype=np.float32)


    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_INT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_INT + ':Input05Value'
        input_value06_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input06Value'
        input_value07_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input07Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']


        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_INT:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = int(dpg_get_value(source_tag))
                input_value = max([self._min_val, input_value])
                input_value = min([self._max_val, input_value])
                dpg_set_value(destination_tag, input_value)
            
            elif connection_type == self.TYPE_IMAGE:

                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)

            else :
                print('Unknown connection type: ' + connection_type)


        frame = node_image_dict.get(connection_info_src, None)
        node_result = node_result_dict.get(connection_info_src, [])
        detections = node_result
        binary_threshold = dpg_get_value(input_value03_tag)
        decay = dpg_get_value(input_value04_tag)  # Get memory decay value
        blur_size = dpg_get_value(input_value05_tag)  # Get blur kernel size
        colormap_name = dpg_get_value(input_value06_tag)  # Get colormap name
        blend_alpha = dpg_get_value(input_value07_tag)  # Get blend alpha
        
        # Ensure blur_size is odd for GaussianBlur
        blur_size = ensure_odd_blur_size(blur_size)
        
        # Get colormap constant
        colormap = get_colormap(colormap_name)


        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        
        if frame is not None:
                bboxes = detections['bboxes']
                scores = detections['scores']

                # Update input image display
                input_texture = self.convert_cv_to_dpg(
                    frame,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(input_value01_tag, input_texture)

                # Frame heatmap (temporary)
                heatmap = np.zeros_like(self.heatmap_accum)

                for box, score in zip(bboxes, scores):
                    x1, y1, x2, y2 = map(int, box)
                    heatmap[y1:y2, x1:x2] += score

                # Accumulate with memory retention
                # Higher memory value = longer retention (0.98 retains 98% of previous values)
                self.heatmap_accum = self.heatmap_accum * decay + heatmap

                # Normalization with division by zero check
                if self.heatmap_accum.max() > 0:
                    heatmap_norm = np.clip(self.heatmap_accum / self.heatmap_accum.max(), 0, 1)
                else:
                    heatmap_norm = self.heatmap_accum
                heatmap_display = (heatmap_norm * 255).astype(np.uint8)
                heatmap_display = cv2.GaussianBlur(heatmap_display, (blur_size, blur_size), 0)
                colored_heatmap = cv2.applyColorMap(heatmap_display, colormap)

                # Overlay - blend with configurable alpha
                frame = cv2.addWeighted(frame, 1.0 - blend_alpha, colored_heatmap, blend_alpha, 0)


        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')


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
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_INT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_INT + ':Input05Value'
        input_value06_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input06Value'
        input_value07_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input07Value'


        #threshold_type = dpg_get_value(input_value02_tag)

        binary_threshold = dpg_get_value(input_value03_tag)
        decay = dpg_get_value(input_value04_tag)
        blur_size = dpg_get_value(input_value05_tag)
        colormap_name = dpg_get_value(input_value06_tag)
        blend_alpha = dpg_get_value(input_value07_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        #setting_dict[input_value02_tag] = threshold_type
        setting_dict[input_value03_tag] = binary_threshold
        setting_dict[input_value04_tag] = decay
        setting_dict[input_value05_tag] = blur_size
        setting_dict[input_value06_tag] = colormap_name
        setting_dict[input_value07_tag] = blend_alpha

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_INT + ':Input03Value'
        input_value04_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input04Value'
        input_value05_tag = tag_node_name + ':' + self.TYPE_INT + ':Input05Value'
        input_value06_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input06Value'
        input_value07_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input07Value'

        #threshold_type = setting_dict[input_value02_tag]
        binary_threshold = float(setting_dict[input_value03_tag])
        decay = setting_dict.get(input_value04_tag, 0.98)  # Default to 0.98 for backward compatibility
        blur_size = setting_dict.get(input_value05_tag, 25)  # Default to 25 for backward compatibility
        colormap_name = setting_dict.get(input_value06_tag, "JET")  # Default to JET for backward compatibility
        blend_alpha = setting_dict.get(input_value07_tag, 0.6)  # Default to 0.6 for backward compatibility

        #dpg_set_value(input_value02_tag, threshold_type)
        dpg_set_value(input_value03_tag, binary_threshold)
        dpg_set_value(input_value04_tag, decay)
        dpg_set_value(input_value05_tag, blur_size)
        dpg_set_value(input_value06_tag, colormap_name)
        dpg_set_value(input_value07_tag, blend_alpha)
