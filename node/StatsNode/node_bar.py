#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import cv2
import pafy
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
#from node_editor.util import convert_cv_to_dpg

import threading
from threading import Lock

from node.basenode import Node
import matplotlib.pyplot as plt
import numpy as np
import io
from PIL import Image
import dearpygui.dearpygui as dpg	
import matplotlib
matplotlib.use('Agg')  # force backend non-GUI
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # force backend non-GUI
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import cv2

from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import random

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import numpy as np

from collections import deque




# Global FIFO list to update on each call




def render_bar_image(history):

    fig, ax = plt.subplots(figsize=(5, 1.5), dpi=100)
    ax.bar(range(len(history)), history, color='skyblue')
    ax.set_ylim(0, 10)
    ax.axis('off')

    canvas = FigureCanvas(fig)
    canvas.draw()
    image = np.asarray(canvas.buffer_rgba())[:, :, :3]
    plt.close(fig)
    return image

import time 
import numpy as np
import dearpygui.dearpygui as dpg



class FactoryNode:
    node_label = 'BAR'
    node_tag = 'BAR'

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
        node = StatNode()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'

        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_INT + ':Input02Value'

        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'

        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node.tag_node_button_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Button'
        node.tag_node_button_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ButtonValue'

        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloat'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloatValue'

        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = 300
        node.small_window_h = 300
        use_pref_counter = node._opencv_setting_dict.get('use_pref_counter', False)

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

		
        # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))          # Yellow background
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255)) # Light yellow on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))   # Darker yellow on press

		
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
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_input02_value_name,
                    label="Interval(ms)",
                    width=node.small_window_w - 110,
                    default_value=33,
                    min_value=node._min_val,
                    max_value=node._max_val,
                    callback=None,
                )

            # Start button with yellow theme
            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn_start = dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node.small_window_w,
                    user_data=node.tag_node_name,
                )
                dpg.bind_item_theme(btn_start, yellow_button_theme)

            # Outputs audio, json, float, elapsed time as disabled yellow buttons
            def add_yellow_disabled_button(label, tag):
                btn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node.small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                return btn



            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                btn = add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)

            with dpg.node_attribute(tag=node.tag_node_output_float_name, attribute_type=dpg.mvNode_Attr_Static):
                btn = add_yellow_disabled_button("Float", node.tag_node_output_float_value_name)

        return node



class StatNode(Node):
    _ver = '0.0.1'

    _opencv_setting_dict = None
    _start_label = 'Start'
    _stop_label = 'Stop'
    _loading_label = 'Loading...'

    _min_val = 1
    _max_val = 200
     
    _youtube_capture = {}
    _prev_read_time = {}

    def __init__(self):
        super().__init__()  # Call parent constructor
        self._min_val = 1
        self._max_val = 1000
        
        self._small_window_w = 240
        self._small_window_h = 135
        
        self.node_tag = "BAR"
        self.node_label = "BAR"
        self.queue = deque(maxlen=3)  # taille fixe à 3 éléments max
        self.last_update_time = time.time()


    
    # Méthode update() modifiée pour votre classe Node
    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict=None):
        """
        Remplacez votre méthode update() par celle-ci
        """
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        input_value02_tag = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        use_pref_counter = self._opencv_setting_dict.get('use_pref_counter', False)

        #  Générer l'image avec la nouvelle fonction
        # ou im_animated(frame_count) pour animation
        frame = None 

        
        current_time = time.time()

        if current_time - self.last_update_time >= 3.0:  # 5 secondes
                #frame = render_bar_image() 
                value = random.randint(0, 10)
                
                self.queue.append(value)
                
                frame = render_bar_image(list(self.queue))
                self.last_update_time = current_time

                # Redimensionner si nécessaire
                height, width = frame.shape[:2]
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)
                frame = cv2.resize(frame, (small_window_w, small_window_h), interpolation=cv2.INTER_AREA)
                #frame = frame.flatten() / 255.0

                # Mettre à jour la texture dans DearPyGui
                dpg.set_value(self.tag_node_output01_value_name, frame)

                print(f"Image updated at {time.strftime('%H:%M:%S')}") 
    
        return {"image": frame, "json": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'

        pos = dpg.get_item_pos(tag_node_name)
        youtube_url = dpg_get_value(tag_node_input01_value_name)
        interval_time = dpg_get_value(tag_node_input02_value_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_input01_value_name] = youtube_url
        setting_dict[tag_node_input02_value_name] = interval_time

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':Input01Value'
        tag_node_input02_value_name = tag_node_name + ':' + self.TYPE_INT + ':Input02Value'

        youtube_url = setting_dict[tag_node_input01_value_name]
        interval_time = setting_dict[tag_node_input02_value_name]

        dpg_set_value(tag_node_input01_value_name, youtube_url)
        dpg_set_value(tag_node_input02_value_name, interval_time)


