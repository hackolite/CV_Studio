#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import copy

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
#from node_editor.util import self.convert_cv_to_dpg
#from node.draw_node.draw_util.draw_util import draw_info
from node.basenode import Node

def create_concat_image(frame_dict, slot_num):
    if slot_num == 1:
        frame = frame_dict[0]
        display_frame = copy.deepcopy(frame)
    

    elif slot_num == 2:
        frame = cv2.hconcat([frame_dict[0], frame_dict[1]])

        bg_image = np.zeros(
            (frame.shape[0] * 2, frame.shape[1], 3)).astype(np.uint8)
        bg_image[int(frame.shape[0] / 2):int(frame.shape[0] / 2) +
                 frame.shape[0], 0:frame.shape[1]] = frame

        display_frame = copy.deepcopy(bg_image)
   

    elif slot_num == 3 or slot_num == 4:
        hconcat_image01 = cv2.hconcat([frame_dict[0], frame_dict[1]])
        hconcat_image02 = cv2.hconcat([frame_dict[2], frame_dict[3]])
        frame = cv2.vconcat([hconcat_image01, hconcat_image02])
        display_frame = copy.deepcopy(frame)
    

    elif slot_num == 5 or slot_num == 6:
        hconcat_image01 = cv2.hconcat([frame_dict[0], frame_dict[1]])
        hconcat_image01 = cv2.hconcat([hconcat_image01, frame_dict[2]])
        hconcat_image02 = cv2.hconcat([frame_dict[3], frame_dict[4]])
        hconcat_image02 = cv2.hconcat([hconcat_image02, frame_dict[5]])
        frame = cv2.vconcat([hconcat_image01, hconcat_image02])
        display_frame = copy.deepcopy(frame)
    

    elif slot_num == 7 or slot_num == 8 or slot_num == 9:
        hconcat_image01 = cv2.hconcat([frame_dict[0], frame_dict[1]])
        hconcat_image01 = cv2.hconcat([hconcat_image01, frame_dict[2]])
        hconcat_image02 = cv2.hconcat([frame_dict[3], frame_dict[4]])
        hconcat_image02 = cv2.hconcat([hconcat_image02, frame_dict[5]])
        hconcat_image03 = cv2.hconcat([frame_dict[6], frame_dict[7]])
        hconcat_image03 = cv2.hconcat([hconcat_image03, frame_dict[8]])
        vconcat_image = cv2.vconcat([hconcat_image01, hconcat_image02])
        frame = cv2.vconcat([vconcat_image, hconcat_image03])
        display_frame = copy.deepcopy(frame)

    return frame, display_frame

