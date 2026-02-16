# Display Checkbox Implementation Guide

## Overview

This document explains the implementation of display checkboxes and daemon mode for CPU optimization in CV_Studio.

## Features Implemented

### 1. Global Display Mode Control

A global display mode flag has been added to `node/basenode.py` that controls whether display updates should be performed:

- **UI Mode** (default): Display enabled, nodes render to UI
- **Daemon Mode**: Display disabled, all display rendering skipped for CPU optimization

```python
from node.basenode import set_display_mode, is_display_enabled

# Set display mode (True = UI mode, False = daemon mode)
set_display_mode(False)  # Disables all display updates

# Check if display is enabled
if is_display_enabled():
    # Perform display updates
    pass
```

### 2. Node Display Checkbox

Individual nodes that display images now have a "Display" checkbox that allows users to selectively disable display updates for specific nodes:

- When **checked**: Node updates its display texture (normal behavior)
- When **unchecked**: Node skips display rendering (CPU optimization)
- In **daemon mode**: All display checkboxes are effectively disabled regardless of their state

### 3. SaveWorkflow Node

A new `SaveWorkflow` node has been added in the `SystemNode` category:

**Location:** `node/SystemNode/node_save_workflow.py`

**Features:**
- Saves workflow configuration to JSON file
- Includes all node parameters (sliders, checkboxes, positions, etc.)
- Can be triggered via button click
- Uses the node editor's existing export mechanism

**Usage:**
1. Add `SaveWorkflow` node from System menu
2. Enter desired filepath (default: `workflow.json`)
3. Click "Save Workflow" button
4. Workflow is saved including all node settings

### 4. Daemon Mode

The application can now run in daemon mode without displaying the UI viewport:

**Command:**
```bash
python main.py --daemon --workflow path/to/workflow.json
```

**Arguments:**
- `--daemon`: Enable daemon mode (no UI display)
- `--workflow <path>`: Path to workflow JSON file to load

**Behavior in Daemon Mode:**
- DearPyGUI viewport is not shown
- Global display mode is set to `False`
- All display updates are skipped (optimizes CPU)
- Workflow processing continues in background
- Workflow is loaded automatically from specified JSON file

## Implementation Pattern for Adding Display Checkbox to Nodes

### Step 1: Add Tag Definitions (in `add_node()` method)

```python
def add_node(self, parent, node_id, pos=[0, 0], opencv_setting_dict=None, callback=None):
    node = Node()
    node.tag_node_name = str(node_id) + ':' + node.node_tag
    
    # ... other tags ...
    
    # Add display checkbox tags
    node.tag_node_display_checkbox_name = node.tag_node_name + ':DisplayCheckbox'
    node.tag_node_display_checkbox_value_name = node.tag_node_name + ':DisplayCheckboxValue'
```

### Step 2: Add UI Checkbox (in `add_node()` method)

```python
# Display checkbox (default True) - for CPU optimization
with dpg.node_attribute(
        tag=node.tag_node_display_checkbox_name,
        attribute_type=dpg.mvNode_Attr_Static,
):
    dpg.add_checkbox(
        tag=node.tag_node_display_checkbox_value_name,
        label='Display',
        default_value=True,
    )
```

### Step 3: Conditionally Update Display (in `update()` method)

**Before:**
```python
if frame is not None:
    texture = self.convert_cv_to_dpg(frame, width, height)
    dpg_set_value(output_value_tag, texture)
```

**After:**
```python
# Only update display if display is enabled (for CPU optimization)
if frame is not None and self.should_update_display(node_id):
    texture = self.convert_cv_to_dpg(frame, width, height)
    dpg_set_value(output_value_tag, texture)
```

### Step 4: Save Display Checkbox State (in `get_setting_dict()` method)

```python
def get_setting_dict(self, node_id):
    tag_node_name = str(node_id) + ':' + self.node_tag
    display_checkbox_tag = tag_node_name + ':DisplayCheckboxValue'
    
    # ... other settings ...
    
    display_value = dpg_get_value(display_checkbox_tag)
    if display_value is None:
        display_value = True  # Default to True
    
    setting_dict = {}
    setting_dict['ver'] = self._ver
    setting_dict['pos'] = pos
    # ... other settings ...
    setting_dict[display_checkbox_tag] = display_value
    
    return setting_dict
```

### Step 5: Restore Display Checkbox State (in `set_setting_dict()` method)

```python
def set_setting_dict(self, node_id, setting_dict):
    tag_node_name = str(node_id) + ':' + self.node_tag
    display_checkbox_tag = tag_node_name + ':DisplayCheckboxValue'
    
    # ... other settings ...
    
    display_value = setting_dict.get(display_checkbox_tag, True)
    
    # Set display checkbox
    try:
        dpg_set_value(display_checkbox_tag, display_value)
    except:
        pass  # Ignore if the UI element doesn't exist yet
```

## Example Implementations

### Example 1: ProcessNode (node_blur.py)

