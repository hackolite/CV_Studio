# CV_Studio Node Editor - Zoom Functionality

## Overview

CV_Studio's node editor includes advanced zoom functionality inspired by `examples/zoomable_node_editor.py`, providing a professional and intuitive zooming experience.

## Zoom Controls

### Mouse Wheel Zoom

**Basic Usage:**
- Scroll **up** (away from you) to **zoom in**
- Scroll **down** (towards you) to **zoom out**

**Range:**
- Minimum zoom: **0.1x** (10% of original size)
- Maximum zoom: **5.0x** (500% of original size)
- Default zoom: **1.0x** (100%, no zoom)

**Behavior:**
- Each scroll increment changes zoom by **±10%**
- Zoom factor: 1.1 for zoom in, 0.9 for zoom out
- Zoom level is clamped to the valid range (0.1x - 5.0x)
- Zoom level is displayed in the menu bar in real-time

### Menu Controls

The **View** menu provides alternative zoom controls:

1. **Zoom In (+10%)** - Increases zoom level by 10%
2. **Zoom Out (-10%)** - Decreases zoom level by 10%
3. **Reset Zoom (100%)** - Resets zoom to 1.0x (100%)

### Zoom Level Display

The current zoom level is shown in the menu bar as:
```
Zoom: 100%
```

This updates in real-time as you zoom in or out.

## Technical Details

### Implementation

CV_Studio uses DearPyGui's built-in node editor zoom functionality, enhanced with:

1. **Zoom Tracking** - Monitors zoom level changes via mouse wheel handler
2. **UI Feedback** - Displays current zoom percentage in menu bar
3. **Manual Controls** - Provides menu-based zoom controls for precision
4. **Range Enforcement** - Ensures zoom stays within 0.1x to 5.0x range

### Code Architecture

The zoom functionality is implemented in `node_editor/node_main.py`:

```python
# Zoom state (class attributes)
_zoom_level = 1.0      # Current zoom level
_min_zoom = 0.1        # Minimum zoom (10%)
_max_zoom = 5.0        # Maximum zoom (500%)

# Zoom handlers
_callback_mouse_wheel_zoom(sender, delta)  # Track mouse wheel
_callback_zoom_in()                         # Menu: Zoom In
_callback_zoom_out()                        # Menu: Zoom Out
_callback_zoom_reset()                      # Menu: Reset Zoom
_update_zoom_display()                      # Update UI
```

### Handler Registry Placement

For zoom to work correctly, the handler registry must be scoped **inside the window context**:

```python
with dpg.window(...) as window:
    # ... node editor and UI ...
    
    # Handler registry INSIDE window
    with dpg.handler_registry():
        dpg.add_mouse_wheel_handler(callback=self._callback_mouse_wheel_zoom)
```

This allows the node editor to receive mouse wheel events while still tracking them for UI feedback.

## Comparison with Example

CV_Studio's zoom implementation is inspired by `examples/zoomable_node_editor.py` but adapted for the built-in DearPyGui node editor:

| Feature | Example Implementation | CV_Studio Implementation |
|---------|----------------------|-------------------------|
| **Zoom Range** | 0.1x - 5.0x ✓ | 0.1x - 5.0x ✓ |
| **Zoom Factor** | 1.1 / 0.9 ✓ | 1.1 / 0.9 ✓ |
| **Mouse Wheel** | Custom handler ✓ | Built-in + tracking ✓ |
| **UI Controls** | N/A | View menu ✓ |
| **Level Display** | N/A | Menu bar ✓ |
| **Rendering** | Custom drawlist | Built-in node_editor |

### Key Differences

1. **Example** uses custom rendering with `dpg.drawlist()` for complete control
2. **CV_Studio** uses `dpg.node_editor()` built-in widget for stability
3. **CV_Studio** adds UI controls (View menu) for better UX
4. **CV_Studio** displays zoom level for user awareness

Both achieve the same zoom range and behavior, but with different technical approaches.

## Usage Tips

### Efficient Zooming

- **Quick zoom in**: Scroll wheel up repeatedly
- **Quick zoom out**: Scroll wheel down repeatedly  
- **Return to default**: View → Reset Zoom (100%)
- **Precise adjustment**: Use View menu for exact 10% increments

### Best Practices

1. **Start at 100%** - Default view shows full detail
2. **Zoom out (0.1x - 1.0x)** - See overall graph structure
3. **Zoom in (1.0x - 5.0x)** - Focus on specific node details
4. **Reset often** - Use Reset Zoom to return to familiar scale

### Common Zoom Levels

- **10% (0.1x)** - Maximum overview, see entire graph
- **50% (0.5x)** - Wide view, navigate large graphs
- **100% (1.0x)** - Default, optimal for most work
- **200% (2.0x)** - Detailed view, read small text
- **500% (5.0x)** - Maximum detail, inspect individual pixels

## Troubleshooting

### Zoom Not Working

If mouse wheel zoom doesn't respond:

1. **Check handler placement** - Handler registry must be inside window context
2. **Update DearPyGui** - Ensure you have DearPyGui 2.0+ installed:
   ```bash
   pip install --upgrade dearpygui>=2.0.0
   ```
3. **Check mouse focus** - Mouse cursor must be over the node editor window

### Zoom Level Incorrect

If the displayed zoom level doesn't match visual zoom:

1. **Reset zoom** - Use View → Reset Zoom (100%)
2. **Restart application** - Zoom level resets to 1.0 on startup

### Can't Zoom Beyond Limits

Zoom is intentionally limited to 0.1x - 5.0x:

- **Below 0.1x**: Graph becomes too small to be useful
- **Above 5.0x**: Nodes become pixelated and hard to work with

These limits match professional node editor standards.

## Future Enhancements

Potential additions (not yet implemented):

- [ ] Keyboard shortcuts (Ctrl+Plus/Minus, Ctrl+0)
- [ ] Zoom to fit - Auto-zoom to show all nodes
- [ ] Zoom to selection - Focus on selected nodes
- [ ] Zoom slider - Visual zoom control
- [ ] Pan controls - Move view without mouse

## References

- **Example Implementation**: `examples/zoomable_node_editor.py`
- **Main Implementation**: `node_editor/node_main.py`
- **Tests**: `tests/test_node_editor_zoom.py`
- **Zoom Fix Documentation**: `docs/NODE_EDITOR_ZOOM_FIX.md`

## Related Documentation

- [Node Editor Zoom Fix](NODE_EDITOR_ZOOM_FIX.md) - Original zoom fix (handler registry placement)
- [Zoomable Node Editor](ZOOMABLE_NODE_EDITOR.md) - Custom implementation details
- [Zoomable Node Editor Summary](ZOOMABLE_NODE_EDITOR_SUMMARY.md) - Feature comparison

---

**Last Updated**: 2026-02-18  
**Version**: 1.0  
**Status**: Implemented and tested ✅
