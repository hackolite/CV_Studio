#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import numpy as np
import cv2
import yt_dlp
import dearpygui.dearpygui as dpg

# Importation des utilitaires
from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


# 📌 Identifiant du live YouTube (à remplacer)
VIDEO_ID = "VR-x3HdhKLQ"
VIDEO_ID = "zeSG7Js32Us"
#VIDEO_ID = "loHbMM9JfCs"
#VIDEO_ID = "elhJf3krR94"
VIDEO_ID = "KSsfLxP-A9g"



def get_light_live_stream_url(video_id):
    """Récupère l'URL du flux live en basse résolution (360p max)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
        "quiet": True,
        "format": "best[height<=400]",  # Limitation à 360p pour réduire la charge
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return cv2.VideoCapture(info.get("url", None))




class FactoryNode:
    node_label = 'YoutubeLive'
    node_tag = 'YoutubeLive'
    

    def __init__(self):
        pass

    
    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Ajoute un nœud au graphe de traitement."""
        
        # Génération des tags pour le Node et ses attributs
        node = Node()

        # Génération des tags pour le Node et ses attributs
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        node.tag_node_output01_name = f"{node.tag_node_name}:{node.TYPE_IMAGE}:Output01"
        node.tag_node_output01_value_name = f"{node.tag_node_name}:{node.TYPE_IMAGE}:Output01Value"

        # Initialisation du flux vidéo
        node.cap = get_light_live_stream_url(VIDEO_ID)
        node.last_frame_time = None
        node.frame_time = 1.0 / 32  # 15 FPS pour une lecture fluide
        node.small_window_w, node.small_window_h = 600, 400  # Taille de l'affichage

        # Image noire pour le démarrage
        black_image = np.zeros((node.small_window_w, node.small_window_h, 3))
        black_texture = node.convert_cv_to_dpg(black_image, node.small_window_w, node.small_window_h)

        # Création de la texture pour afficher l'image
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                node.small_window_w, node.small_window_h, black_texture,
                tag=node.tag_node_output01_value_name, format=dpg.mvFormat_Float_rgb
            )

        # Création du nœud dans l'interface graphique
        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):
            with dpg.node_attribute(tag=node.tag_node_output01_name, attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_image(node.tag_node_output01_value_name)

        return node



class Node(Node):
    """Node DearPyGui pour afficher un flux YouTube Live."""
    
    _ver = '0.0.1'
    node_label = 'YoutubeLive'
    node_tag = 'YoutubeLive'

    def __init__(self):
        """Initialisation du Node."""
        pass


    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        """Met à jour l'image du flux vidéo."""
        print("update YT")
        tag_node_name = f"{node_id}:{self.node_tag}"
        output_value01_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output01Value"

        self.current_time = time.time()
        ret, frame = self.cap.read()
        elapsed_time = self.current_time - self.last_frame_time if self.last_frame_time else 0

        # Attente pour synchroniser le FPS (évite les saccades)
        if elapsed_time < self.frame_time:
            time.sleep(self.frame_time - elapsed_time)

        self.last_frame_time = time.time()

        if ret and frame is not None:
            frame = cv2.resize(frame, (600, 400))  # Réduction de la taille pour alléger
            texture = self.convert_cv_to_dpg(frame, self.small_window_w, self.small_window_h)
            dpg_set_value(output_value01_tag, texture)

        return frame, None

    def close(self, node_id):
        """Libère les ressources vidéo lors de la fermeture du nœud."""
        if self.cap:
            self.cap.release()

    def get_setting_dict(self, node_id):
        """Sauvegarde la position du nœud dans l'interface."""
        tag_node_name = f"{node_id}:{self.node_tag}"
        pos = dpg.get_item_pos(tag_node_name)

        return {"ver": self._ver, "pos": pos}


    def set_setting_dict(self, node_id, setting_dict):
        """Charge les paramètres enregistrés du nœud."""
        pass
