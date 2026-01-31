#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced node_abc that extends the existing DpgNodeABC with new features
while maintaining backward compatibility
"""

from abc import ABCMeta, abstractmethod


class DpgNodeABC(metaclass=ABCMeta):
    """
    Abstract base class for DearPyGUI nodes
    
    This is an enhanced version that maintains compatibility with the original
    while adding support for the new architecture
    """
    _ver = '0.0.0'

    node_label = ''
    node_tag = ''

    TYPE_INT = 'Int'
    TYPE_FLOAT = 'Float'
    TYPE_IMAGE = 'Image'
    TYPE_TIME_MS = 'TimeMS'
    TYPE_JSON = 'Json'
    TYPE_SOUND = 'Sound'

    @abstractmethod
    def add_node(
        self,
        parent,
        node_id,
        pos,
        width=None,
        height=None,
        opencv_setting_dict=None,
    ):
        """Add node to the GUI"""
        pass

    @abstractmethod
    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
    ):
        """Update/execute the node"""
        pass

    @abstractmethod
    def get_setting_dict(self, node_id):
        """Get current node settings"""
        pass

    @abstractmethod
    def set_setting_dict(self, node_id, setting_dict):
        """Apply settings to the node"""
        pass

    @abstractmethod
    def close(self, node_id):
        """Cleanup node resources"""
        pass
