#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Node Resizer Module
Provides functionality to resize nodes in the CV_Studio node editor.
"""

import dearpygui.dearpygui as dpg
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Size presets (width, height)
SIZE_PRESETS = [
    ("Tiny", 120, 68),
    ("Small", 240, 135),
    ("Medium", 480, 270),
    ("Large", 640, 360),
    ("X-Large", 960, 540),
]

SIZE_PRESET_NAMES = [name for name, _, _ in SIZE_PRESETS]
SIZE_PRESET_DICT = {name: (w, h) for name, w, h in SIZE_PRESETS}


def create_size_selector(node_id, tag_prefix, default_size="Small", callback=None):
    """
    Create a size selector combo box for a node.
    
    Args:
        node_id: The node ID
        tag_prefix: Prefix for the combo tag (e.g., node.tag_node_name)
        default_size: Default size preset name
        callback: Optional callback function when size changes
    
    Returns:
        The tag of the created combo box
    """
    combo_tag = f"{tag_prefix}:SizeSelector"
    default_idx = SIZE_PRESET_NAMES.index(default_size) if default_size in SIZE_PRESET_NAMES else 1
    
    dpg.add_combo(
        items=SIZE_PRESET_NAMES,
        default_value=default_size,
        tag=combo_tag,
        width=100,
        callback=callback,
    )
    
    return combo_tag


def get_size_from_preset(preset_name):
    """Get (width, height) tuple from a preset name"""
    return SIZE_PRESET_DICT.get(preset_name, (240, 135))


def add_node_resize_control(node, node_id, parent_attribute_tag, callback=None):
    """
    Add a resize control to a node attribute.
    
    Args:
        node: The node instance
        node_id: The node ID
        parent_attribute_tag: The parent node_attribute tag
        callback: Optional callback when size changes
    
    Returns:
        The combo box tag
    """
    with dpg.group(horizontal=True, parent=parent_attribute_tag):
        dpg.add_text("Size:")
        combo_tag = create_size_selector(
            node_id,
            node.tag_node_name,
            default_size="Small",
            callback=callback
        )
    
    return combo_tag
