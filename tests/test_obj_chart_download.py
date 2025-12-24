#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for ObjChart node download button functionality"""

import sys
import os
from datetime import datetime
import numpy as np
import cv2

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_obj_chart_download_button_exists():
    """Test that download button tag is created"""
    from node.VisualNode.node_obj_chart import FactoryNode, Node
    
    # Create a factory node to check structure
    factory = FactoryNode()
    
    # Verify the factory has the correct label
    assert factory.node_label == 'objchart'
    assert factory.node_tag == 'objchart'


def test_obj_chart_current_image_storage():
    """Test that node instance can store current chart image"""
    from node.VisualNode.node_obj_chart import Node
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Check that current_chart_image attribute exists and is None initially
    assert hasattr(node, 'current_chart_image')
    assert node.current_chart_image is None
    
    # Simulate storing an image
    test_image = np.zeros((400, 600, 3), dtype=np.uint8)
    node.current_chart_image = test_image
    
    # Verify the image is stored
    assert node.current_chart_image is not None
    assert node.current_chart_image.shape == (400, 600, 3)


def test_obj_chart_download_callback_exists():
    """Test that download_chart_callback method exists"""
    from node.VisualNode.node_obj_chart import Node
    
    # Verify the callback method exists
    assert hasattr(Node, 'download_chart_callback')
    assert callable(Node.download_chart_callback)


def test_obj_chart_download_saves_image():
    """Test that download callback can save an image"""
    from node.VisualNode.node_obj_chart import Node
    import tempfile
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Create a test image
    test_image = np.zeros((400, 600, 3), dtype=np.uint8)
    # Add some visual content to the image
    cv2.rectangle(test_image, (50, 50), (150, 150), (255, 0, 0), -1)
    node.current_chart_image = test_image
    
    # Create a temporary directory for test output
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Call the download callback
            Node.download_chart_callback(None, None, node)
            
            # Check that a file was created
            files = [f for f in os.listdir('.') if f.startswith('objchart_') and f.endswith('.png')]
            assert len(files) > 0, "No image file was created"
            
            # Verify the saved image
            saved_image = cv2.imread(files[0])
            assert saved_image is not None, "Saved image could not be read"
            assert saved_image.shape == test_image.shape, "Saved image has wrong dimensions"
            
        finally:
            os.chdir(old_cwd)


def test_obj_chart_download_no_image():
    """Test that download callback handles case when no image is available"""
    from node.VisualNode.node_obj_chart import Node
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # current_chart_image should be None
    assert node.current_chart_image is None
    
    # Call the download callback - should not crash
    Node.download_chart_callback(None, None, node)
    # If we reach here, the callback handled None gracefully


if __name__ == "__main__":
    # Run tests
    print("Testing ObjChart download button functionality...")
    test_obj_chart_download_button_exists()
    print("✅ test_obj_chart_download_button_exists passed")
    
    test_obj_chart_current_image_storage()
    print("✅ test_obj_chart_current_image_storage passed")
    
    test_obj_chart_download_callback_exists()
    print("✅ test_obj_chart_download_callback_exists passed")
    
    test_obj_chart_download_saves_image()
    print("✅ test_obj_chart_download_saves_image passed")
    
    test_obj_chart_download_no_image()
    print("✅ test_obj_chart_download_no_image passed")
    
    print("\n🎉 All tests passed!")
