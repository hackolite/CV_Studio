#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


class FactoryNode:
    node_label = 'Websocket'
    node_tag = 'Websocket'
    
    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Adds a node to the processing graph with link field and Start button."""
        
        # Generate tags for Node and its attributes
        node = WebsocketNode()  # Use MQTTNode class instead of generic Node
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        
        tag_input_url = f"{node.tag_node_name}:InputURL"
        tag_start_button = f"{node.tag_node_name}:StartButton"
        
        node.tag_node_input_text_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input_text_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'
        
        # Use node.node_tag instead of self.node_tag
        tag_node_name = str(node_id) + ':' + node.node_tag
        tag_node_output01_name = tag_node_name + ':' + node.TYPE_INT + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + node.TYPE_INT + ':Output01Value'

        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloat'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloatValue'

        node.tag_node_output_image_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':OutputImage'
        node.tag_node_output_image_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':OutputImageValue'

        node.tag_node_output_type_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':OutputType'
        node.tag_node_output_type_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':OutputTypeValue'

        # Create black image texture
        small_window_w = 240
        small_window_h = 135
        black_image = np.zeros((small_window_w, small_window_h, 3), dtype=np.float32)
        black_texture = black_image.tobytes()

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output_image_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

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
                width=300
            )
            dpg.bind_item_theme(btn, yellow_button_theme)
            return btn  

        # Create node in the GUI
        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):  
            # Input field for link
            with dpg.node_attribute(tag=node.tag_node_input_text_name, attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_text(tag=node.tag_node_input_text_value_name, width=300, hint="Entrer une URL")
        
            # Start button
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                btn = dpg.add_button(label="Start", tag=tag_start_button, callback=callback, user_data=tag_input_url, width=300)
                dpg.bind_item_theme(btn, yellow_button_theme)

            # Add dropdown for output type selection
            with dpg.node_attribute(
                    tag=node.tag_node_output_type_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_output_type_value_name,
                    items=["Image", "Float", "Audio", "JSON"],
                    label="Output Type",
                    default_value="JSON",
                    width=280,
                )
                
            # Outputs
            with dpg.node_attribute(tag=node.tag_node_output_image_name, attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_image(node.tag_node_output_image_value_name)
            
            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Static):
                add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                    
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)

            with dpg.node_attribute(tag=node.tag_node_output_float_name, attribute_type=dpg.mvNode_Attr_Output):
                add_yellow_disabled_button("Float", node.tag_node_output_float_value_name)
                    
        return node


class WebsocketNode(BaseNode):  # Renommé pour éviter la confusion avec BaseNode
    _ver = '0.0.1'
    #node_label = 'MQTT'
    #node_tag = 'MQTT'

    def __init__(self):
        super().__init__()  # Call parent constructor
        self.node_label = 'Websocket'
        self.node_tag = 'Websocket'

    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        return None, None


    def close(self, node_id):
        pass


    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value_tag = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'
        tag_node_output_type_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':OutputTypeValue'

        output_value = round((dpg_get_value(output_value_tag)), 3)
        output_type = dpg_get_value(tag_node_output_type_value_name)
        pos = dpg.get_item_pos(tag_node_name)
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[output_value_tag] = output_value
        setting_dict[tag_node_output_type_value_name] = output_type
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value_tag = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'
        tag_node_output_type_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':OutputTypeValue'

        output_value = float(setting_dict[output_value_tag])
        output_type = setting_dict.get(tag_node_output_type_value_name, "JSON")
        dpg_set_value(output_value_tag, output_value)
        dpg_set_value(tag_node_output_type_value_name, output_type)


# Test code to verify that the node displays correctly
if __name__ == "__main__":
    dpg.create_context()
    
    with dpg.window(label="Test MQTT Node", width=800, height=600):
        with dpg.node_editor(label="Node Editor"):
            factory = FactoryNode()
            factory.add_node(parent=dpg.last_item(), node_id=1, pos=[100, 100])
    
    dpg.create_viewport(title='Test MQTT Node', width=900, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
