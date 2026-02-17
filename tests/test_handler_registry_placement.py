#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify handler_registry placement in node editor
This test ensures the handler_registry is properly scoped to the window
to allow node_editor to receive mouse wheel zoom events.
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHandlerRegistryPlacement(unittest.TestCase):
    """Test that verifies the handler_registry is properly placed"""
    
    # Expected indentation for handler_registry inside window context
    EXPECTED_INDENTATION = 12  # 3 levels deep (class, __init__, window)
    
    def test_handler_registry_in_node_main(self):
        """Verify handler_registry code structure in node_main.py"""
        node_main_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'node_editor',
            'node_main.py'
        )
        
        with open(node_main_path, 'r') as f:
            content = f.read()
        
        # Verify that handler_registry is inside window context (not global)
        # The fix moves handler_registry from outside the window (after 'self.window = window')
        # to inside the window (before 'self.window = window')
        
        # Check that the old pattern (handler_registry outside window) is NOT present
        self.assertNotIn(
            '        # Move handler_registry outside window context',
            content,
            "Handler registry should not be outside window context (old comment should be removed)"
        )
        
        # Find the __init__ method context to search within
        init_start = content.find('def __init__(')
        self.assertGreater(init_start, 0, "__init__ method should exist")
        
        # Find next method after __init__ to limit search scope
        next_method = content.find('\n    def ', init_start + 1)
        init_context = content[init_start:next_method] if next_method > 0 else content[init_start:]
        
        # Check that handler_registry comes BEFORE self.window = window within __init__
        window_assignment_idx = init_context.find('self.window = window')
        handler_registry_idx = init_context.find('with dpg.handler_registry():')
        
        self.assertGreater(
            window_assignment_idx,
            handler_registry_idx,
            "handler_registry should be created before window assignment (inside window context)"
        )
        
        # Verify the handler_registry is created with proper indentation
        lines = init_context.split('\n')
        handler_registry_line = None
        for line in lines:
            # Match actual code, not comments or strings
            stripped = line.lstrip()
            if stripped.startswith('with dpg.handler_registry():'):
                handler_registry_line = line
                break
        
        self.assertIsNotNone(handler_registry_line, "handler_registry line should exist in __init__")
        
        # Count leading spaces (should be EXPECTED_INDENTATION for inside window context)
        leading_spaces = len(handler_registry_line) - len(handler_registry_line.lstrip())
        self.assertEqual(
            leading_spaces,
            self.EXPECTED_INDENTATION,
            f"handler_registry should have {self.EXPECTED_INDENTATION} spaces (inside window), got {leading_spaces}"
        )
    
    def test_handler_registry_comment_updated(self):
        """Verify the comment explaining handler_registry placement is correct"""
        node_main_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'node_editor',
            'node_main.py'
        )
        
        with open(node_main_path, 'r') as f:
            content = f.read()
        
        # Check for the new comment explaining the fix
        self.assertIn(
            'Create handler registry inside window',
            content,
            "Should have comment explaining handler registry is inside window"
        )
        
        self.assertIn(
            'scoped to the window',
            content,
            "Should explain that handlers are scoped to the window"
        )


if __name__ == '__main__':
    unittest.main()
