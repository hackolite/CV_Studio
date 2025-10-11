#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for NodeFactory"""

import pytest
from src.core.nodes.factory import NodeFactory
from src.core.nodes.base import BaseNode
from src.utils.exceptions import NodeError


class TestNode(BaseNode):
    """Test node implementation"""
    node_label = 'Test Node'
    node_tag = 'TestNode'
    
    def add_node(self, parent, node_id, pos, opencv_setting_dict=None):
        return None
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        return {"image": None, "json": None}
    
    def get_setting_dict(self, node_id):
        return {}
    
    def set_setting_dict(self, node_id, setting_dict):
        pass
    
    def close(self, node_id):
        pass


def test_node_factory_register():
    """Test registering a node type"""
    NodeFactory.register('TestNode', TestNode)
    assert NodeFactory.is_registered('TestNode')


def test_node_factory_create():
    """Test creating a node instance"""
    NodeFactory.register('TestNode', TestNode)
    node = NodeFactory.create('TestNode')
    assert isinstance(node, TestNode)


def test_node_factory_create_unregistered():
    """Test creating an unregistered node type"""
    with pytest.raises(NodeError) as exc_info:
        NodeFactory.create('UnregisteredNode')
    assert 'not registered' in str(exc_info.value)


def test_node_factory_get_registered_types():
    """Test getting all registered types"""
    NodeFactory.register('TestNode', TestNode)
    types = NodeFactory.get_registered_types()
    assert 'TestNode' in types
    assert types['TestNode'] == TestNode


def test_node_factory_is_registered():
    """Test checking if a node type is registered"""
    NodeFactory.register('TestNode', TestNode)
    assert NodeFactory.is_registered('TestNode')
    assert not NodeFactory.is_registered('NonexistentNode')


def test_node_factory_unregister():
    """Test unregistering a node type"""
    NodeFactory.register('TestNode', TestNode)
    assert NodeFactory.is_registered('TestNode')
    
    NodeFactory.unregister('TestNode')
    assert not NodeFactory.is_registered('TestNode')


def test_node_factory_replace_registration():
    """Test replacing a node registration"""
    class TestNode2(BaseNode):
        node_tag = 'TestNode2'
        
        def add_node(self, parent, node_id, pos, opencv_setting_dict=None):
            return None
        def update(self, node_id, connection_list, node_image_dict, node_result_dict):
            return {}
        def get_setting_dict(self, node_id):
            return {}
        def set_setting_dict(self, node_id, setting_dict):
            pass
        def close(self, node_id):
            pass
    
    NodeFactory.register('TestNode', TestNode)
    NodeFactory.register('TestNode', TestNode2)  # Replace
    
    node = NodeFactory.create('TestNode')
    assert isinstance(node, TestNode2)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
