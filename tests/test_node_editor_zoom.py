#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Node Editor Zoom functionality"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_zoom_level_initialization():
    """Test that zoom level is properly initialized"""
    try:
        import dearpygui.dearpygui as dpg
        from node_editor.node_editor import DpgNodeEditor
        
        # Create context
        dpg.create_context()
        
        # Create node editor
        editor = DpgNodeEditor(
            width=800,
            height=600,
            pos=[0, 0],
            use_debug_print=False
        )
        
        # Check zoom level is initialized
        assert hasattr(editor, '_zoom_level'), "Editor should have _zoom_level attribute"
        assert hasattr(editor, '_min_zoom'), "Editor should have _min_zoom attribute"
        assert hasattr(editor, '_max_zoom'), "Editor should have _max_zoom attribute"
        assert hasattr(editor, '_zoom_speed'), "Editor should have _zoom_speed attribute"
        
        # Check initial values
        assert editor._zoom_level == 1.0, "Initial zoom level should be 1.0"
        assert editor._min_zoom == 0.25, "Minimum zoom should be 0.25"
        assert editor._max_zoom == 3.0, "Maximum zoom should be 3.0"
        assert editor._zoom_speed == 0.1, "Zoom speed should be 0.1"
        
        # Cleanup
        dpg.destroy_context()
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_zoom_callback_exists():
    """Test that zoom callback method exists"""
    try:
        import dearpygui.dearpygui as dpg
        from node_editor.node_editor import DpgNodeEditor
        
        # Create context
        dpg.create_context()
        
        # Create node editor
        editor = DpgNodeEditor(
            width=800,
            height=600,
            pos=[0, 0],
            use_debug_print=False
        )
        
        # Check callback method exists
        assert hasattr(editor, '_callback_mouse_wheel'), "Editor should have _callback_mouse_wheel method"
        assert callable(editor._callback_mouse_wheel), "_callback_mouse_wheel should be callable"
        
        # Cleanup
        dpg.destroy_context()
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_zoom_in():
    """Test zoom in functionality"""
    try:
        import dearpygui.dearpygui as dpg
        from node_editor.node_editor import DpgNodeEditor
        
        # Create context
        dpg.create_context()
        
        # Create node editor
        editor = DpgNodeEditor(
            width=800,
            height=600,
            pos=[0, 0],
            use_debug_print=False
        )
        
        initial_zoom = editor._zoom_level
        
        # Simulate mouse wheel scroll up (zoom in)
        # Positive value = scroll up
        editor._callback_mouse_wheel(None, 1)
        
        # Check zoom level increased
        assert editor._zoom_level > initial_zoom, "Zoom level should increase when scrolling up"
        expected_zoom = initial_zoom + editor._zoom_speed
        assert editor._zoom_level == expected_zoom, f"Zoom level should be {expected_zoom}, got {editor._zoom_level}"
        
        # Cleanup
        dpg.destroy_context()
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_zoom_out():
    """Test zoom out functionality"""
    try:
        import dearpygui.dearpygui as dpg
        from node_editor.node_editor import DpgNodeEditor
        
        # Create context
        dpg.create_context()
        
        # Create node editor
        editor = DpgNodeEditor(
            width=800,
            height=600,
            pos=[0, 0],
            use_debug_print=False
        )
        
        initial_zoom = editor._zoom_level
        
        # Simulate mouse wheel scroll down (zoom out)
        # Negative value = scroll down
        editor._callback_mouse_wheel(None, -1)
        
        # Check zoom level decreased
        assert editor._zoom_level < initial_zoom, "Zoom level should decrease when scrolling down"
        expected_zoom = initial_zoom - editor._zoom_speed
        assert editor._zoom_level == expected_zoom, f"Zoom level should be {expected_zoom}, got {editor._zoom_level}"
        
        # Cleanup
        dpg.destroy_context()
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_zoom_min_constraint():
    """Test that zoom level respects minimum constraint"""
    try:
        import dearpygui.dearpygui as dpg
        from node_editor.node_editor import DpgNodeEditor
        
        # Create context
        dpg.create_context()
        
        # Create node editor
        editor = DpgNodeEditor(
            width=800,
            height=600,
            pos=[0, 0],
            use_debug_print=False
        )
        
        # Calculate how many scroll events needed to reach minimum
        # Add extra scrolls to ensure we exceed the limit
        scrolls_needed = int((editor._zoom_level - editor._min_zoom) / editor._zoom_speed) + 5
        
        # Try to zoom out beyond minimum
        for _ in range(scrolls_needed):
            editor._callback_mouse_wheel(None, -1)
        
        # Check zoom level is clamped to minimum
        assert editor._zoom_level >= editor._min_zoom, "Zoom level should not go below minimum"
        assert editor._zoom_level == editor._min_zoom, f"Zoom level should be {editor._min_zoom}, got {editor._zoom_level}"
        
        # Cleanup
        dpg.destroy_context()
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_zoom_max_constraint():
    """Test that zoom level respects maximum constraint"""
    try:
        import dearpygui.dearpygui as dpg
        from node_editor.node_editor import DpgNodeEditor
        
        # Create context
        dpg.create_context()
        
        # Create node editor
        editor = DpgNodeEditor(
            width=800,
            height=600,
            pos=[0, 0],
            use_debug_print=False
        )
        
        # Calculate how many scroll events needed to reach maximum
        # Add extra scrolls to ensure we exceed the limit
        scrolls_needed = int((editor._max_zoom - editor._zoom_level) / editor._zoom_speed) + 5
        
        # Try to zoom in beyond maximum
        for _ in range(scrolls_needed):
            editor._callback_mouse_wheel(None, 1)
        
        # Check zoom level is clamped to maximum
        assert editor._zoom_level <= editor._max_zoom, "Zoom level should not go above maximum"
        assert editor._zoom_level == editor._max_zoom, f"Zoom level should be {editor._max_zoom}, got {editor._zoom_level}"
        
        # Cleanup
        dpg.destroy_context()
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


def test_zoom_speed():
    """Test zoom speed is correct"""
    try:
        import dearpygui.dearpygui as dpg
        from node_editor.node_editor import DpgNodeEditor
        
        # Create context
        dpg.create_context()
        
        # Create node editor
        editor = DpgNodeEditor(
            width=800,
            height=600,
            pos=[0, 0],
            use_debug_print=False
        )
        
        initial_zoom = editor._zoom_level
        
        # Simulate multiple scroll events
        editor._callback_mouse_wheel(None, 5)  # Scroll up 5 units
        
        # Check zoom level changed by expected amount (5 * zoom_speed)
        expected_zoom = min(initial_zoom + (5 * editor._zoom_speed), editor._max_zoom)
        assert editor._zoom_level == expected_zoom, f"Zoom level should be {expected_zoom}, got {editor._zoom_level}"
        
        # Cleanup
        dpg.destroy_context()
        
    except ImportError as e:
        pytest.skip(f"Could not import required modules: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
