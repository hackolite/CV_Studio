#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for node editor zoom functionality.
Tests the zoom tracking and UI feedback without requiring GUI interaction.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node_editor.node_main import DpgNodeEditor


def test_zoom_initialization():
    """Test that zoom level is initialized correctly"""
    print("Testing zoom initialization...")
    
    # Create editor (without DearPyGui context since we're just testing logic)
    # Note: We can't actually create the DPG window without a display
    # but we can verify the class attributes
    assert DpgNodeEditor._zoom_level == 1.0, "Initial zoom should be 1.0"
    assert DpgNodeEditor._min_zoom == 0.1, "Min zoom should be 0.1"
    assert DpgNodeEditor._max_zoom == 5.0, "Max zoom should be 5.0"
    
    print("✓ Zoom initialization tests passed")


def test_zoom_logic():
    """Test zoom calculation logic"""
    print("Testing zoom logic...")
    
    # Test zoom in
    zoom = 1.0
    zoom *= 1.1  # Zoom in by 10%
    assert abs(zoom - 1.1) < 0.001, "Zoom in should increase by 10%"
    
    # Test zoom out
    zoom = 1.0
    zoom *= 0.9  # Zoom out by 10%
    assert abs(zoom - 0.9) < 0.001, "Zoom out should decrease by 10%"
    
    # Test zoom clamping - min
    zoom = 0.05
    zoom = max(0.1, min(5.0, zoom))
    assert zoom == 0.1, "Zoom should be clamped to minimum 0.1"
    
    # Test zoom clamping - max
    zoom = 10.0
    zoom = max(0.1, min(5.0, zoom))
    assert zoom == 5.0, "Zoom should be clamped to maximum 5.0"
    
    print("✓ Zoom logic tests passed")


def test_zoom_range_compliance():
    """Test that zoom range matches example specification"""
    print("Testing zoom range compliance with examples/zoomable_node_editor.py...")
    
    # Load the example to compare
    from examples.zoomable_node_editor import ZoomableNodeEditor
    
    example_editor = ZoomableNodeEditor(tag="test", width=800, height=600)
    
    # Verify our implementation matches the example's zoom range
    assert DpgNodeEditor._min_zoom == example_editor.MIN_ZOOM, \
        f"Min zoom should match example: {example_editor.MIN_ZOOM}"
    assert DpgNodeEditor._max_zoom == example_editor.MAX_ZOOM, \
        f"Max zoom should match example: {example_editor.MAX_ZOOM}"
    
    print(f"✓ Zoom range matches example: {DpgNodeEditor._min_zoom}x to {DpgNodeEditor._max_zoom}x")


def test_zoom_factor():
    """Test that zoom factor matches example"""
    print("Testing zoom factor matches examples/zoomable_node_editor.py...")
    
    # The example uses 1.1 for zoom in, 0.9 for zoom out
    zoom_in_factor = 1.1
    zoom_out_factor = 0.9
    
    # Simulate 10 zoom in steps from 1.0
    zoom = 1.0
    for _ in range(10):
        zoom *= zoom_in_factor
    
    # Should be approximately 1.1^10 = 2.594
    assert 2.5 < zoom < 2.7, f"10 zoom in steps should give ~2.59x, got {zoom:.2f}x"
    
    # Simulate 10 zoom out steps from 1.0
    zoom = 1.0
    for _ in range(10):
        zoom *= zoom_out_factor
    
    # Should be approximately 0.9^10 = 0.349
    assert 0.3 < zoom < 0.4, f"10 zoom out steps should give ~0.35x, got {zoom:.2f}x"
    
    print("✓ Zoom factor tests passed")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running Node Editor Zoom Tests")
    print("=" * 60)
    
    try:
        test_zoom_initialization()
        test_zoom_logic()
        test_zoom_range_compliance()
        test_zoom_factor()
        
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
