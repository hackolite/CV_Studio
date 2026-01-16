#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for src/core/nodes/node_abc_enhanced.py - DpgNodeABC class
"""
import sys
import os
import pytest
from typing import Dict, Any

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.nodes.node_abc_enhanced import DpgNodeABC


class ConcreteDpgNode(DpgNodeABC):
    """Concrete implementation of DpgNodeABC for testing"""
    
    _ver = '2.0.0'
    node_label = 'Test DPG Node'
    node_tag = 'TestDpgNode'
    
    def __init__(self):
        super().__init__()
        self.add_node_called = False
        self.update_called = False
        self.close_called = False
        self.last_settings = None
    
    def add_node(self, parent, node_id, pos, width=None, height=None, 
                 opencv_setting_dict=None):
        """Implementation of abstract method"""
        self.add_node_called = True
        return f"dpg_node_{node_id}"
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        """Implementation of abstract method"""
        self.update_called = True
        return {"image": None, "json": None}
    
    def get_setting_dict(self, node_id):
        """Implementation of abstract method"""
        return {"node_id": node_id, "ver": self._ver}
    
    def set_setting_dict(self, node_id, setting_dict):
        """Implementation of abstract method"""
        self.last_settings = setting_dict
    
    def close(self, node_id):
        """Implementation of abstract method"""
        self.close_called = True


class TestDpgNodeABC:
    """Test suite for DpgNodeABC class"""
    
    def test_dpg_node_creation(self):
        """Test that a DpgNodeABC can be instantiated"""
        node = ConcreteDpgNode()
        assert node is not None
        assert isinstance(node, DpgNodeABC)
    
    def test_dpg_node_metadata(self):
        """Test node metadata attributes"""
        node = ConcreteDpgNode()
        
        assert node._ver == '2.0.0'
        assert node.node_label == 'Test DPG Node'
        assert node.node_tag == 'TestDpgNode'
    
    def test_dpg_node_type_constants(self):
        """Test that DPG node type constants are defined"""
        node = ConcreteDpgNode()
        
        assert hasattr(node, 'TYPE_INT')
        assert hasattr(node, 'TYPE_FLOAT')
        assert hasattr(node, 'TYPE_IMAGE')
        assert hasattr(node, 'TYPE_TIME_MS')
        assert hasattr(node, 'TYPE_JSON')
        assert hasattr(node, 'TYPE_SOUND')
        
        assert node.TYPE_INT == 'Int'
        assert node.TYPE_FLOAT == 'Float'
        assert node.TYPE_IMAGE == 'Image'
        assert node.TYPE_TIME_MS == 'TimeMS'
        assert node.TYPE_JSON == 'Json'
        assert node.TYPE_SOUND == 'Sound'
    
    def test_add_node(self):
        """Test add_node method"""
        node = ConcreteDpgNode()
        result = node.add_node(
            parent=None, 
            node_id=1, 
            pos=[10, 20],
            width=100,
            height=100
        )
        
        assert node.add_node_called
        assert result == "dpg_node_1"
    
    def test_add_node_with_settings(self):
        """Test add_node with opencv_setting_dict"""
        node = ConcreteDpgNode()
        settings = {'use_gpu': True, 'process_width': 640}
        
        result = node.add_node(
            parent=None,
            node_id=2,
            pos=[0, 0],
            opencv_setting_dict=settings
        )
        
        assert node.add_node_called
    
    def test_update(self):
        """Test update method"""
        node = ConcreteDpgNode()
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
        node = ConcreteDpgNode()
        settings = node.get_setting_dict(node_id=5)
        
        assert isinstance(settings, dict)
        assert settings["node_id"] == 5
        assert settings["ver"] == '2.0.0'
    
    def test_set_setting_dict(self):
        """Test set_setting_dict method"""
        node = ConcreteDpgNode()
        test_settings = {"width": 640, "height": 480}
        
        node.set_setting_dict(node_id=1, setting_dict=test_settings)
        
        assert node.last_settings == test_settings
    
    def test_close(self):
        """Test close method"""
        node = ConcreteDpgNode()
        node.close(node_id=1)
        
        assert node.close_called


class TestDpgNodeABCAbstract:
    """Test that DpgNodeABC enforces abstract methods"""
    
    def test_cannot_instantiate_dpg_node_abc(self):
        """Test that DpgNodeABC cannot be instantiated directly"""
        with pytest.raises(TypeError):
            # This should fail because DpgNodeABC has abstract methods
            node = DpgNodeABC()


class TestDpgNodeABCSubclassMissingMethods:
    """Test that subclasses must implement all abstract methods"""
    
    def test_missing_add_node(self):
        """Test that missing add_node raises TypeError"""
        with pytest.raises(TypeError):
            class IncompleteNode1(DpgNodeABC):
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
            class IncompleteNode2(DpgNodeABC):
                def add_node(self, parent, node_id, pos, width=None, height=None, 
                           opencv_setting_dict=None):
                    pass
                def get_setting_dict(self, node_id):
                    pass
                def set_setting_dict(self, node_id, setting_dict):
                    pass
                def close(self, node_id):
                    pass
            
            node = IncompleteNode2()
    
    def test_missing_get_setting_dict(self):
        """Test that missing get_setting_dict raises TypeError"""
        with pytest.raises(TypeError):
            class IncompleteNode3(DpgNodeABC):
                def add_node(self, parent, node_id, pos, width=None, height=None,
                           opencv_setting_dict=None):
                    pass
                def update(self, node_id, connection_list, node_image_dict, node_result_dict):
                    pass
                def set_setting_dict(self, node_id, setting_dict):
                    pass
                def close(self, node_id):
                    pass
            
            node = IncompleteNode3()


class TestDpgNodeABCBackwardCompatibility:
    """Test backward compatibility with existing code"""
    
    def test_class_attributes_exist(self):
        """Test that expected class attributes exist"""
        assert hasattr(DpgNodeABC, '_ver')
        assert hasattr(DpgNodeABC, 'node_label')
        assert hasattr(DpgNodeABC, 'node_tag')
    
    def test_type_constants_exist(self):
        """Test that all expected type constants exist"""
        assert hasattr(DpgNodeABC, 'TYPE_INT')
        assert hasattr(DpgNodeABC, 'TYPE_FLOAT')
        assert hasattr(DpgNodeABC, 'TYPE_IMAGE')
        assert hasattr(DpgNodeABC, 'TYPE_TIME_MS')
        assert hasattr(DpgNodeABC, 'TYPE_JSON')
        assert hasattr(DpgNodeABC, 'TYPE_SOUND')
    
    def test_default_values(self):
        """Test default values for class attributes"""
        assert DpgNodeABC._ver == '0.0.0'
        assert DpgNodeABC.node_label == ''
        assert DpgNodeABC.node_tag == ''


if __name__ == '__main__':
    print("Running DpgNodeABC unit tests...")
    print("=" * 60)
    pytest.main([__file__, '-v'])
