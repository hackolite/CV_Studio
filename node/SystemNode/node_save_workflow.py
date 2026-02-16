#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import time
import dearpygui.dearpygui as dpg
from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Global reference to node editor for save functionality
_node_editor_instance = None


def set_node_editor_instance(editor):
    """Set the global node editor instance"""
    global _node_editor_instance
    _node_editor_instance = editor


class FactoryNode:
    node_label = 'SaveWorkflow'
    node_tag = 'SaveWorkflow'

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
        node.tag_node_filepath_name = node.tag_node_name + ':Filepath'
        node.tag_node_filepath_value_name = node.tag_node_name + ':FilepathValue'
        node.tag_node_save_button_name = node.tag_node_name + ':SaveButton'
        node.tag_node_status_name = node.tag_node_name + ':Status'
        node.tag_node_status_value_name = node.tag_node_name + ':StatusValue'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Filepath input
            with dpg.node_attribute(
                    tag=node.tag_node_filepath_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=node.tag_node_filepath_value_name,
                    label='Save Path',
                    default_value='workflow.json',
                    width=small_window_w - 80,
                )

            # Save button
            with dpg.node_attribute(
                    tag=node.tag_node_save_button_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='Save Workflow',
                    width=small_window_w,
                    callback=lambda: node.save_workflow_callback(node_id),
                )

            # Status display
            with dpg.node_attribute(
                    tag=node.tag_node_status_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_status_value_name,
                    default_value='Ready',
                )

        return node


class Node(Node):
    _ver = '0.0.1'
    node_label = 'SaveWorkflow'
    node_tag = 'SaveWorkflow'

    _opencv_setting_dict = None

    def __init__(self):
        pass

    def save_workflow_callback(self, node_id):
        """Callback when save button is clicked"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        filepath_tag = tag_node_name + ':FilepathValue'
        status_tag = tag_node_name + ':StatusValue'

        try:
            filepath = dpg_get_value(filepath_tag)
            if not filepath:
                dpg_set_value(status_tag, 'Error: No filepath')
                return

            # Add .json extension if not present
            if not filepath.endswith('.json'):
                filepath = filepath + '.json'

            # Use the global node editor instance to export workflow
            global _node_editor_instance
            if _node_editor_instance:
                # Export using the node editor's existing method
                _node_editor_instance._callback_file_export(None, {"file_path_name": filepath})
                dpg_set_value(status_tag, f'Saved: {os.path.basename(filepath)}')
                logger.info(f'Workflow saved to: {filepath}')
            else:
                dpg_set_value(status_tag, 'Error: No editor')
                logger.error('Node editor instance not available')
            
        except Exception as e:
            logger.error(f'Error saving workflow: {e}', exc_info=True)
            dpg_set_value(status_tag, f'Error: {str(e)[:50]}')

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """Update called every frame"""
        return {"image": None, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        filepath_tag = tag_node_name + ':FilepathValue'

        filepath = dpg_get_value(filepath_tag)
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[filepath_tag] = filepath

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        filepath_tag = tag_node_name + ':FilepathValue'

        if filepath_tag in setting_dict:
            filepath = setting_dict[filepath_tag]
            dpg_set_value(filepath_tag, filepath)
