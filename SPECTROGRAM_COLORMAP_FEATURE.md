# Spectrogram Colormap Feature

## Overview

This feature adds configurable colormap support to spectrograms in CV_Studio, improving visualization quality and making it easier to detect events in audio/video data. Previously, spectrograms used a hardcoded 'magma' colormap from matplotlib. Now, the system uses a flexible utility module that supports multiple colormaps with both OpenCV and matplotlib backends.

## Key Changes

### 1. New Utility Module: `node/InputNode/spectrogram_utils.py`

A dedicated module for spectrogram colormap operations with three main functions:

#### `apply_colormap_cv2(spectrogram_2d, colormap=cv2.COLORMAP_INFERNO)`
- **Purpose**: Apply colormap using OpenCV (fast, efficient, recommended)
- **Input**: 2D numpy array (H x W) with float or int values
- **Output**: RGB uint8 image (H x W x 3)
- **Features**:
  - Automatic normalization (0-255)
  - BGR to RGB conversion
  - Supports all OpenCV colormaps

#### `apply_colormap_mpl(spectrogram_2d, cmap_name='viridis')`
- **Purpose**: Apply colormap using matplotlib (fallback method)
- **Input**: 2D numpy array (H x W) with float or int values
- **Output**: RGB uint8 image (H x W x 3)
- **Features**:
  - Handles NaN/Inf values gracefully
  - RGBA to RGB conversion
  - Supports all matplotlib colormaps

#### `apply_colormap_to_spectrogram(arr2d, method='cv2', cmap='INFERNO')`
- **Purpose**: Unified wrapper function that auto-detects method and colormap
- **Parameters**:
  - `arr2d`: 2D spectrogram array
  - `method`: 'cv2' (default) or 'mpl'
  - `cmap`: Colormap name (e.g., 'INFERNO', 'VIRIDIS', 'JET')
- **Features**:
  - Smart colormap constant resolution
  - Fallback to INFERNO if colormap not found
  - Input validation

### 2. Refactored `node/InputNode/node_video.py`

#### Changes to VideoNode Class

**New Import**:
```python
from node.InputNode.spectrogram_utils import apply_colormap_to_spectrogram
```

**New Constants**:
```python
DEFAULT_SPECTROGRAM_COLORMAP = 'INFERNO'
```

**New Instance Variable**:
```python
self._spectrogram_colormap = DEFAULT_SPECTROGRAM_COLORMAP
```

#### Updated `_prepare_spectrogram()` Method

**Before** (hardcoded matplotlib colormap):
```python
cmap = matplotlib.colormaps['magma']
S_colored = cmap(ims_normalized)
S_rgb = (S_colored[:, :, :3] * 255).astype(np.uint8)
# ... transpose, flip, convert to BGR
```

**After** (configurable utility function):
```python
ims_transposed = np.transpose(ims, (1, 0))
S_rgb = apply_colormap_to_spectrogram(
    ims_transposed, 
    method='cv2', 
    cmap=self._spectrogram_colormap
)
S_rgb = np.flipud(S_rgb)
S_bgr = cv2.cvtColor(S_rgb, cv2.COLOR_RGB2BGR)
```

**Benefits**:
- Simplified code (utility handles normalization)
- Better NaN/Inf handling
- Configurable colormap selection
- More efficient (OpenCV backend)

## Available Colormaps

### OpenCV Colormaps (Recommended)
- **INFERNO** (default): Perceptually uniform, excellent for data visualization
- **VIRIDIS**: Colorblind-friendly, perceptually uniform
- **PLASMA**: Bright, high-contrast, perceptually uniform
- **MAGMA**: Similar to INFERNO with more purple tones
- **JET**: Classic rainbow colormap (not perceptually uniform, but familiar)
- **HOT**: Red-yellow-white progression (thermal-like)
- **TURBO**: Improved version of JET with better perceptual properties
- And many more (see `AVAILABLE_OPENCV_COLORMAPS` in `spectrogram_utils.py`)

### Matplotlib Colormaps (Fallback)
All matplotlib colormaps are supported when using `method='mpl'`:
- inferno, viridis, plasma, magma, cividis
- jet, rainbow, hot, cool, spring, summer, autumn, winter
- And many more from matplotlib's collection

## Usage Examples

### Basic Usage (Default Colormap)
```python
from node.InputNode.spectrogram_utils import apply_colormap_to_spectrogram
import numpy as np

# Your 2D spectrogram data
spectrogram = np.random.rand(256, 512) * 100

# Apply default INFERNO colormap
colored_img = apply_colormap_to_spectrogram(spectrogram)
# Returns: (256, 512, 3) RGB uint8 array
```

### Using Different Colormaps
```python
# Use VIRIDIS colormap
colored_img = apply_colormap_to_spectrogram(
    spectrogram, 
    method='cv2', 
    cmap='VIRIDIS'
)

# Use JET colormap for classic rainbow look
colored_img = apply_colormap_to_spectrogram(
    spectrogram, 
    method='cv2', 
    cmap='JET'
)
```

