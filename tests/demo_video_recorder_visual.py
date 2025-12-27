#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual test for VideoRecorder node
This script creates a simple node editor with the VideoRecorder node to verify it displays correctly
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
import dearpygui.dearpygui as dpg

from node.ActionNode.node_video_recorder import FactoryNode

def test_video_recorder_visual():
    """Visual test to verify the VideoRecorder node UI"""
    
    opencv_setting_dict = {
        'process_width': 240,
        'process_height': 135,
        'video_writer_fps': 30,
        'video_writer_directory': './_VideoRecorder'
    }
    
    dpg.create_context()
    
    with dpg.window(label="VideoRecorder Node Visual Test", width=800, height=600, tag="main_window"):
        dpg.add_text("VideoRecorder Node Test")
        dpg.add_text("The node should display with:")
        dpg.add_text("  - Trigger JSON input")
        dpg.add_text("  - Image input (with preview)")
        dpg.add_text("  - Metadata JSON input")
        dpg.add_text("  - Format dropdown (avi, mp4, mkv)")
        dpg.add_text("  - Duration slider (1-300 seconds)")
        dpg.add_text("  - Status button (gray 'WAIT')")
        dpg.add_separator()
        
        with dpg.node_editor(label="Node Editor", tag="node_editor"):
            factory = FactoryNode()
            node = factory.add_node(
                parent=dpg.last_item(), 
                node_id=1, 
                pos=[100, 200],
                opencv_setting_dict=opencv_setting_dict
            )
            
            print(f"✓ Node created: {node.node_label}")
            print(f"  Tag: {node.tag_node_name}")
    
    dpg.create_viewport(title='VideoRecorder Node Visual Test', width=900, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    print("\n=== Visual Test Running ===")
    print("Please verify the VideoRecorder node displays correctly.")
    print("Press ESC or close the window to exit.")
    print("============================\n")
    
    dpg.set_primary_window("main_window", True)
    dpg.start_dearpygui()
    dpg.destroy_context()
    
    print("\n✓ Visual test completed")

if __name__ == '__main__':
    test_video_recorder_visual()
