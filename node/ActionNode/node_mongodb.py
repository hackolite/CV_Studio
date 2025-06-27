#!/usr/bin/env python
# -*- coding: utf-8 -*-
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode
from pymongo import MongoClient
import time
from bson import ObjectId
from datetime import datetime
import pytz  # optionnel mais recommandé pour gérer le fuseau UTC




uri = "mongodb+srv://affluence:affluence_password@cluster0.nn3l2bm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connexion à la base
client = MongoClient(uri)
db = client["AFFLUENCE"]  # nom de ta base
collection = db["affluence_phili"]  # nom de ta collection




class FactoryNode:
    node_label = 'Mongodb'
    node_tag = 'Mongodb'
    
    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Ajoute un nœud au graphe de traitement avec champ de lien et bouton Start."""
        
        # Génération des tags pour le Node et ses attributs
        node = MongodbNode()  # Utilise la classe MQTTNode au lieu de Node générique
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        
        tag_input_url = f"{node.tag_node_name}:InputURL"
        tag_start_button = f"{node.tag_node_name}:StartButton"
        
        node.tag_node_input_text_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01'
        node.tag_node_input_text_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input01Value'
        
        # Correction: utilise node.node_tag au lieu de self.node_tag
        tag_node_name = str(node_id) + ':' + node.node_tag
        tag_node_output01_name = tag_node_name + ':' + node.TYPE_INT + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + node.TYPE_INT + ':Output01Value'

        node.tag_node_output_audio_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudio'
        node.tag_node_output_audio_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':OutputAudioValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        node.tag_node_output_float_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloat'
        node.tag_node_output_float_value_name = node.tag_node_name + ':' + node.TYPE_FLOAT + ':OutputFloatValue'

        # Création d'un thème jaune pour boutons avec texte en blanc
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))          # Fond jaune
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 128, 255)) # Jaune clair au survol
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 64, 255))   # Jaune plus foncé en appui
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))                # Texte en noir pour meilleure lisibilité
        
        # Outputs audio, json, float, elapsed time en boutons désactivés mais jaune
        def add_yellow_disabled_button(label, tag):
            btn = dpg.add_button(
                label=label,
                tag=tag,
                enabled=False,
                width=300
            )
            dpg.bind_item_theme(btn, yellow_button_theme)
            return btn  

        # Création du nœud dans l'interface graphique
        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):  
            # Outputs (décommentés et corrigés)
            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Static):
                add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                    
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Input):
                add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)

            with dpg.node_attribute(tag=node.tag_node_output_float_name, attribute_type=dpg.mvNode_Attr_Static):
                add_yellow_disabled_button("Float", node.tag_node_output_float_value_name)
                    
        return node


class MongodbNode(BaseNode):  # Renommé pour éviter la confusion avec BaseNode
    _ver = '0.0.1'

    def __init__(self):
        super().__init__()  # Appel du constructeur parent
        self.node_label = 'Mongodb'
        self.node_tag = 'Mongodb'
        self._last_update_time = 0
        
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        tag_node_name = f"{node_id}:{self.node_tag}"
        tag_node_input01_value_name = f"{tag_node_name}:{self.TYPE_IMAGE}:Input01Value"

        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                        clee = ":".join(connection_info[0].split(":")[0:2])

        current_time = time.time()
        if current_time - self._last_update_time >= 10.0:  # toutes les secondes

            try:
				
                print(node_result_dict[clee])
                data = node_result_dict[clee]
                data['class_names'] = {str(k): v for k, v in data['class_names'].items()}
                data['time'] = datetime.now(pytz.utc)  # ou datetime.utcnow() si tu ne veux pas utiliser pytz

                result = collection.insert_one(data)
                print("ID du document inséré :", result.inserted_id)
            
            except Exception as e:
                print(e)
            

            self._last_update_time = current_time
        return {"image": None, "json": None}

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


# Code de test pour vérifier que le node s'affiche correctement
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
