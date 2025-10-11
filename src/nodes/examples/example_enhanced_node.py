#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example node implementation using the new enhanced architecture

This demonstrates how to create a new node that takes advantage of:
- Enhanced logging
- Exception handling  
- Resource management
- Clean code structure
"""

from typing import Dict, Any, List, Optional
from src.core.nodes import EnhancedNode
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ExampleEnhancedNode(EnhancedNode):
    """Example of a modern, well-structured node"""
    
    node_label = 'Example Enhanced'
    node_tag = 'ExampleEnhanced'
    _ver = '1.0.0'
    
    def add_node(self, parent, node_id, pos, opencv_setting_dict=None):
        """Add the node to the GUI"""
        logger.debug(f"Adding node {self.node_tag} at position {pos}")
        return None
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        """Execute the node's processing logic"""
        logger.debug(f"Updating node {self.node_tag} (ID: {node_id})")
        return {"image": None, "json": {"status": "processed"}}
    
    def get_setting_dict(self, node_id):
        """Get current node settings"""
        return super().get_setting_dict(node_id)
    
    def set_setting_dict(self, node_id, setting_dict):
        """Apply settings to the node"""
        super().set_setting_dict(node_id, setting_dict)
    
    def close(self, node_id):
        """Cleanup node resources"""
        logger.info(f"Closing node {self.node_tag} (ID: {node_id})")
        super().close(node_id)
