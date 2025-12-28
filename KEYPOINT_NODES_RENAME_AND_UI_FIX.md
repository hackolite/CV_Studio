# Summary of Changes - Keypoint Nodes and UI Fix

## Issues Resolved

This PR resolves three problems stated in the issue:

1. **Renamed `Trigger/KeypointDeviation` → `Court/KeypointDeviation`**
2. **Renamed `DataProcess/Keypoints` → `Court/KeypointData`**
3. **Fixed UI bug: unable to create new windows or make links during video playback**

## Code Changes

### 1. Node Renaming

**File: `node/TriggerNode/node_trigger_keypoint_deviation.py`**
- Changed `node_label = 'Trigger/KeypointDeviation'` 
- To `node_label = 'Court/KeypointDeviation'`

**File: `node/StatsNode/node_dataprocessing_keypoints.py`**
- Changed `node_label = 'DataProcess/Keypoints'`
- To `node_label = 'Court/KeypointData'`

**Updated Tests**
- `tests/test_keypoints_nodes.py`: Fixed imports and assertions

### 2. UI Threading Bug Fix

**Identified Problem**
When video is playing, two threads access DearPyGUI simultaneously:
- **Main thread**: Processes UI events via `dpg.start_dearpygui()`
- **Worker thread**: Continuously updates nodes via `async_main()` in thread executor

This caused race conditions that prevented the UI from responding to user actions.

**Implemented Solution**

Added a thread-safe lock (`threading.RLock`) shared across all DearPyGUI access:

**File: `node_editor/util.py`**
```python
import threading
# Global lock for thread-safe DearPyGUI operations
_dpg_lock = threading.RLock()

def dpg_set_value(tag, value):
    with _dpg_lock:
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, value)

def dpg_get_value(tag):
    value = None
    with _dpg_lock:
        if dpg.does_item_exist(tag):
            value = dpg.get_value(tag)
    return value
```

**File: `node_editor/node_editor.py`**
- Import shared lock: `from .util import _dpg_lock`
- Protected `_callback_add_node` with `with _dpg_lock:`
- Protected `_callback_link` with `with _dpg_lock:`

## Technical Details

### Why RLock instead of Lock?

`RLock` (Reentrant Lock) allows the same thread to acquire the lock multiple times, which is necessary when nested DearPyGUI calls occur within the same thread.

### Protected Scenarios

1. **Adding nodes**: When user clicks menu to add node while async_main is updating existing nodes
2. **Creating links**: When user creates connections between nodes while values are being updated
3. **Reading/writing values**: All dpg_get_value/dpg_set_value calls are now thread-safe

## Tests

### New Test: `tests/test_threading_lock.py`
Verifies that:
- ✅ Lock `_dpg_lock` exists and is of type RLock
- ✅ `dpg_set_value` uses the lock
- ✅ `dpg_get_value` uses the lock
- ✅ `_callback_add_node` uses the lock
- ✅ `_callback_link` uses the lock

### Validation
- ✅ All tests pass
- ✅ Python syntax validation
- ✅ CodeQL: 0 vulnerabilities detected

## Impact

### Before
- ❌ UI frozen during video playback
- ❌ Cannot add nodes
- ❌ Cannot create links
- ❌ Possible race conditions

### After
- ✅ UI responsive even during video playback
- ✅ Can add nodes at any time
- ✅ Create links without blocking
- ✅ Thread-safe DearPyGUI access

## Backward Compatibility

These changes are 100% backward compatible:
- `node_tag` values remain unchanged (only `node_label` modified)
- Existing JSON files will continue to work
- No API changes
- Same behavior, just more stable

## Security Summary

**CodeQL Scan**: 0 alerts
- No vulnerabilities introduced
- Appropriate use of synchronization primitives
- No resource leaks
- Error handling preserved
