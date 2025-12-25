#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for ObjDetCount FactoryNode
Tests that the FactoryNode has the add_node method and works correctly
"""
import re


def test_factorynode_has_add_node_method():
    """Test that FactoryNode has the add_node method by checking the source code"""
    # Read the source file
    with open('node/TriggerNode/node_objdetcount.py', 'r') as f:
        content = f.read()
    
    # Check that FactoryNode class exists
    assert 'class FactoryNode:' in content, "FactoryNode class should exist"
    
    # Check that add_node method exists in FactoryNode
    # Look for the method definition within the FactoryNode class
    factory_class_match = re.search(r'class FactoryNode:.*?(?=class\s|\Z)', content, re.DOTALL)
    assert factory_class_match, "Could not find FactoryNode class"
    
    factory_class_content = factory_class_match.group(0)
    assert 'def add_node(' in factory_class_content, "FactoryNode should have add_node method"
    
    print("✓ FactoryNode has add_node method")


def test_factorynode_attributes():
    """Test that FactoryNode has the expected attributes"""
    with open('node/TriggerNode/node_objdetcount.py', 'r') as f:
        content = f.read()
    
    # Extract FactoryNode class content
    factory_class_match = re.search(r'class FactoryNode:.*?(?=class\s|\Z)', content, re.DOTALL)
    assert factory_class_match, "Could not find FactoryNode class"
    
    factory_class_content = factory_class_match.group(0)
    
    # Check node_label
    assert "node_label = 'ObjDetCount'" in factory_class_content, "FactoryNode should have node_label = 'ObjDetCount'"
    
    # Check node_tag
    assert "node_tag = 'ObjDetCount'" in factory_class_content, "FactoryNode should have node_tag = 'ObjDetCount'"
    
    print("✓ FactoryNode has correct attributes")


def test_add_node_method_signature():
    """Test that add_node method has the correct signature"""
    with open('node/TriggerNode/node_objdetcount.py', 'r') as f:
        content = f.read()
    
    # Extract FactoryNode class content
    factory_class_match = re.search(r'class FactoryNode:.*?(?=class\s|\Z)', content, re.DOTALL)
    assert factory_class_match, "Could not find FactoryNode class"
    
    factory_class_content = factory_class_match.group(0)
    
    # Check for add_node method with expected parameters
    add_node_match = re.search(r'def add_node\((.*?)\):', factory_class_content, re.DOTALL)
    assert add_node_match, "Could not find add_node method"
    
    params = add_node_match.group(1)
    
    # Expected parameters
    expected_params = ['parent', 'node_id', 'pos', 'opencv_setting_dict', 'callback']
    
    for param in expected_params:
        assert param in params, f"add_node should have parameter: {param}"
    
    print("✓ add_node has correct signature")


def test_add_node_calls_node_add_node():
    """Test that FactoryNode.add_node creates a Node instance and calls its add_node method"""
    with open('node/TriggerNode/node_objdetcount.py', 'r') as f:
        content = f.read()
    
    # Extract FactoryNode class content
    factory_class_match = re.search(r'class FactoryNode:.*?(?=class\s|\Z)', content, re.DOTALL)
    assert factory_class_match, "Could not find FactoryNode class"
    
    factory_class_content = factory_class_match.group(0)
    
    # Check that add_node method creates a Node instance
    assert 'node = Node()' in factory_class_content, "add_node should create a Node instance"
    
    # Check that it calls node.add_node
    assert 'node.add_node(' in factory_class_content, "add_node should call node.add_node()"
    
    # Check that it returns the node
    assert 'return node.add_node(' in factory_class_content, "add_node should return the result of node.add_node()"
    
    print("✓ add_node creates Node instance and calls its add_node method")


if __name__ == '__main__':
    # Run tests
    test_factorynode_has_add_node_method()
    test_factorynode_attributes()
    test_add_node_method_signature()
    test_add_node_calls_node_add_node()
    
    print("\n✅ All FactoryNode tests passed!")
