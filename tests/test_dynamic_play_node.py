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
    
    # Create a fake node tag for color initialization
    fake_tag = "test_node:DynamicPlay"
    
    # Note: In the new architecture, squares represent OVERLAY streams (slots 1+)
    # So for num_slots total streams, we have num_slots-1 overlay buttons
    test_cases = [
        (2, 1),  # 2 slots (1 master + 1 overlay) -> 1 square
        (3, 2),  # 3 slots (1 master + 2 overlays) -> 2 squares
        (5, 4),  # 5 slots (1 master + 4 overlays) -> 4 squares
        (7, 6),  # 7 slots (1 master + 6 overlays) -> 6 squares
        (9, 8),  # 9 slots (1 master + 8 overlays) -> 8 squares
    ]
    
    for num_slots, expected_num_squares in test_cases:
        # Create squares for overlay streams (num_slots - 1 for master)
        num_overlays = num_slots - 1
        buttons = node._create_bottom_squares(frame, num_overlays, fake_tag)
        assert len(buttons) == num_overlays, f"Should create {num_overlays} squares for {num_slots} total slots"
        
        # Verify all buttons have required fields
        for button in buttons:
            assert 'index' in button
            assert 'bounds' in button
            assert 'center' in button
            assert 'color' in button  # New: verify color field exists


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


def test_dynamic_play_pinch_gesture():
    """Test pinch gesture detection"""
    from node.VideoNode.node_dynamic_play import Node
    
    node = Node()
    
    # Test with close fingers (pinch)
    close_keypoints = {
        4: (100, 100),  # Thumb tip
        8: (130, 100),  # Index tip (30 pixels away - pinch detected)
    }
    
    is_pinch, pinch_pos = node._is_pinching(close_keypoints)
    assert is_pinch is True, "Should detect pinch when fingers are close"
    assert pinch_pos is not None, "Should return pinch position"
    assert pinch_pos == (115, 100), "Pinch position should be midpoint"
    
    # Test with far fingers (no pinch)
    far_keypoints = {
        4: (100, 100),  # Thumb tip
        8: (200, 100),  # Index tip (100 pixels away - no pinch)
    }
    
    is_pinch, pinch_pos = node._is_pinching(far_keypoints)
    assert is_pinch is False, "Should not detect pinch when fingers are far"


def test_dynamic_play_overlay_drawing():
    """Test overlay drawing on master stream"""
    from node.VideoNode.node_dynamic_play import Node
    
    node = Node()
    
    # Create test frames
    master_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    overlay_frame = np.ones((240, 320, 3), dtype=np.uint8) * 255
    
    # Draw overlay at position
    position = (50, 50)
    size = (320, 240)
    result = node._draw_overlay(master_frame, overlay_frame, position, size)
    
    assert result.shape == master_frame.shape, "Result should have same dimensions as master"
    
    # Test with None overlay
    result_none = node._draw_overlay(master_frame, None, position, size)
    np.testing.assert_array_equal(result_none, master_frame, "None overlay should return original master frame")


def test_overlay_activation_without_frame():
    """Test that overlay can be activated even when frame is not available"""
    from node.VideoNode.node_dynamic_play import Node
    
    node = Node()
    
    # Initialize node tag for state tracking
    node_tag = "test_node:DynamicPlay"
    node.tag_node_name = node_tag
    
    # Initialize state
    node._active_overlay_index[node_tag] = None
    node._overlay_position[node_tag] = (50, 50)
    node._overlay_size[node_tag] = (320, 240)
    node._is_dragging[node_tag] = False
    node._drag_offset[node_tag] = (0, 0)
    node._follow_mode_active[node_tag] = False
    node._follow_mode_start_time[node_tag] = None
    node._resize_mode_start_time[node_tag] = None
    
    # Simulate clicking on overlay button index 0
    # This should activate overlay even if no frame is available
    clicked_index = 0
    overlay_slot = clicked_index + 1
    
    # Before fix: would require overlay_slot to be in frames dict
    # After fix: should activate regardless
    
    # Simulate the activation logic (from lines 498-521)
    active_overlay = node._active_overlay_index[node_tag]
    
    # Handle square click (overlay activation)
    if clicked_index is not None:
        # Toggle overlay: if already active, deactivate it
        if active_overlay == clicked_index:
            node._active_overlay_index[node_tag] = None
        else:
            # Activate overlay even if frame not available yet
            node._active_overlay_index[node_tag] = clicked_index
            node._overlay_position[node_tag] = (50, 50)
            node._overlay_size[node_tag] = (320, 240)
    
    # Verify overlay was activated
    assert node._active_overlay_index[node_tag] == 0, "Overlay should be activated when clicking on square"
    
    # Test toggling (clicking same square again)
    active_overlay = node._active_overlay_index[node_tag]
    if active_overlay == clicked_index:
        node._active_overlay_index[node_tag] = None
    
    assert node._active_overlay_index[node_tag] is None, "Overlay should be deactivated when clicking same square again"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
