# Tennis Object Detection Coordinate Offset Fix

## Problem Description (French)
Pour le node object detection, option tennis, j'utilise un model tennis.onnx, qui accept 608*608, la detection est décalé, vérifie ce qui ne va pas, probablement le resize est mal fait pour le display et l'envoie de l'image dans update, vérifie ça et fixe.

## Problem Analysis

The tennis object detection node was experiencing offset/misaligned bounding boxes. Investigation revealed:

1. **Model Input Size**: The `tennis.onnx` model accepts input of shape `[1, 3, 416, 608]` (height=416, width=608)
2. **Incorrect Coordinate Space**: The code was resizing images to 608x416 for inference but not scaling the bounding box coordinates back to the original image dimensions
3. **Missing Ratio Calculation**: Using a fixed `gain = 1` meant no coordinate transformation was applied

## Root Cause

In the original `yolotennis.py`:
- Line 37: Image resized to (608, 416) 
- Line 58: Fixed `gain = 1` used in postprocessing
- Lines 76-79: Bounding boxes calculated in 608x416 space but returned for original image

When these coordinates were drawn on the original image in `node_object_detection.py`, they appeared offset because they were in the wrong coordinate space.

## Solution Implemented

### Changes to `yolotennis.py`:

1. **Added Model Input Constants**:
   ```python
   MODEL_INPUT_WIDTH = 608
   MODEL_INPUT_HEIGHT = 416
   ```

2. **Capture Original Dimensions**:
   ```python
   original_height, original_width = image.shape[:2]
   ```

3. **Calculate Scaling Ratios**:
   ```python
   scale_x = original_width / float(self.MODEL_INPUT_WIDTH)
   scale_y = original_height / float(self.MODEL_INPUT_HEIGHT)
   ```

4. **Apply Scaling in Postprocessing**:
   ```python
   x1 = int((x - w / 2) * scale_x)
   y1 = int((y - h / 2) * scale_y)
   x2 = int((x + w / 2) * scale_x)
   y2 = int((y + h / 2) * scale_y)
   ```

5. **Removed Unused Code**:
   - Removed `gain = 1` variable
   - Removed unused `input_shape`, `input_width`, `input_height` attributes

## Testing

Created comprehensive tests to verify the fix:

1. **Unit Tests** (`test_tennis_detection_coordinates.py`):
   - Verifies coordinate scaling math for various image sizes
   - Confirms presence of scaling logic in source code
   
2. **Integration Tests** (`test_tennis_detection_integration.py`):
   - Tests with actual tennis.onnx model
   - Verifies bounding boxes stay within image bounds
   - Tests multiple image resolutions (VGA, HD, Full HD, native)

All tests pass ✅

## Example

For an image of size 1280x720:
- **Scale X**: 1280 / 608 ≈ 2.105
- **Scale Y**: 720 / 416 ≈ 1.731

If model outputs bbox at (304, 208) with size (100, 100):
- **Before fix**: Box coordinates would be ~(254, 158) to (354, 258) in 608x416 space
- **After fix**: Box coordinates properly scaled to ~(535, 274) to (746, 447) in 1280x720 space

## Benefits

1. ✅ Bounding boxes now align correctly with detected objects
2. ✅ Works with any input image size
3. ✅ More maintainable code with constants
4. ✅ No security vulnerabilities introduced
5. ✅ All existing tests continue to pass

## Files Changed

- `node/DLNode/object_detection/TennisYOLO/yolotennis.py` - Core fix
- `tests/test_tennis_detection_coordinates.py` - Unit tests (new)
- `tests/test_tennis_detection_integration.py` - Integration tests (new)

## Security Summary

CodeQL analysis completed with **0 alerts** - no security vulnerabilities introduced.
