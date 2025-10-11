#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Process node adapters - imports from existing node.ProcessNode modules
This maintains backward compatibility while allowing gradual migration
"""

# Import all process nodes from the existing location
import sys
import os

# Add the parent directory to the path to allow imports from node/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Import existing process nodes
try:
    from node.ProcessNode.node_canny import Node as CannyNode, FactoryNode as CannyFactory
    from node.ProcessNode.node_flip import Node as FlipNode, FactoryNode as FlipFactory
    from node.ProcessNode.node_blur import Node as BlurNode, FactoryNode as BlurFactory
    from node.ProcessNode.node_brightness import Node as BrightnessNode, FactoryNode as BrightnessFactory
    from node.ProcessNode.node_contrast import Node as ContrastNode, FactoryNode as ContrastFactory
    from node.ProcessNode.node_crop import Node as CropNode, FactoryNode as CropFactory
    
    __all__ = [
        'CannyNode', 'CannyFactory',
        'FlipNode', 'FlipFactory',
        'BlurNode', 'BlurFactory',
        'BrightnessNode', 'BrightnessFactory',
        'ContrastNode', 'ContrastFactory',
        'CropNode', 'CropFactory',
    ]
except ImportError as e:
    # If old modules can't be imported, log a warning
    import logging
    logging.warning(f"Could not import process nodes from old location: {e}")
    __all__ = []
