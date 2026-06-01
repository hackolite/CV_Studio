#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import threading
import traceback
import logging
from datetime import datetime

import numpy as np
import sounddevice as sd

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


# ---------------------------------------------------------------------------
# Crash-dump logger for Buzzer nodes
# ---------------------------------------------------------------------------
_BUZZER_LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_BUZZER_LOG_DIR, exist_ok=True)

_buzzer_logger = logging.getLogger("buzzer_crash_dump")
_buzzer_logger.setLevel(logging.DEBUG)
if not _buzzer_logger.handlers:
    _log_path = os.path.join(_BUZZER_LOG_DIR, "buzzer_crash_dump.log")
    _fh = logging.FileHandler(_log_path, encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    _buzzer_logger.addHandler(_fh)

# Global lock protecting sounddevice playback across all BuzzerNode instances
_sd_playback_lock = threading.Lock()

# Registry of active buzzer instances (for crash-dump context)
_active_buzzers: dict = {}  # node_tag_name -> BuzzerNode
_active_buzzers_lock = threading.Lock()


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
        
        tag_node_name = node.tag_node_name
        
        # JSON Input
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputJson'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputJsonValue'
        
        # Sound type combo
        tag_node_sound_type_name = tag_node_name + ':SoundType'
        tag_node_sound_type_value_name = tag_node_name + ':SoundTypeValue'
        
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
            
            # Sound type selection
            with dpg.node_attribute(
                tag=tag_node_sound_type_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=tag_node_sound_type_value_name,
                    label="Sound Indicator",
                    items=BuzzerNode.SOUND_TYPES,
                    default_value=BuzzerNode.SOUND_TYPES[0],
                    width=300,
                )
            
            # Duration slider
            with dpg.node_attribute(
                tag=tag_node_duration_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=tag_node_duration_value_name,
                    label="Buzz Duration (s)",
                    default_value=BuzzerNode.DEFAULT_DURATION,
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
                    default_value=BuzzerNode.DEFAULT_INSENSITIVITY_DELAY,
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
    _ver = '0.0.2'
    
    # Default configuration values
    DEFAULT_DURATION = 5.0
    DEFAULT_INSENSITIVITY_DELAY = 0.0
    
    # Available sound types
    SOUND_TYPES = [
        "Default Buzzer",
        "Airplane Seatbelt Chime",
        "Gentle Beep",
        "Soft Chime",
        "Ambient Tone"
    ]

    def __init__(self):
        super().__init__()
        self.node_label = 'Buzzer'
        self.node_tag = 'Buzzer'
        self._last_buzz_time = 0
        self._is_buzzing = False
        self._buzz_thread = None
        self._insensitivity_end_time = 0
        self._registered = False
        
    def _generate_buzz_sound(self, duration, sound_type="Default Buzzer"):
        """
        Generate different types of buzzer sounds.
        Uses various sound patterns depending on the selected type.
        
        Args:
            duration: Duration of the sound in seconds
            sound_type: Type of sound to generate (from SOUND_TYPES)
        
        Returns:
            tuple: (audio array, sample rate)
        """
        samplerate = 44100  # samples per second
        t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
        
        if sound_type == "Airplane Seatbelt Chime":
            # Two-tone chime similar to airplane seatbelt indicator
            # Calm, pleasant ding-dong sound
            freq1 = 800  # Hz - first tone (higher)
            freq2 = 600  # Hz - second tone (lower)
            
            # First chime
            tone_duration = min(0.3, duration / 2)
            tone_samples = int(samplerate * tone_duration)
            t1 = t[:tone_samples]
            chime1 = 0.4 * np.sin(2 * np.pi * freq1 * t1)
            
            # Add harmonics for richer sound
            chime1 += 0.2 * np.sin(2 * np.pi * freq1 * 2 * t1)
            
            # Fade out first chime
            fade_out = np.exp(-5 * t1 / tone_duration)
            chime1 = chime1 * fade_out
            
            # Second chime (after a short pause)
            if duration > tone_duration * 1.2:
                pause_samples = int(samplerate * 0.05)
                t2 = t[:tone_samples]
                chime2 = 0.4 * np.sin(2 * np.pi * freq2 * t2)
                chime2 += 0.2 * np.sin(2 * np.pi * freq2 * 2 * t2)
                chime2 = chime2 * fade_out
                
                # Combine chimes with pause
                audio = np.zeros(len(t))
                audio[:tone_samples] = chime1
                audio[tone_samples + pause_samples:tone_samples + pause_samples + tone_samples] = chime2
            else:
                audio = np.zeros(len(t))
                audio[:tone_samples] = chime1
                
        elif sound_type == "Gentle Beep":
            # Single gentle beep at a pleasant frequency
            frequency = 650  # Hz - comfortable middle frequency
            audio = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # Smooth envelope for gentle sound
            attack = 0.05  # 50ms attack
            release = 0.1  # 100ms release
            attack_samples = int(samplerate * attack)
            release_samples = int(samplerate * release)
            
            if len(audio) > attack_samples + release_samples:
                audio[:attack_samples] *= np.linspace(0, 1, attack_samples)
                audio[-release_samples:] *= np.linspace(1, 0, release_samples)
                
        elif sound_type == "Soft Chime":
            # Bell-like sound using multiple harmonics
            # Fundamental frequency
            f0 = 520  # Hz
            
            # Create bell harmonics (non-integer ratios for realistic bell)
            audio = (0.4 * np.sin(2 * np.pi * f0 * t) +
                    0.3 * np.sin(2 * np.pi * f0 * 2.4 * t) +
                    0.2 * np.sin(2 * np.pi * f0 * 3.8 * t) +
                    0.1 * np.sin(2 * np.pi * f0 * 5.2 * t))
            
            # Exponential decay for bell-like fade
            decay = np.exp(-2 * t / duration)
            audio = audio * decay
            
        elif sound_type == "Ambient Tone":
            # Very calm, low-stress ambient tone
            # Low frequency with gentle modulation
            base_freq = 350  # Hz - lower, calmer frequency
            
            # Gentle frequency modulation
            mod_depth = 20  # Hz
            mod_freq = 0.5  # Very slow modulation
            frequency = base_freq + mod_depth * np.sin(2 * np.pi * mod_freq * t)
            
            # Generate sound with modulated frequency
            phase = 2 * np.pi * np.cumsum(frequency) / samplerate
            audio = 0.25 * np.sin(phase)
            
            # Very gentle amplitude modulation
            amp_mod = 0.9 + 0.1 * np.sin(2 * np.pi * 0.3 * t)
            audio = audio * amp_mod
            
            # Smooth fade in and out
            fade_duration = min(0.2, duration / 4)
            fade_samples = int(samplerate * fade_duration)
            if len(audio) > 2 * fade_samples:
                audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
                audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
                
        else:  # "Default Buzzer"
            # Original modulated frequency sweep
            start_freq = 400
            end_freq = 600
            frequency = start_freq + (end_freq - start_freq) * (t / duration)
            
            # Generate the base sine wave
            audio = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # Apply amplitude modulation (tremolo)
            mod_freq = 8  # Modulation frequency in Hz
            modulation = 0.5 + 0.5 * np.sin(2 * np.pi * mod_freq * t)
            audio = audio * modulation
            
            # Apply fade-in and fade-out
            fade_duration = 0.05  # 50ms fade
            fade_samples = int(samplerate * fade_duration)
            
            if len(audio) > 2 * fade_samples:
                audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
                audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        return audio, samplerate
    
    def _play_buzz_thread(self, duration, sound_type="Default Buzzer"):
        """Thread function to play the buzzer sound (thread-safe)"""
        try:
            self._is_buzzing = True
            audio, samplerate = self._generate_buzz_sound(duration, sound_type)

            # Acquire global lock to prevent concurrent sd.play() calls
            # Use a generous timeout: multiple buzzers may queue up
            acquired = _sd_playback_lock.acquire(timeout=30)
            if not acquired:
                _buzzer_logger.warning(
                    "TIMEOUT acquiring playback lock for %s (sound=%s, duration=%.2f). "
                    "Another buzzer is monopolizing playback.",
                    self.tag_node_name, sound_type, duration
                )
                return

            try:
                _buzzer_logger.info(
                    "START playback: node=%s sound=%s duration=%.2f",
                    self.tag_node_name, sound_type, duration
                )
                sd.play(audio, samplerate=samplerate)
                sd.wait()  # Wait for playback to complete
                _buzzer_logger.info("END playback: node=%s", self.tag_node_name)
            finally:
                _sd_playback_lock.release()

        except Exception as e:
            # --- Crash dump ---
            self._write_crash_dump(e, sound_type, duration)
        finally:
            self._is_buzzing = False

    def _write_crash_dump(self, exception, sound_type, duration):
        """Write a detailed crash dump log when buzzer playback fails."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dump_file = os.path.join(_BUZZER_LOG_DIR, f"crash_dump_{timestamp}.log")

        # Gather context about all active buzzers
        with _active_buzzers_lock:
            active_snapshot = {
                tag: {
                    "is_buzzing": node._is_buzzing,
                    "last_buzz_time": node._last_buzz_time,
                    "insensitivity_end_time": node._insensitivity_end_time,
                }
                for tag, node in _active_buzzers.items()
            }

        crash_info = (
            f"{'=' * 60}\n"
            f"BUZZER CRASH DUMP - {datetime.now().isoformat()}\n"
            f"{'=' * 60}\n"
            f"Node:         {self.tag_node_name}\n"
            f"Sound type:   {sound_type}\n"
            f"Duration:     {duration:.2f}s\n"
            f"Exception:    {type(exception).__name__}: {exception}\n"
            f"\n--- Active Buzzer Nodes ({len(active_snapshot)}) ---\n"
        )
        for tag, info in active_snapshot.items():
            crash_info += (
                f"  {tag}: buzzing={info['is_buzzing']}, "
                f"last_buzz={info['last_buzz_time']:.3f}, "
                f"insensitivity_end={info['insensitivity_end_time']:.3f}\n"
            )
        crash_info += (
            f"\n--- Traceback ---\n"
            f"{traceback.format_exc()}\n"
            f"\n--- Thread Info ---\n"
            f"Current thread: {threading.current_thread().name}\n"
            f"Active threads: {threading.active_count()}\n"
        )
        for th in threading.enumerate():
            crash_info += f"  - {th.name} (daemon={th.daemon})\n"
        crash_info += f"{'=' * 60}\n"

        # Write to dedicated crash dump file
        try:
            with open(dump_file, "w", encoding="utf-8") as f:
                f.write(crash_info)
        except OSError as write_err:
            _buzzer_logger.warning("Failed to write crash dump file: %s", write_err)

        # Also log to the rolling log
        _buzzer_logger.error(
            "CRASH in node=%s sound=%s duration=%.2f | %s: %s | active_buzzers=%d",
            self.tag_node_name, sound_type, duration,
            type(exception).__name__, exception, len(active_snapshot)
        )
        _buzzer_logger.debug("Full crash dump written to %s", dump_file)

        # Print to console as well for immediate visibility
        print(f"[BUZZER CRASH] {type(exception).__name__}: {exception}")
        print(f"[BUZZER CRASH] Dump saved to: {dump_file}")

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        tag_node_name = f"{node_id}:{self.node_tag}"
        tag_node_sound_type_value_name = f"{tag_node_name}:SoundTypeValue"
        tag_node_duration_value_name = f"{tag_node_name}:DurationValue"
        tag_node_delay_value_name = f"{tag_node_name}:DelayValue"
        tag_node_status_value_name = f"{tag_node_name}:StatusValue"

        # Register this instance in the active buzzers registry
        if not self._registered:
            with _active_buzzers_lock:
                _active_buzzers[tag_node_name] = self
            self._registered = True
        
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
            sound_type = dpg_get_value(tag_node_sound_type_value_name)
            buzz_duration = float(dpg_get_value(tag_node_duration_value_name))
            insensitivity_delay = float(dpg_get_value(tag_node_delay_value_name))
        except (ValueError, TypeError):
            sound_type = self.SOUND_TYPES[0]
            buzz_duration = self.DEFAULT_DURATION
            insensitivity_delay = self.DEFAULT_INSENSITIVITY_DELAY
        
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
            # Priority order: 'BOOL' (standard format) > any boolean field with value True
            if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
                # Standard format from triggers and routers
                should_buzz = node_result['BOOL']
            else:
                # Fallback: look for any boolean field with value True for backward compatibility
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
                args=(buzz_duration, sound_type),
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
        tag_node_name = f"{node_id}:{self.node_tag}"
        # Unregister from active buzzers
        with _active_buzzers_lock:
            _active_buzzers.pop(tag_node_name, None)
        self._registered = False
        # Stop any active buzzing
        try:
            if self._is_buzzing:
                sd.stop()
        except Exception:
            # Ignore errors if no playback is active
            pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_sound_type_value_name = tag_node_name + ':SoundTypeValue'
        tag_node_duration_value_name = tag_node_name + ':DurationValue'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        sound_type_value = dpg_get_value(tag_node_sound_type_value_name)
        duration_value = float(dpg_get_value(tag_node_duration_value_name))
        delay_value = float(dpg_get_value(tag_node_delay_value_name))
        pos = dpg.get_item_pos(tag_node_name)
        
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_sound_type_value_name] = sound_type_value
        setting_dict[tag_node_duration_value_name] = duration_value
        setting_dict[tag_node_delay_value_name] = delay_value
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_sound_type_value_name = tag_node_name + ':SoundTypeValue'
        tag_node_duration_value_name = tag_node_name + ':DurationValue'
        tag_node_delay_value_name = tag_node_name + ':DelayValue'

        sound_type_value = setting_dict.get(tag_node_sound_type_value_name, self.SOUND_TYPES[0])
        duration_value = float(setting_dict.get(tag_node_duration_value_name, self.DEFAULT_DURATION))
        delay_value = float(setting_dict.get(tag_node_delay_value_name, self.DEFAULT_INSENSITIVITY_DELAY))
        
        dpg_set_value(tag_node_sound_type_value_name, sound_type_value)
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
