# Heatmap Parameters Enhancement

## Summary

Added configurable parameters to control the heatmap visualization in both `node_heatmap.py` and `node_obj_heatmap.py`. Users can now adjust blur intensity, colormap style, and overlay transparency using intuitive sliders and dropdowns.

## New Parameters

### 1. Blur Slider
- **Label**: "Blur"
- **Type**: Integer slider
- **Range**: 1 to 99
- **Default**: 25
- **Description**: Controls the Gaussian blur kernel size for smoothing the heatmap. Lower values produce sharper heatmaps with more defined edges, while higher values create smoother, more diffused heatmaps.

### 2. Colormap Dropdown
- **Label**: "Colormap"
- **Type**: Dropdown selection
- **Options**: JET, HOT, COOL, RAINBOW, VIRIDIS, TURBO
- **Default**: JET
- **Description**: Selects the color scheme for the heatmap visualization:
  - **JET**: Blue to red through cyan, yellow (classic thermal colormap)
  - **HOT**: Black to white through red, yellow (heat-based colormap)
  - **COOL**: Cyan to magenta (cool tones)
  - **RAINBOW**: Full spectrum rainbow colors
  - **VIRIDIS**: Perceptually uniform colormap (good for scientific visualization)
  - **TURBO**: Enhanced rainbow with better perceptual uniformity

### 3. Blend Alpha Slider
- **Label**: "Blend Alpha"
- **Type**: Float slider
- **Range**: 0.0 to 1.0
- **Default**: 0.6
- **Description**: Controls the transparency of the heatmap overlay on the input image:
  - **0.0**: Shows only the original image (no heatmap)
  - **0.5**: Equal blend of image and heatmap
  - **1.0**: Shows only the heatmap (no original image)

### 4. Memory Slider (Already Existed)
- **Label**: "Memory"
- **Type**: Float slider
- **Range**: 0.80 to 0.995
- **Default**: 0.98
- **Description**: Controls how long heatmap values persist (decay rate). Higher values retain heat longer.

## Technical Implementation

### node_heatmap.py
- Added three new input attributes (Input05, Input06, Input07) for blur, colormap, and blend alpha
- Implemented automatic blur kernel size adjustment (ensures odd values for GaussianBlur)
- Added colormap dictionary mapping for OpenCV constants
- Modified the blend calculation to use configurable alpha: `cv2.addWeighted(frame, 1.0 - blend_alpha, colored_heatmap, blend_alpha, 0)`
- Updated `get_setting_dict()` and `set_setting_dict()` to save/load new parameters
- Backward compatibility: defaults provided for existing saved configurations

### node_obj_heatmap.py
- Added four new node attributes (Blur, Colormap, BlendValue) plus the existing AlphaValue (Memory) and ClassValue
- Same implementation as node_heatmap.py for consistency
- Maintains class filtering functionality alongside new parameters
- Backward compatibility: defaults provided for existing saved configurations

## Files Modified

1. **node/VisualNode/node_heatmap.py**
   - Added UI controls for new parameters
   - Updated update() method to use configurable values
   - Enhanced get/set_setting_dict for persistence

2. **node/VisualNode/node_obj_heatmap.py**
   - Added UI controls for new parameters
   - Updated update() method to use configurable values
   - Enhanced get/set_setting_dict for persistence

3. **tests/test_heatmap_parameters.py** (New)
   - Unit tests for blur parameter
   - Unit tests for colormap parameter
   - Unit tests for blend alpha parameter
   - Visual output generation for validation

## Usage Example

When using the heatmap nodes in the CV Studio interface:

1. **Adjust Blur**: Move the "Blur" slider to control how smooth or sharp the heatmap appears
   - Low values (1-15): Sharp, defined regions
   - Medium values (15-35): Balanced smoothing
   - High values (35-99): Very smooth, diffused appearance

2. **Change Colormap**: Select from the "Colormap" dropdown to change the color scheme
   - Try different colormaps to find the best visualization for your use case
   - VIRIDIS and TURBO are recommended for scientific accuracy

3. **Adjust Transparency**: Move the "Blend Alpha" slider to control how much the heatmap overlays the original image
   - Low values (0.0-0.3): Subtle overlay, original image dominates
   - Medium values (0.3-0.7): Balanced overlay
   - High values (0.7-1.0): Strong overlay, heatmap dominates

4. **Control Memory**: Use the "Memory" slider to adjust how long detections remain visible
   - Higher values: Longer persistence, better for tracking movement over time
   - Lower values: Faster decay, better for real-time current state

## Backward Compatibility

All changes are backward compatible:
- Existing saved configurations will load with default values for new parameters
- Default values match previous hardcoded behavior (blur=25, colormap=JET, blend_alpha=0.6)
- No breaking changes to the node API or connections

## Benefits

1. **Flexibility**: Users can now customize heatmap appearance to their specific needs
2. **Visual Clarity**: Adjust parameters to optimize visibility for different scenarios
3. **Experimentation**: Easy to try different configurations without code changes
4. **Accessibility**: Intuitive sliders and dropdowns for non-technical users
5. **Scientific Visualization**: VIRIDIS and TURBO colormaps provide perceptually uniform options
