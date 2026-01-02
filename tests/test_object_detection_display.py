#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test object detection node image display"""

import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_object_detection_node_structure():
    """Test that the object detection node has the correct structure"""
    from node.DLNode.node_object_detection import FactoryNode, Node
    
    # Verify FactoryNode has correct attributes
    factory = FactoryNode()
    assert hasattr(factory, 'node_label'), "FactoryNode should have node_label"
    assert hasattr(factory, 'node_tag'), "FactoryNode should have node_tag"
    assert factory.node_label == 'ObjectDetection', "node_label should be 'ObjectDetection'"
    assert factory.node_tag == 'ObjectDetection', "node_tag should be 'ObjectDetection'"
    
    # Verify Node class has correct attributes
    assert hasattr(Node, 'node_label'), "Node should have node_label"
    assert hasattr(Node, 'node_tag'), "Node should have node_tag"
    assert Node.node_label == 'ObjectDetection', "Node.node_label should be 'ObjectDetection'"
    assert Node.node_tag == 'ObjectDetection', "Node.node_tag should be 'ObjectDetection'"


def test_object_detection_file_has_add_image():
    """Test that the object detection file contains dpg.add_image call"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for image widget creation
    assert 'dpg.add_image(' in content, "Should have dpg.add_image() call to display image"
    
    # Check for texture creation
    assert 'dpg.add_raw_texture(' in content, "Should create texture with dpg.add_raw_texture()"
    
    # Check for texture update
    assert 'dpg_set_value(' in content, "Should update texture with dpg_set_value()"
    assert 'convert_cv_to_dpg' in content, "Should convert OpenCV image to DPG texture"


def test_object_detection_attribute_order():
    """Test that node attributes are in the correct order"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the add_node method
    add_node_start = content.find('def add_node(')
    add_node_end = content.find('class Node(Node):', add_node_start)
    add_node_method = content[add_node_start:add_node_end]
    
    # Check that image output attribute exists
    assert 'tag_node_output_image_name' in add_node_method or 'tag_node_output01_name' in add_node_method, \
        "Should have output image attribute"
    
    # Check that dpg.add_image is in an output attribute
    assert 'dpg.mvNode_Attr_Output' in add_node_method, "Should have output attribute"
    assert 'dpg.add_image(' in add_node_method, "Should add image widget in output attribute"
    
    # Verify the texture tag matches the image widget tag
    # Extract the texture tag and image widget tag
    import re
    texture_match = re.search(r'dpg\.add_raw_texture\([^,]+,[^,]+,[^,]+,\s*tag=([^,\)]+)', add_node_method)
    image_match = re.search(r'dpg\.add_image\(([^\)]+)\)', add_node_method)
    
    if texture_match and image_match:
        texture_tag = texture_match.group(1).strip()
        image_tag = image_match.group(1).strip()
        assert texture_tag == image_tag, f"Texture tag {texture_tag} should match image tag {image_tag}"


if __name__ == '__main__':
    test_object_detection_node_structure()
    print("✓ test_object_detection_node_structure passed")
    
    test_object_detection_file_has_add_image()
    print("✓ test_object_detection_file_has_add_image passed")
    
    test_object_detection_attribute_order()
    print("✓ test_object_detection_attribute_order passed")
    
    print("\nAll tests passed!")
