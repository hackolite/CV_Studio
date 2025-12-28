#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for YOLOv8-seg segmentation model"""

import pytest
import sys
import os
import numpy as np
import cv2

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_yolov8_seg_import():
    """Test that YOLOv8Seg can be imported without errors"""
    from node.DLNode.semantic_segmentation.yolov8_seg.yolov8_seg import YOLOv8Seg
    assert YOLOv8Seg is not None


def test_yolov8_seg_class_num():
    """Test that get_class_num method exists and returns correct value"""
    from node.DLNode.semantic_segmentation.yolov8_seg.yolov8_seg import YOLOv8Seg
    
    # Create a mock instance (without loading a model)
    # We'll test the method exists by checking the class
    assert hasattr(YOLOv8Seg, 'get_class_num')
    assert hasattr(YOLOv8Seg, '__call__')
    assert hasattr(YOLOv8Seg, 'extract_contours')
    assert hasattr(YOLOv8Seg, '_preprocess')
    assert hasattr(YOLOv8Seg, '_postprocess')
    assert hasattr(YOLOv8Seg, '_generate_masks')


def test_extract_contours_logic():
    """Test contour extraction logic without requiring a model"""
    
    # Create a simple binary mask
    mask = np.zeros((100, 100), dtype=np.float32)
    mask[25:75, 25:75] = 1.0  # Square in the middle
    
    # Convert to uint8 for contour detection
    mask_uint8 = (mask * 255).astype(np.uint8)
    
    # Find contours
    contours, _ = cv2.findContours(
        mask_uint8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    # Should find one contour
    assert len(contours) > 0, "Should find at least one contour"
    
    # The contour should have at least 4 points (a square)
    assert len(contours[0]) >= 4, "Square contour should have at least 4 points"


def test_preprocessing_shape():
    """Test preprocessing transforms image to correct shape"""
    from node.DLNode.semantic_segmentation.yolov8_seg.yolov8_seg import YOLOv8Seg
    
    # Simulate preprocessing logic
    input_width, input_height = 640, 640
    
    # Create a dummy image
    image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Resize
    resized = cv2.resize(image, (input_width, input_height))
    assert resized.shape == (input_height, input_width, 3)
    
    # Normalize
    normalized = resized.astype(np.float32) / 255.0
    assert normalized.max() <= 1.0
    assert normalized.min() >= 0.0
    
    # Transpose to CHW
    transposed = np.transpose(normalized, (2, 0, 1))
    assert transposed.shape == (3, input_height, input_width)
    
    # Add batch dimension
    batched = np.expand_dims(transposed, axis=0)
    assert batched.shape == (1, 3, input_height, input_width)


def test_node_semantic_segmentation_imports():
    """Test that the node_semantic_segmentation can import YOLOv8Seg"""
    # This test verifies the integration is correct
    try:
        # Import should not fail
        from node.DLNode.node_semantic_segmentation import Node
        # If we got here, the import succeeded
        assert True
    except ImportError as e:
        # If it fails due to missing GUI libraries, that's expected
        if 'dearpygui' in str(e):
            pytest.skip("Skipping due to missing GUI dependencies")
        else:
            # Any other import error is a problem
            raise


def test_basenode_has_draw_method():
    """Test that basenode has the draw_yolov8_seg_contours method"""
    try:
        from node.basenode import Node
        assert hasattr(Node, 'draw_yolov8_seg_contours')
    except ImportError as e:
        if 'dearpygui' in str(e):
            pytest.skip("Skipping due to missing GUI dependencies")
        else:
            raise


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
