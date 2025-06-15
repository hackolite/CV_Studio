#!/usr/bin/env python
# -*- coding: utf-8 -*-
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node



class FactoryNode:
    node_label = 'IntValue'
    node_tag = 'IntValue'
    

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
      """Ajoute un nœud au graphe de traitement avec champ de lien et bouton Start."""
    
      # Génération des tags pour le Node et ses attributs
      node = Node()
      node.tag_node_name = f"{node_id}:{node.node_tag}"
    
      tag_input_url = f"{node.tag_node_name}:InputURL"
      tag_start_button = f"{node.tag_node_name}:StartButton"
      tag_node_output01_name = f"{node.tag_node_name}:{node.TYPE_IMAGE}:Output01"
      tag_node_output01_value_name = f"{node.tag_node_name}:{node.TYPE_IMAGE}:Output01Value"
    
      # Création du nœud dans l'interface graphique
      with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):
        # Champ de saisie pour le lien (Input)
        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
          dpg.add_input_text(label="Lien URL", tag=tag_input_url, width=200, hint="Entrer une URL")
    
        # Bouton Start (avec callback si fourni)
        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
          dpg.add_button(label="Start", tag=tag_start_button, callback=callback, user_data=tag_input_url)
        
      return node




class Node(Node):
    _ver = '0.0.1'

    node_label = 'IntValue'
    node_tag = 'IntValue'

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

        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_output01_name = tag_node_name + ':' + self.TYPE_INT + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'

        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloat'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloatValue'



        return tag_node_name

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
    ):
        return None, None

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value_tag = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'

        output_value = round((dpg_get_value(output_value_tag)), 3)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[output_value_tag] = output_value

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value_tag = tag_node_name + ':' + self.TYPE_INT + ':Output01Value'

        output_value = float(setting_dict[output_value_tag])

        dpg_set_value(output_value_tag, output_value)
