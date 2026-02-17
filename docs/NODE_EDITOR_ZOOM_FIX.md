# Node Editor Mouse Wheel Zoom Fix

## Issue
The node editor's mouse wheel zoom functionality was not working properly.

## Root Cause
The `handler_registry()` was placed **outside** the window context (at global scope), which created a global handler registry that intercepted mouse events before they could reach the node_editor widget.

## Solution
Moved the `handler_registry()` **inside** the window context to properly scope the handlers to the window. This allows the node_editor to receive mouse wheel events and enables its built-in zoom functionality.

## Changes Made

### Before (Broken):
```python
with dpg.window(...) as window:
    # ... window contents including node_editor ...
    self.window = window

# Handler registry at global scope - BLOCKS node_editor events
with dpg.handler_registry():
    dpg.add_mouse_click_handler(callback=self._callback_save_last_pos)
    dpg.add_key_press_handler(dpg.mvKey_Delete, callback=self._callback_mv_key_del)
```

### After (Fixed):
```python
with dpg.window(...) as window:
    # ... window contents including node_editor ...
    
    # Handler registry scoped to window - ALLOWS node_editor events
    with dpg.handler_registry():
        dpg.add_mouse_click_handler(callback=self._callback_save_last_pos)
        dpg.add_key_press_handler(dpg.mvKey_Delete, callback=self._callback_mv_key_del)
    
    self.window = window
```

## How DearPyGui Node Editor Zoom Works

In DearPyGui 2.0+:
- Node editors have **built-in mouse wheel zoom** functionality
- Zoom works automatically when the mouse wheel is scrolled over the node editor
- No special configuration or handlers are needed
- However, global handlers can **block** this functionality by intercepting events

## Handler Registry Scope

- **Inside window**: Handlers are scoped to that window and don't interfere with widget-level events
- **Outside window**: Handlers are global and can intercept events before they reach widgets

## Testing
A test was added in `tests/test_handler_registry_placement.py` to verify:
1. The handler_registry is inside the window context (proper indentation)
2. The handler_registry is created before `self.window = window`
3. The comment explaining the placement is accurate

## Files Modified
- `node_editor/node_main.py` - Moved handler_registry inside window context

## Files Added
- `tests/test_handler_registry_placement.py` - Test to verify the fix
