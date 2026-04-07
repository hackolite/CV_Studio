#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Info Node – System category

Displays static information about the running environment:
  • Last git commit hash and date
  • Python version
  • Platform / OS
  • Current date/time (refreshed each update cycle)
"""
import os
import platform
import subprocess
import sys
import datetime

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_set_value
from node.basenode import Node as BaseNode


def _get_git_commit():
    """Return (short_hash, date_str) of the last git commit, or ('N/A', 'N/A')."""
    try:
        root = os.path.dirname(os.path.abspath(__file__))
        short_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        date_str = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return short_hash, date_str
    except Exception:
        return "N/A", "N/A"


class FactoryNode:
    node_label = "Info"
    node_tag = "Info"

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=None,
        opencv_setting_dict=None,
        callback=None,
    ):
        if pos is None:
            pos = [0, 0]

        node = InfoNode()
        node.tag_node_name = str(node_id) + ":" + node.node_tag
        node._opencv_setting_dict = opencv_setting_dict or {}

        tag = node.tag_node_name

        # Collect static info once at node creation
        commit_hash, commit_date = _get_git_commit()
        python_ver = sys.version.split()[0]
        os_info = platform.platform()

        # Tag names for dynamic labels
        node._tag_commit = tag + ":commit"
        node._tag_commit_date = tag + ":commit_date"
        node._tag_python = tag + ":python"
        node._tag_os = tag + ":os"
        node._tag_now = tag + ":now"

        with dpg.node(tag=tag, parent=parent, label=node.node_label, pos=pos):
            with dpg.node_attribute(
                tag=tag + ":static",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("── System Info ──")
                dpg.add_spacer(height=4)

                dpg.add_text("Last commit:")
                dpg.add_text(
                    tag=node._tag_commit,
                    default_value=commit_hash,
                )
                dpg.add_spacer(height=2)

                dpg.add_text("Commit date:")
                dpg.add_text(
                    tag=node._tag_commit_date,
                    default_value=commit_date,
                )
                dpg.add_spacer(height=4)

                dpg.add_text("Python:")
                dpg.add_text(
                    tag=node._tag_python,
                    default_value=python_ver,
                )
                dpg.add_spacer(height=2)

                dpg.add_text("Platform:")
                dpg.add_text(
                    tag=node._tag_os,
                    default_value=os_info,
                )
                dpg.add_spacer(height=4)

                dpg.add_text("Current time:")
                dpg.add_text(
                    tag=node._tag_now,
                    default_value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )

        return node


class InfoNode(BaseNode):
    _ver = "0.0.1"

    node_label = "Info"
    node_tag = "Info"

    def __init__(self):
        super().__init__()
        self.node_label = "Info"
        self.node_tag = "Info"
        self._tag_now = None

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        # Refresh current time each update cycle
        if self._tag_now and dpg.does_item_exist(self._tag_now):
            dpg_set_value(
                self._tag_now,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        return {"image": None, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag = str(node_id) + ":" + self.node_tag
        pos = dpg.get_item_pos(tag)
        return {"ver": self._ver, "pos": pos}

    def set_setting_dict(self, node_id, setting_dict):
        pass
