#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import copy
import datetime
import json
import threading
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode


class FactoryNode:
    node_label = 'VideoRecorder'
    node_tag = 'VideoRecorder'
    
    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=[0, 0], callback=None, opencv_setting_dict=None):
        """Adds a VideoRecorder node to the processing graph."""
        
        # Generate tags for Node and its attributes
        node = VideoRecorderNode()
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        
        tag_node_name = node.tag_node_name
        
        # JSON Input for trigger
        node.tag_node_input_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputJson'
        node.tag_node_input_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputJsonValue'
        
        # Image Input
        node.tag_node_input_image_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':InputImage'
        node.tag_node_input_image_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':InputImageValue'
        
        # JSON Data Input for metadata
        node.tag_node_input_data_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputData'
        node.tag_node_input_data_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputDataValue'
        
        # Duration slider
        tag_node_duration_name = tag_node_name + ':Duration'
        tag_node_duration_value_name = tag_node_name + ':DurationValue'
        
        # Format dropdown
        tag_node_format_name = tag_node_name + ':Format'
        tag_node_format_value_name = tag_node_name + ':FormatValue'
        
        # Status indicator
        tag_node_status_name = tag_node_name + ':Status'
        tag_node_status_value_name = tag_node_name + ':StatusValue'

        # Set opencv settings
        node._opencv_setting_dict = opencv_setting_dict or {}
        small_window_w = node._opencv_setting_dict.get('process_width', 240)
        small_window_h = node._opencv_setting_dict.get('process_height', 135)

        # Black image for preview
        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(black_image, small_window_w, small_window_h)

        # Create texture for image preview
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_input_image_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Create themes for status button
        with dpg.theme() as wait_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (100, 100, 100, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (100, 100, 100, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (100, 100, 100, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.theme() as record_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        node._wait_theme = wait_theme
        node._record_theme = record_theme

        # Create node in the GUI
        with dpg.node(tag=node.tag_node_name, parent=parent, label=node.node_label, pos=pos):
            # JSON Input for trigger
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='Trigger JSON (bool)',
                )
            
            # Image Input
            with dpg.node_attribute(
                tag=node.tag_node_input_image_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_image(node.tag_node_input_image_value_name)
            
            # JSON Data Input
            with dpg.node_attribute(
                tag=node.tag_node_input_data_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_data_value_name,
                    default_value='Metadata JSON',
                )
            
            # Format dropdown
            with dpg.node_attribute(
                tag=tag_node_format_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=tag_node_format_value_name,
                    label="Format",
                    items=['avi', 'mp4', 'mkv'],
                    default_value='mp4',
                    width=200,
                )
            
            # Duration slider
            with dpg.node_attribute(
                tag=tag_node_duration_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=tag_node_duration_value_name,
                    label="Duration (s)",
                    default_value=VideoRecorderNode.DEFAULT_DURATION,
                    min_value=1,
                    max_value=300,
                    width=200,
                )
            
            # Status indicator
            with dpg.node_attribute(
                tag=tag_node_status_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                btn = dpg.add_button(
                    label="WAIT",
                    tag=tag_node_status_value_name,
                    enabled=False,
                    width=200
                )
                dpg.bind_item_theme(btn, wait_theme)
                    
        return node


class VideoRecorderNode(BaseNode):
    _ver = '0.0.1'
    
    # Default configuration values
    DEFAULT_DURATION = 10

    def __init__(self):
        super().__init__()
        self.node_label = 'VideoRecorder'
        self.node_tag = 'VideoRecorder'
        self._is_recording = False
        self._recording_start_time = 0
        self._video_writer = None
        self._recording_file_path = None
        self._metadata_list = []  # Store metadata for MKV
        self._frame_count = 0
        self._output_dir = None
        
    def _start_recording(self, file_path, fourcc, fps, frame_size):
        """Initialize video writer for recording"""
        try:
            self._video_writer = cv2.VideoWriter(file_path, fourcc, fps, frame_size)
            if not self._video_writer.isOpened():
                print(f"Failed to open video writer for {file_path}")
                return False
            return True
        except Exception as e:
            print(f"Error starting recording: {e}")
            return False
    
    def _stop_recording(self, tag_node_name):
        """Stop recording and finalize video file"""
        try:
            if self._video_writer is not None:
                self._video_writer.release()
                self._video_writer = None
                
                # Save metadata if MKV format and metadata exists
                if self._recording_file_path and self._recording_file_path.endswith('.mkv'):
                    if self._metadata_list:
                        metadata_file = self._recording_file_path.rsplit('.', 1)[0] + '_metadata.json'
                        try:
                            with open(metadata_file, 'w') as f:
                                json.dump(self._metadata_list, f, indent=2)
                            print(f"Metadata saved to {metadata_file}")
                        except Exception as e:
                            print(f"Error saving metadata: {e}")
                
                self._metadata_list = []
                self._frame_count = 0
                print(f"Recording stopped: {self._recording_file_path}")
                
        except Exception as e:
            print(f"Error stopping recording: {e}")

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        tag_node_name = f"{node_id}:{self.node_tag}"
        tag_node_duration_value_name = f"{tag_node_name}:DurationValue"
        tag_node_format_value_name = f"{tag_node_name}:FormatValue"
        tag_node_status_value_name = f"{tag_node_name}:StatusValue"
        tag_node_input_image_value_name = f"{tag_node_name}:{self.TYPE_IMAGE}:InputImageValue"
        
        # Find connected sources for JSON trigger, image, and metadata
        connection_info_trigger = None
        connection_info_image = None
        connection_info_data = None
        
        for connection_info in connection_list:
            connection_parts = connection_info[0].split(':')
            if len(connection_parts) >= 3:
                connection_type = connection_parts[2]
                
                # Check the target to determine which input this is
                target = connection_info[1]
                
                if 'InputJson' in target and connection_type == self.TYPE_JSON:
                    connection_info_trigger = connection_info[0]
                elif 'InputImage' in target and connection_type == self.TYPE_IMAGE:
                    connection_info_image = connection_info[0]
                elif 'InputData' in target and connection_type == self.TYPE_JSON:
                    connection_info_data = connection_info[0]
        
        # Get trigger JSON data
        trigger_json = None
        if connection_info_trigger:
            src_key = ':'.join(connection_info_trigger.split(':')[:2])
            trigger_json = node_result_dict.get(src_key, {})
        
        # Get image data
        frame = None
        if connection_info_image:
            src_key = ':'.join(connection_info_image.split(':')[:2])
            frame = node_image_dict.get(src_key, None)
        
        # Get metadata JSON
        metadata_json = None
        if connection_info_data:
            src_key = ':'.join(connection_info_data.split(':')[:2])
            metadata_json = node_result_dict.get(src_key, {})
        
        # Get configuration values
        try:
            duration = int(dpg_get_value(tag_node_duration_value_name))
            format_ext = dpg_get_value(tag_node_format_value_name)
        except (ValueError, TypeError):
            duration = self.DEFAULT_DURATION
            format_ext = 'mp4'
        
        current_time = time.time()
        
        # Check if we should trigger recording
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            # Look for any boolean field with value True
            for key, value in trigger_json.items():
                if isinstance(value, bool) and value:
                    should_record = True
                    break
        
        # Update image preview
        if frame is not None:
            small_window_w = self._opencv_setting_dict.get('process_width', 240)
            small_window_h = self._opencv_setting_dict.get('process_height', 135)
            texture = self.convert_cv_to_dpg(frame, small_window_w, small_window_h)
            try:
                dpg_set_value(tag_node_input_image_value_name, texture)
            except (SystemError, AttributeError):
                pass
        
        # State machine logic
        if self._is_recording:
            # Currently recording
            elapsed = current_time - self._recording_start_time
            remaining = duration - elapsed
            
            if remaining > 0 and frame is not None:
                # Continue recording
                try:
                    self._video_writer.write(frame)
                    self._frame_count += 1
                    
                    # Store metadata for MKV
                    if format_ext == 'mkv' and metadata_json:
                        self._metadata_list.append({
                            'frame': self._frame_count,
                            'timestamp': current_time,
                            'data': metadata_json
                        })
                    
                    # Update status
                    try:
                        dpg.configure_item(
                            tag_node_status_value_name,
                            label=f"RECORD ({int(remaining)}s)"
                        )
                        dpg.bind_item_theme(tag_node_status_value_name, self._record_theme)
                    except (SystemError, AttributeError):
                        pass
                        
                except Exception as e:
                    print(f"Error writing frame: {e}")
            else:
                # Recording finished
                self._stop_recording(tag_node_name)
                self._is_recording = False
                
                try:
                    dpg.configure_item(tag_node_status_value_name, label="WAIT")
                    dpg.bind_item_theme(tag_node_status_value_name, self._wait_theme)
                except (SystemError, AttributeError):
                    pass
        
        elif should_record and frame is not None and not self._is_recording:
            # Start new recording
            if self._output_dir is None:
                self._output_dir = self._opencv_setting_dict.get('video_writer_directory', './_VideoRecorder')
            
            os.makedirs(self._output_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.{format_ext}"
            self._recording_file_path = os.path.join(self._output_dir, filename)
            
            # Get FPS from settings
            fps = self._opencv_setting_dict.get('video_writer_fps', 30)
            frame_size = (frame.shape[1], frame.shape[0])
            
            # Determine fourcc codec
            if format_ext == 'avi':
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
            elif format_ext == 'mp4':
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            elif format_ext == 'mkv':
                fourcc = cv2.VideoWriter_fourcc(*'X264')
            else:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            if self._start_recording(self._recording_file_path, fourcc, fps, frame_size):
                self._is_recording = True
                self._recording_start_time = current_time
                self._metadata_list = []
                self._frame_count = 0
                
                # Write first frame
                self._video_writer.write(frame)
                self._frame_count += 1
                
                if format_ext == 'mkv' and metadata_json:
                    self._metadata_list.append({
                        'frame': self._frame_count,
                        'timestamp': current_time,
                        'data': metadata_json
                    })
                
                try:
                    dpg.configure_item(tag_node_status_value_name, label=f"RECORD ({duration}s)")
                    dpg.bind_item_theme(tag_node_status_value_name, self._record_theme)
                except (SystemError, AttributeError):
                    pass
        
        else:
            # Not recording, update status
            try:
                dpg.configure_item(tag_node_status_value_name, label="WAIT")
                dpg.bind_item_theme(tag_node_status_value_name, self._wait_theme)
            except (SystemError, AttributeError):
                pass
        
        return {"image": None, "json": None, "audio": None}

    def close(self, node_id):
        """Clean up when node is closed"""
        tag_node_name = f"{node_id}:{self.node_tag}"
        if self._is_recording:
            self._stop_recording(tag_node_name)
            self._is_recording = False

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_duration_value_name = tag_node_name + ':DurationValue'
        tag_node_format_value_name = tag_node_name + ':FormatValue'

        duration_value = int(dpg_get_value(tag_node_duration_value_name))
        format_value = dpg_get_value(tag_node_format_value_name)
        pos = dpg.get_item_pos(tag_node_name)
        
        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_duration_value_name] = duration_value
        setting_dict[tag_node_format_value_name] = format_value
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_duration_value_name = tag_node_name + ':DurationValue'
        tag_node_format_value_name = tag_node_name + ':FormatValue'

        duration_value = int(setting_dict.get(tag_node_duration_value_name, self.DEFAULT_DURATION))
        format_value = setting_dict.get(tag_node_format_value_name, 'mp4')
        
        dpg_set_value(tag_node_duration_value_name, duration_value)
        dpg_set_value(tag_node_format_value_name, format_value)


# Test code to verify that the node displays correctly
if __name__ == "__main__":
    dpg.create_context()
    
    opencv_setting_dict = {
        'process_width': 240,
        'process_height': 135,
        'video_writer_fps': 30,
        'video_writer_directory': './_VideoRecorder'
    }
    
    with dpg.window(label="Test VideoRecorder Node", width=800, height=600):
        with dpg.node_editor(label="Node Editor"):
            factory = FactoryNode()
            factory.add_node(
                parent=dpg.last_item(), 
                node_id=1, 
                pos=[100, 100],
                opencv_setting_dict=opencv_setting_dict
            )
    
    dpg.create_viewport(title='Test VideoRecorder Node', width=900, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
