#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import subprocess
import threading

import cv2
import numpy as np
import dearpygui.dearpygui as dpg
import yt_dlp

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


def get_light_live_stream_url(url):
    """Retrieves live stream URL and returns a VideoCapture using streamlink or direct URL.
    
    Utilise streamlink pour convertir le stream HLS en quelque chose qu'OpenCV peut lire.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty or whitespace")
    
    # Option 1: Essayer avec streamlink (meilleure compatibilité)
    try:
        print("Tentative avec streamlink...")
        import streamlink
        
        # Obtenir les streams disponibles
        streams = streamlink.streams(url)
        
        if not streams:
            raise ValueError("Aucun stream trouvé avec streamlink")
        
        # Choisir la meilleure qualité <= 480p
        preferred_qualities = ['480p', '360p', '240p', 'worst', 'best']
        stream = None
        
        for quality in preferred_qualities:
            if quality in streams:
                stream = streams[quality]
                print(f"Stream trouvé en qualité: {quality}")
                break
        
        if stream is None:
            # Prendre le premier stream disponible
            stream = list(streams.values())[0]
            print(f"Stream par défaut utilisé")
        
        # Ouvrir le stream avec OpenCV
        stream_url = stream.url if hasattr(stream, 'url') else stream.to_url()
        cap = cv2.VideoCapture(stream_url)
        
        # Tester la lecture
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print("✓ Stream ouvert avec streamlink")
                return cap
            else:
                cap.release()
        
    except ImportError:
        print("streamlink n'est pas installé. Installation requise: pip install streamlink")
    except Exception as e:
        print(f"Erreur avec streamlink: {e}")
    
    # Option 2: Utiliser yt-dlp pour obtenir l'URL directe (format bas débit)
    print("Tentative avec yt-dlp...")
    
    format_strategies = [
        "worst[height<=480][protocol!=m3u8]",  # Éviter HLS si possible
        "worst[height<=360]",
        "worst",  # Dernière option: le pire format (mais qui devrait marcher)
    ]
    
    for format_spec in format_strategies:
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "format": format_spec,
                "nocheckcertificate": True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Essayer de trouver un format non-HLS
                formats = info.get("formats", [])
                
                # Filtrer les formats utilisables
                usable_formats = []
                for f in formats:
                    url_f = f.get("url", "")
                    if url_f and "m3u8" not in url_f.lower():
                        height = f.get("height", 0)
                        if 0 < height <= 480:
                            usable_formats.append(f)
                
                # Trier par hauteur (préférer la plus basse résolution)
                if usable_formats:
                    usable_formats.sort(key=lambda x: x.get("height", 9999))
                    video_url = usable_formats[0].get("url")
                    
                    if video_url:
                        cap = cv2.VideoCapture(video_url)
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                print(f"✓ Stream ouvert avec yt-dlp (format: {format_spec})")
                                return cap
                            cap.release()
        
        except Exception as e:
            print(f"Erreur avec format {format_spec}: {e}")
            continue
    
    raise ValueError(
        "Impossible d'ouvrir le stream YouTube. "
        "Solution: installez streamlink avec 'pip install streamlink'"
    )


class FactoryNode:
    node_label = 'YouTube'
    node_tag = 'YouTube'

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
        node = YoutubeNode()
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

        node._opencv_setting_dict = opencv_setting_dict
        node.small_window_w = node._opencv_setting_dict['input_window_width']
        node.small_window_h = node._opencv_setting_dict['input_window_height']

        black_image = np.zeros((node.small_window_h, node.small_window_w, 3), dtype=np.uint8)
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
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # Create blue theme for active streaming
        with dpg.theme() as blue_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (100, 149, 237, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (65, 105, 225, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (25, 25, 112, 255))
        
        node.yellow_button_theme = yellow_button_theme
        node.blue_button_theme = blue_button_theme

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=node.tag_node_input01_value_name,
                    label='URL',
                    width=node.small_window_w - 30,
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Static
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

            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn_start = dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=node.small_window_w,
                    callback=node.button,
                    user_data=node.tag_node_input01_value_name,
                )
                dpg.bind_item_theme(btn_start, yellow_button_theme)

            def add_yellow_disabled_button(label, tag):
                btnn = dpg.add_button(
                    label=label,
                    tag=tag,
                    width=node.small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btnn, yellow_button_theme)
                return btnn

            with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
                add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
                
            with dpg.node_attribute(tag=node.tag_node_output_json_name, attribute_type=dpg.mvNode_Attr_Output):
                add_yellow_disabled_button("JSON", node.tag_node_output_json_value_name)

        return node


class YoutubeNode(Node):
    _ver = '0.0.1'

    node_label = 'YouTube'
    node_tag = 'YouTube'

    _opencv_setting_dict = None
    _start_label = 'Start'
    _stop_label = 'Stop'
    _loading_label = 'Loading...'

    _min_val = 1
    _max_val = 200

    def __init__(self):
        super().__init__()
        self._min_val = 1
        self._max_val = 1000
        self._start_label = "Start"
        self.node_tag = "YouTube"
        self.node_label = "YouTube"
        self.cap = None
        self.small_window_w = 240
        self.small_window_h = 135
        self.yellow_button_theme = None
        self.blue_button_theme = None
        self.is_streaming = False
        self._frame_skip_counter = 0
        
    def convert_cv_to_dpg(self, cv_img, w, h):
        """Converts OpenCV image to DearPyGui format"""
        if cv_img is None:
            return (np.zeros(w * h * 3, dtype=np.float32)).tobytes()
        
        resized = cv2.resize(cv_img, (w, h))
        rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb_image.astype(np.float32) / 255.0
        return normalized.flatten().tobytes()

    def button(self, sender, data, user_data):
        tag_parts = user_data.split(':')
        tag_node_name = ':'.join(tag_parts[:2])
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'
        
        label = dpg.get_item_label(tag_node_button_value_name)
        youtube_url = dpg.get_value(user_data)
        
        if label == self._start_label:
            if not youtube_url or not isinstance(youtube_url, str) or not youtube_url.strip():
                print("❌ Erreur: Veuillez entrer une URL YouTube valide")
                return
            
            try:
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                
                print(f"🔄 Ouverture du stream YouTube: {youtube_url}")
                dpg.set_item_label(tag_node_button_value_name, self._loading_label)
                
                self.cap = get_light_live_stream_url(youtube_url)
                
                if self.cap is None or not self.cap.isOpened():
                    print("❌ Erreur: Impossible d'ouvrir le stream")
                    self.cap = None
                    dpg.set_item_label(tag_node_button_value_name, self._start_label)
                    return
                
                print(f"✅ Stream YouTube démarré avec succès!")
                self.is_streaming = True
                self._frame_skip_counter = 0
                
                dpg.set_item_label(tag_node_button_value_name, self._stop_label)
                
                if self.blue_button_theme is not None:
                    dpg.bind_item_theme(tag_node_button_value_name, self.blue_button_theme)
                    
            except ValueError as e:
                print(f"❌ Erreur: {e}")
                self.cap = None
                self.is_streaming = False
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
            except Exception as e:
                print(f"❌ Erreur inattendue: {e}")
                self.cap = None
                self.is_streaming = False
                dpg.set_item_label(tag_node_button_value_name, self._start_label)
        
        elif label == self._stop_label:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
                print("⏹️ Stream YouTube arrêté")
            
            self.is_streaming = False
            dpg.set_item_label(tag_node_button_value_name, self._start_label)
            
            if self.yellow_button_theme is not None:
                dpg.bind_item_theme(tag_node_button_value_name, self.yellow_button_theme)

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        """Updates the video stream image."""
        tag_node_name = f"{node_id}:{self.node_tag}"
        output_value01_tag = f"{tag_node_name}:{self.TYPE_IMAGE}:Output01Value"

        self.current_time = time.time()

        if not hasattr(self, "_last_frame_time"):
            self._last_frame_time = 0
        
        try:
            slider_tag = f"{tag_node_name}:{self.TYPE_INT}:Input02Value"
            self._frame_interval = max(1, dpg_get_value(slider_tag)) / 1000
        except (ValueError, KeyError, AttributeError, TypeError):
            self._frame_interval = 0.033

        if self.cap is not None and self.is_streaming and self.current_time - self._last_frame_time >= self._frame_interval:
            try:
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    self._last_frame = frame
                    texture = self.convert_cv_to_dpg(frame, self.small_window_w, self.small_window_h)
                    dpg_set_value(output_value01_tag, texture)
                    self._last_frame_time = self.current_time
                    self._frame_skip_counter = 0
                else:
                    self._frame_skip_counter += 1
                    if self._frame_skip_counter > 150:
                        print("⚠️ Avertissement: Stream pourrait être terminé ou avoir un problème")
                        self._frame_skip_counter = 0
                        
            except Exception as e:
                print(f"❌ Erreur de lecture: {e}")
                self._frame_skip_counter += 1

        return {"image": getattr(self, "_last_frame", None), "json": None, "audio": None}
    
    def close(self, node_id):
        """Clean up resources when node is closed."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_streaming = False

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
