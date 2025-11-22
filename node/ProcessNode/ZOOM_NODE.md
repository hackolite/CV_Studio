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
- **Cropped Image**: Square cropped BGR image
- **Processing Time**: Elapsed time in milliseconds (if enabled)

## Behavior

### Square Cropping
The Zoom node always produces square crops. The square size is calculated based on the smaller dimension of the input image to ensure the crop fits within the image bounds.

### Edge Handling
When the crop extends beyond the image boundaries, the node automatically adjusts the crop position to keep it within the image while maintaining the requested square size.

### Examples

#### Example 1: Center Crop
```python
width = 0.5     # 50% crop
center_x = 0.5  # centered horizontally
center_y = 0.5  # centered vertically
# Result: 50% square crop from the center of the image
```

#### Example 2: Top-Left Crop
```python
width = 0.3     # 30% crop
center_x = 0.2  # 20% from left
center_y = 0.2  # 20% from top
# Result: 30% square crop near the top-left
```

#### Example 3: Zoom In
```python
width = 0.2     # 20% crop (smaller = more zoom)
center_x = 0.5  # centered horizontally
center_y = 0.5  # centered vertically
# Result: 20% square crop from center (5x zoom effect)
```

## Comparison with Crop Node

| Feature | Crop Node | Zoom Node |
|---------|-----------|-----------|
| Parameters | min_x, max_x, min_y, max_y | width, center_x, center_y |
| Output Shape | Any rectangle | Always square |
| Use Case | Precise rectangular crops | Center-based zoom/crop |
| Parameter Style | Absolute bounds | Center + size |

## Comparison with CropMonitor Node

| Feature | CropMonitor Node | Zoom Node |
|---------|------------------|-----------|
| Monitoring Info | Yes (displays width, height, center) | No |
| Parameters | min_x, max_x, min_y, max_y | width, center_x, center_y |
| Output Shape | Any rectangle | Always square |
| Primary Purpose | Crop with visual feedback | Simple zoom/crop |

## Technical Details

### Implementation
- Function: `crop_from_center(image, width, center_x, center_y)`
- Square size calculated from: `int(width * min(image_width, image_height))`
- Boundary clamping ensures crop stays within image bounds
- All coordinates are normalized (0.0 to 1.0)

### Boundary Handling
- Width < 0.01 → clamped to 0.01
- Width > 1.0 → clamped to 1.0
- Center positions clamped to keep crop within image
- Minimum crop size: 1 pixel

## Use Cases

1. **Digital Zoom**: Create a zoom effect by reducing width parameter
2. **Face Tracking**: Crop around detected face center
3. **Object Focus**: Center crop around detected objects
4. **Thumbnail Generation**: Create square thumbnails from arbitrary images
5. **Region of Interest**: Extract square regions for further processing
