#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import json
import logging
import requests
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node

# Setup logger
logger = logging.getLogger(__name__)


class FactoryNode:
    node_label = 'Weather'
    node_tag = 'Weather'
    
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
        node = WeatherNode() 
        
        node.tag_node_name = str(node_id) + ':' + self.node_tag
        node.tag_node_latitude_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Latitude'
        node.tag_node_latitude_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':LatitudeValue'
        
        node.tag_node_longitude_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Longitude'
        node.tag_node_longitude_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':LongitudeValue'
        
        node.tag_node_button_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Button'
        node.tag_node_button_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ButtonValue'

        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict.get('input_window_width', 240)
        small_window_h = node._opencv_setting_dict.get('input_window_height', 135)
        
        node._small_window_w = small_window_w
        node._small_window_h = small_window_h

        # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))
        
        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Latitude input
            with dpg.node_attribute(
                    tag=node.tag_node_latitude_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=node.tag_node_latitude_value_name,
                    label='Latitude',
                    width=node._small_window_w - 80,
                    default_value='48.8566',
                )

            # Longitude input
            with dpg.node_attribute(
                    tag=node.tag_node_longitude_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=node.tag_node_longitude_value_name,
                    label='Longitude',
                    width=node._small_window_w - 80,
                    default_value='2.3522',
                )

            # Fetch button
            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn_fetch = dpg.add_button(
                    label='Fetch Weather',
                    tag=node.tag_node_button_value_name,
                    width=node._small_window_w,
                    callback=node._button_fetch,
                    user_data=node.tag_node_name,
                )
                dpg.bind_item_theme(btn_fetch, yellow_button_theme)

            # JSON output
            with dpg.node_attribute(
                    tag=node.tag_node_output_json_name, 
                    attribute_type=dpg.mvNode_Attr_Output
            ):
                btn = dpg.add_button(
                    label="JSON",
                    tag=node.tag_node_output_json_value_name,
                    width=node._small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
        
        return node


class WeatherNode(Node):
    _ver = '1.0.0'

    node_label = 'Weather'
    node_tag = 'Weather'

    _opencv_setting_dict = None
    
    TYPE_TEXT = "TEXT"
    TYPE_JSON = "JSON"
    
    def __init__(self):
        super().__init__()
        self._last_weather_data = None
        self._fetching = False
        
    def _button_fetch(self, sender, app_data, user_data):
        """Callback when fetch button is clicked"""
        if self._fetching:
            return
            
        self._fetching = True
        try:
            # Get latitude and longitude from UI
            tag_node_name = user_data
            latitude_tag = tag_node_name + ':' + self.TYPE_TEXT + ':LatitudeValue'
            longitude_tag = tag_node_name + ':' + self.TYPE_TEXT + ':LongitudeValue'
            
            latitude = dpg_get_value(latitude_tag)
            longitude = dpg_get_value(longitude_tag)
            
            # Fetch weather data
            self._fetch_weather_data(latitude, longitude)
        finally:
            self._fetching = False

    def _fetch_weather_data(self, latitude, longitude):
        """Fetch weather data from Open-Meteo API"""
        try:
            # Convert to float to validate
            lat = float(latitude)
            lon = float(longitude)
            
            # Build API URL
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            
            # Fetch data with timeout
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            # Store the data
            self._last_weather_data = data
            
            logger.info(f"Weather data fetched successfully for ({lat}, {lon})")
            if 'current_weather' in data:
                temp = data['current_weather'].get('temperature', 'N/A')
                logger.info(f"Temperature: {temp}°C")
            
        except ValueError as e:
            logger.error(f"Invalid latitude or longitude format: {e}")
            self._last_weather_data = {
                "error": "Invalid coordinates format",
                "details": str(e)
            }
        except requests.RequestException as e:
            logger.error(f"Error fetching weather data: {e}")
            self._last_weather_data = {
                "error": "Failed to fetch data",
                "details": str(e)
            }
        except Exception as e:
            logger.exception(f"Unexpected error fetching weather data: {e}")
            self._last_weather_data = {
                "error": "Unexpected error",
                "details": str(e)
            }

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """Update method called by the node editor"""
        # Return the last fetched weather data
        return {
            "image": None, 
            "json": self._last_weather_data, 
            "audio": None
        }

    def close(self, node_id):
        """Cleanup when node is closed"""
        self._last_weather_data = None

    def get_setting_dict(self, node_id):
        """Save node settings for export"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        latitude_tag = tag_node_name + ':' + self.TYPE_TEXT + ':LatitudeValue'
        longitude_tag = tag_node_name + ':' + self.TYPE_TEXT + ':LongitudeValue'

        pos = dpg.get_item_pos(tag_node_name)
        
        latitude = dpg_get_value(latitude_tag)
        longitude = dpg_get_value(longitude_tag)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[latitude_tag] = latitude
        setting_dict[longitude_tag] = longitude
        
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Restore node settings from import"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        latitude_tag = tag_node_name + ':' + self.TYPE_TEXT + ':LatitudeValue'
        longitude_tag = tag_node_name + ':' + self.TYPE_TEXT + ':LongitudeValue'

        latitude = setting_dict.get(latitude_tag, '48.8566')
        longitude = setting_dict.get(longitude_tag, '2.3522')

        dpg_set_value(latitude_tag, latitude)
        dpg_set_value(longitude_tag, longitude)
