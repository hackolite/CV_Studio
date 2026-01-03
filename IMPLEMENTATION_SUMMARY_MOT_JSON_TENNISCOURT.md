# Implementation Summary: MOT JSON Output & Tennis Court Size Reduction

## Problem Statement (French)
> il faut que MOT soit capable de renvoyer un JSON comme VisionModel/objecdetection qui peux etre inséré dans homography , le tenniscourt est trop grand, il faut reduire la taille du node de 2x

## Translation
1. MOT needs to be able to return JSON like VisionModel/ObjectDetection that can be inserted into homography
2. The tennis court is too large, it needs to reduce the node size by 2x

## Implementation Details

### 1. MOT JSON Output (✓ Complete)

**Changes Made:**
- Added JSON output pin (Output03) to the Multi-Object Tracking (MOT) node in `node/TrackerNode/node_mot.py`
- Added yellow-themed button for JSON output (consistent with ObjectDetection node)
- JSON output includes all required fields for Homography compatibility:
  - `bboxes`: Bounding boxes of tracked objects
  - `scores`: Detection confidence scores
  - `class_ids`: Object class identifiers
  - `class_names`: Dictionary/list of class names
  - `track_ids`: Unique tracking IDs (MOT-specific)
  - `track_id_dict`: Mapping of track IDs to indices (MOT-specific)

**Code Changes:**
```python
# Added Output03 JSON pin definition (lines 58-59)
node.tag_node_output03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
node.tag_node_output03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

# Added yellow theme for JSON button (lines 84-89)
with dpg.theme() as yellow_button_theme:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

# Added JSON output button UI element (lines 134-145)
with dpg.node_attribute(
        tag=node.tag_node_output03_name,
        attribute_type=dpg.mvNode_Attr_Output,
):
    btn = dpg.add_button(
        label="JSON",
        tag=node.tag_node_output03_value_name,
        width=small_window_w,
        enabled=False,
    )
    dpg.bind_item_theme(btn, yellow_button_theme)
```

**How It Works:**
- The MOT node already returns JSON data in its update method via `return {"image": output_frame, "json": result, "audio": None}`
- The new JSON output pin provides a visual connection point in the UI
- Downstream nodes (like Homography) can now connect to the JSON output and receive the tracking data
- The format is identical to ObjectDetection, ensuring full compatibility

**Pipeline Flow:**
```
ObjectDetection (JSON) → MOT (JSON) → Homography → TennisCourt
```

### 2. Tennis Court Size Reduction (✓ Already Implemented)

**Verification:**
- The tennis court visualization was already reduced by 2x (halved) in the code
- Located in `node/VisualNode/node_tennis_court.py` line 538:
  ```python
  # REDUCE COURT SIZE BY HALF as per requirement
  scale = base_scale / 2.0
  ```

**Measurements:**
- Display dimensions: 600x800 pixels
- Original court size (full scale): 341x740 pixels
- New court size (half scale): 170x370 pixels
- **Reduction factor: 2.0x (exactly half)**

**Benefits:**
- Court is centered in the display area
- Leaves adequate margin for UI elements
- Players are still clearly visible at the reduced scale
- Better overall visualization balance

## Testing

### New Tests Created:

1. **`tests/test_mot_json_output.py`**
   - Verifies MOT JSON output structure
   - Tests MOT → Homography compatibility
   - Confirms all required fields are present
   - ✓ All tests passing

2. **`tests/test_tennis_court_size_reduction.py`**
   - Verifies court size is exactly 2x smaller
   - Tests visualization with reduced size
   - Confirms player positions render correctly
   - ✓ All tests passing

### Existing Tests:
- `tests/test_mot_homography_pipeline.py` - ✓ All tests passing
- Full pipeline test: MOT → Homography → TennisCourt - ✓ Working

## Code Review Results
- ✓ No security vulnerabilities found (CodeQL analysis)
- ✓ Code review completed with minor nitpick addressed
- ✓ All tests passing

## Summary
Both requirements from the problem statement have been successfully implemented:

1. ✅ **MOT JSON Output**: MOT node now has a JSON output pin (Output03) that outputs tracking data in the same format as ObjectDetection, making it compatible with the Homography node.

2. ✅ **Tennis Court Size Reduction**: The tennis court visualization is rendered at half its original size (2x reduction), providing better visual balance and leaving room for UI elements.

The full pipeline now works seamlessly:
```
Camera/Video → ObjectDetection → MOT (with JSON output) → Homography → TennisCourt (half size)
```

## Files Modified
- `node/TrackerNode/node_mot.py`: Added JSON output pin (Output03)
- `tests/test_mot_json_output.py`: New test file
- `tests/test_tennis_court_size_reduction.py`: New test file

## Compatibility
- ✅ Backward compatible (existing MOT functionality unchanged)
- ✅ Forward compatible (JSON output works with Homography)
- ✅ UI consistent (yellow JSON button matches ObjectDetection)
- ✅ Full pipeline tested and working
