#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for src/core/nodes/enhanced.py - EnhancedNode class
"""
import sys
import os
import pytest
import numpy as np
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.nodes.enhanced import EnhancedNode
from src.core.nodes.base import BaseNode


class ConcreteEnhancedNode(EnhancedNode):
    """Concrete implementation of EnhancedNode for testing"""
    
    _ver = '1.0.0'
    node_label = 'Test Enhanced Node'
    node_tag = 'TestEnhancedNode'
    
    def __init__(self, node_id: int = 1, connection_dict: Optional[Dict] = None,
                 opencv_setting_dict: Optional[Dict] = None):
        super().__init__(node_id, connection_dict, opencv_setting_dict)
        self.process_called = False
    
    def process_image(self, image):
        """Test method for safe_execute"""
        self.process_called = True
        return image


class TestEnhancedNode:
    """Test suite for EnhancedNode class"""
    
    def test_enhanced_node_creation(self):
        """Test that an EnhancedNode can be instantiated"""
        node = ConcreteEnhancedNode()
        assert node is not None
        assert isinstance(node, EnhancedNode)
        assert isinstance(node, BaseNode)
    
    def test_enhanced_node_with_settings(self):
        """Test EnhancedNode initialization with settings"""
        settings = {
            'process_width': 1280,
            'process_height': 720,
            'use_pref_counter': True,
            'use_gpu': True
        }
        node = ConcreteEnhancedNode(node_id=5, opencv_setting_dict=settings)
        
        assert node.small_window_w == 1280
        assert node.small_window_h == 720
        assert node.use_pref_counter == True
        assert node.use_gpu == True
    
    def test_enhanced_node_default_settings(self):
        """Test EnhancedNode with default settings"""
        node = ConcreteEnhancedNode()
        
        assert node.small_window_w == 640
        assert node.small_window_h == 480
        assert node.use_pref_counter == False
        assert node.use_gpu == False
    
    def test_tag_node_name(self):
        """Test that tag_node_name is correctly formatted"""
        node = ConcreteEnhancedNode(node_id=7)
        assert node.tag_node_name == "7:TestEnhancedNode"
    
    def test_type_constants(self):
        """Test that EnhancedNode has type constants for compatibility"""
        node = ConcreteEnhancedNode()
        
        assert node.TYPE_BOOLEAN == "BOOLEAN"
        assert node.TYPE_TEXT == "TEXT"
        assert node.TYPE_IMAGE == "IMAGE"
        assert node.TYPE_FLOAT == "FLOAT"
        assert node.TYPE_INT == "INT"
        assert node.TYPE_TIME_MS == "TIME_MS"
        assert node.TYPE_AUDIO == "AUDIO"
        assert node.TYPE_JSON == "JSON"
    
    def test_input_output_constants(self):
        """Test INPUT/OUTPUT constants"""
        node = ConcreteEnhancedNode()
        
        assert node.INPUT == "INPUT"
        assert node.OUTPUT == "OUTPUT"
    
    def test_convert_cv_to_dpg_valid_image(self):
        """Test converting a valid OpenCV image to DPG format"""
        node = ConcreteEnhancedNode()
        
        # Create a test image (100x100 BGR)
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        width, height = 50, 50
        
        result = node.convert_cv_to_dpg(test_image, width, height)
        
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert result.shape == (width * height * 3,)
        assert np.all(result >= 0.0) and np.all(result <= 1.0)
    
    def test_convert_cv_to_dpg_empty_image(self):
        """Test converting an empty image returns safe default"""
        node = ConcreteEnhancedNode()
        
        # Create an empty image
        empty_image = np.zeros((0, 0, 3), dtype=np.uint8)
        width, height = 10, 10
        
        result = node.convert_cv_to_dpg(empty_image, width, height)
        
        # Should return a valid array (may be zeros on error)
        assert result is not None
        assert isinstance(result, np.ndarray)
    
    def test_get_setting_dict(self):
        """Test get_setting_dict method"""
        node = ConcreteEnhancedNode(node_id=3)
        
        # Mock dpg to avoid dependency
        with patch('src.core.nodes.enhanced.dpg') as mock_dpg:
            mock_dpg.get_item_pos.return_value = [100, 200]
            
            settings = node.get_setting_dict(node_id=3)
            
            assert isinstance(settings, dict)
            assert settings['ver'] == '1.0.0'
            assert settings['pos'] == [100, 200]
    
    def test_get_setting_dict_no_dpg(self):
        """Test get_setting_dict when DPG is not available"""
        node = ConcreteEnhancedNode(node_id=4)
        
        # Mock dpg as None
        with patch('src.core.nodes.enhanced.dpg', None):
            settings = node.get_setting_dict(node_id=4)
            
            assert isinstance(settings, dict)
            assert settings['ver'] == '1.0.0'
    
    def test_get_setting_dict_dpg_error(self):
        """Test get_setting_dict when DPG raises an error"""
        node = ConcreteEnhancedNode(node_id=5)
        
        with patch('src.core.nodes.enhanced.dpg') as mock_dpg:
            mock_dpg.get_item_pos.side_effect = Exception("DPG error")
            
            settings = node.get_setting_dict(node_id=5)
            
            assert isinstance(settings, dict)
            assert settings['ver'] == '1.0.0'
            assert settings['pos'] == [0, 0]  # Default on error
    
    def test_set_setting_dict(self):
        """Test set_setting_dict method"""
        node = ConcreteEnhancedNode(node_id=6)
        test_settings = {"param1": 100, "param2": "value"}
        
        # Should not raise an error
        node.set_setting_dict(node_id=6, setting_dict=test_settings)
    
    def test_close(self):
        """Test close method"""
        node = ConcreteEnhancedNode(node_id=7)
        
        # Should not raise an error
        node.close(node_id=7)
    
    def test_update_default(self):
        """Test default update method"""
        node = ConcreteEnhancedNode()
        
        result = node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={}
        )
        
        assert isinstance(result, dict)
        assert result["image"] is None
        assert result["json"] is None
    
    def test_add_node_default(self):
        """Test default add_node method (should log warning)"""
        node = ConcreteEnhancedNode()
        
        result = node.add_node(
            parent=None,
            node_id=1,
            pos=[0, 0]
        )
        
        assert result is None
    
    def test_safe_execute_success(self):
        """Test safe_execute with successful execution"""
        node = ConcreteEnhancedNode()
        
        def test_func(x, y):
            return x + y
        
        result = node.safe_execute(test_func, 5, 10)
        assert result == 15
    
    def test_safe_execute_with_error(self):
        """Test safe_execute with error handling"""
        node = ConcreteEnhancedNode()
        
        def error_func():
            raise ValueError("Test error")
        
        result = node.safe_execute(error_func)
        assert result is None  # Should return None on error
    
    def test_safe_execute_with_kwargs(self):
        """Test safe_execute with keyword arguments"""
        node = ConcreteEnhancedNode()
        
        def test_func(a, b=10, c=20):
            return a + b + c
        
        result = node.safe_execute(test_func, 5, b=15, c=25)
        assert result == 45
    
    def test_safe_execute_complex_operation(self):
        """Test safe_execute with complex operation"""
        node = ConcreteEnhancedNode()
        test_image = np.ones((10, 10, 3), dtype=np.uint8)
        
        result = node.safe_execute(node.process_image, test_image)
        
        assert node.process_called
        assert result is not None
        assert np.array_equal(result, test_image)


class TestEnhancedNodeCompatibility:
    """Test backward compatibility features"""
    
    def test_opencv_setting_dict_compatibility(self):
        """Test that opencv_setting_dict is properly stored"""
        settings = {'custom_param': 'value'}
        node = ConcreteEnhancedNode(opencv_setting_dict=settings)
        
        assert node._opencv_setting_dict == settings
    
    def test_connection_dict_parameter(self):
        """Test that connection_dict parameter is accepted"""
        connection_dict = {'connection': 'data'}
        node = ConcreteEnhancedNode(connection_dict=connection_dict)
        
        # Should not raise an error
        assert node is not None
    
    def test_small_window_dimensions(self):
        """Test that small window dimensions are properly set"""
        settings = {
            'process_width': 800,
            'process_height': 600
        }
        node = ConcreteEnhancedNode(opencv_setting_dict=settings)
        
        assert node.small_window_w == 800
        assert node.small_window_h == 600
        assert node._small_window_w == 800
        assert node._small_window_h == 600


if __name__ == '__main__':
    print("Running EnhancedNode unit tests...")
    print("=" * 60)
    pytest.main([__file__, '-v'])
