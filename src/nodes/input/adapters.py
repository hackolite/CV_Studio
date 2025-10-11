#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Input node adapters - imports from existing node.InputNode modules
This maintains backward compatibility while allowing gradual migration
"""

# Import all input nodes from the existing location
import sys
import os

# Add the parent directory to the path to allow imports from node/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Import existing input nodes
try:
    from node.InputNode.node_image import Node as ImageInputNode, FactoryNode as ImageInputFactory
    from node.InputNode.node_video import Node as VideoInputNode, FactoryNode as VideoInputFactory
    from node.InputNode.node_webcam import Node as WebcamInputNode, FactoryNode as WebcamInputFactory
    from node.InputNode.node_api import ApiNode, FactoryNode as ApiInputFactory
    from node.InputNode.node_float import Node as FloatInputNode, FactoryNode as FloatInputFactory
    
    __all__ = [
        'ImageInputNode', 'ImageInputFactory',
        'VideoInputNode', 'VideoInputFactory',
        'WebcamInputNode', 'WebcamInputFactory',
        'ApiNode', 'ApiInputFactory',
        'FloatInputNode', 'FloatInputFactory',
    ]
except ImportError as e:
    # If old modules can't be imported, log a warning
    import logging
    logging.warning(f"Could not import input nodes from old location: {e}")
    __all__ = []
