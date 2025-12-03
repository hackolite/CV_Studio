#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the SyncQueue node
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_sync_queue_import():
    """Test that the SyncQueue node can be imported"""
    try:
        from node.SystemNode import node_sync_queue
        assert hasattr(node_sync_queue, 'FactoryNode'), "FactoryNode class not found"
        assert hasattr(node_sync_queue, 'Node'), "Node class not found"
        print("✓ SyncQueue node import successful")
        return True
    except ImportError as e:
        print(f"✗ Failed to import SyncQueue node: {e}")
        return False


def test_factory_node_creation():
    """Test that FactoryNode can be instantiated"""
    try:
        from node.SystemNode import node_sync_queue
        factory = node_sync_queue.FactoryNode()
        assert factory.node_label == 'SyncQueue', f"Expected label 'SyncQueue', got '{factory.node_label}'"
        assert factory.node_tag == 'SyncQueue', f"Expected tag 'SyncQueue', got '{factory.node_tag}'"
        print("✓ FactoryNode creation successful")
        return True
    except Exception as e:
        print(f"✗ Failed to create FactoryNode: {e}")
        return False


def test_node_creation():
    """Test that Node class can be instantiated"""
    try:
        from node.SystemNode import node_sync_queue
        node = node_sync_queue.Node()
        assert node.node_label == 'SyncQueue', f"Expected label 'SyncQueue', got '{node.node_label}'"
        assert node.node_tag == 'SyncQueue', f"Expected tag 'SyncQueue', got '{node.node_tag}'"
        assert hasattr(node, '_max_slot_number'), "Node should have _max_slot_number attribute"
        assert hasattr(node, '_slot_id'), "Node should have _slot_id attribute"
        assert hasattr(node, '_sync_state'), "Node should have _sync_state attribute"
        print("✓ Node class instantiation successful")
        return True
    except Exception as e:
        print(f"✗ Failed to create Node instance: {e}")
        return False


def test_node_methods():
    """Test that Node has required methods"""
    try:
        from node.SystemNode import node_sync_queue
        node = node_sync_queue.Node()
        assert hasattr(node, 'update'), "Node should have update method"
        assert hasattr(node, 'close'), "Node should have close method"
        assert hasattr(node, 'get_setting_dict'), "Node should have get_setting_dict method"
        assert hasattr(node, 'set_setting_dict'), "Node should have set_setting_dict method"
        assert hasattr(node, '_add_slot'), "Node should have _add_slot method"
        print("✓ Node has all required methods")
        return True
    except Exception as e:
        print(f"✗ Node methods test failed: {e}")
        return False


if __name__ == '__main__':
    print("Running SyncQueue Node Tests\n")
    
    tests = [
        test_sync_queue_import,
        test_factory_node_creation,
        test_node_creation,
        test_node_methods,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Tests Passed: {passed}/{len(tests)}")
    print(f"Tests Failed: {failed}/{len(tests)}")
    print('='*50)
    
    sys.exit(0 if failed == 0 else 1)
