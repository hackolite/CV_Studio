#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import time
import os

import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node_editor.util import convert_cv_to_dpg
from node.deep_learning_node.object_detection.YOLOX.yolox import YOLOX
from node.deep_learning_node.object_detection.YOLO.yolo import YOLO
from node.deep_learning_node.object_detection.LightWeightPersonDetector.detector import LWPDetector
from node.deep_learning_node.object_detection.FreeYOLO.freeyolo import FreeYOLO
from node.deep_learning_node.object_detection.coco_class_names import coco_class_names
from node.deep_learning_node.object_detection.coco_class_names_only_person import coco_class_names_only_person
from node.draw_node.draw_util.draw_util import draw_object_detection_info
import traceback





_model_base_path = os.path.dirname(
    os.path.abspath(__file__)) + '/object_detection/'


# Combinaison de tous les dictionnaires en un seul dictionnaire _model_info
_model_info = {
    'YOLOX-Nano(416x416)': {
        'model': YOLOX,
        'model_path': _model_base_path + 'YOLOX/model/yolox_nano.onnx',
        'class_names': coco_class_names
    },
    'YOLOX-Tiny(416x416)': {
        'model': YOLOX,
        'model_path': _model_base_path + 'YOLOX/model/yolox_tiny.onnx',
        'class_names': coco_class_names
    },
    'YOLOX-S(640x640)': {
        'model': YOLOX,
        'model_path': _model_base_path + 'YOLOX/model/yolox_s.onnx',
        'class_names': coco_class_names
    },
    'YOLO11Nano': {
        'model': YOLO,
        'model_path': _model_base_path + 'YOLO/model/yolo11_n.onnx',
        'class_names': coco_class_names
    },
    'FreeYOLO-Nano(640x640)': {
        'model': FreeYOLO,
        'model_path': _model_base_path + 'FreeYOLO/model/yolo_free_nano_640x640.onnx',
        'class_names': coco_class_names
    },
    'FreeYOLO-Nano-CrowdHuman(640x640)': {
        'model': FreeYOLO,
        'model_path': _model_base_path + 'FreeYOLO/model/yolo_free_nano_crowdhuman_640x640.onnx',
        'class_names': coco_class_names_only_person
    },
    'Light-Weight Person Detector': {
        'model': LWPDetector,
        'model_path': _model_base_path + 'LightWeightPersonDetector/model/model.onnx',
        'class_names': coco_class_names_only_person
    }
}