class FactoryNode:
    node_label = 'ImageConcat'
    node_tag = 'ImageConcat'
    

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


        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']


        black_image = np.zeros((small_window_w, small_window_h, 3))
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


        if node.tag_node_name not in node._slot_id:
            node._slot_id[node.tag_node_name] = 1


        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

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
            # スロット
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
    _ver = '0.0.1'

    node_label = 'ImageConcat'
    node_tag = 'ImageConcat'

    _opencv_setting_dict = None

    _max_slot_number = 9
    _slot_id = {}

    def __init__(self):
        pass

    def draw_classification_info(
        self,
        image,
        class_ids,
        class_scores,
        class_names,
    ):
        """
        Override base class method to display classification results
        bigger and at the bottom left of the image.
        """
        debug_image = copy.deepcopy(image)
        height, width = debug_image.shape[:2]
        
        # Define colors for top 5 positions (BGR format) - matching node_classification.py
        rank_colors = [
            (0, 0, 255),      # Position 1 (index 0): Red (highest score)
            (0, 255, 255),    # Position 2 (index 1): Yellow
            (255, 0, 0),      # Position 3 (index 2): Blue
            (255, 0, 128),    # Position 4 (index 3): Violet
            (255, 0, 255),    # Position 5 (index 4): Magenta
        ]
        
        # Scale text parameters based on frame height (reference: 480px)
        # This ensures text size is appropriate for the actual frame size
        scale_factor = height / 480.0
        font_scale = 1.0 * scale_factor  # Base 1.0, scaled by frame height
        thickness = max(1, int(3 * scale_factor))  # Base 3, scaled and min 1
        line_spacing = int(35 * scale_factor)  # Base 35, scaled by frame height
        
        # Calculate starting position from bottom
        num_lines = len(class_ids)
        start_y = height - 15 - (num_lines - 1) * line_spacing
        
        for index, (class_score, class_id) in enumerate(zip(class_scores, class_ids)):
            score = "%.2f" % class_score
            text = "%s:%s(%s)" % (str(class_id), str(class_names[int(class_id)]), score)
            
            # Select color based on position
            if index < len(rank_colors):
                color = rank_colors[index]
            else:
                color = (0, 255, 0)  # Default green for lower rankings
            
            # Position at bottom left
            y_position = start_y + (index * line_spacing)
            
            debug_image = cv2.putText(
                debug_image,
                text,
                (15, y_position),  # Bottom left position (x=15 for margin)
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                color,
                thickness=thickness,
            )

        return debug_image


    def create_image_dict(
            self,
            slot_num,
            connection_info_src_dict,
            node_image_dict,
            node_result_dict,
            image_node_name,
            resize_width,
            resize_height,
            draw_info_on_result,
        ):
            frame_exist_flag = False

            black_image = np.zeros((resize_height, resize_width, 3)).astype(np.uint8)

            frame_dict = {}
            for index in range(slot_num - 1, -1, -1):
                node_id_name = connection_info_src_dict.get(index, None)
                frame = copy.deepcopy(node_image_dict.get(node_id_name, None))
                if frame is not None:
                    if draw_info_on_result:
                        node_result = node_result_dict[node_id_name]
                        image_node_name = node_id_name.split(':')[1]
                        frame = self.draw_info(image_node_name, node_result, frame)
                    resize_frame = cv2.resize(frame, (resize_width, resize_height))
                    frame_dict[slot_num - index - 1] = copy.deepcopy(resize_frame)

                    frame_exist_flag = True
                else:
                    frame_dict[slot_num - index - 1] = copy.deepcopy(black_image)

            display_num_list = [1, 2, 4, 4, 6, 6, 9, 9, 9]
            for index in range(display_num_list[slot_num - 1]):
                if frame_dict.get(index, None) is None:
                    frame_dict[index] = copy.deepcopy(black_image)

            if not frame_exist_flag:
                frame_dict = None

            return frame_dict



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
        resize_width = self._opencv_setting_dict['result_width']
        resize_height = self._opencv_setting_dict['result_height']
        draw_info_on_result = self._opencv_setting_dict['draw_info_on_result']


        node_name_dict = {}
        connection_info_src = ''
        connection_info_src_dict = {}
        for connection_info in connection_list:

            slot_number = re.sub(r'\D', '', connection_info[1].split(':')[-1])
            if slot_number == '':
                continue
            slot_number = int(slot_number) - 1

            connection_type = connection_info[0].split(':')[2]
            print("type :", connection_type)
            if connection_type == self.TYPE_IMAGE:

                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                node_name = connection_info_src[1]
                connection_info_src = ':'.join(connection_info_src)

                node_name_dict[slot_number] = node_name
                connection_info_src_dict[slot_number] = connection_info_src

        slot_num = self._slot_id[self.tag_node_name]


        frame_dict = {}
        if len(connection_info_src_dict) > 0:
            frame_dict = self.create_image_dict(
                slot_num,
                connection_info_src_dict,
                node_image_dict,
                node_result_dict,
                node_name,
                resize_width,
                resize_height,
                draw_info_on_result,
            )


        frame = None
        display_frame = None
        if len(connection_info_src_dict) > 0 and frame_dict is not None:
            frame, display_frame = create_concat_image(frame_dict, slot_num)

        print("display :", display_frame)
        if display_frame is not None:
            texture = self.convert_cv_to_dpg(
                display_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(self.output_value01_tag, texture)


        return {"image" : frame, "json" : None, "audio" : None}

    def close(self, node_id):
        pass


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




    def draw_info(self, node_name, node_result, image):
        # need some abstraction here
        print("node name :", node_name, "node_result :", node_result)
        classification_nodes = ['Classification']
        object_detection_nodes = ['ObjectDetection']
        semantic_segmentation_nodes = ['SemanticSegmentation']
        pose_estimation_nodes = ['PoseEstimation']
        face_detection_nodes = ['FaceDetection']
        multi_object_tracking_nodes = ['MultiObjectTracking']
        qr_code_detection_nodes = ['QRCodeDetection']

        debug_image = copy.deepcopy(image)
        if node_name in classification_nodes:
            use_object_detection = node_result.get('use_object_detection', [])
            class_ids = node_result.get('class_ids', [])
            class_scores = node_result.get('class_scores', [])
            class_names = node_result.get('class_names', [])

            if use_object_detection:
                od_bboxes = node_result.get('od_bboxes', [])
                od_scores = node_result.get('od_scores', [])
                od_class_ids = node_result.get('od_class_ids', [])
                od_class_names = node_result.get('od_class_names', [])
                od_score_th = node_result.get('od_score_th', [])
                debug_image = self.draw_classification_with_od_info(
                    debug_image,
                    class_ids,
                    class_scores,
                    class_names,
                    od_bboxes,
                    od_scores,
                    od_class_ids,
                    od_class_names,
                    od_score_th,
                    thickness=3,
                )
            else:
                debug_image = self.draw_classification_info(
                    debug_image,
                    class_ids,
                    class_scores,
                    class_names,
                )
        elif node_name in object_detection_nodes:
            bboxes = node_result.get('bboxes', [])
            scores = node_result.get('scores', [])
            class_ids = node_result.get('class_ids', [])
            class_names = node_result.get('class_names', [])
            score_th = node_result.get('score_th', [])
            debug_image = self.draw_object_detection_info(
                debug_image,
                score_th,
                bboxes,
                scores,
                class_ids,
                class_names,
            )
        elif node_name in semantic_segmentation_nodes:
            class_num = node_result.get('class_num', [])
            segmentation_map = node_result.get('segmentation_map', [])
            score_th = node_result.get('score_th', [])
            debug_image = self.draw_semantic_segmentation_info(
                debug_image,
                score_th,
                class_num,
                segmentation_map,
            )
        elif node_name in pose_estimation_nodes:
            model_name = node_result.get('model_name', [])
            results_list = node_result.get('results_list', [])
            score_th = node_result.get('score_th', [])
            debug_image = self.draw_pose_estimation_info(
                model_name,
                debug_image,
                results_list,
                score_th,
            )
        elif node_name in face_detection_nodes:
            model_name = node_result.get('model_name', [])
            results_list = node_result.get('results_list', [])
            score_th = node_result.get('score_th', [])
            debug_image = self.draw_face_detection_info(
                model_name,
                debug_image,
                results_list,
                score_th,
            )
        elif node_name in multi_object_tracking_nodes:
            track_ids = node_result.get('track_ids', [])
            bboxes = node_result.get('bboxes', [])
            scores = node_result.get('scores', [])
            class_ids = node_result.get('class_ids', [])
            class_names = node_result.get('class_names', [])
            track_id_dict = node_result.get('track_id_dict', [])
            debug_image = self.draw_multi_object_tracking_info(
                debug_image,
                track_ids,
                bboxes,
                scores,
                class_ids,
                class_names,
                track_id_dict,
            )
        return debug_image
