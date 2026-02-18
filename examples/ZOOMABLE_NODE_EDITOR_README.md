# Zoomable Node Editor Example

This example demonstrates a custom node editor implementation with advanced zoom and pan capabilities.

## Overview

The `zoomable_node_editor.py` module provides a complete custom implementation of a node editor using DearPyGui's low-level drawing primitives. Unlike the built-in `dpg.node_editor`, this implementation offers precise control over zoom behavior, rendering, and performance.

## Features

✨ **Smooth Zoom** - Mouse wheel zoom that centers on cursor position (0.1x to 5.0x range)

🖱️ **Pan Support** - Middle mouse button drag to pan the view

📦 **Auto-Sized Nodes** - Nodes automatically size based on content

🔗 **Bezier Connections** - Smooth cubic Bezier curves between node ports

⚡ **Performance Optimized** - Viewport culling, dirty flags, and FPS throttling

📐 **Static Grid** - Background grid that remains fixed while zooming

## Running the Demo

```bash
# Ensure dependencies are installed
pip install dearpygui>=2.0.0

# Run the demo
python examples/zoomable_node_editor.py
```

## Controls

- **Mouse Wheel** - Zoom in/out (centered on cursor)
- **Middle Mouse Button + Drag** - Pan the view
- **Zoom Range** - 0.1x (10%) to 5.0x (500%)

## Usage in Your Code

```python
from examples.zoomable_node_editor import ZoomableNodeEditor
import dearpygui.dearpygui as dpg

# Create context and editor
dpg.create_context()
editor = ZoomableNodeEditor(tag="my_editor", width=1000, height=700)

# Create window and add editor
with dpg.window(label="My Node Editor", width=1020, height=750):
    editor.create("main")

# Add nodes
editor.add_node("input", "Data Input", 100, 100, inputs=0, outputs=2)
editor.add_node("process", "Process", 350, 150, inputs=2, outputs=1)
editor.add_node("output", "Output", 600, 150, inputs=1, outputs=0)

# Connect nodes
editor.add_connection("input", 0, "process", 0)
editor.add_connection("process", 0, "output", 0)

# Setup and run
dpg.create_viewport(title="Node Editor", width=1050, height=800)
dpg.setup_dearpygui()
dpg.show_viewport()

# Main loop - important to call editor.update()!
while dpg.is_dearpygui_running():
    editor.update()  # This triggers redrawing
    dpg.render_dearpygui_frame()

dpg.destroy_context()
```

## Implementation Details

### Zoom Formula

The zoom-towards-cursor behavior uses this mathematical approach:

```python
# Mouse position in viewport
mouse_pos = dpg.get_mouse_pos(local=False)

# Calculate new zoom
old_zoom = self.zoom
self.zoom *= (1.1 if delta > 0 else 0.9)
self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom))

# Adjust offset to keep cursor position fixed
zoom_ratio = self.zoom / old_zoom - 1
self.offset_x -= mouse_pos[0] * zoom_ratio / self.zoom
self.offset_y -= mouse_pos[1] * zoom_ratio / self.zoom
```

### Coordinate Transformation

World coordinates (logical node positions) are transformed to screen coordinates:

```python
screen_x = (world_x + offset_x) * zoom
screen_y = (world_y + offset_y) * zoom
```

### Performance Optimizations

1. **Dirty Flag** - Only redraws when something changes
2. **Viewport Culling** - Skips drawing nodes outside visible area
3. **FPS Throttling** - Limits redraw rate to 60 FPS

## Testing

Run the test suite:

```bash
# Unit tests
python tests/test_zoomable_node_editor.py

# Validation tests (non-GUI)
python tests/test_zoomable_editor_validation.py
```

## Documentation

See [docs/ZOOMABLE_NODE_EDITOR.md](../docs/ZOOMABLE_NODE_EDITOR.md) for complete documentation including:
- Detailed feature descriptions
- Architecture overview
- API reference
- Integration guide
- Performance considerations

## Comparison with Built-in Node Editor

| Aspect | Built-in `dpg.node_editor` | Custom `ZoomableNodeEditor` |
|--------|---------------------------|----------------------------|
| **Zoom** | Basic mouse wheel | Cursor-centered with precise control |
| **Pan** | Click and drag anywhere | Middle mouse button specific |
| **Nodes** | DPG widgets | Custom-drawn primitives |
| **Connections** | Built-in links | Custom Bezier curves |
| **Grid** | Optional minimap | Static background grid |
| **Customization** | Limited to DPG options | Full control over rendering |
| **Performance** | Built-in optimization | Custom culling + dirty flags |
| **Use Case** | General purpose | When you need pixel-perfect control |

## When to Use This vs Built-in

**Use the built-in `dpg.node_editor` when:**
- You want quick setup and standard behavior
- You need DPG's node widgets and interactivity
- Standard zoom/pan is sufficient

**Use `ZoomableNodeEditor` when:**
- You need cursor-centered zoom with specific formulas
- You want full control over node rendering
- You need custom performance optimizations
- You require specific visual customization
- You're learning about custom UI implementations

## Future Enhancements

Potential improvements (contributions welcome!):

- [ ] Interactive node dragging
- [ ] Connection creation by dragging from ports
- [ ] Node selection (single and multi-select)
- [ ] Delete nodes/connections
- [ ] Save/load graph state
- [ ] Undo/redo
- [ ] Snap to grid
- [ ] Zoom to fit all nodes
- [ ] Font size scaling with zoom

## License

This example is part of CV_Studio and uses the same license. See the LICENSE file in the root directory.

## Questions or Issues?

If you have questions about this example or find issues:

1. Check the [documentation](../docs/ZOOMABLE_NODE_EDITOR.md)
2. Run the tests to verify your setup
3. Open an issue in the CV_Studio repository

## Credits

Inspired by the problem statement requirements for implementing a custom node editor with advanced zoom and pan capabilities in DearPyGui.
