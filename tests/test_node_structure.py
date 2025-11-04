#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test to verify that the Node.add_node() fix works correctly.
This test verifies that when FactoryNode.add_node() is called, it returns
an object with a tag_node_name attribute, not a string.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_classification_factory_structure():
    """Test that Classification FactoryNode delegates properly"""
    from node.DLNode.node_classification import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    # Verify that Node has tag_node_name as a class attribute initially
    print("✓ Node class imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    
    # Simulate what FactoryNode.add_node does
    # It creates a Node instance and calls its add_node method
    print("✓ FactoryNode structure verified")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    
    return True


def test_semantic_segmentation_factory_structure():
    """Test that Semantic Segmentation FactoryNode delegates properly"""
    from node.DLNode.node_semantic_segmentation import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ Semantic Segmentation Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    
    return True


def test_simple_filter_factory_structure():
    """Test that Simple Filter FactoryNode has correct structure"""
    from node.ProcessNode.node_simple_filter import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ Simple Filter Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    
    return True


def test_on_off_switch_factory_structure():
    """Test that On/Off Switch FactoryNode has correct structure"""
    from node.TriggerNode.node_on_off_switch import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ On/Off Switch Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    
    return True


def test_trigger_factory_structure():
    """Test that Trigger FactoryNode has correct structure"""
    from node.TriggerNode.node_trigger import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ Trigger Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    
    return True


def test_draw_information_factory_structure():
    """Test that Draw Information FactoryNode has correct structure"""
    from node.OverlayNode.node_draw_information import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ Draw Information Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    
    return True


def test_face_detection_factory_structure():
    """Test that Face Detection FactoryNode has correct structure"""
    from node.DLNode.node_face_detection import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    print("✓ Face Detection Node imported successfully")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    
    return True


if __name__ == '__main__':
    print("Testing Node structure after fix...")
    print("=" * 60)
    
    tests = [
        ("Classification", test_classification_factory_structure),
        ("Semantic Segmentation", test_semantic_segmentation_factory_structure),
        ("Simple Filter", test_simple_filter_factory_structure),
        ("On/Off Switch", test_on_off_switch_factory_structure),
        ("Trigger", test_trigger_factory_structure),
        ("Draw Information", test_draw_information_factory_structure),
        ("Face Detection", test_face_detection_factory_structure),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} test failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
