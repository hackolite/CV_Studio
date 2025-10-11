#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ML/DL node adapters - imports from existing node.DLNode modules
This maintains backward compatibility while allowing gradual migration
"""

# Import all ML/DL nodes from the existing location
import sys
import os

# Add the parent directory to the path to allow imports from node/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Import existing DL nodes
try:
    from node.DLNode.node_classification import Node as ClassificationNode, FactoryNode as ClassificationFactory
    from node.DLNode.node_object_detection import Node as ObjectDetectionNode, FactoryNode as ObjectDetectionFactory
    from node.DLNode.node_face_detection import Node as FaceDetectionNode, FactoryNode as FaceDetectionFactory
    from node.DLNode.node_pose_estimation import Node as PoseEstimationNode, FactoryNode as PoseEstimationFactory
    from node.DLNode.node_semantic_segmentation import Node as SemanticSegmentationNode, FactoryNode as SemanticSegmentationFactory
    
    __all__ = [
        'ClassificationNode', 'ClassificationFactory',
        'ObjectDetectionNode', 'ObjectDetectionFactory',
        'FaceDetectionNode', 'FaceDetectionFactory',
        'PoseEstimationNode', 'PoseEstimationFactory',
        'SemanticSegmentationNode', 'SemanticSegmentationFactory',
    ]
except ImportError as e:
    # If old modules can't be imported, log a warning
    import logging
    logging.warning(f"Could not import ML/DL nodes from old location: {e}")
    __all__ = []
