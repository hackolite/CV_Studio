# ObjHeatmap Coordinate Scaling Fix

## Problem Resolved

The ObjHeatmap node was not working correctly when processing object detection data because it failed to scale bounding box coordinates from the input image space to the processing window space.

### Issue Details

**Symptom**: La heatmap ne fonctionnait pas (The heatmap wasn't working)

**Root Cause**: 
- Object detection nodes (YOLO, etc.) output bounding boxes in the **original input image coordinate system** (e.g., 1920x1080 for Full HD)
- The ObjHeatmap node resizes input images to a processing window size (e.g., 640x480) for display
- The bounding box coordinates were being used **directly** without scaling
- This resulted in coordinates being clipped or placed at incorrect positions

**Example of the Bug**:
```
Input Image: 1920x1080 (Full HD)
Processing Window: 640x480
Detection bbox: [860, 490, 1060, 590] (center in Full HD)

WITHOUT FIX (WRONG):
  Direct use: [860, 490, 1060, 590]
  After clipping: [639, 479, 639, 479] ← Invalid! Clipped to edge
  Result: Heatmap appears at wrong position

WITH FIX (CORRECT):
  Scale factors: scale_x = 640/1920, scale_y = 480/1080
  Scaled bbox: [286, 217, 353, 262] ← Correct center position
  Result: Heatmap appears at correct position matching input
```

## Solution Implemented

### Code Changes

Modified `node/VisualNode/node_obj_heatmap.py`:

1. **Added scale factor calculation**:
   ```python
   # Calculate scaling factors from input image to processing window
   input_h, input_w = input_image.shape[:2]
   scale_x = small_window_w / input_w
   scale_y = small_window_h / input_h
   ```

2. **Applied scaling to bounding box coordinates**:
   ```python
   # Scale coordinates from input image space to processing window space
   x1, y1, x2, y2 = bbox
   x1 = int(x1 * scale_x)
   y1 = int(y1 * scale_y)
   x2 = int(x2 * scale_x)
   y2 = int(y2 * scale_y)
   ```

### Features Preserved

All existing functionality continues to work:
- ✅ Heatmap accumulation over time with decay
- ✅ Class-based filtering (show detections for specific classes)
- ✅ Image overlay blending
- ✅ Support for different processing window sizes
- ✅ Gaussian blur smoothing

### New Capabilities

The fix enables proper operation with:
- Different input image resolutions (QVGA, VGA, HD, Full HD, 4K)
- Real-time video streams at any resolution
- Multiple camera sources with different resolutions
- Object detection from any YOLO or detection model

## Testing

### Test Suite

Created comprehensive tests:

1. **test_obj_heatmap_coordinate_scaling.py** (NEW)
   - Full HD to VGA scaling
   - 4K to HD scaling
   - Same size (no scaling needed)
   - Class filtering with scaling
   - Visual validation outputs

2. **test_obj_heatmap_integration.py** (NEW)
   - Full HD video stream simulation
   - Class filtering integration
   - Multiple resolution sources (QVGA to 4K)

3. **Existing tests** (all still passing)
   - test_obj_heatmap.py
   - test_obj_heatmap_dimension_fix.py
   - test_obj_heatmap_input_validation.py

### Test Results

```
All tests: PASSED ✅
- Basic heatmap generation: ✅
- Class filtering: ✅
- Image overlay: ✅
- Accumulation over time: ✅
- Coordinate scaling (Full HD→VGA): ✅
- Coordinate scaling (4K→HD): ✅
- Multiple resolutions: ✅
- Integration scenarios: ✅
```

## Visual Validation

The fix is visually confirmed by comparing outputs:

**Before Fix**: Heatmap appears at wrong position (clipped to edge)
**After Fix**: Heatmap aligns perfectly with detections in resized image

See comparison image: `/tmp/coordinate_scaling_comparison.png`

## Usage Example

```python
# Object detection outputs (Full HD coordinates)
detection_data = {
    'bboxes': [[860, 490, 1060, 590]],  # Center of 1920x1080
    'scores': [0.9],
    'class_ids': [0]
}

# ObjHeatmap node configuration (VGA processing)
node = ObjHeatmap(opencv_setting_dict={
    'process_height': 480,
    'process_width': 640,
    'use_pref_counter': False
})

# Input image (Full HD)
input_image = cv2.imread("frame.jpg")  # 1920x1080

# Process - coordinates automatically scaled
result = node.update(
    node_id=1,
    connection_list=[...],
    node_image_dict={'VideoSource': input_image},
    node_result_dict={'Detection': detection_data},
    node_audio_dict={}
)

# Output heatmap is correctly positioned at center (480x640)
# with detection scaled to [286, 217, 353, 262]
```

## API Compatibility

**No breaking changes** - The fix is fully backward compatible:
- Existing projects continue to work
- Same input/output format
- Same configuration options
- Improved accuracy in all scenarios

## Performance Impact

**Negligible** - Only adds 2 simple divisions per frame:
- `scale_x = small_window_w / input_w`
- `scale_y = small_window_h / input_h`

No impact on processing speed or memory usage.

## Related Files

- `node/VisualNode/node_obj_heatmap.py` - Main implementation
- `tests/test_obj_heatmap_coordinate_scaling.py` - Coordinate scaling tests
- `tests/test_obj_heatmap_integration.py` - Integration tests

## Summary

La heatmap fonctionne maintenant correctement! (The heatmap now works correctly!)

The fix ensures that:
1. ✅ JSON object detection data is properly retrieved
2. ✅ Coordinates are correctly extracted from bboxes
3. ✅ Coordinates are adapted/scaled to match the resized image
4. ✅ Heatmap is displayed based on classes (filtering works)
5. ✅ Heatmap accumulates over time with proper decay
6. ✅ Works with any input resolution and any processing window size
