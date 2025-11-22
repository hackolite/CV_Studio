#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Basic tests for CropMonitor Node"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_crop_monitor_node_structure():
    """Test that CropMonitor node has the required structure"""
    # This is a basic structure test that doesn't require DearPyGUI or OpenCV
    
    # Check that the file exists and can be parsed
    crop_monitor_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'ProcessNode', 'node_crop_monitor.py'
    )
    
    assert os.path.exists(crop_monitor_node_path), "node_crop_monitor.py file should exist"
    
    # Read the file and check for required components
    with open(crop_monitor_node_path, 'r') as f:
        content = f.read()
    
    # Check imports
    assert 'import cv2' in content, "Should import cv2"
    assert 'import numpy as np' in content, "Should import numpy"
    assert 'import dearpygui.dearpygui as dpg' in content, "Should import dearpygui"
    
    # Check function exists
    assert 'def crop_and_get_info' in content, "Should have crop_and_get_info function"
    
    # Check class structure
    assert 'class FactoryNode:' in content, "Should have FactoryNode class"
    assert 'class Node(Node):' in content, "Should have Node class"
    
    # Check node metadata
    assert "node_label = 'Crop Monitor'" in content, "Should have correct node label"
    assert "node_tag = 'CropMonitor'" in content, "Should have correct node tag"
    
    # Check monitoring info tags
    assert 'InfoWidth' in content, "Should have width info tag"
    assert 'InfoHeight' in content, "Should have height info tag"
    assert 'InfoCenter' in content, "Should have center info tag"
    
    # Check input/output structure
    assert 'TYPE_IMAGE' in content, "Should have image input/output"
    assert 'TYPE_FLOAT' in content, "Should have float inputs for crop parameters"
    
    # Check monitoring text displays
    assert 'Width:' in content, "Should display width"
    assert 'Height:' in content, "Should display height"
    assert 'Center:' in content, "Should display center position"


def test_crop_monitor_node_import():
    """Test that the CropMonitor node can be imported"""
    try:
        from node.ProcessNode import node_crop_monitor
        assert hasattr(node_crop_monitor, 'FactoryNode'), "Module should have FactoryNode"
        assert hasattr(node_crop_monitor, 'Node'), "Module should have Node class"
        
        factory = node_crop_monitor.FactoryNode()
        assert factory.node_label == 'Crop Monitor', "Factory should have correct label"
        assert factory.node_tag == 'CropMonitor', "Factory should have correct tag"
        
    except ImportError as e:
        pytest.skip(f"Could not import node_crop_monitor: {e}")


def test_crop_and_get_info_function():
    """Test the crop_and_get_info helper function"""
    try:
        import numpy as np
        from node.ProcessNode.node_crop_monitor import crop_and_get_info
        
        # Create a test image
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Test cropping
        min_x, max_x = 0.2, 0.8  # 20% to 80%
        min_y, max_y = 0.3, 0.7  # 30% to 70%
        
        cropped, width, height, center_x, center_y = crop_and_get_info(
            test_image, min_x, max_x, min_y, max_y
        )
        
        # Expected values
        expected_width = int(0.8 * 100) - int(0.2 * 100)  # 80 - 20 = 60
        expected_height = int(0.7 * 100) - int(0.3 * 100)  # 70 - 30 = 40
        expected_center_x = int(0.2 * 100) + expected_width // 2  # 20 + 30 = 50
        expected_center_y = int(0.3 * 100) + expected_height // 2  # 30 + 20 = 50
        
        assert width == expected_width, f"Width should be {expected_width}, got {width}"
        assert height == expected_height, f"Height should be {expected_height}, got {height}"
        assert center_x == expected_center_x, f"Center X should be {expected_center_x}, got {center_x}"
        assert center_y == expected_center_y, f"Center Y should be {expected_center_y}, got {center_y}"
        assert cropped.shape == (expected_height, expected_width, 3), "Cropped image should have correct shape"
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_crop_monitor_registered_in_menu():
    """Test that CropMonitor is registered in the menu"""
    from node_editor.style import PROCESS
    
    assert 'CropMonitor' in PROCESS, "CropMonitor should be registered in PROCESS menu"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