class ObjectDetectionNode:
    _ver = '0.0.1'

    node_label = 'ObjectDetection'
    node_tag = 'ObjectDetection'

    _min_val = 0.0
    _max_val = 1.0

    _opencv_setting_dict = None



    _model_base_path = os.path.dirname(
        os.path.abspath(__file__)) + '/object_detection/'


    # Chemin de base pour les modèles
    _model_base_path = os.path.dirname(os.path.abspath(__file__)) + '/object_detection/'





    _model_instance = {}

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

        self.tag_node_name = str(node_id) + ':' + self.node_tag
        
        self.tag_node_input_image_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Input01'
        self.tag_node_input_image_value_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'
        
        self.tag_node_input_text_name = self.tag_node_name + ':' + self.TYPE_TEXT + ':Input02'
        self.tag_node_input_text_value_name = self.tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        

        self.tag_node_input_float_name = self.tag_node_name + ':' + self.TYPE_FLOAT + ':Input03'
        self.tag_node_input_float_value_name = self.tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'
        

        self.tag_node_output_image_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Output01'
        self.tag_node_output_image = self.tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        self.tag_node_output_result_name = self.tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02'
        self.tag_node_output_result = self.tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        self.tag_provider_select_name = self.tag_node_name + ':' + self.TYPE_TEXT + ':Provider'
        self.tag_provider_select_value_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':ProviderValue'
        self._opencv_setting_dict = opencv_setting_dict
        

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']
        use_gpu = self._opencv_setting_dict['use_gpu']


        black_image = np.zeros((small_window_w, small_window_h, 3))
        black_texture = convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )


        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=self.tag_node_output_image,
                format=dpg.mvFormat_Float_rgb,
            )


        with dpg.node(
                tag=self.tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=self.tag_node_input_image_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=self.tag_node_input_image_value_name,
                    default_value='Input BGR image',
                )

            with dpg.node_attribute(
                    tag=self.tag_node_output_image_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(self.tag_node_output_image)

            with dpg.node_attribute(
                    tag=self.tag_node_input_text_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    list(self._model_class.keys()),
                    default_value=list(self._model_class.keys())[0],
                    width=small_window_w,
                    tag=self.tag_node_input_text_value_name,
                )
            if use_gpu:

                with dpg.node_attribute(
                        tag=self.tag_provider_select_name,
                        attribute_type=dpg.mvNode_Attr_Static,
                ):
                    dpg.add_radio_button(
                        ("CPU", "GPU"),
                        tag=self.tag_provider_select_value_name,
                        default_value='CPU',
                        horizontal=True,
                    )

            with dpg.node_attribute(
                    tag=self.tag_node_input_float_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_float(
                    tag=self.tag_node_input_float_value_name,
                    label="score",
                    width=small_window_w - 80,
                    default_value=0.3,
                    min_value=self._min_val,
                    max_value=self._max_val,
                    callback=None,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=self.tag_node_output_result_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=self.tag_node_output_result,
                        default_value='elapsed time(ms)',
                    )
        return self.tag_node_name

    def update(self, node_id, connection_list, node_image_dict, node_result_dict,):
            try:
                self.tag_node_name = str(node_id) + ':' + self.node_tag

                self.tag_provider_select_value_name = self.tag_node_name + ':' + self.TYPE_IMAGE + ':ProviderValue'

                small_window_w = self._opencv_setting_dict['process_width']
                small_window_h = self._opencv_setting_dict['process_height']
                use_pref_counter = self._opencv_setting_dict['use_pref_counter']
                use_gpu = self._opencv_setting_dict['use_gpu']


                connection_info_src = ''
                for connection_info in connection_list:
                    connection_type = connection_info[0].split(':')[2]
                    if connection_type == self.TYPE_FLOAT:

                        source_tag = connection_info[0] + 'Value'
                        destination_tag = connection_info[1] + 'Value'
                        print("source :", source_tag, "destination :", destination_tag)
                        input_value = round(float(dpg_get_value(source_tag)), 3)
                        input_value = max([self._min_val, input_value])
                        input_value = min([self._max_val, input_value])
                        dpg_set_value(destination_tag, input_value)
                    if connection_type == self.TYPE_IMAGE:
                        connection_info_src = connection_info[0]
                        connection_info_src = connection_info_src.split(':')[:2]
                        connection_info_src = ':'.join(connection_info_src)
                        print(connection_info_src)

                frame = node_image_dict.get(connection_info_src, None)


                score_th = round(float(dpg_get_value(self.tag_node_input_float_value_name)), 3)


                provider = 'CPU'
                if use_gpu:
                    provider = dpg_get_value(self.tag_provider_select_value_name)

                print(self.tag_node_input_text_value_name)
                model_name = dpg_get_value(self.tag_node_input_text_value_name)
                print(model_name)

                model_path = self._model_path_setting[model_name]
                model_class = self._model_class[model_name]
                class_name_dict = self._model_class_name_list[model_name]

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
                    start_time = time.perf_counter()

                result = {}
                if frame is not None:

                    bboxes, scores, class_ids = self._model_instance[
                        model_name_with_provider](frame)
                    if len(bboxes) > 0:
                        result['bboxes'] = bboxes.tolist()
                        result['scores'] = scores.tolist()
                        result['class_ids'] = class_ids.tolist()
                        result['class_names'] = class_name_dict
                        result['score_th'] = score_th
                    else:
                        result['bboxes'] = []
                        result['scores'] = []
                        result['class_ids'] = []
                        result['class_names'] = class_name_dict
                        result['score_th'] = score_th


                if frame is not None and use_pref_counter:
                    elapsed_time = time.perf_counter() - start_time
                    elapsed_time = int(elapsed_time * 1000)
                    dpg_set_value(self.tag_node_output_result,
                                  str(elapsed_time).zfill(4) + 'ms')


                if frame is not None:
                    debug_frame = copy.deepcopy(frame)
                    debug_frame = draw_object_detection_info(
                        debug_frame,
                        score_th,
                        bboxes,
                        scores,
                        class_ids,
                        class_name_dict,
                    )
                    texture = convert_cv_to_dpg(
                        debug_frame,
                        small_window_w,
                        small_window_h,
                    )
                    dpg_set_value(self.tag_node_output_image, texture)

                try:
                    print("frame :", frame.shape)
                except:
                    pass
                return frame, result
            except Exception as e:
                    error_trace = traceback.format_exc()  # Récupère la stack trace sous forme de string
                    print("Stack Trace :\n", error_trace)


    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = self.tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = self.tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'


        model_name = dpg_get_value(input_value02_tag)

        score_th = round(float(dpg_get_value(input_value03_tag)), 3)

        pos = dpg.get_item_pos(self.tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = model_name
        setting_dict[input_value03_tag] = score_th

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        self.tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = self.tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        input_value03_tag = self.tag_node_name + ':' + self.TYPE_FLOAT + ':Input03Value'

        model_name = setting_dict[input_value02_tag]
        score_th = setting_dict[input_value03_tag]

        dpg_set_value(self.tag_node_input_text_value_name, model_name)
        dpg_set_value(self.tag_node_input_float_value_name, score_th)




