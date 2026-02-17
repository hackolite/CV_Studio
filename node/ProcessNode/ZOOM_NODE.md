# Zoom Node Documentation

## Overview
The Zoom node is a standalone node for cropping images using center-based coordinates and a square crop size.

## Parameters

### Input
- **Image Input**: BGR image to be cropped

### Crop Parameters
- **width**: Width of the square crop (normalized, 0.01 to 1.0)
  - 0.5 = 50% of the image dimension
  - 1.0 = full image size
  
- **center x**: Horizontal position of the crop center (normalized, 0.0 to 1.0)
  - 0.0 = left edge
  - 0.5 = horizontal center
  - 1.0 = right edge
  
- **center y**: Vertical position of the crop center (normalized, 0.0 to 1.0)
  - 0.0 = top edge
  - 0.5 = vertical center
  - 1.0 = bottom edge

### Output
- **Zoomed Image**: BGR image with the same dimensions as input, showing a magnified view of the selected region
- **Processing Time**: Elapsed time in milliseconds (if enabled)

## Behavior

### Zoom Operation
The Zoom node performs a two-step operation:
1. **Crop**: Extracts a square region from the input image based on the width and center parameters
2. **Resize**: Scales the cropped region back to the original input dimensions, creating a zoom effect

The square size is calculated based on the smaller dimension of the input image to ensure the crop fits within the image bounds.

### Output Dimensions
The output image **always maintains the same dimensions as the input image**. The zoom effect is achieved by:
- Cropping a smaller region (e.g., 50% width = 50% of the image)
- Resizing that region back to the full input size
- This effectively magnifies the selected region

### Edge Handling
When the crop extends beyond the image boundaries, the node automatically adjusts the crop position to keep it within the image while maintaining the requested square size.

### Examples

#### Example 1: Center Zoom (2x magnification)
```python
width = 0.5     # 50% crop
center_x = 0.5  # centered horizontally
center_y = 0.5  # centered vertically
# Result: Center region magnified 2x, output dimensions match input
```

#### Example 2: Top-Left Zoom (3.3x magnification)
```python
width = 0.3     # 30% crop
center_x = 0.2  # 20% from left
center_y = 0.2  # 20% from top
# Result: Top-left region magnified 3.3x, output dimensions match input
```

#### Example 3: Heavy Zoom In (5x magnification)
```python
width = 0.2     # 20% crop (smaller = more zoom)
center_x = 0.5  # centered horizontally
center_y = 0.5  # centered vertically
# Result: Center region magnified 5x, output dimensions match input
```

## Comparison with Crop Node

| Feature | Crop Node | Zoom Node |
|---------|-----------|-----------|
| Parameters | min_x, max_x, min_y, max_y | width, center_x, center_y |
| Output Shape | Variable rectangle (smaller than input) | Same as input (resized) |
| Output Dimensions | Smaller than input | Same as input |
| Use Case | Extract a region | Magnify a region |
| Parameter Style | Absolute bounds | Center + size |

## Comparison with CropMonitor Node

| Feature | CropMonitor Node | Zoom Node |
|---------|------------------|-----------|
| Monitoring Info | Yes (displays width, height, center) | No |
| Parameters | min_x, max_x, min_y, max_y | width, center_x, center_y |
| Output Shape | Variable rectangle (smaller than input) | Same as input (resized) |
| Output Dimensions | Smaller than input | Same as input |
| Primary Purpose | Crop with visual feedback | Magnified view |

## Technical Details

### Implementation
The zoom effect is achieved through a two-step process:

1. **Cropping**: `crop_from_center(image, width, center_x, center_y)` extracts a square region
   - Square size calculated from: `int(width * min(image_width, image_height))`
   - Boundary clamping ensures crop stays within image bounds
   - All coordinates are normalized (0.0 to 1.0)

2. **Resizing**: The cropped region is resized back to the original input dimensions using OpenCV's `cv2.resize()`
   - Uses `INTER_LINEAR` interpolation for good quality
   - Output dimensions always match input dimensions
   - Creates the magnification effect

### Boundary Handling
- Width < 0.01 → clamped to 0.01
- Width > 1.0 → clamped to 1.0
- Center positions clamped to keep crop within image
- Minimum crop size: 1 pixel

### Magnification Factor
The magnification factor is approximately `1 / width`:
- width = 0.5 → 2x magnification
- width = 0.25 → 4x magnification
- width = 0.1 → 10x magnification

## Use Cases

1. **Digital Zoom**: Create a zoom effect by reducing width parameter
2. **Face Tracking**: Crop around detected face center
3. **Object Focus**: Center crop around detected objects
4. **Thumbnail Generation**: Create square thumbnails from arbitrary images
5. **Region of Interest**: Extract square regions for further processing
