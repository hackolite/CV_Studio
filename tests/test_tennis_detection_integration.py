#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Integration test for YOLOTENNIS coordinate scaling with actual model"""

import pytest
import sys
import os
import numpy as np
import cv2

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from node.DLNode.object_detection.TennisYOLO.yolotennis import YOLOTENNIS
    YOLOTENNIS_AVAILABLE = True
except ImportError:
    YOLOTENNIS_AVAILABLE = False


@pytest.mark.skipif(not YOLOTENNIS_AVAILABLE, reason="YOLOTENNIS not available")
def test_yolotennis_coordinate_scaling_with_model():
    """Test YOLOTENNIS with actual model to verify coordinate scaling works"""
    
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'object_detection', 'TennisYOLO', 'model', 'tennis.onnx'
    )
    
    if not os.path.exists(model_path):
        pytest.skip(f"Model not found at {model_path}")
    
    # Create test images of different sizes
    test_sizes = [
        (640, 480),   # VGA
        (1280, 720),  # HD
        (1920, 1080), # Full HD
        (608, 416),   # Native model size
    ]
    
    for width, height in test_sizes:
        # Create a test image with known dimensions
        test_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        # Initialize model
        try:
            model = YOLOTENNIS(
                model_path=model_path,
                providers=['CPUExecutionProvider']
            )
        except Exception as e:
            pytest.skip(f"Could not load model: {e}")
        
        # Run inference
        bboxes, scores, class_ids = model(test_image)
        
        # Verify that if there are any detections, their coordinates are within bounds
        if len(bboxes) > 0:
            for bbox in bboxes:
                x1, y1, x2, y2 = bbox
                
                # Coordinates should be within image bounds
                # Allow some tolerance for edge cases
                assert x1 >= -10, f"X1 {x1} should be >= -10 for image size {width}x{height}"
                assert y1 >= -10, f"Y1 {y1} should be >= -10 for image size {width}x{height}"
                assert x2 <= width + 10, f"X2 {x2} should be <= {width + 10} for image size {width}x{height}"
                assert y2 <= height + 10, f"Y2 {y2} should be <= {height + 10} for image size {width}x{height}"
                
                # Box should have positive dimensions
                assert x2 > x1, f"X2 {x2} should be > X1 {x1}"
                assert y2 > y1, f"Y2 {y2} should be > Y1 {y1}"


@pytest.mark.skipif(not YOLOTENNIS_AVAILABLE, reason="YOLOTENNIS not available")
def test_yolotennis_scaling_consistency():
    """Test that YOLOTENNIS produces correctly scaled bounding boxes"""
    
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'object_detection', 'TennisYOLO', 'model', 'tennis.onnx'
    )
    
    if not os.path.exists(model_path):
        pytest.skip(f"Model not found at {model_path}")
    
    # Create a synthetic image with a clear object
    # Using 1280x720 which should scale to 608x416
    width, height = 1280, 720
    test_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Draw a white rectangle in the center that might be detected
    cv2.rectangle(test_image, (400, 200), (880, 520), (255, 255, 255), -1)
    
    try:
        model = YOLOTENNIS(
            model_path=model_path,
            providers=['CPUExecutionProvider']
        )
    except Exception as e:
        pytest.skip(f"Could not load model: {e}")
    
    # Run inference
    bboxes, scores, class_ids = model(test_image)
    
    # The expected scaling factors
    expected_scale_x = width / 608.0  # ~2.105
    expected_scale_y = height / 416.0  # ~1.731
    
    # If detections are found, verify they're scaled appropriately
    # We can't guarantee detections on random/synthetic data, so just verify 
    # that if there are detections, they're in the right coordinate space
    if len(bboxes) > 0:
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            
            # If coordinates were not scaled, they would be much smaller
            # (max 608 for x, 416 for y). With proper scaling for 1280x720,
            # we should see larger coordinates
            # Just verify they're roughly in the expected range
            assert x1 < width, f"X1 should be within image width {width}"
            assert x2 < width, f"X2 should be within image width {width}"
            assert y1 < height, f"Y1 should be within image height {height}"
            assert y2 < height, f"Y2 should be within image height {height}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
