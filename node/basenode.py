#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import time
import os

import numpy as np
import dearpygui.dearpygui as dpg


from DLNode.object_detection.YOLOX.yolox import YOLOX
from DLNode.object_detection.YOLO.yolo import YOLO
from DLNode.object_detection.LightWeightPersonDetector.detector import LWPDetector
from DLNode.object_detection.FreeYOLO.freeyolo import FreeYOLO
from DLNode.object_detection.coco_class_names import coco_class_names
from DLNode.object_detection.coco_class_names_only_person import coco_class_names_only_person
from node.draw_node.draw_util.draw_util import draw_object_detection_info
import traceback


class DataType:
    TYPE_BOOLEAN = "BOOLEAN"
    TYPE_TEXT = "TEXT"
    TYPE_IMAGE = "IMAGE"
    TYPE_FLOAT = "FLOAT"
    TYPE_TIME_MS = "TIME_MS"
    TYPE_SOUND = "SOUND"


class PortType:
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"




_model_class = {
        'YOLOX-Nano(416x416)': YOLOX,
        'YOLOX-Tiny(416x416)': YOLOX,
        'YOLOX-S(640x640)': YOLOX,
        'Light-Weight Person Detector': LWPDetector,
        'YOLOX-Nano(416x416)': YOLOX,
        'FreeYOLO-Nano(640x640)': FreeYOLO,
        'FreeYOLO-Nano-CrowdHuman(640x640)': FreeYOLO,
        'YOLO11Nano': YOLO
    }



#_model_base_path = os.path.dirname(
#        os.path.abspath(__file__)) + '/object_detection/'


#_model_path_setting = {
#        'YOLOX-Nano(416x416)':
#        _model_base_path + 'YOLOX/model/yolox_nano.onnx',
#        'YOLOX-Tiny(416x416)':
#        _model_base_path + 'YOLOX/model/yolox_tiny.onnx',
#        'YOLOX-S(640x640)':
#        _model_base_path + 'YOLOX/model/yolox_s.onnx',
#        'YOLO11Nano' : _model_base_path + 'YOLO/model/yolo11_n.onnx',
#        'FreeYOLO-Nano(640x640)':
#        _model_base_path + 'FreeYOLO/model/yolo_free_nano_640x640.onnx',
#        'FreeYOLO-Nano-CrowdHuman(640x640)':
#        _model_base_path +
#        'FreeYOLO/model/yolo_free_nano_crowdhuman_640x640.onnx',
#         'Light-Weight Person Detector': 
#        _model_base_path +
#        'LightWeightPersonDetector/model/model.onnx'

#    }


#_model_class_name_list = {
#        'YOLOX-Nano(416x416)': coco_class_names,
#        'YOLOX-Tiny(416x416)': coco_class_names,
#        'YOLOX-S(640x640)': coco_class_names,
#        'Light-Weight Person Detector': coco_class_names_only_person,
#        'FreeYOLO-Nano(640x640)': coco_class_names,
#        'FreeYOLO-Nano-CrowdHuman(640x640)': coco_class_names_only_person,
#        'YOLO11Nano': coco_class_names
#    }



class Node:
    _ver = '0.0.1'
    node_label = 'BaseNode'
    node_tag = 'BaseNode'

    def __init__(self, node_id, connection_dict, opencv_setting_dict=None):
        self.id = self.generate_id()
        self.node_label = 'BaseNode'
        self.node_tag = 'BaseNode'
        self.tag_node_name = f"{node_id}:{self.node_tag}"

        # Générer les tags dynamiquement en fonction du dictionnaire
        self.tags = self.generate_tags(connection_dict)

        # Paramètres OpenCV
        self._opencv_setting_dict = opencv_setting_dict if opencv_setting_dict else {}
        self.small_window_w = self._opencv_setting_dict.get('process_width', 640)
        self.small_window_h = self._opencv_setting_dict.get('process_height', 480)
        self.use_pref_counter = self._opencv_setting_dict.get('use_pref_counter', False)
        self.use_gpu = self._opencv_setting_dict.get('use_gpu', False)



    def generate_id(self):
        return str(uuid.uuid4())



    def generate_tags(self, connection_dict):
        tags = {}

        # Parcours du dictionnaire pour générer les tags
        for index, connection_info in connection_dict.items():
            connection_type = connection_info.get("CONNECTION")
            data_type = connection_info.get("TYPE")
            
            if connection_type and data_type:
                if connection_type == "INPUT":
                    tags[f"{self.tag_node_name}:{data_type}:Input{index}"] = None
                    tags[f"{self.tag_node_name}:{data_type}:Input{index}Value"] = None
                elif connection_type == "OUTPUT":
                    tags[f"{self.tag_node_name}:{data_type}:Output{index}"] = None
                    tags[f"{self.tag_node_name}:{data_type}:Output{index}Value"] = None
        return tags



    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        pass



    def close(self, node_id):
        pass


    def get_setting_dict(self, node_id):
        self.tag_node_name = f"{node_id}:{self.node_tag}"
        # Assurez-vous que dpg.get_value est bien défini
        setting_dict = {}

        for tag, value in self.tags.items():
            setting_dict[tag] = dpg.get_value(tag)  # Exemple d'utilisation de dpg.get_value

        pos = dpg.get_item_pos(self.tag_node_name)

        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        self.tag_node_name = f"{node_id}:{self.node_tag}"

        # Mise à jour des tags selon les settings
        for tag, value in setting_dict.items():
            dpg.set_value(tag, value)  # Exemple d'utilisation de dpg.set_value






if __name__ == '__main__':
    node=Node()