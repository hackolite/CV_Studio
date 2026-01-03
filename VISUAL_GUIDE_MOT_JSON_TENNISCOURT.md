# Visual Guide: MOT JSON Output & Tennis Court Size Reduction

## Feature 1: MOT JSON Output

### Before
```
MOT Node
├── Input01: IMAGE (from Detection)
├── Input02: TEXT (model selection)
├── Output01: IMAGE (visualization)
└── Output02: TIME_MS (elapsed time)
     
     ❌ No JSON output pin
     ❌ Cannot connect to Homography
```

### After
```
MOT Node
├── Input01: IMAGE (from Detection)
├── Input02: TEXT (model selection)
├── Output01: IMAGE (visualization)
├── Output02: TIME_MS (elapsed time)
└── Output03: JSON (tracking data) ⭐ NEW
     │
     ├─ bboxes: [[x1,y1,x2,y2], ...]
     ├─ scores: [0.9, 0.85, ...]
     ├─ class_ids: [0, 0, 1, ...]
     ├─ class_names: {0: 'person', 1: 'ball'}
     ├─ track_ids: [1, 2, 3, ...] (MOT-specific)
     └─ track_id_dict: {1: 0, 2: 1, ...} (MOT-specific)
     
     ✅ Yellow button (matches ObjectDetection style)
     ✅ Can connect to Homography node
     ✅ Full pipeline: MOT → Homography → TennisCourt
```

## Feature 2: Tennis Court Size Reduction

### Before (Full Scale)
```
Display Area: 600x800 pixels
┌─────────────────────────────────────────────────┐
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │                                          │  │
│  │                                          │  │
│  │                                          │  │
│  │                                          │  │
│  │          Tennis Court (Full Size)       │  │
│  │          341 x 740 pixels                │  │
│  │                                          │  │
│  │                                          │  │
│  │                                          │  │
│  │                                          │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘

❌ Court takes up most of display
❌ Little room for margins/UI elements
```

### After (2x Reduction)
```
Display Area: 600x800 pixels
┌─────────────────────────────────────────────────┐
│                                                 │
│                   [margin]                      │
│                                                 │
│        ┌──────────────────────┐                │
│        │                      │                │
│        │  Tennis Court        │                │
│        │  (Half Size)         │                │
│        │  170 x 370 pixels    │                │
│        │                      │                │
│        │    [centered]        │                │
│        │                      │                │
│        └──────────────────────┘                │
│                                                 │
│                   [margin]                      │
│                                                 │
└─────────────────────────────────────────────────┘

✅ Court is 50% of original size (2x reduction)
✅ Centered with adequate margins
✅ Better visual balance
✅ Room for UI elements
```

## Implementation Details

### Code Changes in `node/TrackerNode/node_mot.py`

```python
# Added JSON output pin definition (lines 58-59)
node.tag_node_output03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
node.tag_node_output03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

# Added yellow theme (lines 84-89)
with dpg.theme() as yellow_button_theme:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

# Added JSON button UI (lines 134-145)
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

# JSON data already returned (line 350)
return {"image": output_frame, "json": result, "audio": None}
```

### Tennis Court Size in `node/VisualNode/node_tennis_court.py`

```python
# Calculate base scale (lines 533-535)
scale_x = (small_window_w - VISUALIZATION_MARGIN) / COURT_WIDTH_M
scale_y = (small_window_h - VISUALIZATION_MARGIN) / COURT_LENGTH_M
base_scale = min(scale_x, scale_y)

# Reduce by 2x (line 538)
scale = base_scale / 2.0  # ⭐ KEY CHANGE

# Center the court (lines 541-544)
court_width_px = int(COURT_WIDTH_M * scale)
court_length_px = int(COURT_LENGTH_M * scale)
offset_x = (small_window_w - court_width_px) // 2
offset_y = (small_window_h - court_length_px) // 2
```

## Pipeline Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Camera    │────▶│ObjectDetection│────▶│     MOT      │────▶│  Homography  │
│   / Video    │     │   (JSON Out) │     │  (JSON Out)  │     │ (Transform)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                              │                     │                    │
                              │                     │                    │
                              └─────────────────────┴────────────────────┘
                                                     │
                                                     ▼
                                            ┌──────────────┐
                                            │ TennisCourt  │
                                            │ (Half Size)  │
                                            └──────────────┘
```

## Usage Example

### Step 1: Connect Nodes
1. Connect Camera/Video to ObjectDetection
2. Connect ObjectDetection to MOT (image input)
3. Connect MOT JSON output (yellow button) to Homography
4. Connect PoseEstimation (court keypoints) to Homography
5. Connect Homography to TennisCourt

### Step 2: Configure
- MOT: Select tracking algorithm (ByteTrack, SORT, etc.)
- ObjectDetection: Set score threshold
- TennisCourt: Automatically uses half-size rendering

### Step 3: Run
- Tennis court appears centered at half size
- Player positions transform from image to court coordinates
- Tracking IDs persist across frames
- Average positions calculated by label

## Benefits

### MOT JSON Output
✅ **Compatibility**: Works with Homography like ObjectDetection
✅ **Flexibility**: Can use MOT or ObjectDetection interchangeably
✅ **Tracking**: Includes persistent track IDs
✅ **UI Consistency**: Yellow button matches existing design

### Tennis Court Size Reduction
✅ **Better Proportions**: Court doesn't dominate the display
✅ **More Space**: Room for multiple visualization nodes
✅ **Centered**: Professional, balanced appearance
✅ **Scalable**: Still readable at half size

## Testing

Three comprehensive test suites verify functionality:

1. **`test_mot_json_output.py`**
   - JSON structure validation
   - Homography compatibility
   - Field type checking

2. **`test_tennis_court_size_reduction.py`**
   - Scale calculation verification
   - 2x reduction confirmation
   - Centering validation

3. **`test_mot_homography_pipeline.py`**
   - End-to-end pipeline testing
   - Data flow verification
   - Integration testing

All tests: ✅ PASSING

## Security

- CodeQL scan: ✅ 0 vulnerabilities
- No new dependencies
- No external connections
- Data validation at multiple layers
- Read-only operations

---

**Status**: ✅ Implementation Complete  
**Ready for**: Production Use  
**Compatibility**: Backward compatible
