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
from node.basenode import Node as Chart
from node.DLNode.object_detection.coco_class_names import coco_class_names

import matplotlib
matplotlib.use('Agg')  # force backend non-GUI
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg


def get_class_dropdown_items():
    """Generate dropdown items with class IDs and names from COCO dataset"""
    items = ["All"]
    # Add common COCO classes with their names
    for class_id, class_name in coco_class_names.items():
        items.append(f"{class_id}: {class_name}")
    return items


def get_dict_dropdown_items(data_dict):
    """Generate dropdown items from dictionary keys."""
    if not isinstance(data_dict, dict):
        return []
    return [str(key) for key in data_dict.keys()]


class FactoryNode:
    node_label = 'Chart'
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
        
        # Chart type dropdown
        node.tag_node_chart_type_name = node.tag_node_name + ':ChartType'
        node.tag_node_chart_type_value_name = node.tag_node_name + ':ChartTypeValue'
        
        # Class selection slots
        node.tag_node_class_slots_name = node.tag_node_name + ':ClassSlots'
        node.tag_node_add_slot_name = node.tag_node_name + ':AddSlot'
        
        # Download button
        node.tag_node_download_button_name = node.tag_node_name + ':DownloadButton'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']


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
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Create file dialog for saving chart image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            modal=True,
            height=int(small_window_h * 3),
            default_filename=f"objchart_{timestamp}",
            callback=Node.save_chart_callback,
            id=f"chart_save:{node_id}",
            user_data=node,
        ):
            dpg.add_file_extension(".png", color=(0, 255, 0, 255))
            dpg.add_file_extension(".*")


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
                    items=["second", "minute", "hour"],
                    default_value="minute",
                    width=small_window_w - 100,
                )

            # Chart type dropdown
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_chart_type_value_name,
                    label="Chart Type",
                    items=["bar", "line", "area"],
                    default_value="bar",
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
                    items=get_class_dropdown_items(),
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
                    user_data=(node.tag_node_name, small_window_w - 100),
                    width=small_window_w - 100,
                )

            # Download button
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=node.tag_node_download_button_name,
                    label="Download Chart Image",
                    callback=lambda: dpg.show_item(f"chart_save:{node_id}"),
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

        # Store node instance for file dialog callback access
        Node._node_instances[node_id] = node

        return node


