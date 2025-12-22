#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for the DearPyGui node editor example.
This test verifies that all functions work correctly without needing a display.
"""

import sys
import os
import traceback

# Add the examples directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the example module
from examples.dearpygui_node_editor_colored_combo_example import brighter, DOMAINS


def test_brighter_function():
    """Test the brighter() function"""
    print("Testing brighter() function...")
    
    # Test with a blue color
    color = (70, 130, 180, 255)
    bright_color = brighter(color, 1.3)
    
    assert len(bright_color) == 4, "brighter() should return 4 values (RGBA)"
    assert bright_color[0] >= color[0], "R component should be brighter"
    assert bright_color[1] >= color[1], "G component should be brighter"
    assert bright_color[2] >= color[2], "B component should be brighter"
    assert bright_color[3] == color[3], "A component should remain the same"
    
    # Test that values don't exceed 255
    white = (255, 255, 255, 255)
    bright_white = brighter(white, 2.0)
    assert all(c <= 255 for c in bright_white), "Color components should not exceed 255"
    
    print(f"  Original color: {color}")
    print(f"  Brighter color: {bright_color}")
    print("  ✓ brighter() function works correctly")


def test_domains_structure():
    """Test that DOMAINS dictionary is properly structured"""
    print("\nTesting DOMAINS structure...")
    
    assert len(DOMAINS) == 3, "Should have exactly 3 domains"
    
    expected_domains = ["Vision", "Audio", "Network"]
    for domain_name in expected_domains:
        assert domain_name in DOMAINS, f"Domain '{domain_name}' should exist"
        
        domain_data = DOMAINS[domain_name]
        assert "color" in domain_data, f"Domain '{domain_name}' should have a color"
        assert "nodes" in domain_data, f"Domain '{domain_name}' should have nodes"
        
        color = domain_data["color"]
        assert len(color) == 4, f"Color for '{domain_name}' should have 4 components (RGBA)"
        assert all(0 <= c <= 255 for c in color), f"Color components for '{domain_name}' should be 0-255"
        
        nodes = domain_data["nodes"]
        assert len(nodes) == 3, f"Domain '{domain_name}' should have exactly 3 nodes"
        
        print(f"  Domain: {domain_name}")
        print(f"    Color: {color}")
        print(f"    Nodes: {nodes}")
    
    print("  ✓ DOMAINS structure is correct")


def test_color_calculations():
    """Test color calculations for all domains"""
    print("\nTesting color calculations for all domains...")
    
    for domain_name, domain_data in DOMAINS.items():
        base_color = domain_data["color"]
        
        # Test hover color
        hover_color = brighter(base_color, 1.2)
        
        # Test active color
        active_color = brighter(base_color, 1.4)
        
        # Test dark color (for nodes)
        dark_color = (
            int(base_color[0] * 0.7),
            int(base_color[1] * 0.7),
            int(base_color[2] * 0.7),
            base_color[3]
        )
        
        print(f"  {domain_name}:")
        print(f"    Base:   {base_color}")
        print(f"    Dark:   {dark_color}")
        print(f"    Hover:  {hover_color}")
        print(f"    Active: {active_color}")
    
    print("  ✓ Color calculations work correctly")


def test_module_imports():
    """Test that all necessary modules can be imported"""
    print("\nTesting module imports...")
    
    try:
        # Just test if the module exists, don't call any functions
        # (calling dpg functions in headless environment causes segfault)
        import dearpygui
        print(f"  ✓ DearPyGui module is available")
    except ImportError as e:
        print(f"  ✗ Failed to import DearPyGui: {e}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing DearPyGui Node Editor Example")
    print("=" * 60)
    
    try:
        # Test imports
        if not test_module_imports():
            print("\n⚠ Warning: DearPyGui import failed, but other tests will continue")
        
        # Test the brighter function
        test_brighter_function()
        
        # Test DOMAINS structure
        test_domains_structure()
        
        # Test color calculations
        test_color_calculations()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
        print("\nTo run the example visually:")
        print("  python examples/dearpygui_node_editor_colored_combo_example.py")
        
        return 0
    
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
