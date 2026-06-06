#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


class FactoryNode:
    node_label = 'Operator'
    node_tag = 'Operator'

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
        node = OperatorNode()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        
        # Input A (JSON from first IOU node)
        node.tag_node_input_a_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputA'
        node.tag_node_input_a_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputAValue'
        
        # Input B (JSON from second IOU node)
        node.tag_node_input_b_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputB'
        node.tag_node_input_b_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':InputBValue'
        
        # JSON Output (for Chart node)
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':OutputValue'
        
        # Time output (optional)
        node.tag_node_output_time_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':OutputTime'
        node.tag_node_output_time_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':OutputTimeValue'
        
        # Operation selector
        node.tag_operation_name = node.tag_node_name + ':Operation'
        node.tag_operation_value_name = node.tag_node_name + ':OperationValue'
        
        # Status display
        node.tag_status_name = node.tag_node_name + ':Status'
        node.tag_status_value_name = node.tag_node_name + ':StatusValue'

        node._opencv_setting_dict = opencv_setting_dict
        use_pref_counter = node._opencv_setting_dict.get('use_pref_counter', False)

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Input A
            with dpg.node_attribute(
                tag=node.tag_node_input_a_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_a_value_name,
                    default_value='Input A (JSON)',
                )

            # Input B
            with dpg.node_attribute(
                tag=node.tag_node_input_b_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_b_value_name,
                    default_value='Input B (JSON)',
                )

            # Operation selector
            with dpg.node_attribute(
                tag=node.tag_operation_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_operation_value_name,
                    label='Operation',
                    items=['Addition (+)', 'Subtraction (-)', 'Multiplication (*)', 'Division (/)'],
                    default_value='Addition (+)',
                    width=200,
                )

            # Status display
            with dpg.node_attribute(
                tag=node.tag_status_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_status_value_name,
                    default_value='Ready',
                )

            # JSON Output
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='Result (JSON)',
                )

            # Time output (if performance counter is enabled)
            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output_time_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output_time_value_name,
                        default_value='Elapsed time(ms)',
                    )

        return node


class OperatorNode(Node):
    _ver = '0.0.1'

    node_label = 'Operator'
    node_tag = 'Operator'

    _opencv_setting_dict = None

    def __init__(self):
        pass

    def _get_source_for_input(self, connection_list, node_result_dict, input_suffix):
        """Return the JSON dict connected to the given input slot."""
        for connection_info in connection_list:
            destination = connection_info[1]
            source = connection_info[0]
            connection_type = source.split(':')[2]
            if connection_type.upper() != self.TYPE_JSON.upper():
                continue
            if not destination.endswith(input_suffix):
                continue
            source_key = ':'.join(source.split(':')[:2])
            return node_result_dict.get(source_key, None)
        return None

    def _apply_operation(self, value_a, value_b, operation):
        """Apply the selected operation to two values."""
        try:
            a = float(value_a)
            b = float(value_b)
            
            if operation == 'Addition (+)':
                return a + b
            elif operation == 'Subtraction (-)':
                return a - b
            elif operation == 'Multiplication (*)':
                return a * b
            elif operation == 'Division (/)':
                # Handle division by zero
                if b == 0:
                    return float('inf') if a >= 0 else float('-inf')
                return a / b
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        operation_tag = tag_node_name + ':OperationValue'
        status_tag = tag_node_name + ':StatusValue'
        output_time_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':OutputTimeValue'

        use_pref_counter = self._opencv_setting_dict.get('use_pref_counter', False)

        if use_pref_counter:
            start_time = time.monotonic()

        # Get operation type
        operation = dpg_get_value(operation_tag)
        if operation is None:
            operation = 'Addition (+)'

        # Get input data from both sources
        json_a = self._get_source_for_input(connection_list, node_result_dict, 'InputA')
        json_b = self._get_source_for_input(connection_list, node_result_dict, 'InputB')

        result = None
        if isinstance(json_a, dict) and isinstance(json_b, dict):
            # Apply operation key-by-key on matching keys
            result = {}
            
            # Get all keys that exist in both dictionaries
            common_keys = set(json_a.keys()) & set(json_b.keys())
            
            # Process only numeric values
            for key in common_keys:
                value_a = json_a[key]
                value_b = json_b[key]
                
                # Only process numeric values (int or float)
                if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)):
                    result[key] = self._apply_operation(value_a, value_b, operation)
            
            # Update status
            if result:
                dpg_set_value(
                    status_tag,
                    f'{operation}: {len(result)} keys processed',
                )
            else:
                dpg_set_value(
                    status_tag,
                    'No matching numeric keys',
                )
        else:
            # No valid inputs
            if json_a is None and json_b is None:
                dpg_set_value(status_tag, 'Waiting for inputs A & B')
            elif json_a is None:
                dpg_set_value(status_tag, 'Waiting for input A')
            elif json_b is None:
                dpg_set_value(status_tag, 'Waiting for input B')
            else:
                dpg_set_value(status_tag, 'Invalid input data')

        if use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_time_tag, str(elapsed_time).zfill(4) + 'ms')

        return result


# Alias for compatibility
Node = OperatorNode
