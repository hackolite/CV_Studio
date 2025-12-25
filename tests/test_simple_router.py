#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test SimpleRouter node structure and basic functionality
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSimpleRouterNode(unittest.TestCase):
    """Test SimpleRouter node structure"""
    
    def test_import_simple_router(self):
        """Test that SimpleRouter module can be imported"""
        try:
            from node.RouterNode.node_simple_router import FactoryNode, Node
            self.assertTrue(True, "SimpleRouter module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import SimpleRouter: {e}")
    
    def test_factory_node_attributes(self):
        """Test FactoryNode has required attributes"""
        from node.RouterNode.node_simple_router import FactoryNode
        
        factory = FactoryNode()
        
        # Check required attributes
        self.assertEqual(factory.node_label, 'SimpleRouter')
        self.assertEqual(factory.node_tag, 'SimpleRouter')
        self.assertTrue(hasattr(factory, 'add_node'))
    
    def test_node_class_attributes(self):
        """Test Node class has required attributes"""
        from node.RouterNode.node_simple_router import Node
        
        node = Node()
        
        # Check required attributes
        self.assertEqual(node.node_label, 'SimpleRouter')
        self.assertEqual(node.node_tag, 'SimpleRouter')
        self.assertEqual(node._ver, '0.0.1')
        
        # Check methods exist
        self.assertTrue(hasattr(node, 'add_node'))
        self.assertTrue(hasattr(node, 'update'))
        self.assertTrue(hasattr(node, 'close'))
        self.assertTrue(hasattr(node, 'get_setting_dict'))
        self.assertTrue(hasattr(node, 'set_setting_dict'))
    
    def test_node_initialization(self):
        """Test Node initializes with correct defaults"""
        from node.RouterNode.node_simple_router import Node
        
        node = Node()
        
        # Check initialization values
        self.assertEqual(len(node.activation_timestamps), 0)
        self.assertIsNone(node.blink_start_time)
        self.assertFalse(node.blink_active)
        self.assertFalse(node.previous_trigger_state)
        self.assertEqual(node.num_slots, 2)
        self.assertEqual(node.max_slots, 10)
    
    def test_style_registration(self):
        """Test that SimpleRouter is registered in STYLE"""
        from node_editor.style import STYLE, ROUTER
        
        # Check SimpleRouter is in ROUTER list
        self.assertIn('SimpleRouter', ROUTER)
        
        # Check Router category exists in STYLE
        self.assertIn('Router', STYLE)
        self.assertIn('SimpleRouter', STYLE['Router']['names'])


if __name__ == '__main__':
    unittest.main()
