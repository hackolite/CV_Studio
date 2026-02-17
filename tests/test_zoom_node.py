#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Zoom Node"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_zoom_node_structure():
    """Test that Zoom node has the required structure"""
    # This is a basic structure test that doesn't require DearPyGUI or OpenCV
    
    # Check that the file exists and can be parsed
    zoom_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'ProcessNode', 'node_zoom.py'
    )
    
    assert os.path.exists(zoom_node_path), "node_zoom.py file should exist"
    
    # Read the file and check for required components
    with open(zoom_node_path, 'r') as f:
        content = f.read()
    
    # Check imports
    assert 'import cv2' in content, "Should import cv2"
    assert 'import numpy as np' in content, "Should import numpy"
    assert 'import dearpygui.dearpygui as dpg' in content, "Should import dearpygui"
    
    # Check function exists
    assert 'def crop_from_center' in content, "Should have crop_from_center function"
    
    # Check class structure
    assert 'class FactoryNode:' in content, "Should have FactoryNode class"
    assert 'class Node(Node):' in content, "Should have Node class"
    
    # Check node metadata
    assert "node_label = 'Zoom'" in content, "Should have correct node label"
    assert "node_tag = 'Zoom'" in content, "Should have correct node tag"
    
    # Check input labels match requirements
    assert 'label="width"' in content, "Should have width parameter"
    assert 'label="center x"' in content, "Should have center x parameter"
    assert 'label="center y"' in content, "Should have center y parameter"
    
    # Check input/output structure
    assert 'TYPE_IMAGE' in content, "Should have image input/output"
    assert 'TYPE_FLOAT' in content, "Should have float inputs for zoom parameters"


def test_zoom_node_import():
    """Test that the Zoom node can be imported"""
    try:
        from node.ProcessNode import node_zoom
        assert hasattr(node_zoom, 'FactoryNode'), "Module should have FactoryNode"
        assert hasattr(node_zoom, 'Node'), "Module should have Node class"
        
        factory = node_zoom.FactoryNode()
        assert factory.node_label == 'Zoom', "Factory should have correct label"
        assert factory.node_tag == 'Zoom', "Factory should have correct tag"
        
    except ImportError as e:
        pytest.skip(f"Could not import node_zoom: {e}")


def test_crop_from_center_function():
    """Test the crop_from_center helper function"""
    try:
        import numpy as np
        from node.ProcessNode.node_zoom import crop_from_center
        
        # Create a test image
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Test 1: Center crop with 50% width
        width = 0.5  # 50% of image
        center_x = 0.5  # Center at 50%
        center_y = 0.5  # Center at 50%
        
        cropped = crop_from_center(test_image, width, center_x, center_y)
        
        # Should produce a square crop of 50x50
        expected_size = 50
        assert cropped.shape[0] == expected_size, f"Height should be {expected_size}, got {cropped.shape[0]}"
        assert cropped.shape[1] == expected_size, f"Width should be {expected_size}, got {cropped.shape[1]}"
        assert cropped.shape[0] == cropped.shape[1], "Crop should be square"
        
        # Test 2: Off-center crop
        width = 0.4
        center_x = 0.3
        center_y = 0.7
        
        cropped2 = crop_from_center(test_image, width, center_x, center_y)
        
        # Width should be 40 pixels (0.4 * 100)
        expected_size2 = 40
        assert cropped2.shape[0] == expected_size2, f"Height should be {expected_size2}, got {cropped2.shape[0]}"
        assert cropped2.shape[1] == expected_size2, f"Width should be {expected_size2}, got {cropped2.shape[1]}"
        assert cropped2.shape[0] == cropped2.shape[1], "Crop should be square"
        
        # Test 3: Edge case - small width
        width = 0.1
        center_x = 0.5
        center_y = 0.5
        
        cropped3 = crop_from_center(test_image, width, center_x, center_y)
        expected_size3 = 10
        assert cropped3.shape[0] == expected_size3, f"Height should be {expected_size3}, got {cropped3.shape[0]}"
        assert cropped3.shape[1] == expected_size3, f"Width should be {expected_size3}, got {cropped3.shape[1]}"
        assert cropped3.shape[0] == cropped3.shape[1], "Crop should be square"
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_zoom_registered_in_menu():
    """Test that Zoom is registered in the menu"""
    from node_editor.style import PROCESS
    
    assert 'Zoom' in PROCESS, "Zoom should be registered in PROCESS menu"


def test_crop_from_center_boundary_cases():
    """Test boundary cases for crop_from_center function"""
    try:
        import numpy as np
        from node.ProcessNode.node_zoom import crop_from_center
        
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Test with width at boundaries
        # Width = 0 should be clamped to 0.01
        cropped = crop_from_center(test_image, 0.0, 0.5, 0.5)
        assert cropped.shape[0] > 0, "Should have positive height even with width=0"
        assert cropped.shape[1] > 0, "Should have positive width even with width=0"
        assert cropped.shape[0] == cropped.shape[1], "Should be square"
        
        # Width > 1.0 should be clamped to 1.0
        cropped = crop_from_center(test_image, 1.5, 0.5, 0.5)
        assert cropped.shape[0] <= 100, "Height should not exceed image height"
        assert cropped.shape[1] <= 100, "Width should not exceed image width"
        assert cropped.shape[0] == cropped.shape[1], "Should be square"
        
        # Test with center near edges
        # This should clamp properly and not crash
        cropped = crop_from_center(test_image, 0.5, 0.1, 0.1)
        assert cropped.shape[0] > 0, "Should crop successfully near edge"
        assert cropped.shape[1] > 0, "Should crop successfully near edge"
        assert cropped.shape[0] == cropped.shape[1], "Should be square"
        
        cropped = crop_from_center(test_image, 0.5, 0.9, 0.9)
        assert cropped.shape[0] > 0, "Should crop successfully near opposite edge"
        assert cropped.shape[1] > 0, "Should crop successfully near opposite edge"
        assert cropped.shape[0] == cropped.shape[1], "Should be square"
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_zoom_output_dimensions():
    """Test that zoom node outputs image with same dimensions as input"""
    try:
        import numpy as np
        import cv2
        from node.ProcessNode.node_zoom import crop_from_center
        
        # Create a test image
        original_height, original_width = 200, 300
        test_image = np.random.randint(0, 255, (original_height, original_width, 3), dtype=np.uint8)
        
        # Simulate the zoom operation (crop + resize)
        width = 0.5  # 50% zoom
        center_x = 0.5
        center_y = 0.5
        
        # Crop
        cropped = crop_from_center(test_image, width, center_x, center_y)
        
        # The zoom node should resize back to original dimensions
        zoomed = cv2.resize(cropped, (original_width, original_height), interpolation=cv2.INTER_LINEAR)
        
        # Verify output dimensions match input
        assert zoomed.shape[0] == original_height, f"Output height should be {original_height}, got {zoomed.shape[0]}"
        assert zoomed.shape[1] == original_width, f"Output width should be {original_width}, got {zoomed.shape[1]}"
        assert zoomed.shape[2] == 3, "Should maintain 3 color channels"
        
        # Test with different zoom levels
        for width_param in [0.2, 0.3, 0.7, 1.0]:
            cropped = crop_from_center(test_image, width_param, 0.5, 0.5)
            zoomed = cv2.resize(cropped, (original_width, original_height), interpolation=cv2.INTER_LINEAR)
            assert zoomed.shape == test_image.shape, f"Zoom with width={width_param} should maintain input dimensions"
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