### Using Matplotlib Backend
```python
# Use matplotlib's 'plasma' colormap
colored_img = apply_colormap_to_spectrogram(
    spectrogram, 
    method='mpl', 
    cmap='plasma'
)
```

### Configuring VideoNode
```python
from node.InputNode.node_video import VideoNode

# Create node
node = VideoNode()

# Change colormap (before preparing spectrogram)
node._spectrogram_colormap = 'VIRIDIS'

# Prepare spectrogram (will use VIRIDIS)
node._prepare_spectrogram(node_id, video_path)
```

## Testing

### Test Suite: `tests/test_spectrogram_colormap.py`

Comprehensive test coverage including:
- ✅ Basic colormap application (OpenCV)
- ✅ Multiple colormap support
- ✅ Matplotlib backend testing
- ✅ Wrapper function testing
- ✅ Edge cases (uniform values, NaN values)
- ✅ Invalid input handling
- ✅ Output validation (shape, dtype, non-grayscale)
- ✅ File I/O testing

Run tests:
```bash
pytest tests/test_spectrogram_colormap.py -v
```

### Demo Script: `tests/demo_spectrogram_colormap.py`

Demonstrates the feature with real audio signal processing:
- Generates synthetic audio with multiple frequency components
- Computes spectrogram using librosa
- Applies multiple colormaps
- Saves comparison images

Run demo:
```bash
python tests/demo_spectrogram_colormap.py
```

Output images saved to: `/tmp/demo_spectrogram_*.png`

## Technical Details

### Color Space Handling

The utility functions ensure proper color space conversion:

1. **OpenCV Method**: 
   - OpenCV's `applyColorMap()` returns BGR
   - Automatically converted to RGB for consistency
   - Frontend receives RGB or BGR as needed

2. **Matplotlib Method**:
   - Matplotlib returns RGBA (0-1 range)
   - Alpha channel discarded
   - Scaled to uint8 (0-255) RGB

### Normalization Strategy

The utility handles normalization internally:
- Uses `cv2.normalize()` with `NORM_MINMAX` for OpenCV
- Custom normalization for matplotlib (handles NaN/Inf)
- Clips values to valid range [0, 255]
- Converts to uint8 for optimal memory usage

### Edge Case Handling

Robust handling of problematic data:
- **NaN values**: Replaced with 0 or minimum value
- **Inf values**: Clamped to valid range
- **Uniform data**: Returns mid-tone colored image
- **Empty data**: Returns black or minimum value colored image

## Performance Considerations

### OpenCV vs Matplotlib

**OpenCV (Recommended)**:
- ⚡ Faster execution (~5-10x)
- 🎨 21+ built-in colormaps
- 💾 Lower memory footprint
- ✅ Direct uint8 support

**Matplotlib**:
- 🐌 Slower (Python-based)
- 🎨 100+ colormaps
- 📊 Better for scientific visualization
- 🔄 More flexible customization

**Recommendation**: Use OpenCV (`method='cv2'`) for production, matplotlib for research/experimentation.

## Migration from Old Code

### For Existing Code Using Matplotlib

**Old approach**:
```python
# Manual normalization
ims_normalized = (ims - ims.min()) / (ims.max() - ims.min())
cmap = matplotlib.colormaps['magma']
S_colored = cmap(ims_normalized)
S_rgb = (S_colored[:, :, :3] * 255).astype(np.uint8)
```

**New approach**:
```python
# Single function call
S_rgb = apply_colormap_to_spectrogram(ims, method='cv2', cmap='MAGMA')
```

### For Existing VideoNode Instances

No changes required! The default colormap (INFERNO) is automatically applied. To change:

```python
node._spectrogram_colormap = 'VIRIDIS'  # Or any other colormap
```

## Future Enhancements

Possible future improvements:
1. **UI Configuration**: Add colormap selector to DearPyGUI interface
2. **Per-Node Settings**: Allow different nodes to use different colormaps
3. **Custom Colormaps**: Support user-defined colormap gradients
4. **Dynamic Switching**: Change colormap in real-time during playback
5. **Colormap Presets**: Pre-configured sets for different use cases

## References

- OpenCV ColorMaps: https://docs.opencv.org/master/d3/d50/group__imgproc__colormap.html
- Matplotlib Colormaps: https://matplotlib.org/stable/tutorials/colors/colormaps.html
- Perceptually Uniform Colormaps: https://bids.github.io/colormap/

## License

This feature is part of CV_Studio and follows the same license as the main project.

## Contributors

- Implementation based on requirements for improved spectrogram visualization
- Uses OpenCV and matplotlib libraries for colormap rendering
- Inspired by scientific visualization best practices

---

**Last Updated**: November 2025
**Version**: 1.0.0
