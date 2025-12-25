#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import threading
import numpy as np
import sounddevice as sd

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


class FactoryNode:
    node_label = 'Buzzer'
    node_tag = 'Buzzer'
    
    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Adds a Buzzer node to the processing graph."""
        
        # Generate tags for Node and its attributes
        node = BuzzerNode()
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        
        tag_node_name = str(node_id) + ':' + node.node_tag
        
        # JSON Input
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputJson'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputJsonValue'
        
        # Duration slider
        tag_node_duration_name = tag_node_name + ':Duration'
        tag_node_duration_value_name = tag_node_name + ':DurationValue'
        
        # Insensitivity delay slider
        tag_node_delay_name = tag_node_name + ':Delay'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'
        
        # Status indicator
        tag_node_status_name = tag_node_name + ':Status'
        tag_node_status_value_name = tag_node_name + ':StatusValue'

        # Create yellow theme for buttons
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 128, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 64, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))

        # Create node in the GUI
        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):
            # JSON Input
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Input JSON with boolean',
                )
            
            # Duration slider
            with dpg.node_attribute(
                tag=tag_node_duration_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=tag_node_duration_value_name,
                    label="Buzz Duration (s)",
                    default_value=5.0,
                    min_value=0.1,
                    max_value=10.0,
                    width=300,
                )
            
            # Insensitivity delay slider
            with dpg.node_attribute(
                tag=tag_node_delay_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=tag_node_delay_value_name,
                    label="Insensitivity Delay (s)",
                    default_value=0.0,
                    min_value=0.0,
                    max_value=60.0,
                    width=300,
                )
            
            # Status indicator
            with dpg.node_attribute(
                tag=tag_node_status_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn = dpg.add_button(
                    label="Ready",
                    tag=tag_node_status_value_name,
                    enabled=False,
                    width=300
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                    
        return node


class BuzzerNode(BaseNode):
    _ver = '0.0.1'

    def __init__(self):
        super().__init__()
        self.node_label = 'Buzzer'
        self.node_tag = 'Buzzer'
        self._last_buzz_time = 0
        self._is_buzzing = False
        self._buzz_thread = None
        self._insensitivity_end_time = 0
        
    def _generate_buzz_sound(self, duration):
        """
        Generate a non-aggressive modulated buzzer sound.
        Uses a frequency sweep to make it less harsh.
        """
        samplerate = 44100  # samples per second
        t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
        
        # Create a modulated frequency sweep from 400Hz to 600Hz
        # This is less aggressive than a constant high-pitched tone
        start_freq = 400
        end_freq = 600
        frequency = start_freq + (end_freq - start_freq) * (t / duration)
        
        # Generate the base sine wave
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Apply amplitude modulation (tremolo) for a less aggressive sound
        mod_freq = 8  # Modulation frequency in Hz
        modulation = 0.5 + 0.5 * np.sin(2 * np.pi * mod_freq * t)
        audio = audio * modulation
        
        # Apply fade-in and fade-out to avoid clicks
        fade_duration = 0.05  # 50ms fade
        fade_samples = int(samplerate * fade_duration)
        
        if len(audio) > 2 * fade_samples:
            # Fade in
            audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
            # Fade out
            audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        return audio, samplerate
    
    def _play_buzz_thread(self, duration):
        """Thread function to play the buzzer sound"""
        try:
            self._is_buzzing = True
            audio, samplerate = self._generate_buzz_sound(duration)
            sd.play(audio, samplerate=samplerate)
            sd.wait()  # Wait for playback to complete
        except Exception as e:
            print(f"Buzzer error: {e}")
        finally:
            self._is_buzzing = False

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        tag_node_name = f"{node_id}:{self.node_tag}"
        tag_node_duration_value_name = f"{tag_node_name}:DurationValue"
        tag_node_delay_value_name = f"{tag_node_name}:DelayValue"
        tag_node_status_value_name = f"{tag_node_name}:StatusValue"
        
        # Find connected source for JSON data
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)
                break
        
        # Get JSON data
        node_result = node_result_dict.get(connection_info_src, {})
        
        # Get configuration values
        try:
            buzz_duration = float(dpg_get_value(tag_node_duration_value_name))
            insensitivity_delay = float(dpg_get_value(tag_node_delay_value_name))
        except (ValueError, TypeError):
            buzz_duration = 5.0
            insensitivity_delay = 0.0
        
        current_time = time.time()
        
        # Check if we're in insensitivity period
        if current_time < self._insensitivity_end_time:
            # Still in insensitivity period
            remaining = self._insensitivity_end_time - current_time
            try:
                dpg.configure_item(
                    tag_node_status_value_name,
                    label=f"Insensitive ({remaining:.1f}s)"
                )
            except (SystemError, AttributeError):
                pass
            return {"image": None, "json": None, "audio": None}
        
        # Check if JSON contains a boolean that is True
        should_buzz = False
        if node_result and isinstance(node_result, dict):
            # Look for any boolean field with value True
            for key, value in node_result.items():
                if isinstance(value, bool) and value:
                    should_buzz = True
                    break
        
        # Update status
        if self._is_buzzing:
            try:
                dpg.configure_item(tag_node_status_value_name, label="Buzzing...")
            except (SystemError, AttributeError):
                pass
        elif should_buzz and not self._is_buzzing:
            # Start buzzing
            self._buzz_thread = threading.Thread(
                target=self._play_buzz_thread,
                args=(buzz_duration,),
                daemon=True
            )
            self._buzz_thread.start()
            
            # Set insensitivity end time
            self._insensitivity_end_time = current_time + buzz_duration + insensitivity_delay
            
            try:
                dpg.configure_item(tag_node_status_value_name, label="Buzzing...")
            except (SystemError, AttributeError):
                pass
        else:
            try:
                dpg.configure_item(tag_node_status_value_name, label="Ready")
            except (SystemError, AttributeError):
                pass
        
        return {"image": None, "json": None, "audio": None}

    def close(self, node_id):
        """Clean up when node is closed"""
        # Stop any active buzzing
        if self._is_buzzing:
            sd.stop()

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_duration_value_name = tag_node_name + ':DurationValue'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        duration_value = float(dpg_get_value(tag_node_duration_value_name))
        delay_value = float(dpg_get_value(tag_node_delay_value_name))
        pos = dpg.get_item_pos(tag_node_name)
        
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_duration_value_name] = duration_value
        setting_dict[tag_node_delay_value_name] = delay_value
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_duration_value_name = tag_node_name + ':DurationValue'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        duration_value = float(setting_dict.get(tag_node_duration_value_name, 5.0))
        delay_value = float(setting_dict.get(tag_node_delay_value_name, 0.0))
        
        dpg_set_value(tag_node_duration_value_name, duration_value)
        dpg_set_value(tag_node_delay_value_name, delay_value)


# Test code to verify that the node displays correctly
if __name__ == "__main__":
    dpg.create_context()
    
    with dpg.window(label="Test Buzzer Node", width=800, height=600):
        with dpg.node_editor(label="Node Editor"):
            factory = FactoryNode()
            factory.add_node(parent=dpg.last_item(), node_id=1, pos=[100, 100])
    
    dpg.create_viewport(title='Test Buzzer Node', width=900, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