class Node(Chart):
    _ver = '0.0.1'

    node_label = 'Chart'
    node_tag = 'ObjChart'
    
    # Class variable to store node instances for file dialog callbacks
    _node_instances = {}
    
    def __init__(self, opencv_setting_dict=None):
        super().__init__()

        if opencv_setting_dict is None:
            # Default values
            opencv_setting_dict = {
                'process_height': 400,
                'process_width': 600
            }

        self._opencv_setting_dict = opencv_setting_dict
        
        # Data accumulation by time buckets with 24h round-robin
        # Structure: {class_id: {time_bucket: count}}
        self.time_counts = defaultdict(lambda: defaultdict(int))
        
        # Accumulator for computing averages (OnlineTraining distillation scores)
        # Structure: {key: {time_bucket: [sum, count]}}
        self._avg_accumulators = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
        
        # 24-hour data retention (1440 minutes max)
        self.max_data_age_hours = 24
        
        # Store current chart image for download
        self.current_chart_image = None
        
        # Performance optimization: throttle chart rendering
        self.last_render_time = 0
        self.render_interval = 1.0  # Render chart at most once per second
        self.cached_chart_image = None

    @staticmethod
    def add_class_slot_callback(sender, app_data, user_data):
        """Callback to add a new class selection slot"""
        node_tag, combo_width = user_data
        class_slots_tag = f"{node_tag}:ClassSlots"
        
        # Find current number of slots
        if dpg.does_item_exist(class_slots_tag):
            children = dpg.get_item_children(class_slots_tag, slot=1)
            slot_count = len(children) if children else 0
            
            new_slot_tag = f"{node_tag}:ClassSlot:{slot_count}"
            dropdown_items = Node.get_slot_dropdown_items(class_slots_tag)
            default_value = dropdown_items[0] if dropdown_items else ""
            
            # Add new combo to the class slots container
            dpg.add_combo(
                tag=new_slot_tag,
                label=f"Class {slot_count + 1}",
                items=dropdown_items,
                default_value=default_value,
                width=combo_width,
                parent=class_slots_tag,
            )

    @staticmethod
    def get_slot_dropdown_items(class_slots_tag):
        """Get current dropdown items from existing class slots."""
        if dpg.does_item_exist(class_slots_tag):
            children = dpg.get_item_children(class_slots_tag, slot=1)
            if children:
                try:
                    config = dpg.get_item_configuration(children[0])
                    items = config.get("items")
                    if isinstance(items, list) and items:
                        return items
                except (KeyError, TypeError, AttributeError):
                    pass
        return get_class_dropdown_items()
    
    @staticmethod
    def save_chart_callback(sender, app_data, user_data):
        """Callback to save the chart image using file dialog (similar to video/selectmovie pattern)"""
        node_instance = user_data
        
        # Check if user actually selected a file (not cancelled)
        if app_data.get("file_name") and app_data["file_name"] != ".":
            file_path = app_data["file_path_name"]
            
            # Ensure .png extension
            if not file_path.lower().endswith('.png'):
                file_path += '.png'
            
            if node_instance and hasattr(node_instance, 'current_chart_image'):
                chart_image = node_instance.current_chart_image
                
                if chart_image is not None:
                    # Save the image
                    try:
                        cv2.imwrite(file_path, chart_image)
                        print(f"✅ Chart image saved to: {file_path}")
                    except Exception as e:
                        print(f"❌ Error saving chart image: {e}")
                else:
                    print("⚠️ No chart image available to download")
            else:
                print("❌ Could not access node instance or chart image")

    def get_time_bucket(self, time_unit):
        """Get current time bucket based on aggregation unit"""
        now = datetime.now()
        if time_unit == "second":
            return now.replace(microsecond=0)
        elif time_unit == "minute":
            return now.replace(second=0, microsecond=0)
        else:  # hour
            return now.replace(minute=0, second=0, microsecond=0)

    def cleanup_old_data(self):
        """Remove data older than 24 hours (round-robin)"""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=self.max_data_age_hours)
        
        # Clean up old buckets from all classes
        for class_id in list(self.time_counts.keys()):
            buckets_to_remove = [
                bucket for bucket in self.time_counts[class_id].keys()
                if bucket < cutoff_time
            ]
            for bucket in buckets_to_remove:
                del self.time_counts[class_id][bucket]
            
            # Remove empty class entries
            if not self.time_counts[class_id]:
                del self.time_counts[class_id]

        # Clean up old accumulator buckets
        for key in list(self._avg_accumulators.keys()):
            buckets_to_remove = [
                bucket for bucket in self._avg_accumulators[key].keys()
                if bucket < cutoff_time
            ]
            for bucket in buckets_to_remove:
                del self._avg_accumulators[key][bucket]
            if not self._avg_accumulators[key]:
                del self._avg_accumulators[key]

    def update_class_slot_items(self, tag_node_name, items):
        """Update class slot combos with new available items."""
        class_slots_tag = f"{tag_node_name}:ClassSlots"
        if not dpg.does_item_exist(class_slots_tag):
            return

        normalized_items = [normalized for normalized in (str(item) for item in items) if normalized]
        if not normalized_items:
            return

        children = dpg.get_item_children(class_slots_tag, slot=1)
        if not children:
            return

        for child in children:
            try:
                previous_value = dpg_get_value(child)
                dpg.configure_item(child, items=normalized_items)
                if previous_value not in normalized_items:
                    dpg_set_value(child, normalized_items[0])
            except (KeyError, TypeError, AttributeError, ValueError):
                pass

    def render_chart(self, time_unit, selected_classes, class_names_dict, chart_type="bar"):
        """Render the chart as an image using matplotlib
        
        Args:
            time_unit: "minute" or "hour"
            selected_classes: list of class IDs to display
            class_names_dict: mapping of class ID to class name from detection JSON
            chart_type: "bar", "line", or "area" for visualization type
        """
        # Merge class_names_dict with COCO class names (COCO as fallback)
        # Only add names for selected classes to improve performance
        merged_class_names = {}
        for class_id in selected_classes:
            if class_id != "All":
                class_id_str = str(class_id)
                # First try detection JSON, then COCO names
                if class_names_dict and class_id_str in class_names_dict:
                    merged_class_names[class_id_str] = class_names_dict[class_id_str]
                elif class_id in coco_class_names:
                    merged_class_names[class_id_str] = coco_class_names[class_id]
        
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        
        # Calculate max_buckets based on time unit to show full 24h round-robin
        # This ensures the chart displays all available data within 24 hours
        if time_unit == "second":
            max_buckets = 1440  # 24 minutes × 60 seconds = 1440 seconds (show last 24 minutes for practical display)
        elif time_unit == "minute":
            max_buckets = 1440  # 24 hours × 60 minutes = full 24 hours
        else:  # hour
            max_buckets = 24    # 24 hours = full 24 hours
        
        # Get sorted time buckets (last N buckets)
        all_buckets = set()
        for class_data in self.time_counts.values():
            all_buckets.update(class_data.keys())
        
        sorted_buckets = sorted(all_buckets)[-max_buckets:]
        
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
                if time_unit == "second":
                    x_labels.append(bucket.strftime("%H:%M:%S"))
                elif time_unit == "minute":
                    x_labels.append(bucket.strftime("%H:%M"))
                else:
                    x_labels.append(bucket.strftime("%H:00"))
            
            x_pos = np.arange(len(x_labels))
            
            # Check if we're dealing with dB data (special case)
            is_db_data = "dB" in selected_classes
            
            # Plot based on chart type
            if chart_type == "bar":
                # Plot bars for each selected class
                bar_width = 0.8 / max(len(selected_classes), 1)
                
                for idx, class_id in enumerate(selected_classes):
                    counts = [self.time_counts[class_id].get(bucket, 0) for bucket in sorted_buckets]
                    offset = (idx - len(selected_classes)/2 + 0.5) * bar_width
                    
                    # Get class name for legend
                    if class_id == "All":
                        label = "All Classes"
                    elif class_id == "dB":
                        label = "Decibel Intensity (dB)"
                    elif isinstance(class_id, str) and class_id in merged_class_names:
                        label = merged_class_names[class_id]
                    elif str(class_id) in merged_class_names:
                        label = f"{class_id}: {merged_class_names[str(class_id)]}"
                    else:
                        label = f"Class {class_id}"
                    
                    ax.bar(x_pos + offset, counts, bar_width, label=label)
            
            elif chart_type == "line":
                # Plot lines for each selected class
                for class_id in selected_classes:
                    counts = [self.time_counts[class_id].get(bucket, 0) for bucket in sorted_buckets]
                    
                    # Get class name for legend
                    if class_id == "All":
                        label = "All Classes"
                    elif class_id == "dB":
                        label = "Decibel Intensity (dB)"
                    elif isinstance(class_id, str) and class_id in merged_class_names:
                        label = merged_class_names[class_id]
                    elif str(class_id) in merged_class_names:
                        label = f"{class_id}: {merged_class_names[str(class_id)]}"
                    else:
                        label = f"Class {class_id}"
                    
                    ax.plot(x_pos, counts, marker='o', label=label, linewidth=2)
            
            elif chart_type == "area":
                # Plot area chart (stacked) for each selected class
                counts_by_class = []
                labels = []
                
                for class_id in selected_classes:
                    counts = [self.time_counts[class_id].get(bucket, 0) for bucket in sorted_buckets]
                    counts_by_class.append(counts)
                    
                    # Get class name for legend
                    if class_id == "All":
                        label = "All Classes"
                    elif class_id == "dB":
                        label = "Decibel Intensity (dB)"
                    elif isinstance(class_id, str) and class_id in merged_class_names:
                        label = merged_class_names[class_id]
                    elif str(class_id) in merged_class_names:
                        label = f"{class_id}: {merged_class_names[str(class_id)]}"
                    else:
                        label = f"Class {class_id}"
                    labels.append(label)
                
                ax.stackplot(x_pos, *counts_by_class, labels=labels, alpha=0.7)
            
            # Detect if this is numeric metric data (e.g. SystemResource)
            is_metric_data = any(
                isinstance(c, str) and c not in ("All", "dB")
                for c in selected_classes
            )

            # Set appropriate axis labels based on data type
            ax.set_xlabel(f'Time ({time_unit})')
            if is_db_data:
                ax.set_ylabel('Decibel Intensity (dB)')
                ax.set_title('Microphone Decibel Intensity Over Time')
            elif is_metric_data:
                ax.set_ylabel('Value')
                ax.set_title('System Metrics Over Time')
            else:
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
        chart_type_tag = tag_node_name + ':ChartTypeValue'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Get time aggregation unit and chart type
        time_unit = dpg_get_value(time_agg_tag)
        chart_type = dpg_get_value(chart_type_tag)
        
        # Cleanup old data (24h round-robin)
        self.cleanup_old_data()

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

        # Check if we should render a new chart or use cached version
        current_time = time.time()
        should_render = (current_time - self.last_render_time) >= self.render_interval
        
        chart_image = None
        
        if node_result and isinstance(node_result, dict):
            # Check if this is microphone dB intensity data
            if 'db_value' in node_result and 'output_mode' in node_result and node_result.get('output_mode') == 'dB Intensity':
                # Handle microphone dB intensity data
                db_value = node_result.get('db_value', 0)
                
                # Get current time bucket
                current_bucket = self.get_time_bucket(time_unit)
                
                # Store dB value as a special "dB" class identifier
                self.time_counts["dB"][current_bucket] = db_value
                
                # Render chart with dB data only if render interval has passed
                if should_render or self.cached_chart_image is None:
                    selected_classes = ["dB"]
                    chart_image = self.render_chart(time_unit, selected_classes, {"dB": "Decibel Intensity"}, chart_type)
                    self.cached_chart_image = chart_image
                    self.last_render_time = current_time
                else:
                    chart_image = self.cached_chart_image
            elif 'distillation_losses' in node_result and isinstance(
                node_result.get('distillation_losses'), dict
            ):
                # Handle OnlineTraining distillation loss metrics
                # distillation_losses is a flat numeric dict: {avg_iou, score, class_accuracy, ...}
                loss_data = node_result['distillation_losses']
                current_bucket = self.get_time_bucket(time_unit)

                for key, value in loss_data.items():
                    if isinstance(value, (int, float)):
                        # Accumulate sum and count to compute running average
                        acc = self._avg_accumulators[key][current_bucket]
                        acc[0] += value
                        acc[1] += 1
                        self.time_counts[key][current_bucket] = acc[0] / acc[1]

                self.update_class_slot_items(tag_node_name, get_dict_dropdown_items(loss_data))

                # Determine which series to display from class slots or default to all keys
                selected_classes = []
                class_slots_tag = f"{tag_node_name}:ClassSlots"
                if dpg.does_item_exist(class_slots_tag):
                    children = dpg.get_item_children(class_slots_tag, slot=1)
                    if children:
                        for child in children:
                            try:
                                selected_value = dpg_get_value(child)
                                if selected_value and selected_value != "":
                                    if selected_value in loss_data:
                                        selected_classes.append(selected_value)
                            except (ValueError, TypeError):
                                pass

                if not selected_classes:
                    # Default: show avg_iou, score, class_accuracy
                    selected_classes = [
                        k for k in ['avg_iou', 'score', 'class_accuracy']
                        if k in loss_data
                    ]
                    if not selected_classes:
                        selected_classes = list(loss_data.keys())

                # Build class_names_dict from keys
                class_names_dict = {k: k for k in loss_data}

                if should_render or self.cached_chart_image is None:
                    chart_image = self.render_chart(time_unit, selected_classes, class_names_dict, chart_type)
                    self.cached_chart_image = chart_image
                    self.last_render_time = current_time
                else:
                    chart_image = self.cached_chart_image
            elif 'class_ids' not in node_result and all(
                isinstance(v, (int, float)) for v in node_result.values()
            ) and node_result:
                # Handle flat numeric dict (e.g. SystemResource output)
                # Each key becomes a series plotted over time
                current_bucket = self.get_time_bucket(time_unit)

                for key, value in node_result.items():
                    self.time_counts[key][current_bucket] = value

                self.update_class_slot_items(tag_node_name, get_dict_dropdown_items(node_result))

                # Determine which series to display from class slots or default to all keys
                selected_classes = []
                class_slots_tag = f"{tag_node_name}:ClassSlots"
                if dpg.does_item_exist(class_slots_tag):
                    children = dpg.get_item_children(class_slots_tag, slot=1)
                    if children:
                        for child in children:
                            try:
                                selected_value = dpg_get_value(child)
                                if selected_value and selected_value != "":
                                    if selected_value in node_result:
                                        selected_classes.append(selected_value)
                            except (ValueError, TypeError):
                                pass

                if not selected_classes:
                    # Default: show percent-type metrics for readability
                    percent_keys = [k for k in node_result if 'percent' in k]
                    selected_classes = percent_keys if percent_keys else list(node_result.keys())

                # Build class_names_dict from keys
                class_names_dict = {k: k for k in node_result}

                if should_render or self.cached_chart_image is None:
                    chart_image = self.render_chart(time_unit, selected_classes, class_names_dict, chart_type)
                    self.cached_chart_image = chart_image
                    self.last_render_time = current_time
                else:
                    chart_image = self.cached_chart_image
            else:
                # Extract detection data (original behavior)
                class_ids = node_result.get('class_ids', [])
                class_names = node_result.get('class_names', {})
                self.update_class_slot_items(tag_node_name, get_class_dropdown_items())
            
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
                                    elif ":" in selected_value:
                                        # Parse "ID: name" format to extract class ID
                                        class_id = int(selected_value.split(":")[0].strip())
                                        selected_classes.append(class_id)
                                    else:
                                        # Fallback: try to parse as plain integer (for backwards compatibility)
                                        class_id = int(selected_value)
                                        selected_classes.append(class_id)
                            except (ValueError, TypeError, IndexError):
                                # Skip invalid values
                                pass
                
                # If no classes selected, default to "All"
                if not selected_classes:
                    selected_classes = ["All"]
                
                # Render chart with selected chart type only if render interval has passed
                if should_render or self.cached_chart_image is None:
                    chart_image = self.render_chart(time_unit, selected_classes, class_names, chart_type)
                    self.cached_chart_image = chart_image
                    self.last_render_time = current_time
                else:
                    chart_image = self.cached_chart_image

        else:
            # No detection data yet, render empty chart only if render interval has passed
            if should_render or self.cached_chart_image is None:
                chart_image = self.render_chart(time_unit, ["All"], {}, chart_type)
                self.cached_chart_image = chart_image
                self.last_render_time = current_time
            else:
                chart_image = self.cached_chart_image

        if use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')

        if chart_image is not None:
            # Store the current chart image for download
            self.current_chart_image = chart_image
            
            texture = self.convert_cv_to_dpg(
                chart_image,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return {"image": chart_image, "json": None, "audio": None}


    def close(self, node_id):
        # Clean up node instance from class variable
        try:
            del Node._node_instances[node_id]
        except KeyError:
            pass  # Node instance already removed or never added


    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        time_agg_tag = tag_node_name + ':TimeAggregationValue'
        chart_type_tag = tag_node_name + ':ChartTypeValue'

        time_unit = dpg_get_value(time_agg_tag)
        chart_type = dpg_get_value(chart_type_tag)

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[time_agg_tag] = time_unit
        setting_dict[chart_type_tag] = chart_type
        
        # Save class slot selections
        class_slots_tag = f"{tag_node_name}:ClassSlots"
        if dpg.does_item_exist(class_slots_tag):
            children = dpg.get_item_children(class_slots_tag, slot=1)
            if children:
                for idx, child in enumerate(children):
                    try:
                        selected_value = dpg_get_value(child)
                        setting_dict[f"{tag_node_name}:ClassSlot:{idx}"] = selected_value
                    except (KeyError, TypeError, AttributeError):
                        # Skip slots that can't be retrieved
                        pass

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        time_agg_tag = tag_node_name + ':TimeAggregationValue'
        chart_type_tag = tag_node_name + ':ChartTypeValue'

        time_unit = setting_dict.get(time_agg_tag, "minute")
        chart_type = setting_dict.get(chart_type_tag, "bar")
        dpg_set_value(time_agg_tag, time_unit)
        dpg_set_value(chart_type_tag, chart_type)
        
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
                        except (KeyError, TypeError, AttributeError):
                            # Skip slots that can't be set
                            pass