Complete example of display checkbox implementation in a ProcessNode. Shows the pattern for:
- Simple image processing node
- Single image output
- Basic display control

**File:** `node/ProcessNode/node_blur.py`

### Example 2: DLNode (node_object_detection.py)

Complete example of display checkbox implementation in a DLNode. Shows the pattern for:
- Complex AI model node
- Multiple outputs (image + JSON)
- Display of processed results with bounding boxes

**File:** `node/DLNode/node_object_detection.py`

## Node Types Requiring Display Checkbox

The following node types should have display checkboxes added:

1. **ProcessNode** (~26 files)
   - All nodes that process and display images
   - Examples: Blur, Canny, Threshold, ColorSpace, etc.

2. **VisualNode** (~5 files)
   - Visualization nodes that create image outputs
   - Examples: Heatmap, Map, ObjChart, ObjHeatmap, TennisCourt

3. **DLNode** (~7 files)
   - Deep learning model nodes
   - Examples: ObjectDetection, PoseEstimation, Classification, etc.

4. **VideoNode** (selected nodes)
   - Nodes that display video frames
   - Examples: VideoWriter, ImageConcat, etc.

5. **TrackerNode** (selected nodes)
   - Object tracking nodes that display results
   
6. **OverlayNode** (all nodes)
   - Nodes that draw overlays on images

7. **InputNode** (selected nodes)
   - Video input nodes that display preview

## Testing

### Test Display Checkbox in UI Mode

1. Launch CV_Studio normally: `python main.py`
2. Create a workflow with nodes that have display checkboxes (e.g., Blur)
3. Toggle the "Display" checkbox:
   - **Checked**: Node should update display
   - **Unchecked**: Node should NOT update display (texture stays unchanged)
4. Verify node still processes data (output connects work) even when display is off

### Test SaveWorkflow Node

1. Create a workflow with several nodes
2. Adjust node parameters (sliders, checkboxes)
3. Add SaveWorkflow node from System menu
4. Enter filepath and click "Save Workflow"
5. Verify JSON file is created with all node settings
6. Load the workflow (File > Import) and verify all settings are restored

### Test Daemon Mode

1. Save a workflow to `test_workflow.json`
2. Run in daemon mode:
   ```bash
   python main.py --daemon --workflow test_workflow.json
   ```
3. Verify:
   - No UI window appears
   - Workflow processes in background
   - Display updates are skipped (check logs)
   - CPU usage is lower than UI mode

## Performance Benefits

### CPU Optimization

When display is disabled (checkbox unchecked or daemon mode):
- **Skipped operations:**
  - Image resizing for display (`cv2.resize`)
  - Color conversion for DearPyGUI (`np.flip`, `np.true_divide`)
  - Texture updates (`dpg_set_value`)
  
- **Expected CPU reduction:**
  - Per node: 5-15% CPU reduction (depends on image size)
  - Full workflow (10+ nodes): 20-50% CPU reduction
  - Daemon mode (all displays off): Up to 60% CPU reduction

### Use Cases for Daemon Mode

1. **Production deployment**: Run workflows on servers without display overhead
2. **Batch processing**: Process video files without UI
3. **Edge devices**: Run on resource-constrained devices
4. **Testing**: Automated testing without UI dependencies

## Implementation Status

- [x] Global display mode control (basenode.py)
- [x] `should_update_display()` helper method
- [x] SaveWorkflow node (SystemNode)
- [x] Daemon mode support (main.py)
- [x] Example: ProcessNode/node_blur.py
- [x] Example: DLNode/node_object_detection.py
- [ ] Remaining ProcessNode files (~24 nodes)
- [ ] Remaining VisualNode files (~5 nodes)
- [ ] Remaining DLNode files (~6 nodes)
- [ ] VideoNode files (selected)
- [ ] TrackerNode files (selected)
- [ ] OverlayNode files (all)
- [ ] InputNode files (selected)

## Migration Notes

### Backward Compatibility

- Display checkbox defaults to `True` (enabled)
- Old workflows without display settings will work normally
- `should_update_display()` handles missing checkbox gracefully
- Daemon mode is opt-in via command line flag

### Version Compatibility

- Display checkbox added in version: TBD
- Workflows saved with display settings are forward-compatible
- Loading old workflows without display settings: checkbox defaults to `True`

## Future Enhancements

1. **Auto-disable display for disconnected outputs**: Automatically disable display for nodes whose image output is not connected
2. **Performance monitoring**: Add metrics to show CPU savings from disabled displays
3. **Bulk enable/disable**: Global UI control to toggle all display checkboxes
4. **Display groups**: Group nodes and control display for entire groups

## References

- Main implementation: `main.py` (daemon mode)
- Base functionality: `node/basenode.py` (global display control)
- Save node: `node/SystemNode/node_save_workflow.py`
- Example ProcessNode: `node/ProcessNode/node_blur.py`
- Example DLNode: `node/DLNode/node_object_detection.py`
