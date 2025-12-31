#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that Node subclasses properly initialize parent class attributes.

This test ensures that the fix for the AttributeError: 'Node' object has no 
attribute '_last_texture_update' issue is working correctly.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.basenode import Node as BaseNode


def test_base_node_initialization():
    """Test that base Node class initializes all required attributes."""
    node = BaseNode()
    
    # Check that all texture cache related attributes are initialized
    assert hasattr(node, '_last_texture_update'), "BaseNode should have _last_texture_update attribute"
    assert hasattr(node, '_texture_cache'), "BaseNode should have _texture_cache attribute"
    assert hasattr(node, '_texture_cache_hash'), "BaseNode should have _texture_cache_hash attribute"
    assert hasattr(node, '_texture_update_interval'), "BaseNode should have _texture_update_interval attribute"
    
    # Check initial values
    assert node._last_texture_update == 0, "_last_texture_update should be initialized to 0"
    assert node._texture_cache is None, "_texture_cache should be initialized to None"
    assert node._texture_cache_hash is None, "_texture_cache_hash should be initialized to None"
    assert node._texture_update_interval == 0.033, "_texture_update_interval should be initialized to 0.033"
    
    print("✓ Base Node initialization test passed")


def test_node_subclass_inheritance():
    """
    Test that Node subclasses inherit parent initialization.
    
    This is a mock test that verifies the pattern is correct without importing
    the actual DLNode classes (which have heavy dependencies).
    """
    
    # Create a test subclass that mimics the pattern used in DLNode files
    class TestNode(BaseNode):
        node_label = 'TestNode'
        node_tag = 'TestNode'
        
        def __init__(self):
            super().__init__()
    
    # Create an instance
    node = TestNode()
    
    # Verify that parent attributes are properly initialized
    assert hasattr(node, '_last_texture_update'), "TestNode should inherit _last_texture_update"
    assert hasattr(node, '_texture_cache'), "TestNode should inherit _texture_cache"
    assert hasattr(node, '_texture_cache_hash'), "TestNode should inherit _texture_cache_hash"
    assert hasattr(node, '_texture_update_interval'), "TestNode should inherit _texture_update_interval"
    
    # Check values
    assert node._last_texture_update == 0, "Inherited _last_texture_update should be 0"
    assert node._texture_cache is None, "Inherited _texture_cache should be None"
    assert node._texture_cache_hash is None, "Inherited _texture_cache_hash should be None"
    assert node._texture_update_interval == 0.033, "Inherited _texture_update_interval should be 0.033"
    
    print("✓ Node subclass inheritance test passed")


def test_node_subclass_without_super():
    """
    Test that demonstrates the bug when super().__init__() is not called.
    
    This test shows what happens when a subclass doesn't call super().__init__().
    """
    
    class BrokenNode(BaseNode):
        node_label = 'BrokenNode'
        node_tag = 'BrokenNode'
        
        def __init__(self):
            pass  # Bug: not calling super().__init__()
    
    # Create an instance
    node = BrokenNode()
    
    # Verify that parent attributes are NOT initialized
    assert not hasattr(node, '_last_texture_update'), "BrokenNode should NOT have _last_texture_update (demonstrating the bug)"
    assert not hasattr(node, '_texture_cache'), "BrokenNode should NOT have _texture_cache (demonstrating the bug)"
    
    print("✓ Node subclass without super() test passed (bug demonstrated)")


if __name__ == '__main__':
    test_base_node_initialization()
    test_node_subclass_inheritance()
    test_node_subclass_without_super()
    print("\n✓ All tests passed!")
