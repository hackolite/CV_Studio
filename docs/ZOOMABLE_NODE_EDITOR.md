# Zoomable Node Editor Implementation

This document describes the custom zoomable node editor implementation for CV_Studio.

## Overview

The `ZoomableNodeEditor` class provides a complete custom node editor implementation using DearPyGui's low-level drawing primitives (`dpg.drawlist`). This implementation offers advanced zoom and pan capabilities beyond the built-in DearPyGui node editor.

## Features

### 1. **Smooth Mouse Wheel Zoom**
- **Range**: 0.1x to 5.0x
- **Zoom Center**: Always centered on cursor position (zoom "towards the cursor")
- **Formula**: Uses the exact formula specified:
  ```python
  zoom_ratio = self.zoom / old_zoom - 1
  self.offset_x -= mouse_pos[0] * zoom_ratio / self.zoom
  self.offset_y -= mouse_pos[1] * zoom_ratio / self.zoom
  ```

### 2. **Pan with Middle Mouse Button**
- Smooth drag with real-time updates
- Zoom compensation: `offset += mouse_delta / zoom`
- Natural feel regardless of zoom level

### 3. **Auto-Sized Nodes**
- **Width calculation** based on:
  - Label length (approximation: `char_width = font_size * 0.6`)
  - Number of ports
  - Minimum padding (20px)
- **Height calculation** based on:
  - Header height (30px)
  - Number of ports
  - Port spacing (25px)
- **Minimum width**: 150px

### 4. **Visual Rendering**
- Rounded rectangle nodes (rounding=5)
- Colored header separate from body
- Centered labels
- Input ports (left, green): 5px radius circles
- Output ports (right, red): 5px radius circles
- All elements scale with zoom

### 5. **Bezier Curve Connections**
- Cubic Bezier curves between ports
- Control point formula: `offset = abs(x2 - x1) * 0.5`
- Horizontal control points for natural appearance
- Line thickness scales with zoom

### 6. **Performance Optimizations**
- **Dirty Flag**: Only redraws when state changes (zoom, pan, add/remove nodes)
- **Viewport Culling**: Skips drawing nodes outside visible area
  ```python
  if x + width < 0 or x > viewport_width:
      skip
  ```
- **FPS Throttling**: Limits to 60 FPS maximum
- **Time-based redraw**: Prevents excessive rendering

### 7. **Static Background Grid**
- Grid lines spaced at 50px intervals
- Subtle color: (50, 50, 50, 100)
- **Grid does NOT zoom** - remains fixed regardless of zoom level
- Separate drawlist for grid vs. content

## Architecture

### Class Structure

```python
class ZoomableNodeEditor:
    def __init__(self, tag, width, height):
        # Zoom/pan state
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        
        # Node storage
        self.nodes = {}  # {id: {x, y, width, height, label, inputs, outputs}}
        self.connections = []  # [{from: (node_id, port), to: (node_id, port)}]
        
        # Performance
        self.dirty = False
        self.fps_limit = 60
```

### Key Methods

- **`create(parent)`**: Creates the UI within a parent window
- **`add_node(id, label, x, y, inputs, outputs)`**: Adds a node with auto-sizing
- **`add_connection(from_node, from_port, to_node, to_port)`**: Connects two nodes
- **`update()`**: Call in render loop to update display
- **`_on_wheel(sender, delta)`**: Handles zoom events
- **`_on_pan(sender, data)`**: Handles pan events
- **`_redraw()`**: Renders all nodes and connections (with culling)

### Coordinate Systems

The editor uses two coordinate systems:

1. **World Coordinates**: The logical position of nodes (independent of zoom/pan)
2. **Screen Coordinates**: The pixel position on screen after transformation

**Transformation Formula**:
```python
screen_x = (world_x + offset_x) * zoom
screen_y = (world_y + offset_y) * zoom
```

## Usage Example

