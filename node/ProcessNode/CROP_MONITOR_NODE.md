# Crop Monitor Node

## Overview

The **Crop Monitor** node is a monitoring and visualization node that displays information about cropped regions of an image. It allows you to monitor the dimensions and position of a cropped area in real-time.

## Location

- **Menu Category**: VisionProcess
- **File**: `node/ProcessNode/node_crop_monitor.py`

## Features

- **Real-time Crop Monitoring**: Displays the cropped region with live updates
- **Dimension Display**: Shows width and height of the cropped area in pixels
- **Position Tracking**: Displays the center coordinates (x, y) of the cropped region
- **Compatible with Crop Node**: Can be connected to the output of a Crop node or accept manual crop parameters

## Inputs

1. **Image Input** (TYPE_IMAGE)
   - The original image to be cropped
   - Can accept images from camera, video, or other image processing nodes

2. **min x** (TYPE_FLOAT)
   - Minimum X coordinate (normalized, 0.0 to 0.99)
   - Defines the left edge of the crop region
   - Default: 0.0

3. **max x** (TYPE_FLOAT)
   - Maximum X coordinate (normalized, 0.01 to 1.00)
   - Defines the right edge of the crop region
   - Default: 1.0

4. **min y** (TYPE_FLOAT)
   - Minimum Y coordinate (normalized, 0.0 to 0.99)
   - Defines the top edge of the crop region
   - Default: 0.0

5. **max y** (TYPE_FLOAT)
   - Maximum Y coordinate (normalized, 0.01 to 1.00)
   - Defines the bottom edge of the crop region
   - Default: 1.0

## Outputs

1. **Cropped Image** (TYPE_IMAGE)
   - The cropped region of the input image
   - Can be connected to other processing nodes

2. **Processing Time** (TYPE_TIME_MS)
   - Elapsed processing time in milliseconds
   - Only displayed when `use_pref_counter` is enabled

## Monitoring Information

The node displays the following information directly in the node interface:

- **Width**: Width of the cropped region in pixels
- **Height**: Height of the cropped region in pixels
- **Center**: Center position of the crop region in pixel coordinates (x, y)

## Usage Examples

### Example 1: Monitoring a Static Crop

1. Add a **WebCam** or **Video** node
2. Add a **Crop Monitor** node
3. Connect the image output to the Crop Monitor
4. Adjust the crop sliders to define the region
5. View the monitoring information in real-time

### Example 2: Chaining with Crop Node

1. Add a **WebCam** or **Video** node
2. Add a **Crop** node and set desired crop parameters
3. Add a **Crop Monitor** node
4. Connect Float Value nodes to provide the same crop parameters to both Crop and Crop Monitor
5. The Crop Monitor will display the dimensions and position of the cropped region

### Example 3: Dynamic Region Monitoring

1. Add an **Image** or **Video** node
2. Add **Float Value** nodes for dynamic crop parameters
3. Connect Float Values to the Crop Monitor's crop inputs
4. The monitor will update in real-time as you adjust the values

## Technical Details

### Coordinate System

- **Input coordinates** are normalized (0.0 to 1.0)
- **Output dimensions and positions** are in pixel coordinates
- The center position is calculated as: `(min + (max - min) / 2)`

### Coordinate Validation

The node automatically validates and corrects invalid coordinate ranges:
- If `min_x > max_x`, the values are swapped with a 0.01 offset
- If `min_y > max_y`, the values are swapped with a 0.01 offset

This ensures the crop region always has a valid area.

### Processing Function

The core processing is handled by the `crop_and_get_info()` function:

```python
def crop_and_get_info(image, min_x, max_x, min_y, max_y):
    """
    Crop image and calculate monitoring information
    
    Returns:
    - cropped: The cropped image
    - width_pixels: Width in pixels
    - height_pixels: Height in pixels
    - center_x: X coordinate of center
    - center_y: Y coordinate of center
    """
```

## Implementation Notes

- Follows the same pattern as other ProcessNode nodes
- Compatible with the timestamped queue system
- Supports audio dictionary passthrough for compatibility
- Includes performance counter integration when enabled

## Testing

The node includes comprehensive tests in `tests/test_crop_monitor_node.py`:

- Structure validation
- Import verification
- Function logic testing
- Menu registration check

Run tests with:
```bash
python -m pytest tests/test_crop_monitor_node.py -v
```

## Version

- **Version**: 0.0.1
- **Node Tag**: `CropMonitor`
- **Node Label**: `Crop Monitor`

## See Also

- **Crop Node**: The standard crop node for image cropping
- **Resize Node**: For resizing images
- **Result Image Node**: For displaying final output
