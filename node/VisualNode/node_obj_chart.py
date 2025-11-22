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
from node.basenode import Node

import matplotlib
matplotlib.use('Agg')  # force backend non-GUI
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg


class FactoryNode:
    node_label = 'ObjChart'
    node_tag = 'ObjChart'
    

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

        node = Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        # Time aggregation dropdown
        node.tag_node_time_agg_name = node.tag_node_name + ':TimeAggregation'
        node.tag_node_time_agg_value_name = node.tag_node_name + ':TimeAggregationValue'
        
        # Class selection slots
        node.tag_node_class_slots_name = node.tag_node_name + ':ClassSlots'
        node.tag_node_add_slot_name = node.tag_node_name + ':AddSlot'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']


        black_image = np.zeros((small_window_h, small_window_w, 3))
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
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )


        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input image (optional)',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Input detection JSON',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Time aggregation dropdown
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_time_agg_value_name,
                    label="Time Unit",
                    items=["minute", "hour"],
                    default_value="minute",
                    width=small_window_w - 100,
                )

            # Container for class selection slots
            with dpg.node_attribute(
                    tag=node.tag_node_class_slots_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                # Initial class slot
                dpg.add_combo(
                    tag=f"{node.tag_node_name}:ClassSlot:0",
                    label="Class 1",
                    items=["All", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                    default_value="All",
                    width=small_window_w - 100,
                )

            # Add slot button
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=node.tag_node_add_slot_name,
                    label="Add Class Slot",
                    callback=lambda s, a, u: Node.add_class_slot_callback(s, a, u),
                    user_data=node.tag_node_name,
                    width=small_window_w - 100,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'ObjChart'
    node_tag = 'ObjChart'

    _class_slot_counter = 0
    
    def __init__(self, opencv_setting_dict=None):
        super().__init__()

        if opencv_setting_dict is None:
            # Default values
            opencv_setting_dict = {
                'process_height': 400,
                'process_width': 600
            }

        self._opencv_setting_dict = opencv_setting_dict
        
        # Data accumulation by time buckets
        # Structure: {class_id: {time_bucket: count}}
        self.time_counts = defaultdict(lambda: defaultdict(int))
        
        # Keep track of last N time buckets for visualization
        self.max_buckets = 30
        
        self._class_slot_counter = 1  # Start at 1 since we have one initial slot

    @staticmethod
    def add_class_slot_callback(sender, app_data, user_data):
        """Callback to add a new class selection slot"""
        node_tag = user_data
        class_slots_tag = f"{node_tag}:ClassSlots"
        
        # Find current number of slots
        if dpg.does_item_exist(class_slots_tag):
            children = dpg.get_item_children(class_slots_tag, slot=1)
            slot_count = len(children) if children else 0
            
            new_slot_tag = f"{node_tag}:ClassSlot:{slot_count}"
            
            # Add new combo to the class slots container
            dpg.add_combo(
                tag=new_slot_tag,
                label=f"Class {slot_count + 1}",
                items=["All", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                default_value="All",
                width=500,
                parent=class_slots_tag,
            )

    def get_time_bucket(self, time_unit):
        """Get current time bucket based on aggregation unit"""
        now = datetime.now()
        if time_unit == "minute":
            return now.replace(second=0, microsecond=0)
        else:  # hour
            return now.replace(minute=0, second=0, microsecond=0)

    def render_chart(self, time_unit, selected_classes, class_names_dict):
        """Render the chart as an image using matplotlib"""
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        
        # Get sorted time buckets (last N buckets)
        all_buckets = set()
        for class_data in self.time_counts.values():
            all_buckets.update(class_data.keys())
        
        sorted_buckets = sorted(all_buckets)[-self.max_buckets:]
        
        if not sorted_buckets:
            # No data yet, create empty chart
            ax.text(0.5, 0.5, 'Waiting for detection data...', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 10)
        else:
            # Prepare data for selected classes
            x_labels = []
            for bucket in sorted_buckets:
                if time_unit == "minute":
                    x_labels.append(bucket.strftime("%H:%M"))
                else:
                    x_labels.append(bucket.strftime("%H:00"))
            
            x_pos = np.arange(len(x_labels))
            
            # Plot bars for each selected class
            bar_width = 0.8 / max(len(selected_classes), 1)
            
            for idx, class_id in enumerate(selected_classes):
                counts = [self.time_counts[class_id].get(bucket, 0) for bucket in sorted_buckets]
                offset = (idx - len(selected_classes)/2 + 0.5) * bar_width
                
                # Get class name for legend
                if class_id == "All":
                    label = "All Classes"
                elif class_names_dict and str(class_id) in class_names_dict:
                    label = f"{class_id}: {class_names_dict[str(class_id)]}"
                else:
                    label = f"Class {class_id}"
                
                ax.bar(x_pos + offset, counts, bar_width, label=label)
            
            ax.set_xlabel(f'Time ({time_unit})')
            ax.set_ylabel('Detection Count')
            ax.set_title('Object Detection Accumulation Over Time')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(x_labels, rotation=45, ha='right')
            ax.legend(loc='upper left')
            ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        # Render to image
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        image = np.asarray(canvas.buffer_rgba())[:, :, :3]
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        plt.close(fig)
        
        return image

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        time_agg_tag = tag_node_name + ':TimeAggregationValue'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get time aggregation unit
        time_unit = dpg_get_value(time_agg_tag)

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
        
        if use_pref_counter:
            start_time = time.monotonic()

        chart_image = None
        
        if node_result and isinstance(node_result, dict):
            # Extract detection data
            class_ids = node_result.get('class_ids', [])
            class_names = node_result.get('class_names', {})
            
            if class_ids:
                # Get current time bucket
                current_bucket = self.get_time_bucket(time_unit)
                
                # Accumulate counts for each class
                for class_id in class_ids:
                    self.time_counts[int(class_id)][current_bucket] += 1
                    self.time_counts["All"][current_bucket] += 1
            
            # Get selected classes from slots
            selected_classes = []
            class_slots_tag = f"{tag_node_name}:ClassSlots"
            
            if dpg.does_item_exist(class_slots_tag):
                children = dpg.get_item_children(class_slots_tag, slot=1)
                if children:
                    for child in children:
                        try:
                            selected_value = dpg_get_value(child)
                            if selected_value and selected_value != "":
                                if selected_value == "All":
                                    selected_classes.append("All")
                                else:
                                    selected_classes.append(int(selected_value))
                        except:
                            pass
            
            # If no classes selected, default to "All"
            if not selected_classes:
                selected_classes = ["All"]
            
            # Render chart
            chart_image = self.render_chart(time_unit, selected_classes, class_names)

        else:
            # No detection data yet, render empty chart
            chart_image = self.render_chart(time_unit, ["All"], {})

        if use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')

        if chart_image is not None:
            texture = self.convert_cv_to_dpg(
                chart_image,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": chart_image, "json": None, "audio": None}


    def close(self, node_id):
        pass


    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        time_agg_tag = tag_node_name + ':TimeAggregationValue'

        time_unit = dpg_get_value(time_agg_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[time_agg_tag] = time_unit
        
        # Save class slot selections
        class_slots_tag = f"{tag_node_name}:ClassSlots"
        if dpg.does_item_exist(class_slots_tag):
            children = dpg.get_item_children(class_slots_tag, slot=1)
            if children:
                for idx, child in enumerate(children):
                    try:
                        selected_value = dpg_get_value(child)
                        setting_dict[f"{tag_node_name}:ClassSlot:{idx}"] = selected_value
                    except:
                        pass

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        time_agg_tag = tag_node_name + ':TimeAggregationValue'

        time_unit = setting_dict.get(time_agg_tag, "minute")
        dpg_set_value(time_agg_tag, time_unit)
        
        # Restore class slot selections
        class_slots_tag = f"{tag_node_name}:ClassSlots"
        if dpg.does_item_exist(class_slots_tag):
            children = dpg.get_item_children(class_slots_tag, slot=1)
            if children:
                for idx, child in enumerate(children):
                    slot_key = f"{tag_node_name}:ClassSlot:{idx}"
                    if slot_key in setting_dict:
                        try:
                            dpg_set_value(child, setting_dict[slot_key])
                        except:
                            pass
