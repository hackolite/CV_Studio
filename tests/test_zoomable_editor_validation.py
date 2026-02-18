#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Non-GUI validation test for ZoomableNodeEditor.
This test validates that the module can be imported and initialized
without requiring actual GUI interaction.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import():
    """Test that the module can be imported"""
    print("Testing module import...")
    try:
        from examples.zoomable_node_editor import ZoomableNodeEditor
        print("✓ Module imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import module: {e}")
        return False


def test_initialization():
    """Test that the editor can be initialized"""
    print("Testing editor initialization...")
    try:
        from examples.zoomable_node_editor import ZoomableNodeEditor
        editor = ZoomableNodeEditor(tag="test", width=800, height=600)
        print("✓ Editor initialized successfully")
        
        # Verify initial state
        assert editor.zoom == 1.0, "Initial zoom should be 1.0"
        assert editor.offset_x == 0.0, "Initial offset_x should be 0.0"
        assert editor.offset_y == 0.0, "Initial offset_y should be 0.0"
        assert len(editor.nodes) == 0, "Initial nodes should be empty"
        assert len(editor.connections) == 0, "Initial connections should be empty"
        print("✓ Initial state verified")
        
        return True
    except Exception as e:
        print(f"✗ Failed to initialize editor: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_operations():
    """Test basic node operations"""
    print("Testing node operations...")
    try:
        from examples.zoomable_node_editor import ZoomableNodeEditor
        editor = ZoomableNodeEditor(tag="test", width=800, height=600)
        
        # Add nodes
        editor.add_node("n1", "Node 1", 100, 100, inputs=2, outputs=1)
        editor.add_node("n2", "Node 2", 300, 100, inputs=1, outputs=2)
        
        assert len(editor.nodes) == 2, "Should have 2 nodes"
        print("✓ Nodes added successfully")
        
        # Add connection
        editor.add_connection("n1", 0, "n2", 0)
        
        assert len(editor.connections) == 1, "Should have 1 connection"
        print("✓ Connection added successfully")
        
        return True
    except Exception as e:
        print(f"✗ Node operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coordinate_math():
    """Test coordinate transformation math"""
    print("Testing coordinate transformations...")
    try:
        from examples.zoomable_node_editor import ZoomableNodeEditor
        editor = ZoomableNodeEditor(tag="test", width=800, height=600)
        
        # Test basic transformation
        x, y = editor._world_to_screen(100, 200)
        assert x == 100 and y == 200, "Basic transformation should work"
        
        # Test with zoom
        editor.zoom = 2.0
        x, y = editor._world_to_screen(100, 200)
        assert x == 200 and y == 400, "Zoom transformation should work"
        
        # Test with offset
        editor.zoom = 1.0
        editor.offset_x = 50
        editor.offset_y = 100
        x, y = editor._world_to_screen(100, 200)
        assert x == 150 and y == 300, "Offset transformation should work"
        
        print("✓ Coordinate transformations working correctly")
        return True
    except Exception as e:
        print(f"✗ Coordinate math failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests"""
    print("=" * 60)
    print("ZoomableNodeEditor Validation (Non-GUI)")
    print("=" * 60)
    
    tests = [
        test_import,
        test_initialization,
        test_node_operations,
        test_coordinate_math,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=" * 60)
    if all(results):
        print("✓ All validation tests passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some validation tests failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
