#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from node.node_abc import DpgNodeABC
from collections import deque
import time 


class FactoryNode:
    node_label = 'Histogram'
    node_tag = 'Histogram'

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
        node = HistoNode()
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        node.tag_node_input01_name = f"{node.tag_node_name}:{node.TYPE_JSON}:Input01"
        node.tag_node_input01_value_name = f"{node.tag_node_name}:{node.TYPE_JSON}:Input01Value"
        node.tag_plot_container = f"{node.tag_node_name}:plot_container"
        node.tag_line_b = f"{node.tag_node_input01_value_name}:line_b"

        node._opencv_setting_dict = opencv_setting_dict or {}
        node.small_window_w = node._opencv_setting_dict.get('result_width', 240)
        node.small_window_h = node._opencv_setting_dict.get('result_height', 135)

        node._default_xdata = np.linspace(0, 255, 256)
        node._default_ydata = np.zeros(256)

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
                with dpg.group(horizontal=False):
                    # Boutons
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Réduire", callback=node.reset_plot_size)
                        dpg.add_button(label="Maximiser", callback=node.maximize_plot_size)


                    with dpg.child_window(
                     tag=node.tag_plot_container,
                     width=node.small_window_w,
                     height=node.small_window_h,
                     autosize_x=False,
                     autosize_y=False,
                     border=False
                         ):
                      with dpg.plot(
                        width=-1,
                        height=-1,
                        tag=node.tag_node_input01_value_name,
                        no_menus=True
                         ):
                          dpg.add_plot_legend(horizontal=True, location=dpg.mvPlot_Location_NorthEast)
                          dpg.add_plot_axis(dpg.mvXAxis,tag=f"{node.tag_node_input01_value_name}_xaxis")
                          dpg.set_axis_limits(dpg.last_item(), 0, 256)  # Limite adaptée à ta deque maxlen
                          dpg.add_plot_axis(dpg.mvYAxis,tag=f"{node.tag_node_input01_value_name}_yaxis")
                          dpg.add_bar_series(list(range(256)),[0]*256, label='Live Data',parent=f"{node.tag_node_input01_value_name}_yaxis",tag=node.tag_line_b)
        return node


class HistoNode(Node):
    _ver = '0.0.1'
    node_label = 'Histogram'
    node_tag = 'Histogram'

    def __init__(self):
        super().__init__()
        self.node_tag = self.node_tag
        self.node_label = self.node_label
        self._history = deque(maxlen=256)
        self.tag_node_name = ""
        self.tag_node_input01_value_name = ""
        self.tag_plot_container = ""
        self.tag_line_b = ""
        self._default_xdata = np.linspace(0, 255, 256)
        self._current_ydata = np.zeros(256)  # Histogramme initialisé à zéro
        self._update_index = 0  # Index de la valeur à mettre à jour
        #self._default_xdata = np.linspace(0, 255, 256)
        self._default_ydata = np.zeros(256)
        self._last_update_time = 0
        self.small_window_w = 240
        self.small_window_h = 135

    def maximize_plot_size(self):
        width = dpg.get_viewport_client_width()
        height = dpg.get_viewport_client_height()
        dpg.configure_item(self.tag_plot_container, width=width - 100, height=height - 200)
        dpg.set_item_pos(self.tag_node_name, [0, 0])

    def reset_plot_size(self):
        dpg.configure_item(self.tag_plot_container, width=self.small_window_w, height=self.small_window_h)
        dpg.set_item_pos(self.tag_node_name, [0, 0])

    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        tag_node_name = f"{node_id}:{self.node_tag}"
        tag_node_input01_value_name = f"{tag_node_name}:{self.TYPE_IMAGE}:Input01Value"
        affluence = 0
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                        clee = ":".join(connection_info[0].split(":")[0:2])
                        affluence = len(node_result_dict[clee]['class_ids'])
                        
        

        current_time = time.time()
        if current_time - self._last_update_time >= 1.0:  # toutes les secondes
            new_value = affluence
            self._history.append(new_value)
            self._last_update_time = current_time

            if dpg.does_item_exist(self.tag_line_b):
                x_data = list(range(len(self._history)))
                y_data = list(self._history)
                dpg.set_value(self.tag_line_b, [x_data, y_data])


        return {"image": None, "json": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = f"{node_id}:{self.node_tag}"
        pos = dpg.get_item_pos(tag_node_name)
        return {'ver': self._ver, 'pos': pos}

    def set_setting_dict(self, node_id, setting_dict):
        pass
