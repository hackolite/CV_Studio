#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo script to test node editor zoom functionality.
This script creates a minimal node editor window to verify zoom works.
Run this and use the mouse wheel to zoom in and out.
"""

import sys
import os
import dearpygui.dearpygui as dpg

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node_editor.node_editor import DpgNodeEditor


def main():
    """Create a minimal node editor to test zoom"""
    
    # Create DearPyGUI context
    dpg.create_context()
    
    # Create node editor
    node_editor = DpgNodeEditor(
        width=1024,
        height=768,
        pos=[0, 0],
        use_debug_print=True  # Enable debug output to see zoom level
    )
    
    # Setup viewport
    dpg.create_viewport(
        title="CV Studio - Zoom Test",
        width=1024,
        height=768
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    # Add test instructions
    with dpg.window(label="Instructions", pos=[10, 30], width=400, height=150):
        dpg.add_text("Mouse Wheel Zoom Test")
        dpg.add_separator()
        dpg.add_text("• Scroll UP (away from you) to ZOOM IN")
        dpg.add_text("• Scroll DOWN (toward you) to ZOOM OUT")
        dpg.add_text("• Zoom range: 0.25x (25%) to 3.0x (300%)")
        dpg.add_separator()
        dpg.add_text("Watch the console for zoom level debug output.")
        dpg.add_text(f"Current zoom: {node_editor._zoom_level:.2f}x", tag="zoom_display")
    
    # Update loop to show current zoom level
    def update_zoom_display():
        dpg.set_value("zoom_display", f"Current zoom: {node_editor._zoom_level:.2f}x")
    
    # Set frame callback to update display
    dpg.set_frame_callback(1, update_zoom_display)
    
    print("\n" + "="*60)
    print("CV Studio - Node Editor Zoom Test")
    print("="*60)
    print("Instructions:")
    print("  • Use mouse wheel to zoom in/out")
    print("  • Zoom range: 0.25x to 3.0x")
    print("  • Watch for 'Zoom level: X.XX' messages in console")
    print("="*60 + "\n")
    
    # Start DearPyGUI
    dpg.start_dearpygui()
    
    # Cleanup
    dpg.destroy_context()


if __name__ == "__main__":
    main()
