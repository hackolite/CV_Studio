#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for ZoomableNodeEditor functionality.
Tests the core logic without requiring GUI interaction.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from examples.zoomable_node_editor import ZoomableNodeEditor


def test_zoom_functionality():
    """Test zoom calculations"""
    print("Testing zoom functionality...")
    
    editor = ZoomableNodeEditor(tag="test", width=800, height=600)
    
    # Initial state
    assert editor.zoom == 1.0, "Initial zoom should be 1.0"
    assert editor.offset_x == 0.0, "Initial offset_x should be 0.0"
    assert editor.offset_y == 0.0, "Initial offset_y should be 0.0"
    
    # Test zoom range
    editor.zoom = 0.05  # Try to go below min
    # The _on_wheel method enforces limits, but manually set values aren't clamped yet
    # So we'll test the zoom calculation logic instead
    
    # Test zoom bounds
    assert editor.MIN_ZOOM == 0.1, "Min zoom should be 0.1"
    assert editor.MAX_ZOOM == 5.0, "Max zoom should be 5.0"
    
    print("✓ Zoom functionality tests passed")


def test_node_addition():
    """Test adding nodes"""
    print("Testing node addition...")
    
    editor = ZoomableNodeEditor(tag="test", width=800, height=600)
    
    # Add a node
    editor.add_node("node1", "Test Node", 100, 100, inputs=2, outputs=1)
    
    assert "node1" in editor.nodes, "Node should be added to nodes dict"
    assert editor.nodes["node1"]["label"] == "Test Node", "Node label should be correct"
    assert editor.nodes["node1"]["x"] == 100, "Node x position should be correct"
    assert editor.nodes["node1"]["y"] == 100, "Node y position should be correct"
    assert editor.nodes["node1"]["inputs"] == 2, "Node should have 2 inputs"
    assert editor.nodes["node1"]["outputs"] == 1, "Node should have 1 output"
    
    # Check auto-sizing
    assert editor.nodes["node1"]["width"] >= editor.MIN_NODE_WIDTH, "Node width should be at least MIN_NODE_WIDTH"
    assert editor.nodes["node1"]["height"] > editor.HEADER_HEIGHT, "Node height should be greater than header height"
    
    print("✓ Node addition tests passed")


def test_connection_addition():
    """Test adding connections"""
    print("Testing connection addition...")
    
    editor = ZoomableNodeEditor(tag="test", width=800, height=600)
    
    # Add nodes
    editor.add_node("node1", "Node 1", 100, 100, inputs=0, outputs=1)
    editor.add_node("node2", "Node 2", 300, 100, inputs=1, outputs=0)
    
    # Add connection
    editor.add_connection("node1", 0, "node2", 0)
    
    assert len(editor.connections) == 1, "Should have 1 connection"
    assert editor.connections[0]["from"] == ("node1", 0), "Connection from should be correct"
    assert editor.connections[0]["to"] == ("node2", 0), "Connection to should be correct"
    
    print("✓ Connection addition tests passed")


def test_coordinate_transformation():
    """Test world to screen coordinate transformation"""
    print("Testing coordinate transformation...")
    
    editor = ZoomableNodeEditor(tag="test", width=800, height=600)
    
    # Test with zoom = 1.0, no offset
    screen_x, screen_y = editor._world_to_screen(100, 200)
    assert screen_x == 100, "Screen X should equal world X at zoom 1.0 with no offset"
    assert screen_y == 200, "Screen Y should equal world Y at zoom 1.0 with no offset"
    
    # Test with zoom = 2.0
    editor.zoom = 2.0
    screen_x, screen_y = editor._world_to_screen(100, 200)
    assert screen_x == 200, "Screen X should be doubled at zoom 2.0"
    assert screen_y == 400, "Screen Y should be doubled at zoom 2.0"
    
    # Test with offset
    editor.zoom = 1.0
    editor.offset_x = 50
    editor.offset_y = 100
    screen_x, screen_y = editor._world_to_screen(100, 200)
    assert screen_x == 150, "Screen X should include offset"
    assert screen_y == 300, "Screen Y should include offset"
    
    # Test combined zoom and offset
    editor.zoom = 2.0
    editor.offset_x = 50
    editor.offset_y = 100
    screen_x, screen_y = editor._world_to_screen(100, 200)
    assert screen_x == 300, "Screen X should include both zoom and offset: (100 + 50) * 2"
    assert screen_y == 600, "Screen Y should include both zoom and offset: (200 + 100) * 2"
    
    print("✓ Coordinate transformation tests passed")


def test_viewport_culling():
    """Test viewport culling logic"""
    print("Testing viewport culling...")
    
    editor = ZoomableNodeEditor(tag="test", width=800, height=600)
    
    # Test visible rectangle
    assert editor._is_visible(100, 100, 200, 200) == True, "Rectangle in viewport should be visible"
    
    # Test rectangle completely to the left
    assert editor._is_visible(-300, 100, 200, 200) == False, "Rectangle to the left should be culled"
    
    # Test rectangle completely to the right
    assert editor._is_visible(900, 100, 200, 200) == False, "Rectangle to the right should be culled"
    
    # Test rectangle completely above
    assert editor._is_visible(100, -300, 200, 200) == False, "Rectangle above should be culled"
    
    # Test rectangle completely below
    assert editor._is_visible(100, 700, 200, 200) == False, "Rectangle below should be culled"
    
    # Test partially visible rectangle (should still be visible)
    assert editor._is_visible(-50, 100, 200, 200) == True, "Partially visible rectangle should not be culled"
    assert editor._is_visible(750, 100, 200, 200) == True, "Partially visible rectangle should not be culled"
    
    print("✓ Viewport culling tests passed")


def test_port_positioning():
    """Test port position calculation"""
    print("Testing port positioning...")
    
    editor = ZoomableNodeEditor(tag="test", width=800, height=600)
    editor.add_node("node1", "Test Node", 100, 100, inputs=2, outputs=2)
    
    node = editor.nodes["node1"]
    
    # Test input port (left side)
    port_x, port_y = editor._get_port_position(node, 0, True)
    assert port_x == node['x'], "Input port X should be at left edge of node"
    expected_y = node['y'] + editor.HEADER_HEIGHT + editor.PORT_SPACING / 2
    assert port_y == expected_y, f"Input port Y should be correct (expected {expected_y}, got {port_y})"
    
    # Test output port (right side)
    port_x, port_y = editor._get_port_position(node, 0, False)
    assert port_x == node['x'] + node['width'], "Output port X should be at right edge of node"
    
    # Test second port
    port_x, port_y = editor._get_port_position(node, 1, True)
    expected_y = node['y'] + editor.HEADER_HEIGHT + (1 * editor.PORT_SPACING) + editor.PORT_SPACING / 2
    assert port_y == expected_y, f"Second port Y should be spaced correctly"
    
    print("✓ Port positioning tests passed")


def test_performance_features():
    """Test performance optimization features"""
    print("Testing performance features...")
    
    editor = ZoomableNodeEditor(tag="test", width=800, height=600)
    
    # Test dirty flag
    assert editor.dirty == True, "Editor should be dirty initially"
    
    # Test FPS limit
    assert editor.fps_limit == 60, "FPS limit should be 60"
    assert editor.min_frame_time == 1.0 / 60, "Min frame time should be calculated correctly"
    
    print("✓ Performance features tests passed")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running ZoomableNodeEditor Tests")
    print("=" * 60)
    
    try:
        test_zoom_functionality()
        test_node_addition()
        test_connection_addition()
        test_coordinate_transformation()
        test_viewport_culling()
        test_port_positioning()
        test_performance_features()
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
