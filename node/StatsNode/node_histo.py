#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from node.node_abc import DpgNodeABC


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
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_plot_container = node.tag_node_name + ':plot_container'

        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['result_width']
        node.small_window_h = node._opencv_setting_dict['result_height']

        node._default_xdata = np.linspace(0, 256 - 1, 256)
        node._default_ydata = np.linspace(0, 100, 256)

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
                with dpg.group(horizontal=False) as node.group_tag:
                    
                    # Boutons en haut
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Réduire",
                            callback=lambda: node.reset_plot_size(),
                        )
                        dpg.add_button(
                            label="Maximiser",
                            callback=lambda: node.maximize_plot_size(),
                        )

                    # Conteneur pour le plot (redimensionnable)
                    with dpg.child_window(
                        tag=node.tag_plot_container,
                        width=node.small_window_w,
                        height=node.small_window_h,
                        autosize_x=False,
                        autosize_y=False,
                        border=False
                    ):
                        with dpg.plot(
                            width=-1,  # prend toute la taille du conteneur
                            height=-1,
                            tag=node.tag_node_input01_value_name,
                            no_menus=True,
                        ):
                            dpg.add_plot_legend(horizontal=True, location=dpg.mvPlot_Location_NorthEast)

                            dpg.add_plot_axis(
                                dpg.mvXAxis,
                                tag=node.tag_node_input01_value_name + 'xaxis',
                            )
                            dpg.set_axis_limits(dpg.last_item(), 0, 256)

                            dpg.add_plot_axis(
                                dpg.mvYAxis,
                                tag=node.tag_node_input01_value_name + 'yaxis',
                            )
                            dpg.add_line_series(
                                node._default_xdata,
                                node._default_ydata,
                                label='B',
                                parent=node.tag_node_input01_value_name + 'yaxis',
                                tag=node.tag_node_input01_value_name + 'line_b',
                            )
                            dpg.add_line_series(
                                node._default_xdata,
                                node._default_ydata,
                                label='R',
                                parent=node.tag_node_input01_value_name + 'yaxis',
                                tag=node.tag_node_input01_value_name + 'line_r',
                            )
                            dpg.add_line_series(
                                node._default_xdata,
                                node._default_ydata,
                                label='G',
                                parent=node.tag_node_input01_value_name + 'yaxis',
                                tag=node.tag_node_input01_value_name + 'line_g',
                            )

        return node


class HistoNode(Node):
    _ver = '0.0.1'
    node_label = 'Histogram'
    node_tag = 'Histogram'

    _yaxis_divide_value = 32
    _default_xdata = None
    _default_ydata = None

    def __init__(self):
        super().__init__()
        self._min_val = 1
        self._max_val = 1000

        self.small_window_w = 240
        self.small_window_h = 135

        self.node_tag = "Histogram"
        self.node_label = "Histogram"

        self.tag_node_name = ""
        self.tag_node_input01_value_name = ""
        self.tag_plot_container = ""

    def maximize_plot_size(self):
        width, height = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
        dpg.configure_item(self.tag_plot_container, width=width - 100, height=height - 100)

    def reset_plot_size(self):
        dpg.configure_item(self.tag_plot_container, width=self.small_window_w, height=self.small_window_h)

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'

        connection_info_src = ''
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = connection_info_src.split(':')[:2]
            connection_info_src = ':'.join(connection_info_src)

        frame = node_image_dict.get(connection_info_src, None)

        result = None
        if frame is not None:
            b_histgram = cv2.calcHist([frame], [0], None, [256], [0, 256])
            g_histgram = cv2.calcHist([frame], [1], None, [256], [0, 256])
            r_histgram = cv2.calcHist([frame], [2], None, [256], [0, 256])

            dpg_set_value(tag_node_input01_value_name + 'line_b',
                          [self._default_xdata, b_histgram.T[0]])
            dpg_set_value(tag_node_input01_value_name + 'line_g',
                          [self._default_xdata, g_histgram.T[0]])
            dpg_set_value(tag_node_input01_value_name + 'line_r',
                          [self._default_xdata, r_histgram.T[0]])

            if dpg.does_item_exist(tag_node_input01_value_name + 'yaxis'):
                dpg.set_axis_limits(
                    tag_node_input01_value_name + 'yaxis', 0,
                    int(np.sum(b_histgram.T[0]) / self._yaxis_divide_value))

            result = {
                'r_histgram': list(r_histgram.T[0]),
                'g_histgram': list(g_histgram.T[0]),
                'b_histgram': list(b_histgram.T[0]),
            }

        return {"image": frame, "json": result}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)

        return {
            'ver': self._ver,
            'pos': pos
        }

    def set_setting_dict(self, node_id, setting_dict):
        pass
