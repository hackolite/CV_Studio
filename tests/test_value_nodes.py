#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that IntValue and FloatValue nodes are properly implemented.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_int_value_node_structure():
    """Test that IntValue node has correct structure"""
    from node.InputNode.node_int_value import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    # Verify factory attributes
    assert factory.node_label == 'IntValue', f"Expected node_label 'IntValue', got '{factory.node_label}'"
    assert factory.node_tag == 'IntValue', f"Expected node_tag 'IntValue', got '{factory.node_tag}'"
    
    # Verify node attributes
    assert node.node_label == 'IntValue', f"Expected node_label 'IntValue', got '{node.node_label}'"
    assert node.node_tag == 'IntValue', f"Expected node_tag 'IntValue', got '{node.node_tag}'"
    
    # Verify node has required type constants
    assert hasattr(node, 'TYPE_INT'), "Node should have TYPE_INT attribute"
    assert node.TYPE_INT == 'INT', f"Expected TYPE_INT to be 'INT', got '{node.TYPE_INT}'"
    
    print("✓ IntValue Node structure verified")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")


def test_float_value_node_structure():
    """Test that FloatValue node has correct structure"""
    from node.InputNode.node_float_value import FactoryNode, Node
    
    factory = FactoryNode()
    node = Node()
    
    # Verify factory attributes
    assert factory.node_label == 'FloatValue', f"Expected node_label 'FloatValue', got '{factory.node_label}'"
    assert factory.node_tag == 'FloatValue', f"Expected node_tag 'FloatValue', got '{factory.node_tag}'"
    
    # Verify node attributes
    assert node.node_label == 'FloatValue', f"Expected node_label 'FloatValue', got '{node.node_label}'"
    assert node.node_tag == 'FloatValue', f"Expected node_tag 'FloatValue', got '{node.node_tag}'"
    
    # Verify node has required type constants
    assert hasattr(node, 'TYPE_FLOAT'), "Node should have TYPE_FLOAT attribute"
    assert node.TYPE_FLOAT == 'FLOAT', f"Expected TYPE_FLOAT to be 'FLOAT', got '{node.TYPE_FLOAT}'"
    
    print("✓ FloatValue Node structure verified")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")


def test_int_value_node_methods():
    """Test that IntValue node has required methods"""
    from node.InputNode.node_int_value import Node
    
    node = Node()
    
    # Check for required methods
    assert hasattr(node, 'update'), "Node should have update method"
    assert hasattr(node, 'close'), "Node should have close method"
    assert hasattr(node, 'get_setting_dict'), "Node should have get_setting_dict method"
    assert hasattr(node, 'set_setting_dict'), "Node should have set_setting_dict method"
    
    print("✓ IntValue Node methods verified")


def test_float_value_node_methods():
    """Test that FloatValue node has required methods"""
    from node.InputNode.node_float_value import Node
    
    node = Node()
    
    # Check for required methods
    assert hasattr(node, 'update'), "Node should have update method"
    assert hasattr(node, 'close'), "Node should have close method"
    assert hasattr(node, 'get_setting_dict'), "Node should have get_setting_dict method"
    assert hasattr(node, 'set_setting_dict'), "Node should have set_setting_dict method"
    
    print("✓ FloatValue Node methods verified")


if __name__ == '__main__':
    print("Testing IntValue and FloatValue nodes...")
    print("=" * 60)
    
    tests = [
        ("IntValue Structure", test_int_value_node_structure),
        ("FloatValue Structure", test_float_value_node_structure),
        ("IntValue Methods", test_int_value_node_methods),
        ("FloatValue Methods", test_float_value_node_methods),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name} test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name} test failed with error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
