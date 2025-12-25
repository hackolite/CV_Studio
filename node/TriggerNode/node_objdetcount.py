#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode
from node.DLNode.object_detection.coco_class_names import coco_class_names


def get_class_dropdown_items():
    """Generate dropdown items with class IDs and names from COCO dataset"""
    items = ["All"]
    # Add common COCO classes with their names
    for class_id, class_name in coco_class_names.items():
        items.append(f"{class_id}: {class_name}")
    return items


class FactoryNode:
    node_label = 'ObjDetCount'
    node_tag = 'ObjDetCount'
    
    def __init__(self):
        pass


class Node(BaseNode):
    _ver = '0.0.1'

    node_label = 'ObjDetCount'
    node_tag = 'ObjDetCount'

    _opencv_setting_dict = None

    def __init__(self):
        # Detection accumulator: stores timestamps of detections
        self.detection_timestamps = deque()
        # Current class names from detection JSON
        self.current_class_names = {}

    def add_node(
        self,
        parent,
        node_id,
        pos=[0, 0],
        opencv_setting_dict=None,
        callback=None,
    ):
        # Tag names
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_name = tag_node_name + ':' + self.TYPE_JSON + ':Input01'
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Input01Value'
        tag_node_output01_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Output01Value'

        # Control inputs
        tag_node_class_select_name = tag_node_name + ':ClassSelect'
        tag_node_class_select_value_name = tag_node_name + ':ClassSelectValue'
        
        tag_node_min_threshold_name = tag_node_name + ':MinThreshold'
        tag_node_min_threshold_value_name = tag_node_name + ':MinThresholdValue'
        
        tag_node_max_threshold_name = tag_node_name + ':MaxThreshold'
        tag_node_max_threshold_value_name = tag_node_name + ':MaxThresholdValue'
        
        tag_node_window_duration_name = tag_node_name + ':WindowDuration'
        tag_node_window_duration_value_name = tag_node_name + ':WindowDurationValue'

        # OpenCV settings
        self._opencv_setting_dict = opencv_setting_dict
        small_window_w = self._opencv_setting_dict.get('process_width', 640)
        small_window_h = self._opencv_setting_dict.get('process_height', 480)

        # Create node in the GUI
        with dpg.node(
                tag=tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):
            # JSON Input
            with dpg.node_attribute(
                    tag=tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=tag_node_input01_value_name,
                    default_value='Input detection JSON',
                )

            # Class selection dropdown
            with dpg.node_attribute(
                    tag=tag_node_class_select_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=tag_node_class_select_value_name,
                    label="Class to Count",
                    items=get_class_dropdown_items(),
                    default_value="All",
                    width=small_window_w - 100,
                )

            # Min threshold
            with dpg.node_attribute(
                    tag=tag_node_min_threshold_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_int(
                    tag=tag_node_min_threshold_value_name,
                    label="Min Threshold",
                    default_value=0,
                    min_value=0,
                    min_clamped=True,
                    width=small_window_w - 150,
                )

            # Max threshold
            with dpg.node_attribute(
                    tag=tag_node_max_threshold_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_int(
                    tag=tag_node_max_threshold_value_name,
                    label="Max Threshold",
                    default_value=10,
                    min_value=0,
                    min_clamped=True,
                    width=small_window_w - 150,
                )

            # Window duration in seconds
            with dpg.node_attribute(
                    tag=tag_node_window_duration_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_float(
                    tag=tag_node_window_duration_value_name,
                    label="Window (seconds)",
                    default_value=5.0,
                    min_value=0.1,
                    min_clamped=True,
                    width=small_window_w - 150,
                    format="%.1f",
                )

            # JSON Output
            with dpg.node_attribute(
                    tag=tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=tag_node_output01_value_name,
                    default_value='Output trigger JSON',
                )

        self.tag_node_name = tag_node_name
        return self

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_class_select_value_name = tag_node_name + ':ClassSelectValue'
        tag_node_min_threshold_value_name = tag_node_name + ':MinThresholdValue'
        tag_node_max_threshold_value_name = tag_node_name + ':MaxThresholdValue'
        tag_node_window_duration_value_name = tag_node_name + ':WindowDurationValue'

        # Find connected source for JSON data
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)
                break

        # Get detection data
        node_result = node_result_dict.get(connection_info_src, {})
        
        # Get configuration values
        try:
            selected_class = dpg_get_value(tag_node_class_select_value_name)
            min_threshold = int(dpg_get_value(tag_node_min_threshold_value_name))
            max_threshold = int(dpg_get_value(tag_node_max_threshold_value_name))
            window_duration = float(dpg_get_value(tag_node_window_duration_value_name))
        except:
            # Default values if there's an error
            selected_class = "All"
            min_threshold = 0
            max_threshold = 10
            window_duration = 5.0

        current_time = time.time()
        
        # Update class names if available in detection JSON
        if node_result and isinstance(node_result, dict):
            class_names = node_result.get('class_names', {})
            if class_names and class_names != self.current_class_names:
                # Update the dropdown with new class names
                self.current_class_names = class_names
                # Regenerate dropdown items
                new_items = ["All"]
                for class_id, class_name in class_names.items():
                    # Handle both int and string keys
                    try:
                        class_id_int = int(class_id) if isinstance(class_id, str) else class_id
                        new_items.append(f"{class_id_int}: {class_name}")
                    except (ValueError, TypeError):
                        pass
                
                # Update combo box items
                try:
                    dpg.configure_item(tag_node_class_select_value_name, items=new_items)
                except:
                    pass

        # Process detections
        if node_result and isinstance(node_result, dict):
            class_ids = node_result.get('class_ids', [])
            
            if class_ids:
                # Determine which class to count
                if selected_class == "All":
                    # Count all detections
                    count = len(class_ids)
                    for _ in range(count):
                        self.detection_timestamps.append(current_time)
                elif ":" in selected_class:
                    # Parse "ID: name" format
                    try:
                        target_class_id = int(selected_class.split(":")[0].strip())
                        # Count only detections of the selected class
                        count = sum(1 for cid in class_ids if int(cid) == target_class_id)
                        for _ in range(count):
                            self.detection_timestamps.append(current_time)
                    except (ValueError, IndexError):
                        pass
        
        # Clean up old timestamps outside the sliding window
        cutoff_time = current_time - window_duration
        while self.detection_timestamps and self.detection_timestamps[0] < cutoff_time:
            self.detection_timestamps.popleft()
        
        # Count detections in the current window
        count_in_window = len(self.detection_timestamps)
        
        # Determine if threshold is exceeded
        # Trigger is True if count is within [min_threshold, max_threshold]
        # If max_threshold is 0, it means no upper limit
        trigger_active = False
        
        if max_threshold == 0:
            # No upper limit, only check minimum
            trigger_active = (count_in_window >= min_threshold)
        else:
            # Check both min and max thresholds
            trigger_active = (min_threshold <= count_in_window <= max_threshold)
        
        # Create output JSON
        output_json = {"BOOL": trigger_active}
        
        return {"image": None, "json": output_json, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_class_select_value_name = tag_node_name + ':ClassSelectValue'
        tag_node_min_threshold_value_name = tag_node_name + ':MinThresholdValue'
        tag_node_max_threshold_value_name = tag_node_name + ':MaxThresholdValue'
        tag_node_window_duration_value_name = tag_node_name + ':WindowDurationValue'

        selected_class = dpg_get_value(tag_node_class_select_value_name)
        min_threshold = dpg_get_value(tag_node_min_threshold_value_name)
        max_threshold = dpg_get_value(tag_node_max_threshold_value_name)
        window_duration = dpg_get_value(tag_node_window_duration_value_name)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[tag_node_class_select_value_name] = selected_class
        setting_dict[tag_node_min_threshold_value_name] = min_threshold
        setting_dict[tag_node_max_threshold_value_name] = max_threshold
        setting_dict[tag_node_window_duration_value_name] = window_duration

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_class_select_value_name = tag_node_name + ':ClassSelectValue'
        tag_node_min_threshold_value_name = tag_node_name + ':MinThresholdValue'
        tag_node_max_threshold_value_name = tag_node_name + ':MaxThresholdValue'
        tag_node_window_duration_value_name = tag_node_name + ':WindowDurationValue'

        selected_class = setting_dict.get(tag_node_class_select_value_name, "All")
        min_threshold = setting_dict.get(tag_node_min_threshold_value_name, 0)
        max_threshold = setting_dict.get(tag_node_max_threshold_value_name, 10)
        window_duration = setting_dict.get(tag_node_window_duration_value_name, 5.0)

        dpg_set_value(tag_node_class_select_value_name, selected_class)
        dpg_set_value(tag_node_min_threshold_value_name, min_threshold)
        dpg_set_value(tag_node_max_threshold_value_name, max_threshold)
        dpg_set_value(tag_node_window_duration_value_name, window_duration)
