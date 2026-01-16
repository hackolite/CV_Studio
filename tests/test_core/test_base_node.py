#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for src/core/nodes/base.py - BaseNode class
"""
import sys
import os
import pytest
from typing import Dict, Any, List, Optional

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.nodes.base import BaseNode
from src.utils.exceptions import NodeExecutionError, NodeConfigurationError


class ConcreteNode(BaseNode):
    """Concrete implementation of BaseNode for testing"""
    
    _ver = '1.0.0'
    node_label = 'Test Node'
    node_tag = 'TestNode'
    
    def __init__(self):
        super().__init__()
        self.add_node_called = False
        self.update_called = False
        self.close_called = False
        self.last_settings = None
    
    def add_node(self, parent, node_id: int, pos: List[int], 
                 opencv_setting_dict: Optional[Dict[str, Any]] = None):
        """Implementation of abstract method"""
        self.add_node_called = True
        return f"node_{node_id}"
    
    def update(self, node_id: int, connection_list: List[Any],
               node_image_dict: Dict[str, Any], 
               node_result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Implementation of abstract method"""
        self.update_called = True
        return {"image": None, "json": None}
    
    def get_setting_dict(self, node_id: int) -> Dict[str, Any]:
        """Implementation of abstract method"""
        return {"node_id": node_id, "ver": self._ver}
    
    def set_setting_dict(self, node_id: int, setting_dict: Dict[str, Any]):
        """Implementation of abstract method"""
        self.last_settings = setting_dict
    
    def close(self, node_id: int):
        """Implementation of abstract method"""
        self.close_called = True


class TestBaseNode:
    """Test suite for BaseNode class"""
    
    def test_node_creation(self):
        """Test that a BaseNode can be instantiated"""
        node = ConcreteNode()
        assert node is not None
        assert isinstance(node, BaseNode)
    
    def test_node_has_unique_id(self):
        """Test that each node gets a unique ID"""
        node1 = ConcreteNode()
        node2 = ConcreteNode()
        
        assert node1.node_id != node2.node_id
        assert len(node1.node_id) > 0
        assert len(node2.node_id) > 0
    
    def test_node_metadata(self):
        """Test node metadata attributes"""
        node = ConcreteNode()
        
        assert node._ver == '1.0.0'
        assert node.node_label == 'Test Node'
        assert node.node_tag == 'TestNode'
    
    def test_node_type_constants(self):
        """Test that node type constants are defined"""
        node = ConcreteNode()
        
        assert hasattr(node, 'TYPE_INT')
        assert hasattr(node, 'TYPE_FLOAT')
        assert hasattr(node, 'TYPE_IMAGE')
        assert hasattr(node, 'TYPE_TIME_MS')
        assert hasattr(node, 'TYPE_JSON')
        assert hasattr(node, 'TYPE_SOUND')
        assert hasattr(node, 'TYPE_TEXT')
        assert hasattr(node, 'TYPE_BOOLEAN')
        assert hasattr(node, 'TYPE_AUDIO')
        
        assert node.TYPE_INT == 'Int'
        assert node.TYPE_FLOAT == 'Float'
        assert node.TYPE_IMAGE == 'Image'
    
    def test_add_node(self):
        """Test add_node method"""
        node = ConcreteNode()
        result = node.add_node(parent=None, node_id=1, pos=[0, 0])
        
        assert node.add_node_called
        assert result == "node_1"
    
    def test_update(self):
        """Test update method"""
        node = ConcreteNode()
        result = node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={}
        )
        
        assert node.update_called
        assert isinstance(result, dict)
        assert "image" in result
        assert "json" in result
    
    def test_get_setting_dict(self):
        """Test get_setting_dict method"""
        node = ConcreteNode()
        settings = node.get_setting_dict(node_id=5)
        
        assert isinstance(settings, dict)
        assert settings["node_id"] == 5
        assert settings["ver"] == '1.0.0'
    
    def test_set_setting_dict(self):
        """Test set_setting_dict method"""
        node = ConcreteNode()
        test_settings = {"param1": 10, "param2": "test"}
        
        node.set_setting_dict(node_id=1, setting_dict=test_settings)
        
        assert node.last_settings == test_settings
    
    def test_close(self):
        """Test close method"""
        node = ConcreteNode()
        node.close(node_id=1)
        
        assert node.close_called
    
    def test_validate_config_default(self):
        """Test default validate_config implementation"""
        node = ConcreteNode()
        config = {"param1": 1, "param2": 2}
        
        assert node.validate_config(config) == True
    
    def test_handle_error(self):
        """Test handle_error method"""
        node = ConcreteNode()
        test_error = ValueError("Test error")
        
        with pytest.raises(NodeExecutionError) as exc_info:
            node.handle_error(node_id=1, error=test_error)
        
        assert exc_info.value.node_id == 1
        assert "Test error" in str(exc_info.value)


class TestBaseNodeAbstract:
    """Test that BaseNode enforces abstract methods"""
    
    def test_cannot_instantiate_base_node(self):
        """Test that BaseNode cannot be instantiated directly"""
        with pytest.raises(TypeError):
            # This should fail because BaseNode has abstract methods
            node = BaseNode()


class TestBaseNodeSubclassMissingMethods:
    """Test that subclasses must implement all abstract methods"""
    
    def test_missing_add_node(self):
        """Test that missing add_node raises TypeError"""
        with pytest.raises(TypeError):
            class IncompleteNode1(BaseNode):
                def update(self, node_id, connection_list, node_image_dict, node_result_dict):
                    pass
                def get_setting_dict(self, node_id):
                    pass
                def set_setting_dict(self, node_id, setting_dict):
                    pass
                def close(self, node_id):
                    pass
            
            node = IncompleteNode1()
    
    def test_missing_update(self):
        """Test that missing update raises TypeError"""
        with pytest.raises(TypeError):
            class IncompleteNode2(BaseNode):
                def add_node(self, parent, node_id, pos, opencv_setting_dict=None):
                    pass
                def get_setting_dict(self, node_id):
                    pass
                def set_setting_dict(self, node_id, setting_dict):
                    pass
                def close(self, node_id):
                    pass
            
            node = IncompleteNode2()


if __name__ == '__main__':
    print("Running BaseNode unit tests...")
    print("=" * 60)
    pytest.main([__file__, '-v'])
