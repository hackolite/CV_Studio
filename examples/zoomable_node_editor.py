#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Zoomable Node Editor with Zoom and Pan for DearPyGui

A complete Node Editor implementation in Python with DearPyGui featuring:
- Smooth mouse wheel zoom (0.1x to 5.0x range)
- Zoom centered on cursor position
- Pan with middle mouse button drag
- Auto-sized nodes
- Bezier curve connections
- Performance optimizations (dirty flag, culling, throttling)
- Background grid that doesn't zoom

This is a standalone implementation demonstrating advanced node editor concepts
that can be integrated or used as a reference for custom node editor needs.
"""

import dearpygui.dearpygui as dpg
from typing import Dict, List, Tuple, Optional
import time


class ZoomableNodeEditor:
    """
    A custom node editor with advanced zoom and pan capabilities.
    
    Features:
    - Mouse wheel zoom centered on cursor
    - Middle mouse button pan
    - Auto-sized nodes with ports
    - Bezier curve connections
    - Performance optimizations (dirty flag, culling)
    - Static background grid
    """
    
    def __init__(self, tag: str = "editor", width: int = 800, height: int = 600):
        """
        Initialize the zoomable node editor.
        
        Args:
            tag: Unique tag for the editor
            width: Viewport width in pixels
            height: Viewport height in pixels
        """
        self.tag = tag
        self.width = width
        self.height = height
        
        # Zoom and pan state
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        
        # Node storage
        self.nodes: Dict[str, dict] = {}  # {id: {x, y, width, height, label, inputs, outputs}}
        self.connections: List[dict] = []  # [{from: (node_id, port), to: (node_id, port)}]
        
        # Performance optimization
        self.dirty = True
        self.last_draw_time = 0
        self.fps_limit = 60  # Max 60 FPS
        self.min_frame_time = 1.0 / self.fps_limit
        
        # Pan state
        self.is_panning = False
        self.last_mouse_pos = None
        
        # Drawing tags
        self.drawlist_tag = f"{tag}_drawlist"
        self.grid_drawlist_tag = f"{tag}_grid_drawlist"
        
        # Constants
        self.MIN_ZOOM = 0.1
        self.MAX_ZOOM = 5.0
        self.GRID_SIZE = 50
        self.GRID_COLOR = (50, 50, 50, 100)
        self.NODE_ROUNDING = 5
        self.HEADER_HEIGHT = 30
        self.PORT_RADIUS = 5
        self.PORT_SPACING = 25
        self.MIN_NODE_WIDTH = 150
        self.PADDING = 20
        self.CHAR_WIDTH_RATIO = 0.6  # Character width as ratio of font size
        self.FONT_SIZE = 15  # Default font size
        
        # Colors
        self.COLOR_NODE_HEADER = (100, 100, 200, 255)
        self.COLOR_NODE_BODY = (70, 70, 70, 255)
        self.COLOR_PORT_INPUT = (0, 255, 0, 255)  # Green
        self.COLOR_PORT_OUTPUT = (255, 0, 0, 255)  # Red
        self.COLOR_CONNECTION = (200, 200, 200, 255)
        self.COLOR_TEXT = (255, 255, 255, 255)
    
    def create(self, parent: str):
        """
        Create the node editor UI within a parent window.
        
        Args:
            parent: Tag of the parent window
        """
        with dpg.drawlist(width=self.width, height=self.height, tag=self.grid_drawlist_tag, parent=parent):
            # Grid will be drawn here (static, doesn't zoom)
            self._draw_grid()
        
        with dpg.drawlist(width=self.width, height=self.height, tag=self.drawlist_tag, parent=parent):
            # Nodes and connections will be drawn here
            pass
        
        # Set up event handlers
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self._on_wheel)
            dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Middle, callback=self._on_pan)
    
    def add_node(self, node_id: str, label: str, x: float, y: float, 
                 inputs: int = 0, outputs: int = 0):
        """
        Add a node to the editor with auto-calculated size.
        
        Args:
            node_id: Unique identifier for the node
            label: Display label for the node
            x: X position in world coordinates
            y: Y position in world coordinates
            inputs: Number of input ports
            outputs: Number of output ports
        """
        # Calculate node width based on label length
        label_width = len(label) * self.FONT_SIZE * self.CHAR_WIDTH_RATIO
        ports_width = max(inputs, outputs) * 30  # Rough estimate for port spacing
        width = max(self.MIN_NODE_WIDTH, label_width + self.PADDING * 2, ports_width)
        
        # Calculate node height based on ports
        max_ports = max(inputs, outputs)
        height = self.HEADER_HEIGHT + (max_ports * self.PORT_SPACING) + self.PADDING
        
        self.nodes[node_id] = {
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'label': label,
            'inputs': inputs,
            'outputs': outputs
        }
        
        self.dirty = True
    
    def add_connection(self, from_node: str, from_port: int, to_node: str, to_port: int):
        """
        Add a connection between two nodes.
        
        Args:
            from_node: Source node ID
            from_port: Source port index
            to_node: Destination node ID
            to_port: Destination port index
        """
        self.connections.append({
            'from': (from_node, from_port),
            'to': (to_node, to_port)
        })
        
        self.dirty = True
    
    def _on_wheel(self, sender, delta):
        """
        Handle mouse wheel zoom events.
        Implements zoom centered on cursor position.
        
        Args:
            sender: DPG sender
            delta: Mouse wheel delta (positive = zoom in, negative = zoom out)
        """
        # Get mouse position in viewport coordinates
        mouse_pos = dpg.get_mouse_pos(local=False)
        
        # Store old zoom level
        old_zoom = self.zoom
        
        # Calculate new zoom level
        zoom_factor = 1.1 if delta > 0 else 0.9
        self.zoom *= zoom_factor
        
        # Clamp zoom to valid range
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom))
        
        # Adjust offset to keep point under cursor fixed
        # Formula: new_pos = (original_pos + offset) * zoom
        # We want the world position under the mouse to stay the same
        zoom_ratio = self.zoom / old_zoom - 1
        self.offset_x -= mouse_pos[0] * zoom_ratio / self.zoom
        self.offset_y -= mouse_pos[1] * zoom_ratio / self.zoom
        
        self.dirty = True
    
    def _on_pan(self, sender, data):
        """
        Handle middle mouse button pan events.
        Implements smooth panning with zoom compensation.
        
        Args:
            sender: DPG sender
            data: Mouse drag data
        """
        # Get mouse delta
        if self.last_mouse_pos is None:
            self.last_mouse_pos = dpg.get_mouse_pos(local=False)
            return
        
        current_mouse_pos = dpg.get_mouse_pos(local=False)
        delta_x = current_mouse_pos[0] - self.last_mouse_pos[0]
        delta_y = current_mouse_pos[1] - self.last_mouse_pos[1]
        
        # Update offset with zoom compensation
        # Formula: offset += mouse_delta / zoom
        self.offset_x += delta_x / self.zoom
        self.offset_y += delta_y / self.zoom
        
        self.last_mouse_pos = current_mouse_pos
        self.dirty = True
        
        # Reset on mouse release
        if not dpg.is_mouse_button_down(dpg.mvMouseButton_Middle):
            self.last_mouse_pos = None
    
    def _world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            x: World X coordinate
            y: World Y coordinate
            
        Returns:
            Tuple of (screen_x, screen_y)
        """
        screen_x = (x + self.offset_x) * self.zoom
        screen_y = (y + self.offset_y) * self.zoom
        return screen_x, screen_y
    
    def _is_visible(self, x: float, y: float, width: float, height: float) -> bool:
        """
        Check if a rectangle is visible in the viewport (culling).
        
        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            width: Screen width
            height: Screen height
            
        Returns:
            True if visible, False if culled
        """
        if x + width < 0 or x > self.width:
            return False
        if y + height < 0 or y > self.height:
            return False
        return True
    
    def _draw_grid(self):
        """
        Draw the background grid (static, doesn't zoom).
        """
        dpg.delete_item(self.grid_drawlist_tag, children_only=True)
        
        # Draw vertical lines
        for x in range(0, self.width, self.GRID_SIZE):
            dpg.draw_line(
                (x, 0), (x, self.height),
                color=self.GRID_COLOR,
                thickness=1,
                parent=self.grid_drawlist_tag
            )
        
        # Draw horizontal lines
        for y in range(0, self.height, self.GRID_SIZE):
            dpg.draw_line(
                (0, y), (self.width, y),
                color=self.GRID_COLOR,
                thickness=1,
                parent=self.grid_drawlist_tag
            )
    
    def _get_port_position(self, node: dict, port_index: int, is_input: bool) -> Tuple[float, float]:
        """
        Calculate the position of a port on a node.
        
        Args:
            node: Node dictionary
            port_index: Index of the port
            is_input: True for input port, False for output port
            
        Returns:
            Tuple of (x, y) in world coordinates
        """
        x = node['x']
        y = node['y'] + self.HEADER_HEIGHT + (port_index * self.PORT_SPACING) + self.PORT_SPACING / 2
        
        if is_input:
            # Input ports on the left
            x = node['x']
        else:
            # Output ports on the right
            x = node['x'] + node['width']
        
        return x, y
    
    def _draw_bezier_connection(self, x1: float, y1: float, x2: float, y2: float):
        """
        Draw a Bezier curve connection between two points.
        
        Args:
            x1: Start X coordinate (screen)
            y1: Start Y coordinate (screen)
            x2: End X coordinate (screen)
            y2: End Y coordinate (screen)
        """
        # Calculate control points for horizontal bezier curve
        offset = abs(x2 - x1) * 0.5
        
        # Control points
        cp1_x = x1 + offset
        cp1_y = y1
        cp2_x = x2 - offset
        cp2_y = y2
        
        # Draw the bezier curve
        thickness = max(1, 2 * self.zoom)  # Scale thickness with zoom
        dpg.draw_bezier_cubic(
            (x1, y1), (cp1_x, cp1_y), (cp2_x, cp2_y), (x2, y2),
            color=self.COLOR_CONNECTION,
            thickness=thickness,
            parent=self.drawlist_tag
        )
    
    def _redraw(self):
        """
        Redraw all nodes and connections.
        Implements culling and dirty flag optimization.
        """
        # Throttle to max FPS
        current_time = time.time()
        if current_time - self.last_draw_time < self.min_frame_time and not self.dirty:
            return
        
        if not self.dirty:
            return
        
        self.last_draw_time = current_time
        self.dirty = False
        
        # Clear the drawlist
        dpg.delete_item(self.drawlist_tag, children_only=True)
        
        # Draw connections first (behind nodes)
        for connection in self.connections:
            from_node_id, from_port = connection['from']
            to_node_id, to_port = connection['to']
            
            if from_node_id not in self.nodes or to_node_id not in self.nodes:
                continue
            
            from_node = self.nodes[from_node_id]
            to_node = self.nodes[to_node_id]
            
            # Get port positions in world coordinates
            from_x, from_y = self._get_port_position(from_node, from_port, False)
            to_x, to_y = self._get_port_position(to_node, to_port, True)
            
            # Convert to screen coordinates
            from_screen_x, from_screen_y = self._world_to_screen(from_x, from_y)
            to_screen_x, to_screen_y = self._world_to_screen(to_x, to_y)
            
            # Draw connection
            self._draw_bezier_connection(from_screen_x, from_screen_y, to_screen_x, to_screen_y)
        
        # Draw nodes
        for node_id, node in self.nodes.items():
            # Transform to screen coordinates
            screen_x, screen_y = self._world_to_screen(node['x'], node['y'])
            screen_width = node['width'] * self.zoom
            screen_height = node['height'] * self.zoom
            
            # Viewport culling
            if not self._is_visible(screen_x, screen_y, screen_width, screen_height):
                continue
            
            # Draw node body
            dpg.draw_rectangle(
                (screen_x, screen_y + self.HEADER_HEIGHT * self.zoom),
                (screen_x + screen_width, screen_y + screen_height),
                color=self.COLOR_NODE_BODY,
                fill=self.COLOR_NODE_BODY,
                rounding=self.NODE_ROUNDING,
                parent=self.drawlist_tag
            )
            
            # Draw node header
            dpg.draw_rectangle(
                (screen_x, screen_y),
                (screen_x + screen_width, screen_y + self.HEADER_HEIGHT * self.zoom),
                color=self.COLOR_NODE_HEADER,
                fill=self.COLOR_NODE_HEADER,
                rounding=self.NODE_ROUNDING,
                parent=self.drawlist_tag
            )
            
            # Draw label (centered in header)
            # Note: Text doesn't scale with zoom in this basic implementation
            # For production, you'd want to use different font sizes based on zoom
            label_x = screen_x + screen_width / 2
            label_y = screen_y + (self.HEADER_HEIGHT * self.zoom) / 2
            dpg.draw_text(
                (label_x, label_y),
                node['label'],
                color=self.COLOR_TEXT,
                size=max(10, self.FONT_SIZE * self.zoom),
                parent=self.drawlist_tag
            )
            
            # Draw input ports
            for i in range(node['inputs']):
                port_x, port_y = self._get_port_position(node, i, True)
                screen_port_x, screen_port_y = self._world_to_screen(port_x, port_y)
                radius = self.PORT_RADIUS * self.zoom
                
                dpg.draw_circle(
                    (screen_port_x, screen_port_y),
                    radius,
                    color=self.COLOR_PORT_INPUT,
                    fill=self.COLOR_PORT_INPUT,
                    parent=self.drawlist_tag
                )
            
            # Draw output ports
            for i in range(node['outputs']):
                port_x, port_y = self._get_port_position(node, i, False)
                screen_port_x, screen_port_y = self._world_to_screen(port_x, port_y)
                radius = self.PORT_RADIUS * self.zoom
                
                dpg.draw_circle(
                    (screen_port_x, screen_port_y),
                    radius,
                    color=self.COLOR_PORT_OUTPUT,
                    fill=self.COLOR_PORT_OUTPUT,
                    parent=self.drawlist_tag
                )
    
    def update(self):
        """
        Update the editor. Call this in your render loop.
        """
        self._redraw()


