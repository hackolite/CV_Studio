#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backward compatibility layer for CV Studio
This module provides compatibility wrappers to maintain the existing API
while using the new architecture internally.
"""

# Re-export the old node module structure for backward compatibility
# This ensures existing code continues to work without modifications

# Import from old locations
try:
    from node.node_abc import DpgNodeABC
    from node.basenode import Node as OldNode, DataType, PortType
except ImportError:
    # If old modules don't exist yet, provide dummy classes
    class DpgNodeABC:
        pass
    
    class OldNode:
        pass
    
    class DataType:
        pass
    
    class PortType:
        pass

# Import new architecture
from src.core.nodes.base import BaseNode as NewBaseNode
from src.core.nodes.factory import NodeFactory as NewNodeFactory
from src.core.config.settings import Settings
from src.utils.exceptions import NodeError, NodeExecutionError
from src.utils.logging import setup_logging, get_logger

# Export both old and new APIs
__all__ = [
    # Old API
    'DpgNodeABC',
    'OldNode',
    'DataType',
    'PortType',
    # New API
    'NewBaseNode',
    'NewNodeFactory',
    'Settings',
    'NodeError',
    'NodeExecutionError',
    'setup_logging',
    'get_logger'
]
