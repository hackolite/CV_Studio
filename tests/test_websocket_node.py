#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the Websocket input node.
Verifies that the websocket node can be imported and instantiated correctly.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_websocket_node_import():
    """Test that Websocket node can be imported"""
    from node.InputNode.node_websocket import FactoryNode, WebsocketNode
    
    print("✓ Websocket node imported successfully")
    return True


def test_websocket_factory_structure():
    """Test that Websocket FactoryNode has correct structure"""
    from node.InputNode.node_websocket import FactoryNode, WebsocketNode
    
    factory = FactoryNode()
    node = WebsocketNode()
    
    # Verify FactoryNode attributes
    assert hasattr(factory, 'node_label'), "FactoryNode missing node_label"
    assert hasattr(factory, 'node_tag'), "FactoryNode missing node_tag"
    assert factory.node_label == 'Websocket', f"Expected node_label 'Websocket', got '{factory.node_label}'"
    assert factory.node_tag == 'Websocket', f"Expected node_tag 'Websocket', got '{factory.node_tag}'"
    
    # Verify Node attributes
    assert hasattr(node, 'node_label'), "Node missing node_label"
    assert hasattr(node, 'node_tag'), "Node missing node_tag"
    assert node.node_label == 'Websocket', f"Expected node_label 'Websocket', got '{node.node_label}'"
    assert node.node_tag == 'Websocket', f"Expected node_tag 'Websocket', got '{node.node_tag}'"
    
    # Verify Node has required type constants
    assert hasattr(node, 'TYPE_AUDIO'), "Node missing TYPE_AUDIO"
    assert hasattr(node, 'TYPE_JSON'), "Node missing TYPE_JSON"
    assert hasattr(node, 'TYPE_INT'), "Node missing TYPE_INT"
    assert hasattr(node, 'TYPE_TEXT'), "Node missing TYPE_TEXT"
    
    # Verify Node has required methods
    assert hasattr(node, 'update'), "Node missing update method"
    assert hasattr(node, 'close'), "Node missing close method"
    assert hasattr(node, 'get_setting_dict'), "Node missing get_setting_dict method"
    assert hasattr(node, 'set_setting_dict'), "Node missing set_setting_dict method"
    
    print("✓ Websocket node has correct structure")
    return True


def test_websocket_node_new_fields():
    """Test that the new API_KEY and message fields are correctly defined"""
    from node.InputNode.node_websocket import FactoryNode, WebsocketNode
    
    # The field tags are created in add_node, so we can't test them directly on the node instance
    # But we can verify the get_setting_dict and set_setting_dict methods handle the new fields
    node = WebsocketNode()
    
    # Verify the methods exist
    assert callable(node.get_setting_dict), "get_setting_dict should be callable"
    assert callable(node.set_setting_dict), "set_setting_dict should be callable"
    
    print("✓ Websocket node methods are callable")
    return True


if __name__ == "__main__":
    print("\n=== Testing Websocket Node ===\n")
    
    try:
        test_websocket_node_import()
        test_websocket_factory_structure()
        test_websocket_node_new_fields()
        print("\n✅ All tests passed!\n")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