def demo():
    """
    Demonstration of the ZoomableNodeEditor.
    """
    dpg.create_context()
    
    # Create the editor
    editor = ZoomableNodeEditor(tag="demo_editor", width=1000, height=700)
    
    # Create main window
    with dpg.window(label="Zoomable Node Editor Demo", width=1020, height=750, tag="main"):
        # Add instructions
        dpg.add_text("Controls:")
        dpg.add_text("  - Mouse Wheel: Zoom in/out (centered on cursor)")
        dpg.add_text("  - Middle Mouse Button: Pan/drag the view")
        dpg.add_text("  - Zoom Range: 0.1x to 5.0x")
        dpg.add_separator()
        
        # Create the editor
        editor.create("main")
    
    # Add some demo nodes
    editor.add_node("input", "CSV Input", 100, 100, inputs=0, outputs=2)
    editor.add_node("process", "Data Transform", 350, 150, inputs=2, outputs=1)
    editor.add_node("output", "Save File", 600, 150, inputs=1, outputs=0)
    editor.add_node("filter", "Filter Data", 350, 300, inputs=1, outputs=1)
    
    # Add connections
    editor.add_connection("input", 0, "process", 0)
    editor.add_connection("input", 1, "filter", 0)
    editor.add_connection("process", 0, "output", 0)
    
    # Setup and run
    dpg.create_viewport(title="Zoomable Node Editor", width=1050, height=800)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main", True)
    
    # Main loop
    while dpg.is_dearpygui_running():
        editor.update()
        dpg.render_dearpygui_frame()
    
    dpg.destroy_context()


if __name__ == "__main__":
    demo()
