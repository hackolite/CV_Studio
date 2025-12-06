#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import copy
import datetime
import json
import subprocess

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
#from node_editor.util import convert_cv_to_dpg
from node.basenode import Node

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

def slow_motion_interpolation(prev_frame, next_frame, alpha):
    """ Generates smooth intermediate frame between 2 images """
    return cv2.addWeighted(prev_frame, 1 - alpha, next_frame, alpha, 0)



class FactoryNode:
    node_label = 'VideoWriter'
    node_tag = 'VideoWriter'
    

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

        node = VideoWriterNode()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'

        node.tag_node_button_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Button'
        node.tag_node_button_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':ButtonValue'


        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']


        black_image = np.zeros((small_window_w, small_window_h, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_input01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )


        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_image(node.tag_node_input01_value_name)

            # Add format selector
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_name + ':Format',
                    items=['MP4', 'AVI', 'MKV'],
                    default_value='MP4',
                    width=small_window_w,
                    label='Format',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label=node._start_label,
                    tag=node.tag_node_button_value_name,
                    width=small_window_w,
                    callback=node._recording_button,
                    user_data=node.tag_node_name,
                )

        return node



class VideoWriterNode(Node):
    _ver = '0.0.2'

    node_label = 'VideoWriter'
    node_tag = 'VideoWriter'

    _opencv_setting_dict = None

    _video_writer_dict = {}
    _mkv_metadata_dict = {}  # Store audio and JSON metadata for MKV files
    _mkv_file_handles = {}  # Store file handles for MKV metadata tracks
    _start_label = 'Start'
    _stop_label = 'Stop'

    _prev_frame_flag = False

    def __init__(self):
        pass



    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Input01Value'
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'


        connection_info_src = ''
        print(connection_list)
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = connection_info_src.split(':')[:2]
            connection_info_src = ':'.join(connection_info_src)

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        writer_width = self._opencv_setting_dict['video_writer_width']
        writer_height = self._opencv_setting_dict['video_writer_height']

        frame = node_image_dict.get(connection_info_src, None)
        
        # Get audio and JSON data if available
        audio_data = node_audio_dict.get(connection_info_src, None)
        json_data = node_result_dict.get(connection_info_src, None)


        if frame is not None:
            rec_frame = copy.deepcopy(frame)

            if tag_node_name in self._video_writer_dict:

                writer_frame = cv2.resize(rec_frame,
                                          (writer_width, writer_height),
                                          interpolation=cv2.INTER_CUBIC)
                self._video_writer_dict[tag_node_name].write(writer_frame)
                
                # Write audio and JSON data to MKV metadata tracks if applicable
                if tag_node_name in self._mkv_metadata_dict:
                    metadata = self._mkv_metadata_dict[tag_node_name]
                    file_base = metadata['file_path'].rsplit('.', 1)[0]
                    metadata_dir = file_base + '_metadata'
                    
                    # Write audio chunks if available
                    if audio_data is not None:
                        for slot_idx, audio_chunk in (audio_data.items() if isinstance(audio_data, dict) else enumerate([audio_data])):
                            # Create audio track file if not exists
                            if slot_idx not in metadata['audio_handles']:
                                audio_file = os.path.join(metadata_dir, f'audio_slot_{slot_idx}.jsonl')
                                metadata['audio_handles'][slot_idx] = open(audio_file, 'a')
                            
                            handle = metadata['audio_handles'][slot_idx]
                            # Store audio chunk as JSON (will be written to file)
                            handle.write(json.dumps({'slot': slot_idx, 'data': audio_chunk.tolist() if hasattr(audio_chunk, 'tolist') else str(audio_chunk)}) + '\n')
                            handle.flush()  # Ensure data is written
                    
                    # Write JSON data if available
                    if json_data is not None:
                        for slot_idx, json_chunk in (json_data.items() if isinstance(json_data, dict) else enumerate([json_data])):
                            # Create JSON track file if not exists
                            if slot_idx not in metadata['json_handles']:
                                json_file = os.path.join(metadata_dir, f'json_slot_{slot_idx}.jsonl')
                                metadata['json_handles'][slot_idx] = open(json_file, 'a')
                            
                            handle = metadata['json_handles'][slot_idx]
                            # Write JSON chunk
                            handle.write(json.dumps({'slot': slot_idx, 'data': json_chunk}) + '\n')
                            handle.flush()  # Ensure data is written


                rec_frame = cv2.circle(rec_frame, (10, 10),
                                       50, (0, 0, 255),
                                       thickness=-1)

            texture = self.convert_cv_to_dpg(
                rec_frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(input_value01_tag, texture)
        else:
            label = dpg.get_item_label(tag_node_button_value_name)
            if label == self._stop_label and self._prev_frame_flag:

                self._recording_button(None, None, tag_node_name)

                black_image = np.zeros((small_window_w, small_window_h, 3))

                texture = self.convert_cv_to_dpg(
                    black_image,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(input_value01_tag, texture)

        if frame is not None:
            self._prev_frame_flag = True
        else:
            self._prev_frame_flag = False

        return {"image":frame, "json":None, "audio":None}

    def close(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        if tag_node_name in self._video_writer_dict:
            self._video_writer_dict[tag_node_name].release()
            self._video_writer_dict.pop(tag_node_name)
        
        # Clean up MKV metadata if exists
        if tag_node_name in self._mkv_metadata_dict:
            metadata = self._mkv_metadata_dict[tag_node_name]
            
            # Close all audio handles
            for handle in metadata.get('audio_handles', {}).values():
                if not handle.closed:
                    handle.close()
            
            # Close all JSON handles
            for handle in metadata.get('json_handles', {}).values():
                if not handle.closed:
                    handle.close()
            
            self._mkv_metadata_dict.pop(tag_node_name)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass

    


    def _recording_button(self, sender, data, user_data):
        tag_node_name = user_data
        tag_node_button_value_name = tag_node_name + ':' + self.TYPE_TEXT + ':ButtonValue'

        label = dpg.get_item_label(tag_node_button_value_name)

        if label == self._start_label:

            datetime_now = datetime.datetime.now()
            
            startup_time_text = datetime_now.strftime('%Y%m%d_%H%M%S')
            writer_width = self._opencv_setting_dict['video_writer_width']
            writer_height = self._opencv_setting_dict['video_writer_height']
            writer_fps = self._opencv_setting_dict['video_writer_fps']
            video_writer_directory = self._opencv_setting_dict[
                'video_writer_directory']

            os.makedirs(video_writer_directory, exist_ok=True)

            # Get selected format
            format_tag = tag_node_name + ':Format'
            video_format = dpg_get_value(format_tag)

            if tag_node_name not in self._video_writer_dict:
                if video_format == 'AVI':
                    # Use MJPEG codec for AVI
                    file_path = os.path.join(video_writer_directory, f'{startup_time_text}.avi')
                    self._video_writer_dict[tag_node_name] = cv2.VideoWriter(
                        file_path,
                        cv2.VideoWriter_fourcc(*"MJPG"),
                        writer_fps,
                        (writer_width, writer_height),
                    )
                elif video_format == 'MKV':
                    # Use FFV1 lossless codec for MKV (better for archival)
                    file_path = os.path.join(video_writer_directory, f'{startup_time_text}.mkv')
                    self._video_writer_dict[tag_node_name] = cv2.VideoWriter(
                        file_path,
                        cv2.VideoWriter_fourcc(*"FFV1"),
                        writer_fps,
                        (writer_width, writer_height),
                    )
                    
                    # Initialize metadata tracking for MKV
                    self._mkv_metadata_dict[tag_node_name] = {
                        'audio_handles': {},
                        'json_handles': {},
                        'file_path': file_path,
                    }
                    
                    # Create metadata track files (will be stored alongside video)
                    metadata_dir = os.path.join(video_writer_directory, f'{startup_time_text}_metadata')
                    os.makedirs(metadata_dir, exist_ok=True)
                    
                    # Note: Audio and JSON tracks will be created dynamically when data arrives
                    # This allows us to support variable number of slots from concat node
                    
                else:  # MP4 (default)
                    file_path = os.path.join(video_writer_directory, f'{startup_time_text}.mp4')
                    self._video_writer_dict[tag_node_name] = cv2.VideoWriter(
                        file_path,
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        writer_fps,
                        (writer_width, writer_height),
                    )

            dpg.set_item_label(tag_node_button_value_name, self._stop_label)
        elif label == self._stop_label:

            self._video_writer_dict[tag_node_name].release()
            self._video_writer_dict.pop(tag_node_name)
            
            # Close metadata file handles if MKV
            if tag_node_name in self._mkv_metadata_dict:
                metadata = self._mkv_metadata_dict[tag_node_name]
                
                # Close all audio handles
                for handle in metadata.get('audio_handles', {}).values():
                    handle.close()
                
                # Close all JSON handles
                for handle in metadata.get('json_handles', {}).values():
                    handle.close()
                
                self._mkv_metadata_dict.pop(tag_node_name)

            dpg.set_item_label(tag_node_button_value_name, self._start_label)