```python
import dearpygui.dearpygui as dpg
from examples.zoomable_node_editor import ZoomableNodeEditor

dpg.create_context()

# Create editor
editor = ZoomableNodeEditor(tag="my_editor", width=1000, height=700)

# Create window
with dpg.window(label="Node Editor", width=1020, height=750):
    editor.create("main")

# Add nodes
editor.add_node("input", "CSV Input", 100, 100, inputs=0, outputs=2)
editor.add_node("process", "Transform", 350, 150, inputs=2, outputs=1)
editor.add_node("output", "Save", 600, 150, inputs=1, outputs=0)

# Add connections
editor.add_connection("input", 0, "process", 0)
editor.add_connection("process", 0, "output", 0)

# Setup viewport
dpg.create_viewport()
dpg.setup_dearpygui()
dpg.show_viewport()

# Render loop
while dpg.is_dearpygui_running():
    editor.update()  # Important: call this to trigger redraws
    dpg.render_dearpygui_frame()

dpg.destroy_context()
```

## Controls

- **Mouse Wheel**: Zoom in/out (centered on cursor)
- **Middle Mouse Button Drag**: Pan the view
- **Zoom Range**: 0.1x (10%) to 5.0x (500%)

## Implementation Details

### Zoom Formula Derivation

The zoom-towards-cursor feature uses this key insight:

```
World position under cursor should remain constant:
  world_pos = (screen_pos - offset * zoom_old) / zoom_old
  world_pos = (screen_pos - offset * zoom_new) / zoom_new

Solving for new offset:
  offset_new = offset_old + screen_pos * (1/zoom_new - 1/zoom_old)
```

### Culling Logic

Nodes are culled (not drawn) if they're completely outside the viewport:

```python
def _is_visible(x, y, width, height):
    if x + width < 0:  # Completely to the left
        return False
    if x > viewport_width:  # Completely to the right
        return False
    if y + height < 0:  # Completely above
        return False
    if y > viewport_height:  # Completely below
        return False
    return True
```

### Grid Implementation

The grid is drawn on a separate drawlist to avoid zoom scaling:

```python
with dpg.drawlist(tag=grid_drawlist_tag):
    # Draw fixed-size grid
    
with dpg.drawlist(tag=content_drawlist_tag):
    # Draw nodes (with zoom scaling)
```

## Differences from Built-in Node Editor

This custom implementation differs from DearPyGui's built-in `dpg.node_editor`:

| Feature | Built-in | Custom Zoomable |
|---------|----------|-----------------|
| Zoom | Basic mouse wheel | Cursor-centered zoom with precise formula |
| Pan | Click and drag | Middle mouse button with zoom compensation |
| Nodes | DPG node widgets | Custom-drawn with auto-sizing |
| Connections | DPG node links | Custom Bezier curves |
| Performance | Built-in optimization | Custom culling + dirty flag |
| Grid | Optional minimap | Static background grid |
| Customization | Limited | Full control via drawing |

## Testing

Run the test suite:

```bash
python tests/test_zoomable_node_editor.py
```

Run the demo:

```bash
python examples/zoomable_node_editor.py
```

## Integration with CV_Studio

This implementation is provided as a **standalone module** and **reference implementation**. 

The main CV_Studio node editor (`node_editor/node_main.py`) uses DearPyGui's built-in node editor with its native zoom functionality. This custom implementation can be used:

1. As a learning resource for understanding advanced zoom/pan mechanics
2. As a base for creating custom node editors with specific requirements
3. For projects that need pixel-perfect control over node rendering
4. When the built-in zoom behavior doesn't meet specific needs

## Future Enhancements

Potential improvements for future versions:

- [ ] Node selection and dragging
- [ ] Connection creation by dragging from ports
- [ ] Node deletion
- [ ] Save/load node graphs
- [ ] Custom node rendering callbacks
- [ ] Snap to grid
- [ ] Multi-selection
- [ ] Copy/paste nodes
- [ ] Undo/redo
- [ ] Zoom to fit
- [ ] Font scaling with zoom level

## License

Same as CV_Studio - see LICENSE file in the root directory.
