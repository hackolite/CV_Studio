#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Basic tests for CropMonitor Node - DISABLED"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_crop_monitor_node_disabled():
    """Test that CropMonitor node has been disabled"""
    # Check that the file has been renamed to _node_crop_monitor.py (disabled)
    disabled_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'ProcessNode', '_node_crop_monitor.py'
    )
    
    assert os.path.exists(disabled_node_path), "_node_crop_monitor.py file should exist (disabled)"
    
    # Read the file and check that it's still there but disabled
    with open(disabled_node_path, 'r') as f:
        content = f.read()
    
    # Verify it's the original crop monitor file
    assert 'class FactoryNode:' in content, "Should have FactoryNode class"
    assert "node_tag = 'CropMonitor'" in content, "Should have correct node tag"


def test_crop_monitor_not_in_menu():
    """Test that CropMonitor is NOT registered in the menu anymore"""
    from node_editor.style import PROCESS
    
    assert 'CropMonitor' not in PROCESS, "CropMonitor should NOT be registered in PROCESS menu"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
