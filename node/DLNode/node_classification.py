#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import time
import os

import numpy as np
import cv2
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC

from node.DLNode.classification.MobileNetV3.mobilenet_v3 import MobileNetV3
from node.DLNode.classification.EfficientNetB0.efficientnet import EfficientNetB0
from node.DLNode.classification.ResNet50.resnet50 import ResNet50

# Import YoloCls using importlib.util due to hyphenated directory name
import importlib.util
from src.utils import resource_path

_yolo_cls_init_path = resource_path(
    'node/DLNode/classification/Yolo-cls/__init__.py'
)
_yolo_cls_spec = importlib.util.spec_from_file_location(
    'yolo_cls_init_module', _yolo_cls_init_path
)
_yolo_cls_module = importlib.util.module_from_spec(_yolo_cls_spec)
_yolo_cls_spec.loader.exec_module(_yolo_cls_module)
YoloCls = _yolo_cls_module.YoloCls

from node.DLNode.classification.imagenet_class_names import imagenet_class_names
from node.DLNode.classification.esc50_class_names import esc50_class_names

from node.basenode import Node


class FactoryNode:
    node_label = 'Classification'
    node_tag = 'Classification'
    

    def __init__(self):
        pass

    
    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Adds a node to the processing graph."""
        node = Node()
        
        # タグ名
        tag_node_name = str(node_id) + ':' + node.node_tag
        tag_node_input01_name = tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        tag_node_input01_value_name = tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        tag_node_input02_name = tag_node_name + ':' + node.TYPE_TEXT + ':Input02'
        tag_node_input02_value_name = tag_node_name + ':' + node.TYPE_TEXT + ':Input02Value'
        tag_node_output01_name = tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        tag_node_output02_name = tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        tag_node_output02_value_name = tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        tag_node_output_json_name = tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        tag_node_output_json_value_name = tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        tag_provider_select_name = tag_node_name + ':' + node.TYPE_TEXT + ':Provider'
        tag_provider_select_value_name = tag_node_name + ':' + node.TYPE_IMAGE + ':ProviderValue'

        # OpenCV向け設定
        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']
        use_gpu = node._opencv_setting_dict['use_gpu']

        # 初期化用黒画像
        black_image = np.zeros((small_window_w, small_window_h, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        # テクスチャ登録
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Create yellow theme for JSON button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # ノード
        with dpg.node(
                tag=tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # 入力端子
            with dpg.node_attribute(
                    tag=tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=tag_node_input01_value_name,
                    default_value='Input BGR image',
                )
            # 画像
            with dpg.node_attribute(
                    tag=tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(tag_node_output01_value_name)
            # 使用アルゴリズム
            with dpg.node_attribute(
                    tag=tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    list(node._model_class.keys()),
                    default_value=list(node._model_class.keys())[0],
                    width=small_window_w,
                    tag=tag_node_input02_value_name,
                )
            if use_gpu:
                # CPU/GPU切り替え
                with dpg.node_attribute(
                        tag=tag_provider_select_name,
                        attribute_type=dpg.mvNode_Attr_Static,
                ):
                    dpg.add_radio_button(
                        ("CPU", "GPU"),
                        tag=tag_provider_select_value_name,
                        default_value='CPU',
                        horizontal=True,
                    )
            # 処理時間
            if use_pref_counter:
                with dpg.node_attribute(
                        tag=tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

            # JSON output button
            with dpg.node_attribute(
                    tag=tag_node_output_json_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="JSON",
                    tag=tag_node_output_json_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)

        node.tag_node_name = tag_node_name
        return node



class Node(Node):
    _ver = '0.0.1'

    node_label = 'Classification'
    node_tag = 'Classification'

    _opencv_setting_dict = None

    # モデル設定
    _model_class = {
        'MobileNetV3 Small': MobileNetV3,
        'MobileNetV3 Large': MobileNetV3,
        'EfficientNet B0': EfficientNetB0,
        'ResNet50': ResNet50,
        'Yolo-cls': YoloCls,
    }
    _model_path_setting = {
        'MobileNetV3 Small':
        resource_path('node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx'),
        'MobileNetV3 Large':
        resource_path('node/DLNode/classification/MobileNetV3/model/MobileNetV3Large.onnx'),
        'EfficientNet B0':
        resource_path('node/DLNode/classification/EfficientNetB0/model/EfficientNetB0.onnx'),
        'ResNet50':
        resource_path('node/DLNode/classification/ResNet50/model/ResNet50.onnx'),
        'Yolo-cls':
        resource_path('node/DLNode/classification/Yolo-cls/model/son.onnx'),
    }
    _model_class_name_dict = {
        'MobileNetV3 Small': imagenet_class_names,
        'MobileNetV3 Large': imagenet_class_names,
        'EfficientNet B0': imagenet_class_names,
        'ResNet50': imagenet_class_names,
        'Yolo-cls': esc50_class_names,
    }

    _model_instance = {}
    _class_name_dict = None

    def __init__(self):
        pass

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        tag_provider_select_value_name = tag_node_name + ':' + self.TYPE_IMAGE + ':ProviderValue'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']
        use_gpu = self._opencv_setting_dict['use_gpu']

        # 接続情報確認
        src_node_name = ''
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_INT:
                # 接続タグ取得
                source_tag = connection_info[0] + 'Value'
                destination_tag = connection_info[1] + 'Value'
                # 値更新
                input_value = int(dpg_get_value(source_tag))
                input_value = max([self._min_val, input_value])
                input_value = min([self._max_val, input_value])
                dpg_set_value(destination_tag, input_value)
            if connection_type == self.TYPE_IMAGE or connection_type == self.TYPE_AUDIO:
                # 画像取得元のノード名(ID付き)を取得
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                src_node_name = connection_info_src[1]
                connection_info_src = ':'.join(connection_info_src)

        # 画像取得
        frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)

        # CPU/GPU選択状態取得
        provider = 'CPU'
        if use_gpu:
            provider = dpg_get_value(tag_provider_select_value_name)

        # モデル情報取得
        model_name = dpg_get_value(input_value02_tag)
        model_path = self._model_path_setting[model_name]
        model_class = self._model_class[model_name]

        class_name_dict = self._model_class_name_dict[model_name]

        model_name_with_provider = model_name + '_' + provider

        # モデル取得
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

        # 計測開始
        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # 接続元がObjectDetectionノードの場合、各バウンディングボックスに対して推論
        result = {}
        frame_list, class_id_list, score_list = [], [], []
        od_target_bboxes = []
        od_target_scores = []
        od_target_class_ids = []
        if frame is not None:
            if src_node_name == 'ObjectDetection':
                # 物体検出情報取得
                node_result = node_result_dict.get(connection_info_src, [])
                od_bboxes = node_result.get('bboxes', [])
                od_scores = node_result.get('scores', [])
                od_class_ids = node_result.get('class_ids', [])
                od_class_names = node_result.get('class_names', [])
                od_score_th = node_result.get('score_th', [])

                # バウンディングボックスで切り抜き
                for od_bbox, od_score, od_class_id in zip(
                        od_bboxes, od_scores, od_class_ids):
                    x1, y1 = int(od_bbox[0]), int(od_bbox[1])
                    x2, y2 = int(od_bbox[2]), int(od_bbox[3])

                    if od_score_th > od_score:
                        continue

                    frame_list.append(copy.deepcopy(frame[y1:y2, x1:x2]))
                    od_target_bboxes.append([x1, y1, x2, y2])
                    od_target_scores.append(od_score)
                    od_target_class_ids.append(od_class_id)

                # 各バウンディングボックスに対しClassification推論
                for temp_frame in frame_list:
                    class_scores, class_ids = self._model_instance[
                        model_name_with_provider](temp_frame)
                    score_list.append(class_scores[0])
                    class_id_list.append(class_ids[0])
                result['use_object_detection'] = True
                result['class_ids'] = class_id_list
                result['class_scores'] = score_list
                result['class_names'] = class_name_dict
                result['od_bboxes'] = od_target_bboxes
                result['od_scores'] = od_target_scores
                result['od_class_ids'] = od_target_class_ids
                result['od_class_names'] = od_class_names
                result['od_score_th'] = od_score_th
            else:
                class_scores, class_ids = self._model_instance[
                    model_name_with_provider](frame)
                result['use_object_detection'] = False
                result['class_ids'] = class_ids.tolist()
                result['class_scores'] = class_scores.tolist()
                result['class_names'] = class_name_dict

        # 計測終了
        if frame is not None and use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')

        # 描画
        output_frame = frame
        if frame is not None:
            # Create debug_frame with original dimensions for output
            debug_frame = copy.deepcopy(frame)
            
            # Draw labels on the original frame
            if result['use_object_detection']:
                debug_frame = self.draw_classification_with_od_info(
                    debug_frame,
                    result['class_ids'],
                    result['class_scores'],
                    result['class_names'],
                    result['od_bboxes'],
                    result['od_scores'],
                    result['od_class_ids'],
                    result['od_class_names'],
                    result['od_score_th'],
                )
            else:
                debug_frame = self.draw_classification_info(
                    debug_frame,
                    result['class_ids'],
                    result['class_scores'],
                    result['class_names'],
                )
            
            output_frame = debug_frame

            texture = self.convert_cv_to_dpg(
                debug_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": output_frame, "json": result, "audio": None}

    def close(self, node_id):
        pass
    
    def draw_classification_info(
        self,
        image,
        class_ids,
        class_scores,
        class_names,
    ):
        """
        Override base class method to add color differentiation based on ranking.
        Position 1 (index 0, highest score): Red
        Position 2 (index 1): Yellow
        Position 3 (index 2): Blue
        Position 4 (index 3): Violet
        Position 5 (index 4): Magenta
        """
        debug_image = copy.deepcopy(image)
        
        # Define colors for top 5 positions (BGR format)
        rank_colors = [
            (0, 0, 255),      # Position 1 (index 0): Red (highest score)
            (0, 255, 255),    # Position 2 (index 1): Yellow
            (255, 0, 0),      # Position 3 (index 2): Blue
            (255, 0, 128),    # Position 4 (index 3): Violet (purple-ish)
            (255, 0, 255),    # Position 5 (index 4): Magenta
        ]
        
        for index, (class_score, class_id) in enumerate(zip(class_scores, class_ids)):
            score = "%.2f" % class_score
            text = "%s:%s(%s)" % (str(class_id), str(class_names[int(class_id)]), score)
            
            # Select color based on position (1, 2, 3, 4, 5)
            # Use default green for positions beyond 5
            if index < len(rank_colors):
                color = rank_colors[index]
            else:
                color = (0, 255, 0)  # Default green for lower rankings
            
            debug_image = cv2.putText(
                debug_image,
                text,
                (15, 25 + (index * 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                thickness=2,
            )

        return debug_image

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'

        # 選択モデル
        model_name = dpg_get_value(input_value02_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[input_value02_tag] = model_name

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value02_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input02Value'

        model_name = setting_dict[input_value02_tag]

        dpg_set_value(input_value02_tag, model_name)
