#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import time
import os

import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
#from node_editor.util import convert_cv_to_dpg


from node.basenode import Node

from node.DLNode.pose_estimation.movenet.movenet import (
    MoveNetSinglePoseLightning,
    MoveNetSinglePoseThunder,
    MoveNetMultiPoseLightning,
)
from node.DLNode.pose_estimation.mediapipe_hands.mediapipe_hands import (
    MediaPipeHandsComplexity0,
    MediaPipeHandsComplexity1,
)
from node.DLNode.pose_estimation.mediapipe_pose.mediapipe_pose import (
    MediaPipePoseComplexity0,
    MediaPipePoseComplexity1,
    MediaPipePoseComplexity2,
)

from node.DLNode.pose_estimation.tennis_keypoints.tennis_keypoints import tennis_keypoints 
from node.DLNode.pose_estimation.tennis_keypoints_2.tennis_keypoints_2 import tennis_keypoints_2
from src.utils.logging import get_logger
from src.utils.gpu_utils import get_execution_providers

logger = get_logger(__name__)


import random

class FactoryNode:
    node_label = 'PoseEstimation'
    node_tag = 'PoseEstimation'
    

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
        node.tag_node_name = str(node_id) + ':' + self.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':Input03Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

        node.tag_provider_select_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Provider'
        node.tag_provider_select_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':ProviderValue'

        # OpenCV
        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['process_width']
        node.small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']
        use_gpu = node._opencv_setting_dict['use_gpu']


        black_image = np.zeros((node.small_window_w, node.small_window_h, 3), dtype=np.uint8)
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


        logger.debug(f"Creating pose estimation node: {node.node_label}")
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
                    default_value='Input BGR image',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    list(node._model_class.keys()),
                    default_value=list(node._model_class.keys())[0],
                    width=node.small_window_w,
                    tag=node.tag_node_input02_value_name,
                )
            if use_gpu:
                # CPU/GPU
                with dpg.node_attribute(
                        tag=node.tag_provider_select_name,
                        attribute_type=dpg.mvNode_Attr_Static,
                ):
                    dpg.add_radio_button(
                        ("CPU", "GPU"),
                        tag=node.tag_provider_select_value_name,
                        default_value='CPU',
                        horizontal=True,
                    )

            with dpg.node_attribute(
                    tag=node.tag_node_input03_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_input03_value_name,
                    label="score",
                    width=node.small_window_w - 80,
                    default_value=0.3,
                    min_value=node._min_val,
                    max_value=node._max_val,
                    callback=None,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='Elapsed time(ms)',
                    )

            with dpg.node_attribute(
                        tag=node.tag_node_output_json_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output_json_value_name,
                        default_value='Pose Results',
                    )

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'PoseEstimation'
    node_tag = 'PoseEstimation'

    _min_val = 0.0
    _max_val = 1.0

    _opencv_setting_dict = None

    _model_class = {
        'MoveNet(SinglePose Lightning)': MoveNetSinglePoseLightning,
        'MoveNet(SinglePose Thunder)': MoveNetSinglePoseThunder,
        'MoveNet(MulitPose Lightning)': MoveNetMultiPoseLightning,
        'MediaPipe Hands(Complexity0)': MediaPipeHandsComplexity0,
        'MediaPipe Hands(Complexity1)': MediaPipeHandsComplexity1,
        'MediaPipe Pose(Complexity0)': MediaPipePoseComplexity0,
        'MediaPipe Pose(Complexity1)': MediaPipePoseComplexity1,
        'MediaPipe Pose(Complexity2)': MediaPipePoseComplexity2,
        'TennisKeyPoints': tennis_keypoints,
        'TennisKeyPoints_2': tennis_keypoints_2,
    }

    _model_base_path = os.path.dirname(os.path.abspath(__file__)) + '/pose_estimation/'
    _model_path_setting = {
        'MoveNet(SinglePose Lightning)':
        _model_base_path + 'movenet/model/movenet_singlepose_lightning_4.onnx',
        'MoveNet(SinglePose Thunder)':
        _model_base_path + 'movenet/model/movenet_singlepose_thunder_4.onnx',
        'MoveNet(MulitPose Lightning)':
        _model_base_path + 'movenet/model/movenet_multipose_lightning_1.onnx',
        'TennisKeyPoints': _model_base_path + 'tennis_keypoints/model/tennis.onnx',
        'TennisKeyPoints_2': _model_base_path + 'tennis_keypoints_2/model/tennis_old.onnx',
        'MediaPipe Hands(Complexity0)': None,
        'MediaPipe Hands(Complexity1)': None,
        'MediaPipe Pose(Complexity0)': None,
        'MediaPipe Pose(Complexity1)': None,
        'MediaPipe Pose(Complexity2)': None,
    }

    _model_instance = {}

    def __init__(self):
        super().__init__()



    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        self.input_value02_tag = self.tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        self.input_value03_tag = self.tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        self.output_value01_tag = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        self.output_value02_tag = self.tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        tag_provider_select_value_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':ProviderValue'

        self.small_window_w = self._opencv_setting_dict['process_width']
        self.small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']
        use_gpu = self._opencv_setting_dict['use_gpu']


        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_FLOAT:

                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'

                input_value = round(float(dpg_get_value(source_tag)), 3)
                input_value = max([self._min_val, input_value])
                input_value = min([self._max_val, input_value])
                dpg_set_value(destination_tag, input_value)
            if connection_type == self.TYPE_IMAGE:

                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)


        frame = node_image_dict.get(connection_info_src, None)


        score_th = round(float(dpg_get_value(self.input_value03_tag)), 3)


        provider = 'CPU'
        if use_gpu:
        	provider = dpg_get_value(tag_provider_select_value_name)


        model_name = dpg_get_value(self.input_value02_tag)
        model_path = self._model_path_setting[model_name]
        model_class = self._model_class[model_name]

        model_name_with_provider = model_name + '_' + provider


        if frame is not None:
            if model_name_with_provider not in self._model_instance:
                if provider == 'CPU':
                    providers = ['CPUExecutionProvider']
                    self._model_instance[
                        model_name_with_provider] = model_class(
                            model_path,
                            providers=providers,
                        )
                else:
                    self._model_instance[
                        model_name_with_provider] = model_class(model_path)


        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        result = {}
        debug_frame = None
        if frame is not None:
            results_list = self._model_instance[model_name_with_provider](
                frame)
            result['model_name'] = model_name
            result['score_th'] = score_th
            result['results_list'] = results_list


        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(self.output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')


        if frame is not None:
            debug_frame = copy.deepcopy(frame)
            debug_frame = self.draw_pose_estimation_info(
                model_name,
                debug_frame,
                results_list,
                score_th,
            )

            # Use cached texture conversion for better performance
            texture = self.convert_cv_to_dpg_cached(
                debug_frame,
                self.small_window_w,
                self.small_window_h,
            )
            dpg_set_value(self.output_value01_tag, texture)

        return {"image": debug_frame if debug_frame is not None else frame, "json": result, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'


        model_name = dpg_get_value(input_value02_tag)

        score_th = round(float(dpg_get_value(input_value03_tag)), 3)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = model_name
        setting_dict[input_value03_tag] = score_th

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'

        model_name = setting_dict[input_value02_tag]
        score_th = setting_dict[input_value03_tag]

        dpg_set_value(input_value02_tag, model_name)
        dpg_set_value(input_value03_tag, score_th)
