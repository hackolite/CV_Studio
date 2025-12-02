#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Basic tests for DynamicPlay Node"""

import pytest
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_dynamic_play_node_registered():
    """Test that DynamicPlay node is registered in the menu"""
    from node_editor.style import VIDEO
    
    assert 'DynamicPlay' in VIDEO, "DynamicPlay should be registered in VIDEO menu"


def test_dynamic_play_node_exists():
    """Test that the DynamicPlay node file exists"""
    node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'VideoNode', 'node_dynamic_play.py'
    )
    
    assert os.path.exists(node_path), "node_dynamic_play.py file should exist"


def test_dynamic_play_node_imports():
    """Test that DynamicPlay node can be imported"""
    try:
        from node.VideoNode import node_dynamic_play
        assert hasattr(node_dynamic_play, 'FactoryNode'), "Should have FactoryNode class"
        assert hasattr(node_dynamic_play, 'Node'), "Should have Node class"
    except ImportError as e:
        pytest.fail(f"Failed to import node_dynamic_play: {e}")


def test_dynamic_play_factory_node():
    """Test DynamicPlay FactoryNode attributes"""
    from node.VideoNode.node_dynamic_play import FactoryNode
    
    factory = FactoryNode()
    assert factory.node_label == 'DynamicPlay', "node_label should be 'DynamicPlay'"
    assert factory.node_tag == 'DynamicPlay', "node_tag should be 'DynamicPlay'"


def test_dynamic_play_node_class():
    """Test DynamicPlay Node class attributes"""
    from node.VideoNode.node_dynamic_play import Node
    
    assert Node.node_label == 'DynamicPlay', "node_label should be 'DynamicPlay'"
    assert Node.node_tag == 'DynamicPlay', "node_tag should be 'DynamicPlay'"
    assert Node._max_slot_number == 9, "Should support up to 9 slots"


def test_dynamic_play_node_initialization():
    """Test DynamicPlay Node can be initialized"""
    from node.VideoNode.node_dynamic_play import Node
    
    node = Node()
    assert node is not None, "Node should be created"
    assert hasattr(node, '_init_hand_model'), "Should have hand model initialization method"
    assert hasattr(node, '_detect_hands'), "Should have hand detection method"
    assert hasattr(node, '_calculate_pinch_distance'), "Should have pinch distance calculation"


def test_dynamic_play_button_creation():
    """Test button grid creation logic"""
    from node.VideoNode.node_dynamic_play import Node
    
    node = Node()
    
    # Test with a dummy frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Test different slot numbers
    test_cases = [
        (1, 1, 1),  # 1 slot -> 1 col, 1 row
        (2, 2, 1),  # 2 slots -> 2 cols, 1 row
        (4, 2, 2),  # 4 slots -> 2 cols, 2 rows
        (6, 3, 2),  # 6 slots -> 3 cols, 2 rows
        (9, 3, 3),  # 9 slots -> 3 cols, 3 rows
    ]
    
    for num_slots, expected_cols, expected_rows in test_cases:
        buttons = node._create_grid_buttons(frame, num_slots)
        assert len(buttons) == num_slots, f"Should create {num_slots} buttons"
        
        # Verify all buttons have required fields
        for button in buttons:
            assert 'index' in button
            assert 'bounds' in button
            assert 'center' in button


def test_dynamic_play_pinch_distance():
    """Test pinch distance calculation"""
    from node.VideoNode.node_dynamic_play import Node
    
    node = Node()
    
    # Test with mock keypoints
    keypoints = {
        4: (100, 100),  # Thumb tip
        8: (150, 100),  # Index tip
    }
    
    distance = node._calculate_pinch_distance(keypoints)
    assert distance is not None, "Should calculate distance"
    assert distance == 50, "Distance should be 50 pixels"
    
    # Test with missing keypoints
    incomplete_keypoints = {4: (100, 100)}
    distance = node._calculate_pinch_distance(incomplete_keypoints)
    assert distance is None, "Should return None for incomplete keypoints"


def test_dynamic_play_zoom_application():
    """Test zoom application to frame"""
    from node.VideoNode.node_dynamic_play import Node
    
    node = Node()
    
    # Create test frame
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Apply 2x zoom
    zoom_scale = 2.0
    center = (320, 240)
    zoomed = node._apply_zoom(frame, zoom_scale, center)
    
    assert zoomed.shape == frame.shape, "Zoomed frame should have same dimensions"
    
    # Test with no zoom (scale = 1.0)
    no_zoom = node._apply_zoom(frame, 1.0, center)
    np.testing.assert_array_equal(no_zoom, frame, "No zoom should return original frame")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
